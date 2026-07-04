from __future__ import annotations

import pandas as pd

from config import OUTPUT_COLUMNS, STATUS_FOUND
from io_excel import merge_results_into_original_excel
from models import ScrapeResult


def test_merge_preserves_original_columns_and_appends_outputs() -> None:
    input_df = pd.DataFrame(
        [
            {
                "FSN": "ABC123456789",
                "Title": "Product A",
                "Category": "Cat",
                "Brand": "Brand",
                "MRP": "999",
                "Any Existing Business Column": "Keep me",
            },
            {
                "FSN": "",
                "Title": "Blank row",
                "Category": "Cat",
                "Brand": "Brand",
                "MRP": "199",
                "Any Existing Business Column": "Keep blank outputs",
            },
        ]
    )
    result = ScrapeResult(
        fsn="ABC123456789",
        url="https://www.flipkart.com/product/p/itme?pid=ABC123456789",
        deal_tag_found=True,
        deal_tag="Hot Deal",
        discount_percentage="50%",
        old_price="999",
        new_price="499",
        status=STATUS_FOUND,
        reason="deal badge accepted",
        scraped_at="2026-07-03T00:00:00+00:00",
    )

    output = merge_results_into_original_excel(input_df, {"ABC123456789": result}, fsn_column="FSN")

    original_columns = list(input_df.columns)
    assert list(output.columns[: len(original_columns)]) == original_columns
    assert list(output.columns[len(original_columns) :]) == OUTPUT_COLUMNS
    assert output.loc[0, "Any Existing Business Column"] == "Keep me"
    assert output.loc[0, "Deal_Tag"] == "Hot Deal"
    assert output.loc[1, "Deal_Tag"] == ""
    assert output.loc[1, "Scrape_Status"] == ""
