# Farsi Flow Workflow — Build Trace

Append-only log of every Stage commit pushed to `origin main` (newest last).
Format: `- <UTC time> · <file-commit SHA> · <what changed>`

## Stage 1 — Claude Opus 5.5 (Principal Video Pipeline Architect & Core Builder)

Plan:
1. `pipeline/farsi_flow_workflow.py` — config-driven CLI (`build`, `speech-audit`, `sub-clips-only`, `clipboard-image`, `clipboard-prompt`), written in ~150-line chunks.
2. `pipeline/manifests/series1_part1_whats_her_number.json`, `pipeline/manifests/ugly_chef_part2.json`.
3. `pipeline/prompts/ugly_chef_flow_prompts.json` (prompt library for `clipboard-prompt`).
4. Synthetic smoke test (ffmpeg testsrc + tone bursts) of every subcommand.
5. `docs/farsi-flow-workflow/01-opus55-architecture-spec.md`.

Environment probed: Python 3.12.3, ffmpeg 6.1.1 (libx264, aac, libmp3lame), Pillow 13 (raqm present), numpy 2.x,
arabic-reshaper 3.0.1, python-bidi 0.6.12, no OpenCV (pipeline deliberately does not need it).

### Log
- 2026-10-26T12:01Z · `62aa669` · Created TRACE.md with Stage 1 plan + environment probe
- 2026-10-26T12:08Z · `3518b28` · farsi_flow_workflow.py chunk 1/8: module header, defaults, subprocess/ffprobe/sha256/SRT helpers
- 2026-10-26T12:19Z · `b0b8bcd` · farsi_flow_workflow.py chunk 2: Cue/ClipSpec/Episode dataclasses, defaults tables, speech_safe modes (auto_expand|warn|off), ${VAR} path resolution w/ Windows->POSIX remap
- 2026-10-26T12:22Z · `dd8579d` · farsi_flow_workflow.py chunk 3: load_manifest() with CLI overrides, cue/segment/speaker validation, clip source resolution
- 2026-10-26T12:24Z · `80210b0` · farsi_flow_workflow.py chunk 4: analyze_clip_speech() — 16 kHz PCM decode, 20 ms RMS dBFS, adaptive floor + -38 dBFS threshold, speech segments, first/last speech, trim-cuts-speech diagnostics
- 2026-10-26T12:27Z · `a8e08fd` · farsi_flow_workflow.py chunk 5: plan_trim() auto_expand/warn/lock, frame-quantised splice_clip() w/ centred acrossfade=0.02, normalize_clip() 720x1280@24 loudnorm 48k stereo AAC + PCM sidecar (verified on synthetic 10s clip: 184/168 frames, A/V equal)
- 2026-10-26T12:35Z · `21f7c5b` · farsi_flow_workflow.py chunk 6: shape_fa() (reshaper+bidi, raqm fallback), resolve_font() w/ Persian-glyph check (manifest/--font/$FARSI_FLOW_FONT/Windows Vazirmatn/system), fit_text() 27->16pt + 2-line balance wrap, draw_rtl_pill() pill+gold outline+drop shadow, render_pill_png(), build_overlays() incl. badge 0..3.5s @ y=130 (visually verified)
- 2026-10-26T12:38Z · `6f59582` · farsi_flow_workflow.py chunk 7: fingerprint/cache_ok/cache_write build records, prepare_source() (splice raw_orig into _work, never overwrites sources; pre-spliced fallback), window_speech_check(), local_cues() trim_local/source time bases + bounds/overlap/speech-energy checks, overlay_chain(), render_subbed_clip() burns PNG pills and stream-copies the Flow audio (-map 0:a:0 -c:a copy); verified on synthetic clip
- 2026-10-26T12:39Z · `344633a` · farsi_flow_workflow.py chunk 8: ClipResult, plan_clip() (source prep + analysis + trim plan + final-window speech check), render_clip() (cached normalise -> local cues -> pills -> clip_XX_subbed.mp4 + .srt, mirrored to clips_dir and out_dir/clips_subbed per outputs.per_clip_location), run_clips() with --only filter
- 2026-10-26T12:41Z · `2c5a046` · farsi_flow_workflow.py chunk 9: av_checks() ffprobe gate (h264 720x1280@24, aac 48k stereo, drift<0.15s, expected duration), promote() verify-then-replace, assemble_base() timeline|concat_subbed with sample-exact PCM audio concat + single AAC encode, Base .srt, normalize_cta() frame-exact CTA (optional burn/loudnorm, silent-audio fallback)
- 2026-10-26T12:42Z · `c756a8f` · farsi_flow_workflow.py chunk 10: assemble_master() Base + exactly one CTA keyed on sha256(Base)+sha256(CTA), temp->verify->promote, Base byte-copy when CTA missing/--no-cta, Master .srt w/ cta_subtitles; write_audit_mp3(); contact_points() + write_contact_sheet() single-pass frame select grid (badge, every cue midpoint, CTA cues)
- 2026-10-26T12:42Z · `8cfa7d4` · farsi_flow_workflow.py chunk 11: clip_report(), write_qa_report() (ffprobe media gates per clip/Base/Master, subtitle bounds, pill layout, speech-safe trim, single-CTA duration check; human review gates 'pending'; host/font/manifest hashes), build_episode(), sub_clips_only(), speech_audit()
- 2026-10-26T12:43Z · `b093aa2` · farsi_flow_workflow.py chunk 12: verify_keyframe() full decode + 9:16 check + sha256, copy_image_to_clipboard() (Windows Forms SetImage via STA PowerShell / macOS PNGf / wl-copy / xclip), copy_text_to_clipboard() (clip.exe UTF-16LE+BOM, pbcopy, wl-copy, xclip, xsel), load_prompts()
- 2026-10-26T12:43Z · `465d981` · farsi_flow_workflow.py chunk 13: CLI (build | speech-audit [--json] | sub-clips-only | clipboard-image [--dry-run] | clipboard-prompt [--list/--print]) with --var/--clips-dir/--out-dir/--font/--speech-safe/--only/--cta-video/--no-cta/--force, --ffmpeg/--ffprobe/-v, speech-audit table, exit codes 0/1/2
- 2026-10-26T12:45Z · `d0d5f7b` · manifests/series1_part1_whats_her_number.json: 6 clips, trims, 6 voice colours, clip_03 raw_orig splice [[0,5.22],[6.14,8.60]], badge, Kelidbox Agnes CTA + 2 cta_subtitles (ELLA), Windows roots as ${BASE}/${CHEF_BASE} vars; every Persian line verified verbatim against the reference script
- 2026-10-26T12:47Z · `1355793` · manifests/ugly_chef_part2.json: episode_id Part2 (keeps Master_Part2_Flow_Native_Farsi name), 6 clips + trims + 9 cues, 7-voice Series Character Table (colours + edge-tts fallback), badge, Kelidbox Agnes CTA w/ subs_a from 10_append_kelidbox_flow_cta.py, continuity block; every trim/cue/Persian line verified verbatim against reference scripts 2+3
- 2026-10-26T12:47Z · `07f7c7f` · prompts/ugly_chef_flow_prompts.json: 6 Google Flow scene prompts ported verbatim from set_flow_clipboard.py (text byte-identical, verified via ast), + scene/speakers/location_sheet/dialogue_fa metadata and Character/Location Sheet references; clipboard-prompt --list works
- 2026-10-26T12:49Z · `5ad06d9` · farsi_flow_workflow.py fix: clipboard-image/clipboard-prompt --dry-run report a missing clipboard tool instead of exiting 1 (headless CI)
