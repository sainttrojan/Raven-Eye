"""Facebook phone check via the account-recovery identify endpoint.

Same markers as user-scanner's email module (taken/available/ratelimit).
NETWORK NOTE (verified): facebook.com blocks datacenter IPs at the
homepage (HTTP 400) and rejects bare AJAX identify calls (error 1357004)
even with a logged-in session. The module degrades gracefully to
rate_limited/unknown there and activates on networks Facebook trusts.
Both E.164 (+20...) and national (01...) forms are tried.
"""

import re

import httpx

NAME = "facebook"
DOMAIN = "facebook.com"

_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36")


def interpret_identify_body(body: str) -> str:
    """Pure classifier: taken | available | ratelimit | unknown."""
    b = body or ""
    if "3252001" in b or "temporarily blocked" in b:
        return "ratelimit"
    if "These accounts matched your search" in b or "redirectPageTo" in b:
        return "taken"
    if "No search results" in b or "did not return any results" in b:
        return "available"
    return "unknown"


async def _tokens(client: httpx.AsyncClient):
    res = await client.get("https://www.facebook.com", params={"_rdr": ""},
                           headers={"User-Agent": _UA,
                                    "Accept": "text/html,application/xhtml+xml,"
                                              "application/xml;q=0.9,*/*;q=0.8"})
    html = res.text
    lsd = (re.search(r'\["LSD",\[\],\{"token":"([^"]+)"\}', html)
           or re.search(r'name="lsd"\s+value="([^"]+)"', html)
           or re.search(r'"lsd":"([^"]+)"', html))
    jaz = (re.search(r'jazoest=(\d+)', html)
           or re.search(r'name="jazoest"\s+value="(\d+)"', html))
    if not lsd or not jaz:
        return None, None
    return lsd.group(1), jaz.group(1)


async def _probe(client: httpx.AsyncClient, target: str):
    lsd, jaz = await _tokens(client)
    if not lsd:
        return "unknown"
    payload = {"jazoest": jaz, "lsd": lsd, "email": target,
               "did_submit": "1", "__user": "0", "__a": "1", "__req": "7"}
    headers = {"User-Agent": _UA, "Accept-Encoding": "identity",
               "origin": "https://www.facebook.com",
               "sec-fetch-site": "same-origin", "sec-fetch-mode": "cors",
               "sec-fetch-dest": "empty", "x-fb-lsd": lsd,
               "referer": "https://www.facebook.com/login/identify/?ctx=recover",
               "accept-language": "en-US,en;q=0.9"}
    r = await client.post("https://www.facebook.com/ajax/login/help/identify.php",
                          params={"ctx": "recover"}, data=payload, headers=headers)
    return interpret_identify_body(r.text)


async def _probe_authenticated(target: str, timeout: int = 25) -> str:
    """Same probe through the logged-in Playwright session.

    Datacenter IPs get a 400 error page on facebook.com while a real
    authenticated session is trusted. Falls back gracefully when no
    session exists.
    """
    from playwright.async_api import async_playwright
    from core.browser import new_context
    from core.config import fb_session_available
    if not fb_session_available():
        return "unknown"
    async with async_playwright() as p:
        browser, context = await new_context(p, headless=True)
        try:
            page = await context.new_page()
            await page.goto("https://www.facebook.com/",
                            wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)
            html = await page.content()
            lsd = (re.search(r'\["LSD",\[\],\{"token":"([^"]+)"\}', html)
                   or re.search(r'name="lsd"\s+value="([^"]+)"', html)
                   or re.search(r'"lsd":"([^"]+)"', html))
            jaz = (re.search(r'jazoest=(\d+)', html)
                   or re.search(r'name="jazoest"\s+value="(\d+)"', html))
            if not lsd or not jaz:
                return "unknown"
            body = await page.evaluate(
                """async (a) => {
                     const p = new URLSearchParams();
                     p.append('jazoest', a.j); p.append('lsd', a.l);
                     p.append('email', a.t); p.append('did_submit', '1');
                     p.append('__user', '0'); p.append('__a', '1'); p.append('__req', '7');
                     const r = await fetch(
                       'https://www.facebook.com/ajax/login/help/identify.php?ctx=recover',
                       {method: 'POST', body: p,
                        headers: {'x-fb-lsd': a.l},
                        credentials: 'same-origin'});
                     return await r.text();
                   }""",
                {"l": lsd.group(1), "j": jaz.group(1), "t": target})
            return interpret_identify_body(body or "")
        except Exception:
            return "unknown"
        finally:
            await browser.close()


async def check_facebook(e164: str, national: str, cc: str,
                         client: httpx.AsyncClient, out: list):
    """Try E.164 first, fall back to national form on explicit absence."""
    try:
        verdict = await _probe(client, e164)
        if verdict == "available":
            verdict = await _probe(client, "0" + national)
        if verdict == "unknown":
            # IP-level block on the anonymous path — retry authenticated.
            verdict = await _probe_authenticated(e164)
            if verdict == "available":
                verdict = await _probe_authenticated("0" + national)
        out.append({"name": NAME, "domain": DOMAIN,
                    "exists": verdict == "taken",
                    "rate_limited": verdict in ("ratelimit", "unknown"),
                    "error": "" if verdict in ("taken", "available") else verdict})
    except Exception as e:
        out.append({"name": NAME, "domain": DOMAIN, "exists": False,
                    "rate_limited": True, "error": str(e)[:120]})


# Uniform entry point: every site module exposes NAME, DOMAIN and check().
check = check_facebook
