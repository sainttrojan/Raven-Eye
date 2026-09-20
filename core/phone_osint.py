"""Phone OSINT for Raven-Eye.

Two layers (both free, no API keys):
  1. Offline analysis via `phonenumbers` (Google libphonenumber):
     validity, carrier (Vodafone/Orange/Etisalat/WE), region, type.
     Instant — safe to run on every number scraped from listings.
  2. Account checks via `ignorant` library (amazon / instagram / snapchat):
     tells whether the number is registered on those platforms.
     Ignorant does NOT alert the target number. Can hit rate limits —
     results then come back as rate_limited instead of failing.

Plus investigation deep-links (WhatsApp / Telegram / Truecaller) that the
analyst can open manually.

Egyptian input handling: accepts 01xxxxxxxxx, +201xxxxxxxxx, 00201...,
with spaces or dashes, and normalizes to E.164.
"""

import re
from typing import Any, Dict, List, Optional

try:
    import phonenumbers
    from phonenumbers import carrier as _carrier
    from phonenumbers import geocoder as _geocoder
    from phonenumbers import timezone as _tz
    _HAS_PHONENUMBERS = True
except ImportError:
    _HAS_PHONENUMBERS = False

EG_MOBILE_RE = re.compile(r"^(?:\+?20|0020|0)?(1[0125]\d{8})$")


def normalize(raw: str) -> Dict[str, Any]:
    """Normalize an Egyptian mobile number to E.164 parts.

    Returns {"ok": bool, "e164": "+2010...", "country_code": "20",
             "national": "1001234567", "error": "..."}.
    """
    digits = re.sub(r"[\s\-().]", "", (raw or "").strip())
    if digits.startswith("0020"):
        digits = "+20" + digits[4:]
    m = EG_MOBILE_RE.match(digits)
    if not m:
        # tolerate a trunk zero pasted after the country code: +20010... / 20010...
        m = re.match(r"^(?:\+?20)0(1[0125]\d{8})$", digits)
    if not m:
        return {"ok": False, "error": "رقم مصري غير صالح (المتوقع: 01xxxxxxxxx أو +20...)"}
    national = m.group(1)
    return {"ok": True, "e164": f"+20{national}", "country_code": "20",
            "national": national}


def analyze(raw: str) -> Dict[str, Any]:
    """Offline number analysis. Never touches the network."""
    norm = normalize(raw)
    if not norm["ok"]:
        return norm
    if not _HAS_PHONENUMBERS:
        return {"ok": False, "error": "مكتبة phonenumbers غير مثبتة"}
    try:
        num = phonenumbers.parse(norm["e164"])
    except Exception as e:
        return {"ok": False, "error": f"تعذر تحليل الرقم: {e}"}
    ntype = phonenumbers.number_type(num)
    type_label = {0: "ثابت", 1: "موبايل", 2: "ثابت", 3: "VoIP",
                  4: "مجاني", 5: "مميز", 6: "SMS", 7: "shared",
                  8: "VoIP", 9: "شخصي", 10: "pagers"}.get(int(ntype), "غير معروف")
    return {
        "ok": True,
        "e164": norm["e164"],
        "national": norm["national"],
        "country_code": norm["country_code"],
        "valid": phonenumbers.is_valid_number(num),
        "possible": phonenumbers.is_possible_number(num),
        "carrier": _carrier.name_for_number(num, "en") or "غير معروف",
        "region": _geocoder.description_for_number(num, "en") or "Egypt",
        "number_type": type_label,
        "timezones": list(_tz.time_zones_for_number(num)) or [],
    }


def check_accounts(raw: str, timeout: int = 15) -> Dict[str, Any]:
    """Check number registration on amazon/instagram/snapchat via ignorant.

    Returns {"ok": True, "results": [{"name","domain","exists","rate_limited"}]}.
    """
    norm = normalize(raw)
    if not norm["ok"]:
        return norm
    try:
        import trio
        import httpx
        from ignorant.modules.shopping.amazon import amazon
        from ignorant.modules.social_media.instagram import instagram
        from ignorant.modules.social_media.snapchat import snapchat
    except ImportError as e:
        return {"ok": False, "error": f"مكتبة ignorant غير مثبتة: {e}"}

    modules = [("amazon", "amazon.com", amazon),
               ("instagram", "instagram.com", instagram),
               ("snapchat", "snapchat.com", snapchat)]

    async def _run_one(name, domain, func, phone, cc, client, out):
        try:
            await func(phone, cc, client, out)
        except Exception:
            out.append({"name": name, "domain": domain,
                        "rateLimit": True, "exists": False})

    async def _main():
        out: List[Dict[str, Any]] = []
        client = httpx.AsyncClient(timeout=timeout)
        try:
            async with trio.open_nursery() as nursery:
                for name, domain, func in modules:
                    nursery.start_soon(_run_one, name, domain, func,
                                       norm["national"], norm["country_code"],
                                       client, out)
        finally:
            await client.aclose()
        return sorted(out, key=lambda d: d.get("name", ""))

    try:
        raw_out = trio.run(_main)
    except Exception as e:
        return {"ok": False, "error": f"فشل فحص الحسابات: {e}"}

    # Raven-Eye's own phone-site modules (facebook, ...) run on asyncio.
    try:
        import asyncio as _asyncio
        from core.phone_sites import module_list as _phone_modules

        async def _main2():
            out2: List[Dict[str, Any]] = []

            async def _run_mod(mod):
                try:
                    await mod.check(norm["e164"], norm["national"],
                                    norm["country_code"], client2, out2)
                except Exception as e:
                    out2.append({"name": getattr(mod, "NAME", "?"),
                                 "domain": getattr(mod, "DOMAIN", ""),
                                 "exists": False, "rate_limited": True,
                                 "error": str(e)[:120]})

            client2 = httpx.AsyncClient(timeout=timeout)
            try:
                async with _asyncio.TaskGroup() as tg:
                    for mod in _phone_modules():
                        tg.create_task(_run_mod(mod))
            except Exception:
                pass
            finally:
                await client2.aclose()
            return out2

        try:
            raw_out = list(raw_out) + _asyncio.run(_main2())
        except Exception:
            pass
    except Exception:
        pass

    results = [{"name": d.get("name", ""), "domain": d.get("domain", ""),
                "exists": bool(d.get("exists", False)),
                "rate_limited": bool(d.get("rateLimit", d.get("rate_limited", False)))}
               for d in raw_out]
    results.sort(key=lambda d: d.get("name", ""))
    return {"ok": True, "e164": norm["e164"], "results": results,
            "hits": [r for r in results if r["exists"]]}


def deep_links(raw: str) -> Dict[str, str]:
    """Manual-investigation links for a number (open in browser)."""
    norm = normalize(raw)
    if not norm["ok"]:
        return {}
    digits = norm["e164"].lstrip("+")
    return {
        "whatsapp": f"https://wa.me/{digits}",
        "telegram": f"https://t.me/+{digits}",
        "truecaller": f"https://www.truecaller.com/search/eg/{digits}",
        "google": f"https://www.google.com/search?q=%22{norm['e164']}%22",
    }


def full_check(raw: str, with_accounts: bool = True,
               timeout: int = 15) -> Dict[str, Any]:
    """Offline analysis + optional ignorant account check + deep links."""
    info = analyze(raw)
    if not info["ok"]:
        return info
    info["links"] = deep_links(raw)
    if with_accounts:
        acc = check_accounts(raw, timeout=timeout)
        info["accounts"] = acc.get("results", []) if acc.get("ok") else []
        info["accounts_error"] = acc.get("error", "")
    else:
        info["accounts"] = []
        info["accounts_error"] = ""
    return info


def phone_variants(raw: str) -> List[str]:
    """All stored-format variants of a number for DB/web matching."""
    norm = normalize(raw)
    if not norm["ok"]:
        return []
    national = norm["national"]
    return [national, f"0{national}", norm["e164"], f"0020{national}"]


def find_in_database(raw: str, db=None) -> Dict[str, Any]:
    """Correlate a number with listings already saved in raven_eye.db.

    Answers: is this number already in our radar? How many ads? Which
    sources? Owner or broker? Instant and fully offline.
    """
    norm = normalize(raw)
    if not norm["ok"]:
        return norm
    try:
        if db is None:
            from core.db import DatabaseManager
            db = DatabaseManager()
        listings = db.search_by_phone(phone_variants(raw))
    except Exception as e:
        return {"ok": False, "error": f"تعذر البحث في قاعدة البيانات: {e}"}
    sources: Dict[str, int] = {}
    for li in listings:
        s = li.get("Source") or "غير معروف"
        sources[s] = sources.get(s, 0) + 1
    return {"ok": True, "e164": norm["e164"], "count": len(listings),
            "sources": sources, "listings": listings}


def web_footprint(raw: str, api_keys, max_pages: int = 2) -> Dict[str, Any]:
    """Search the public web for exact mentions of the number.

    Uses Raven-Eye's own GoogleScraper (ScraperAPI credits apply).
    Finds the number in indexed ads, posts and directories.
    """
    import asyncio
    norm = normalize(raw)
    if not norm["ok"]:
        return norm
    if not api_keys:
        return {"ok": False, "error": "لا توجد مفاتيح ScraperAPI"}
    try:
        from scrapers.google import GoogleScraper
    except ImportError as e:
        return {"ok": False, "error": f"تعذر تحميل سكرابر جوجل: {e}"}
    query = f'"{norm["national"]}" OR "{norm["e164"]}"'
    try:
        scraper = GoogleScraper(api_keys if isinstance(api_keys, list) else [api_keys])
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(scraper.search(query, "", max_pages=max_pages))
        finally:
            loop.close()
        items = [r.to_dict() for r in (results or [])]
        return {"ok": True, "e164": norm["e164"], "count": len(items), "items": items}
    except Exception as e:
        return {"ok": False, "error": f"فشل البحث: {e}"}


# Sites worth checking individually for number mentions (Egypt-focused).
FOOTPRINT_SITES = ["facebook.com", "dubizzle.com", "olx.com.eg",
                   "propertyfinder.eg", "aqarmap.com"]


def web_footprint_sites(raw: str, api_keys,
                        sites: Optional[List[str]] = None) -> Dict[str, Any]:
    """Per-site web footprint: where exactly does the number appear?

    One quoted search per site (1 page each — each costs ScraperAPI
    credit). Returns {"ok", "e164", "sites": {site: {"count", "items", "error"}}}.
    This is the honest website-by-website phone search: public mentions
    per platform, complementing registration checks.
    """
    import asyncio
    norm = normalize(raw)
    if not norm["ok"]:
        return norm
    if not api_keys:
        return {"ok": False, "error": "لا توجد مفاتيح ScraperAPI"}
    try:
        from scrapers.google import GoogleScraper
    except ImportError as e:
        return {"ok": False, "error": f"تعذر تحميل سكرابر جوجل: {e}"}
    keys = api_keys if isinstance(api_keys, list) else [api_keys]
    out: Dict[str, Any] = {}
    try:
        scraper = GoogleScraper(keys)
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            for site in (sites or FOOTPRINT_SITES):
                try:
                    res = loop.run_until_complete(
                        scraper.search(f'"{norm["e164"]}" site:{site}', "", max_pages=1))
                    items = [r.to_dict() for r in (res or [])]
                    out[site] = {"count": len(items), "items": items[:10], "error": ""}
                except Exception as e:
                    out[site] = {"count": 0, "items": [], "error": str(e)[:120]}
        finally:
            loop.close()
    except Exception as e:
        return {"ok": False, "error": f"فشل البحث: {e}"}
    return {"ok": True, "e164": norm["e164"], "sites": out}
