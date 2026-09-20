"""Fast orchestration test: limited modules, no full scans."""
import tempfile, os
from core.db import DatabaseManager
from core.deep_investigate import investigate


def test_empty():
    r = investigate()
    assert r["phone"] is None and r["email"] is None and r["usernames"] == []
    assert r["summary"]["total_hits"] == 0
    print("empty OK")


def test_limited():
    with tempfile.TemporaryDirectory() as tmp:
        db = DatabaseManager(db_path=os.path.join(tmp, "t.db"))
        r = investigate(phone="01001234567", email="test@gmail.com",
                        email_modules="gravatar", username_modules="github",
                        phone_timeout=20, scan_timeout=300, db=db)
        assert r["phone"] and r["phone"]["ok"], r["phone"]
        assert r["email"] and r["email"]["ok"], r["email"]
        assert len(r["usernames"]) >= 1 and r["usernames"][0]["ok"], r["usernames"]
        assert "phone" in r["summary"]["engines"] and "email" in r["summary"]["engines"]
        assert r["summary"]["total_hits"] >= 1, r["summary"]
        assert len(db.get_osint_results()) >= 2  # email + username saved
        print("limited OK:", r["summary"])


if __name__ == "__main__":
    test_empty()
    test_limited()
    print("ALL DEEP INVESTIGATE TESTS PASSED")
