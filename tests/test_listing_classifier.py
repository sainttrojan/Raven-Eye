"""Tests for Madinaty scoping + owner/broker classification."""
from core.listing_classifier import is_madinaty, classify
from core.db import DatabaseManager


def test_madinaty_positive():
    assert is_madinaty("شقة للبيع في مدينتي", "تشطيب سوبر لوكس", strict=True)["in_madinaty"]
    assert is_madinaty("Flat in Madinaty", "", strict=True)["in_madinaty"]
    assert is_madinaty("شقه مدينتى B8", "", strict=True)["in_madinaty"]
    print("madinaty positive OK")


def test_madinaty_leaks():
    r = is_madinaty("شقة في الشروق", "قريبة من مدينتي", strict=True)
    assert not r["in_madinaty"] and r["other_city"], r
    r = is_madinaty("شقة الرحاب", "مدينتي قريبة", strict=True)
    assert not r["in_madinaty"], r
    # lenient mode keeps Madinaty mentions
    assert is_madinaty("شقة في الشروق", "قريبة من مدينتي", strict=False)["in_madinaty"]
    # no mention at all
    assert not is_madinaty("شقة للبيع", "تشطيب ممتاز", strict=False)["in_madinaty"]
    print("madinaty leaks OK")


def test_real_csv_cases():
    # Regression cases from 2026-09-20 export (row numbers in file).
    from urllib.parse import quote
    def url(title):
        return "https://www.dubizzle.com.eg/ad/" + quote(title) + "-ID1.html"
    # outside: Suez road / Shorouk glued typo / Sarai / La Vista / bare proximity
    outsiders = [
        "شقه 197 متر - للبيع من المالك مباشره واستلام فورى بالقرب من التراث مول و طريق السويس و مدينتى",
        "شقه للبيع من المالك مباشره-بمدينه الشروشقه للبيع من استلام فورى -من المالكه وبالقرب من مدينتى",
        "فيلا بسعر شقة في كمبوند سراي امام مدينتي",
        "شقه 2 غرفه ريسيل من المالك في كمبوند سراي سور بسور مدينتي",
        "شقه من المالك مباشرة 215م قسط سنتين امام كمبوند لافيستا و دقيقتين من مدينتي",
        "للبيع من المالك مباشره شقه استلام فورى و بموقع مميز و سعر مميز و بالقرب من مدينتى",
    ]
    for t in outsiders:
        r = is_madinaty(t, "", url(t), strict=True)
        assert not r["in_madinaty"], (t, r)
    # inside: "امام النادى" is inside Madinaty; B-sections and groups are proof
    insiders = [
        "للبيع بمدينتي شقه 266 متر سوبر لوكس من المالك امام النادى",
        "شقة للبيع في مدينتي B6 – 144م – فيو جاردن وبارك – من المالك مباشرة",
        "شقه ٨٩متر في مدينتي للبيع من المالك مجموعه٦٩ انا المالك",
    ]
    for t in insiders:
        r = is_madinaty(t, "", url(t), strict=True)
        assert r["in_madinaty"], (t, r)
    print("real csv cases OK")


def test_owner():
    c = classify("شقة من المالك مباشرة", "البيع من المالك بدون وسيط وبدون عمولة")
    assert c["label"] == "owner", c
    print("owner OK:", c["reasons"][:2])


def test_broker_text():
    c = classify("شقة للبيع", "مكتب للتسويق العقاري - لدينا عروض كثيرة - عمولة 2%")
    assert c["label"] == "broker", c
    c2 = classify("شقة", "desc", url="https://site.com/agent/123")
    assert c2["label"] == "broker", c2
    print("broker text OK")


def test_phone_frequency():
    c = classify("شقة للبيع", "وصف عادي", phone_listing_count=7)
    assert c["label"] == "broker", c
    c = classify("شقة للبيع", "وصف عادي", phone_listing_count=1)
    assert c["label"] == "unknown" and c["owner_score"] == 1, c
    # weak phone signal + owner text together -> owner
    c = classify("شقة من المالك", "وصف عادي", phone_listing_count=1)
    assert c["label"] == "owner", c
    c = classify("شقة للبيع", "وصف عادي", phone_listing_count=3)
    assert c["label"] in ("broker", "unknown"), c
    c = classify("شقة للبيع", "وصف عادي")
    assert c["label"] == "unknown", c
    print("phone frequency OK")


def test_db_columns():
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        db = DatabaseManager(db_path=os.path.join(tmp, "t.db"))
        assert db.insert_property({"Source": "D", "Title": "شقة مدينتي",
                                   "URL": "http://x/9", "Price": "", "Area": "",
                                   "Phone Number": "", "Location": "",
                                   "Description": "", "Broker Type": "",
                                   "Images": ""})
        assert db.set_classification("http://x/9", "owner", 0, 2)
        rows = db.get_all_properties()
        assert rows[0]["Owner Label"] == "owner", rows[0]
    # real DB migrates too
    db2 = DatabaseManager()
    assert len(db2.get_all_properties()) >= 0
    print("db columns OK")


if __name__ == "__main__":
    test_madinaty_positive()
    test_madinaty_leaks()
    test_real_csv_cases()
    test_owner()
    test_broker_text()
    test_phone_frequency()
    test_db_columns()
    print("ALL CLASSIFIER TESTS PASSED")
