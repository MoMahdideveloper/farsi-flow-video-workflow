#!/usr/bin/env python3
"""Read-only diagnostics for the Farsi Google Flow Video Pipeline.

Checks likely problems; it cannot prove semantic continuity or complete speech:
  1. 8.0s Veo Speech Cutoffs / Dropped Clauses:
     - Pre-submission gate: flags any 8s clip subtitle > MAX_WORDS_PER_8S_CLIP (18 words)
       or > MAX_CHARS_PER_8S_CLIP (105 chars).
     - Post-generation gate: runs faster-whisper Persian word-level ASR on every
       raw_unsubbed/clip_XX.mp4 and checks (a) overall word recall against the
       manifest subtitle, (b) first-2-words & last-2-words presence, and
       (c) tail speech touching the 8.0s Veo ceiling (>= 7.92s).
  2. Source Story Compression / Dropped Scenes:
     - Checks manifest `source_span` coverage against the source video duration
       and flags any uncovered gap > MAX_UNCOVERED_SOURCE_GAP_SEC (14.0s) or any
       single 8s clip compressing > MAX_SOURCE_SPAN_PER_CLIP_SEC (28.0s).
  3. Context-Compaction Drift (Manifest <-> Batch Prompt <-> Keyframe <-> Publish Kit):
     - Verifies that the Persian quote «...» in `submit_flow_batch.mjs` matches
       the manifest's `subtitles` for every clip.
     - Verifies that `keyframes/kf_provenance.json` exists and locks each keyframe's
       SHA-256 and `story_beat` to the manifest's `story_beat`.
Publication still requires the separate documented visual and audio reviews.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from difflib import SequenceMatcher
from typing import Any

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding="utf-8")

SPEECH_BUDGET = json.loads(Path(__file__).with_name('production_policy.json').read_text(encoding='utf-8'))['speech_budget']
MAX_WORDS_PER_8S_CLIP = SPEECH_BUDGET['max_words']
MAX_CHARS_PER_8S_CLIP = SPEECH_BUDGET['max_chars']
MAX_UNCOVERED_SOURCE_GAP_SEC = 14.0
MAX_SOURCE_SPAN_PER_CLIP_SEC = 28.0
MIN_ASR_WORD_RECALL = 0.72
TAIL_CUTOFF_SEC = 7.92

_HARAKAT = re.compile(r"[\u064B-\u065F\u0670]")
_PERSIAN_CLEAN = re.compile(r"[^\w\u0600-\u06FF]+")


def strip_harakat(text: str) -> str:
    return _HARAKAT.sub("", text)


def normalize_dialogue(text: str) -> str:
    return ' '.join(strip_harakat(text).replace('ي', 'ی').replace('ك', 'ک').split())


def normalize_fa_words(text: str) -> list[str]:
    text = normalize_dialogue(text).replace("\u200c", " ")
    cleaned = _PERSIAN_CLEAN.sub(" ", text)
    return cleaned.split()


def word_match(expected: str, actual_words: list[str]) -> bool:
    return not expected or expected in actual_words


def expand_vars(val: str, variables: dict[str, str]) -> str:
    for _ in range(4):
        for k, v in variables.items():
            val = val.replace(f"${{{k}}}", v)
    return val


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_batch_prompts(batch_mjs_path: Path, batch_key: str) -> dict[int, str]:
    text = batch_mjs_path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"BATCHES\.{re.escape(batch_key)}\s*=\s*\[(.*?)\n\];",
        re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        return {}
    block = m.group(1)
    out: dict[int, str] = {}
    for cm in re.finditer(
        r"clip:\s*(\d+).*?prompt:\s*'((?:\\'|[^'])*)'",
        block,
        re.DOTALL,
    ):
        out[int(cm.group(1))] = cm.group(2)
    return out


def validate_manifest(
    manifest_path: Path,
    *,
    batch_mjs_path: Path | None = None,
    batch_key: str | None = None,
    run_asr: bool = False,
    whisper_model: Any = None,
) -> dict[str, Any]:
    manifest_path = Path(manifest_path).resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    variables = {'MANIFEST_DIR': str(manifest_path.parent), **data.get("variables", {})}
    def asset(value):
        path = Path(expand_vars(value, variables))
        return path if path.is_absolute() else manifest_path.parent / path
    clips = data.get("clips", [])
    issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    # 1. Dialogue length & source span compression checks
    prev_span_end = float(data.get("source_start_offset", 0.0))
    for c in clips:
        cid = c["id"]
        sub_text = " ".join(s[3] if isinstance(s, list) else s["text"] for s in c.get("subtitles", []))
        clean_sub = normalize_dialogue(sub_text)
        words = clean_sub.split()
        duration = float(c.get('generation_duration_sec', 8))
        if duration <= 0:
            issues.append({'clip': cid, 'gate': 'GATE1_DIALOGUE_LENGTH', 'code': 'INVALID_DURATION', 'detail': 'Generation duration must be positive'})
            duration = 8
        max_words = int(MAX_WORDS_PER_8S_CLIP * duration / SPEECH_BUDGET['reference_duration_sec'])
        max_chars = int(MAX_CHARS_PER_8S_CLIP * duration / SPEECH_BUDGET['reference_duration_sec'])
        if len(words) > max_words or len(clean_sub) > max_chars:
            issues.append({
                "clip": cid,
                "gate": "GATE1_DIALOGUE_LENGTH",
                "code": "DIALOGUE_TOO_LONG_FOR_8S_CLIP",
                "detail": f"{len(words)} words / {len(clean_sub)} chars for {duration:g}s (max {max_words} words / {max_chars} chars)",
                "text": sub_text,
            })

        span = c.get("source_span")
        if span and len(span) == 2:
            s0, s1 = float(span[0]), float(span[1])
            if s1 - s0 > MAX_SOURCE_SPAN_PER_CLIP_SEC:
                issues.append({
                    "clip": cid,
                    "gate": "GATE2_SOURCE_COVERAGE",
                    "code": "SOURCE_SPAN_OVERCOMPRESSED",
                    "detail": f"Clip covers {s1 - s0:.1f}s of source video ({s0:.1f}s..{s1:.1f}s) in a single 8s clip (max {MAX_SOURCE_SPAN_PER_CLIP_SEC}s)",
                })
            if s0 - prev_span_end > MAX_UNCOVERED_SOURCE_GAP_SEC:
                issues.append({
                    "clip": cid,
                    "gate": "GATE2_SOURCE_COVERAGE",
                    "code": "SOURCE_SCENE_GAP",
                    "detail": f"Uncovered source video gap of {s0 - prev_span_end:.1f}s ({prev_span_end:.1f}s..{s0:.1f}s) before {cid}",
                })
            prev_span_end = max(prev_span_end, s1)

    # 2. Batch prompt sync check (Gate 3A)
    legacy_requested = bool(batch_key)
    if legacy_requested or any('generation_prompt' in c for c in clips):
        prompts = parse_batch_prompts(batch_mjs_path, batch_key) if batch_mjs_path and batch_key and batch_mjs_path.is_file() else {}
        for c in clips:
            cid = c["id"]
            sub_text = " ".join(s[3] if isinstance(s, list) else s["text"] for s in c.get("subtitles", []))
            suffix = re.search(r'(\d+)$', cid)
            idx = int(suffix.group(1)) if suffix else None
            p = prompts.get(idx) if legacy_requested else c.get('generation_prompt')
            if not p:
                issues.append({
                    "clip": cid,
                    "gate": "GATE3_MANIFEST_BATCH_SYNC",
                    "code": "MISSING_BATCH_PROMPT",
                    "detail": f"No prompt for clip {idx} in BATCHES.{batch_key}",
                })
                continue
            quoted = ' '.join(re.findall(r"«([^»]*)»", p))
            if normalize_dialogue(quoted) != normalize_dialogue(sub_text):
                issues.append({
                    "clip": cid,
                    "gate": "GATE3_MANIFEST_BATCH_SYNC",
                    "code": "PROMPT_SUBTITLE_MISMATCH",
                    "detail": f"Batch prompt Farsi quote does not match manifest subtitle",
                    "batch_quote": quoted,
                    "manifest_subtitle": sub_text,
                })

    # 3. Keyframe provenance check (Gate 3B)
    if clips:
        first_kf = asset(clips[0].get("keyframe", ""))
        prov_path = first_kf.parent / "kf_provenance.json"
        if not prov_path.is_file():
            warnings.append({
                "gate": "GATE3_KEYFRAME_PROVENANCE",
                "code": "MISSING_KF_PROVENANCE_LOCK",
                "detail": f"No {prov_path} found locking keyframe SHA-256 and story_beat to manifest",
            })
        else:
            prov = json.loads(prov_path.read_text(encoding="utf-8"))
            for c in clips:
                cid = c["id"]
                kf_path = asset(c.get("keyframe", ""))
                entry = prov.get("clips", {}).get(cid)
                if not entry:
                    issues.append({
                        "clip": cid,
                        "gate": "GATE3_KEYFRAME_PROVENANCE",
                        "code": "MISSING_CLIP_PROVENANCE",
                        "detail": f"{cid} missing from {prov_path.name}",
                    })
                else:
                    if entry.get("story_beat") != c.get("story_beat"):
                        issues.append({
                            "clip": cid,
                            "gate": "GATE3_KEYFRAME_PROVENANCE",
                            "code": "KEYFRAME_BEAT_MISMATCH",
                            "detail": f"Keyframe provenance beat {entry.get('story_beat')!r} != manifest beat {c.get('story_beat')!r}",
                        })
                    if kf_path.is_file() and entry.get("sha256") != sha256_file(kf_path):
                        issues.append({
                            "clip": cid,
                            "gate": "GATE3_KEYFRAME_PROVENANCE",
                            "code": "KEYFRAME_SHA256_MISMATCH",
                            "detail": f"Keyframe file {kf_path.name} changed without updating provenance lock",
                        })

    # 4. Post-generation ASR word-level completeness check (Gate 4)
    if run_asr and whisper_model is None:
        issues.append({'gate': 'GATE4_ASR_SPEECH_COMPLETENESS', 'code': 'MISSING_ASR_MODEL', 'detail': 'ASR requested without an available model'})
    if run_asr and whisper_model is not None:
        clips_dir = asset(data.get("clips_dir", ""))
        raw_dir = clips_dir / "raw_unsubbed"
        for c in clips:
            cid = c["id"]
            mp4 = raw_dir / c["file"]
            if not mp4.is_file():
                mp4 = clips_dir / c['file']
            if not mp4.is_file():
                issues.append({'clip': cid, 'gate': 'GATE4_ASR_SPEECH_COMPLETENESS', 'code': 'MISSING_ASR_MEDIA', 'detail': f'Missing clip for requested ASR: {mp4}'})
                continue
            sub_text = " ".join(s[3] if isinstance(s, list) else s["text"] for s in c.get("subtitles", []))
            exp_words = normalize_fa_words(sub_text)
            segs, _ = whisper_model.transcribe(str(mp4), language="fa", word_timestamps=True)
            asr_words_timed = [
                (w.word.strip(), float(w.start), float(w.end))
                for s in segs
                for w in (s.words or [])
            ]
            asr_text = " ".join(w[0] for w in asr_words_timed)
            act_words = normalize_fa_words(asr_text)
            matched = sum(block.size for block in SequenceMatcher(None, exp_words, act_words, autojunk=False).get_matching_blocks())
            exp_skel = "".join(exp_words)
            act_skel = "".join(act_words)
            recall = matched / max(1, len(exp_words)) if exp_words else float(not act_words)
            last_end = asr_words_timed[-1][2] if asr_words_timed else 0.0
            tail_words_ok = (
                all(word_match(ew, act_words[-4:]) for ew in exp_words[-2:])
            ) if len(exp_words) >= 2 else True
            head_words_ok = (
                all(word_match(ew, act_words[:4]) for ew in exp_words[:2])
            ) if len(exp_words) >= 2 else True

            if last_end >= TAIL_CUTOFF_SEC and not tail_words_ok:
                issues.append({
                    "clip": cid,
                    "gate": "GATE4_ASR_SPEECH_COMPLETENESS",
                    "code": "ASR_TAIL_SPEECH_CUT_AT_8S",
                    "detail": f"Speech hit {last_end:.2f}s ceiling and cut off final words {exp_words[-2:]}",
                    "expected": sub_text,
                    "asr_heard": asr_text,
                })
            elif recall < MIN_ASR_WORD_RECALL or not tail_words_ok or not head_words_ok:
                issues.append({
                    "clip": cid,
                    "gate": "GATE4_ASR_SPEECH_COMPLETENESS",
                    "code": "ASR_INCOMPLETE_SPEECH",
                    "detail": f"ASR word recall={recall:.2f} (head_ok={head_words_ok}, tail_ok={tail_words_ok}, last_end={last_end:.2f}s)",
                    "expected": sub_text,
                    "asr_heard": asr_text,
                })

    return {
        'ready_to_publish': False,
        'scope': 'diagnostic_checks_only',
        "manifest": str(manifest_path),
        "episode_id": data.get("episode_id"),
        "passed": len(issues) == 0,
        "issue_count": len(issues),
        "issues": issues,
        "warnings": warnings,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate Farsi Flow story manifests and clips against all 4 gates.")
    ap.add_argument("manifests", nargs="+", help="Path(s) to manifest JSON files")
    ap.add_argument("--batch-mjs", default=r"C:\Users\LifeCycle\.gemini\antigravity\scratch\farsi-flow-video-workflow\scripts\submit_flow_batch.mjs")
    ap.add_argument("--batch-key", help="Optional BATCHES.<key> name when validating a single manifest")
    ap.add_argument("--asr", action="store_true", help="Run faster-whisper Persian word-level ASR gate on raw_unsubbed clips")
    args = ap.parse_args()

    whisper_model = None
    if args.asr:
        from faster_whisper import WhisperModel
        whisper_model = WhisperModel("small", device="cpu", compute_type="int8")

    batch_mjs = Path(args.batch_mjs) if args.batch_mjs else None
    all_passed = True
    for m_str in args.manifests:
        mp = Path(m_str)
        bkey = args.batch_key
        if not bkey:
            m = re.match(r"story(\d+)_", mp.name)
            if m:
                bkey = f"s4_story{m.group(1)}"
            elif (m2 := re.match(r"emotional_part(\d+)", mp.name)):
                bkey = f"eg_part{m2.group(1)}"
            elif (m3 := re.match(r"pizza_part(\d+)", mp.name)):
                bkey = f"pz_part{m3.group(1)}"
        res = validate_manifest(mp, batch_mjs_path=batch_mjs, batch_key=bkey, run_asr=args.asr, whisper_model=whisper_model)
        status = "PASS" if res["passed"] else "FAIL"
        print(f"\n=== [{status}] {res['episode_id']} ({mp.name}) — {res['issue_count']} issue(s) ===")
        for iss in res["issues"]:
            print(f"  [FAIL] {iss.get('clip', 'episode')} | {iss['gate']} | {iss['code']}: {iss['detail']}")
            if "asr_heard" in iss:
                print(f"         Expected : {iss['expected']}")
                print(f"         ASR Heard: {iss['asr_heard']}")
        for w in res["warnings"]:
            print(f"  [WARN] {w['gate']} | {w['code']}: {w['detail']}")
        if not res["passed"]:
            all_passed = False

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
