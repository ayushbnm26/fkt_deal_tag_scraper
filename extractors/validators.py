from __future__ import annotations

import math
import re
from typing import Any


DIMENSION_PATTERNS = [
    re.compile(
        r"\b\d+(?:\.\d+)?\s*(?:inch|inches|in\.?|cm|mm|m|meter|metre|ft|feet)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b\d+(?:\.\d+)?\s*(?:inch|inches|in\.?|cm|mm|m|meter|metre|ft|feet)?\s*[x×]\s*"
        r"\d+(?:\.\d+)?(?:\s*(?:inch|inches|in\.?|cm|mm|m|meter|metre|ft|feet))?\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b\d+\s*[x×]\s*\d+\b", re.IGNORECASE),
]

SIZE_WORDS = {
    "xs",
    "s",
    "m",
    "l",
    "xl",
    "xxl",
    "small",
    "medium",
    "large",
    "single",
    "double",
    "queen",
    "king",
    "full",
    "twin",
    "standard",
}

COLOR_WORDS = {
    "black",
    "white",
    "blue",
    "green",
    "red",
    "yellow",
    "pink",
    "purple",
    "brown",
    "grey",
    "gray",
    "orange",
    "maroon",
    "beige",
    "cream",
    "silver",
    "gold",
    "multicolor",
    "multi color",
    "multi-color",
    "navy",
}

MATERIAL_WORDS = {
    "cotton",
    "polyester",
    "plastic",
    "wood",
    "wooden",
    "steel",
    "stainless steel",
    "iron",
    "aluminium",
    "aluminum",
    "rubber",
    "silicone",
    "leather",
    "fabric",
    "terry",
    "microfiber",
    "foam",
}

UI_NOISE_PATTERNS = [
    re.compile(r"\badd\s*to\s*cart\b", re.IGNORECASE),
    re.compile(r"\bbuy\s*now\b", re.IGNORECASE),
    re.compile(r"\bbuy\s+at\b", re.IGNORECASE),
    re.compile(r"\blogin\b", re.IGNORECASE),
    re.compile(r"\bdelivery\b", re.IGNORECASE),
    re.compile(r"\bfree\s+delivery\b", re.IGNORECASE),
    re.compile(r"\bpincode\b|\bcheck\s+availability\b|\blocation\b", re.IGNORECASE),
    re.compile(r"\bsold\s+by\b|\bseller\b", re.IGNORECASE),
    re.compile(r"\bratings?\b|\breviews?\b", re.IGNORECASE),
    re.compile(r"\bquestions?\b|\banswers?\b", re.IGNORECASE),
    re.compile(r"\bshare\b|\bcompare\b|\bwishlist\b", re.IGNORECASE),
    re.compile(r"\bhighlights?\b|\bspecifications?\b", re.IGNORECASE),
]

OFFER_NOISE_PATTERNS = [
    re.compile(r"\bbank\s+offer\b", re.IGNORECASE),
    re.compile(r"\bcoupons?\b|\bapply\s+coupon\b", re.IGNORECASE),
    re.compile(r"\bexchange\b", re.IGNORECASE),
    re.compile(r"\bemi\b", re.IGNORECASE),
    re.compile(r"\bcashback\b", re.IGNORECASE),
    re.compile(r"\bapply\s+offers?\b", re.IGNORECASE),
    re.compile(r"\bmaximum\s+savings?\b", re.IGNORECASE),
    re.compile(r"\blowest\s+price\s+for\s+you\b", re.IGNORECASE),
]

BAD_CONTEXT_PATTERNS = [
    re.compile(r"\bsimilar\s+products?\b", re.IGNORECASE),
    re.compile(r"\bsponsored\b|\bad\b", re.IGNORECASE),
    re.compile(r"\bcustomers?\s+also\b|\brecommend", re.IGNORECASE),
    re.compile(r"\breviews?\b|\bratings?\b", re.IGNORECASE),
    re.compile(r"\bdelivery\s+details?\b", re.IGNORECASE),
    re.compile(r"\bselected\s+(?:pack|size|color)\b|\bvariant\b", re.IGNORECASE),
    re.compile(r"\bcombo\b|\bfrequently\s+bought\b", re.IGNORECASE),
    re.compile(r"\bbank\s+offer\b|\bapply\s+offers?\b|\bcoupon\b", re.IGNORECASE),
]

PROMOTIONAL_PATTERNS = [
    (re.compile(r"\bhot\b", re.IGNORECASE), 2, "hot"),
    (re.compile(r"\bdeal\b", re.IGNORECASE), 4, "deal"),
    (re.compile(r"\bearly\b", re.IGNORECASE), 2, "early"),
    (re.compile(r"\baccess\b", re.IGNORECASE), 2, "access"),
    (re.compile(r"\bbird\b", re.IGNORECASE), 2, "bird"),
    (re.compile(r"\bblack\s+deal\b", re.IGNORECASE), 4, "black deal"),
    (re.compile(r"\blowest\s+price(?:\s+in\s+the\s+year)?\b", re.IGNORECASE), 5, "lowest price"),
    (re.compile(r"\bprice\s+drop\b", re.IGNORECASE), 4, "price drop"),
    (re.compile(r"\bspecial\s+deal\b", re.IGNORECASE), 4, "special deal"),
    (re.compile(r"\blimited(?:\s+time)?\s+deal\b", re.IGNORECASE), 4, "limited deal"),
    (re.compile(r"\btop\s+discount(?:\s+of\s+the\s+sale)?\b", re.IGNORECASE), 5, "top discount"),
    (re.compile(r"\bsuper\s+saver\b", re.IGNORECASE), 4, "super saver"),
    (re.compile(r"\bbig\s+sav(?:ing|er|ings)\b", re.IGNORECASE), 3, "big saving"),
    (re.compile(r"\bflash\b", re.IGNORECASE), 2, "flash"),
    (re.compile(r"\bfestive\b", re.IGNORECASE), 2, "festive"),
    (re.compile(r"\bsteal\b", re.IGNORECASE), 3, "steal"),
    (re.compile(r"\bsale\b", re.IGNORECASE), 2, "sale"),
]

PROMOTIONAL_BADGE_PHRASES = [
    (re.compile(r"\bearly\s+bird\s+deals?\b", re.IGNORECASE), "Early Bird Deal"),
    (re.compile(r"\blowest\s+price\s+in\s+the\s+year\b", re.IGNORECASE), "Lowest Price in the Year"),
    (re.compile(r"\blowest\s+price\s+since\s+launch\b", re.IGNORECASE), "Lowest Price since Launch"),
    (re.compile(r"\blimited\s+time\s+deals?\b", re.IGNORECASE), "Limited Time Deal"),
    (re.compile(r"\bdeal\s+of\s+the\s+day\b", re.IGNORECASE), "Deal of the Day"),
    (re.compile(r"\btop\s+discount\s+of\s+the\s+sale\b", re.IGNORECASE), "Top Discount of the Sale"),
    (re.compile(r"\bearly\s+access\b", re.IGNORECASE), "Early Access"),
    (re.compile(r"\bblack\s+deals?\b", re.IGNORECASE), "Black Deal"),
    (re.compile(r"\bspecial\s+deals?\b", re.IGNORECASE), "Special Deal"),
    (re.compile(r"\blimited\s+deals?\b", re.IGNORECASE), "Limited Deal"),
    (re.compile(r"\blowest\s+price(?!\s+for\s+you)\b", re.IGNORECASE), "Lowest Price"),
    (re.compile(r"\bprice\s+drop\b", re.IGNORECASE), "Price Drop"),
    (re.compile(r"\bsuper\s+saver\b", re.IGNORECASE), "Super Saver"),
    (re.compile(r"\bbig\s+sav(?:ing|er|ings)\b", re.IGNORECASE), "Big Saving"),
    (re.compile(r"\bflash\s+deals?\b", re.IGNORECASE), "Flash Deal"),
    (re.compile(r"\bfestive\s+deals?\b", re.IGNORECASE), "Festive Deal"),
    (re.compile(r"\bhot\s+deals?\b", re.IGNORECASE), "Hot Deal"),
]


def normalize_text(text: str) -> str:
    cleaned = "" if text is None else str(text)
    cleaned = cleaned.replace("\u00a0", " ")
    cleaned = cleaned.replace("\u200b", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _lower(text: str) -> str:
    return normalize_text(text).lower()


def is_dimension_or_variant_text(text: str) -> bool:
    value = normalize_text(text)
    lowered = value.lower()
    if not lowered:
        return False

    for pattern in DIMENSION_PATTERNS:
        if pattern.search(value):
            return True

    if re.search(r"\bpack\s*of\s*\d+\b", value, re.IGNORECASE):
        return True
    if re.search(r"\b\d+\s*(?:pcs|piece|pieces|set|sets|kg|g|gm|ml|l|litre|liter)\b", value, re.IGNORECASE):
        return True

    tokenized = re.sub(r"[^a-z0-9+ -]", " ", lowered)
    tokenized = re.sub(r"\s+", " ", tokenized).strip()
    if tokenized in SIZE_WORDS or tokenized in COLOR_WORDS or tokenized in MATERIAL_WORDS:
        return True

    words = set(tokenized.split())
    if words and words.issubset(SIZE_WORDS | COLOR_WORDS | MATERIAL_WORDS | {"and", "&", "of"}):
        return True

    if re.search(r"\b(?:size|color|colour|material|variant|selected pack|selected size)\b", lowered):
        return True

    return False


def is_price_or_discount_text(text: str) -> bool:
    value = normalize_text(text)
    lowered = value.lower()
    if not lowered:
        return False

    if re.search(r"₹\s*[\d,]+", value):
        return True
    if re.fullmatch(r"[\d,]+(?:\.\d+)?", value):
        return True
    if re.search(r"\b\d{1,3}\s*%\s*(?:off)?\b", value, re.IGNORECASE):
        return True
    if re.fullmatch(r"(?:special\s+price|mrp|list\s+price|selling\s+price|inclusive\s+of\s+all\s+taxes)", lowered):
        return True
    if re.search(r"\b(?:mrp|inclusive of all taxes|off\b|discount)\b", lowered) and re.search(r"\d", lowered):
        return True
    return False


def is_ui_or_offer_noise(text: str) -> bool:
    value = normalize_text(text)
    if not value:
        return False
    return any(pattern.search(value) for pattern in UI_NOISE_PATTERNS + OFFER_NOISE_PATTERNS)


def positive_deal_score(text: str) -> int:
    value = normalize_text(text)
    if not value:
        return 0
    score = 0
    for pattern, points, _name in PROMOTIONAL_PATTERNS:
        if pattern.search(value):
            score += points
    if re.search(r"\bearly\s+bird\s+deal\b", value, re.IGNORECASE):
        score += 3
    if re.search(r"\bearly\s+access\b", value, re.IGNORECASE):
        score += 3
    return score


def positive_deal_signals(text: str) -> list[str]:
    value = normalize_text(text)
    signals: list[str] = []
    for pattern, _points, name in PROMOTIONAL_PATTERNS:
        if pattern.search(value):
            signals.append(name)
    if re.search(r"\bearly\s+bird\s+deal\b", value, re.IGNORECASE):
        signals.append("early bird deal")
    if re.search(r"\bearly\s+access\b", value, re.IGNORECASE):
        signals.append("early access")
    return sorted(set(signals))


def extract_promotional_badge_phrase(text: str) -> str:
    value = normalize_text(text)
    if not value:
        return ""

    matches: list[tuple[int, int, str]] = []
    for pattern, canonical in PROMOTIONAL_BADGE_PHRASES:
        match = pattern.search(value)
        if match:
            matches.append((match.start(), -len(match.group(0)), canonical))

    if not matches:
        return ""
    matches.sort()
    return matches[0][2]


def negative_noise_score(text: str) -> int:
    value = normalize_text(text)
    if not value:
        return 10

    score = 0
    if len(value) < 3 or len(value) > 60:
        score += 5
    if len(value.split()) > 8:
        score += 4
    if not re.search(r"[A-Za-z]", value):
        score += 8
    if is_dimension_or_variant_text(value):
        score += 10
    if is_price_or_discount_text(value):
        score += 10
    if is_ui_or_offer_noise(value):
        score += 8

    digit_count = len(re.findall(r"\d", value))
    if digit_count >= 3 and not re.search(r"\blowest\s+price\s+in\s+the\s+year\b", value, re.IGNORECASE):
        score += 4

    return score


def negative_noise_signals(text: str) -> list[str]:
    signals: list[str] = []
    value = normalize_text(text)
    if len(value) < 3:
        signals.append("too short")
    if len(value) > 60 or len(value.split()) > 8:
        signals.append("too long for badge")
    if value and not re.search(r"[A-Za-z]", value):
        signals.append("no alphabetic text")
    if is_dimension_or_variant_text(value):
        signals.append("dimension/variant text")
    if is_price_or_discount_text(value):
        signals.append("price/discount text")
    if is_ui_or_offer_noise(value):
        signals.append("ui/offer noise")
    if len(re.findall(r"\d", value)) >= 3:
        signals.append("too many numbers")
    return signals


def is_promotional_badge_text(text: str) -> bool:
    value = normalize_text(text)
    if not value:
        return False
    if negative_noise_score(value) > 0:
        return False
    return positive_deal_score(value) >= 3


def _parse_rgb(value: str) -> tuple[int, int, int, float] | None:
    match = re.search(
        r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?:\s*,\s*([\d.]+))?\s*\)",
        value or "",
        re.IGNORECASE,
    )
    if not match:
        return None
    r, g, b = (int(match.group(i)) for i in range(1, 4))
    alpha = float(match.group(4)) if match.group(4) is not None else 1.0
    return r, g, b, alpha


def _is_transparent(color: str) -> bool:
    color = (color or "").strip().lower()
    if not color or color == "transparent":
        return True
    rgb = _parse_rgb(color)
    return bool(rgb and rgb[3] <= 0.05)


def _is_non_white_badge_color(color: str) -> bool:
    rgb = _parse_rgb(color)
    if not rgb:
        return False
    r, g, b, alpha = rgb
    if alpha < 0.25:
        return False
    if r >= 235 and g >= 235 and b >= 235:
        return False
    return True


def _is_flipkart_deal_green(color: str) -> bool:
    rgb = _parse_rgb(color)
    if not rgb:
        return False
    r, g, b, alpha = rgb
    if alpha < 0.25:
        return False
    return r <= 30 and 95 <= g <= 160 and 35 <= b <= 100


def _as_rect(element: dict[str, Any]) -> dict[str, float]:
    rect = element.get("bounding_box") or element.get("bbox") or element.get("rect") or {}
    return {
        "x": float(rect.get("x", rect.get("left", 0)) or 0),
        "y": float(rect.get("y", rect.get("top", 0)) or 0),
        "width": float(rect.get("width", 0) or 0),
        "height": float(rect.get("height", 0) or 0),
        "left": float(rect.get("left", rect.get("x", 0)) or 0),
        "top": float(rect.get("top", rect.get("y", 0)) or 0),
        "right": float(rect.get("right", 0) or 0),
        "bottom": float(rect.get("bottom", 0) or 0),
    }


def _style_layers(element: dict[str, Any]) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    style = element.get("computed_style") or element.get("style_summary") or element.get("style") or {}
    if isinstance(style, dict):
        layers.append(style)
    ancestors = element.get("ancestor_styles") or []
    for ancestor in ancestors:
        if isinstance(ancestor, dict):
            layers.append(ancestor)
    return layers


def has_badge_visual_context(element: dict[str, Any]) -> bool:
    if not isinstance(element, dict):
        return False
    if element.get("visible") is False:
        return False

    rect = _as_rect(element)
    width = rect["width"]
    height = rect["height"]
    if width <= 0 or height <= 0:
        return False
    if width > 320 or height > 90:
        return False

    text = normalize_text(str(element.get("text") or element.get("candidate_text") or ""))
    if text and (len(text) > 60 or len(text.split()) > 8):
        return False

    visual_score = 0
    compact_white_text_score = 0
    has_white_text = False
    has_compact_shape = False
    for style in _style_layers(element):
        background = str(style.get("backgroundColor") or style.get("background") or "")
        pseudo_backgrounds = [
            str(style.get("beforeBackgroundColor") or ""),
            str(style.get("afterBackgroundColor") or ""),
        ]
        color = str(style.get("color") or "")
        border_radius = _to_float(style.get("borderRadius"))
        font_weight = _to_float(style.get("fontWeight"))
        padding_x = _to_float(style.get("paddingLeft")) + _to_float(style.get("paddingRight"))
        padding_y = _to_float(style.get("paddingTop")) + _to_float(style.get("paddingBottom"))
        display = str(style.get("display") or "").lower()

        if _is_flipkart_deal_green(background):
            visual_score += 5
        elif _is_non_white_badge_color(background):
            visual_score += 3
        for pseudo_background in pseudo_backgrounds:
            if _is_flipkart_deal_green(pseudo_background):
                visual_score += 5
            elif _is_non_white_badge_color(pseudo_background):
                visual_score += 3
        if border_radius >= 2:
            visual_score += 1
        if padding_x >= 4 and padding_y >= 2:
            visual_score += 1
        if font_weight >= 600:
            visual_score += 1
        if not _is_transparent(background) and _is_non_white_badge_color(background):
            visual_score += 1
        color_rgb = _parse_rgb(color)
        is_white_text = bool(color_rgb and color_rgb[0] >= 235 and color_rgb[1] >= 235 and color_rgb[2] >= 235)
        has_white_text = has_white_text or is_white_text
        has_compact_shape = has_compact_shape or border_radius >= 4 or padding_x >= 8 or display in {"flex", "inline-flex"}
        if is_white_text and (border_radius >= 4 or padding_x >= 8 or display in {"flex", "inline-flex"}):
            compact_white_text_score += 3

    # Flipkart's current web component sometimes paints the badge surface through
    # generated/atomic CSS while the text node reports a transparent background.
    # Keep this as a visual rule only; text/variant rejection runs before it.
    return visual_score >= 4 or compact_white_text_score >= 3 or (has_white_text and has_compact_shape)


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(float(value)) else 0.0
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    if not match:
        return 0.0
    return float(match.group(0))


def is_inside_bad_context(element: dict[str, Any]) -> bool:
    if not isinstance(element, dict):
        return True

    context_values = [
        element.get("context_text", ""),
        element.get("ancestor_text", ""),
        element.get("dom_path", ""),
        " ".join(str(x) for x in element.get("context_labels", []) or []),
    ]
    context = normalize_text(" ".join(str(value) for value in context_values if value))
    text = normalize_text(str(element.get("text") or ""))

    for pattern in BAD_CONTEXT_PATTERNS:
        if pattern.search(context):
            if pattern.pattern.find("variant") >= 0 or "selected" in pattern.pattern:
                return True
            if text and pattern.search(text):
                return True
            local_text = normalize_text(str(element.get("local_container_text", "")))
            if local_text and pattern.search(local_text):
                return True

    if re.search(r"\bbuy\s+at\b|\bapply\s+offers?\b|\bmaximum\s+savings?\b", context, re.IGNORECASE):
        return True

    return False


def is_near_primary_price_block(element: dict[str, Any], price_block: dict[str, Any]) -> bool:
    if not isinstance(element, dict) or not isinstance(price_block, dict):
        return False
    if not price_block:
        return False

    candidate = _as_rect(element)
    price_rect = _as_rect(price_block)
    if candidate["width"] <= 0 or candidate["height"] <= 0 or price_rect["width"] <= 0 or price_rect["height"] <= 0:
        return False

    horizontal_overlap = min(candidate["right"], price_rect["right"] + 80) - max(candidate["left"], price_rect["left"] - 80)
    horizontal_ok = horizontal_overlap > 0 or abs(candidate["left"] - price_rect["left"]) <= 220

    candidate_center_y = (candidate["top"] + candidate["bottom"]) / 2
    price_center_y = (price_rect["top"] + price_rect["bottom"]) / 2
    vertical_distance = abs(candidate_center_y - price_center_y)

    above_price = candidate["bottom"] <= price_rect["top"] + 12 and price_rect["top"] - candidate["bottom"] <= 180
    same_band = vertical_distance <= 150
    slightly_below = candidate["top"] >= price_rect["top"] and candidate["top"] <= price_rect["bottom"] + 70

    return horizontal_ok and (above_price or same_band or slightly_below)


def classify_candidate_text(text: str) -> dict[str, Any]:
    normalized = normalize_text(text)
    positives = positive_deal_signals(normalized)
    negatives = negative_noise_signals(normalized)
    return {
        "normalized_text": normalized,
        "positive_score": positive_deal_score(normalized),
        "negative_score": negative_noise_score(normalized),
        "positive_signals": positives,
        "negative_signals": negatives,
        "is_promotional_text": is_promotional_badge_text(normalized),
    }
