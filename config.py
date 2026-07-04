from __future__ import annotations

import os
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent

SCRIPT_VERSION = "2026.07.04-production-v3"
BASE_URL = "https://www.flipkart.com/product/p/itme?pid={fsn}"
DEFAULT_FSN_COLUMN = "FSN"

OUTPUT_COLUMNS = [
    "Deal_Tag",
    "Deal_Tag_Found",
    "Discount_Percentage",
    "Old_Price",
    "New_Price",
    "Flipkart_URL",
    "Scrape_Status",
    "Scrape_Reason",
    "Scraped_At",
]

STATUS_FOUND = "FOUND"
STATUS_NO_TAG = "NO_TAG"
STATUS_PARTIAL = "PARTIAL"
STATUS_UNCERTAIN = "UNCERTAIN"
STATUS_TIMEOUT = "TIMEOUT"
STATUS_ERROR = "ERROR"
STATUS_INVALID_FSN = "INVALID_FSN"

DEFAULT_HEADLESS = True
DEFAULT_DEBUG = False
DEFAULT_CONCURRENCY = 4
DEFAULT_SAVE_EVERY = 10

PAGE_TIMEOUT_MS = 30_000
RENDER_SETTLE_MS = 2_500
RETRY_RENDER_SETTLE_MS = 5_000
RETRY_COUNT = 2

DEBUG_ROOT = Path(os.environ.get("FKT_DEBUG_ROOT", PROJECT_DIR / "debug_artifacts"))

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)


def build_url(fsn: str) -> str:
    return BASE_URL.format(fsn=fsn)
