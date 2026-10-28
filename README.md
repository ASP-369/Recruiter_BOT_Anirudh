# Recruiter Bot

Backend service that ranks candidates for jobs (and jobs for candidates).
**Python + FastAPI + stdlib `sqlite3`**, all SQL hand-written (no ORM, no query builder).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m seed.seed                  # creates recruiter.db, loads data, computes matches
uvicorn app.main:app --reload        # API on http://127.0.0.1:8000, interactive docs at /docs
python -m pytest                     # run the tests
```

If `recruiter.db` does not exist, the server seeds it automatically on startup.

## Project layout

```
app/schema.sql      hand-written DDL             app/matching.py   scoring + SQL for the matches table
app/db.py           connection helpers           app/main.py       FastAPI routes
seed/data.json      candidates and jobs          seed/seed.py      schema + ingestion + first match run
sql_detective.sql   Part 2 answers               sql_detective/dataset.sql   Part 2 data, loaded as-is
tests/              scoring, API and Part 2 tests
```

## API (curl examples)

```bash
curl localhost:8000/health
curl localhost:8000/jobs                                          # list jobs
curl localhost:8000/candidates                                    # list candidates
curl localhost:8000/jobs/1/matches                                # ranked candidates for a job
curl "localhost:8000/jobs/2/matches?limit=2"                      # top 2 only
curl "localhost:8000/jobs/2/matches?include_unavailable=false"    # hide "not looking" candidates
curl localhost:8000/candidates/1/matches                          # ranked jobs for a candidate
curl -X POST localhost:8000/seed                                  # ingestion: rebuild DB from seed/data.json
curl -X POST localhost:8000/recompute                             # recompute matches after data or weight changes
```

Each match has `rank`, `score` (0-100), a human-readable `reason` and a `breakdown` of the four components.
Unknown ids return 404 and an invalid `limit` returns 422.

## Schema

Skills are normalised (`skills`, `candidate_skills`, `job_required_skills`), so skill overlap is a SQL join.
Traits and culture keywords are rows, not comma-separated strings. Availability is a constrained value
(`immediate`, `2_weeks`, `not_looking`) enforced with a CHECK. Results go into a `matches` table with a
composite primary key `(job_id, candidate_id)` and the individual component scores, so the API is a plain
`SELECT ... ORDER BY`.

## Matching algorithm: decisions and trade-offs

`score = 100 * (0.60 * skills + 0.20 * experience + 0.10 * culture + 0.10 * availability)`

- **Skills (60%)**: matched required skills / total required, computed in SQL with a join and `COUNT`.
  It has the biggest weight because a candidate without the skills cannot do the job, whatever else is true.
- **Experience (20%)**: 1.0 at or above the minimum, otherwise `years / minimum`. Being overqualified earns
  nothing extra: Rick with 20 years is not "better" than MacGyver with 10 for a job that asks for 2.
- **Culture (10%)**: candidate traits equal to the job's culture keywords, divided by the number of keywords.
  The weight is low on purpose. In the seed data only a few traits line up exactly ("analytical",
  "innovative", "decisive", ...), so a heavy weight would mostly measure vocabulary luck.
- **Availability (10%)**: immediate 1.0, 2 weeks 0.7, not looking 0.2. "Not looking" candidates are ranked
  lower rather than removed, because a recruiter still wants to know the best person exists.
  `include_unavailable=false` hides them when wanted.
- **Zero skill overlap means no match.** Such pairs are never stored (the inner joins drop them). Otherwise Ron
  would appear for Backend Detective with 22 points earned only from experience and availability.
- **Tie-breaking** is deterministic: score, then skill score, then experience, then availability, then name.
  Example: for Rapid Prototyping Engineer, MacGyver and Tony both score 87.0 and MacGyver ranks first
  because he is more available.
- **Reasons** are generated from the components: matched skills, years vs minimum, availability, shared culture.

Trade-offs, and what I would change with real data:

- Matches are **precomputed** for fast reads and simple queries. The cost is staleness, which is why
  `POST /recompute` exists. At large scale I would recompute incrementally (only pairs touching changed rows),
  or compute on the fly for one job using the index on `candidate_skills(skill_id)`.
- Culture uses **exact string matching**. Real data would need synonyms or embeddings.
- Skills are **all-or-nothing**. Proficiency levels or skill weights would be a column on the link tables.
- The experience curve is **linear** below the minimum, so 1 year against a 5-year minimum still scores 0.2,
  which is arguably generous.
- There is **no minimum score threshold**, so weak matches are listed (Sales Engineer includes candidates who
  match only 1 of 3 skills). A cutoff would be a one-line change in the API query.
- Weights are constants in `app/matching.py`, not tuned against real hiring outcomes.

## Part 2: SQL Detective

`sql_detective.sql` has one query per question, each with its assumption in a comment. To run it:

```bash
sqlite3 sql_detective/detective.db < sql_detective/dataset.sql
sqlite3 -header -column sql_detective/detective.db < sql_detective.sql
```

Q3 is the trap: Ananya Rao is two applicant rows with the same email in different case, so identity is
`LOWER(email)`. `tests/test_sql_detective.py` checks all five answers.

## AI Usage

I used Claude (Anthropic) as an AI development assistant throughout this assignment. I started by using it to brainstorm the initial project idea and outline the implementation approach. After creating the repository in VS Code, I used Claude to help design the database schema and implement the seed function to create and populate the database with the provided data.

I then used Claude's assistance to develop the core matching logic, FastAPI endpoints, SQL Detective queries, and tests. During integration, I ran the project and tests locally, investigated errors, and worked with Claude to identify and resolve issues encountered during testing and execution.

The implementation was developed iteratively, moving from the initial design and schema through data seeding, application logic, API integration, and testing. I used AI assistance to troubleshoot problems and refine the implementation as the components came together.

Claude contributed substantially to the code and design decisions, including the matching weights and tie-breaking rules. I have documented the algorithm's rationale, assumptions, and trade-offs in this README and am prepared to discuss the implementation, explain the decisions I understand, and clarify any areas where I relied more heavily on AI assistance.
