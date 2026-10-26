# Series 2 — Stage 2 verification and qualified sign-off

**Date:** 2026-10-26 UTC · **Pipeline:** 1.2.2 · **Target branch:** main

## 1. Decision

**Engineering verification: PASS. Production/publication sign-off: WITHHELD.**

All **203 collected repository tests passed**, with zero failures, skips or expected failures. The dedicated workflow suite separately passed **114/114** tests. This verifies the implemented detection, tracing, speech trimming, synthetic hybrid recovery and offline submission guards—not the meaning or publishability of the five production videos.

The fresh diagnostic audit evaluates **5 parts / 30 clips / 180 per-clip stage records**. It detects **13 metric-failing clips**, comprising **12 keyframe-mismatch flags, 3 contamination flags and 5 internal-cut flags**; categories overlap. Every flagged clip has a story beat and a structurally valid candidate source window. **13 recoveries are planned; zero production replacements were rendered or verified here.** Thus `audit_passed=true`, `all_passed=false` and 13 unresolved clips are correct.

This supersedes the earlier claim in the [Stage 1 architecture report](01-opus55-pipeline-architecture-and-fix.md) that probe-only evaluation resolved all failures and passed all five episodes. A fallback plan is not evidence of an executed repair. Exact scene boundaries and semantic completeness remain unverified without the source host.

### Evidence and tested revision

- [Full, unabridged pytest output](02-astra-pytest-results.txt): 203 passed in 191.59 seconds.
- [Fresh 30-clip audit](trace_parts1_to_5_audit.json) and [original probe input](parts1_to_5_clips_probe.json).
- [Append-only commit trace](TRACE.md), including red/green tests and every incremental content commit.
- Tested code tree: [03c1e703d7f8](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/commit/03c1e703d7f8e27dbc605fe573a8d677868ca5ce). Test-log content commit: [fee7c0b95123](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/commit/fee7c0b95123290c431f5e3be6ae80164456aedd). Subsequent documentation does not change the tested implementation.
- Environment: Python 3.12.3; pytest 9.1.1; FFmpeg/ffprobe 6.1.1; Node v24.22.1; NumPy 2.5.4; Pillow 13.0.0. No installation was required.

## 2. What was independently verified

| Contract | Evidence / result |
|---|---|
| All five manifests | [Parts 1](../../pipeline/manifests/fruits_of_power_part1.json), [2](../../pipeline/manifests/fruits_of_power_part2.json), [3](../../pipeline/manifests/fruits_of_power_part3.json), [4](../../pipeline/manifests/fruits_of_power_part4.json), [5](../../pipeline/manifests/fruits_of_power_part5.json) load successfully. Six clips each; own-part keyframe paths; declared speakers; story beats; finite ordered source spans; fallback and tight trim enabled; separate output directories. Doctor alias includes the caption's دکتر گلابی. Bounds relative to actual source MP4s remain a host check. |
| `evaluate_probe_entry` | Golden clip-by-clip expectations and strict 32.0/5.0 threshold boundaries pass. Missing, malformed, boolean, NaN, infinite and out-of-range metrics fail closed. L1 flags are similarity heuristics, not proof of a particular UI failure or semantic character identity. |
| `analyze_clip_visuals` | Real 9:16 FFmpeg fixtures detect keyframe mismatch, contamination and cuts at 2 and 4 seconds; matching video passes. Keyframe input hashes remain unchanged. |
| Six-stage CLI trace | The actual CLI produces all six named stages for every clip. Missing probe entries and incomplete story metadata fail. Keyframe preflight is skipped when assets are unavailable; acoustic and mux verification are not invented. |
| Speech-safe tight trim | Ten seconds containing three seconds of synthetic speech becomes a 3.55-second planned window; the rendered synthetic hybrid clip is 3.5833 seconds after frame rounding. Pre/post handles are 0.20/0.35 seconds; dropped detected speech is 0.0 seconds. Boundary, minimum-duration, locked-window and internal-silence cases are covered. This is acoustic evidence, not proof of Persian intelligibility. |
| Hybrid fallback | Source interval 2–4 seconds supplies the replacement video; the original Flow clip supplies the audio. All 240 synthetic output frames are processed. Independent compressed-audio hashes and decoded PCM match the Flow input, not the original source soundtrack. Source/keyframe input bytes remain unchanged. |
| Fallback safety | Reversed, zero-length, negative and out-of-duration source windows are rejected; no silent clamping. Audio mismatch does not overwrite a previous output. Inpainting changes only the source subtitle band. Valid cache is reused; corrupted cache is regenerated and verified. |
| Real build failure paths | Missing keyframe evidence and disabled fallback produce failing QA and exit 1. A matching Flow picture is not unnecessarily replaced. Even a passing synthetic build retains pending human-review/publication status. |
| Submission guards | [Submitter](../../scripts/submit_flow_batch.mjs) syntax check and **13/13 offline Node tests** pass. Every paste/retry requires zero chips; confirmed image upload and pre-Start require exactly one. Missing, multiple, lost or delayed chips block rather than silently degrading to text-to-video. JSONL trace writes are exercised; write failures block. No live Google Flow session was accessed. |

The [Python tests](../../tests/test_farsi_flow_workflow.py) exercise the [Node test suite](../../tests/js/submit_flow_batch.test.mjs) as well. Those 13 Node cases are nested checks, not an additional 13 pytest items.

**Audio scope:** bit-exact compressed-audio preservation is verified at the fallback intermediate. Later normalization, loudness processing, trimming and AAC export intentionally transform audio; final-master packet equality is not claimed.

## 3. Exact metric-failure map and recovery plans

Legend: **K** = `KEYFRAME_MISMATCH`; **M** = `MULTI_INGREDIENT_CONTAMINATION`; **C** = `INTERNAL_SCENE_CUT`. Every row below is **planned, not production-verified**. Source seconds refer to each part's original video, not its Flow clip.

| Part / clip | Flags | Candidate source span (seconds) | Story beat |
|---|---|---|---|
| 1 / 01 | K, M, C | 5.8–10.4 | Duke discovers betrayal in the rainy pool |
| 1 / 02 | C | 10.4–14.6 | Pregnancy revelation and conspiracy at the yellow car |
| 1 / 03 | K | 14.6–18.7 | Phone message creates suspicion |
| 1 / 06 | K | 47.9–57.9 | Duke watches the fountain kiss from the balcony |
| 2 / 04 | K | 35.1–45.1 | Lemonella reacts to Duke and Strawberry |
| 2 / 05 | K, M, C | 58.5–68.5 | DNA envelope confrontation |
| 3 / 04 | K | 33.3–41.1 | Shadow Fig returns with evidence of the past |
| 4 / 04 | K, C | 32.0–42.0 | Lemonella reacts to ultrasound; span continues to Shadow Fig |
| 4 / 06 | K, M, C | 61.9–66.1 | Attackers arrive; Duke protects Lemonella |
| 5 / 01 | K | 7.2–10.8 | Banana asks whether he was another mistake |
| 5 / 02 | K | 10.8–20.8 | Duke learns about Shadow Fig |
| 5 / 03 | K | 31.3–41.3 | Lemonella's casino-world past |
| 5 / 06 | K | 69.9–74.6 | Hospital reveal: triplets |

The other 17 clips pass these stored numerical rules only. They have **not** been certified as narratively or visually correct. Conservative terminal-window corrections remove known overrun candidates; no exact source duration was measured in this workspace.
