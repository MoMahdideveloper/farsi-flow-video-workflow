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


## Stage 2 — Conversion audit, playbook and pytest verification

Recorded 2026-10-26 19:26 UTC. Stage-1 entries above preserved verbatim; their times are inherited, not independently reconciled.

Scope: offline seeded-catalog validation and user-confirmed offer terms. No web searches, no external curl, no live product/checkout fetch. Existing pytest 9.1.1 used; no package installation.

| Commit | Stage 2 change |
|---|---|
| [b0add28](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/commit/b0add28) | fix(ig10): remove unseeded products and harden hooks and demo claims |
| [7282e09](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/commit/7282e09) | fix(ig10): anchor core product prices and encode evidence and release gates |
| [bb58b09](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/commit/bb58b09) | docs(ig10): add conversion ranking and Persian profile and pinned scripts |
| [104b937](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/commit/104b937) | docs(ig10): add five highlight scripts and ten gated Persian DM flows |
| [0dbead3](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/commit/0dbead3) | docs(ig10): complete 30-day calendar measurement and launch gates |
| [3eae15a](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/commit/3eae15a) | test(ig10): validate all products hooks CTAs and 50 shot contracts |
| [1acd346](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/commit/1acd346) | test(ig10): cover deliverable completeness generation drift and negative cases |
| [32cbeb6](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/commit/32cbeb6) | fix(ig10): remove residual synthetic proof and unsupported production promises |

### Verification results

- 10 unique ideas, 50 shots, 40 seconds per idea; 3-second Persian hook budgets and matching first-shot dialogue.
- Featured IDs, exact titles and starting prices independently checked against enumerated catalog rows. Three unseeded listings removed. Primary-product pricing replaces cheapest-accessory anchoring.
- Persian RTL cues checked for direction, non-empty text, timing bounds and non-overlap; Flow visual/motion prompts required for every shot. Audio and visual readability remain human/render QA.
- Coupon: WELCOME10, 10%, maximum 150,000 Toman, minimum order 100,000 Toman. TorobPay / DigiPay four-installment terms attributed to the explicit Stage-2 brief. No unverified zero-interest, universal credit or instant-delivery assertions.
- Both Markdown deliverables complete; generated Stage-1 Markdown and manifest match source. Playbook: 10 ranked ideas, 106-character bio, 3 pinned scripts, 5 four-frame highlights, 10 DM scripts, 30 sequential calendar days.
- Regression cases reject missing shots, unknown products, wrong prices/anchors, English-only/long/misaligned hooks and absent coupons.
- Final recommendation: publish IG10_01 (تیزر), IG10_02 (انیمیشن), IG10_06 (اسلاید) first. Rankings are editorial hypotheses, not observed sales evidence.

### Pytest output

Command: `pytest tests/test_instagram_10_ideas_manifest.py -v`

```text
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0 -- /usr/bin/python3
plugins: anyio-4.15.1
collecting ... collected 89 items

tests/test_instagram_10_ideas_manifest.py::test_manifest_shape_and_provenance PASSED [  1%]
tests/test_instagram_10_ideas_manifest.py::test_each_idea_has_seeded_products_hook_and_conversion_cta[IG10_01] PASSED [  2%]
tests/test_instagram_10_ideas_manifest.py::test_each_idea_has_seeded_products_hook_and_conversion_cta[IG10_02] PASSED [  3%]
tests/test_instagram_10_ideas_manifest.py::test_each_idea_has_seeded_products_hook_and_conversion_cta[IG10_03] PASSED [  4%]
tests/test_instagram_10_ideas_manifest.py::test_each_idea_has_seeded_products_hook_and_conversion_cta[IG10_04] PASSED [  5%]
tests/test_instagram_10_ideas_manifest.py::test_each_idea_has_seeded_products_hook_and_conversion_cta[IG10_05] PASSED [  6%]
tests/test_instagram_10_ideas_manifest.py::test_each_idea_has_seeded_products_hook_and_conversion_cta[IG10_06] PASSED [  7%]
tests/test_instagram_10_ideas_manifest.py::test_each_idea_has_seeded_products_hook_and_conversion_cta[IG10_07] PASSED [  8%]
tests/test_instagram_10_ideas_manifest.py::test_each_idea_has_seeded_products_hook_and_conversion_cta[IG10_08] PASSED [ 10%]
tests/test_instagram_10_ideas_manifest.py::test_each_idea_has_seeded_products_hook_and_conversion_cta[IG10_09] PASSED [ 11%]
tests/test_instagram_10_ideas_manifest.py::test_each_idea_has_seeded_products_hook_and_conversion_cta[IG10_10] PASSED [ 12%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_01_S01] PASSED [ 13%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_01_S02] PASSED [ 14%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_01_S03] PASSED [ 15%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_01_S04] PASSED [ 16%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_01_S05] PASSED [ 17%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_02_S01] PASSED [ 19%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_02_S02] PASSED [ 20%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_02_S03] PASSED [ 21%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_02_S04] PASSED [ 22%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_02_S05] PASSED [ 23%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_03_S01] PASSED [ 24%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_03_S02] PASSED [ 25%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_03_S03] PASSED [ 26%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_03_S04] PASSED [ 28%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_03_S05] PASSED [ 29%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_04_S01] PASSED [ 30%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_04_S02] PASSED [ 31%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_04_S03] PASSED [ 32%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_04_S04] PASSED [ 33%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_04_S05] PASSED [ 34%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_05_S01] PASSED [ 35%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_05_S02] PASSED [ 37%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_05_S03] PASSED [ 38%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_05_S04] PASSED [ 39%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_05_S05] PASSED [ 40%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_06_S01] PASSED [ 41%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_06_S02] PASSED [ 42%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_06_S03] PASSED [ 43%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_06_S04] PASSED [ 44%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_06_S05] PASSED [ 46%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_07_S01] PASSED [ 47%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_07_S02] PASSED [ 48%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_07_S03] PASSED [ 49%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_07_S04] PASSED [ 50%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_07_S05] PASSED [ 51%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_08_S01] PASSED [ 52%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_08_S02] PASSED [ 53%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_08_S03] PASSED [ 55%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_08_S04] PASSED [ 56%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_08_S05] PASSED [ 57%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_09_S01] PASSED [ 58%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_09_S02] PASSED [ 59%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_09_S03] PASSED [ 60%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_09_S04] PASSED [ 61%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_09_S05] PASSED [ 62%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_10_S01] PASSED [ 64%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_10_S02] PASSED [ 65%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_10_S03] PASSED [ 66%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_10_S04] PASSED [ 67%]
tests/test_instagram_10_ideas_manifest.py::test_each_shot_has_flow_prompts_and_timed_rtl_subtitles[IG10_10_S05] PASSED [ 68%]
tests/test_instagram_10_ideas_manifest.py::test_offer_terms_are_exact_and_attributed PASSED [ 69%]
tests/test_instagram_10_ideas_manifest.py::test_coupon_boundaries[99999-None] PASSED [ 70%]
tests/test_instagram_10_ideas_manifest.py::test_coupon_boundaries[100000-10000] PASSED [ 71%]
tests/test_instagram_10_ideas_manifest.py::test_coupon_boundaries[380000-38000] PASSED [ 73%]
tests/test_instagram_10_ideas_manifest.py::test_coupon_boundaries[1500000-150000] PASSED [ 74%]
tests/test_instagram_10_ideas_manifest.py::test_coupon_boundaries[1710000-150000] PASSED [ 75%]
tests/test_instagram_10_ideas_manifest.py::test_coupon_boundaries[None-None] PASSED [ 76%]
tests/test_instagram_10_ideas_manifest.py::test_generated_manifest_and_stage1_document_are_current PASSED [ 77%]
tests/test_instagram_10_ideas_manifest.py::test_stage1_markdown_has_all_ten_complete_ideas PASSED [ 78%]
tests/test_instagram_10_ideas_manifest.py::test_playbook_has_substantive_ranking_profile_calendar_and_launch_gates PASSED [ 79%]
tests/test_instagram_10_ideas_manifest.py::test_each_dm_contains_matching_product_offer_and_installment_steps[IG10_01] PASSED [ 80%]
tests/test_instagram_10_ideas_manifest.py::test_each_dm_contains_matching_product_offer_and_installment_steps[IG10_02] PASSED [ 82%]
tests/test_instagram_10_ideas_manifest.py::test_each_dm_contains_matching_product_offer_and_installment_steps[IG10_03] PASSED [ 83%]
tests/test_instagram_10_ideas_manifest.py::test_each_dm_contains_matching_product_offer_and_installment_steps[IG10_04] PASSED [ 84%]
tests/test_instagram_10_ideas_manifest.py::test_each_dm_contains_matching_product_offer_and_installment_steps[IG10_05] PASSED [ 85%]
tests/test_instagram_10_ideas_manifest.py::test_each_dm_contains_matching_product_offer_and_installment_steps[IG10_06] PASSED [ 86%]
tests/test_instagram_10_ideas_manifest.py::test_each_dm_contains_matching_product_offer_and_installment_steps[IG10_07] PASSED [ 87%]
tests/test_instagram_10_ideas_manifest.py::test_each_dm_contains_matching_product_offer_and_installment_steps[IG10_08] PASSED [ 88%]
tests/test_instagram_10_ideas_manifest.py::test_each_dm_contains_matching_product_offer_and_installment_steps[IG10_09] PASSED [ 89%]
tests/test_instagram_10_ideas_manifest.py::test_each_dm_contains_matching_product_offer_and_installment_steps[IG10_10] PASSED [ 91%]
tests/test_instagram_10_ideas_manifest.py::test_validation_rejects_regressions[missing_shot] PASSED [ 92%]
tests/test_instagram_10_ideas_manifest.py::test_validation_rejects_regressions[unknown_product] PASSED [ 93%]
tests/test_instagram_10_ideas_manifest.py::test_validation_rejects_regressions[wrong_price] PASSED [ 94%]
tests/test_instagram_10_ideas_manifest.py::test_validation_rejects_regressions[wrong_anchor] PASSED [ 95%]
tests/test_instagram_10_ideas_manifest.py::test_validation_rejects_regressions[english_hook] PASSED [ 96%]
tests/test_instagram_10_ideas_manifest.py::test_validation_rejects_regressions[long_hook] PASSED [ 97%]
tests/test_instagram_10_ideas_manifest.py::test_validation_rejects_regressions[mismatched_hook] PASSED [ 98%]
tests/test_instagram_10_ideas_manifest.py::test_validation_rejects_regressions[missing_coupon] PASSED [100%]

============================== 89 passed in 0.16s ==============================
```

### Deliverables and release decision

- [Audited Stage-1 scripts](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/blob/council/instagram-10-customer-ideas-20261026/docs/instagram-10-ideas/01-opus55-10-instagram-conversion-ideas.md)
- [Stage-2 conversion playbook](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/blob/council/instagram-10-customer-ideas-20261026/docs/instagram-10-ideas/02-astra-verified-conversion-playbook.md)
- [Planning manifest](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/blob/council/instagram-10-customer-ideas-20261026/pipeline/manifests/instagram_10_conversion_ideas.json)
- [Verification tests](https://github.com/MoMahdideveloper/farsi-flow-video-workflow/blob/council/instagram-10-customer-ideas-20261026/tests/test_instagram_10_ideas_manifest.py)

**Offline deliverables: PASS (89/89 tests). Customer-facing launch: HOLD pending real product permalinks, selected-plan/checkout checks, automation permission/send tests, and rendered Farsi timing/RTL review.** The source does not document product URL routing; all proposed product URLs are explicitly `candidate_unverified_route`. No claim that URLs resolve, checkout was tested, DMs were deployed or videos rendered. The JSON is an idea/shot planning schema, not a direct clip-level build input.

This entry is introduced by the current commit; its SHA is recorded in the next receipt entry, following the append-only convention.
