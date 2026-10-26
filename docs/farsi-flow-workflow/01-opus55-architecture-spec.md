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

## 5. Persian RTL typography & pill renderer

**Shaping engine** (`shaping_engine()`, recorded in `qa_report.json → host.shaping_engine`):

| engine | when | how |
|--------|------|-----|
| `reshaper` (preferred) | `arabic_reshaper` + `python-bidi` importable | `get_display(arabic_reshaper.reshape(text))`, Pillow BASIC layout — pixel-identical on Windows / Linux / macOS |
| `raqm` | packages missing, Pillow built with libraqm | logical text passed through, `direction="rtl"` (no double reversal) |
| `none` | neither | renders, but `qa_report` makes the degraded engine visible |

**Font resolution** (`resolve_font`): `--font` → manifest `font_path` → `$FARSI_FLOW_FONT` →
the Windows Vazirmatn path → Linux/macOS/Windows system fonts (Vazirmatn, Noto Sans/Naskh Arabic,
DejaVu, Geeza Pro, Tahoma, Arial). Each candidate must contain the Persian glyphs the subtitles
need (alef, Farsi yeh U+06CC, plus noon-medial and keheh presentation forms for the reshaper
engine) via fontTools when installed. A missing preferred font is a **warning**, never a silent
substitution; the chosen font path and its SHA-256 go into `qa_report.json`.

**Fit** (`fit_text`): start at `font_size` (27; badge 28), step down 2 pt to `min_font_size` (16)
until `text_width ≤ frame_w − max_text_margin` (720 − 84 = 636 px). If a single line still
overflows at 16 pt and `max_lines ≥ 2`, balance-wrap at the word boundary that best equalises the
halves and retry from 27 pt. `fits_width=false` fails the `pill_layout` gate.

**Draw** (`draw_rtl_pill`): rounded rectangle radius 16, fill `(12,14,22,210)`, 2 px gold outline
`(255,215,80,220)`, Gaussian-blurred drop shadow, text shadow `(0,0,0,230)` at +2/+2, text in the
speaker's `voices[*].color` (CTA default `(255,230,150)`), centred with `anchor="mm"`. Padding 22×12,
pill clamped to `[16, w−16]`. Subtitles sit at `y = 0.84·H` (1075 px); the Episode Badge at
`y_center = 130` for `0.0–3.5 s` on `badge.clip_index` (clip 1) only.

**Composite**: each pill is rendered once to a cropped transparent PNG (`render_pill_png`) and
placed by ffmpeg `overlay=x:y:enable='between(t,start,end)'`. No per-frame Python loop, no OpenCV,
no colour-space round-trip, and the video never leaves ffmpeg — which is what keeps audio attached.

## 6. Outputs, naming and idempotency

Per episode, in `out_dir` (Windows manifests: `…\05_final_masters`):

| File | Content |
|------|---------|
| `clips_subbed/clip_XX_subbed.mp4` (+ copy in `clips_dir`) | one clip: burned pills (+badge on clip 1) **and its own normalised Flow audio** |
| `clips_subbed/clip_XX_subbed.srt` | that clip's cues, clip-local time, UTF-8 BOM |
| `Base_<ep>_Flow_Native_Farsi.mp4` / `.srt` | immutable story-only master |
| `Master_<ep>_Flow_Native_Farsi.mp4` / `.srt` | Base + exactly one CTA (or byte copy of Base) |
| `Master_<ep>_Flow_Native_Farsi_audit.mp3` | 128 k MP3 of the Master audio for listening QA |
| `qa_<ep>_contact.jpg` | grid: badge midpoint, every cue midpoint, every CTA cue midpoint, labelled `t + speaker` |
| `qa_report.json` (`qa_report_<cmd>.json` for partial runs) | §7 |
| `_work/<ep>/` | spliced sources, normalised clips + PCM sidecars, pill PNGs, normalised CTA |
| `*.build.json` | build record next to every product: cache key, SHA-256, inputs |

**Caching.** Every stage writes `<output>.build.json` with a fingerprint of its exact inputs
(source SHA-256, trims, cues, style, video/audio settings, pipeline version). A stage is skipped
only when the output exists, is non-empty, and the key matches; `--force` ignores the cache.
Change a cue → only that clip's pills, subbed clip, Base and Master rebuild.

**Immutability & promotion.** Sources in `clips_dir` are read-only to the pipeline (the only
writes there are the `clip_XX_subbed.*` mirrors). Every product is written to `*.tmp.*`, probed
by `av_checks`, then `os.replace`d (`promote`); a failed render leaves the previous good file
in place.

**CTA idempotency.** `Master` is always rebuilt *from Base*, never from a previous Master. Its key
is `sha256(Base) + sha256(CTA) + sha256(normalised CTA) + settings`, and its build record stores
`cta_count: 1`. Re-running with identical inputs is a no-op (smoke test: 4.4 s, Master SHA-256
unchanged, one Kelidbox cue). `--no-cta` or a missing `cta_video` makes Master a byte copy of Base
(SHA-256 identical) with a warning. `normalize_cta` frame-quantises the CTA to 720×1280@24 and
48 kHz stereo; it does **not** re-burn subtitles or re-loudnorm the already-finished
`cta_kelidbox_agnes_subbed.mp4` unless `outputs.cta_burn_subtitles` / `cta_loudnorm` are set.
The Master `.srt` appends `cta_subtitles` at `+Base duration`.

**Base modes.** `timeline` (default): concat the normalised clips and overlay every pill at its
global offset — one encode generation from the 14-CRF intermediates. `concat_subbed`: concat the
already-burned `clip_XX_subbed.mp4` videos (one extra generation, byte-for-byte the same pixels as
the per-clip deliverables). Audio in both modes is the sample-exact concatenation of the per-clip
PCM sidecars, i.e. *exactly* the samples inside each `clip_XX_subbed.mp4`, encoded to AAC once.

## 7. QA certification (`qa_report.json`)

Top level: `pipeline_version`, `command`, `generated_utc`, `host` (python, platform, shaping
engine, raqm), `manifest {path, sha256}`, `font {path, sha256}`, `settings`, `clips[]`, `base`,
`master`, `deliverables`, `gates`, `overall_automatic`, `warnings`, `note`.

Per clip: `provenance` (mode `direct | spliced | pre_spliced_file`, source path + SHA-256, splice
segments), `speech` (full analyzer report), `plan` (requested vs final trim, shift, notes),
`final_window_speech`, `duration`, `frames`, `subtitles[]` (authored vs local time, `in_bounds`,
`overlaps_previous`, `speech_energy_ratio`), `overlays[]` (box, font size, lines, `fits_width`,
`inside_frame`), `media` (ffprobe checks), `mirror_sha256_match`.

| Automatic gate | Passes when |
|----------------|-------------|
| `per_clip_media` | every `clip_XX_subbed.mp4`: h264 720×1280 @ 24, aac 48 kHz stereo, `|v−a| < 0.15 s`, duration within 1.5 frames of plan |
| `subtitle_bounds` | every cue inside its clip, no overlap with the previous cue |
| `pill_layout` | every pill fits `W − 84` and lies inside the frame |
| `speech_safe_trim` | no final window starts/ends inside speech or drops speech energy |
| `base_media` / `master_media` | same ffprobe checks + expected duration |
| `master_single_cta` | `Master − Base − CTA` within 1.5 frames (exactly one CTA) |

`overall_automatic` is `pass` only if every automatic gate passes. The **human_review** block
(`listen_every_clip_edges`, `listen_final_master`, `transcript_word_for_word`,
`visual_frame_review`, `voice_continuity`) is always written as `pending`; the pipeline never
claims a listening pass it did not perform (Gate 3 / Gate 4 of the skill).

## 8. CLI reference

```
python pipeline/farsi_flow_workflow.py [--ffmpeg BIN] [--ffprobe BIN] [-v] <command> …

build           MANIFEST [--var K=V]… [--clips-dir D] [--out-dir D] [--font TTF]
                [--speech-safe auto_expand|warn|off] [--cta-video MP4] [--no-cta]
                [--force] [--no-contact]
speech-audit    MANIFEST [same path/speech options] [--only ids] [--json]
sub-clips-only  MANIFEST [same path/speech options] [--only clip_01,3] [--force]
clipboard-image IMAGE [--allow-any-ratio] [--dry-run]
clipboard-prompt [KEY] [--prompts JSON] [--list] [--print] [--dry-run]
```

Exit codes: `0` success · `1` `PipelineError` (bad manifest, missing source, failed render or
verification, non-9:16 keyframe) · `2` usage (argparse, or `clipboard-prompt` with no key).

Typical runs

```bash
# Windows, paths exactly as in the manifest
python pipeline\farsi_flow_workflow.py build pipeline\manifests\series1_part1_whats_her_number.json

# Linux/macOS with the same manifest
python pipeline/farsi_flow_workflow.py build pipeline/manifests/ugly_chef_part2.json \
    --var CHEF_BASE=/data/ugly-face-chef-farsi

# "give me each Flow clip with its original audio, just add subtitles"
python pipeline/farsi_flow_workflow.py sub-clips-only pipeline/manifests/series1_part1_whats_her_number.json

# check trims against speech before rendering anything
python pipeline/farsi_flow_workflow.py speech-audit pipeline/manifests/ugly_chef_part2.json --speech-safe warn
```

**Clipboard helpers** (Gate 2 / Workflow B step 1). `clipboard-image` fully decodes the keyframe,
requires 9:16 (±2 %), logs its SHA-256, then copies it via Windows Forms `Clipboard.SetImage`
(STA PowerShell) / macOS `osascript` PNGf / `wl-copy` / `xclip`. `clipboard-prompt` reads
`pipeline/prompts/ugly_chef_flow_prompts.json` (6 scene prompts, verbatim from
`set_flow_clipboard.py`, plus scene/speaker/location-sheet metadata) and copies via `clip.exe`
(UTF-16LE + BOM) / `pbcopy` / `wl-copy` / `xclip` / `xsel`. `--dry-run` verifies and reports
without touching the clipboard and succeeds on headless hosts.

## 9. Verification performed in Stage 1

Environment: Python 3.12.3, ffmpeg 6.1.1, Pillow (raqm present, reshaper engine used),
arabic-reshaper 3.0.1, python-bidi 0.6.12, Noto Sans Arabic Bold (Vazirmatn not installed on the
build host → warning recorded, as designed).

Synthetic media: six 1080×1920 @ 30 fps `testsrc2` clips with 44.1 kHz mono tone-burst "speech",
`clip_03_raw_orig.mp4` for the splice, an 8 s CTA, a 720×1280 keyframe.

| Check | Result |
|-------|--------|
| `speech-audit` Series 1 | 6/6 clips analysed; `auto_expand` widened 5 edges; `--speech-safe warn` kept the curated `clip_02` window and flagged `CUTS-SPEECH` |
| `build` Series 1 (cold) | 3 m 16 s; 6 × `clip_XX_subbed.mp4` in both locations, Base 52.125 s, Master 60.125 s, all h264 720×1280@24 + aac 48 kHz stereo, A/V durations equal |
| SRT | UTF-8 BOM, 17 cues incl. 2 CTA at `+52.125 s` |
| Contact sheet | 18 tiles (badge, 15 cues, 2 CTA); badge + RTL pills visually correct, joined Persian, speaker colours |
| `qa_report.json` | `overall_automatic = pass`, human gates `pending` |
| Re-run, same inputs | 4.4 s, Master SHA-256 unchanged, exactly one Kelidbox cue |
| `--no-cta` | Master SHA-256 == Base SHA-256, no CTA cues |
| `sub-clips-only --only 1,3` on `ugly_chef_part2` | pass |
| `clipboard-prompt --list / --dry-run`, `clipboard-image --dry-run` | exit 0; landscape keyframe rejected with exit 1 |
| Manifests vs reference scripts | trims, cues, speakers, Persian text, CTA subs verbatim (ast-checked) |

Bug found and fixed during the smoke test: adaptive speech threshold could exceed the clip's peak
on dense dialogue (commit `aa196bb`, §4).

## 10. Known limits & hand-off to later stages

- **Amplitude ≠ intelligibility.** RMS detection cannot tell a finished sentence from a cut one,
  and music/SFX beds can read as speech. Real Flow clips still need the listening gates; an ASR /
  VAD pass (e.g. Whisper word timestamps) is the natural Stage 2+ upgrade to `analyze_clip_speech`.
- **Source defects are not repairable here.** If Flow itself starts/ends mid-word the clip is
  flagged (`pre/post-handle only …`) but must be regenerated (bounded retry, Workflow B step 1).
- **Fonts.** Install `Vazirmatn-Bold.ttf` or pass `--font`; fallbacks render correctly but differ
  stylistically from the published series.
- **CTA asset is trusted as finished.** Its loudness/subtitles are only touched when
  `cta_loudnorm` / `cta_burn_subtitles` are set.
- **Tests.** `tests/test_farsi_flow_workflow.py` (pytest, required by `00-context…` §1) is not
  part of Stage 1; `pipeline/tools/synth_fixtures.py` provides manifest-driven fixtures with known
  ground truth (`fixtures.json`, `--leak-in`, `--fps`) for it.
- Real Windows paths in the manifests were **not** exercised (no access to the author's machine);
  path remapping was exercised via `--var` on Linux.
