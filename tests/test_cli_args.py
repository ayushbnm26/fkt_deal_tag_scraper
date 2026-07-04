from __future__ import annotations

from flipkart_deal_tag_scraper import parse_args


def test_parse_args_honors_debug_true_and_input_path() -> None:
    args = parse_args(
        [
            "--input",
            "All SKUs Flipkart for deal Tags.xlsx",
            "--output",
            "flipkart_deal_tag_result.xlsx",
            "--fsn-column",
            "FSN",
            "--headless",
            "true",
            "--debug",
            "true",
            "--concurrency",
            "4",
        ]
    )

    assert args.input == "All SKUs Flipkart for deal Tags.xlsx"
    assert args.output == "flipkart_deal_tag_result.xlsx"
    assert args.fsn_column == "FSN"
    assert args.headless is True
    assert args.debug is True
    assert args.concurrency == 4
