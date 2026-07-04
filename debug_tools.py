from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from playwright.async_api import Page

from config import DEBUG_ROOT


def safe_file_name(value: str) -> str:
    keep = []
    for char in value:
        if char.isalnum() or char in {"-", "_", "."}:
            keep.append(char)
        else:
            keep.append("_")
    return "".join(keep)[:120] or "blank"


async def save_debug_artifacts(
    page: Page,
    fsn: str,
    trace: dict[str, Any],
    debug_root: Path = DEBUG_ROOT,
) -> str:
    fsn_dir = debug_root / safe_file_name(fsn)
    fsn_dir.mkdir(parents=True, exist_ok=True)

    try:
        await page.screenshot(path=fsn_dir / "page.png", full_page=True)
    except Exception as exc:
        trace.setdefault("artifact_errors", []).append(f"page screenshot failed: {exc}")

    price_box = (trace.get("price_parse_result") or {}).get("bounding_box") or {}
    if price_box:
        try:
            clip = {
                "x": max(float(price_box.get("left", price_box.get("x", 0))) - 40, 0),
                "y": max(float(price_box.get("top", price_box.get("y", 0))) - 140, 0),
                "width": min(float(price_box.get("width", 600)) + 220, 1200),
                "height": min(float(price_box.get("height", 260)) + 260, 900),
            }
            await page.screenshot(path=fsn_dir / "price_area.png", clip=clip, full_page=False)
        except Exception as exc:
            trace.setdefault("artifact_errors", []).append(f"focused screenshot failed: {exc}")

    try:
        html = await page.content()
        (fsn_dir / "page.html").write_text(html, encoding="utf-8")
    except Exception as exc:
        trace.setdefault("artifact_errors", []).append(f"html save failed: {exc}")

    (fsn_dir / "trace.json").write_text(
        json.dumps(trace, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return str(fsn_dir)
