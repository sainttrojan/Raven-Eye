"""Tests for Google Sheets sync (no network: stub db + worksheet)."""
from core.sheets_sync import HEADERS, build_row, existing_urls, lead_type, sync_database


PROP = {"Added On": "2026-09-21", "Title": "شقة B7", "Price": "5 مليون",
        "Area": "120م", "Phone Number": "01001234567", "Owner Label": "مالك",
        "Author": "", "Source": "Dubizzle", "URL": "http://x/1",
        "Description": "وصف"}


def test_build_row():
    row = build_row(PROP)
    assert len(row) == len(HEADERS) == 11, row
    assert row[0] == "2026-09-21" and row[-1] == "new"
    assert row[HEADERS.index("URL")] == "http://x/1"
    print("build_row OK")


class FakeWS:
    def __init__(self, values):
        self.values = values
        self.appended = []

    def get_all_values(self):
        return self.values

    def append_rows(self, rows, value_input_option=None):
        self.appended.extend(rows)
        self.values.extend([list(map(str, r)) for r in rows])


class FakeDB:
    def __init__(self, props):
        self.props = props

    def get_all_properties(self):
        return self.props


def test_existing_urls():
    ws = FakeWS([HEADERS, ["", "", "", "", "", "", "", "", "http://x/1", "", "new"]])
    assert existing_urls(ws) == {"http://x/1"}
    assert existing_urls(FakeWS([])) == set()
    assert existing_urls(FakeWS([["A", "B"]])) == set()
    print("existing_urls OK")


def test_sync_dedupe(monkeypatch=None):
    import core.sheets_sync as mod
    orig_client, orig_ws = mod._client, mod._worksheet
    ws = FakeWS([HEADERS, ["", "", "", "", "", "", "", "", "http://x/1", "", "old"]])
    mod._worksheet = lambda client, sid, name="Sale", headers=None: ws
    mod._client = lambda creds: object()
    db = FakeDB([PROP, dict(PROP, URL="http://x/2", Title="شقة2")])
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        creds = f.name
    try:
        r = sync_database(db, "sheet123", creds)
        assert r["ok"] and r["pushed"] == 1 and r["skipped"] == 1, r
        assert ws.appended and ws.appended[0][HEADERS.index("URL")] == "http://x/2"
    finally:
        os.unlink(creds)
        mod._client, mod._worksheet = orig_client, orig_ws
    print("sync dedupe OK")


def test_sync_guards():
    r = sync_database(FakeDB([]), "", "/tmp/none.json")
    assert not r["ok"]
    r = sync_database(FakeDB([]), "sid", "/tmp/definitely-not-here.json")
    assert not r["ok"]
    print("guards OK")


def test_lead_type():
    assert lead_type({"Title": "شقة للبيع مدينتي", "Description": ""}) == "sale"
    assert lead_type({"Title": "شقة للإيجار مدينتي", "Description": ""}) == "rent"
    assert lead_type({"Title": "شقة مفروشة", "Description": ""}) == "rent"
    assert lead_type({"Title": "شقة", "Description": "تشطيب ممتاز"}) == "other"
    print("lead_type OK")


class SheetDB:
    def __init__(self):
        self.sheets = {}

    def sheet(self, name, values):
        ws = FakeWS(values)
        self.sheets[name] = ws
        return ws


def test_split_and_osint_and_log():
    import core.sheets_sync as mod
    orig_client = mod._client
    store = SheetDB()
    mod._client = lambda creds: object()
    orig_ws = mod._worksheet

    def fake_ws(client, sid, name="Sale", headers=None):
        from core.sheets_sync import HEADERS as H
        if name not in store.sheets:
            store.sheets[name] = FakeWS([headers or H])
        return store.sheets[name]

    mod._worksheet = fake_ws
    try:
        sale = dict(PROP, URL="http://s/1", Title="شقة للبيع")
        rent = dict(PROP, URL="http://r/1", Title="شقة للإيجار")
        other = dict(PROP, URL="http://o/1", Title="شقة")
        db = FakeDB([sale, rent, other])

        class FullDB(FakeDB):
            def get_osint_results(self, limit=500):
                return [{"target_type": "username", "target": "u1",
                         "total_hits": 2, "total_checked": 10,
                         "hits": [{"site_name": "Github"}], "property_url": "",
                         "created_at": "2026-01-01"}]

            def get_phone_osint(self, limit=500):
                return [{"phone": "+2010", "carrier": "Vodafone", "valid": True,
                         "accounts": [{"domain": "instagram", "exists": True}],
                         "property_url": "", "created_at": "2026-01-02"}]

        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            creds = f.name
        try:
            from core.sheets_sync import sync_osint, log_wa_send
            r = sync_database(FullDB([sale, rent, other]), "sid", creds)
            assert r["ok"] and r["pushed"] == 3, r
            assert r["by_sheet"] == {"Sale": 1, "Rent": 1, "Other": 1}, r
            r = sync_database(FullDB([sale]), "sid", creds)
            assert r["pushed"] == 0 and r["skipped"] == 1, r
            o = sync_osint(FullDB([]), "sid", creds)
            assert o["ok"] and o["pushed"] == 2, o
            o = sync_osint(FullDB([]), "sid", creds)
            assert o["pushed"] == 0, o
            w = log_wa_send("sid", creds,
                            [{"target": "2010", "ok": True, "error": ""}], "msg")
            assert w["ok"] and w["logged"] == 1, w
        finally:
            os.unlink(creds)
    finally:
        mod._client, mod._worksheet = orig_client, orig_ws
    print("split+osint+log OK")


if __name__ == "__main__":
    test_build_row()
    test_existing_urls()
    test_sync_dedupe()
    test_sync_guards()
    test_lead_type()
    test_split_and_osint_and_log()
    print("ALL SHEETS TESTS PASSED")
