"""Shared, bounded conversion copy. All prices are snapshot starting prices."""
from __future__ import annotations
from .catalog import COUPON, fa_num, load_catalog

PAY_FA = "ترب‌پی / دیجی‌پی"


def products(idea: dict, cat: dict | None = None) -> list[dict]:
    cat = cat or load_catalog()
    return [dict(cat[p]) for p in idea["products"]]


def coupon_saving(price: int | None) -> int | None:
    if price is None or price < COUPON["min_order_toman"]:
        return None
    return min(price * COUPON["percent"] // 100, COUPON["max_discount_toman"])


def product_url(pid: str) -> str:
    # Candidate path, NOT a verified route: snapshot records IDs, not permalinks.
    return f"https://kelidbox.com/product/{pid}"


def cta_fa(idea: dict, cat: dict | None = None) -> str:
    cat = cat or load_catalog()
    anchor = cat[idea["primary_product_id"]]
    return (f"کلمه «{idea['keyword']}» رو کامنت کن تا لینک و راهنمای خرید رو بگیری. "
            f"محصول اصلی: {anchor['title']}؛ قیمت ثبت‌شده از {fa_num(anchor['min_price_toman'])} تومان "
            "(قیمت همین محصول، نه هزینه همه ابزارهای دمو؛ قیمت روز و پلن را در صفحه ببین). "
            "کد WELCOME10: ده درصد (۱۰٪) تخفیف تا سقف ۱۵۰٬۰۰۰ تومان، حداقل سفارش ۱۰۰٬۰۰۰ تومان. "
            f"در تسویه، پرداخت ۴ قسط با {PAY_FA} را طبق شرایط اعتبار انتخاب کن؛ "
            "مبلغ نهایی، امکان ترکیب کد و قسط، سررسیدها و زمان تحویل را پیش از پرداخت بررسی کن.")
