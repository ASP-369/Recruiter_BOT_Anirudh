"""FastAPI entry point. Run with:  uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query

from app.db import db_path, db_session
from app.matching import recompute_matches
from seed.seed import seed


@asynccontextmanager
async def lifespan(_: FastAPI):
    # First run convenience: build and seed the database if it does not exist yet.
    if not db_path().exists():
        seed()
    yield


app = FastAPI(
    title="Recruiter Bot",
    description="Ranks candidates for jobs and jobs for candidates.",
    lifespan=lifespan,
)

# Same ordering everywhere, so results are deterministic.
JOB_MATCHES_SQL = """
SELECT c.id AS candidate_id, c.name, c.experience_years, c.availability,
       m.score, m.skill_score, m.exp_score, m.culture_score, m.avail_score, m.reason
FROM matches m
JOIN candidates c ON c.id = m.candidate_id
WHERE m.job_id = ?
  AND (? = 1 OR c.availability != 'not_looking')
ORDER BY m.score DESC, m.skill_score DESC, m.exp_score DESC, m.avail_score DESC, c.name ASC
"""

CANDIDATE_MATCHES_SQL = """
SELECT j.id AS job_id, j.title, j.min_experience, j.tagline,
       m.score, m.skill_score, m.exp_score, m.culture_score, m.avail_score, m.reason
FROM matches m
JOIN jobs j ON j.id = m.job_id
WHERE m.candidate_id = ?
ORDER BY m.score DESC, m.skill_score DESC, m.exp_score DESC, m.avail_score DESC, j.title ASC
"""


def _breakdown(row: Any) -> Dict[str, float]:
    return {
        "skills": row["skill_score"],
        "experience": row["exp_score"],
        "culture": row["culture_score"],
        "availability": row["avail_score"],
    }


@app.get("/health")
def health() -> Dict[str, Any]:
    with db_session() as conn:
        n = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
        m = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    return {"status": "ok", "candidates": n, "matches": m}


@app.post("/seed")
def reseed() -> Dict[str, str]:
    """Ingestion endpoint: rebuild the database from seed/data.json and recompute matches."""
    seed()
    return {"status": "seeded"}


@app.post("/recompute")
def recompute() -> Dict[str, int]:
    """Recompute all matches (call after changing data or weights)."""
    with db_session() as conn:
        return {"matches_written": recompute_matches(conn)}


@app.get("/jobs")
def list_jobs() -> List[Dict[str, Any]]:
    with db_session() as conn:
        rows = conn.execute(
            "SELECT id, title, min_experience, tagline FROM jobs ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/candidates")
def list_candidates() -> List[Dict[str, Any]]:
    with db_session() as conn:
        rows = conn.execute(
            "SELECT id, name, experience_years, availability, quirk FROM candidates ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/jobs/{job_id}/matches")
def job_matches(
    job_id: int,
    limit: Optional[int] = Query(None, ge=1, le=100, description="Max results"),
    include_unavailable: bool = Query(
        True, description="Set false to hide candidates who are not looking"
    ),
) -> Dict[str, Any]:
    with db_session() as conn:
        job = conn.execute(
            "SELECT id, title, min_experience, tagline FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        if job is None:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        rows = conn.execute(
            JOB_MATCHES_SQL, (job_id, 1 if include_unavailable else 0)
        ).fetchall()

    if limit is not None:
        rows = rows[:limit]
    matches = [
        {
            "rank": i,
            "candidate_id": r["candidate_id"],
            "name": r["name"],
            "score": r["score"],
            "reason": r["reason"],
            "breakdown": _breakdown(r),
            "experience_years": r["experience_years"],
            "availability": r["availability"],
        }
        for i, r in enumerate(rows, start=1)
    ]
    return {"job": dict(job), "count": len(matches), "matches": matches}


@app.get("/candidates/{candidate_id}/matches")
def candidate_matches(
    candidate_id: int,
    limit: Optional[int] = Query(None, ge=1, le=100, description="Max results"),
) -> Dict[str, Any]:
    with db_session() as conn:
        cand = conn.execute(
            "SELECT id, name, experience_years, availability FROM candidates WHERE id = ?",
            (candidate_id,),
        ).fetchone()
        if cand is None:
            raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")
        rows = conn.execute(CANDIDATE_MATCHES_SQL, (candidate_id,)).fetchall()

    if limit is not None:
        rows = rows[:limit]
    matches = [
        {
            "rank": i,
            "job_id": r["job_id"],
            "title": r["title"],
            "score": r["score"],
            "reason": r["reason"],
            "breakdown": _breakdown(r),
            "min_experience": r["min_experience"],
        }
        for i, r in enumerate(rows, start=1)
    ]
    return {"candidate": dict(cand), "count": len(matches), "matches": matches}
