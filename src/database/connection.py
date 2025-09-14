import sqlite3
from contextlib import contextmanager
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: str = "data/horses.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database with schema"""
        schema_path = Path(__file__).parent / "schema.sql"
        with self.get_connection() as conn:
            if schema_path.exists():
                with open(schema_path, "r") as f:
                    conn.executescript(f.read())
            conn.execute("PRAGMA foreign_keys = ON")
            conn.commit()

    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(
            self.db_path, timeout=30.0, isolation_level=None  # autocommit mode
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, query: str, params: tuple = ()):
        """Execute a query and return results"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()

    def execute_insert(self, query: str, params: tuple = ()):
        """Execute an insert and return last row id"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.lastrowid

    def execute_many(self, query: str, params_list: list):
        """Execute multiple inserts efficiently"""
        with self.get_connection() as conn:
            conn.executemany(query, params_list)
            conn.commit()
