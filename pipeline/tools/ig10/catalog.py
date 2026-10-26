"""KelidBox catalog lookup for the Instagram 10-ideas council.

Source of truth: docs/instagram-10-ideas/00-kelidbox-instagram-and-catalog-context.md
(seeded live snapshot). Products referenced by the brief but ABSENT from that
snapshot are listed in UNVERIFIED with the brief's price and flagged
verified_in_seed=False so Stage 2 (Astra) can confirm them on kelidbox.com.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONTEXT = ROOT / "docs" / "instagram-10-ideas" / "00-kelidbox-instagram-and-catalog-context.md"
_ROW = re.compile(r"- \*\*(.+?)\*\* \(`id: ([^`]+)`\) — از ([\d,]+) تومان")

UNVERIFIED = {
    "draft_ee59478a-977e-42ca-b176-9ceb0def34c8": ("اشتراک CapCut Pro", 190_000),
    "draft_75a7b397-5b21-46ee-81a6-e134abb55ab1": ("اشتراک Wordwall Pro", None),
    "office-365-onedrive": ("اشتراک Office 365 + ۱ ترابایت OneDrive", 590_000),
}

COUPON = {"code": "WELCOME10", "percent": 10, "max_discount_toman": 150_000,
          "min_order_toman": 100_000,
          "source": "Stage-1 brief (not stated in 00-context.md; Astra to confirm)"}


def load_catalog(path: Path = CONTEXT) -> dict[str, dict]:
    text = path.read_text(encoding="utf-8")
    cat = {m.group(2): {"id": m.group(2), "title": m.group(1),
                        "min_price_toman": int(m.group(3).replace(",", "")),
                        "verified_in_seed": True}
           for m in _ROW.finditer(text)}
    for pid, (title, price) in UNVERIFIED.items():
        cat.setdefault(pid, {"id": pid, "title": title, "min_price_toman": price,
                             "verified_in_seed": False})
    return cat


def fa_num(n: int | None) -> str:
    if n is None:
        return "؟"
    return f"{n:,}".translate(str.maketrans("0123456789,", "۰۱۲۳۴۵۶۷۸۹٬"))
