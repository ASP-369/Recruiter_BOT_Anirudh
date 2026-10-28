from app.db import get_connection
from app.matching import (
    availability_score, culture_score, experience_score, recompute_matches,
    score_pair, skill_score,
)


# ---- pure scoring -----------------------------------------------------------

def test_skill_score_is_fraction_of_required_skills():
    assert skill_score(3, 3) == 1.0
    assert skill_score(1, 4) == 0.25
    assert skill_score(0, 0) == 0.0


def test_experience_meets_minimum_gets_full_score_and_no_seniority_bonus():
    assert experience_score(3, 3) == 1.0
    assert experience_score(20, 2) == 1.0


def test_experience_below_minimum_scales_down():
    assert experience_score(2, 4) == 0.5
    assert experience_score(0, 4) == 0.0


def test_experience_zero_minimum_is_always_full():
    assert experience_score(0, 0) == 1.0


def test_culture_score():
    assert culture_score(1, 2) == 0.5
    assert culture_score(0, 0) == 0.0


def test_availability_ordering():
    assert availability_score("immediate") > availability_score("2_weeks") > availability_score("not_looking")


def test_perfect_candidate_scores_95_when_half_the_culture_matches():
    r = score_pair(["a", "b", "c"], 3, 8, 3, "immediate", ["analytical"], 2)
    assert r["score"] == 95.0          # 60 + 20 + 5 + 10
    assert "3/3 required skills" in r["reason"]


def test_reason_mentions_below_minimum():
    r = score_pair(["a"], 2, 1, 5, "2_weeks", [], 2)
    assert "below minimum" in r["reason"]


# ---- against the seeded database -------------------------------------------

def test_zero_overlap_pairs_are_not_stored(seeded_db):
    conn = get_connection()
    # Ron (woodworking, minimalism, negotiation) should not match Backend Detective (job 1).
    n = conn.execute(
        "SELECT COUNT(*) FROM matches m JOIN candidates c ON c.id = m.candidate_id "
        "WHERE m.job_id = 1 AND c.name = 'Ron S.'"
    ).fetchone()[0]
    conn.close()
    assert n == 0


def test_recompute_is_idempotent(seeded_db):
    conn = get_connection()
    first = recompute_matches(conn)
    second = recompute_matches(conn)
    total = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
    conn.close()
    assert first == second == total
