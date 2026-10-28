"""Matching algorithm.

Final score (0-100) = 100 * (0.60*skill + 0.20*experience + 0.10*culture + 0.10*availability)
where each component is a fraction between 0 and 1.

- skill        matched required skills / total required skills (computed in SQL)
- experience   1.0 if years >= minimum, otherwise years / minimum (no bonus for seniority)
- culture      shared (trait, keyword) pairs / number of culture keywords on the job
- availability immediate 1.0, 2 weeks 0.7, not looking 0.2

A pair with ZERO skill overlap is not a match at all and is never stored.
Ranking order: score, then skill, then experience, then availability, then name (A-Z),
so results are fully deterministic.
"""
import sqlite3
from typing import Dict, List, Optional, Tuple

WEIGHTS = {"skill": 0.60, "experience": 0.20, "culture": 0.10, "availability": 0.10}

AVAILABILITY_SCORE = {"immediate": 1.0, "2_weeks": 0.7, "not_looking": 0.2}
AVAILABILITY_LABEL = {
    "immediate": "available immediately",
    "2_weeks": "available in 2 weeks",
    "not_looking": "not actively looking",
}

# --- Hand-written SQL ---------------------------------------------------------

# One row per (job, candidate) pair that shares at least one required skill.
# The inner joins are what exclude zero-overlap pairs.
SKILL_OVERLAP_SQL = """
SELECT
    j.id                              AS job_id,
    c.id                              AS candidate_id,
    j.min_experience                  AS min_experience,
    c.experience_years                AS experience_years,
    c.availability                    AS availability,
    (SELECT COUNT(*) FROM job_required_skills r WHERE r.job_id = j.id) AS total_required,
    COUNT(s.id)                       AS matched,
    GROUP_CONCAT(s.name, ',')         AS matched_skills
FROM jobs j
JOIN job_required_skills jrs ON jrs.job_id = j.id
JOIN skills s                ON s.id = jrs.skill_id
JOIN candidate_skills cs     ON cs.skill_id = s.id
JOIN candidates c            ON c.id = cs.candidate_id
GROUP BY j.id, c.id
"""

# Candidate traits that equal a job's culture keyword (case-insensitive).
SHARED_CULTURE_SQL = """
SELECT
    jck.job_id                        AS job_id,
    ct.candidate_id                   AS candidate_id,
    GROUP_CONCAT(jck.keyword, ',')    AS shared
FROM job_culture_keywords jck
JOIN candidate_traits ct ON LOWER(ct.trait) = LOWER(jck.keyword)
GROUP BY jck.job_id, ct.candidate_id
"""

KEYWORD_COUNT_SQL = """
SELECT job_id, COUNT(*) AS n FROM job_culture_keywords GROUP BY job_id
"""

INSERT_MATCH_SQL = """
INSERT INTO matches
    (job_id, candidate_id, score, skill_score, exp_score, culture_score, avail_score, reason)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""


# --- Pure scoring functions (no database, easy to unit test) ------------------

def skill_score(matched: int, total_required: int) -> float:
    return matched / total_required if total_required > 0 else 0.0


def experience_score(experience_years: int, min_experience: int) -> float:
    if min_experience <= 0 or experience_years >= min_experience:
        return 1.0
    return experience_years / min_experience


def culture_score(shared_count: int, keyword_count: int) -> float:
    return shared_count / keyword_count if keyword_count > 0 else 0.0


def availability_score(availability: str) -> float:
    return AVAILABILITY_SCORE.get(availability, 0.0)


def build_reason(
    matched_skills: List[str],
    total_required: int,
    experience_years: int,
    min_experience: int,
    availability: str,
    shared_traits: List[str],
) -> str:
    parts = [
        f"Matches {len(matched_skills)}/{total_required} required skills "
        f"({', '.join(sorted(matched_skills))})"
    ]
    if experience_years >= min_experience:
        parts.append(f"{experience_years} yrs vs {min_experience} min")
    else:
        parts.append(f"{experience_years} yrs vs {min_experience} min (below minimum)")
    parts.append(AVAILABILITY_LABEL.get(availability, availability))
    if shared_traits:
        parts.append(f"culture fit: {', '.join(sorted(shared_traits))}")
    return "; ".join(parts)


def score_pair(
    matched_skills: List[str],
    total_required: int,
    experience_years: int,
    min_experience: int,
    availability: str,
    shared_traits: List[str],
    keyword_count: int,
) -> Dict[str, object]:
    """Combine the components into one result dict."""
    s = skill_score(len(matched_skills), total_required)
    e = experience_score(experience_years, min_experience)
    c = culture_score(len(shared_traits), keyword_count)
    a = availability_score(availability)
    total = 100 * (
        WEIGHTS["skill"] * s
        + WEIGHTS["experience"] * e
        + WEIGHTS["culture"] * c
        + WEIGHTS["availability"] * a
    )
    return {
        "score": round(total, 2),
        "skill_score": round(s, 3),
        "exp_score": round(e, 3),
        "culture_score": round(c, 3),
        "avail_score": round(a, 3),
        "reason": build_reason(
            matched_skills, total_required, experience_years,
            min_experience, availability, shared_traits,
        ),
    }


# --- Database-facing step -----------------------------------------------------

def recompute_matches(conn: sqlite3.Connection) -> int:
    """Rebuild the `matches` table from scratch. Returns the number of rows written."""
    shared: Dict[Tuple[int, int], List[str]] = {
        (r["job_id"], r["candidate_id"]): r["shared"].split(",")
        for r in conn.execute(SHARED_CULTURE_SQL)
    }
    keyword_counts: Dict[int, int] = {
        r["job_id"]: r["n"] for r in conn.execute(KEYWORD_COUNT_SQL)
    }

    rows = []
    for r in conn.execute(SKILL_OVERLAP_SQL).fetchall():
        key = (r["job_id"], r["candidate_id"])
        result = score_pair(
            matched_skills=r["matched_skills"].split(","),
            total_required=r["total_required"],
            experience_years=r["experience_years"],
            min_experience=r["min_experience"],
            availability=r["availability"],
            shared_traits=shared.get(key, []),
            keyword_count=keyword_counts.get(r["job_id"], 0),
        )
        rows.append((
            r["job_id"], r["candidate_id"], result["score"], result["skill_score"],
            result["exp_score"], result["culture_score"], result["avail_score"],
            result["reason"],
        ))

    conn.execute("DELETE FROM matches")
    conn.executemany(INSERT_MATCH_SQL, rows)
    conn.commit()
    return len(rows)
