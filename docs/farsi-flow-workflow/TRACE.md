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
- 2026-10-26T12:50Z · `aa196bb` · farsi_flow_workflow.py fix: detect_speech_segments() adaptive threshold capped at peak - peak_margin_db (12 dB). Before: clips with speech in >90% of frames (10th-pct floor = speech) got threshold above peak -> 'no speech' -> auto_expand silently disabled (found by smoke test: clip_01/clip_04). Verified: dense clip, music-bed, silence cases
- 2026-10-26T12:51Z · `6565e05` · tools/synth_fixtures.py: manifest-driven synthetic Flow sources (testsrc2 1080x1920 + voiced bursts at every cue's source time, -62 dBFS floor), splice-aware raw_orig with junk in removed gaps, --leak-in (word before trim_in), --fps CLIP=30, CTA clip, 9:16 PNG keyframe, fixtures.json ground truth
- 2026-10-26T12:55Z · `fe4dc33` · smoke test (synthetic 1080x1920@30 testsrc2 + 44.1k mono tone-burst "speech", 6 clips + raw_orig splice + 8s CTA): speech-audit OK (auto_expand widened 5 edges, warn flags clip_02 CUTS-SPEECH w/o changing trims); build 3m16s -> 6x clip_XX_subbed.mp4 (h264 720x1280@24 + aac 48k stereo, mirrored clips_dir + out_dir/clips_subbed), Base 52.125s, Master 60.125s (A/V equal), BOM .srt 17 cues incl. 2 CTA, audit.mp3, 18-tile contact sheet visually checked (badge + RTL pills correct), qa_report overall_automatic=pass, human_review=pending; re-run 4.4s, Master sha unchanged, exactly 1 CTA; --no-cta Master == Base byte-identical; sub-clips-only --only 1,3 on ugly_chef_part2 pass; clipboard-prompt --list/--dry-run, clipboard-image --dry-run OK, landscape keyframe rejected exit 1
- 2026-10-26T12:56Z · `d84393e` · 01-opus55-architecture-spec.md part 1/4: deliverables table, 7 legacy failures -> root cause -> fix, end-to-end data-flow diagram, single-timeline/frame+sample quantisation contract
- 2026-10-26T12:57Z · `d578bd1` · 01-opus55-architecture-spec.md part 2/4: full manifest schema + validation rules, ${VAR}/Windows->POSIX path resolution, two-manifest comparison table, speech analyzer algorithm incl. peak-12 dB cap rationale, plan_trim mode table + subtitle_shift
- 2026-10-26T12:57Z · `5ac1877` · 01-opus55-architecture-spec.md part 3/4: shaping-engine table, Persian-glyph font resolution chain, 27->16pt fit + 2-line balance wrap, pill geometry/colours, PNG+ffmpeg overlay composite; output file table, build.json caching, tmp->verify->promote, CTA idempotency keys, timeline vs concat_subbed Base modes
- 2026-10-26T12:58Z · `5572fbe` · farsi_flow_workflow.py fix (v1.0.1): loudnorm emits a 67-83 ms audio pts hole ~5.5 s into every clip; mp4 muxer stored it as one stretched AAC packet, so clip_XX_subbed.mp4 audio drifted late after it while the 0.15 s drift gate still passed. Fix: asetpts=N/SR/TB after loudnorm (normalize_clip + normalize_cta); new audio_pts_gaps() (pts jumps + stretched packets) -> av_checks 'audio_contiguous' gate on every clip/Base/Master; version bump invalidates cached intermediates. Base/Master were unaffected (PCM sidecar path)
- 2026-10-26T12:58Z · `cdb6471` · 01-opus55-architecture-spec.md part 4/4 (complete, 343 lines): qa_report.json structure + automatic gate table, human gates always pending, CLI reference + exit codes + typical runs, clipboard helpers, Stage 1 verification matrix, known limits & hand-off (ASR upgrade, fonts, pytest suite via synth_fixtures)
- 2026-10-26T13:00Z · `8355b20` · 01-opus55-architecture-spec.md synced to v1.0.1: version header, audio_contiguous added to per-clip/Base/Master gates, §9 lists both Stage 1 fixes (aa196bb speech threshold, 5572fbe loudnorm PTS hole) + re-verification on v1.0.1 (clip_01/03 contiguous, drift <1 ms, all gates pass). Stage 1 COMPLETE

- 2026-10-26T13:00Z · `049acb25878ddcd404b4e14801b99a2086ade011` · Stage 2: fix(stage2): validate inputs, protect sources, hash cached media, support --manifest and honest CLI failures

- 2026-10-26T13:01Z · `00f4786f97db41c6f5c8c579b2532ce9592d34f6` · Stage 2: fix(stage2): retain exact audio trims, audit splice boundaries, and expose complete scoped QA status

- 2026-10-26T13:02Z · `07fb355c6973b16d234aedcb26dbdf72431675bf` · Stage 2: fix(stage2): preserve Series1 curated trim windows with warn mode and explicit listening gate

- 2026-10-26T13:02Z · `266bf66a2b2f88dbc169952ad2ac471af2a3379c` · Stage 2: docs(stage2): document Ugly Chef auto-expansion limits and native-audio listening requirements

- 2026-10-26T13:03Z · `42fa0b07c788a7a4d42055d6c6129b8e769cb8e1` · Stage 2: test(stage2): add real 720x1280 24fps harmonic-audio fixtures and end-to-end build harness
