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

## 4. Corrections made and keyframe policy

The earlier [Stage 2 trace](TRACE.md) records the substantive repairs already present at handoff: strict evidence validation, complete per-clip traces, honest planned-versus-verified resolution, source bounds and stream validation, strict narrative configuration, isolated episode outputs, safe paste retries and a corrected Series 1 synthetic fixture.

This continuation added **12 regression cases** in [commit 14bd1aeb54c9](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/commit/14bd1aeb54c934bd9653963d93599ac82044d440). One exposed a real remaining error: when visual evidence was absent, `plan_clip` formatted `visual['flags']` despite `visual` being `None`. [Fix 607967ed9d08](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/commit/607967ed9d08d2f01d320e2e8f4f22b24225e2e4) preserves an explicit `VISUAL_EVIDENCE_MISSING` diagnostic through to failing QA. It does not waive the missing-evidence gate. All 66 Stage 2-focused cases then passed, followed by both complete suite runs.

**No keyframe-defacing filter was added or executed.** A tracked-code search and Python AST regression find no executable definition or call of the forbidden Part 3 sanitizer. Synthetic tests verify byte-identical input keyframes after visual analysis, fallback and build. The [runtime pipeline](../../pipeline/farsi_flow_workflow.py) opens/hashes/downscales keyframes in memory for comparison; it does not rewrite them. Source-video subtitle-band interpolation is a separate operation.

Do not confuse this with a claim that the entire repository contains no drawing code: Persian subtitle canvases have existing rounded-pill/shadow rendering, and contact-sheet thumbnails have labels. The archived [keyframe extraction evidence script](series2_scripts/05_extract_clean_episode_kfs.py) also performs OpenCV subtitle-band cleanup **before saving extracted keyframes**. It was neither executed nor changed here and is **not certified for an untouched-source-keyframe workflow**. Do not run that historical extractor under the current untouched-keyframe requirement. Existing production keyframe identity and 9:16 dimensions must be verified on the media host.

## 5. Why production sign-off is still withheld

1. **Assets are not on this host.** The five manifests reference Windows-host source MP4s, production Flow clips and original keyframes. Those paths are unavailable here. Historical audit images, including a separate Part 3 keyframe archive, are not the full current production media set. No actual episode was rebuilt; no generation credits were spent.
2. **The probe and rendered evidence are not proven to describe the same versions.** In the inspected [Part 3 master contact sheet](contact_sheets/flow_6clip_master_part3.jpg), the 44.84-second frame is a human-like blonde character and the 54.84-second frame is eggplant-like. The corresponding [extracted-keyframe sheet](contact_sheets/extracted_6kfs_part3.jpg) shows a lemon-headed character and the distinct fig character. Yet stored Part 3 clips 05 and 06 pass the numerical probe. This is a provenance/semantic discrepancy, not permission to invent failure flags or alter the original measurements. Re-probe the exact files used for the final master and record their hashes. Inspect the additional concerns in the [problem brief](00-problem-statement-and-evidence.md), including Part 4 clip 03 and Part 5 clip 04.
3. **Similarity is not story comprehension.** RGB L1 at 2 fps cannot prove character identity, catch every short cut, detect every human-face substitution or confirm that a phone/DNA/ultrasound insert is present. A passing metadata story beat checks declarations, not pixels or cause-and-effect coverage. The 13 flagged clips are the exact stored metric failures, not a guaranteed exhaustive list of broken production clips.
4. **Recovery windows are candidates.** Validate actual MP4 bounds, source cut points, depicted characters and dialogue fit. Short source spans are extended with held frames; this preserves the audio timeline but can look frozen. Source replacement is not guaranteed lip-sync. Subtitle-band interpolation can affect bright non-text detail and needs visual review.
5. **The full narrative-edit modes remain unimplemented.** The loader has no implemented `bridge_clips` / `segment_type` edit list and no `video_source_mode: original_inpainted_with_flow_audio` timeline assembly. The implemented feature is per-clip automatic fallback, not restoration of all 16–22 source shots. Do not assume adding those keys enables a mode. Restoring missing bridge shots requires a separate edit implementation or an explicitly reviewed edit outside this pipeline.
6. **Live submission is unverified.** The chip counter is a snapshot-marker heuristic, currently scanning snapshot frames rather than a proven live composer boundary. Offline state-machine tests establish its guard behavior, not current Google Flow UI compatibility or attachment identity. Verify those on the target host before a paid batch; preserve actual submission receipts and keyframe hashes.
7. **Human publication gates remain pending.** Listen to every dialogue edge and final master, check the Persian transcript and speaker voices, inspect subtitles/inpainting and confirm visual story beats. `all_passed` on a rendered QA report covers automatic checks only; it must not authorize publication by itself.

## 6. Reproduction and host acceptance checklist

The commands below were executed here with `python3` because this Linux host has no `python` alias. On the Windows media host, use the installed Python command with equivalent arguments. Commands are repo-root relative.

```bash
pytest tests/test_farsi_flow_workflow.py -v
# 114 passed in 190.86s

# Bash: preserve pytest's exit status instead of tee's status.
set -o pipefail
pytest -v 2>&1 | tee docs/series2-meaning-and-pipeline-solution/02-astra-pytest-results.txt
# 203 passed in 191.59s

python3 pipeline/farsi_flow_workflow.py trace-all-parts \
  --probe-json docs/series2-meaning-and-pipeline-solution/parts1_to_5_clips_probe.json \
  --out-json docs/series2-meaning-and-pipeline-solution/trace_parts1_to_5_audit.json
# Exit 0 = complete diagnostic audit; not successful production rendering.

node --check scripts/submit_flow_batch.mjs
node --test tests/js/submit_flow_batch.test.mjs
# 13 passed; offline fixtures only.
```

Before any of Parts 1–5 can be approved for publication:

- [ ] Resolve the manifest asset paths on the media host; preserve originals; hash all actual source, Flow and keyframe inputs. Confirm every keyframe is untouched and 9:16.
- [ ] Measure source durations and review every candidate source window against the actual scene and dialogue. Confirm no long frozen holds hide missing action.
- [ ] Run live visual and acoustic audits against the actual input versions. Resolve the contact-sheet/probe discrepancy and review *all 30 clips*, not only the 13 numeric failures.
- [ ] If resubmitting, validate the live empty-composer and single-keyframe states first. Capture durable submission traces and match attachment hashes; never silently use text-only generation.
- [ ] Build each part with its own output directory. Require exit 0, complete six-stage media QA, verified fallback extraction where used, valid A/V timing and no clipped speech. A nonzero build can leave diagnostic output: do not publish it.
- [ ] Restore missing causal bridge shots or implement and validate the deferred full-source edit mode; review the entire episode against the caption and story summary.
- [ ] Complete and record the human-review gates. Only then approve a final master for publication.

### Evidence integrity

| File | SHA-256 at verification |
|---|---|
| [Pipeline](../../pipeline/farsi_flow_workflow.py) | `8267441b43b21a48633220c4eede6c7c4e2216f70e9cd491ddf1bb985b759c66` |
| [Submitter](../../scripts/submit_flow_batch.mjs) | `87dbfaf5ba29176fc7dd111b52702d447a63111c1e6de8559c924e8e2c1dad86` |
| [Workflow tests](../../tests/test_farsi_flow_workflow.py) | `7e8c25f660f1a06a3d9f78f8126b40d0b32c3551cdb143a317bb2975e57a12b0` |
| [Original probe](parts1_to_5_clips_probe.json) | `c6b3c0ec957f6f96d3711a9f5a5940c651a14c2a711f508080fb39785f3a7a61` |
| [Regenerated audit](trace_parts1_to_5_audit.json) | `599fb0c6973c5d4d2a9ec07abc9dc6346df20bcfe979b0b43c00cb18ba860c94` |
| [Full pytest log](02-astra-pytest-results.txt) | `0ad086e9dc70275bd76a59a53272a795657fe1ec5ea280141d952fd790ca63b8` |

**Final disposition:** the implemented engineering contracts pass the recorded tests and the diagnostic audit is complete. The five production videos are **not signed off**. The blockers above cannot honestly be cleared with probe JSON and synthetic media alone.
