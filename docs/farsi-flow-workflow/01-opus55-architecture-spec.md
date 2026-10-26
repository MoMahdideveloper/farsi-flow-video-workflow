# 01 · Farsi Google Flow Viral Series Workflow — Architecture Spec (Stage 1)

Author: Stage 1 (Principal Video Pipeline Architect & Core Builder) · Pipeline version `1.0.0`
Status: **implemented, pushed to `main`, smoke-tested end-to-end on synthetic media.**
Human/audio review of real Flow footage is still **pending** (see §9).

Deliverables in this stage

| Path | What it is |
|------|------------|
| `pipeline/farsi_flow_workflow.py` | Self-contained Python 3.10+ CLI: `build`, `speech-audit`, `sub-clips-only`, `clipboard-image`, `clipboard-prompt` |
| `pipeline/manifests/series1_part1_whats_her_number.json` | Series 1 Part 1 *What's Her Number?* (6 clips, `clip_03` re-splice, ELLA Kelidbox CTA) |
| `pipeline/manifests/ugly_chef_part2.json` | *The Ugly Face Chef* Part 2 (6 clips, 7-voice series bible, AGNES Kelidbox CTA) |
| `pipeline/prompts/ugly_chef_flow_prompts.json` | Google Flow scene-prompt library used by `clipboard-prompt` |
| `pipeline/tools/synth_fixtures.py` | Manifest-driven synthetic Flow sources for CI / smoke tests |
| `docs/farsi-flow-workflow/TRACE.md` | Append-only build log, one line per pushed commit |

## 1. Problems this replaces (from conversation `07b71ed0`)

| # | Legacy failure | Root cause | Fix in this pipeline |
|---|----------------|-----------|----------------------|
| 1 | `subbed_s1_p1.mp4` had **no audio** | `cv2.VideoWriter` writes video only; audio re-muxed late from a different file | No OpenCV. Pills are PNGs composited by ffmpeg `overlay`; every subbed clip **stream-copies its own normalised Flow audio** (`-map 0:a:0 -c:a copy`) |
| 2 | No per-clip subtitled deliverable | Scripts only produced `trim720_XX.mp4` (no subs) and one concatenated master | `clip_XX_subbed.mp4` + `clip_XX_subbed.srt` for every clip, mirrored to `clips_dir` **and** `out_dir/clips_subbed/` |
| 3 | Words cut mid-syllable | Hand-typed `trim_in/trim_out`, generic settle trims, no acoustic check | `analyze_clip_speech()` + `plan_trim()` (`auto_expand` / `warn` / `off`, `lock_trim`) with 0.20 s / 0.35 s handles |
| 4 | `clip_03` overwritten in place by its own re-splice | `ffmpeg ... clip_03_raw_orig.mp4 -> clip_03.mp4` | Splice written to `_work/<ep>/clip_03_spliced.mov`; **sources are never written** |
| 5 | CTA appended twice on re-run / base inferred by renaming Master | `os.replace(master, base_backup)` + unconditional concat | Immutable `Base_…mp4`; `Master` keyed on `sha256(Base)+sha256(CTA)`; temp → verify → promote |
| 6 | Persian glyphs broken on Windows Pillow | No libraqm | `arabic_reshaper` + `python-bidi` when present, raqm fallback, font glyph check |
| 7 | Silent "pass" claims | No QA record | `qa_report.json`: automatic gates pass/fail, human gates `pending`, all hashes |

## 2. End-to-end data flow

```
 manifest.json ──load_manifest()──► Episode (validated, ${VAR}s resolved, CLI overrides applied)
                                        │
   for each clip ───────────────────────┤
   ┌────────────────────────────────────┴───────────────────────────────────────────┐
   │ prepare_source()   raw_orig + splice_segments ─► _work/clip_XX_spliced.mov      │
   │                    (acrossfade d=0.02 tri/tri, frame-quantised, PCM audio)     │
   │ analyze_clip_speech()  16 kHz mono PCM → 20 ms RMS dBFS → speech segments      │
   │ plan_trim()        requested [in,out] → final [in,out] + subtitle_shift         │
   │ normalize_clip()   trim → 720x1280 fill-crop @24 → loudnorm -14 LUFS            │
   │                    → 48 kHz stereo: AAC-192k MP4  +  PCM WAV sidecar (same     │
   │                    samples)                                                     │
   │ local_cues()       manifest cues → clip-local time + bounds/overlap/energy     │
   │ build_overlays()   RTL pill PNGs (badge on clip_01 0.0–3.5 s @ y=130)           │
   │ render_subbed_clip() overlay PNGs, -map 0:a:0 -c:a copy ─► clip_XX_subbed.mp4  │
   └────────────────────────────────────┬───────────────────────────────────────────┘
                                        ▼
 assemble_base()   video: concat normalised clips + every pill at global offset
                   audio: sample-exact concat of the PCM sidecars, ONE AAC encode
                   ─► Base_<ep>_Flow_Native_Farsi.mp4 / .srt   (immutable, story only)
                                        ▼
 assemble_master() cta present & !--no-cta: Base + normalize_cta(cta) (exactly one)
                   else: byte copy of Base
                   ─► Master_<ep>_Flow_Native_Farsi.mp4 / .srt (+cta_subtitles)
                                        ▼
 write_audit_mp3() · write_contact_sheet() · write_qa_report()
```

One explicit timeline is used for video, audio and subtitles; `-shortest` is never used to hide a
mismatch. Every duration is frame-quantised (`frame_quantize`) and the audio is padded/trimmed to the
exact sample count of the video (`apad,atrim=end_sample=N`), so `|v_dur − a_dur|` is 0 by construction
and the 0.15 s gate is a safety net, not a tolerance budget.
