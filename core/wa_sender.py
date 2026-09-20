"""WhatsApp sender via WhatsApp Web (Playwright, own number).

Model: one-time manual login (`venv/bin/python wa_login.py`, QR scan)
saves the session to wa_storage_state.json. Afterwards messages are
sent from YOUR number through the real Web UI — no unofficial APIs.

Safety rules (anti-ban, anti-accident):
  * dry_run=True default everywhere: logs what WOULD be sent.
  * random delay between messages (default 8-15s), never bulk-blast.
  * per-run target cap (default 30).

Typical Raven-Eye use: push new owner-listings to subscribed buyers,
or message advertisers from your own number.
"""

import os
import random
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

WA_STORAGE_FILE = os.getenv("WA_STORAGE_FILE", "wa_storage_state.json")
WA_PROFILE_DIR = os.getenv("WA_PROFILE_DIR", "wa_profile")
WA_SUBS_FILE = os.getenv("WA_SUBS_FILE", "wa_subscribers.json")

DEFAULT_DELAY = (8, 15)
DEFAULT_CAP = 30


class WaNotLoggedIn(Exception):
    """Raised when no usable WhatsApp session exists."""


def wa_session_available() -> bool:
    """True if a persistent WhatsApp profile exists (the only session
    that works — WhatsApp keeps auth in IndexedDB, which storage_state
    files do NOT include)."""
    return os.path.isdir(WA_PROFILE_DIR) and bool(os.listdir(WA_PROFILE_DIR))


async def check_logged_in_now(page) -> bool:
    """Inspect the CURRENT page without navigating (safe during QR scan)."""
    try:
        body = await page.locator("body").inner_text()
    except Exception:
        return False
    if "Scan to log in" in body or "Scan the QR code" in body:
        return False
    pane = page.locator('div[aria-label*="Chat"], div[role="grid"], '
                        'div[data-testid="chat-list"]')
    try:
        await pane.first.wait_for(timeout=5000)
        return True
    except Exception:
        return False


async def is_logged_in_async(page) -> bool:
    """True when chats are visible (session alive).

    Strict: the QR landing page contains grid-ish elements that fooled
    the old check, so an explicit "Scan to log in" marker vetoes True.
    """
    try:
        await page.goto("https://web.whatsapp.com/",
                        wait_until="domcontentloaded")
        await page.wait_for_timeout(8000)
        return await check_logged_in_now(page)
    except Exception:
        return False


def parse_targets(raw: str) -> List[str]:
    """Extract Egyptian mobile digits (for wa.me) from free text.

    Accepts 01xxxxxxxxx / +20... / 0020... Returns wa.me digits
    (e.g. 201001234567), deduped, order kept.
    """
    seen, out = set(), []
    for m in re.findall(r"\+?0{0,2}2?0?1[0125]\d{8}", (raw or "").replace(" ", "")):
        digits = re.sub(r"\D", "", m)
        if digits.startswith("0020"):
            digits = digits[2:]
        elif digits.startswith("0"):
            digits = "20" + digits[1:]
        if not digits.startswith("20"):
            digits = "20" + digits.lstrip("0")
        if len(digits) == 12 and digits not in seen:
            seen.add(digits)
            out.append(digits)
    return out


def build_send_url(digits: str, text: str = "") -> str:
    url = f"https://web.whatsapp.com/send?phone={digits}"
    if text:
        url += f"&text={quote(text)}&type=phone_number&app_absent=0"
    return url


def render_listing(prop: Dict[str, Any]) -> str:
    """One listing dict -> WhatsApp message text."""
    lines = [f"*{prop.get('Title', 'عقار')}*"]
    if prop.get("Price"):
        lines.append(f"السعر: {prop['Price']}")
    if prop.get("Area"):
        lines.append(f"المساحة: {prop['Area']}")
    if prop.get("Phone Number"):
        lines.append(f"للتواصل: {prop['Phone Number']}")
    if prop.get("URL"):
        lines.append(prop["URL"])
    return "\n".join(lines)


async def _send_one(page, digits: str, text: str,
                    image_path: Optional[str] = None) -> Dict[str, Any]:
    await page.goto(build_send_url(digits, text), wait_until="domcontentloaded")
    try:
        box = page.locator('div[contenteditable="true"][data-tab="10"]').first
        await box.wait_for(timeout=45000)
    except Exception:
        return {"target": digits, "ok": False,
                "error": "الشات مفتحش (الرقم ممكن ميكونش عليه واتساب)"}
    try:
        if image_path and os.path.exists(image_path):
            await page.locator('span[data-icon="clip"]').first.click()
            await page.wait_for_timeout(1500)
            await page.locator('input[type="file"]').first.set_input_files(image_path)
            await page.wait_for_timeout(3000)
            send_btn = page.locator('span[data-icon="send"]').first
            await send_btn.wait_for(timeout=20000)
            await send_btn.click()
        else:
            await box.press("Enter")
        await page.wait_for_timeout(2000)
        return {"target": digits, "ok": True, "error": ""}
    except Exception as e:
        return {"target": digits, "ok": False, "error": str(e)[:150]}


async def launch_wa_browser(p, headless: bool = True):
    """Persistent-context browser: the ONLY way to keep a WhatsApp login.

    Returns (browser, context). Caller's try/finally must close browser.
    """
    from core.browser import _CHROME_UA
    browser = await p.chromium.launch_persistent_context(
        WA_PROFILE_DIR,
        headless=headless,
        viewport={"width": 1280, "height": 720},
        user_agent=_CHROME_UA,
        locale="en-US",
    )
    return browser, browser


async def _run(targets: List[str], text: str,
               image_path: Optional[str] = None,
               delay: tuple = DEFAULT_DELAY) -> List[Dict[str, Any]]:
    if not wa_session_available():
        raise WaNotLoggedIn(
            "مفيش جلسة واتساب. شغل مرة واحدة: venv/bin/python wa_login.py "
            "وامسح QR بالموبايل.")
    from playwright.async_api import async_playwright
    results: List[Dict[str, Any]] = []
    async with async_playwright() as p:
        browser, context = await launch_wa_browser(p, headless=True)
        try:
            page = await context.new_page()
            if not await is_logged_in_async(page):
                raise WaNotLoggedIn("جلسة واتساب منتهية (الموبايل مفصول؟). "
                                    "شغل venv/bin/python wa_login.py من جديد.")
            for digits in targets:
                results.append(await _send_one(page, digits, text, image_path))
                time.sleep(random.uniform(*delay))
        finally:
            await browser.close()
    return results


def send_messages(targets: List[str], text: str,
                  image_path: Optional[str] = None,
                  delay: tuple = DEFAULT_DELAY, cap: int = DEFAULT_CAP,
                  dry_run: bool = True) -> Dict[str, Any]:
    """Send text (+optional image) to wa.me digit targets.

    dry_run=True (default) sends NOTHING and returns what would happen.
    Returns {"dry_run", "results": [...], "sent", "failed"}.
    """
    import asyncio
    targets = (targets or [])[:max(1, cap)]
    if not targets:
        return {"dry_run": dry_run, "results": [], "sent": 0, "failed": 0,
                "error": "مفيش أرقام صالحة"}
    if not (text or "").strip() and not image_path:
        return {"dry_run": dry_run, "results": [], "sent": 0, "failed": 0,
                "error": "الرسالة فاضية"}
    if dry_run:
        return {"dry_run": True,
                "results": [{"target": d, "ok": True, "error": "dry-run"} for d in targets],
                "sent": len(targets), "failed": 0, "error": ""}
    results = asyncio.run(_run(targets, text, image_path, delay))
    return {"dry_run": False, "results": results,
            "sent": sum(1 for r in results if r["ok"]),
            "failed": sum(1 for r in results if not r["ok"]), "error": ""}


def extract_numbers_from_frame(df) -> List[str]:
    """Pull Egyptian mobile digits out of every cell of a sheet."""
    try:
        blob = " ".join(df.astype(str).values.ravel())
    except Exception:
        return []
    return parse_targets(blob)


def load_numbers_file(path: str) -> List[str]:
    """Read .xlsx/.csv and extract all phone numbers it contains."""
    import pandas as pd
    if path.lower().endswith(".csv"):
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
    else:
        df = pd.read_excel(path, dtype=str)
    return extract_numbers_from_frame(df)


def load_subscribers(path: str = WA_SUBS_FILE) -> List[str]:
    import json
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            pass
    return []


def save_subscribers(subs: List[str], path: str = WA_SUBS_FILE) -> None:
    import json
    with open(path, "w") as f:
        json.dump(sorted(set(subs)), f, ensure_ascii=False)
