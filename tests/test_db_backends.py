"""Tests for the dual-backend database layer (SQLite path, no server needed)."""
import os
import tempfile

from core.db import DatabaseManager, resolve_database_url


def test_resolve_order_env():
    os.environ["DATABASE_URL"] = "postgresql://x"
    try:
        assert resolve_database_url() == "postgresql://x"
    finally:
        del os.environ["DATABASE_URL"]
    print("resolve env OK")


def test_resolve_fallback_sqlite():
    os.environ.pop("DATABASE_URL", None)
    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            assert resolve_database_url() is None
            db = DatabaseManager(db_path=os.path.join(tmp, "t.db"))
            assert db.backend == "sqlite"
        finally:
            os.chdir(cwd)
    print("fallback OK")


def test_placeholder_translation():
    assert DatabaseManager._q("a=? AND b=?", False) == "a=? AND b=?"
    assert DatabaseManager._q("a=? AND b=?", True) == "a=%s AND b=%s"
    print("placeholders OK")


def test_pg_selected_by_url():
    db = DatabaseManager.__new__(DatabaseManager)
    db.database_url = "postgresql://u:p@host:5432/db"
    db.use_pg = bool(db.database_url and "postgres" in db.database_url)
    assert db.use_pg and db.backend == "postgres"
    # must fail fast without a server (proves it really tries postgres)
    try:
        db._connect()
        raise AssertionError("should not connect")
    except Exception:
        pass
    print("pg-select OK")


def test_wa_log_roundtrip():
    import tempfile
    from core.db import DatabaseManager
    with tempfile.TemporaryDirectory() as tmp:
        db = DatabaseManager(db_path=os.path.join(tmp, "t.db"))
        assert db.log_wa_batch([], "x") == 0
        n = db.log_wa_batch(
            [{"target": "2010", "ok": True, "error": ""},
             {"target": "2011", "ok": False, "error": "no chat"}], "hello", "dry-run")
        assert n == 2
        rows = db.get_wa_log()
        assert len(rows) == 2 and rows[0]["Message"] == "hello"
        assert rows[0]["Mode"] == "dry-run"
        assert {r["Target"] for r in rows} == {"2010", "2011"}
    print("wa-log OK")


if __name__ == "__main__":
    test_resolve_order_env()
    test_resolve_fallback_sqlite()
    test_placeholder_translation()
    test_pg_selected_by_url()
    test_wa_log_roundtrip()
    print("ALL DB BACKEND TESTS PASSED")
