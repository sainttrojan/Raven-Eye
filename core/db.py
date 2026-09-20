import sqlite3
import json
from typing import List, Dict, Any

class DatabaseManager:
    def __init__(self, db_path: str = "raven_eye.db"):
        self.db_path = db_path
        self._create_tables()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS properties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT,
                    title TEXT,
                    url TEXT UNIQUE,
                    price TEXT,
                    area TEXT,
                    phone_number TEXT,
                    location TEXT,
                    description TEXT,
                    broker_type TEXT,
                    images TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS broker_osint (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_type TEXT,
                    target TEXT,
                    total_hits INTEGER DEFAULT 0,
                    total_checked INTEGER DEFAULT 0,
                    hits_json TEXT,
                    property_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS phone_osint (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT,
                    carrier TEXT,
                    valid INTEGER DEFAULT 0,
                    accounts_json TEXT,
                    property_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def insert_property(self, property_data: Dict[str, Any]) -> bool:
        """
        Inserts a property into the database.
        Returns True if inserted, False if it was a duplicate (based on URL).
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO properties (source, title, url, price, area, phone_number, location, description, broker_type, images)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    property_data.get('Source'),
                    property_data.get('Title'),
                    property_data.get('URL'),
                    property_data.get('Price'),
                    property_data.get('Area'),
                    property_data.get('Phone Number'),
                    property_data.get('Location'),
                    property_data.get('Description'),
                    property_data.get('Broker Type'),
                    property_data.get('Images')
                ))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Duplicate URL
                return False

    def get_all_properties(self) -> List[Dict[str, Any]]:
        """
        Retrieves all properties from the database.
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM properties ORDER BY created_at DESC")
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    'Source': row['source'],
                    'Title': row['title'],
                    'URL': row['url'],
                    'Price': row['price'],
                    'Area': row['area'],
                    'Phone Number': row['phone_number'],
                    'Location': row['location'],
                    'Description': row['description'],
                    'Broker Type': row['broker_type'],
                    'Images': row['images'],
                    'Added On': row['created_at']
                })
            return results

    def save_osint_result(self, target_type: str, target: str,
                          total_hits: int, total_checked: int,
                          hits: List[Dict[str, Any]],
                          property_url: str = "") -> int:
        """Persist one user-scanner result. Returns row id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO broker_osint
                (target_type, target, total_hits, total_checked, hits_json, property_url)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (target_type, target, int(total_hits), int(total_checked),
                  json.dumps(hits or [], ensure_ascii=False),
                  property_url or ""))
            conn.commit()
            return int(cursor.lastrowid)

    def get_osint_results(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM broker_osint ORDER BY created_at DESC LIMIT ?",
                (int(limit),))
            rows = cursor.fetchall()
            out = []
            for row in rows:
                try:
                    hits = json.loads(row["hits_json"] or "[]")
                except Exception:
                    hits = []
                out.append({
                    "id": row["id"],
                    "target_type": row["target_type"],
                    "target": row["target"],
                    "total_hits": row["total_hits"],
                    "total_checked": row["total_checked"],
                    "hits": hits,
                    "property_url": row["property_url"],
                    "created_at": row["created_at"],
                })
            return out

    def save_phone_osint(self, phone: str, carrier: str, valid: bool,
                         accounts: List[Dict[str, Any]],
                         property_url: str = "") -> int:
        """Persist one phone check. Returns row id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO phone_osint
                (phone, carrier, valid, accounts_json, property_url)
                VALUES (?, ?, ?, ?, ?)
            """, (phone, carrier or "", 1 if valid else 0,
                  json.dumps(accounts or [], ensure_ascii=False),
                  property_url or ""))
            conn.commit()
            return int(cursor.lastrowid)

    def get_phone_osint(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM phone_osint ORDER BY created_at DESC LIMIT ?",
                (int(limit),))
            rows = cursor.fetchall()
            out = []
            for row in rows:
                try:
                    accounts = json.loads(row["accounts_json"] or "[]")
                except Exception:
                    accounts = []
                out.append({
                    "id": row["id"],
                    "phone": row["phone"],
                    "carrier": row["carrier"],
                    "valid": bool(row["valid"]),
                    "accounts": accounts,
                    "property_url": row["property_url"],
                    "created_at": row["created_at"],
                })
            return out

    def search_by_phone(self, variants: List[str]) -> List[Dict[str, Any]]:
        """Find saved listings whose phone matches any of the given variants."""
        variants = [v for v in (variants or []) if v]
        if not variants:
            return []
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            conds = " OR ".join(["phone_number LIKE ?"] * len(variants))
            params = [f"%{v}%" for v in variants]
            cursor.execute(
                f"SELECT * FROM properties WHERE {conds} ORDER BY created_at DESC LIMIT 50",
                params)
            rows = cursor.fetchall()
            return [{
                "Title": r["title"],
                "URL": r["url"],
                "Source": r["source"],
                "Price": r["price"],
                "Broker Type": r["broker_type"],
                "Added On": r["created_at"],
            } for r in rows]
