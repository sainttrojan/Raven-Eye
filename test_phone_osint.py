"""Smoke test for Raven-Eye x ignorant/phone integration."""
from core.phone_osint import normalize, analyze, deep_links, check_accounts
from core.phone_osint import phone_variants, find_in_database, web_footprint
from core.db import DatabaseManager


def test_normalize():
    assert normalize("01001234567")["e164"] == "+201001234567"
    assert normalize("+201001234567")["e164"] == "+201001234567"
    assert normalize("00201001234567")["e164"] == "+201001234567"
    assert normalize("+2001001234567")["e164"] == "+201001234567"  # trunk zero tolerance
    assert normalize("0100 123 4567")["e164"] == "+201001234567"
    assert not normalize("12345")["ok"]
    assert not normalize("011112345678")["ok"]
    print("normalize OK")


def test_analyze_offline():
    r = analyze("01001234567")
    assert r["ok"] and r["valid"] and r["carrier"], r
    assert r["e164"] == "+201001234567"
    print(f"analyze OK: carrier={r['carrier']} type={r['number_type']}")


def test_links():
    links = deep_links("01001234567")
    assert links["whatsapp"] == "https://wa.me/201001234567", links
    assert "telegram" in links and "truecaller" in links
    print("links OK:", links)


def test_accounts_live():
    # Synthetic number; asserts structure only (exists may be True/False/rate-limited)
    r = check_accounts("01000000000", timeout=20)
    assert r["ok"], r
    names = {x["name"] for x in r["results"]}
    assert names == {"amazon", "instagram", "snapchat"}, r
    for x in r["results"]:
        assert isinstance(x["exists"], bool) and isinstance(x["rate_limited"], bool)
    print("accounts OK:", [(x["name"], x["exists"], x["rate_limited"]) for x in r["results"]])


def test_db():
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        db = DatabaseManager(db_path=os.path.join(tmp, "t.db"))
        rid = db.save_phone_osint("+201001234567", "Vodafone", True,
                                  [{"name": "instagram"}], "")
        rows = db.get_phone_osint()
        assert rid and rows and rows[0]["phone"] == "+201001234567"
        # internal correlation: insert listings with mixed phone formats
        assert db.insert_property({"Source": "Dubizzle", "Title": "شقة",
                                   "URL": "http://x/1", "Price": "", "Area": "",
                                   "Phone Number": "01001234567", "Location": "",
                                   "Description": "", "Broker Type": "broker",
                                   "Images": ""})
        assert db.insert_property({"Source": "FB", "Title": "شقة2",
                                   "URL": "http://x/2", "Title2": "",
                                   "Price": "", "Area": "",
                                   "Phone Number": "+201001234567", "Location": "",
                                   "Description": "", "Broker Type": "owner",
                                   "Images": ""})
        corr = find_in_database("01001234567", db)
        assert corr["ok"] and corr["count"] == 2, corr
        assert corr["sources"].get("Dubizzle") == 1
    print("db + correlation OK")


def test_web_footprint_no_keys():
    r = web_footprint("01001234567", [])
    assert not r["ok"] and "ScraperAPI" in r["error"], r
    print("web footprint guard OK")


if __name__ == "__main__":
    test_normalize()
    test_analyze_offline()
    test_links()
    test_accounts_live()
    test_db()
    test_web_footprint_no_keys()
    print("ALL PHONE_OSINT TESTS PASSED")
