# TRACE — Instagram 10 Customer Ideas Council (`council/instagram-10-customer-ideas-20261026`)

Append-only progress log. Each entry: UTC time · stage · file · action · commit SHA (the SHA of the
commit that introduced the change is recorded in the *next* entry, because a commit cannot contain
its own hash).

## Stage 1 — Claude Opus 5.5 (Chief Viral Content Architect)

| # | UTC | File | Action | Commit |
|---|-----|------|--------|--------|
| 1 | 2026-10-26 18:34 | `docs/instagram-10-ideas/TRACE.md` | Stage 1 started; branch checked out at `723b0af`; context file `00-…context.md` read (189 lines) | (this commit) |
| 2 | 2026-10-26 19:10 | `docs/instagram-10-ideas/TRACE.md` | Entry #1 landed | `e79deac` |
| 3 | 2026-10-26 19:20 | `01-opus55-10-instagram-conversion-ideas.md`, `pipeline/tools/ig10/{catalog,common,ideas_01_05,render_md}.py` | Ideas 1–5 written (shop teaser, faceless animation, AI spokesperson, birthday song, kid drawing) | `6c6ec63` |
| 4 | 2026-10-26 19:30 | `01-opus55-…md`, `pipeline/tools/ig10/ideas_06_10.py` | Ideas 6–10 appended (slides/notes, freelance income, price-trust, ad-free family, gaming) — 846 lines | `3063de6` |
| 5 | 2026-10-26 19:38 | `pipeline/manifests/instagram_10_conversion_ideas.json`, `pipeline/tools/ig10/build_manifest.py` | Manifest generated: 10 ideas × 5 shots (40 s each), `--check` mode passes | `9bb7c17` |
| 6 | 2026-10-26 19:40 | `docs/instagram-10-ideas/TRACE.md` | Stage 1 sign-off (this entry) | (this commit) |

### Stage 1 summary & hand-off notes for Stage 2 (GPT-6 Astra)

- **Single source of truth:** ideas live in `pipeline/tools/ig10/ideas_01_05.py` + `ideas_06_10.py`. Both the Markdown doc
  (`render_md.py`) and the JSON manifest (`build_manifest.py`) are generated from them — edit the modules, then rerun both.
  `python pipeline/tools/ig10/build_manifest.py --check` exits 1 if the JSON is stale (useful for the pytest suite).
- **Prices:** every `min_price_toman` is parsed from the seeded snapshot `00-…context.md`. The Stage-1 brief quoted lower
  "از" prices for 12 products (e.g. ChatGPT 390,000 vs snapshot 3,740,000; Canva 230,000 vs 380,000; Kling 850,000 vs
  4,010,000). **Snapshot prices were used**; brief figures are listed per idea under *Brief discrepancy*. Astra: confirm on kelidbox.com.
- **Unverified products** (not in snapshot, `verified_in_seed: false`): CapCut Pro `draft_ee59478a-…` (brief: 190,000),
  Wordwall Pro `draft_75a7b397-…` (no price), Office 365 + 1TB `office-365-onedrive` (brief: 590,000).
- **Coupon / installments:** `WELCOME10` rules (10%, max 150,000, min order 100,000) and DigiPay come from the brief, not
  the context file (bio confirms TorobPay + SnappPay only). Idea 8's "~9% tax/fee" is illustrative — no exact figure is claimed on screen.
- **Mix:** ideas 1–7 = "what can an ordinary person do/earn with AI" (≥6 required); 8–10 = price-trust, family entertainment, gaming.
- **Comment keywords (for DM funnel):** تیزر · انیمیشن · مجری · تولد · نقاشی · اسلاید · درآمد · قیمت · بدون تبلیغ · گیم.
- **Manifest note:** schema is idea/shot-level (prompts + RTL cues), not the clip-level render schema of
  `farsi_flow_workflow.py build`; per-shot `subtitles_rtl` cues are placeholders to re-time after Flow renders (Gate 3).
