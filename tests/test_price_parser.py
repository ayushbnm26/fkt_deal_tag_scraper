from __future__ import annotations

from extractors.price_parser import (
    clean_price_block,
    discount_matches_prices,
    format_discount,
    format_price,
    infer_old_price_from_price_text,
    parse_discount_value,
    parse_price_value,
)


def test_parse_price_value() -> None:
    assert parse_price_value("₹1,399") == 1399
    assert parse_price_value("1,399") == 1399
    assert parse_price_value("no price") is None


def test_format_price() -> None:
    assert format_price("₹1399") == "1,399"
    assert format_price(279) == "279"
    assert format_price("") == ""


def test_parse_and_format_discount() -> None:
    assert parse_discount_value("↓80%") == 80
    assert format_discount("80% off") == "80%"
    assert parse_discount_value("120%") is None


def test_discount_validation() -> None:
    assert discount_matches_prices("1,399", "279", "80%")
    assert not discount_matches_prices("1,399", "1,500", "80%")


def test_clean_price_block_blanks_invalid_old_price_and_bad_discount() -> None:
    block = clean_price_block(
        {
            "new_price": "₹1,500",
            "old_price": "₹1,399",
            "discount_percentage": "80%",
        }
    )
    assert block["new_price"] == "1,500"
    assert block["old_price"] == ""
    assert block["discount_percentage"] == "80%"

    block = clean_price_block(
        {
            "new_price": "₹279",
            "old_price": "₹1,399",
            "discount_percentage": "20%",
        }
    )
    assert block["old_price"] == "1,399"
    assert block["discount_percentage"] == ""


def test_infer_old_price_from_badge_price_line_without_rupee_on_mrp() -> None:
    text = "Top Discount of the Sale 81% 3,499 \u20b9662 +\u20b926 Protect Promise Fee"

    assert infer_old_price_from_price_text(text, "662", "81%") == "3,499"

    block = clean_price_block(
        {
            "text": text,
            "new_price": "\u20b9662",
            "old_price": "",
            "discount_percentage": "\u219381%",
        }
    )
    assert block["old_price"] == "3,499"
    assert block["new_price"] == "662"
    assert block["discount_percentage"] == "81%"


def test_clean_price_block_uses_nearby_text_to_recover_old_price() -> None:
    block = clean_price_block(
        {
            "text": "Top Discount of the Sale \u20b9662",
            "nearby_text": "Top Discount of the Sale 81% 3,499 \u20b9662 Buy at \u20b9628",
            "new_price": "662",
            "old_price": "",
            "discount_percentage": "81%",
        }
    )

    assert block["old_price"] == "3,499"
