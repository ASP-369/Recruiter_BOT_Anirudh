-- Recruiter Bot schema (hand-written DDL, SQLite dialect)

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS matches;
DROP TABLE IF EXISTS job_culture_keywords;
DROP TABLE IF EXISTS candidate_traits;
DROP TABLE IF EXISTS job_required_skills;
DROP TABLE IF EXISTS candidate_skills;
DROP TABLE IF EXISTS skills;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS candidates;

CREATE TABLE candidates (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT    NOT NULL UNIQUE,
    experience_years INTEGER NOT NULL CHECK (experience_years >= 0),
    availability     TEXT    NOT NULL
                     CHECK (availability IN ('immediate', '2_weeks', 'not_looking')),
    quirk            TEXT
);

CREATE TABLE jobs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    title          TEXT    NOT NULL UNIQUE,
    min_experience INTEGER NOT NULL CHECK (min_experience >= 0),
    tagline        TEXT
);

-- Normalised skills: skill overlap becomes a plain SQL join.
CREATE TABLE skills (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE candidate_skills (
    candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    skill_id     INTEGER NOT NULL REFERENCES skills(id)     ON DELETE CASCADE,
    PRIMARY KEY (candidate_id, skill_id)
);

CREATE TABLE job_required_skills (
    job_id   INTEGER NOT NULL REFERENCES jobs(id)   ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, skill_id)
);

CREATE TABLE candidate_traits (
    candidate_id INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    trait        TEXT    NOT NULL,
    PRIMARY KEY (candidate_id, trait)
);

CREATE TABLE job_culture_keywords (
    job_id  INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    keyword TEXT    NOT NULL,
    PRIMARY KEY (job_id, keyword)
);

-- Precomputed matches. Filled by the matching step, read by the API.
CREATE TABLE matches (
    job_id        INTEGER NOT NULL REFERENCES jobs(id)       ON DELETE CASCADE,
    candidate_id  INTEGER NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    score         REAL    NOT NULL CHECK (score BETWEEN 0 AND 100),
    skill_score   REAL    NOT NULL,
    exp_score     REAL    NOT NULL,
    culture_score REAL    NOT NULL,
    avail_score   REAL    NOT NULL,
    reason        TEXT    NOT NULL,
    PRIMARY KEY (job_id, candidate_id)
);

-- The PKs already index the "job -> skills" / "candidate -> skills" direction.
-- These cover the reverse direction and the ranked lookups.
CREATE INDEX idx_candidate_skills_skill ON candidate_skills(skill_id);
CREATE INDEX idx_job_required_skills_skill ON job_required_skills(skill_id);
CREATE INDEX idx_matches_job_score ON matches(job_id, score DESC);
CREATE INDEX idx_matches_candidate_score ON matches(candidate_id, score DESC);
