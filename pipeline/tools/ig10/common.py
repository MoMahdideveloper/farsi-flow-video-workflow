"""Shared CTA / pricing helpers for the IG10 ideas (doc + manifest)."""
from __future__ import annotations

from .catalog import COUPON, fa_num, load_catalog

PAY_FA = "ترب‌پی / اسنپ‌پی / دیجی‌پی"  # bio confirms TorobPay+SnappPay; DigiPay per brief (Astra to verify)


def products(idea: dict, cat: dict | None = None) -> list[dict]:
    cat = cat or load_catalog()
    return [dict(cat[p]) for p in idea["products"]]


def coupon_saving(price: int | None) -> int | None:
    if price is None or price < COUPON["min_order_toman"]:
        return None
    return min(price * COUPON["percent"] // 100, COUPON["max_discount_toman"])


def cta_fa(idea: dict, cat: dict | None = None) -> str:
    prods = [p for p in products(idea, cat) if p["min_price_toman"]]
    anchor = min(prods, key=lambda p: p["min_price_toman"])
    price = anchor["min_price_toman"]
    return (f"زیر همین پست کلمه «{idea['keyword']}» رو کامنت کن تا لینک مستقیم کلیدباکس رو دایرکت بگیری. "
            f"شروع قیمت از {fa_num(price)} تومان؛ با کد WELCOME10 تا {fa_num(COUPON['max_discount_toman'])} تومان تخفیف "
            f"(خرید بالای {fa_num(COUPON['min_order_toman'])} تومان) و پرداخت ۴ قسط بدون بهره با {PAY_FA}. "
            "خرید ۲ کلیکی، نماد اعتماد اینماد، تحویل فوری.")
