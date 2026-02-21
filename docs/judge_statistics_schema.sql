-- ============================================================================
-- Judge Event Statistics Schema
-- ============================================================================
--
-- Pre-computed bias statistics for each judge in each event.
-- Each event has 9 judges (J1-J9) who evaluate all skaters.
-- These statistics are calculated once and stored for fast analysis.
--
-- ============================================================================

CREATE TABLE IF NOT EXISTS judge_event_statistics (
    -- Primary identifiers
    judge_id INTEGER NOT NULL,
    event_id INTEGER NOT NULL,

    -- Judge metadata (denormalized for convenience)
    judge_position TEXT NOT NULL,  -- J1, J2, ... J9
    judge_name TEXT,
    judge_country TEXT,

    -- Event context
    num_skaters_judged INTEGER,
    num_elements_judged INTEGER,

    -- ========================================================================
    -- BIAS METRICS (relative to panel mean)
    -- ========================================================================

    -- Raw deviation statistics
    mean_goe_deviation REAL,           -- Average (judge_goe - panel_mean_goe)
    median_goe_deviation REAL,         -- Median deviation (robust to outliers)
    sum_goe_deviation REAL,            -- Total cumulative deviation

    -- Standardized bias (z-score)
    bias_z_score REAL,                 -- How many std devs from panel mean?

    -- Directional bias
    positive_bias_count INTEGER,       -- Times judge scored > panel mean
    negative_bias_count INTEGER,       -- Times judge scored < panel mean
    neutral_count INTEGER,             -- Times judge scored = panel mean

    -- Magnitude of bias
    mean_absolute_deviation REAL,     -- Average |deviation| (ignores direction)

    -- ========================================================================
    -- CONSISTENCY METRICS
    -- ========================================================================

    -- How variable is this judge compared to panel?
    std_deviation REAL,                -- Std dev of judge's deviations

    -- How well does judge agree with panel?
    correlation_with_panel REAL,       -- Pearson correlation (judge vs panel mean)

    -- Extreme scoring behavior
    outlier_count INTEGER,             -- Scores >2 std devs from panel mean
    outlier_percentage REAL,           -- % of scores that are outliers

    -- ========================================================================
    -- NATIONAL BIAS METRICS (if applicable)
    -- ========================================================================

    -- Does judge favor their own country?
    has_home_country_skaters BOOLEAN,  -- Are there skaters from judge's country?
    home_country_mean_goe REAL,        -- Mean GOE for home country skaters
    other_country_mean_goe REAL,       -- Mean GOE for other skaters
    home_country_differential REAL,    -- Difference (home - other)
    home_country_z_score REAL,         -- Standardized home country bias

    -- Regional bias (e.g., European judges favoring European skaters)
    -- (Can be calculated later if needed)

    -- ========================================================================
    -- SCORE DISTRIBUTION
    -- ========================================================================

    -- Range of GOE scores given
    min_goe INTEGER,
    max_goe INTEGER,
    goe_range INTEGER,                 -- max - min

    -- Central tendency
    mean_goe REAL,                     -- Average GOE given by this judge
    median_goe REAL,                   -- Median GOE given

    -- Use of score spectrum
    num_negative_goe INTEGER,          -- Count of negative GOEs
    num_zero_goe INTEGER,              -- Count of zero GOEs
    num_positive_goe INTEGER,          -- Count of positive GOEs

    -- ========================================================================
    -- METADATA
    -- ========================================================================

    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (judge_id, event_id),
    FOREIGN KEY (judge_id) REFERENCES judges(judge_id),
    FOREIGN KEY (event_id) REFERENCES events(event_id)
);

-- Index for fast queries
CREATE INDEX IF NOT EXISTS idx_jes_event ON judge_event_statistics(event_id);
CREATE INDEX IF NOT EXISTS idx_jes_bias ON judge_event_statistics(bias_z_score);
CREATE INDEX IF NOT EXISTS idx_jes_outliers ON judge_event_statistics(outlier_percentage);
CREATE INDEX IF NOT EXISTS idx_jes_home_bias ON judge_event_statistics(home_country_z_score);

-- ============================================================================
-- Example Queries This Schema Enables
-- ============================================================================

-- Find the most biased judges in WC 2024
-- SELECT judge_name, judge_position, bias_z_score, mean_goe_deviation
-- FROM judge_event_statistics
-- WHERE event_id IN (SELECT event_id FROM events WHERE competition_id = 3)
-- ORDER BY ABS(bias_z_score) DESC;

-- Find judges with significant home country bias
-- SELECT judge_name, judge_country, home_country_differential, home_country_z_score
-- FROM judge_event_statistics
-- WHERE has_home_country_skaters = 1 AND ABS(home_country_z_score) > 2.0;

-- Find most inconsistent judges (high outlier percentage)
-- SELECT judge_name, outlier_percentage, outlier_count, num_elements_judged
-- FROM judge_event_statistics
-- WHERE outlier_percentage > 10.0
-- ORDER BY outlier_percentage DESC;

-- Compare judge behavior across multiple events
-- SELECT judge_name, event_id, bias_z_score, correlation_with_panel
-- FROM judge_event_statistics
-- WHERE judge_name = 'John Smith'
-- ORDER BY event_id;
