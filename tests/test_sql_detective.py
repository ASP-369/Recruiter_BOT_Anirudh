"""Runs the Part 2 answers against the dataset and checks the results."""
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def results():
    conn = sqlite3.connect(":memory:")
    conn.executescript((ROOT / "sql_detective" / "dataset.sql").read_text())
    sql = (ROOT / "sql_detective.sql").read_text()
    statements = [s.strip() for s in sql.split(";") if "SELECT" in s.upper()]
    assert len(statements) == 5
    return [conn.execute(s).fetchall() for s in statements]


def test_q1_open_postings(results):
    assert [r[0] for r in results[0]] == [1, 2, 4, 5]


def test_q2_final_counts_include_zero(results):
    counts = {r[0]: r[2] for r in results[1]}
    assert counts == {1: 2, 2: 2, 3: 1, 4: 2, 5: 0, 6: 0, 7: 2}


def test_q3_merges_duplicate_ananya(results):
    emails = {r[0] for r in results[2]}
    assert "ananya.rao@mail.com" in emails
    assert len(emails) == len(results[2])    # Ananya appears once, not twice


def test_q4_conversion(results):
    rows = {r[1]: (r[2], r[3], r[4]) for r in results[3]}
    assert rows == {"Priya Shah": (4, 3, 0.75), "Daniel Ortiz": (4, 2, 0.5)}


def test_q5_top_placer_per_department(results):
    assert [tuple(r) for r in results[4]] == [("Data", "Fatima Al-Sayed", 1), ("Engineering", "Priya Shah", 3)]
