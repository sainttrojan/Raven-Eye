"""Tests for Facebook Marketplace source (no browser / no login needed)."""
import asyncio
import os
import tempfile

from scrapers.facebook import FacebookScraper, parse_card
from core.fb_session import FacebookNotLoggedIn, run_facebook_search
from core.listing_classifier import is_madinaty, classify


def test_parse_full_card():
    c = parse_card("/marketplace/item/123456789/",
                   ["EGP 3,150,000", "شقة 197م مدينتي من المالك", "Madinaty, Cairo"])
    assert c and c.title == "شقة 197م مدينتي من المالك"
    assert c.price == "EGP 3,150,000" and c.location == "Madinaty, Cairo"
    assert c.url == "https://www.facebook.com/marketplace/item/123456789/"
    assert c.source == "Facebook Marketplace"
    print("parse full OK")


def test_parse_short_cards():
    c = parse_card("/marketplace/item/1/", ["5,000,000 ج.م", "شقة مدينتي"])
    assert c and c.title == "شقة مدينتي" and c.price == "5,000,000 ج.م"
    c = parse_card("https://www.facebook.com/marketplace/item/2/", ["عنوان فقط"])
    assert c and c.title == "عنوان فقط"
    assert parse_card("/marketplace/search/?query=x", ["a", "b", "c"]) is None
    assert parse_card("", ["a"]) is None
    print("parse short/bad OK")


def test_scraper_needs_page():
    async def go():
        try:
            await FacebookScraper(None).search("شقة مدينتي")
            return False
        except RuntimeError:
            return True
    assert asyncio.run(go())
    print("needs-page OK")


def test_no_session_clean_error():
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            try:
                run_facebook_search("شقة مدينتي", max_pages=1)
                raise AssertionError("should have raised")
            except FacebookNotLoggedIn as e:
                assert "fb_login" in str(e), e
        finally:
            os.chdir(cwd)
    print("no-session error OK")


def test_fb_result_pipeline():
    c = parse_card("/marketplace/item/9/",
                   ["6,000,000 ج.م", "شقة مدينتي B11 من المالك", "Madinaty"])
    d = c.to_dict()
    geo = is_madinaty(d["Title"], d.get("Description") or "", d["URL"], strict=True)
    assert geo["in_madinaty"], geo
    cls = classify(d["Title"], "", d["URL"])
    assert cls["label"] == "owner", cls
    print("pipeline OK")


if __name__ == "__main__":
    test_parse_full_card()
    test_parse_short_cards()
    test_scraper_needs_page()
    test_no_session_clean_error()
    test_fb_result_pipeline()
    print("ALL FACEBOOK TESTS PASSED")
