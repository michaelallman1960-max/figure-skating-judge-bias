-- ============================================================================
-- Pairwise Judge Statistics Schema
-- ============================================================================
--
-- Stores bias statistics for every pairwise combination of competitors
-- within each event, for each judge.
--
-- This extends the gold-silver methodology to ALL pairs, enabling detection
-- of bias patterns throughout the competitive field, not just at the podium.
--
-- ============================================================================

CREATE TABLE IF NOT EXISTS pairwise_judge_statistics (
    -- Primary identifiers
    pairwise_stat_id INTEGER PRIMARY KEY AUTOINCREMENT,

    judge_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,

    -- The two competitors being compared
    entry_id_a INTEGER NOT NULL,  -- First competitor (typically higher rank)
    entry_id_b INTEGER NOT NULL,  -- Second competitor (typically lower rank)

    -- Competitor metadata (denormalized for convenience)
    skater_a_name TEXT,
    skater_a_country TEXT,
    skater_a_rank INTEGER,

    skater_b_name TEXT,
    skater_b_country TEXT,
    skater_b_rank INTEGER,

    -- Judge metadata (denormalized)
    judge_position TEXT,  -- J1, J2, etc.
    judge_name TEXT,
    judge_country TEXT,

    -- ========================================================================
    -- PAIRWISE BIAS STATISTIC (B(j) from the paper)
    -- ========================================================================

    -- The directional bias score
    -- B(j) = Σ[elements_a] d(u,j) + Σ[elements_b] (-d(u,j))
    -- where d(u,j) = judge_score - median(other 8 judges)
    --
    -- Positive B(j) means: judge favors A over B (relative to peers)
    -- Negative B(j) means: judge favors B over A (relative to peers)
    bias_statistic REAL NOT NULL,

    -- Number of elements used in calculation
    num_elements_a INTEGER,  -- Elements scored by competitor A
    num_elements_b INTEGER,  -- Elements scored by competitor B
    total_elements INTEGER,  -- Total elements in calculation

    -- ========================================================================
    -- PERMUTATION TEST RESULTS
    -- ========================================================================

    -- P-value from permutation test
    -- How often is B(j) this extreme under random chance?
    p_value REAL,

    -- Number of permutations used
    num_permutations INTEGER,

    -- One-sided vs two-sided test
    test_type TEXT CHECK(test_type IN ('one-sided', 'two-sided')),

    -- Z-score equivalent (for comparison)
    -- Calculated from permutation distribution
    permutation_z_score REAL,

    -- ========================================================================
    -- DESCRIPTIVE STATISTICS
    -- ========================================================================

    -- Mean deviation for competitor A (positive = judge scores A high)
    mean_deviation_a REAL,

    -- Mean deviation for competitor B (positive = judge scores B high)
    mean_deviation_b REAL,

    -- Difference in means (should equal bias_statistic / total_elements)
    differential REAL,

    -- ========================================================================
    -- SIGNIFICANCE FLAGS
    -- ========================================================================

    -- Flags for quick filtering
    is_significant_01 BOOLEAN,   -- p < 0.01
    is_significant_001 BOOLEAN,  -- p < 0.001
    is_significant_bonferroni BOOLEAN,  -- p < (0.001 / num_pairs_in_event)

    -- ========================================================================
    -- METADATA
    -- ========================================================================

    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign keys
    FOREIGN KEY (judge_id) REFERENCES judges(judge_id),
    FOREIGN KEY (event_id) REFERENCES events(event_id),
    FOREIGN KEY (entry_id_a) REFERENCES entries(entry_id),
    FOREIGN KEY (entry_id_b) REFERENCES entries(entry_id),

    -- Ensure we don't duplicate pairs (A,B) should not coexist with (B,A)
    -- Always store higher rank first (rank 1 before rank 2)
    CHECK (skater_a_rank <= skater_b_rank),

    -- Unique constraint: one statistic per judge per pair per event
    UNIQUE(judge_id, event_id, entry_id_a, entry_id_b)
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_pairwise_event
    ON pairwise_judge_statistics(event_id);

CREATE INDEX IF NOT EXISTS idx_pairwise_judge
    ON pairwise_judge_statistics(judge_id);

CREATE INDEX IF NOT EXISTS idx_pairwise_entries
    ON pairwise_judge_statistics(entry_id_a, entry_id_b);

CREATE INDEX IF NOT EXISTS idx_pairwise_pvalue
    ON pairwise_judge_statistics(p_value);

CREATE INDEX IF NOT EXISTS idx_pairwise_significant
    ON pairwise_judge_statistics(is_significant_001);

CREATE INDEX IF NOT EXISTS idx_pairwise_countries
    ON pairwise_judge_statistics(skater_a_country, skater_b_country);

-- ============================================================================
-- Summary View: Event-Level Pairwise Statistics
-- ============================================================================

CREATE VIEW IF NOT EXISTS v_pairwise_event_summary AS
SELECT
    e.event_id,
    c.name as competition_name,
    e.discipline,
    e.segment,
    COUNT(DISTINCT pjs.judge_id) as num_judges,
    COUNT(DISTINCT pjs.pairwise_stat_id) as total_pairwise_tests,
    SUM(CASE WHEN pjs.is_significant_001 = 1 THEN 1 ELSE 0 END) as significant_001_count,
    SUM(CASE WHEN pjs.is_significant_bonferroni = 1 THEN 1 ELSE 0 END) as significant_bonferroni_count,
    ROUND(AVG(ABS(pjs.bias_statistic)), 3) as avg_abs_bias,
    ROUND(MAX(pjs.bias_statistic), 2) as max_bias,
    ROUND(MIN(pjs.bias_statistic), 2) as min_bias
FROM pairwise_judge_statistics pjs
JOIN events e ON pjs.event_id = e.event_id
JOIN competitions c ON e.competition_id = c.competition_id
GROUP BY e.event_id;

-- ============================================================================
-- Summary View: Judge-Level Pairwise Statistics
-- ============================================================================

CREATE VIEW IF NOT EXISTS v_pairwise_judge_summary AS
SELECT
    pjs.judge_id,
    pjs.judge_name,
    pjs.judge_country,
    COUNT(DISTINCT pjs.event_id) as events_judged,
    COUNT(DISTINCT pjs.pairwise_stat_id) as total_pairwise_tests,
    SUM(CASE WHEN pjs.is_significant_001 = 1 THEN 1 ELSE 0 END) as significant_001_count,
    SUM(CASE WHEN pjs.is_significant_bonferroni = 1 THEN 1 ELSE 0 END) as significant_bonferroni_count,
    ROUND(100.0 * SUM(CASE WHEN pjs.is_significant_001 = 1 THEN 1 ELSE 0 END) /
          COUNT(pjs.pairwise_stat_id), 2) as pct_significant_001
FROM pairwise_judge_statistics pjs
GROUP BY pjs.judge_id;

-- ============================================================================
-- Example Queries
-- ============================================================================

-- Find all significant pairwise biases in Milano 2026 Ice Dance
-- SELECT * FROM pairwise_judge_statistics
-- WHERE event_id = 2 AND is_significant_001 = 1
-- ORDER BY p_value;

-- Find judges with multiple significant biases
-- SELECT judge_name, COUNT(*) as num_significant_pairs
-- FROM pairwise_judge_statistics
-- WHERE is_significant_001 = 1
-- GROUP BY judge_id
-- HAVING COUNT(*) > 1
-- ORDER BY num_significant_pairs DESC;

-- Find country-specific bias patterns
-- SELECT judge_country, skater_a_country, skater_b_country,
--        COUNT(*) as occurrences,
--        AVG(bias_statistic) as avg_bias
-- FROM pairwise_judge_statistics
-- WHERE is_significant_001 = 1
-- GROUP BY judge_country, skater_a_country, skater_b_country
-- ORDER BY occurrences DESC;
