from __future__ import annotations

import pytest

from extractors.dom_extractor import evaluate_candidates, fallback_candidate_from_price_block
from extractors.validators import (
    extract_promotional_badge_phrase,
    has_badge_visual_context,
    is_dimension_or_variant_text,
    is_price_or_discount_text,
    is_promotional_badge_text,
    is_ui_or_offer_noise,
)


REJECTED_TEXTS = [
    "72 inch x 36 inch",
    "72 inch x 84 inch",
    "72 inch x 72 inch",
    "72 cm x 46 cm",
    "60 cm x 90 cm",
    "Pack of 2",
    "Queen",
    "King",
    "Multicolor",
    "Cotton",
    "₹529",
    "65% off",
    "Bank Offer",
    "Apply Coupon",
    "Free delivery",
    "Ratings",
    "Reviews",
    "Lowest price for you",
]

ACCEPTED_BADGE_TEXTS = [
    "Hot Deal",
    "Early Bird Deal",
    "Early Access",
    "Lowest Price in the Year",
    "Black Deal",
    "Special Deal",
    "Limited Time Deal",
    "Lowest Price",
    "Lowest Price since Launch",
    "Top Discount of the Sale",
]


@pytest.mark.parametrize("text", REJECTED_TEXTS)
def test_invalid_text_never_promotional(text: str) -> None:
    assert not is_promotional_badge_text(text)


@pytest.mark.parametrize(
    "text",
    [
        "72 inch x 36 inch",
        "72 cm x 46 cm",
        "60 cm x 90 cm",
        "Pack of 2",
        "Queen",
        "King",
        "Multicolor",
        "Cotton",
    ],
)
def test_dimension_or_variant_detection(text: str) -> None:
    assert is_dimension_or_variant_text(text)


@pytest.mark.parametrize("text", ["₹529", "65% off", "MRP ₹1,399"])
def test_price_or_discount_detection(text: str) -> None:
    assert is_price_or_discount_text(text)


@pytest.mark.parametrize("text", ["Bank Offer", "Apply Coupon", "Free delivery", "Ratings", "Reviews"])
def test_ui_offer_noise_detection(text: str) -> None:
    assert is_ui_or_offer_noise(text)


@pytest.mark.parametrize("text", ACCEPTED_BADGE_TEXTS)
def test_promotional_text_accepts_known_real_badges(text: str) -> None:
    assert is_promotional_badge_text(text)


def test_extract_promotional_badge_phrase_from_price_line() -> None:
    assert extract_promotional_badge_phrase("Hot Deal 57% 390 ₹166") == "Hot Deal"
    assert extract_promotional_badge_phrase("Lowest Price in the Year 61% ₹451") == "Lowest Price in the Year"
    assert extract_promotional_badge_phrase("Lowest Price since Launch 61% ₹451") == "Lowest Price since Launch"
    assert extract_promotional_badge_phrase("Lowest price for you ₹4,608") == ""
    assert extract_promotional_badge_phrase("Top Discount of the Sale 71% 5,000 ₹1,427") == "Top Discount of the Sale"
    assert extract_promotional_badge_phrase("Bank Offer 10% instant discount") == ""


def green_badge_candidate(text: str) -> dict[str, object]:
    return {
        "text": text,
        "visible": True,
        "bounding_box": {
            "left": 1110,
            "top": 530,
            "right": 1228,
            "bottom": 558,
            "width": 118,
            "height": 28,
        },
        "computed_style": {
            "backgroundColor": "rgb(0, 128, 66)",
            "color": "rgb(255, 255, 255)",
            "borderRadius": "4px",
            "fontWeight": "700",
            "paddingLeft": "8px",
            "paddingRight": "8px",
            "paddingTop": "3px",
            "paddingBottom": "3px",
        },
        "ancestor_styles": [],
        "context_text": "Product title 4.2 Ratings Hot Deal 63% ₹585 ₹219",
        "local_container_text": f"{text} 63% ₹585 ₹219",
    }


def white_variant_candidate(text: str) -> dict[str, object]:
    candidate = green_badge_candidate(text)
    candidate.update(
        {
            "bounding_box": {
                "left": 1110,
                "top": 280,
                "right": 1240,
                "bottom": 345,
                "width": 130,
                "height": 65,
            },
            "computed_style": {
                "backgroundColor": "rgb(255, 255, 255)",
                "color": "rgb(33, 33, 33)",
                "borderRadius": "8px",
                "fontWeight": "500",
                "paddingLeft": "8px",
                "paddingRight": "8px",
                "paddingTop": "8px",
                "paddingBottom": "8px",
            },
            "context_text": "Variant: 72 inch x 48 inch 72 inch x 36 inch 63% ₹1,199 ₹438",
            "local_container_text": "72 inch x 36 inch 63% ₹1,199 ₹438",
        }
    )
    return candidate


def price_block() -> dict[str, object]:
    return {
        "bounding_box": {
            "left": 1105,
            "top": 560,
            "right": 1420,
            "bottom": 630,
            "width": 315,
            "height": 70,
        },
        "new_price": "219",
        "old_price": "585",
        "discount_percentage": "63%",
    }


def test_visual_context_accepts_compact_green_badge() -> None:
    assert has_badge_visual_context(green_badge_candidate("Hot Deal"))


def test_visual_context_rejects_plain_variant_card() -> None:
    assert not has_badge_visual_context(white_variant_candidate("72 inch x 36 inch"))


def test_final_acceptance_requires_style_and_semantics() -> None:
    accepted, decisions, uncertain = evaluate_candidates([green_badge_candidate("Hot Deal")], price_block())
    assert accepted is not None
    assert accepted["text"] == "Hot Deal"
    assert decisions[0]["accepted"] is True
    assert uncertain is False


def test_final_acceptance_rejects_dimension_even_with_nearby_prices() -> None:
    accepted, decisions, _uncertain = evaluate_candidates(
        [white_variant_candidate("72 inch x 36 inch")],
        price_block(),
    )
    assert accepted is None
    assert decisions[0]["accepted"] is False
    assert decisions[0]["rejection_reason"] == "dimension/variant text"


def test_semantic_text_alone_is_not_enough() -> None:
    candidate = green_badge_candidate("Hot Deal")
    candidate["computed_style"] = {
        "backgroundColor": "rgba(0, 0, 0, 0)",
        "color": "rgb(33, 33, 33)",
        "borderRadius": "0px",
        "fontWeight": "400",
        "paddingLeft": "0px",
        "paddingRight": "0px",
        "paddingTop": "0px",
        "paddingBottom": "0px",
    }
    accepted, decisions, uncertain = evaluate_candidates([candidate], price_block())
    assert accepted is None
    assert decisions[0]["rejection_reason"] == "badge visual context not confirmed"
    assert uncertain is True


def test_price_block_fallback_accepts_embedded_hot_deal_badge() -> None:
    candidate = fallback_candidate_from_price_block(
        {
            "found": True,
            "text": "Hot Deal 57% 390 ₹166",
            "nearby_text": "Hot Deal 57% 390 ₹166 Buy at ₹116",
            "new_price": "166",
            "old_price": "390",
            "discount_percentage": "57%",
            "bounding_box": {
                "left": 1105,
                "top": 560,
                "right": 1420,
                "bottom": 630,
                "width": 315,
                "height": 70,
            },
        }
    )
    assert candidate is not None
    assert candidate["text"] == "Hot Deal"
    assert candidate["accepted"] is True


def test_price_block_fallback_rejects_plain_discount_without_badge_phrase() -> None:
    candidate = fallback_candidate_from_price_block(
        {
            "found": True,
            "text": "57% 390 ₹166",
            "nearby_text": "Bank Offer 57% 390 ₹166",
            "new_price": "166",
            "old_price": "390",
            "discount_percentage": "57%",
        }
    )
    assert candidate is None


def test_price_block_fallback_rejects_wow_lowest_price_for_you_offer() -> None:
    candidate = fallback_candidate_from_price_block(
        {
            "found": True,
            "text": "15% 5,999 ₹5,121",
            "nearby_text": "15% 5,999 ₹5,121 Buy at ₹4,608 Lowest price for you Apply offers for maximum savings",
            "new_price": "5,121",
            "old_price": "5,999",
            "discount_percentage": "15%",
        }
    )
    assert candidate is None


def test_price_block_fallback_still_accepts_real_lowest_price_badge_phrase() -> None:
    candidate = fallback_candidate_from_price_block(
        {
            "found": True,
            "text": "Lowest Price 15% 5,999 ₹5,121",
            "nearby_text": "Lowest Price 15% 5,999 ₹5,121",
            "new_price": "5,121",
            "old_price": "5,999",
            "discount_percentage": "15%",
        }
    )
    assert candidate is not None
    assert candidate["text"] == "Lowest Price"


def test_price_block_fallback_rejects_lowest_price_from_similar_products() -> None:
    candidate = fallback_candidate_from_price_block(
        {
            "found": True,
            "text": "1% 4,999 ₹4,949",
            "nearby_text": (
                "1% 4,999 ₹4,949 Buy at ₹4,701 Apply offers for maximum savings "
                "Similar Products Nima Small Grinder 85% OFF ₹2,899 ₹442 Lowest Price since Launch Get it by 10 Jul"
            ),
            "new_price": "4,949",
            "old_price": "4,999",
            "discount_percentage": "1%",
        }
    )
    assert candidate is None


def test_price_block_fallback_still_accepts_top_discount_badge_phrase() -> None:
    candidate = fallback_candidate_from_price_block(
        {
            "found": True,
            "text": "Top Discount of the Sale 71% 5,000 ₹1,427",
            "nearby_text": "Top Discount of the Sale 71% 5,000 ₹1,427 Buy at ₹1,151",
            "new_price": "1,427",
            "old_price": "5,000",
            "discount_percentage": "71%",
        }
    )
    assert candidate is not None
    assert candidate["text"] == "Top Discount of the Sale"


def test_visual_context_accepts_live_flipkart_white_text_child_pattern() -> None:
    candidate = green_badge_candidate("Hot Deal")
    candidate["computed_style"] = {
        "backgroundColor": "rgba(0, 0, 0, 0)",
        "color": "rgb(255, 255, 255)",
        "borderRadius": "0px",
        "fontWeight": "400",
        "display": "block",
        "paddingLeft": "0px",
        "paddingRight": "0px",
        "paddingTop": "0px",
        "paddingBottom": "0px",
    }
    candidate["ancestor_styles"] = [
        {
            "backgroundColor": "rgba(0, 0, 0, 0)",
            "color": "rgb(0, 0, 0)",
            "borderRadius": "0px",
            "fontWeight": "400",
            "display": "flex",
            "paddingLeft": "8px",
            "paddingRight": "8px",
            "paddingTop": "0px",
            "paddingBottom": "0px",
        },
        {
            "backgroundColor": "rgba(0, 0, 0, 0)",
            "color": "rgb(0, 0, 0)",
            "borderRadius": "4px",
            "fontWeight": "400",
            "display": "flex",
            "paddingLeft": "0px",
            "paddingRight": "0px",
            "paddingTop": "0px",
            "paddingBottom": "0px",
        },
    ]
    assert has_badge_visual_context(candidate)
