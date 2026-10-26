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

## 3. Manifest schema (`schema_version: 1`)

```jsonc
{
  "episode_id": "Series1_Part1",            // [A-Za-z0-9_-]+ → Base_/Master_<episode_id>_Flow_Native_Farsi
  "title_fa": "قسمت اول: عدد سرنوشت",
  "variables": {"BASE": "C:\\…\\series1-whats-her-number-farsi"},   // ${VAR}; --var / env override
  "clips_dir": "${BASE}\\03_flow_clips\\part1",
  "out_dir":   "${BASE}\\05_final_masters",
  "font_path": "${CHEF_BASE}\\03_farsi_audio_tts\\Vazirmatn-Bold.ttf",
  "cta_video": "${CHEF_BASE}\\05_final_masters\\cta_kelidbox_agnes_subbed.mp4",
  "cta_speaker": "ELLA",
  "cta_subtitles": [{"start": 0.10, "end": 3.60, "text": "…"}],      // CTA-local seconds
  "video":  {"width": 720, "height": 1280, "fps": 24, "crf": 18, "preset": "fast",
             "work_crf": 14, "scale_mode": "fill|fit|stretch"},
  "audio":  {"loudnorm": "loudnorm=I=-14:TP=-1.5:LRA=11", "sample_rate": 48000,
             "channels": 2, "bitrate": "192k", "audit_bitrate": "128k"},
  "speech": {"speech_safe": "auto_expand|warn|off|true|false", "threshold_dbfs": -38.0,
             "noise_margin_db": 10.0, "peak_margin_db": 12.0, "frame_ms": 20,
             "min_speech_ms": 60, "merge_gap_ms": 250,
             "pre_handle": 0.20, "post_handle": 0.35, "splice_crossfade": 0.02},
  "subtitle_style": {"time_base": "trim_local|source", "y_ratio": 0.84, "font_size": 27,
                     "min_font_size": 16, "max_text_margin": 84, "max_lines": 2},
  "badge":  {"text": "…", "start": 0.0, "end": 3.5, "y_center": 130, "font_size": 28,
             "color": [255, 225, 110], "clip_index": 1},
  "outputs": {"per_clip_location": "both|clips_dir|out_dir",
              "base_mode": "timeline|concat_subbed",
              "cta_burn_subtitles": false, "cta_loudnorm": false},
  "voices": {"ELLA": {"name_fa": "الا", "color": [130, 255, 220], "source": "google_flow_native"}},
  "clips": [{
      "id": "clip_03", "file": "clip_03.mp4",
      "raw_orig_file": "clip_03_raw_orig.mp4", "splice_segments": [[0.0, 5.22], [6.14, 8.60]],
      "trim_in": 0.50, "trim_out": 7.50,            // seconds on the (spliced) source
      "speech_safe": "auto_expand", "lock_trim": false,
      "subtitles": [[0.60, 3.00, "LIAM", "سلام! تو دختر جدیده‌ای، درسته؟"]]   // or {start,end,speaker,text}
  }]
}
```

Validation (`load_manifest`, fails fast with `PipelineError`, exit 1):
`0 ≤ trim_in < trim_out`; `0 ≤ start < end` for every cue; non-empty text; every speaker declared in
`voices`; `splice_segments` ascending and non-overlapping; unique clip ids; known enum values.
Unknown keys (`_comment`, `continuity`, `bible_tts`, `notes`) are carried through untouched, so the
manifest doubles as the series Character/Continuity bible.

**Path resolution.** `${VAR}` expands from manifest `variables` → `--var NAME=VALUE` → environment
(nested up to 6 levels). On POSIX, backslashes in a remapped path become `/`, so the Windows manifests
run unchanged on Linux with `--var BASE=/data/series1 --var CHEF_BASE=/data/chef`. An unremapped
`C:\…` path on POSIX is kept verbatim (for error messages) and simply reports "not found".
`clips_dir` / `out_dir` / `font` / `cta_video` / `speech_safe` can also be overridden per run.

**Two shipped manifests.**

| | `series1_part1_whats_her_number.json` | `ugly_chef_part2.json` |
|---|---|---|
| episode_id | `Series1_Part1` | `Part2` (keeps legacy `Master_Part2_…` name) |
| clips | 6, `clip_03` re-spliced `[[0,5.22],[6.14,8.60]]` from `clip_03_raw_orig.mp4` | 6, direct |
| cues | 15 story + 2 CTA (ELLA) | 10 story + 2 CTA (AGNES) |
| badge | `قسمت اول: عدد سرنوشت` | `قسمت دوم: سرآشپز زشت` |
| CTA | `cta_kelidbox_agnes_subbed.mp4` (`subs_a`) | same asset (Parts 2–4 use `subs_a`) |
| voices | MOM, DOC, CHLOE, LIAM, ELLA, RUBY | AGNES, MAYA, TONY, HENRY, DOC, HOST, CRITIC |

Every trim, cue time, speaker and Persian line in both manifests was checked **programmatically**
(Python `ast` parse of the reference scripts in `00-context-and-requirements.md`) to be verbatim.

## 4. Speech-safe boundary analyzer

`analyze_clip_speech(mp4, trim_in, trim_out, cfg)`

1. `decode_pcm` — ffmpeg → 16 kHz mono `s16le` → float32.
2. `frame_dbfs` — non-overlapping 20 ms frames, `20·log10(RMS)`.
3. `detect_speech_segments` — threshold
   `thr = max(threshold_dbfs, min(floor + noise_margin_db, −20, peak − peak_margin_db))`
   where `floor` = 10th-percentile frame level. Runs shorter than `min_speech_ms` are dropped, gaps
   shorter than `merge_gap_ms` are merged.
   *The `peak − 12 dB` cap was added after the Stage 1 smoke test*: on dense-dialogue clips
   (speech in > 90 % of frames) the 10th percentile **is** speech, the uncapped threshold sat above
   the peak, and the analyzer reported "no speech" — silently disabling `auto_expand`.
4. Report: `speech_segments`, `first_speech_sec`, `last_speech_sec`, `trim_in/out_inside_speech`,
   `speech_dropped_before_in_sec` / `_after_out_sec`, pre/post handles, `cuts_speech`, noise floor,
   threshold, peak.

`plan_trim(clip, analysis, src_dur, cfg)`

| mode | behaviour |
|------|-----------|
| `auto_expand` (default, `true`) | `trim_in = min(trim_in, max(0, first − 0.20))`, `trim_out = max(trim_out, min(src_dur, last + 0.35))` — **only ever widens**; notes when a handle is shorter than requested because the source itself is tight |
| `warn` | keeps the curated window, records `WARNING: curated trim cuts speech energy` |
| `off` (`false`) / `lock_trim: true` | verbatim window, diagnostics still recorded |

`trim_out > src_dur` is clamped with a note. Because cues are authored trim-local, widening
`trim_in` by `d` shifts every cue by `+d` (`subtitle_shift`), so text stays on the same words.
After the plan, `window_speech_check` re-evaluates the **final** window; that drives the
`speech_safe_trim` QA gate.

Amplitude evidence locates candidates; it does not prove a sentence finished. The report says so
and the listening gates stay `pending` until a human/audio-capable reviewer signs off.
