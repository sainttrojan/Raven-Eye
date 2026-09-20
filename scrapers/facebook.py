"""Facebook Marketplace scraper (authenticated session required).

Needs a one-time manual login: `venv/bin/python fb_login.py`.
Search cards give title/price/location/url; pass fetch_details=True to
open each item page for description + phone extraction (slower).
"""

import asyncio
import re
from typing import List, Optional
from urllib.parse import quote

from scrapers.base import BaseScraper
from models.result import SearchResult
from core.parser import SmartParser

ITEM_RE = re.compile(r"/marketplace/item/(\d+)")


def parse_card(href: str, lines: List[str]) -> Optional[SearchResult]:
    """Pure card parser (unit-testable, no browser needed)."""
    if not href:
        return None
    url = href if href.startswith("http") else "https://www.facebook.com" + href
    if not ITEM_RE.search(url):
        return None
    title, price, location = "Unknown Title", "", ""
    # Usual card order: [Price, Title, Location] (+ seller extras).
    if len(lines) >= 3:
        price, title, location = lines[0], lines[1], lines[2]
    elif len(lines) == 2:
        price, title = lines[0], lines[1]
    elif len(lines) == 1:
        title = lines[0]
    return SearchResult(source="Facebook Marketplace", title=title, url=url,
                        price=price or None, location=location or None)


class FacebookScraper(BaseScraper):
    def __init__(self, page=None, fetch_details: bool = False, detail_limit: int = 10):
        super().__init__(page)
        self.fetch_details = fetch_details
        self.detail_limit = detail_limit

    async def search(self, query: str, time_filter: str = "",
                     max_pages: int = 5) -> List[SearchResult]:
        if self.page is None:
            raise RuntimeError("FacebookScraper needs an authenticated page "
                               "(use core.fb_session.run_facebook_search).")
        results: List[SearchResult] = []
        seen = set()
        try:
            url = f"https://www.facebook.com/marketplace/cairo/search/?query={quote(query)}"
            await self.page.goto(url, wait_until="domcontentloaded")
            await self.page.wait_for_timeout(4000)

            scrolls = max(2, min(int(max_pages), 10))
            for _ in range(scrolls):
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await self.page.wait_for_timeout(2000)
                items = self.page.locator('a[href*="/marketplace/item/"]')
                count = await items.count()
                for i in range(count):
                    try:
                        item = items.nth(i)
                        href = await item.get_attribute("href")
                        inner = await item.inner_text()
                        lines = [ln.strip() for ln in inner.split("\n") if ln.strip()]
                        card = parse_card(href or "", lines)
                        if card and card.url not in seen:
                            seen.add(card.url)
                            results.append(card)
                    except Exception:
                        continue
        except Exception as e:
            print(f"Failed to search Facebook Marketplace: {e}")

        if self.fetch_details and results:
            await self._enrich_details(results[: self.detail_limit])
        return results

    async def _enrich_details(self, cards: List[SearchResult]) -> None:
        """Visit item pages to fill description + phone (best effort)."""
        for card in cards:
            try:
                await self.page.goto(card.url, wait_until="domcontentloaded")
                await self.page.wait_for_timeout(2500)
                text = await self.page.locator("body").inner_text()
                text = re.sub(r"\s+", " ", text or "").strip()
                if text:
                    card.description = text[:2000]
                    phone = SmartParser.extract_phone(text)
                    if phone:
                        card.phone_number = phone
            except Exception:
                continue
