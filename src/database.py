import logging
import sqlite3


logger = logging.getLogger(__name__)

class CompanyDB:
    def __init__(self, db_path="companies.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self._ensure_table()

    def _ensure_table(self):
        self.cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='companies';
        """)
        if self.cursor.fetchone() is None:
            self.cursor.execute("""
                CREATE TABLE companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT CHECK (length(name) <= 64),
                    website TEXT UNIQUE,
                    country TEXT CHECK (length(country) <= 32),
                    description TEXT,
                    phone TEXT CHECK (length(phone) <= 32),
                    email TEXT CHECK (length(email) <= 64)
                );
            """)
            self.conn.commit()

    def add(self, name, website, country, description, phone, email):
        try:
            if description is None:
                description = ""
            self.cursor.execute("""
                INSERT INTO companies (name, website, country, description, phone, email)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, website, country, description[:255], phone, email))
            self.conn.commit()
        except sqlite3.IntegrityError as e:
            logger.error(f"[!] Error inserting: {e}")

    def close(self):
        self.conn.close()
