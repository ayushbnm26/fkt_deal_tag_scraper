# Flipkart Deal Tag Scraper

Production-oriented Playwright scraper for extracting only real Flipkart deal badges from product pages.

The scraper reads FSNs from an Excel workbook, preserves the original rows and columns, and appends or updates scraper output columns in the same workbook structure.

## Setup

```powershell
pip install -r requirements.txt
playwright install chromium
```

## Run

```powershell
python flipkart_deal_tag_scraper.py --input demo_fsn.xlsx --output flipkart_deal_tag_result.xlsx --fsn-column FSN --headless true --debug true --concurrency 4
```

Useful options:

```powershell
python flipkart_deal_tag_scraper.py --input demo_fsn.xlsx --output result.xlsx --limit 10
python flipkart_deal_tag_scraper.py --input demo_fsn.xlsx --output result.xlsx --resume true
python flipkart_deal_tag_scraper.py --input demo_fsn.xlsx --output result.xlsx --save-every 5
```

## Input

The workbook must contain an FSN column. The default column name is `FSN`; override it with `--fsn-column`.
The scraper does not filter by category unless the input workflow does so before this script runs. If the workbook only has
`FSN`, `SKU`, and `Brand`, every valid FSN in that column is scraped.

Each URL is built as:

```text
https://www.flipkart.com/product/p/itme?pid=<FSN>
```

## Output Columns

The original workbook columns remain in their original order. These columns are appended if missing, or updated if already present:

```text
Deal_Tag
Deal_Tag_Found
Discount_Percentage
Old_Price
New_Price
Flipkart_URL
Scrape_Status
Scrape_Reason
Scraped_At
```

Duplicate FSNs are scraped once and written back to every matching row. Blank FSN rows keep scraper output columns blank.

## Deal Badge Rules

A value is written to `Deal_Tag` only when all checks pass:

- The text is visible and compact.
- It is near the primary product price block.
- It has badge-like visual context such as a compact green/dark/non-white label container.
- It has promotional badge language such as `Hot Deal`, `Top Discount of the Sale`, `Early Access`, `Lowest Price in the Year`, `Special Deal`, or similar.
- It is not a dimension, product variant, price, discount, coupon, bank offer, delivery text, seller text, rating text, or UI action.
- If Flipkart embeds a known badge phrase inside the primary price line instead of a clean standalone DOM node, the scraper extracts the clean phrase from that primary price block.

Examples that are rejected:

```text
72 inch x 36 inch
72 cm x 46 cm
Pack of 2
Queen
Multicolor
Cotton
₹529
65% off
Bank Offer
Apply Coupon
Free delivery
Ratings
Reviews
Lowest price for you
```

When uncertain, the scraper leaves `Deal_Tag` blank and records `UNCERTAIN` or `NO_TAG` with a reason.

## Debug Mode

With `--debug true`, artifacts are saved under:

```text
debug_artifacts/<FSN>/page.png
debug_artifacts/<FSN>/price_area.png
debug_artifacts/<FSN>/page.html
debug_artifacts/<FSN>/trace.json
```

Set `FKT_DEBUG_ROOT` to write debug artifacts somewhere else for a smoke run:

```powershell
$env:FKT_DEBUG_ROOT = "debug_artifacts_restore_smoke"
```

`trace.json` includes the final status, accepted candidate, rejected candidates, candidate bounding boxes, DOM paths, computed style summaries, validation signals, rejection reasons, and primary price parse result.

## Tests

```powershell
python -m pytest
```

The offline tests cover:

- Text validation and false-positive rejection.
- Badge visual-context validation.
- Final acceptance requiring both semantic and visual evidence.
- Price parsing and plausibility checks.
- Excel preservation and output column appending.

## Status Values

```text
FOUND       Real badge accepted and price block parsed.
PARTIAL     Real badge accepted, but one or more price fields were incomplete.
NO_TAG      No valid deal badge found.
UNCERTAIN   Promotional-looking text existed, but visual/context checks were not enough.
TIMEOUT     Page timed out.
ERROR       Unexpected scrape error.
INVALID_FSN FSN format failed validation.
```

## Troubleshooting

- If Chromium is missing, run `playwright install chromium`.
- If Flipkart rate-limits or serves unusual markup, lower `--concurrency`.
- If output appears stale, check the startup version stamp printed by the script.
- Use `--debug true` and inspect `debug_artifacts/<FSN>/trace.json` for candidate decisions.

## Known Limitations

Flipkart uses dynamic markup and may change badge styling. This scraper avoids guessing: a real promotional phrase without compact badge styling is not accepted. This can miss a new badge style until the visual classifier is updated, but it avoids writing product variants such as dimensions into `Deal_Tag`.
