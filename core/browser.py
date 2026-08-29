import asyncio
import os
import json
from playwright.async_api import async_playwright, BrowserContext
from core.config import FB_COOKIES_FILE

async def get_browser_context(p) -> BrowserContext:
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={'width': 1280, 'height': 720},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    if os.path.exists(FB_COOKIES_FILE):
        with open(FB_COOKIES_FILE, 'r') as f:
            cookies = json.load(f)
            await context.add_cookies(cookies)
    return context

async def login_to_facebook(page):
    print("Checking Facebook login status...")
    await page.goto("https://www.facebook.com/")
    await page.wait_for_timeout(3000)
    
    email_inputs = page.locator("input[name='email'], input[type='text']")
    if await email_inputs.first.is_visible():
        raise Exception("\n\n*** NOT LOGGED IN! ***\nFacebook requested a manual login or your session expired.\nPlease run: .\\uv_extracted\\uv.exe run python login_manual.py\nSolve the CAPTCHA in the browser, then run main.py again.\n")
    else:
        print("Successfully authenticated with Facebook cookies.")
