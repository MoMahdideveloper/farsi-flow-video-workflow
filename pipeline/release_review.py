"""Release exact reviewed assets; never confuse an encoded draft with approval.

Review evidence is an operator attestation, not an automatic judgment of meaning.
This module does not modify media, transcripts, or QA verdicts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_REVIEWS = (
    'story_continuity', 'visual_frame_review', 'listen_every_clip_edges',
    'listen_final_master', 'transcript_word_for_word', 'voice_continuity',
)


def digest(path: Path) -> str:
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _read(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def snapshot(report_path: Path) -> tuple[dict, dict, list[str]]:
    report_path = Path(report_path).resolve()
    report = _read(report_path)
    hashes, issues = {}, []

    def add(value, expected=None):
        if not value:
            issues.append('Required asset path missing')
            return
        path = Path(value)
        path = (report_path.parent / path).resolve() if not path.is_absolute() else path.resolve()
        if not path.is_file():
            issues.append(f'Missing asset: {path}')
            return
        actual = digest(path)
        hashes[str(path)] = actual
        if expected and actual != expected:
            issues.append(f'Stale QA fingerprint: {path.name}')

    add(report_path)
    manifest, master = report.get('manifest') or {}, report.get('master') or {}
    add(manifest.get('path'), manifest.get('sha256'))
    add(master.get('path'), (master.get('media') or {}).get('sha256'))
    add(master.get('srt'))
    if not manifest.get('sha256') or not (master.get('media') or {}).get('sha256'):
        issues.append('QA lacks manifest or master fingerprint; rebuild required')
    if master.get('cta_used'):
        add(master.get('cta_video'), master.get('cta_sha256'))
    keyframes = report.get('step_trace', {}).get('step_2_keyframe_preflight', {}).get('clips', {})
    if not report.get('clips'):
        issues.append('QA has no reviewed clip provenance')
    for clip in report.get('clips', []):
        prov = clip.get('provenance') or {}
        add(prov.get('source'), prov.get('source_sha256'))
        if not prov.get('source_sha256'):
            issues.append(f"Missing source fingerprint: {clip.get('id')}")
        if clip.get('keyframe'):
            expected = keyframes.get(clip.get('id'), {}).get('sha256')
            add(clip['keyframe'], expected)
            if not expected:
                issues.append(f"Missing keyframe fingerprint: {clip.get('id')}")
        if prov.get('mode') == 'source_bridge_fallback' or (clip.get('fallback') or {}).get('resolution') == 'source_bridge_fallback':
            issues.append('Source-footage replacement is not permitted for this workflow')
    return report, hashes, issues


def make_template(report_path: Path) -> dict:
    report, hashes, issues = snapshot(report_path)
    names = set(REQUIRED_REVIEWS) | set(report.get('gates', {}).get('human_review', {}))
    return {
        'schema_version': 1, 'episode_id': report.get('episode_id'), 'assets': hashes,
        'snapshot_issues': issues,
        'reviews': {name: {'status': 'pending', 'reviewer': '', 'evidence': '', 'reviewed_at': ''}
                    for name in sorted(names)},
    }


def check(report_path: Path, package: dict) -> dict:
    try:
        report, hashes, issues = snapshot(report_path)
    except (OSError, ValueError, TypeError) as exc:
        return {'passed': False, 'issues': [str(exc)]}
    if package.get('schema_version') != 1 or package.get('episode_id') != report.get('episode_id'):
        issues.append('Review package does not identify this episode/version')
    if package.get('assets') != hashes:
        issues.append('Assets or QA changed since review; repeat affected reviews')
    automatic = report.get('gates', {}).get('automatic', {})
    if report.get('command') != 'build' or report.get('overall_automatic') != 'pass' or not automatic:
        issues.append('A passing full build is required')
    issues += [f'Automatic check not passed: {name}' for name, status in automatic.items() if status != 'pass']
    if (report.get('master') or {}).get('media', {}).get('pass') is not True:
        issues.append('Master media verification not passed')
    names = set(REQUIRED_REVIEWS) | set(report.get('gates', {}).get('human_review', {}))
    reviews = package.get('reviews') or {}
    for name in sorted(names):
        entry = reviews.get(name) or {}
        if not isinstance(entry, dict) or entry.get('status') != 'pass' or any(
            not isinstance(entry.get(field), str) or not entry[field].strip()
            for field in ('reviewer', 'evidence', 'reviewed_at')
        ):
            issues.append(f'Review pending, failed, or undocumented: {name}')
            continue
        try:
            when = datetime.fromisoformat(entry['reviewed_at'].replace('Z', '+00:00'))
            if when.tzinfo is None:
                raise ValueError('timezone required')
        except ValueError:
            issues.append(f'Review timestamp invalid: {name}')
    return {'passed': not issues, 'issues': issues, 'assets': hashes}


def promote(report_path: Path, package: dict, out_dir: Path) -> dict:
    verdict = check(report_path, package)
    if not verdict['passed']:
        raise ValueError('Release not approved: ' + '; '.join(verdict['issues']))
    out_dir = Path(out_dir).resolve()
    if out_dir.exists():
        raise FileExistsError(f'Release directory already exists: {out_dir}; use a new revision')
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    report = _read(report_path)
    with tempfile.TemporaryDirectory(prefix='.release-', dir=out_dir.parent) as temp:
        staging = Path(temp) / 'approved'
        staging.mkdir()
        copies = {}
        for field in ('path', 'srt'):
            source = Path(report['master'][field])
            source = (Path(report_path).resolve().parent / source).resolve() if not source.is_absolute() else source.resolve()
            target = staging / source.name
            if target.exists():
                raise ValueError('Release filenames collide')
            shutil.copyfile(source, target)
            if digest(target) != verdict['assets'][str(source)]:
                raise ValueError('Asset changed during release copy')
            copies[source.name] = digest(target)
        if not check(report_path, package)['passed']:
            raise ValueError('Review inputs changed during release')
        receipt = {'publication_status': 'approved', 'episode_id': report['episode_id'],
                   'created_utc': datetime.now(timezone.utc).isoformat(), 'files': copies,
                   'review_package': package}
        (staging / 'release_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
        # rename, not replace: an existing release is never overwritten.
        os.rename(staging, out_dir)
    return receipt


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('template', 'check', 'promote'))
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--reviews', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'template':
            if not args.out:
                raise ValueError('--out is required')
            result = make_template(args.report)
            with args.out.open('x', encoding='utf-8') as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
        else:
            if not args.reviews:
                raise ValueError('--reviews is required')
            package = _read(args.reviews)
            if args.command == 'promote':
                if not args.out:
                    raise ValueError('--out is required')
                result = promote(args.report, package, args.out)
            else:
                result = check(args.report, package)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get('passed') is False else 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({'passed': False, 'issues': [str(exc)]}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
