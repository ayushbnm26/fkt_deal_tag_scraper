from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import (
    DEFAULT_CONCURRENCY,
    DEFAULT_DEBUG,
    DEFAULT_FSN_COLUMN,
    DEFAULT_HEADLESS,
    DEFAULT_SAVE_EVERY,
    PAGE_TIMEOUT_MS,
    PROJECT_DIR,
    RENDER_SETTLE_MS,
    RETRY_COUNT,
    RETRY_RENDER_SETTLE_MS,
    SCRIPT_VERSION,
    STATUS_ERROR,
    STATUS_FOUND,
    STATUS_NO_TAG,
    STATUS_PARTIAL,
    STATUS_TIMEOUT,
    STATUS_UNCERTAIN,
    USER_AGENT,
    build_url,
)


DEFAULT_INPUT = PROJECT_DIR / "All SKUs Flipkart for deal Tags.xlsx"
DEFAULT_OUTPUT = PROJECT_DIR / "flipkart_deal_tag_result.xlsx"


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Expected true or false, got: {value}")


def existing_input_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path

    cwd_path = Path.cwd() / path
    if cwd_path.exists():
        return cwd_path

    project_path = PROJECT_DIR / path
    return project_path


def output_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path.cwd() / path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape Flipkart product deal tags from an Excel workbook.",
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input Excel workbook path.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output Excel workbook path.")
    parser.add_argument("--fsn-column", default=DEFAULT_FSN_COLUMN, help="Column containing FSNs.")
    parser.add_argument("--headless", type=parse_bool, default=DEFAULT_HEADLESS, help="Run browser headlessly.")
    parser.add_argument("--debug", type=parse_bool, default=DEFAULT_DEBUG, help="Save debug artifacts.")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Parallel pages to scrape.")
    parser.add_argument("--limit", type=int, default=None, help="Scrape only the first N unique FSNs.")
    parser.add_argument("--resume", type=parse_bool, default=False, help="Skip FSNs already present in output.")
    parser.add_argument("--save-every", type=int, default=DEFAULT_SAVE_EVERY, help="Write progress every N results.")
    parser.add_argument("--retries", type=int, default=RETRY_COUNT, help="Retry misses/errors this many times.")
    return parser.parse_args(argv)


async def block_heavy_resources(route: Any) -> None:
    request = route.request
    if request.resource_type in {"image", "media", "font"}:
        await route.abort()
        return

    url = request.url.lower()
    blocked_fragments = (
        "googletagmanager",
        "google-analytics",
        "doubleclick",
        "facebook",
        "hotjar",
        "/ads",
        "adsystem",
    )
    if request.resource_type in {"beacon", "websocket"} or any(fragment in url for fragment in blocked_fragments):
        await route.abort()
        return

    await route.continue_()


async def wait_for_render(page: Page, retry_attempt: bool) -> None:
    await page.wait_for_load_state("domcontentloaded", timeout=PAGE_TIMEOUT_MS)
    await page.wait_for_selector("body", state="attached", timeout=PAGE_TIMEOUT_MS)
    await page.wait_for_timeout(RETRY_RENDER_SETTLE_MS if retry_attempt else RENDER_SETTLE_MS)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_trace(
    fsn: str,
    attempt: int,
    result: ScrapeResult,
    extraction: dict[str, Any] | None,
) -> dict[str, Any]:
    extraction = extraction or {}
    candidates = extraction.get("candidates") or []
    rejected = [candidate for candidate in candidates if not candidate.get("accepted")]
    return {
        "script_version": SCRIPT_VERSION,
        "fsn": fsn,
        "url": result.url,
        "attempt": attempt,
        "result": result.as_trace_dict(),
        "status": result.status,
        "reason": result.reason,
        "price_parse_result": extraction.get("price_block") or {},
        "accepted_candidate": extraction.get("accepted_candidate"),
        "rejected_candidates": rejected,
        "candidates": candidates,
        "raw_candidate_count": extraction.get("raw_candidate_count", 0),
    }


async def maybe_save_debug(
    page: Any,
    fsn: str,
    attempt: int,
    result: Any,
    extraction: dict[str, Any] | None,
    enabled: bool,
) -> Any:
    if not enabled:
        return result

    from debug_tools import save_debug_artifacts

    trace = make_trace(fsn, attempt, result, extraction)
    debug_path = await save_debug_artifacts(page, fsn, trace)
    return replace(result, debug_path=debug_path)


async def scrape_attempt(
    context: Any,
    fsn: str,
    attempt: int,
    debug: bool,
) -> Any:
    from extractors.dom_extractor import extract_deal_badge, extraction_to_result
    from models import ScrapeResult
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError

    page = await context.new_page()
    extraction: dict[str, Any] | None = None

    try:
        result: Any
        await page.goto(build_url(fsn), wait_until="domcontentloaded", timeout=PAGE_TIMEOUT_MS)
        await wait_for_render(page, retry_attempt=attempt > 1)

        extraction = await extract_deal_badge(page)
        result = extraction_to_result(fsn, extraction)
        return await maybe_save_debug(page, fsn, attempt, result, extraction, debug)

    except PlaywrightTimeoutError:
        result = ScrapeResult.blank(
            fsn=fsn,
            status=STATUS_TIMEOUT,
            reason="timeout",
            scraped_at=utc_now(),
        )
        return await maybe_save_debug(page, fsn, attempt, result, extraction, debug)
    except Exception as exc:
        result = ScrapeResult.blank(
            fsn=fsn,
            status=STATUS_ERROR,
            reason=f"page error: {exc}",
            scraped_at=utc_now(),
        )
        return await maybe_save_debug(page, fsn, attempt, result, extraction, debug)
    finally:
        await page.close()


async def scrape_one_fsn(
    context: Any,
    fsn: str,
    semaphore: asyncio.Semaphore,
    debug: bool,
    retries: int,
) -> Any:
    from models import ScrapeResult

    async with semaphore:
        last_result: Any | None = None
        total_attempts = max(1, retries + 1)
        for attempt in range(1, total_attempts + 1):
            last_result = await scrape_attempt(context, fsn, attempt, debug)
            if last_result.status in {STATUS_FOUND, STATUS_PARTIAL}:
                return last_result
            if last_result.status not in {STATUS_TIMEOUT, STATUS_ERROR, STATUS_UNCERTAIN}:
                return last_result
        return last_result or ScrapeResult.blank(
            fsn=fsn,
            status=STATUS_ERROR,
            reason="no scrape attempts completed",
            scraped_at=utc_now(),
        )


def print_result(completed: int, total: int, result: Any) -> None:
    if result.status in {STATUS_FOUND, STATUS_PARTIAL}:
        print(
            f"[{completed}/{total}] {result.status} | {result.fsn} | "
            f"Tag: {result.deal_tag} | {result.discount_percentage} | "
            f"Old: {result.old_price} | New: {result.new_price}",
            flush=True,
        )
        return

    print(f"[{completed}/{total}] {result.status} | {result.fsn} | reason: {result.reason}", flush=True)


async def run_scraper(
    fsns: list[str],
    existing_results: dict[str, Any],
    input_path: Path,
    output_path_value: Path,
    fsn_column: str,
    headless: bool,
    debug: bool,
    concurrency: int,
    retries: int,
    save_every: int,
) -> dict[str, Any]:
    from io_excel import write_results_to_workbook
    from playwright.async_api import async_playwright

    results = dict(existing_results)
    pending = [fsn for fsn in fsns if fsn not in results]
    if not pending:
        return results

    semaphore = asyncio.Semaphore(max(1, concurrency))
    completed = 0
    total = len(pending)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=USER_AGENT,
            locale="en-IN",
            service_workers="block",
        )
        context.set_default_timeout(PAGE_TIMEOUT_MS)
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
        await context.route("**/*", block_heavy_resources)

        try:
            tasks = [
                asyncio.create_task(scrape_one_fsn(context, fsn, semaphore, debug, retries))
                for fsn in pending
            ]
            for task in asyncio.as_completed(tasks):
                result = await task
                results[result.fsn] = result
                completed += 1
                print_result(completed, total, result)

                if save_every > 0 and completed % save_every == 0:
                    write_results_to_workbook(input_path, output_path_value, results, fsn_column)
                    print(f"Progress saved: {output_path_value}", flush=True)
        finally:
            await context.close()
            await browser.close()

    return results


async def main() -> None:
    from io_excel import (
        invalid_fsn_results,
        is_valid_fsn,
        load_resume_results,
        read_input_excel,
        unique_fsns,
        write_results_to_workbook,
    )

    args = parse_args()
    input_path = existing_input_path(args.input)
    out_path = output_path(args.output)
    concurrency = max(1, int(args.concurrency))
    save_every = max(0, int(args.save_every))
    retries = max(0, int(args.retries))

    input_df = read_input_excel(input_path, args.fsn_column)
    fsns = unique_fsns(input_df, args.fsn_column, args.limit)
    invalid_results = invalid_fsn_results(fsns, utc_now())
    valid_fsns = [fsn for fsn in fsns if is_valid_fsn(fsn)]

    resumed = load_resume_results(out_path, args.fsn_column) if args.resume else {}
    results: dict[str, Any] = {**invalid_results, **resumed}

    print(f"Flipkart deal tag scraper {SCRIPT_VERSION}", flush=True)
    print(f"Input: {input_path}", flush=True)
    print(f"Output: {out_path}", flush=True)
    print(f"Total rows in Excel: {len(input_df)}", flush=True)
    print(f"Unique FSNs: {len(fsns)} | Valid: {len(valid_fsns)} | Invalid: {len(invalid_results)}", flush=True)
    print(
        f"Headless: {args.headless} | Debug: {args.debug} | "
        f"Concurrency: {concurrency} | Retries: {retries} | Resume: {args.resume}",
        flush=True,
    )

    results = await run_scraper(
        fsns=valid_fsns,
        existing_results=results,
        input_path=input_path,
        output_path_value=out_path,
        fsn_column=args.fsn_column,
        headless=args.headless,
        debug=args.debug,
        concurrency=concurrency,
        retries=retries,
        save_every=save_every,
    )

    write_results_to_workbook(input_path, out_path, results, args.fsn_column)
    deal_tag_rows = sum(1 for result in results.values() if result.deal_tag_found)
    found_rows = sum(1 for result in results.values() if result.status == STATUS_FOUND)
    partial_rows = sum(1 for result in results.values() if result.status == STATUS_PARTIAL)
    no_tag_rows = sum(1 for result in results.values() if result.status == STATUS_NO_TAG)
    error_rows = sum(1 for result in results.values() if result.status == STATUS_ERROR)
    timeout_rows = sum(1 for result in results.values() if result.status == STATUS_TIMEOUT)

    print("", flush=True)
    print("DONE", flush=True)
    print(f"Output saved: {out_path}", flush=True)
    print(f"Scraped/result FSNs: {len(results)}", flush=True)
    print(f"Deal tags found: {deal_tag_rows}", flush=True)
    print(
        f"Status counts: FOUND={found_rows} PARTIAL={partial_rows} "
        f"NO_TAG={no_tag_rows} ERROR={error_rows} TIMEOUT={timeout_rows}",
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
