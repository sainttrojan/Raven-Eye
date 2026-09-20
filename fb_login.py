"""One-time Facebook login for Marketplace scraping.

Usage:
    venv/bin/python fb_login.py

Opens a real browser window: log in to Facebook manually (solve any
checkpoint), then press ENTER here. The authenticated session is saved
to fb_storage_state.json and reused by all scrapers — your password is
never stored anywhere.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.browser import new_context
from core.config import FB_STORAGE_FILE


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser, context = await new_context(p, headless=False)
        page = await context.new_page()
        await page.goto("https://www.facebook.com/")
        print("=" * 60)
        print("سجل الدخول لفيسبوك في المتصفح اللي اتفتح، وبعدها دوس ENTER هنا.")
        print("=" * 60)
        await asyncio.get_event_loop().run_in_executor(None, input)
        await context.storage_state(path=FB_STORAGE_FILE)
        # quick verify
        await page.goto("https://www.facebook.com/marketplace/", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        print(f"Saved session to {FB_STORAGE_FILE}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
