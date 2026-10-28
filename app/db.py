"""Tiny connection helper. All SQL in this project is hand-written."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "app" / "schema.sql"


def db_path() -> Path:
    """Read at call time so tests can point RECRUITER_DB at a temp file."""
    return Path(os.environ.get("RECRUITER_DB", ROOT / "recruiter.db"))


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row            # rows behave like dicts
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite needs this per connection
    return conn


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    """Open a connection for one request and always close it."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
