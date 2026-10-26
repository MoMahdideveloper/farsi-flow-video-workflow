# Series 2 — Stage 1 (Claude Opus 5.5, medium) execution trace

Append-only log. Every row = one committed + pushed change to `origin main`.
Keyframe policy for every step: keyframes are read-only (hashed + compared), never drawn on, boxed, blurred or "sanitized".

| # | UTC | Deliverable | Files | Commit | Notes |
|---|-----|-------------|-------|--------|-------|
| 0 | 2026-10-26 21:20 | Baseline | — | `ffd8e21` | origin/main checked out. Baseline pytest: 136 passed, 1 pre-existing failure (`test_all_six_series1_clips_with_shipped_windows`, Series 1 clip_03 window 7.67 vs 7.5 — unrelated to Series 2). |
| 1 | 2026-10-26 21:34 | D1 pipeline v1.2 | `pipeline/farsi_flow_workflow.py` | `1acb09c` | ClipSpec/Episode extensions, `analyze_clip_visuals`, `evaluate_probe_entry`, `inpaint_source_subtitle_band` (numpy-only, source frames only), `extract_source_fallback_clip`, `apply_tight_speech_trim` (min 2.2 s), 6-stage `step_trace` in qa_report.json + trace_<ep>.json, `trace-audit` / `trace-all-parts`. 136 existing tests still pass. Synthetic smoke: fallback keeps Flow audio sha-identical, 192/192 frames band-inpainted, tight trim 7.95 s → 3.55 s. |
