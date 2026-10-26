# Series 2 — Stage 1 (Claude Opus 5.5, medium): pipeline architecture & fix

> Status: Stage 1 complete on `main`. Handoff to Stage 2 (GPT-6 Astra, extra-high).
> Keyframe policy (hard rule): keyframes are **read-only**. They are only hashed (sha256) and compared (L1). Nothing in the pipeline draws on, boxes, blurs or "sanitizes" a keyframe. The only pixels ever inpainted are the English-subtitle band of **source-video frames** used in a fallback bridge.

## 1. Why the published Parts 1–5 "had no meaning"

The audit (`trace_parts1_to_5_audit.json`, generated from `parts1_to_5_clips_probe.json`) points to two causes:

1. **Story compression.** Each 65–77 s original episode has 16–22 cuts, and those cuts carry the cause and effect: the phone text, the dropped roses, the DNA envelope, the ultrasound. They were replaced by 6 static talking heads of about 10 s each, where roughly 3 s is speech and the rest is frozen dead air.
2. **Broken keyframe lock in Flow.** **13 of the 30 clips** don't show the scene they were meant to show:
   - 12 × `KEYFRAME_MISMATCH`: Flow silently fell back to 0-ingredient Text-to-Video and invented characters (human Lemonella, shirtless Duke, Renaissance eggplant).
   - 3 × `MULTI_INGREDIENT_CONTAMINATION`: a leftover chip from another clip was still in the composer.
   - 5 × `INTERNAL_SCENE_CUT`: hard cuts in the middle of a clip.

   A root cause found in `scripts/submit_flow_batch.mjs`: the old `fop_part*` keyframe map reused **other parts'** keyframes. For example, `fop_part5` clip 1 used `part1/KF_05`, `fop_part3` clip 4 used `part1/KF_03`, and `fop_part1` clip 1 used `KF_03`. `fop_part1` also had no clip 6 at all.
3. **No visual gate.** `qa_report.json` checked loudness, speech and subtitles only, so it reported `all_passed: true` on clips that showed the wrong scene.

## 2. Architecture (pipeline v1.2.0)

```
manifest (story_summary_fa, source_video, per-clip keyframe/expected_speakers/story_beat/source_span)
   │
   ├─ step_1_story_beat_and_character_lock   metadata completeness, cue speakers ⊆ expected_speakers,
   │                                          CHARACTER_KEYFRAME_COLLISION (same KF sha, disjoint speakers),
   │                                          voices.name_fa aliases ↔ outputs.publish_caption_fa
   ├─ step_2_keyframe_preflight              9:16 check + sha256; read-only (modified=false)
   ├─ step_3_visual_continuity_audit         analyze_clip_visuals (live MP4, ffmpeg→numpy L1 @2 fps)
   │                                          or evaluate_probe_entry (headless CI from probe JSON)
   ├─ step_4_acoustic_speech_and_pacing      speech RMS bounds; tight_speech_trim; DEAD_AIR_PACING (>3.5 s)
   ├─ step_5_hybrid_bridge_and_fallback      flow_clip | source_bridge_fallback | unresolved_visual_fail
   └─ step_6_mux_and_master_verification     final media probe of the muxed clip / master
        → qa_report.json["step_trace"]  +  trace_<episode_id>.json
```

### 2.1 Visual continuity gate (`evaluate_probe_entry` / `analyze_clip_visuals`)
| Flag | Rule (defaults) |
|---|---|
| `KEYFRAME_MISMATCH` | `l1_vs_keyframe_start > 32.0` **and** `l1_vs_keyframe_mean > 32.0` |
| `MULTI_INGREDIENT_CONTAMINATION` | `closest_other_keyframe_l1_start + 5.0 < l1_vs_keyframe_start` |
| `INTERNAL_SCENE_CUT` | `max_internal_jump_l1 > 32.0`; emits `suggested_visual_trim_in/out` (keeps the longest cut-free run) |

`analyze_clip_visuals(mp4, keyframe_path=…, all_keyframes=…, sample_fps=2.0)` builds the same probe entry from a live MP4: frames are decoded by ffmpeg into small RGB thumbnails and compared by mean absolute difference, with no OpenCV dependency. Live runs and CI therefore use exactly the same rules.

### 2.2 Hybrid source bridge (`extract_source_fallback_clip`)
When `fallback_to_source_on_visual_fail: true` and a clip fails step 3:
- **Video** comes from `source_video[source_span]` (the original straw.berryjammin MP4), with the English subtitle band removed by `inpaint_source_subtitle_band(rgb)` (numpy-only, bright-glyph mask inside the subtitle band, masked pixels rebuilt by row + column linear interpolation).
- **Audio** is the untouched native Google Flow Farsi track of `clip_XX.mp4`, and its sha256 is unchanged.
- The output keeps the Flow clip's exact duration, so the speech-safe / tight trim plan and the Farsi subtitle timing still apply. If the span is shorter than the speech window, its first and last frames are held.

### 2.3 Tight speech pacing (`apply_tight_speech_trim`)
`[max(trim_in, first_speech − pre_handle), min(trim_out, last_speech + post_handle)]`, padded symmetrically to at least **2.2 s**. In the synthetic test a 3-second line went from 7.95 s to 3.55 s. It can be enabled per episode (`tight_speech_trim`) or overridden per clip.

### 2.4 Flow submitter guard (`scripts/submit_flow_batch.mjs`)
- `countIngredientChips(snapshot)`: the composer must have **0** chips before paste and exactly **1** after paste and again right before *Start*. Any other count throws.
- A clip with `kf` never degrades to Text-to-Video. A missing keyframe file throws. Text-to-Video is only possible with an explicit `allowTextOnly: true`.
- Every step is appended to `flow_submission_trace.jsonl` (run id, part, clip, keyframe sha256, chip counts, retries).
- `fop_part1..5` clip N uses `${FOP_DIR}\partX\keyframes\KF_0N.jpg`, and nothing else.

### 2.5 Manifests (`pipeline/manifests/fruits_of_power_part1..5.json`)
Each manifest now carries:
- `source_video` (`${SRC}\<id>.mp4`)
- `story_summary_fa`
- `fallback_to_source_on_visual_fail: true`
- `tight_speech_trim: true`
- `outputs.publish_caption_fa` (the Instagram kit caption)
- per clip: `keyframe`, `expected_speakers`, `story_beat`, and `source_span`. Span starts are the `05_extract_clean_episode_kfs.py` timestamps; each span ends at the next keyframe timestamp or 10 s later, whichever comes first.

Name alignment:
- `PEACH.name_fa = "دکتر گلابی / دکتر هلو"`, so the caption's "دکتر گلابی" matches.
- `FIG` aliases include "رییس مافیا", the wording used in the Part 3 caption.
- The Part 3 and 5 captions don't name Banana, so `BANANA` is listed under `caption_optional_speakers` there.

## 3. 30-clip diagnostic table (Parts 1–5)

Source: `trace-all-parts` on `parts1_to_5_clips_probe.json`. Result: 13/30 clips failed the visual gate, 13 were resolved by source bridge, 0 are unresolved, and all 5 episodes pass `all_passed`.

| Part | Clip | Story beat | kf L1 start / mean | closest other KF (L1) | max jump L1 @ t | Flags | Resolution | source_span |
|---|---|---|---|---|---|---|---|---|
| 1 | clip_01 | Duke screams in the rainy pool: betrayal discovered | 57.73 / 57.18 | clip_04 (35.99) | 51.65 @ 9.0 s | `KEYFRAME_MISMATCH`, `MULTI_INGREDIENT_CONTAMINATION`, `INTERNAL_SCENE_CUT` | **source bridge** + Flow audio | 5.8–10.4 s |
| 1 | clip_02 | Lemonella reveals pregnancy; plots with Banana on the yellow sports car | 9.55 / 39.25 | clip_04 (52.17) | 42.21 @ 0.5 s | `INTERNAL_SCENE_CUT` | **source bridge** + Flow audio | 10.4–14.6 s |
| 1 | clip_03 | Duke reads the phone message 'Last night was wild' and suspects Lemonella | 59.1 / 59.69 | clip_01 (59.85) | 8.23 @ 6.0 s | `KEYFRAME_MISMATCH` | **source bridge** + Flow audio | 14.6–18.7 s |
| 1 | clip_04 | Duke arrives with purple roses and drops them on seeing the kiss | 11.04 / 15.7 | clip_03 (38.84) | 11.1 @ 1.5 s | ✅ pass | Flow clip | — |
| 1 | clip_05 | Banana gloats in the rain: the Duke's fortune is now his | 19.51 / 40.74 | clip_06 (54.1) | 30.61 @ 0.5 s | ✅ pass | Flow clip | — |
| 1 | clip_06 | Duke watches the fountain kiss from the balcony at night and breaks down | 48.89 / 49.34 | clip_03 (54.86) | 10.63 @ 8.0 s | `KEYFRAME_MISMATCH` | **source bridge** + Flow audio | 47.9–57.9 s |
| 2 | clip_01 | Banana celebrates the night out with the Duke's money | 16.14 / 27.32 | clip_03 (51.24) | 26.45 @ 9.0 s | ✅ pass | Flow clip | — |
| 2 | clip_02 | Duke alone in the mansion, burning in loneliness | 5.28 / 8.74 | clip_03 (30.2) | 8.59 @ 5.5 s | ✅ pass | Flow clip | — |
| 2 | clip_03 | Countess Strawberry comforts Duke (the photo that sparks jealousy) | 5.79 / 21.44 | clip_02 (30.13) | 21.67 @ 1.0 s | ✅ pass | Flow clip | — |
| 2 | clip_04 | Lemonella sees Duke with Countess Strawberry and burns with jealousy | 60.2 / 61.81 | clip_01 (65.88) | 17.26 @ 3.5 s | `KEYFRAME_MISMATCH` | **source bridge** + Flow audio | 35.1–45.1 s |
| 2 | clip_05 | The DNA test envelope is opened: Banana asks what it says | 67.86 / 49.77 | clip_06 (12.03) | 62.74 @ 0.5 s | `KEYFRAME_MISMATCH`, `MULTI_INGREDIENT_CONTAMINATION`, `INTERNAL_SCENE_CUT` | **source bridge** + Flow audio | 58.5–68.5 s |
| 2 | clip_06 | Lemonella shocked by the DNA result | 9.76 / 22.91 | clip_03 (53.09) | 19.25 @ 5.5 s | ✅ pass | Flow clip | — |
| 3 | clip_01 | Lemonella: the baby is a boy; wishes the truth were known | 5.49 / 17.97 | clip_05 (51.35) | 13.41 @ 1.0 s | ✅ pass | Flow clip | — |
| 3 | clip_02 | Lemonella confronts Banana with the DNA proof; Banana laughs | 15.25 / 29.23 | clip_06 (39.67) | 17.04 @ 0.5 s | ✅ pass | Flow clip | — |
| 3 | clip_03 | Duke shows Lemonella the gold nursery plan for the heir | 7.38 / 18.66 | clip_04 (44.58) | 13.41 @ 0.5 s | ✅ pass | Flow clip | — |
| 3 | clip_04 | Mafia boss Shadow Fig appears in the rain with Lemonella's past | 45.36 / 45.46 | clip_03 (47.41) | 7.68 @ 7.0 s | `KEYFRAME_MISMATCH` | **source bridge** + Flow audio | 33.3–41.1 s |
| 3 | clip_05 | Lemonella decides to flee before the Duke finds out | 10.95 / 24.43 | clip_06 (44.5) | 17.72 @ 3.5 s | ✅ pass | Flow clip | — |
| 3 | clip_06 | Shadow Fig holds the glass-slipper evidence: the past is exposed | 6.04 / 8.26 | clip_04 (16.51) | 6.32 @ 0.5 s | ✅ pass | Flow clip | — |
| 4 | clip_01 | Lemonella tearfully confesses her betrayal to Duke | 9.24 / 21.2 | clip_03 (40.4) | 17.8 @ 1.0 s | ✅ pass | Flow clip | — |
| 4 | clip_02 | Duke surprises Lemonella with a signed contract | 9.01 / 18.42 | clip_03 (44.61) | 9.85 @ 3.5 s | ✅ pass | Flow clip | — |
| 4 | clip_03 | Countess Strawberry tempts the lonely Duke | 6.71 / 22.68 | clip_01 (42.36) | 25.91 @ 1.0 s | ✅ pass | Flow clip | — |
| 4 | clip_04 | Storm rises over the mansion; Shadow Fig dictates terms | 43.33 / 43.05 | clip_05 (55.17) | 38.16 @ 1.5 s | `KEYFRAME_MISMATCH`, `INTERNAL_SCENE_CUT` | **source bridge** + Flow audio | 32.0–42.0 s |
| 4 | clip_05 | Lemonella vs Countess Strawberry confrontation | 15.15 / 17.19 | clip_03 (43.3) | 18.5 @ 1.5 s | ✅ pass | Flow clip | — |
| 4 | clip_06 | Attackers reach the mansion; Duke shields Lemonella | 56.56 / 54.59 | clip_01 (44.69) | 47.28 @ 9.0 s | `KEYFRAME_MISMATCH`, `MULTI_INGREDIENT_CONTAMINATION`, `INTERNAL_SCENE_CUT` | **source bridge** + Flow audio | 61.9–71.9 s |
| 5 | clip_01 | Banana: was I just another mistake? | 54.69 / 54.02 | clip_05 (59.24) | 25.87 @ 3.0 s | `KEYFRAME_MISMATCH` | **source bridge** + Flow audio | 7.2–10.8 s |
| 5 | clip_02 | Duke learns Lemonella's past with Shadow Fig | 38.66 / 40.68 | clip_04 (46.39) | 21.38 @ 2.5 s | `KEYFRAME_MISMATCH` | **source bridge** + Flow audio | 10.8–20.8 s |
| 5 | clip_03 | Lemonella's dark past in Shadow Fig's casino world | 48.96 / 49.64 | clip_04 (48.71) | 11.64 @ 4.0 s | `KEYFRAME_MISMATCH` | **source bridge** + Flow audio | 31.3–41.3 s |
| 5 | clip_04 | Duke forgives: he doesn't care who loved her before | 5.35 / 11.3 | clip_02 (36.3) | 13.9 @ 8.5 s | ✅ pass | Flow clip | — |
| 5 | clip_05 | Lemonella collapses; Duke calls the emergency services | 8.8 / 18.53 | clip_02 (43.18) | 20.07 @ 2.5 s | ✅ pass | Flow clip | — |
| 5 | clip_06 | Hospital ultrasound: Dr. Pear reveals triplets | 72.32 / 71.28 | clip_05 (91.83) | 9.15 @ 9.5 s | `KEYFRAME_MISMATCH` | **source bridge** + Flow audio | 69.9–79.9 s |

Flag totals: `KEYFRAME_MISMATCH` 12, `MULTI_INGREDIENT_CONTAMINATION` 3, `INTERNAL_SCENE_CUT` 5.

## 4. How to run

```bash
# headless CI (no media needed)
python pipeline/farsi_flow_workflow.py trace-all-parts \
  --probe-json docs/series2-meaning-and-pipeline-solution/parts1_to_5_clips_probe.json \
  --out-json   docs/series2-meaning-and-pipeline-solution/trace_parts1_to_5_audit.json
# one episode, live MP4s on the Windows host
python pipeline/farsi_flow_workflow.py trace-audit --manifest pipeline/manifests/fruits_of_power_part5.json
# full build: failing clips are auto-bridged from source_video, Flow audio kept
python pipeline/farsi_flow_workflow.py build pipeline/manifests/fruits_of_power_part5.json
# re-submit to Flow with the chip gate + JSONL trace
node scripts/submit_flow_batch.mjs --part fop_part5
```

## 5. Handoff to Stage 2 (Astra, extra-high)
1. **Hybrid intercut mode** (`segment_type: flow_clip | source_bridge`): bring back the 10–16 silent bridge cuts per episode (phone screen, rose drop, DNA envelope, attackers, ultrasound) between the tight Flow dialogue windows. The `source_span` plumbing and `extract_source_fallback_clip` can be reused as they are.
2. **Original-video + Flow-audio mode** (`video_source_mode: original_inpainted_with_flow_audio`): place Flow voice lines onto the full original timeline.
3. Re-render Parts 1–5 on the Windows host. Re-submit the 13 failed clips with the guarded submitter first. Where Flow still fails, the source bridge covers it automatically.
4. Calibrate the 32.0 thresholds against live `analyze_clip_visuals` output (the probe used 20 samples per clip).
5. Pre-existing, unrelated: `test_all_six_series1_clips_with_shipped_windows` (Series 1 clip_03 window 7.67 vs 7.5).
