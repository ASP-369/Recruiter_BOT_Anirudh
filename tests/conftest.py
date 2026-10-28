import pytest

from seed.seed import seed


@pytest.fixture()
def seeded_db(tmp_path, monkeypatch):
    """A fresh seeded database in a temp file for each test."""
    monkeypatch.setenv("RECRUITER_DB", str(tmp_path / "test.db"))
    seed()
    return tmp_path / "test.db"
