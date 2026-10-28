import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client(seeded_db):
    with TestClient(app) as c:
        yield c


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["candidates"] == 15 and body["matches"] > 0


def test_backend_detective_top_match_is_sherlock(client):
    body = client.get("/jobs/1/matches").json()
    top = body["matches"][0]
    assert top["name"] == "Sherlock H." and top["rank"] == 1
    assert top["score"] == 95.0
    assert top["reason"]


def test_matches_are_sorted_descending(client):
    for job_id in range(1, 7):
        scores = [m["score"] for m in client.get(f"/jobs/{job_id}/matches").json()["matches"]]
        assert scores == sorted(scores, reverse=True)


def test_tie_is_broken_by_availability(client):
    # Rapid Prototyping Engineer: MacGyver and Tony tie on score, MacGyver is more available.
    names = [m["name"] for m in client.get("/jobs/2/matches").json()["matches"]]
    assert names.index("MacGyver") < names.index("Tony S.")


def test_include_unavailable_false_hides_not_looking(client):
    body = client.get("/jobs/2/matches?include_unavailable=false").json()
    assert all(m["availability"] != "not_looking" for m in body["matches"])
    assert "Tony S." not in [m["name"] for m in body["matches"]]


def test_limit(client):
    assert client.get("/jobs/2/matches?limit=1").json()["count"] == 1


def test_candidate_matches_reverse_direction(client):
    body = client.get("/candidates/1/matches").json()   # Sherlock
    assert body["matches"][0]["title"] == "Backend Detective"


def test_unknown_ids_return_404(client):
    assert client.get("/jobs/999/matches").status_code == 404
    assert client.get("/candidates/999/matches").status_code == 404


def test_invalid_limit_is_rejected(client):
    assert client.get("/jobs/1/matches?limit=0").status_code == 422


def test_recompute_endpoint(client):
    assert client.post("/recompute").json()["matches_written"] > 0
