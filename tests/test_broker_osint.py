"""Smoke test for Raven-Eye x user-scanner integration."""
from core.broker_osint import (
    extract_contacts,
    extract_profile_link,
    guess_usernames_from_email,
    is_available,
    resolve_binary,
    scan_username,
)
from core.db import DatabaseManager


def test_extract():
    text = ("شقة من المالك @broker_eg تواصل instagram.com/broker_eg "
            "أو على mail@example.com وشوف https://x.com/broker_eg")
    c = extract_contacts(text, "https://dubizzle.com.eg/ad/123")
    assert "mail@example.com" in c["emails"], c
    assert "broker_eg" in c["usernames"], c
    print("extract OK:", c)


def test_binary():
    b = resolve_binary()
    print("binary:", b, "available:", is_available())
    assert is_available(), "user-scanner binary not found"


def test_scan_single_module():
    r = scan_username("test", modules="github", timeout=120)
    assert r["ok"], r
    assert r["total_hits"] >= 1, r
    print(f"scan OK: {r['total_hits']}/{r['total_checked']}")


def test_db():
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        db = DatabaseManager(db_path=os.path.join(tmp, "t.db"))
        rid = db.save_osint_result("username", "test", 1, 1,
                                   [{"site_name": "Github"}], "")
        rows = db.get_osint_results()
        assert rid and rows and rows[0]["target"] == "test"
    print("db OK")


def test_guess_and_profile_link():
    g = guess_usernames_from_email("John.Doe99@gmail.com")
    assert "john.doe99" in g and "johndoe99" in g, g
    assert extract_profile_link({"url": "https://github.com/test", "extra": {}}) == "https://github.com/test"
    assert extract_profile_link({"url": "https://gravatar.com",
                                 "extra": {"profile_url": "https://gravatar.com/abc"}}) == "https://gravatar.com/abc"
    print("guess+profile_link OK:", g)


if __name__ == "__main__":
    test_extract()
    test_binary()
    test_scan_single_module()
    test_db()
    test_guess_and_profile_link()
    print("ALL BROKER_OSINT TESTS PASSED")
