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
