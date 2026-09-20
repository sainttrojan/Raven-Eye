"""Facebook session lifecycle for scrapers.

`run_facebook_search()` owns the whole browser lifecycle so Streamlit /
Telegram callers never touch Playwright objects directly.
"""

import asyncio
from typing import List

from core.browser import facebook_page, is_logged_in
from core.config import fb_session_available, load_fb_groups
from models.result import SearchResult
from scrapers.facebook import FacebookScraper
from scrapers.facebook_groups import FacebookGroupsScraper


class FacebookNotLoggedIn(Exception):
    """Raised when no usable Facebook session exists."""


async def _search(query: str, max_pages: int, fetch_details: bool,
                  detail_limit: int) -> List[SearchResult]:
    if not fb_session_available():
        raise FacebookNotLoggedIn(
            "لا توجد جلسة فيسبوك. شغل مرة واحدة: venv/bin/python fb_login.py "
            "وسجل الدخول في المتصفح اللي هيتفتح.")
    async with facebook_page(headless=True) as page:
        if not await is_logged_in(page):
            raise FacebookNotLoggedIn(
                "جلسة فيسبوك منتهية. شغل: venv/bin/python fb_login.py وسجل الدخول من جديد.")
        scraper = FacebookScraper(page, fetch_details=fetch_details,
                                  detail_limit=detail_limit)
        return await scraper.search(query, max_pages=max_pages)


def run_facebook_search(query: str, max_pages: int = 5,
                        fetch_details: bool = False,
                        detail_limit: int = 10) -> List[SearchResult]:
    """Sync entry point (safe to call from Streamlit/bot threads)."""
    return asyncio.run(_search(query, max_pages, fetch_details, detail_limit))


async def _search_groups(groups, query: str,
                         max_pages: int) -> List[SearchResult]:
    if not fb_session_available():
        raise FacebookNotLoggedIn(
            "لا توجد جلسة فيسبوك. شغل مرة واحدة: venv/bin/python fb_login.py "
            "وسجل الدخول في المتصفح اللي هيتفتح.")
    groups = groups or load_fb_groups()
    if not groups:
        raise FacebookNotLoggedIn(
            "مفيش جروبات متسجلة. ضيف روابط الجروبات من تاب الإعدادات الأول.")
    async with facebook_page(headless=True) as page:
        if not await is_logged_in(page):
            raise FacebookNotLoggedIn(
                "جلسة فيسبوك منتهية. شغل: venv/bin/python fb_login.py وسجل الدخول من جديد.")
        scraper = FacebookGroupsScraper(page)
        return await scraper.search_groups(groups, query, max_pages=max_pages)


def run_facebook_groups_search(query: str, groups=None,
                               max_pages: int = 3) -> List[SearchResult]:
    """Sync entry point for groups search (safe from Streamlit/bot threads)."""
    return asyncio.run(_search_groups(groups, query, max_pages))
