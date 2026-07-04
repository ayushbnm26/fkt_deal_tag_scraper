from __future__ import annotations

import re
from typing import Any


PRICE_SEQUENCE_RE = re.compile(
    r"(?:\u2193\s*)?(\d{1,3})\s*%[^\u20b9\d]{0,12}(\d[\d,]*)[^\u20b9]{0,24}\u20b9\s*(\d[\d,]*)"
)
DISCOUNT_RE = re.compile(r"(?:\u2193\s*)?(\d{1,3})\s*%")
NUMBER_TOKEN_RE = re.compile(r"(?:\u20b9\s*)?(\d[\d,]*)")


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


def infer_old_price_from_price_text(raw_text: str, new_price: str, discount: str) -> str:
    new_value = parse_price_value(new_price)
    discount_value = parse_discount_value(discount)
    if new_value is None or discount_value is None:
        return ""

    text = str(raw_text or "").replace("\u00a0", " ")
    for discount_match in DISCOUNT_RE.finditer(text):
        if parse_discount_value(discount_match.group(0)) != discount_value:
            continue

        window_start = discount_match.start()
        window = text[window_start : discount_match.end() + 140]
        discount_end = discount_match.end() - window_start
        tokens: list[tuple[int, int]] = []
        for token in NUMBER_TOKEN_RE.finditer(window):
            if token.start() < discount_end:
                continue
            value = parse_price_value(token.group(1))
            if value is not None:
                tokens.append((value, token.start()))

        for index, (value, _position) in enumerate(tokens):
            if value != new_value:
                continue
            previous_prices = [candidate for candidate, _ in tokens[:index] if candidate > new_value]
            for candidate in reversed(previous_prices):
                formatted = format_price(candidate)
                if discount_matches_prices(formatted, format_price(new_value), format_discount(discount_value)):
                    return formatted

        for value, _position in tokens:
            if value <= new_value:
                continue
            formatted = format_price(value)
            if discount_matches_prices(formatted, format_price(new_value), format_discount(discount_value)):
                return formatted

    return ""


def clean_price_block(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = raw or {}
    old_price = format_price(raw.get("old_price") or raw.get("oldPrice"))
    new_price = format_price(raw.get("new_price") or raw.get("newPrice"))
    discount = format_discount(raw.get("discount_percentage") or raw.get("discountPercentage"))

    raw_text = " ".join(
        str(part)
        for part in (raw.get("text"), raw.get("nearby_text"))
        if part not in (None, "")
    )
    sequence = PRICE_SEQUENCE_RE.search(raw_text)
    if sequence:
        candidate_old = format_price(sequence.group(2))
        candidate_new = format_price(sequence.group(3))
        if not discount:
            discount = format_discount(sequence.group(1))
        if not old_price:
            old_price = candidate_old
        if not new_price:
            new_price = candidate_new

    if not old_price:
        old_price = infer_old_price_from_price_text(raw_text, new_price, discount)

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
