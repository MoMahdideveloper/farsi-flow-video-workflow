# 02 · Stage 2 — Verified implementation and pytest audit

**Pipeline version:** 1.1.1 · **Verification date:** 2026-10-26 UTC.

**Scope:** engineering and automated-media verification, not publication approval of the real episode. The real Windows Google Flow assets were not available on this Linux runner. A passing acoustic-energy check cannot certify that a Persian word or sentence finished. The listening, transcript, voice-continuity and visual-review gates remain **pending**.

## 1. Inputs and audit scope

Reviewed the complete [requirements and reference scripts](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/blob/main/docs/farsi-flow-workflow/00-context-and-requirements.md), [Stage 1 architecture](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/blob/main/docs/farsi-flow-workflow/01-opus55-architecture-spec.md), [trace](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/blob/main/docs/farsi-flow-workflow/TRACE.md), [implementation](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/blob/main/pipeline/farsi_flow_workflow.py), [Series 1 manifest](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/blob/main/pipeline/manifests/series1_part1_whats_her_number.json), [Ugly Chef manifest](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/blob/main/pipeline/manifests/ugly_chef_part2.json), and [pytest suite](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/blob/main/tests/test_farsi_flow_workflow.py).

All 96 function/method/nested-helper definitions in the final implementation were inspected. The inventory below records their names; this is **not** a claim of 100% line/branch coverage.

The Stage 1 architecture is historical: this report supersedes its descriptions of trim clamping, missing-shaper fallback, cache checking, and Stage 2 test availability.

## 2. Hardened implementation

Previously pushed Stage 2 work, retained and reverified:

- Input/schema/enum/finite-number validation and output/source collision prevention.
- `build --manifest` support while preserving the positional CLI form.
- Source hashes and primary/PCM-sidecar cache hashes; corrupted outputs rebuild.
- Exact requested audio trim endpoints followed by **tail-only** padding to whole video frames. No requested tail audio is rounded away.
- Explicit original-audio mapping into every subtitled clip; no TTS replacement.
- Frame/sample-duration, stream-presence, start alignment and audio packet-continuity gates.
- Temporary per-clip, Base and Master MP4 verification before replacement of good MP4s.
- Explicit `overall_status` and `overall_status_scope="automatic_checks_only"`; CLI exit 1 on failed QA.
- Honest separation of automatic QA and pending human/audio-capable review.

Additional defects found and fixed during this resumed audit:

| Defect | Correction | Verification |
|---|---|---|
| Raw splice audit inspected internal joins but omitted the first and last retained endpoints | Audit every segment start/end; internal edges also include the 20 ms crossfade neighborhood | Outer head/tail unit cases plus a real ffmpeg tail-cut fixture that fails the CLI and QA gate |
| Out-points beyond source duration were silently clamped, changing a curated window while allowing a pass | Reject the invalid source/window instead of shortening it, for all speech modes | Three mode-specific regressions; fallback fixture now genuinely covers the 7.50 s endpoint |
| Input stream offsets could be erased by timestamp resets, hiding an original A/V alignment problem | Validate source streams, durations and start times **before** direct trimming and raw-original splicing | Six direct/splice offset regressions |

Fix commits: [outer boundaries and strict trims](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/commit/3299a763c1987a72b55ce4118fc0f7af759d1291), [pre-splice source timing guard](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/commit/5703f45cbaf48a30b64c93e0623cede971edf9a7), [13 additional regression cases](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/commit/93202211ad94a8f0be015c8fa56be82c0de20c2b).

## 3. Exact Series 1 behavior

The [Series 1 manifest](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/blob/main/pipeline/manifests/series1_part1_whats_her_number.json) still points to the requested Windows clips directory:

```text
C:\Users\LifeCycle\.gemini\antigravity\scratch\series1-whats-her-number-farsi\03_flow_clips\part1
```

Its six curated windows are unchanged:

| Clip | Requested in | Requested out | Rendered duration at 24 fps |
|---|---:|---:|---:|
| 01 | 0.00 | 9.40 | 9.4167 s |
| 02 | 0.50 | 8.90 | 8.4167 s |
| 03 | 0.50 | 7.50 | 7.0000 s |
| 04 | 0.60 | 9.40 | 8.8333 s |
| 05 | 1.10 | 9.80 | 8.7083 s |
| 06 | 0.40 | 8.40 | 8.0000 s |

Rendered durations round **up**, using a cloned final video frame and silence only after the exact retained audio interval. The total story duration is 50.375 s; an 8.000 s CTA produces 58.375 s.

- If the exact raw-original asset exists, keep `[0.0, 5.22] + [6.14, 8.60]` and use `acrossfade=d=0.02:c1=tri:c2=tri`. The work product is separate; neither original asset is overwritten.
- If that asset is absent, use the existing clip 03 as the pre-spliced source, without applying the splice again. Its duration must cover the requested 7.50 s out-point; otherwise fail clearly.
- The raw splice is 185 video frames at 24 fps. Audio overlap is 0.02 s and is explicitly reported. Final padding is not evidence of sentence completion.
- Every numbered subtitled clip is produced in **both** the source clips directory and the output directory's subtitled-clips folder. Both copies contain h264 portrait video with burned Persian text and the original Flow-derived, loudness-normalized AAC audio at 48 kHz stereo.
- Base is always story-only. Master is built from Base plus exactly one CTA, never by appending to a prior Master. Missing/disabled CTA yields a byte-identical copy of Base.
- Master SRT is UTF-8 with BOM; the Series 1 fixture has 15 story cues plus two CTA cues. Audio-listening MP3, contact JPEG and full QA JSON are also generated.
- `speech_safe: "warn"` is the Series 1 default: exact valid windows are preserved, but detected speech loss makes automatic QA **fail**. `auto_expand` widens the window within source bounds and shifts trim-local subtitles; it does not repair already-missing words or change splice segments.

**There is no honest way to promise both arbitrary unchanged cuts and zero mid-word cuts without inspecting the actual speech.** If warn mode flags a cut, reject publication, review it, and explicitly choose revised trims, auto-expansion, or source regeneration. Do not relabel the failure as a pass.

## 4. Automated test coverage

The suite synthesizes three 720×1280, 24 fps moving-picture MP4s plus a synthetic CTA. Sources contain silent handles and distinct modulated harmonic bursts; source audio starts as 44.1 kHz mono to exercise conversion to 48 kHz stereo. These signals test timing/provenance, not Persian intelligibility.

A separate end-to-end fixture renders **all six** Series 1 clips using the shipped dialogue, exact trims and raw-original splice. The test substitutes fixture paths, a local Persian font, an ultrafast encoder preset and synthetic CTA text burning; it is not a run on the user's Windows machine.

Coverage includes:

- Both output locations; video/audio codecs, dimensions, rate, channels, durations, packet continuity, and full ffmpeg decode of generated MP4s.
- Decoded audio equality between normalized and subtitled clips, non-silence and distinct source frequencies, and unchanged source hashes.
- Burned subtitle/badge pixels, SRT BOM and cue counts, JPEG decoding and the audio-listening export.
- Unchanged MP4 hashes **and modification times** on repeated builds; exactly one CTA; no-CTA, missing-CTA and restored-CTA transitions.
- Speech start/end accuracy within 60 ms on the known bursts, unsafe warn-mode failure, auto-expansion and subtitle retiming.
- Exact raw splice, removal of unwanted gap audio, non-destructive fallback, corrupted primary/PCM cache detection and rebuild.
- Invalid manifests, source/output collisions, dense-speech thresholding, silence, partial final RMS frames and SRT time rollover.
- Windows-root path mapping and mocked Windows clipboard encoding/STA commands; missing shaping engine rejection.
- Verbatim reference-script dialogue/trim comparison, failed-render promotion protection, and unavailable ffprobe fields.
- The 13 newly added outer-edge, strict source-bound and pre-reset stream-offset regression cases.

