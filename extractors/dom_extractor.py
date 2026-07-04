from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from playwright.async_api import Page

from config import STATUS_FOUND, STATUS_NO_TAG, STATUS_PARTIAL, STATUS_UNCERTAIN, build_url
from extractors.price_parser import clean_price_block
from extractors.validators import (
    classify_candidate_text,
    extract_promotional_badge_phrase,
    has_badge_visual_context,
    is_inside_bad_context,
    is_near_primary_price_block,
    is_promotional_badge_text,
    normalize_text,
)
from models import ScrapeResult


PRIMARY_PRICE_BLOCK_JS = r"""
() => {
  const clean = (value) => (value || "").replace(/\s+/g, " ").trim();
  const rupeeRegex = /₹\s*[\d,]+/;
  const percentRegex = /(?:↓\s*)?\b(\d{1,3})\s*%/;

  const isVisible = (el) => {
    if (!el || !(el instanceof Element)) return false;
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== "none" &&
      style.visibility !== "hidden" &&
      Number(style.opacity || "1") > 0.05 &&
      rect.width > 0 &&
      rect.height > 0;
  };

  const textOf = (el) => clean(el.innerText || el.textContent || "");

  const hasLineThrough = (el) => {
    if (!el) return false;
    const style = window.getComputedStyle(el);
    return /line-through/i.test(`${style.textDecoration || ""} ${style.textDecorationLine || ""}`);
  };

  const rectOf = (el) => {
    const rect = el.getBoundingClientRect();
    return {
      x: rect.x,
      y: rect.y,
      left: rect.left,
      top: rect.top,
      right: rect.right,
      bottom: rect.bottom,
      width: rect.width,
      height: rect.height
    };
  };

  const moneyValue = (text) => {
    const match = clean(text).match(/₹?\s*(\d[\d,]*)/);
    return match ? Number(match[1].replace(/,/g, "")) : NaN;
  };

  const moneyText = (text) => {
    const match = clean(text).match(/₹\s*(\d[\d,]*)/);
    return match ? match[1] : "";
  };

  const styleScore = (el) => {
    const style = window.getComputedStyle(el);
    const fontSize = parseFloat(style.fontSize || "0") || 0;
    const fontWeight = parseInt(style.fontWeight || "0", 10) || 0;
    return { fontSize, fontWeight };
  };

  const localContext = (el, maxDepth = 5) => {
    let current = el;
    const parts = [];
    for (let depth = 0; current && depth < maxDepth; depth += 1) {
      const rect = current.getBoundingClientRect();
      const text = textOf(current);
      if (text && rect.height <= 420 && text.length <= 1200) parts.push(text);
      current = current.parentElement;
    }
    return clean(parts.join(" "));
  };

  const isBadPriceContext = (el) => {
    const context = localContext(el, 5);
    if (/\b(?:similar products|sponsored|ad|advertisement|customers also|recommend|reviews|ratings|combo|view similar)\b/i.test(context)) {
      return true;
    }
    if (/\b(?:buy at|apply offers?|maximum savings|add to cart|delivery details|bank offer|coupon|notify me)\b/i.test(context)) {
      return true;
    }
    return false;
  };

  const visible = Array.from(document.querySelectorAll("body *")).filter(isVisible);
  const rupeeElements = visible
    .map((el) => {
      const text = textOf(el);
      const rect = rectOf(el);
      const style = styleScore(el);
      const value = moneyValue(text);
      return { el, text, rect, style, value };
    })
    .filter((item) =>
      item.text.length <= 90 &&
      rupeeRegex.test(item.text) &&
      Number.isFinite(item.value) &&
      item.value > 0 &&
      !hasLineThrough(item.el) &&
      !isBadPriceContext(item.el)
    );

  const candidates = rupeeElements.map((item) => {
    const nearbyText = visible
      .filter((el) => {
        const rect = el.getBoundingClientRect();
        return rect.top >= item.rect.top - 110 &&
          rect.top <= item.rect.bottom + 120 &&
          rect.left <= item.rect.right + 420 &&
          rect.right >= item.rect.left - 160;
      })
      .map(textOf)
      .join(" ");

    let score = 0;
    if (item.style.fontSize >= 24) score += 6;
    if (item.style.fontSize >= 30) score += 4;
    if (item.style.fontWeight >= 600) score += 2;
    if (percentRegex.test(nearbyText)) score += 5;
    if (nearbyText.match(/₹\s*[\d,]+/g)?.length >= 2) score += 3;
    if (item.rect.top < 950) score += 3;
    if (item.rect.top < 180) score -= 2;
    if (item.rect.width > 240 || item.rect.height > 80) score -= 2;
    return { ...item, nearbyText, score };
  });

  candidates.sort((a, b) => b.score - a.score || b.style.fontSize - a.style.fontSize || a.rect.top - b.rect.top);
  const best = candidates[0];
  if (!best) {
    return { found: false, reason: "primary selling price not found", candidates: [] };
  }

  const nearbyElements = visible.filter((el) => {
    const rect = el.getBoundingClientRect();
    return rect.top >= best.rect.top - 130 &&
      rect.top <= best.rect.bottom + 130 &&
      rect.left <= best.rect.right + 480 &&
      rect.right >= best.rect.left - 180;
  });
  const nearbyText = clean(nearbyElements.map(textOf).join(" "));

  const strikeCandidates = nearbyElements
    .map((el) => ({ el, text: textOf(el), rect: rectOf(el), value: moneyValue(textOf(el)) }))
    .filter((item) => item.text.length <= 90 && rupeeRegex.test(item.text) && hasLineThrough(item.el) && Number.isFinite(item.value));
  strikeCandidates.sort((a, b) => b.value - a.value || a.rect.top - b.rect.top);

  const percentMatch = nearbyText.match(percentRegex);
  const oldPrice = strikeCandidates[0] ? moneyText(strikeCandidates[0].text) : "";
  const sequence = nearbyText.match(/(?:↓\s*)?(\d{1,3})\s*%[^₹]{0,20}₹?\s*(\d[\d,]*)[^₹]{0,20}₹\s*(\d[\d,]*)/);

  let parsedOld = oldPrice;
  let parsedNew = moneyText(best.text);
  let parsedDiscount = percentMatch ? `${percentMatch[1]}%` : "";
  if (sequence) {
    const oldValue = Number(sequence[2].replace(/,/g, ""));
    const newValue = Number(sequence[3].replace(/,/g, ""));
    if (Number.isFinite(oldValue) && Number.isFinite(newValue) && oldValue > newValue) {
      parsedDiscount = parsedDiscount || `${sequence[1]}%`;
      parsedOld = parsedOld || sequence[2];
      parsedNew = parsedNew || sequence[3];
    }
  }

  let container = best.el;
  for (let current = best.el; current; current = current.parentElement) {
    const text = textOf(current);
    const rect = current.getBoundingClientRect();
    if (
      text.includes(best.text) &&
      text.length <= 900 &&
      rect.height <= 360 &&
      rect.width <= 900 &&
      (percentRegex.test(text) || rupeeRegex.test(text))
    ) {
      container = current;
    }
  }

  const pathOf = (el) => {
    const parts = [];
    let current = el;
    while (current && current.nodeType === Node.ELEMENT_NODE && parts.length < 8) {
      let part = current.tagName.toLowerCase();
      if (current.id) part += `#${current.id}`;
      const className = String(current.className || "").trim().split(/\s+/).filter(Boolean).slice(0, 3).join(".");
      if (className) part += `.${className}`;
      parts.unshift(part);
      current = current.parentElement;
    }
    return parts.join(" > ");
  };

  return {
    found: true,
    reason: "primary price block found",
    new_price: parsedNew,
    old_price: parsedOld,
    discount_percentage: parsedDiscount,
    text: textOf(container),
    bounding_box: rectOf(container),
    selling_price_box: best.rect,
    dom_path: pathOf(container),
    nearby_text: nearbyText
  };
}
"""


DEAL_CANDIDATE_JS = r"""
(priceBlock) => {
  const clean = (value) => (value || "").replace(/\s+/g, " ").trim();
  const isVisible = (el) => {
    if (!el || !(el instanceof Element)) return false;
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== "none" &&
      style.visibility !== "hidden" &&
      Number(style.opacity || "1") > 0.05 &&
      rect.width > 0 &&
      rect.height > 0;
  };
  const textOf = (el) => clean(el.innerText || el.textContent || "");
  const rectOf = (el) => {
    const rect = el.getBoundingClientRect();
    return {
      x: rect.x,
      y: rect.y,
      left: rect.left,
      top: rect.top,
      right: rect.right,
      bottom: rect.bottom,
      width: rect.width,
      height: rect.height
    };
  };
  const styleOf = (el) => {
    const style = window.getComputedStyle(el);
    const beforeStyle = window.getComputedStyle(el, "::before");
    const afterStyle = window.getComputedStyle(el, "::after");
    return {
      tagName: el.tagName.toLowerCase(),
      className: String(el.className || ""),
      backgroundColor: style.backgroundColor,
      background: style.background,
      beforeBackgroundColor: beforeStyle.backgroundColor,
      afterBackgroundColor: afterStyle.backgroundColor,
      color: style.color,
      borderColor: style.borderColor,
      borderRadius: style.borderRadius,
      fontSize: style.fontSize,
      fontWeight: style.fontWeight,
      display: style.display,
      paddingLeft: style.paddingLeft,
      paddingRight: style.paddingRight,
      paddingTop: style.paddingTop,
      paddingBottom: style.paddingBottom,
      textDecoration: style.textDecoration,
      textDecorationLine: style.textDecorationLine
    };
  };
  const pathOf = (el) => {
    const parts = [];
    let current = el;
    while (current && current.nodeType === Node.ELEMENT_NODE && parts.length < 9) {
      let part = current.tagName.toLowerCase();
      if (current.id) part += `#${current.id}`;
      const className = String(current.className || "").trim().split(/\s+/).filter(Boolean).slice(0, 3).join(".");
      if (className) part += `.${className}`;
      parts.unshift(part);
      current = current.parentElement;
    }
    return parts.join(" > ");
  };
  const ancestorStyles = (el) => {
    const layers = [];
    let current = el.parentElement;
    for (let depth = 0; current && depth < 5; depth += 1) {
      const rect = current.getBoundingClientRect();
      const text = textOf(current);
      layers.push({
        ...styleOf(current),
        bounding_box: rectOf(current),
        text_length: text.length
      });
      current = current.parentElement;
    }
    return layers;
  };
  const nearestLocalText = (el) => {
    let current = el;
    for (let depth = 0; current && depth < 5; depth += 1) {
      const rect = current.getBoundingClientRect();
      const text = textOf(current);
      if (text.length > 0 && text.length <= 700 && rect.height <= 260) return text;
      current = current.parentElement;
    }
    return textOf(el);
  };
  const ancestorText = (el) => {
    const parts = [];
    let current = el.parentElement;
    for (let depth = 0; current && depth < 6; depth += 1) {
      const rect = current.getBoundingClientRect();
      const text = textOf(current);
      if (text.length <= 1200 && rect.height <= 420) parts.push(text);
      current = current.parentElement;
    }
    return clean(parts.join(" "));
  };
  const visible = Array.from(document.querySelectorAll("body *")).filter(isVisible);
  const priceRect = priceBlock && (priceBlock.bounding_box || priceBlock.bbox || priceBlock.rect);
  const hasPriceRect = priceRect && priceRect.width > 0 && priceRect.height > 0;
  const priceTop = hasPriceRect ? priceRect.top : 0;
  const priceBottom = hasPriceRect ? priceRect.bottom : window.innerHeight;
  const priceLeft = hasPriceRect ? priceRect.left : 0;
  const priceRight = hasPriceRect ? priceRect.right : window.innerWidth;

  const candidates = [];
  for (const el of visible) {
    const text = textOf(el);
    if (!text || text.length < 3 || text.length > 80) continue;
    if ((text.match(/\n/g) || []).length > 1) continue;
    if (!/[A-Za-z]/.test(text)) continue;

    const rect = rectOf(el);
    if (rect.width <= 0 || rect.height <= 0 || rect.width > 340 || rect.height > 100) continue;

    if (hasPriceRect) {
      const horizontalOverlap = Math.min(rect.right, priceRight + 120) - Math.max(rect.left, priceLeft - 120);
      const horizontallyRelevant = horizontalOverlap > 0 || Math.abs(rect.left - priceLeft) <= 260;
      const verticallyRelevant =
        (rect.bottom <= priceTop + 20 && priceTop - rect.bottom <= 220) ||
        Math.abs(((rect.top + rect.bottom) / 2) - ((priceTop + priceBottom) / 2)) <= 180 ||
        (rect.top >= priceTop && rect.top <= priceBottom + 90);
      if (!horizontallyRelevant || !verticallyRelevant) continue;
    }

    const children = Array.from(el.children || []).filter(isVisible);
    const childText = clean(children.map(textOf).join(" "));
    if (children.length > 4 && childText.length > text.length * 0.8) continue;

    candidates.push({
      text,
      raw_text: text,
      visible: true,
      bounding_box: rect,
      computed_style: styleOf(el),
      ancestor_styles: ancestorStyles(el),
      dom_path: pathOf(el),
      context_text: ancestorText(el),
      local_container_text: nearestLocalText(el),
      page_y: window.scrollY,
      viewport: { width: window.innerWidth, height: window.innerHeight }
    });
  }

  return {
    candidates,
    page_title: document.title,
    url: location.href
  };
}
"""


async def extract_primary_price_block(page: Page) -> dict[str, Any]:
    raw = await page.evaluate(PRIMARY_PRICE_BLOCK_JS)
    if not raw or not raw.get("found"):
        return raw or {"found": False, "reason": "primary price block script returned no data"}
    return clean_price_block(raw)


async def collect_deal_candidates(page: Page, price_block: dict[str, Any]) -> dict[str, Any]:
    return await page.evaluate(DEAL_CANDIDATE_JS, price_block)


def _candidate_distance(candidate: dict[str, Any], price_block: dict[str, Any]) -> float:
    c = candidate.get("bounding_box") or {}
    p = price_block.get("bounding_box") or {}
    cy = ((c.get("top", 0) or 0) + (c.get("bottom", 0) or 0)) / 2
    py = ((p.get("top", 0) or 0) + (p.get("bottom", 0) or 0)) / 2
    cx = ((c.get("left", 0) or 0) + (c.get("right", 0) or 0)) / 2
    px = ((p.get("left", 0) or 0) + (p.get("right", 0) or 0)) / 2
    return abs(cy - py) + (abs(cx - px) * 0.2)


def evaluate_candidates(
    raw_candidates: list[dict[str, Any]],
    price_block: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], bool]:
    decisions: list[dict[str, Any]] = []
    uncertain = False

    for candidate in raw_candidates:
        text = normalize_text(str(candidate.get("text") or ""))
        candidate["text"] = text
        classification = classify_candidate_text(text)
        decision = {
            **candidate,
            **classification,
            "accepted": False,
            "rejection_reason": "",
        }

        if not is_promotional_badge_text(text):
            reason = classification["negative_signals"][0] if classification["negative_signals"] else "insufficient promotional language"
            decision["rejection_reason"] = reason
            decisions.append(decision)
            continue

        if is_inside_bad_context(candidate):
            decision["rejection_reason"] = "bad product-page context"
            decisions.append(decision)
            continue

        if not has_badge_visual_context(candidate):
            decision["rejection_reason"] = "badge visual context not confirmed"
            uncertain = True
            decisions.append(decision)
            continue

        if not is_near_primary_price_block(candidate, price_block):
            decision["rejection_reason"] = "not near primary price block"
            decisions.append(decision)
            continue

        decision["accepted"] = True
        decision["rejection_reason"] = ""
        decision["distance_to_price"] = _candidate_distance(candidate, price_block)
        decisions.append(decision)

    accepted = [item for item in decisions if item["accepted"]]
    accepted.sort(
        key=lambda item: (
            item.get("distance_to_price", 9999),
            -int(item.get("positive_score", 0)),
            len(item.get("text", "")),
        )
    )
    return (accepted[0] if accepted else None), decisions, uncertain


def _has_price_context(text: str, phrase: str) -> bool:
    if not text or not phrase:
        return False
    index = text.lower().find(phrase.lower())
    if index < 0:
        return False
    window = text[max(0, index - 80) : index + len(phrase) + 120]
    return bool(re.search(r"₹\s*[\d,]+|\b\d{1,3}\s*%", window))


def _is_unsafe_nearby_fallback(source: str, text: str, phrase: str) -> bool:
    if source != "primary_price_nearby_text":
        return False

    lowered_phrase = phrase.lower()
    if lowered_phrase in {"lowest price", "lowest price since launch"}:
        return True

    index = text.lower().find(lowered_phrase)
    window = text[max(0, index - 600) : index + len(phrase) + 220].lower() if index >= 0 else text.lower()
    return bool(
        re.search(
            r"\b(?:similar products|sponsored|advertisement|view similar|notify me)\b|\bad\b",
            window,
            re.IGNORECASE,
        )
    )


def fallback_candidate_from_price_block(price_block: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(price_block, dict) or not price_block.get("found"):
        return None
    if not price_block.get("new_price"):
        return None

    sources = [
        ("primary_price_block_text", normalize_text(str(price_block.get("text") or ""))),
        ("primary_price_nearby_text", normalize_text(str(price_block.get("nearby_text") or ""))),
    ]
    for source, text in sources:
        phrase = extract_promotional_badge_phrase(text)
        if not phrase or not _has_price_context(text, phrase):
            continue
        if _is_unsafe_nearby_fallback(source, text, phrase):
            continue

        classification = classify_candidate_text(phrase)
        if not classification.get("is_promotional_text"):
            continue

        return {
            "text": phrase,
            "raw_text": text,
            "visible": True,
            "accepted": True,
            "rejection_reason": "",
            "source": source,
            "bounding_box": price_block.get("bounding_box") or {},
            "dom_path": price_block.get("dom_path", ""),
            "context_text": text[:1200],
            "local_container_text": text[:700],
            **classification,
        }

    return None


async def extract_deal_badge(page: Page) -> dict[str, Any]:
    price_block = await extract_primary_price_block(page)
    if not price_block.get("found"):
        return {
            "status": STATUS_UNCERTAIN,
            "reason": price_block.get("reason", "primary price block not found"),
            "deal_tag": "",
            "price_block": price_block,
            "candidates": [],
            "accepted_candidate": None,
        }

    raw = await collect_deal_candidates(page, price_block)
    raw_candidates = raw.get("candidates", []) if raw else []
    accepted, decisions, uncertain = evaluate_candidates(raw_candidates, price_block)

    if not accepted:
        accepted = fallback_candidate_from_price_block(price_block)
        if accepted:
            decisions.append(accepted)
            price_complete = bool(
                price_block.get("discount_percentage") and price_block.get("old_price") and price_block.get("new_price")
            )
            return {
                "status": STATUS_FOUND if price_complete else STATUS_PARTIAL,
                "reason": "deal badge accepted from primary price block text"
                if price_complete
                else "deal badge accepted from primary price block text but primary price block was incomplete",
                "deal_tag": accepted["text"],
                "price_block": price_block,
                "candidates": decisions,
                "accepted_candidate": accepted,
                "raw_candidate_count": len(raw_candidates),
            }

        semantic_candidates = [
            item for item in decisions if item.get("positive_score", 0) >= 3 and not item.get("accepted")
        ]
        return {
            "status": STATUS_UNCERTAIN if uncertain and semantic_candidates else STATUS_NO_TAG,
            "reason": "semantic badge candidates rejected by visual/context checks"
            if uncertain and semantic_candidates
            else "no valid deal badge found",
            "deal_tag": "",
            "price_block": price_block,
            "candidates": decisions,
            "accepted_candidate": None,
            "raw_candidate_count": len(raw_candidates),
        }

    price_complete = bool(
        price_block.get("discount_percentage") and price_block.get("old_price") and price_block.get("new_price")
    )
    return {
        "status": STATUS_FOUND if price_complete else STATUS_PARTIAL,
        "reason": "deal badge accepted"
        if price_complete
        else "deal badge accepted but primary price block was incomplete",
        "deal_tag": accepted["text"],
        "price_block": price_block,
        "candidates": decisions,
        "accepted_candidate": accepted,
        "raw_candidate_count": len(raw_candidates),
    }


def extraction_to_result(fsn: str, extraction: dict[str, Any], debug_path: str = "") -> ScrapeResult:
    price_block = extraction.get("price_block") or {}
    status = extraction.get("status") or STATUS_NO_TAG
    deal_tag = normalize_text(extraction.get("deal_tag") or "")
    found = bool(deal_tag and status in {STATUS_FOUND, STATUS_PARTIAL})
    return ScrapeResult(
        fsn=fsn,
        url=build_url(fsn),
        deal_tag_found=found,
        deal_tag=deal_tag,
        discount_percentage=price_block.get("discount_percentage", "") if found else "",
        old_price=price_block.get("old_price", "") if found else "",
        new_price=price_block.get("new_price", "") if found else "",
        status=status,
        reason=extraction.get("reason", ""),
        scraped_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        debug_path=debug_path,
    )
