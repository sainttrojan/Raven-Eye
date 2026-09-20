"""One-time WhatsApp Web login for the sender.

Usage:
    venv/bin/python wa_login.py

Opens a real browser window: scan the QR code with your phone
(WhatsApp > Linked devices) and WAIT until your chats appear.
The script detects the login by itself (up to 3 minutes) — no ENTER
needed. The full browser profile (including IndexedDB, where WhatsApp
keeps its keys) is stored in wa_profile/ and reused by the sender.
Your phone must stay connected to the internet afterwards.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.wa_sender import WA_PROFILE_DIR, check_logged_in_now


async def main():
    from playwright.async_api import async_playwright
    from core.wa_sender import launch_wa_browser
    async with async_playwright() as p:
        browser, _context = await launch_wa_browser(p, headless=False)
        page = await _context.new_page()
        await page.goto("https://web.whatsapp.com/", wait_until="domcontentloaded")
        print("=" * 60)
        print("امسح QR بالموبايل واستنى — السكريبت هيتأكد تلقائيا أول ما الشاتات تظهر.")
        print("=" * 60)
        for _ in range(60):
            await page.wait_for_timeout(3000)
            try:
                if await check_logged_in_now(page):
                    print("تمام، الجلسة شغالة ومحفوظة في wa_profile/ — اقفل المتصفح.")
                    break
            except Exception:
                pass
        else:
            print("الشاتات مظهرتش خلال 3 دقايق — حاول تاني.")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
