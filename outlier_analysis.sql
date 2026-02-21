-- Outlier Analysis: France vs USA Ice Dance Free Dance
-- Using proper SQLite functions (no STDEV, compute manually)

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
        jet.reconstructed_total
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
        -- Manual standard deviation calculation for SQLite
        SQRT(AVG(differential * differential) - AVG(differential) * AVG(differential)) as std_diff,
        COUNT(*) as n
    FROM judge_diffs
)
SELECT
    jd.judge_position,
    jd.judge_name,
    jd.country_code,
    ROUND(jd.fra_score, 2) as FRA_score,
    ROUND(jd.usa_score, 2) as USA_score,
    ROUND(jd.differential, 2) as differential,
    ROUND(s.mean_diff, 2) as mean_differential,
    ROUND(s.std_diff, 2) as std_dev,
    ROUND((jd.differential - s.mean_diff) / NULLIF(s.std_diff, 0), 3) as z_score,
    CASE
        WHEN ABS((jd.differential - s.mean_diff) / NULLIF(s.std_diff, 0)) > 2.0 THEN '🚨 EXTREME OUTLIER'
        WHEN ABS((jd.differential - s.mean_diff) / NULLIF(s.std_diff, 0)) > 1.5 THEN '⚠️  Significant'
        WHEN ABS((jd.differential - s.mean_diff) / NULLIF(s.std_diff, 0)) > 1.0 THEN '⚠️  Notable'
        ELSE ''
    END as outlier_flag
FROM judge_diffs jd
CROSS JOIN stats s
ORDER BY differential DESC;
