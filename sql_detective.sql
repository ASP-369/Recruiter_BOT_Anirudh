-- SQL Detective answers (SQLite dialect, window functions need SQLite 3.25+).
--   sqlite3 sql_detective/detective.db < sql_detective/dataset.sql
--   sqlite3 -header -column sql_detective/detective.db < sql_detective.sql

-- Q1: All currently open job postings with the owning recruiter's name.
-- Assumption: "currently open" means status = 'open' (not closed or on_hold).
SELECT jp.id, jp.title, jp.department, jp.opened_date, r.name AS recruiter
FROM job_postings jp
JOIN recruiters r ON r.id = jp.recruiter_id
WHERE jp.status = 'open'
ORDER BY jp.id;

-- Q2: Number of applicants who reached the Final stage, per job posting.
-- Assumption: "reached Final" = has a Final interview scheduled, whatever the outcome.
-- LEFT JOIN keeps postings with zero Finals (shown as 0). DISTINCT guards against duplicate rows.
SELECT jp.id, jp.title, COUNT(DISTINCT i.applicant_id) AS final_stage_applicants
FROM job_postings jp
LEFT JOIN interviews i
       ON i.job_posting_id = jp.id AND i.stage = 'Final'
GROUP BY jp.id, jp.title
ORDER BY jp.id;

-- Q3: People who effectively applied to more than one job posting.
-- The trap: Ananya Rao is two applicant rows (ids 1 and 2) with the same email in different case.
-- Identity = LOWER(email). The applicants table has no job column, so "applied to a posting"
-- is taken from interviews (the only link between a person and a posting).
SELECT LOWER(a.email)                        AS person_email,
       MIN(a.full_name)                      AS full_name,
       GROUP_CONCAT(DISTINCT a.id)           AS applicant_ids,
       COUNT(DISTINCT i.job_posting_id)      AS postings_count,
       GROUP_CONCAT(DISTINCT i.job_posting_id) AS posting_ids
FROM applicants a
JOIN interviews i ON i.applicant_id = a.id
GROUP BY LOWER(a.email)
HAVING COUNT(DISTINCT i.job_posting_id) > 1
ORDER BY full_name;

-- Q4: Final-stage conversion rate per recruiter, only recruiters with at least 3 Final interviews.
-- Rate = passed / total Final interviews. Pending (NULL) and no_show count in the denominator.
-- 1.0 * forces decimal division instead of integer division.
SELECT r.id, r.name,
       COUNT(*)                                                    AS final_interviews,
       SUM(CASE WHEN i.outcome = 'passed' THEN 1 ELSE 0 END)       AS passed,
       ROUND(1.0 * SUM(CASE WHEN i.outcome = 'passed' THEN 1 ELSE 0 END) / COUNT(*), 2)
                                                                   AS conversion_rate
FROM interviews i
JOIN job_postings jp ON jp.id = i.job_posting_id
JOIN recruiters r    ON r.id = jp.recruiter_id
WHERE i.stage = 'Final'
GROUP BY r.id, r.name
HAVING COUNT(*) >= 3
ORDER BY conversion_rate DESC, r.name;

-- Q5 (Bonus): Recruiter with the most successful placements per department.
-- Placement = a 'passed' Final interview. RANK() means ties share first place and all are shown.
-- Departments with no placements at all do not appear.
WITH placements AS (
    SELECT jp.department, r.id AS recruiter_id, r.name AS recruiter, COUNT(*) AS placements
    FROM interviews i
    JOIN job_postings jp ON jp.id = i.job_posting_id
    JOIN recruiters r    ON r.id = jp.recruiter_id
    WHERE i.stage = 'Final' AND i.outcome = 'passed'
    GROUP BY jp.department, r.id, r.name
),
ranked AS (
    SELECT department, recruiter, placements,
           RANK() OVER (PARTITION BY department ORDER BY placements DESC) AS rnk
    FROM placements
)
SELECT department, recruiter, placements
FROM ranked
WHERE rnk = 1
ORDER BY department;