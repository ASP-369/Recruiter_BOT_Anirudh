"""Tiny connection helper. All SQL in this project is hand-written."""
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "app" / "schema.sql"
DB_PATH = Path(os.environ.get("RECRUITER_DB", ROOT / "recruiter.db"))


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row            # rows behave like dicts
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite needs this per connection
    return conn
