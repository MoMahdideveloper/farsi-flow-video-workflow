"""Render docs/instagram-10-ideas/01-opus55-10-instagram-conversion-ideas.md from the idea modules."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ig10.catalog import ROOT, COUPON, fa_num, load_catalog  # noqa: E402
from ig10.common import cta_fa, coupon_saving, products, product_url  # noqa: E402

OUT = ROOT / "docs" / "instagram-10-ideas" / "01-opus55-10-instagram-conversion-ideas.md"

HEADER = """# Stage 1 — Claude Opus 5.5: 10 Instagram Conversion Ideas for `@kelidbox_com`

> Audience: **general everyday Iranian Instagram users (مخاطب عام)** — not AI experts.
> Rule of every reel: *show a normal person's problem → show the AI result in 5 seconds → show the exact KelidBox accounts that did it → one comment keyword.*
> Ideas 1–7 answer **"What can an ordinary person do / earn with AI video & AI accounts?"**; ideas 8–10 bridge the 3D-animation style to price-trust, entertainment and gaming accounts.

**Stage 2 audit:** Product IDs and starting prices are checked offline against the
[seeded catalog](00-kelidbox-instagram-and-catalog-context.md), not re-fetched live.
Unseeded CapCut Pro, Wordwall Pro and Office 365 listings were removed.
Coupon: WELCOME10 = {pct}% off, max {mx} Toman, minimum order {mn} Toman;
TorobPay / DigiPay four installments are user-confirmed in the Stage-2 brief.
Eligibility, fees, due dates, coupon stacking and delivery follow the actual checkout.
Candidate product links are NOT verified permalinks; do not enable automation until checked.
No guaranteed income, production time, instant fulfillment, interest-free credit or performance.

**Shared production spec (all reels):** 9:16, 720×1280 @ 24 fps, 5 shots × 8 s = 40 s, Google Flow (Veo) native Farsi
audio, RTL Vazirmatn-Bold subtitle pills, last shot = CTA (no separate KelidBox CTA clip appended). The machine-readable
version is the [planning manifest](../../pipeline/manifests/instagram_10_conversion_ideas.json).
It is NOT a clip-level render input: render clips, then adapt and retime cues. Hooks have a 3-second script budget, not measured audio.
Spoken copy needs a native-Farsi timing pass. Add Persian UI text/subtitles in editing; never trust generated text or badges.

| # | Idea | Segment | Keyword |
|---|------|---------|---------|
"""


def idea_md(i: int, idea: dict, cat: dict, briefs: dict) -> str:
    L = [f"\n---\n\n## Idea {i} — {idea['title_fa']}\n",
         f"**Segment:** `{idea['segment']}` · **Psychological trigger:** {idea['trigger']}\n",
         "### (a) Everyday persona & pain point",
         f"- **Persona:** {idea['persona_fa']}", f"- **Pain:** {idea['pain_fa']}\n",
         "### (b) 3-second information-gap hook",
         f"- **Visual:** {idea['hook_visual']}", f"- **First spoken line (Farsi):** «{idea['hook_fa']}»\n",
         "### (c) Before → After demo (understood in 5 seconds)",
         f"- **Before:** {idea['before_fa']}", f"- **After:** {idea['after_fa']}\n",
         "### (d) 40-second 5-shot reel script",
         "| Shot | Sec | Visual | Spoken Farsi | RTL subtitle pills |", "|---|---|---|---|---|"]
    t = 0
    for n, (d, vis, _mot, fa, subs) in enumerate(idea["shots"], 1):
        L.append(f"| {n} | {t}–{t + d} | {vis.split('. ', 1)[-1] if vis.startswith('3D Pixar') else vis} | {fa} | {' · '.join(subs)} |")
        t += d
    L.append("\n### (e) Ready-to-paste Google Flow / Kling prompts")
    for n, (d, vis, mot, _fa, _s) in enumerate(idea["shots"], 1):
        L.append(f"**Shot {n} — image/keyframe prompt**\n```text\n{vis}\n```\n**Shot {n} — motion + audio prompt ({d}s)**\n```text\n{mot}\n```")
    L.append("\n### (f) Featured KelidBox accounts, price anchor & CTA")
    L.append("| Product | id | Snapshot from (Toman) | WELCOME10 saving | Illustrative price / 4, before discount or fees |\n|---|---|---|---|---|")
    for p in products(idea, cat):
        pr = p["min_price_toman"]
        flag = "" if p["verified_in_seed"] else " ⚠️ unverified"
        sv = coupon_saving(pr)
        L.append(f"| [{p['title']}{flag}]({product_url(p['id'])}) (candidate URL) | `{p['id']}` | {fa_num(pr)} | {fa_num(sv) if sv else '—'} | "
                 f"{fa_num(-(-pr // 4)) if pr else '—'} |")
    L.append("\nInstallment division is arithmetic only, not an approved repayment schedule. Primary product: " + idea["primary_product_id"] + "; others optional/alternatives, not a bundle.")
    disc = [f"{k}: brief said {v}" for k, v in briefs.items() if k in idea["products"]]
    if disc:
        L.append("\n*Brief discrepancy (snapshot price used):* " + "; ".join(disc))
    L.append(f"\n- **Comment keyword:** `{idea['keyword']}`\n- **CTA caption (Farsi):** {cta_fa(idea, cat)}\n")
    return "\n".join(L)


BRIEF_PRICES = {  # prices quoted in the Stage-1 brief that differ from the seeded snapshot
    "draft_83353025-b540-45aa-ac1f-624f826a4098": "850,000", "chatgpt-plus": "390,000", "canva-pro": "230,000",
    "midjourney-pro": "720,000", "claude-pro": "440,000", "youtube-premium": "175,000",
    "spotify-premium": "165,000", "netflix-4k": "290,000", "cod-mobile-cp": "68,000",
    "roblox-robux": "295,000", "valorant-points": "195,000", "telegram-stars": "135,000",
}


def render(ideas: list[dict]) -> str:
    cat = load_catalog()
    head = HEADER.format(pct=COUPON["percent"], mx=fa_num(COUPON["max_discount_toman"]), mn=fa_num(COUPON["min_order_toman"]))
    rows = "\n".join(f"| {n} | {x['title_fa']} | `{x['segment']}` | `{x['keyword']}` |" for n, x in enumerate(ideas, 1))
    return head + rows + "\n" + "".join(idea_md(n, x, cat, BRIEF_PRICES) for n, x in enumerate(ideas, 1))


if __name__ == "__main__":
    from ig10.ideas_01_05 import IDEAS as A
    ideas = list(A)
    try:
        from ig10.ideas_06_10 import IDEAS as B
        ideas += B
    except ImportError:
        pass
    OUT.write_text(render(ideas), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(ideas)} ideas")
