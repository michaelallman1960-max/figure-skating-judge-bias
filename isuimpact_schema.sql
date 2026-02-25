-- isuimpact_schema.sql
-- New tables for the ISU-impact pairwise judge bias pipeline (isuimpact_quantile_v1).
-- The legacy pairwise_judge_statistics table is retained but deprecated.
-- Run: sqlite3 figure_skating_ijs_seed.sqlite < isuimpact_schema.sql

-- ── One row per (judge × competitor pair) per event ───────────────────────────
CREATE TABLE IF NOT EXISTS pairwise_impact_results (
    result_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    method_version   TEXT    NOT NULL DEFAULT 'isuimpact_quantile_v1',
    event_id         INTEGER NOT NULL REFERENCES events(event_id),
    judge_id         INTEGER NOT NULL REFERENCES judges(judge_id),
    judge_position   TEXT    NOT NULL,
    judge_name       TEXT,
    judge_country    TEXT,
    entry_id_a       INTEGER NOT NULL REFERENCES entries(entry_id),
    entry_id_b       INTEGER NOT NULL REFERENCES entries(entry_id),
    team_a           TEXT,
    noc_a            TEXT,
    rank_a           INTEGER,
    team_b           TEXT,
    noc_b            TEXT,
    rank_b           INTEGER,
    bias_points      REAL    NOT NULL,   -- B_j(A,B) = I_j(A) - I_j(B)
    vote             TEXT,               -- 'A', 'B', or 'tie'
    p_value          REAL,
    q_value_bh       REAL,
    permutations     INTEGER,
    rng_seed         INTEGER,
    calculated_at    TEXT,
    UNIQUE (method_version, event_id, judge_id, entry_id_a, entry_id_b)
);

CREATE INDEX IF NOT EXISTS idx_pir_event   ON pairwise_impact_results (event_id);
CREATE INDEX IF NOT EXISTS idx_pir_judge   ON pairwise_impact_results (judge_id);
CREATE INDEX IF NOT EXISTS idx_pir_pvalue  ON pairwise_impact_results (p_value);
CREATE INDEX IF NOT EXISTS idx_pir_qvalue  ON pairwise_impact_results (q_value_bh);
CREATE INDEX IF NOT EXISTS idx_pir_nocs    ON pairwise_impact_results (noc_a, noc_b);

-- ── One row per (judge × competitor) per event — I_j(T) totals ────────────────
CREATE TABLE IF NOT EXISTS judge_team_impacts (
    impact_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    method_version   TEXT    NOT NULL DEFAULT 'isuimpact_quantile_v1',
    event_id         INTEGER NOT NULL REFERENCES events(event_id),
    judge_id         INTEGER NOT NULL REFERENCES judges(judge_id),
    judge_position   TEXT    NOT NULL,
    judge_name       TEXT,
    judge_country    TEXT,
    entry_id         INTEGER NOT NULL REFERENCES entries(entry_id),
    team             TEXT,
    noc              TEXT,
    rank             INTEGER,
    impact_points    REAL    NOT NULL,   -- I_j(T) = sum of delta_{j,r} for all rows r of T
    calculated_at    TEXT,
    UNIQUE (method_version, event_id, judge_id, entry_id)
);

CREATE INDEX IF NOT EXISTS idx_jti_event   ON judge_team_impacts (event_id);
CREATE INDEX IF NOT EXISTS idx_jti_judge   ON judge_team_impacts (judge_id);
