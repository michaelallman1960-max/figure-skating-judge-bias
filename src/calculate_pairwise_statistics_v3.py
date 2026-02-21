#!/usr/bin/env python3
"""
Pairwise Judge Bias Analysis — v3
===================================

Version 3 changes from v2:

  1. EXACT COMBINATORIAL TEST: the Monte Carlo permutation test (100,000 random
     shuffles) is replaced with a complete enumeration of ALL C(2k, k) ways to
     split the combined deviation pool into two groups of k. For a 9-element
     program (k=9), C(18,9) = 48,620 — small enough to enumerate exactly.
     This yields a fully deterministic, mathematically exact p-value with no
     sampling error and no dependence on a random seed.

     Exact combination counts by program length:
       k=5  (short RD segments): C(10,5)  =       252  — trivial
       k=9  (FD / FS / SP):      C(18,9)  =    48,620  — fast
       k=12 (some FS):           C(24,12) = 2,704,156  — ~1s per pair

  2. EXTREME COUNT STORED: the raw numerator of the p-value (e.g., 36 out of
     48,620) is stored in the new `extreme_count` column, enabling full audit
     of every significance result.

  3. NO RNG: the random number generator is eliminated entirely. Results are
     fully reproducible without any seed dependency.

  4. NUM_PERMUTATIONS column now stores the exact C(2k,k) count rather than
     the fixed value 100,000.

  5. TEST_TYPE is now "one-sided-exact" (was "one-sided").

Version 2 changes from v1 (still in effect):
  - TRUE MEDIAN: peer benchmark uses (4th + 5th sorted values) / 2.0.
  - SIGNIFICANCE THRESHOLDS: corrected to <= (not strict <) for 0.01 and 0.001.

Target database: figure_skating_ijs_v3.sqlite
Source (v2):     figure_skating_ijs_v2.sqlite  (untouched)
Original (v1):   figure_skating_ijs_seed.sqlite (untouched)

Extends the gold-silver bias methodology to ALL pairwise combinations
of competitors within an event.

For each judge and each pair of competitors, calculates:
1. BI(j) statistic (directional bias score)
2. Exact p-value via complete combinatorial enumeration
3. Significance flags
"""

import sqlite3
import math
import numpy as np
from itertools import combinations
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import time


@dataclass
class PairwiseStatistic:
    """Statistics for one judge comparing two competitors"""
    judge_id: int
    event_id: int
    entry_id_a: int
    entry_id_b: int

    skater_a_name: str
    skater_a_country: str
    skater_a_rank: int

    skater_b_name: str
    skater_b_country: str
    skater_b_rank: int

    judge_position: str
    judge_name: str
    judge_country: str

    bias_statistic: float
    num_elements_a: int
    num_elements_b: int
    total_elements: int

    p_value: float
    num_permutations: int    # v3: C(2k,k) exact count (e.g. 48,620 for k=9)
    test_type: str           # v3: always "one-sided-exact"
    permutation_z_score: float
    extreme_count: int       # v3: raw numerator of p-value (e.g. 36)

    mean_deviation_a: float
    mean_deviation_b: float
    differential: float

    is_significant_01: bool
    is_significant_001: bool
    is_significant_bonferroni: bool


class PairwiseAnalyzer:
    """Calculate pairwise bias statistics using exact combinatorial enumeration"""

    def __init__(self, db_path: str = 'figure_skating_ijs_v3.sqlite'):
        self.db_path = db_path

    def get_event_pairs(self, event_id: int) -> List[Tuple[int, int, int]]:
        """Get all pairwise combinations of competitors in an event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT entry_id, rank
            FROM entries
            WHERE event_id = ? AND rank IS NOT NULL
            ORDER BY rank
        """, (event_id,))

        entries = cursor.fetchall()
        conn.close()

        # Generate all pairs (higher rank first)
        pairs = []
        for i, (entry_a, rank_a) in enumerate(entries):
            for entry_b, rank_b in entries[i+1:]:
                pairs.append((entry_a, entry_b, rank_a))

        return pairs

    def get_deviations(self, conn: sqlite3.Connection, event_id: int,
                       entry_id: int, judge_id: int) -> List[float]:
        """
        Get peer-median deviations for one competitor as scored by one judge.

        For each element in the competitor's program, computes:
            deviation = judge's GOE integer − true_median(other 8 judges' GOE)

        The true median of 8 values = (4th value + 5th value) / 2.0 when sorted
        ascending. This can produce .5 values when the two middle scores differ.

        Returns a list of floats, one per element (typically 9 for senior events).
        All values remain in raw GOE integer units — no TSS conversion occurs here.

        Note on parameter count: the SQL uses 6 positional parameters (not 4)
        because the true-median computation requires two independent subqueries
        (OFFSET 3 and OFFSET 4), each needing event_id and judge_id. SQLite does
        not allow reuse of the same positional ? placeholder across subqueries.
        """

        cursor = conn.cursor()

        # For each element, compute the judge's deviation from the panel consensus.
        # Panel consensus = true mathematical median of the OTHER 8 judges' scores
        # (i.e., judge_id is explicitly excluded from the median calculation).
        # v2 FIX: (OFFSET 3 + OFFSET 4) / 2.0 — the true median of 8 sorted values.
        # v1 used OFFSET 4 alone (the 5th value = upper/ceiling median, always integer).
        cursor.execute("""
            WITH panel_medians AS (
                SELECT
                    el.element_id,
                    -- True median of OTHER 8 judges: average of 4th and 5th sorted values.
                    -- Requires two subqueries because SQLite OFFSET can only return one row.
                    -- Both subqueries exclude the focal judge (judge_id != ?) and
                    -- filter to this event's judges only (j2.event_id = ?).
                    (
                        (SELECT CAST(judge_goe_int AS REAL)
                         FROM element_judge_scores ejs2
                         JOIN judges j2 ON ejs2.judge_id = j2.judge_id
                         WHERE ejs2.element_id = el.element_id
                           AND j2.event_id = ?          -- param 1: event_id
                           AND ejs2.judge_id != ?        -- param 2: judge_id (exclude self)
                         ORDER BY judge_goe_int
                         LIMIT 1 OFFSET 3)              -- 4th value (0-indexed)
                        +
                        (SELECT CAST(judge_goe_int AS REAL)
                         FROM element_judge_scores ejs2
                         JOIN judges j2 ON ejs2.judge_id = j2.judge_id
                         WHERE ejs2.element_id = el.element_id
                           AND j2.event_id = ?          -- param 3: event_id (repeated)
                           AND ejs2.judge_id != ?        -- param 4: judge_id (repeated)
                         ORDER BY judge_goe_int
                         LIMIT 1 OFFSET 4)              -- 5th value (0-indexed)
                    ) / 2.0 AS peer_median
                FROM elements el
                WHERE el.entry_id = ?                   -- param 5: entry_id
            )
            SELECT
                ejs.judge_goe_int,
                pm.peer_median,
                (ejs.judge_goe_int - pm.peer_median) as deviation
            FROM element_judge_scores ejs
            JOIN panel_medians pm ON ejs.element_id = pm.element_id
            WHERE ejs.judge_id = ?                      -- param 6: judge_id
        """, (event_id, judge_id, event_id, judge_id, entry_id, judge_id))

        deviations = [row[2] for row in cursor.fetchall()]
        return deviations

    def calculate_bias_statistic(self, deviations_a: List[float],
                                 deviations_b: List[float]) -> float:
        """
        Calculate the BI(j) statistic (Bias Index) for a judge comparing pair (A, B).

        BI(j) = S(A) − S(B)
              = Σ[deviations_a] − Σ[deviations_b]

        where S(X) is the sum of the judge's peer-median deviations across all
        elements for competitor X. All values are in raw GOE integer units
        (no TSS conversion — that occurs later when computing reconstructed scores).

        Interpretation:
          BI(j) > 0 → judge scores A systematically higher than panel consensus
                       relative to how they score B (favors A over B)
          BI(j) < 0 → judge favors B over A
          BI(j) = 0 → judge's relative scoring matches the panel consensus

        Note: competitor A is always the higher-ranked of the two (lower rank number),
        so a positive BI(j) means the judge favors the better-ranked competitor.
        """
        sum_a = sum(deviations_a) if deviations_a else 0
        sum_b = -sum(deviations_b) if deviations_b else 0
        return sum_a + sum_b

    def exact_permutation_test(self, deviations_a: List[float],
                               deviations_b: List[float],
                               observed_bi: float) -> Tuple[float, float, int, int]:
        """
        Exact combinatorial permutation test for the BI(j) statistic.

        Under the null hypothesis, judge j is unbiased — their deviation pattern
        for competitors A and B is just a random draw from a common pool. If true,
        any assignment of the combined pool values to the two competitors is equally
        plausible, and the observed split is just one of C(2k, k) equally likely ones.

        Method:
          1. Combine all k deviations for A and k deviations for B into one pool
             of 2k values (e.g., 18 values for a 9-element program).
          2. Enumerate ALL C(2k, k) ways to split the pool into an A-group (k values)
             and a B-group (remaining k values).
          3. For each split, compute simulated BI(j) = sum(A-group) − sum(B-group).
          4. p-value = (number of splits as extreme or more extreme) / C(2k, k).

        IMPORTANT: This is a combined-pool split — all deviations for both competitors
        are pooled and reassigned. It is NOT a per-element reshuffling across all judges.

        Optimization: Since sum(B-group) = total_sum − sum(A-group), we compute only
        sum(A-group) per iteration using NumPy array indexing. The B-group sum is derived
        in O(1). This halves the inner-loop work compared to summing both groups.

        No random sampling. No seed. Fully deterministic and mathematically exact.

        Returns: (p_value, z_score, extreme_count, total_combinations)
          - p_value:            exact fraction of splits as extreme or more extreme
          - z_score:            (observed_bi − mean) / std of the exact null distribution
          - extreme_count:      raw numerator (e.g. 36) — stored for full auditability
          - total_combinations: C(2k,k) — the exact denominator (e.g. 48,620)
        """
        if not deviations_a or not deviations_b:
            return (1.0, 0.0, 0, 0)

        k = len(deviations_a)
        pool = np.array(deviations_a + deviations_b, dtype=np.float64)
        n = len(pool)
        total_sum = float(pool.sum())  # constant: sum(A) + sum(B) never changes
        indices = list(range(n))

        extreme = 0
        total = 0
        sim_stats = []

        # Enumerate all C(n, k) index subsets for the A-group.
        # B-group is the complement — its sum = total_sum − sum(A-group).
        for a_idx in combinations(indices, k):
            s_a = float(pool[list(a_idx)].sum())
            sim_bi = 2.0 * s_a - total_sum   # = s_a - (total_sum - s_a)
            sim_stats.append(sim_bi)
            total += 1
            # One-sided: count splits as extreme or more extreme than observed.
            # Uses >= / <= (not strict > / <) so boundary values are counted.
            if observed_bi >= 0:
                if sim_bi >= observed_bi:
                    extreme += 1
            else:
                if sim_bi <= observed_bi:
                    extreme += 1

        p_value = extreme / total

        # Exact null distribution statistics for z-score
        mean = sum(sim_stats) / total
        variance = sum((x - mean) ** 2 for x in sim_stats) / total
        std = math.sqrt(variance)
        z_score = (observed_bi - mean) / std if std > 0 else 0.0

        return (p_value, z_score, extreme, total)

    def analyze_pair(self, conn: sqlite3.Connection, event_id: int,
                     entry_a: int, entry_b: int, rank_a: int,
                     judge_id: int, judge_position: str, judge_name: str,
                     judge_country: str, num_pairs: int) -> Optional[PairwiseStatistic]:
        """
        Analyze one judge's bias for one pair of competitors.

        Uses exact_permutation_test() — no RNG parameter needed.
        """

        cursor = conn.cursor()

        # Fetch both competitors ordered by rank (ascending = better rank first).
        # comp_a is always the higher-ranked (lower rank number) of the pair.
        # This means a positive BI(j) consistently indicates the judge favored
        # the better-ranked skater — which is the convention used throughout.
        cursor.execute("""
            SELECT entry_id, team_name, noc, rank
            FROM entries
            WHERE entry_id IN (?, ?)
            ORDER BY rank
        """, (entry_a, entry_b))

        competitors = cursor.fetchall()
        if len(competitors) != 2:
            return None

        comp_a = competitors[0]  # higher-ranked (lower rank number)
        comp_b = competitors[1]  # lower-ranked (higher rank number)

        # Get deviations for each competitor
        dev_a = self.get_deviations(conn, event_id, comp_a[0], judge_id)
        dev_b = self.get_deviations(conn, event_id, comp_b[0], judge_id)

        if not dev_a or not dev_b:
            return None

        # Calculate bias statistic
        bias_stat = self.calculate_bias_statistic(dev_a, dev_b)

        # Run exact combinatorial test — deterministic, no RNG
        p_value, z_score, extreme_count, total_combos = self.exact_permutation_test(
            dev_a, dev_b, bias_stat
        )

        # Calculate descriptive statistics
        mean_dev_a = sum(dev_a) / len(dev_a) if dev_a else 0
        mean_dev_b = sum(dev_b) / len(dev_b) if dev_b else 0
        differential = mean_dev_a - mean_dev_b

        # Bonferroni correction for multiple testing
        bonferroni_threshold = 0.001 / num_pairs

        return PairwiseStatistic(
            judge_id=judge_id,
            event_id=event_id,
            entry_id_a=comp_a[0],
            entry_id_b=comp_b[0],

            skater_a_name=comp_a[1],
            skater_a_country=comp_a[2],
            skater_a_rank=comp_a[3],

            skater_b_name=comp_b[1],
            skater_b_country=comp_b[2],
            skater_b_rank=comp_b[3],

            judge_position=judge_position,
            judge_name=judge_name,
            judge_country=judge_country,

            bias_statistic=bias_stat,
            num_elements_a=len(dev_a),
            num_elements_b=len(dev_b),
            total_elements=len(dev_a) + len(dev_b),

            p_value=p_value,
            num_permutations=total_combos,   # v3: exact C(2k,k), e.g. 48,620
            test_type='one-sided-exact',     # v3: exact enumeration
            permutation_z_score=z_score,
            extreme_count=extreme_count,     # v3: raw numerator, e.g. 36

            mean_deviation_a=mean_dev_a,
            mean_deviation_b=mean_dev_b,
            differential=differential,

            # Thresholds use <= (not strict <) per the OSNR rule specification.
            # Boundary values (p exactly = 0.01 or 0.001) are counted as significant.
            is_significant_01=(p_value <= 0.01),
            is_significant_001=(p_value <= 0.001),
            is_significant_bonferroni=(p_value < bonferroni_threshold)  # strict < intentional
        )

    def store_statistic(self, conn: sqlite3.Connection, stat: PairwiseStatistic):
        """Store pairwise statistic in database, including extreme_count"""
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO pairwise_judge_statistics (
                judge_id, event_id, entry_id_a, entry_id_b,
                skater_a_name, skater_a_country, skater_a_rank,
                skater_b_name, skater_b_country, skater_b_rank,
                judge_position, judge_name, judge_country,
                bias_statistic, num_elements_a, num_elements_b, total_elements,
                p_value, num_permutations, test_type, permutation_z_score,
                extreme_count,
                mean_deviation_a, mean_deviation_b, differential,
                is_significant_01, is_significant_001, is_significant_bonferroni
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            stat.judge_id, stat.event_id, stat.entry_id_a, stat.entry_id_b,
            stat.skater_a_name, stat.skater_a_country, stat.skater_a_rank,
            stat.skater_b_name, stat.skater_b_country, stat.skater_b_rank,
            stat.judge_position, stat.judge_name, stat.judge_country,
            stat.bias_statistic, stat.num_elements_a, stat.num_elements_b, stat.total_elements,
            stat.p_value, stat.num_permutations, stat.test_type, stat.permutation_z_score,
            stat.extreme_count,
            stat.mean_deviation_a, stat.mean_deviation_b, stat.differential,
            stat.is_significant_01, stat.is_significant_001, stat.is_significant_bonferroni
        ))

    def analyze_event(self, event_id: int) -> int:
        """Analyze all pairwise combinations for all judges in an event"""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get event details
        cursor.execute("""
            SELECT e.discipline, e.segment, c.name
            FROM events e
            JOIN competitions c ON e.competition_id = c.competition_id
            WHERE e.event_id = ?
        """, (event_id,))

        event_info = cursor.fetchone()
        if not event_info:
            conn.close()
            return 0

        discipline, segment, comp_name = event_info

        print(f"\n{'='*70}")
        print(f"Event: {discipline} - {segment}")
        print(f"Competition: {comp_name}")
        print(f"{'='*70}\n")

        # Get all judges for this event
        cursor.execute("""
            SELECT DISTINCT j.judge_id, j.judge_position, j.judge_name, j.country_code
            FROM judges j
            WHERE j.event_id = ?
            ORDER BY j.judge_position
        """, (event_id,))

        judges = cursor.fetchall()

        if not judges:
            print("  ⚠️  No judges found")
            conn.close()
            return 0

        # Get all pairs
        pairs = self.get_event_pairs(event_id)
        num_pairs = len(pairs)

        print(f"  Judges: {len(judges)}")
        print(f"  Pairwise combinations: {num_pairs}")
        print(f"  Total tests: {len(judges) * num_pairs}")
        print(f"  Bonferroni threshold: p < {0.001/num_pairs:.2e}\n")

        # Analyze each judge-pair combination (no RNG — exact test)
        stats_stored = 0
        start_time = time.time()

        for judge_id, judge_pos, judge_name, judge_country in judges:
            print(f"  {judge_pos} {judge_name}...", end=' ', flush=True)

            pair_count = 0
            for entry_a, entry_b, rank_a in pairs:
                stat = self.analyze_pair(
                    conn, event_id, entry_a, entry_b, rank_a,
                    judge_id, judge_pos, judge_name, judge_country or '',
                    num_pairs
                )

                if stat:
                    self.store_statistic(conn, stat)
                    pair_count += 1

            print(f"{pair_count} pairs analyzed")
            stats_stored += pair_count

        conn.commit()

        # Summary
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_significant_001 = 1 THEN 1 ELSE 0 END) as sig_001,
                SUM(CASE WHEN is_significant_bonferroni = 1 THEN 1 ELSE 0 END) as sig_bonf
            FROM pairwise_judge_statistics
            WHERE event_id = ?
        """, (event_id,))

        total, sig_001, sig_bonf = cursor.fetchone()

        elapsed = time.time() - start_time
        print(f"\n  ✅ Stored {stats_stored} pairwise statistics")
        print(f"  📊 Significant (p ≤ 0.001): {sig_001}")
        print(f"  📊 Significant (Bonferroni): {sig_bonf}")
        print(f"  ⏱️  Time: {elapsed:.1f}s")

        conn.close()
        return stats_stored


def main():
    """Calculate pairwise statistics for all events with data"""

    print("\n" + "="*70)
    print("PAIRWISE JUDGE BIAS ANALYSIS — v3 (EXACT COMBINATORIAL TEST)")
    print("="*70)

    db_path = 'figure_skating_ijs_v3.sqlite'

    # Get events to analyze
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT e.event_id
        FROM events e
        JOIN entries en ON e.event_id = en.event_id
        JOIN elements el ON en.entry_id = el.entry_id
        JOIN element_judge_scores ejs ON el.element_id = ejs.element_id
        ORDER BY e.event_id
    """)

    event_ids = [row[0] for row in cursor.fetchall()]

    # Check which events already have complete pairwise data (resume support)
    already_done = set()
    try:
        cursor.execute("SELECT DISTINCT event_id FROM pairwise_judge_statistics")
        already_done = set(row[0] for row in cursor.fetchall())
    except Exception:
        pass

    conn.close()

    remaining = [eid for eid in event_ids if eid not in already_done]
    print(f"\nFound {len(event_ids)} events with judge score data")
    print(f"Already completed: {len(already_done)} events")
    print(f"Remaining: {len(remaining)} events\n")

    # Analyze each remaining event
    analyzer = PairwiseAnalyzer(db_path=db_path)
    total_stats = 0

    for event_id in remaining:
        stats_count = analyzer.analyze_event(event_id)
        total_stats += stats_count

    print("\n" + "="*70)
    print(f"✅ COMPLETE: {total_stats} pairwise statistics calculated")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
