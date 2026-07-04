from __future__ import annotations

from dataclasses import asdict, dataclass

from config import build_url


@dataclass(frozen=True)
class ScrapeResult:
    fsn: str
    url: str
    deal_tag_found: bool
    deal_tag: str
    discount_percentage: str
    old_price: str
    new_price: str
    status: str
    reason: str
    scraped_at: str
    debug_path: str = ""

    @classmethod
    def blank(
        cls,
        fsn: str,
        status: str,
        reason: str,
        scraped_at: str,
        debug_path: str = "",
    ) -> "ScrapeResult":
        return cls(
            fsn=fsn,
            url=build_url(fsn) if fsn else "",
            deal_tag_found=False,
            deal_tag="",
            discount_percentage="",
            old_price="",
            new_price="",
            status=status,
            reason=reason,
            scraped_at=scraped_at,
            debug_path=debug_path,
        )

    def to_output_values(self) -> dict[str, str]:
        return {
            "Deal_Tag": self.deal_tag,
            "Deal_Tag_Found": "TRUE" if self.deal_tag_found else "FALSE",
            "Discount_Percentage": self.discount_percentage,
            "Old_Price": self.old_price,
            "New_Price": self.new_price,
            "Flipkart_URL": self.url,
            "Scrape_Status": self.status,
            "Scrape_Reason": self.reason,
            "Scraped_At": self.scraped_at,
        }

    def as_trace_dict(self) -> dict[str, object]:
        return asdict(self)
