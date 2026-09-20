"""Tests for Raven-Eye phone-site modules (facebook first)."""
import asyncio

import httpx

from core.phone_sites.facebook import (
    DOMAIN,
    NAME,
    check as fb_check,
    interpret_identify_body,
)


def test_interpret():
    assert interpret_identify_body('x "These accounts matched your search" y') == "taken"
    assert interpret_identify_body('{"redirectPageTo":"/x"}') == "taken"
    assert interpret_identify_body("No search results for that") == "available"
    assert interpret_identify_body("Your search did not return any results.") == "available"
    assert interpret_identify_body('error":3252001') == "ratelimit"
    assert interpret_identify_body("temporarily blocked you") == "ratelimit"
    assert interpret_identify_body("<html>login page</html>") == "unknown"
    assert interpret_identify_body("") == "unknown"
    print("interpret OK")


def test_module_contract():
    assert NAME == "facebook" and DOMAIN == "facebook.com"
    import inspect
    assert inspect.iscoroutinefunction(fb_check)
    print("contract OK")


def test_live_facebook_probe():
    # Synthetic number; any verdict shape is acceptable (network-dependent).
    async def go():
        out = []
        async with httpx.AsyncClient(timeout=20) as client:
            await fb_check("+201000000000", "1000000000", "20", client, out)
        return out

    out = asyncio.run(go())
    assert len(out) == 1 and out[0]["name"] == "facebook", out
    assert isinstance(out[0]["exists"], bool)
    assert isinstance(out[0]["rate_limited"], bool)
    print(f"live probe OK: exists={out[0]['exists']} limited={out[0]['rate_limited']}")


def test_merged_accounts():
    from core.phone_osint import check_accounts
    r = check_accounts("01000000000", timeout=25)
    assert r["ok"], r
    names = {x["name"] for x in r["results"]}
    assert {"amazon", "instagram", "snapchat", "facebook"} <= names, names
    print("merged OK:", sorted(names))


def test_footprint_sites_guard():
    from core.phone_osint import web_footprint_sites, FOOTPRINT_SITES
    assert len(FOOTPRINT_SITES) >= 4
    r = web_footprint_sites("01001234567", [])
    assert not r["ok"], r
    print("footprint guard OK")


if __name__ == "__main__":
    test_interpret()
    test_module_contract()
    test_live_facebook_probe()
    test_merged_accounts()
    test_footprint_sites_guard()
    print("ALL PHONE SITES TESTS PASSED")
