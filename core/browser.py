"""Shared Playwright browser helpers (Facebook).

Session model: a one-time manual login (`venv/bin/python fb_login.py`)
saves an authenticated storage state to FB_STORAGE_FILE. Every scraper
loads that file — no passwords stored anywhere.
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager

from core.config import FB_COOKIES_FILE, FB_STORAGE_FILE

_CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


async def new_context(p, headless: bool = True):
    """Launch Chromium and return (browser, context) with FB session loaded."""
    browser = await p.chromium.launch(headless=headless)
    kwargs = {
        "viewport": {"width": 1280, "height": 720},
        "user_agent": _CHROME_UA,
        "locale": "en-US",
    }
    if os.path.exists(FB_STORAGE_FILE):
        kwargs["storage_state"] = FB_STORAGE_FILE
    context = await browser.new_context(**kwargs)
    if not os.path.exists(FB_STORAGE_FILE) and os.path.exists(FB_COOKIES_FILE):
        with open(FB_COOKIES_FILE, "r") as f:
            await context.add_cookies(json.load(f))
    return browser, context


async def is_logged_in(page) -> bool:
    """True if the page's Facebook session is authenticated."""
    try:
        await page.goto("https://www.facebook.com/", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        email_inputs = page.locator("input[name='email'], input[type='text']")
        return not await email_inputs.first.is_visible()
    except Exception:
        return False


async def login_to_facebook(page) -> bool:
    """Backwards-compatible check: True when authenticated."""
    ok = await is_logged_in(page)
    print("Successfully authenticated with Facebook cookies."
          if ok else "NOT LOGGED IN: run `venv/bin/python fb_login.py` first.")
    return ok


async def get_browser_context(p):
    """Backwards-compatible context factory (old callers)."""
    _browser, context = await new_context(p)
    return context


@asynccontextmanager
async def facebook_page(headless: bool = True):
    """Yield an authenticated FB page, closing the browser afterwards."""
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser, context = await new_context(p, headless=headless)
        try:
            page = await context.new_page()
            yield page
        finally:
            await browser.close()
