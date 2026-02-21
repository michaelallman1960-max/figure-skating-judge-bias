-- Analysis Queries for Figure Skating Judging Database
-- ========================================================

-- QUERY 1: Judge Outlier Analysis (France vs USA type analysis)
-- This query computes judge differentials and z-scores for any two teams
-- Usage: Replace team names and event_id as needed

WITH team_scores AS (
    SELECT
        jet.judge_id,
        j.judge_position,
        j.judge_name,
        j.country_code,
        e.entry_id,
        e.team_name,
        e.noc,
        e.rank,
        jet.reconstructed_total,
        jet.reconstructed_tes,
        jet.reconstructed_pcs
    FROM judge_entry_totals jet
    JOIN judges j ON jet.judge_id = j.judge_id
    JOIN entries e ON jet.entry_id = e.entry_id
    WHERE jet.event_id = 2  -- Ice Dance Free Dance
      AND e.team_name IN (
          'FOURNIER BEAUDRY Laurence / CIZERON Guillaume',
          'CHOCK Madison / BATES Evan'
      )
),
judge_diffs AS (
    SELECT
        judge_id,
        judge_position,
        judge_name,
        country_code,
        MAX(CASE WHEN noc = 'FRA' THEN reconstructed_total END) as fra_score,
        MAX(CASE WHEN noc = 'USA' THEN reconstructed_total END) as usa_score,
        MAX(CASE WHEN noc = 'FRA' THEN reconstructed_total END) -
        MAX(CASE WHEN noc = 'USA' THEN reconstructed_total END) as differential
    FROM team_scores
    GROUP BY judge_id, judge_position, judge_name, country_code
),
stats AS (
    SELECT
        AVG(differential) as mean_diff,
        STDEV(differential) as std_diff
    FROM judge_diffs
)
SELECT
    jd.judge_position,
    jd.judge_name,
    jd.country_code,
    ROUND(jd.fra_score, 2) as FRA_score,
    ROUND(jd.usa_score, 2) as USA_score,
    ROUND(jd.differential, 2) as differential,
    ROUND((jd.differential - s.mean_diff) / NULLIF(s.std_diff, 0), 3) as z_score,
    CASE
        WHEN ABS((jd.differential - s.mean_diff) / NULLIF(s.std_diff, 0)) > 2 THEN '⚠️ EXTREME'
        WHEN ABS((jd.differential - s.mean_diff) / NULLIF(s.std_diff, 0)) > 1.5 THEN '⚠️ Notable'
        ELSE ''
    END as outlier_flag
FROM judge_diffs jd
CROSS JOIN stats s
ORDER BY differential DESC;


-- QUERY 2: Element-level Judge Agreement Analysis
-- Identifies elements where judges had high disagreement (large GOE spread)

SELECT
    e.team_name,
    e.rank,
    el.element_no,
    el.element_code,
    el.base_value,
    el.panel_goe_points,
    MIN(ejs.judge_goe_int) as min_goe,
    MAX(ejs.judge_goe_int) as max_goe,
    MAX(ejs.judge_goe_int) - MIN(ejs.judge_goe_int) as goe_spread,
    ROUND(AVG(ejs.judge_goe_int * 1.0), 2) as avg_goe,
    COUNT(DISTINCT ejs.judge_id) as n_judges
FROM elements el
JOIN entries e ON el.entry_id = e.entry_id
JOIN element_judge_scores ejs ON el.element_id = ejs.element_id
WHERE e.event_id = 2  -- Ice Dance Free Dance
GROUP BY el.element_id, e.team_name, e.rank, el.element_no, el.element_code, el.base_value, el.panel_goe_points
HAVING (MAX(ejs.judge_goe_int) - MIN(ejs.judge_goe_int)) >= 3  -- High disagreement
ORDER BY goe_spread DESC, e.rank, el.element_no
LIMIT 20;


-- QUERY 3: PCS Component Analysis by Judge
-- Shows which judges gave systematically higher/lower PCS marks

WITH pcs_stats AS (
    SELECT
        pcs.component_name,
        AVG(pjs.judge_mark) as mean_mark,
        STDEV(pjs.judge_mark) as std_mark
    FROM pcs_components pcs
    JOIN pcs_judge_scores pjs ON pcs.pcs_id = pjs.pcs_id
    JOIN entries e ON pcs.entry_id = e.entry_id
    WHERE e.event_id = 2  -- Ice Dance Free Dance
    GROUP BY pcs.component_name
)
SELECT
    j.judge_position,
    j.judge_name,
    pcs.component_name,
    e.team_name,
    e.rank,
    ROUND(pjs.judge_mark, 2) as judge_mark,
    ROUND(ps.mean_mark, 2) as mean_mark,
    ROUND(pjs.judge_mark - ps.mean_mark, 2) as deviation,
    ROUND((pjs.judge_mark - ps.mean_mark) / NULLIF(ps.std_mark, 0), 2) as z_score
FROM pcs_judge_scores pjs
JOIN pcs_components pcs ON pjs.pcs_id = pcs.pcs_id
JOIN judges j ON pjs.judge_id = j.judge_id
JOIN entries e ON pcs.entry_id = e.entry_id
CROSS JOIN pcs_stats ps ON ps.component_name = pcs.component_name
WHERE e.event_id = 2
  AND e.rank <= 3  -- Top 3 teams
ORDER BY pcs.component_name, e.rank, j.judge_position;


-- QUERY 4: Judge Consistency Analysis
-- Measures how consistent each judge is compared to panel average

WITH judge_deviations AS (
    SELECT
        ejs.judge_id,
        j.judge_position,
        j.judge_name,
        AVG(ABS(ejs.judge_goe_int -
            (SELECT AVG(ejs2.judge_goe_int * 1.0)
             FROM element_judge_scores ejs2
             WHERE ejs2.element_id = ejs.element_id))) as avg_deviation_from_panel
    FROM element_judge_scores ejs
    JOIN judges j ON ejs.judge_id = j.judge_id
    JOIN elements el ON ejs.element_id = el.element_id
    JOIN entries e ON el.entry_id = e.entry_id
    WHERE e.event_id = 2  -- Ice Dance Free Dance
    GROUP BY ejs.judge_id, j.judge_position, j.judge_name
)
SELECT
    judge_position,
    judge_name,
    ROUND(avg_deviation_from_panel, 3) as avg_goe_deviation,
    CASE
        WHEN avg_deviation_from_panel > 1.0 THEN 'High variance'
        WHEN avg_deviation_from_panel > 0.7 THEN 'Moderate variance'
        ELSE 'Low variance'
    END as consistency_rating
FROM judge_deviations
ORDER BY avg_deviation_from_panel DESC;


-- QUERY 5: National Bias Detection
-- Identifies potential national bias by comparing judge scores for same-nation teams

SELECT
    j.judge_position,
    j.judge_name,
    j.country_code as judge_country,
    e.noc as team_country,
    e.team_name,
    e.rank,
    ROUND(jet.reconstructed_total, 2) as judge_total,
    ROUND(e.tss, 2) as official_total,
    ROUND(jet.reconstructed_total - e.tss, 2) as difference_from_official,
    CASE
        WHEN j.country_code = e.noc THEN '🏴 Same nation'
        ELSE ''
    END as bias_flag
FROM judge_entry_totals jet
JOIN judges j ON jet.judge_id = j.judge_id
JOIN entries e ON jet.entry_id = e.entry_id
WHERE jet.event_id = 2  -- Ice Dance Free Dance
  AND e.rank <= 5
ORDER BY e.rank, j.judge_position;


-- QUERY 6: Competition Summary Statistics

SELECT
    c.season,
    c.name,
    e.discipline,
    e.segment,
    COUNT(DISTINCT en.entry_id) as num_competitors,
    COUNT(DISTINCT j.judge_id) as num_judges,
    COUNT(DISTINCT el.element_id) as num_elements_scored,
    ROUND(AVG(en.tss), 2) as avg_total_score,
    ROUND(MAX(en.tss), 2) as max_total_score,
    ROUND(MIN(en.tss), 2) as min_total_score
FROM events e
JOIN competitions c ON e.competition_id = c.competition_id
JOIN entries en ON e.event_id = en.event_id
LEFT JOIN judges j ON e.event_id = j.event_id
LEFT JOIN elements el ON en.entry_id = el.entry_id
GROUP BY c.season, c.name, e.discipline, e.segment
ORDER BY c.season DESC, e.discipline, e.segment;


-- QUERY 7: Database Coverage Report
-- Shows what data is available in the database

SELECT
    'Competitions' as entity,
    COUNT(*) as count,
    MIN(season) as earliest,
    MAX(season) as latest
FROM competitions
UNION ALL
SELECT
    'Events',
    COUNT(*),
    NULL,
    NULL
FROM events
UNION ALL
SELECT
    'Entries (performances)',
    COUNT(*),
    NULL,
    NULL
FROM entries
UNION ALL
SELECT
    'Judges',
    COUNT(*),
    NULL,
    NULL
FROM judges
UNION ALL
SELECT
    'Elements scored',
    COUNT(*),
    NULL,
    NULL
FROM elements
UNION ALL
SELECT
    'Element judge scores',
    COUNT(*),
    NULL,
    NULL
FROM element_judge_scores
UNION ALL
SELECT
    'PCS components',
    COUNT(*),
    NULL,
    NULL
FROM pcs_components
UNION ALL
SELECT
    'PCS judge scores',
    COUNT(*),
    NULL,
    NULL
FROM pcs_judge_scores;
