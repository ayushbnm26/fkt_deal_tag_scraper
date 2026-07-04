from __future__ import annotations

import re
from typing import Any


def parse_price_value(text: str) -> int | None:
    if text is None:
        return None
    match = re.search(r"(\d[\d,]*)", str(text).replace("\u00a0", " "))
    if not match:
        return None
    try:
        return int(match.group(1).replace(",", ""))
    except ValueError:
        return None


def format_price(value: int | str | None) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, int):
        return f"{value:,}"
    parsed = parse_price_value(str(value))
    return f"{parsed:,}" if parsed is not None else ""


def parse_discount_value(text: str) -> int | None:
    if text is None:
        return None
    match = re.search(r"(\d{1,3})\s*%", str(text))
    if not match:
        return None
    value = int(match.group(1))
    if 0 < value < 100:
        return value
    return None


def format_discount(value: int | str | None) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, int):
        return f"{value}%"
    parsed = parse_discount_value(str(value))
    return f"{parsed}%" if parsed is not None else ""


def discount_matches_prices(old_price: str, new_price: str, discount: str, tolerance: int = 3) -> bool:
    old_value = parse_price_value(old_price)
    new_value = parse_price_value(new_price)
    discount_value = parse_discount_value(discount)
    if old_value is None or new_value is None or discount_value is None:
        return True
    if old_value <= 0 or new_value <= 0 or old_value <= new_value:
        return False
    computed = round(((old_value - new_value) / old_value) * 100)
    return abs(computed - discount_value) <= tolerance


def clean_price_block(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw or {}
    old_price = format_price(raw.get("old_price") or raw.get("oldPrice"))
    new_price = format_price(raw.get("new_price") or raw.get("newPrice"))
    discount = format_discount(raw.get("discount_percentage") or raw.get("discountPercentage"))

    raw_text = str(raw.get("text") or raw.get("nearby_text") or "")
    sequence = re.search(
        r"(?:↓\s*)?(\d{1,3})\s*%[^₹\d]{0,8}(\d[\d,]*)[^₹]{0,20}₹\s*(\d[\d,]*)",
        raw_text,
    )
    if sequence:
        candidate_old = format_price(sequence.group(2))
        candidate_new = format_price(sequence.group(3))
        if not discount:
            discount = format_discount(sequence.group(1))
        if not old_price:
            old_price = candidate_old
        if not new_price:
            new_price = candidate_new

    valid = bool(new_price)
    old_value = parse_price_value(old_price)
    new_value = parse_price_value(new_price)
    if old_price and new_price and (old_value is None or new_value is None or old_value <= new_value):
        old_price = ""
    if old_price and new_price and discount and not discount_matches_prices(old_price, new_price, discount):
        discount = ""

    cleaned = dict(raw)
    cleaned.update(
        {
            "old_price": old_price,
            "new_price": new_price,
            "discount_percentage": discount,
            "price_parse_valid": valid,
        }
    )
    return cleaned
