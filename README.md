# Recruiter Bot

Backend service that ranks candidates for jobs (and jobs for candidates).
Python + FastAPI + stdlib `sqlite3` with hand-written SQL (no ORM).

## Setup
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m seed.seed                 # creates recruiter.db and loads seed data
uvicorn app.main:app --reload       # API at http://127.0.0.1:8000  (docs at /docs)
```

## API
_TODO: curl examples_

## Matching algorithm: decisions and trade-offs
_TODO_

## Part 2: SQL Detective
See `sql_detective.sql`. Dataset loader: `sql_detective/dataset.sql`.

## AI usage
_TODO: be honest about where AI helped._
