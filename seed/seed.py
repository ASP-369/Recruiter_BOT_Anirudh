"""Create the schema and load seed data. Safe to re-run (it rebuilds everything).

Usage:  python -m seed.seed
"""
import json
from pathlib import Path

from app.db import SCHEMA_PATH, get_connection
from app.matching import recompute_matches

DATA_PATH = Path(__file__).resolve().parent / "data.json"


def seed() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        # 1. Every distinct skill, once.
        all_skills = {s for c in data["candidates"] for s in c["skills"]}
        all_skills |= {s for j in data["jobs"] for s in j["required_skills"]}
        conn.executemany(
            "INSERT INTO skills (name) VALUES (?)", [(s,) for s in sorted(all_skills)]
        )

        # 2. Candidates and their skills / traits.
        for c in data["candidates"]:
            cur = conn.execute(
                "INSERT INTO candidates (name, experience_years, availability, quirk) "
                "VALUES (?, ?, ?, ?)",
                (c["name"], c["experience_years"], c["availability"], c["quirk"]),
            )
            cid = cur.lastrowid
            conn.executemany(
                "INSERT INTO candidate_skills (candidate_id, skill_id) "
                "SELECT ?, id FROM skills WHERE name = ?",
                [(cid, s) for s in c["skills"]],
            )
            conn.executemany(
                "INSERT INTO candidate_traits (candidate_id, trait) VALUES (?, ?)",
                [(cid, t) for t in c["traits"]],
            )

        # 3. Jobs and their required skills / culture keywords.
        for j in data["jobs"]:
            cur = conn.execute(
                "INSERT INTO jobs (title, min_experience, tagline) VALUES (?, ?, ?)",
                (j["title"], j["min_experience"], j["tagline"]),
            )
            jid = cur.lastrowid
            conn.executemany(
                "INSERT INTO job_required_skills (job_id, skill_id) "
                "SELECT ?, id FROM skills WHERE name = ?",
                [(jid, s) for s in j["required_skills"]],
            )
            conn.executemany(
                "INSERT INTO job_culture_keywords (job_id, keyword) VALUES (?, ?)",
                [(jid, k) for k in j["culture_keywords"]],
            )

        conn.commit()
        n_matches = recompute_matches(conn)
        tables = ("candidates", "jobs", "skills", "candidate_skills",
                  "job_required_skills", "candidate_traits", "job_culture_keywords")
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
        counts["matches"] = n_matches
        print("Seeded:", counts)
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
