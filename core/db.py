"""Database layer with dual backend.

- Local default: SQLite file (zero setup, tests, offline work).
- Online: PostgreSQL (Supabase) when a DATABASE_URL is found, so the
  Streamlit Cloud deployment shares one persistent database instead of
  an ephemeral local file.

URL resolution order: Streamlit secrets -> DATABASE_URL env var ->
config.json "database_url" -> None (SQLite fallback).

Postgres tables enable Row Level Security with NO grants to anon/
authenticated roles, so the Data API cannot reach them; only this
server-side code (owner connection string) reads/writes.
"""

import json
import os
from typing import Any, Dict, List, Optional


def resolve_database_url() -> Optional[str]:
    # 1. Streamlit Cloud secrets (works only inside streamlit runtime).
    try:
        import streamlit as st
        url = (st.secrets.get("DATABASE_URL", "") or "").strip()
        if url:
            return url
    except Exception:
        pass
    # 2. Environment variable (local dev, Render, bot process).
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url
    # 3. config.json (written by the Settings tab).
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                url = (json.load(f).get("database_url", "") or "").strip()
                if url:
                    return url
    except Exception:
        pass
    return None


def _dict_factory(cursor, row):
    return {d[0]: row[i] for i, d in enumerate(cursor.description)}


class DatabaseManager:
    def __init__(self, db_path: str = "raven_eye.db",
                 database_url: Optional[str] = None):
        if database_url is None:
            database_url = resolve_database_url()
        self.database_url = database_url
        self.use_pg = bool(database_url and "postgres" in database_url)
        self.db_path = db_path
        self._dup_exc: tuple = (Exception,)
        if self.use_pg:
            try:
                import psycopg.errors as _errs
                self._dup_exc = (_errs.UniqueViolation,)
            except Exception:
                pass
        else:
            import sqlite3
            self._dup_exc = (sqlite3.IntegrityError,)
        self._create_tables()

    @property
    def backend(self) -> str:
        return "postgres" if self.use_pg else "sqlite"

    # ---------- low-level ----------

    def _connect(self):
        if self.use_pg:
            import psycopg
            from psycopg.rows import dict_row
            return psycopg.connect(self.database_url, row_factory=dict_row)
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = _dict_factory
        return conn

    def _get_connection(self):
        return self._connect()

    @staticmethod
    def _q(sql: str, use_pg: bool) -> str:
        return sql.replace("?", "%s") if use_pg else sql

    def _execute(self, cursor, sql: str, params=()):
        cursor.execute(self._q(sql, self.use_pg), params)
        return cursor

    def _table_cols(self, cursor, table: str):
        if self.use_pg:
            cursor.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = %s", (table,))
            return {r["column_name"] for r in cursor.fetchall()}
        cursor.execute(f"PRAGMA table_info({table})")
        return {r["name"] for r in cursor.fetchall()}

    def _add_column(self, cursor, table: str, ddl: str):
        if self.use_pg:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {ddl}")
        else:
            cols = self._table_cols(cursor, table)
            name = ddl.split()[0]
            if name not in cols:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

    def _insert_returning_id(self, cursor) -> int:
        if self.use_pg:
            row = cursor.fetchone()
            return int(row["id"])
        return int(cursor.lastrowid)

    # ---------- schema ----------

    def _create_tables(self):
        id_col = ("id SERIAL PRIMARY KEY" if self.use_pg
                  else "id INTEGER PRIMARY KEY AUTOINCREMENT")
        ts = "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS properties (
                    {id_col},
                    source TEXT, title TEXT, url TEXT UNIQUE, price TEXT,
                    area TEXT, phone_number TEXT, location TEXT,
                    description TEXT, broker_type TEXT, images TEXT,
                    owner_label TEXT DEFAULT '',
                    owner_score INTEGER DEFAULT 0,
                    author TEXT DEFAULT '', author_url TEXT DEFAULT '',
                    {ts}
                )
            """)
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS broker_osint (
                    {id_col},
                    target_type TEXT, target TEXT,
                    total_hits INTEGER DEFAULT 0,
                    total_checked INTEGER DEFAULT 0,
                    hits_json TEXT, property_url TEXT, {ts}
                )
            """)
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS phone_osint (
                    {id_col},
                    phone TEXT, carrier TEXT, valid INTEGER DEFAULT 0,
                    accounts_json TEXT, property_url TEXT, {ts}
                )
            """)
            # Upgrades for pre-existing SQLite files.
            self._add_column(cur, "properties", "owner_label TEXT DEFAULT ''")
            self._add_column(cur, "properties", "owner_score INTEGER DEFAULT 0")
            self._add_column(cur, "properties", "author TEXT DEFAULT ''")
            self._add_column(cur, "properties", "author_url TEXT DEFAULT ''")
            if self.use_pg:
                # Block Data API access; owner connection is unaffected.
                for t in ("properties", "broker_osint", "phone_osint"):
                    cur.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
            conn.commit()

    # ---------- properties ----------

    def insert_property(self, property_data: Dict[str, Any]) -> bool:
        """
        Inserts a property into the database.
        Returns True if inserted, False if it was a duplicate (based on URL).
        """
        with self._connect() as conn:
            cur = conn.cursor()
            try:
                sql = """
                    INSERT INTO properties (source, title, url, price, area, phone_number, location, description, broker_type, images, author, author_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                if self.use_pg:
                    sql += " RETURNING id"
                self._execute(cur, sql, (
                    property_data.get('Source'),
                    property_data.get('Title'),
                    property_data.get('URL'),
                    property_data.get('Price'),
                    property_data.get('Area'),
                    property_data.get('Phone Number'),
                    property_data.get('Location'),
                    property_data.get('Description'),
                    property_data.get('Broker Type'),
                    property_data.get('Images'),
                    property_data.get('Author'),
                    property_data.get('Author URL')
                ))
                conn.commit()
                return True
            except self._dup_exc:
                # Duplicate URL
                try:
                    conn.rollback()
                except Exception:
                    pass
                return False

    def get_all_properties(self) -> List[Dict[str, Any]]:
        """
        Retrieves all properties from the database.
        """
        with self._connect() as conn:
            cur = conn.cursor()
            self._execute(cur, "SELECT * FROM properties ORDER BY created_at DESC")
            rows = cur.fetchall()

            results = []
            for row in rows:
                owner_label = row.get('owner_label', '') or ''
                owner_score = row.get('owner_score', 0) or 0
                author = row.get('author', '') or ''
                author_url = row.get('author_url', '') or ''
                created = row.get('created_at', '')
                results.append({
                    'Source': row.get('source'),
                    'Title': row.get('title'),
                    'URL': row.get('url'),
                    'Price': row.get('price'),
                    'Area': row.get('area'),
                    'Phone Number': row.get('phone_number'),
                    'Location': row.get('location'),
                    'Description': row.get('description'),
                    'Broker Type': row.get('broker_type'),
                    'Owner Label': owner_label,
                    'Owner Score': owner_score,
                    'Author': author,
                    'Author URL': author_url,
                    'Images': row.get('images'),
                    'Added On': created,
                })
            return results

    def set_classification(self, url: str, label: str,
                           broker_score: int = 0, owner_score: int = 0) -> bool:
        """Persist owner/broker classification for a saved listing URL."""
        with self._connect() as conn:
            cur = conn.cursor()
            self._execute(cur, """
                UPDATE properties SET owner_label = ?, owner_score = ?
                WHERE url = ?
            """, (label, int(broker_score) - int(owner_score), url))
            conn.commit()
            return cur.rowcount > 0

    # ---------- broker osint ----------

    def save_osint_result(self, target_type: str, target: str,
                          total_hits: int, total_checked: int,
                          hits: List[Dict[str, Any]],
                          property_url: str = "") -> int:
        """Persist one user-scanner result. Returns row id."""
        with self._connect() as conn:
            cur = conn.cursor()
            sql = """
                INSERT INTO broker_osint
                (target_type, target, total_hits, total_checked, hits_json, property_url)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            if self.use_pg:
                sql += " RETURNING id"
            self._execute(cur, sql, (
                target_type, target, int(total_hits), int(total_checked),
                json.dumps(hits or [], ensure_ascii=False),
                property_url or ""))
            conn.commit()
            return self._insert_returning_id(cur)

    def get_osint_results(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.cursor()
            self._execute(cur,
                          "SELECT * FROM broker_osint ORDER BY created_at DESC LIMIT ?",
                          (int(limit),))
            rows = cur.fetchall()
            out = []
            for row in rows:
                try:
                    hits = json.loads(row.get("hits_json") or "[]")
                except Exception:
                    hits = []
                out.append({
                    "id": row.get("id"),
                    "target_type": row.get("target_type"),
                    "target": row.get("target"),
                    "total_hits": row.get("total_hits"),
                    "total_checked": row.get("total_checked"),
                    "hits": hits,
                    "property_url": row.get("property_url"),
                    "created_at": row.get("created_at"),
                })
            return out

    # ---------- phone osint ----------

    def save_phone_osint(self, phone: str, carrier: str, valid: bool,
                         accounts: List[Dict[str, Any]],
                         property_url: str = "") -> int:
        """Persist one phone check. Returns row id."""
        with self._connect() as conn:
            cur = conn.cursor()
            sql = """
                INSERT INTO phone_osint
                (phone, carrier, valid, accounts_json, property_url)
                VALUES (?, ?, ?, ?, ?)
            """
            if self.use_pg:
                sql += " RETURNING id"
            self._execute(cur, sql, (
                phone, carrier or "", 1 if valid else 0,
                json.dumps(accounts or [], ensure_ascii=False),
                property_url or ""))
            conn.commit()
            return self._insert_returning_id(cur)

    def get_phone_osint(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.cursor()
            self._execute(cur,
                          "SELECT * FROM phone_osint ORDER BY created_at DESC LIMIT ?",
                          (int(limit),))
            rows = cur.fetchall()
            out = []
            for row in rows:
                try:
                    accounts = json.loads(row.get("accounts_json") or "[]")
                except Exception:
                    accounts = []
                out.append({
                    "id": row.get("id"),
                    "phone": row.get("phone"),
                    "carrier": row.get("carrier"),
                    "valid": bool(row.get("valid")),
                    "accounts": accounts,
                    "property_url": row.get("property_url"),
                    "created_at": row.get("created_at"),
                })
            return out

    def search_by_phone(self, variants: List[str]) -> List[Dict[str, Any]]:
        """Find saved listings whose phone matches any of the given variants."""
        variants = [v for v in (variants or []) if v]
        if not variants:
            return []
        with self._connect() as conn:
            cur = conn.cursor()
            conds = " OR ".join(["phone_number LIKE ?"] * len(variants))
            params = [f"%{v}%" for v in variants]
            self._execute(
                cur,
                f"SELECT * FROM properties WHERE {conds} ORDER BY created_at DESC LIMIT 50",
                params)
            rows = cur.fetchall()
            return [{
                "Title": r.get("title"),
                "URL": r.get("url"),
                "Source": r.get("source"),
                "Price": r.get("price"),
                "Broker Type": r.get("broker_type"),
                "Added On": r.get("created_at"),
            } for r in rows]
