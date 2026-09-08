import sqlite3
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
