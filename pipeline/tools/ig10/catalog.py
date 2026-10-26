"""KelidBox catalog lookup for the Instagram 10-ideas council.

Source of truth: docs/instagram-10-ideas/00-kelidbox-instagram-and-catalog-context.md
(seeded live snapshot). Products referenced by the brief but ABSENT from that
snapshot are excluded. No network lookup is performed.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONTEXT = ROOT / "docs" / "instagram-10-ideas" / "00-kelidbox-instagram-and-catalog-context.md"
_ROW = re.compile(r"- \*\*(.+?)\*\* \(`id: ([^`]+)`\) — از ([\d,]+) تومان")

COUPON = {"code": "WELCOME10", "percent": 10, "max_discount_toman": 150_000,
          "min_order_toman": 100_000,
          "source": "User-confirmed Stage-2 brief, 2026-10-26; no live checkout check"}


def load_catalog(path: Path = CONTEXT) -> dict[str, dict]:
    text = path.read_text(encoding="utf-8")
    cat = {m.group(2): {"id": m.group(2), "title": m.group(1),
                        "min_price_toman": int(m.group(3).replace(",", "")),
                        "verified_in_seed": True}
           for m in _ROW.finditer(text)}
    return cat


def fa_num(n: int | None) -> str:
    if n is None:
        return "؟"
    return f"{n:,}".translate(str.maketrans("0123456789,", "۰۱۲۳۴۵۶۷۸۹٬"))
