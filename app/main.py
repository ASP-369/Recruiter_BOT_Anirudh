"""FastAPI entry point. Run with:  uvicorn app.main:app --reload"""
from fastapi import FastAPI

from app.db import get_connection

app = FastAPI(title="Recruiter Bot")


@app.get("/health")
def health() -> dict:
    conn = get_connection()
    try:
        n = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    finally:
        conn.close()
    return {"status": "ok", "candidates": n}


# TODO: GET /jobs/{id}/matches
# TODO: GET /candidates/{id}/matches
