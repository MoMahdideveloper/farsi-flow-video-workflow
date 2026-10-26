# Part 3 Audit — Stage Trace Log

Append-only log. Each entry = one logical change pushed to `origin/main`
(`<UTC time> | <stage> | <files> | <commit SHA of the change>`).
The SHA of an entry is the commit that introduced the change described; the
trace line itself is committed in the follow-up commit.

## Stage 1 — Claude Opus 5.5 (visual continuity, keyframe sanitizer, step-trace)

| # | UTC | Change | Files | Commit |
|---|-----|--------|-------|--------|
| 0 | 2026-10-26 17:25 | Stage 1 start. Baseline on `8724c87`: `pytest tests` = 47 pass / 1 pre-existing fail (`test_all_six_series1_clips_with_shipped_windows`: series1 manifest window `[0.5, 7.5]` auto-expands to `[0.5, 7.67]`; unrelated to Part 3). | `docs/part3-audit/TRACE.md` | `8724c87` (base) |
