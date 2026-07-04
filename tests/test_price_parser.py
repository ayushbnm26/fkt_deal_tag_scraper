from __future__ import annotations

from extractors.price_parser import (
    clean_price_block,
    discount_matches_prices,
    format_discount,
    format_price,
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
