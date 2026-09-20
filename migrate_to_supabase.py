"""One-shot migration: local raven_eye.db (SQLite) -> Supabase Postgres.

Usage:
    DATABASE_URL="postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres" \\
        venv/bin/python migrate_to_supabase.py [sqlite_path]

Creates the schema on first connect (DatabaseManager does that) and
copies every row. Safe to re-run: property duplicates are skipped by URL.
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db import DatabaseManager  # noqa: E402


def main():
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        print("Set DATABASE_URL first (Supabase dashboard > Project Settings > Database > Connection string).")
        sys.exit(1)
    src = sys.argv[1] if len(sys.argv) > 1 else "raven_eye.db"
    if not os.path.exists(src):
        print(f"SQLite file not found: {src}")
        sys.exit(1)

    dst = DatabaseManager(database_url=url)
    print(f"Target backend: {dst.backend}")
    con = sqlite3.connect(src)
    con.row_factory = sqlite3.Row

    props = [dict(r) for r in con.execute("SELECT * FROM properties")]
    moved = dup = 0
    for p in props:
        ok = dst.insert_property({
            'Source': p['source'], 'Title': p['title'], 'URL': p['url'],
            'Price': p['price'], 'Area': p['area'],
            'Phone Number': p['phone_number'], 'Location': p['location'],
            'Description': p['description'], 'Broker Type': p['broker_type'],
            'Images': p['images'],
            'Author': p['author'] if 'author' in p.keys() else None,
            'Author URL': p['author_url'] if 'author_url' in p.keys() else None,
        })
        if ok:
            moved += 1
            if p['owner_label'] if 'owner_label' in p.keys() else '':
                dst.set_classification(
                    p['url'], p['owner_label'],
                    max(0, p['owner_score'] or 0), 0)
        else:
            dup += 1
    print(f"properties: {moved} moved, {dup} duplicates skipped")

    for table, saver in (("broker_osint", None), ("phone_osint", None)):
        rows = [dict(r) for r in con.execute(f"SELECT * FROM {table}")]
        n = 0
        for r in rows:
            if table == "broker_osint":
                dst.save_osint_result(r['target_type'], r['target'],
                                      r['total_hits'], r['total_checked'],
                                      __import__('json').loads(r['hits_json'] or '[]'),
                                      r['property_url'])
            else:
                dst.save_phone_osint(r['phone'], r['carrier'],
                                     bool(r['valid']),
                                     __import__('json').loads(r['accounts_json'] or '[]'),
                                     r['property_url'])
            n += 1
        print(f"{table}: {n} moved")
    print("DONE")


if __name__ == "__main__":
    main()
