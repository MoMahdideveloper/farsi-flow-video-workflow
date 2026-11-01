import importlib.util
import json
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / 'pipeline' / 'release_review.py'
spec = importlib.util.spec_from_file_location('release_review', MODULE)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


@pytest.fixture
def case(tmp_path):
    paths = {}
    for name in ('master.mp4', 'master.srt', 'source.mp4', 'frame.jpg', 'manifest.json'):
        paths[name] = tmp_path / name
        paths[name].write_text(name, encoding='utf-8')
    record = lambda name: {'path': str(paths[name]), 'sha256': review.digest(paths[name])}
    report = {
        'command': 'build', 'episode_id': 'pilot', 'overall_automatic': 'pass',
        'manifest': record('manifest.json'),
        'master': {'path': str(paths['master.mp4']), 'srt': str(paths['master.srt']),
                   'media': record('master.mp4') | {'pass': True}},
        'clips': [{'id': 'clip_01', 'keyframe': str(paths['frame.jpg']),
                   'provenance': {'source': str(paths['source.mp4']),
                                  'source_sha256': review.digest(paths['source.mp4'])}}],
        'step_trace': {'step_2_keyframe_preflight': {'clips': {'clip_01': record('frame.jpg')}}},
        'gates': {'automatic': {'master_media': 'pass'}, 'human_review': {'voice_continuity': 'pending'}}
    }
    qa = tmp_path / 'qa_report.json'
    qa.write_text(json.dumps(report), encoding='utf-8')
    return qa, paths, report


def approved(qa):
    package = review.make_template(qa)
    for name in package['reviews']:
        package['reviews'][name] = {'status': 'pass', 'reviewer': 'test reviewer',
                                    'evidence': 'Synthetic test evidence',
                                    'reviewed_at': '2026-10-31T20:00:00Z'}
    return package


def test_pending_reviews_cannot_release(case, tmp_path):
    qa, _, _ = case
    package = review.make_template(qa)
    assert not review.check(qa, package)['passed']
    with pytest.raises(ValueError, match='not approved'):
        review.promote(qa, package, tmp_path / 'approved')
    assert not (tmp_path / 'approved').exists()


@pytest.mark.parametrize('name', ['master.mp4', 'master.srt', 'source.mp4', 'frame.jpg', 'manifest.json'])
def test_changed_assets_invalidate_review(case, name):
    qa, paths, _ = case
    package = approved(qa)
    paths[name].write_bytes(b'changed after review')
    assert not review.check(qa, package)['passed']


def test_stale_qa_cannot_be_blessed_by_new_template(case):
    qa, paths, _ = case
    paths['source.mp4'].write_bytes(b'new source but old qa')
    assert not review.check(qa, approved(qa))['passed']


def test_automatic_failure_blocks_even_complete_reviews(case):
    qa, _, report = case
    report['gates']['automatic']['master_media'] = 'fail'
    qa.write_text(json.dumps(report), encoding='utf-8')
    assert not review.check(qa, approved(qa))['passed']


@pytest.mark.parametrize('field', ['reviewer', 'evidence', 'reviewed_at'])
def test_empty_review_evidence_is_not_approval(case, field):
    qa, _, _ = case
    package = approved(qa)
    package['reviews']['story_continuity'][field] = ''
    assert not review.check(qa, package)['passed']


def test_successful_release_copies_only_verified_files(case, tmp_path):
    qa, paths, _ = case
    package = approved(qa)
    output = tmp_path / 'approved'
    receipt = review.promote(qa, package, output)
    assert receipt['publication_status'] == 'approved'
    assert (output / 'master.mp4').read_bytes() == paths['master.mp4'].read_bytes()
    assert (output / 'master.srt').read_bytes() == paths['master.srt'].read_bytes()
    assert json.loads((output / 'release_receipt.json').read_text())['publication_status'] == 'approved'
    with pytest.raises(FileExistsError):
        review.promote(qa, package, output)
