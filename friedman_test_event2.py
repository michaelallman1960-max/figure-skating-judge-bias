#!/usr/bin/env python3
"""
friedman_test_event2.py
=======================
Tests the Friedman + Nemenyi approach on event_id=2 (OWG 2026 Ice Dance FD).

Two analyses:
  1. Friedman test: is there ANY systematic judge effect after controlling for
     skater/element quality? (skater-elements as blocks, judges as treatments)
  2. Residual-based BiasPoints: does J1's differential treatment of FRA vs USA
     survive when we properly remove the shared performance signal?

Compares to current isuimpact_quantile_v1 results from the database.
"""

import sqlite3
import numpy as np
from scipy import stats
import scikit_posthocs as sp
from itertools import combinations

DB = "/Users/allman/Library/CloudStorage/Dropbox/Dropbox Mike/Judging Bias/figure_skating_ijs_v4.sqlite"
EVENT_ID = 2

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# ── 1. Load raw GOE scores for event ────────────────────────────────────────
rows = conn.execute("""
    SELECT el.entry_id, el.element_no, j.judge_position, ejs.judge_goe_int,
           e.team_name, e.noc, e.rank
    FROM element_judge_scores ejs
    JOIN elements el ON ejs.element_id = el.element_id
    JOIN judges j ON ejs.judge_id = j.judge_id
    JOIN entries e ON el.entry_id = e.entry_id
    WHERE e.event_id = ?
    ORDER BY el.entry_id, el.element_no, j.judge_position
""", (EVENT_ID,)).fetchall()

print(f"Loaded {len(rows)} judge-element score rows for event_id={EVENT_ID}")

# Check judge_position format
sample_pos = rows[0]['judge_position']
print(f"Sample judge_position value: {repr(sample_pos)}")

# ── 2. Build matrix: rows=(entry_id, elem_pos), cols=judge_pos ──────────────
from collections import defaultdict
scores = defaultdict(dict)  # scores[(entry_id, elem_pos)][judge_pos] = goe
entry_meta = {}             # entry_id -> (team_name, noc, rank)

for r in rows:
    key = (r['entry_id'], r['element_no'])
    # Normalize judge_position to integer (handles "J1" or "1" formats)
    jp = r['judge_position']
    jp_int = int(str(jp).replace('J','').replace('j',''))
    scores[key][jp_int] = r['judge_goe_int']
    entry_meta[r['entry_id']] = (r['team_name'], r['noc'], r['rank'])

# Keep only rows where all 9 judges are present
judge_positions = list(range(1, 10))
complete_keys = [k for k, v in scores.items() if all(j in v for j in judge_positions)]
print(f"Element rows with all 9 judges present: {len(complete_keys)} / {len(scores)}")

# Build numpy matrix: shape (n_elements, 9)
matrix = np.array([[scores[k][j] for j in judge_positions] for k in complete_keys])
print(f"Matrix shape: {matrix.shape}  (blocks × treatments)")

# ── 3. Friedman test ─────────────────────────────────────────────────────────
stat, p_friedman = stats.friedmanchisquare(*[matrix[:, j] for j in range(9)])
print(f"\n{'='*60}")
print(f"FRIEDMAN TEST")
print(f"  χ² = {stat:.4f},  p = {p_friedman:.2e}")
print(f"  Interpretation: {'Significant judge effects detected' if p_friedman < 0.05 else 'No significant judge effects'}")

# ── 4. Nemenyi post-hoc ──────────────────────────────────────────────────────
print(f"\nNEMENYI POST-HOC (p-values, judge i vs judge j)")
nemenyi = sp.posthoc_nemenyi_friedman(matrix)
nemenyi.columns = [f"J{j}" for j in judge_positions]
nemenyi.index   = [f"J{j}" for j in judge_positions]

# Print just the significant pairs (p < 0.05)
print("\nSignificant pairs (p < 0.05):")
found_any = False
for i in range(9):
    for j in range(i+1, 9):
        p = nemenyi.iloc[i, j]
        if p < 0.05:
            print(f"  J{i+1} vs J{j+1}: p = {p:.4f}")
            found_any = True
if not found_any:
    print("  None")

# Print J1 row specifically
print("\nJ1 vs all other judges (Nemenyi p-values):")
for j in range(1, 9):
    p = nemenyi.iloc[0, j]
    sig = " ***" if p < 0.001 else (" **" if p < 0.01 else (" *" if p < 0.05 else ""))
    print(f"  J1 vs J{j+1}: p = {p:.4f}{sig}")

# ── 5. Residual-based BiasPoints: J1, FRA vs USA ────────────────────────────
print(f"\n{'='*60}")
print("RESIDUAL-BASED BIASPOINTS: J1, FRA vs USA")

# Get entry_ids for FRA and USA
entries = conn.execute("""
    SELECT entry_id, team_name, noc, rank FROM entries WHERE event_id = ?
""", (EVENT_ID,)).fetchall()

fra_id = next((e['entry_id'] for e in entries if e['noc'] == 'FRA'), None)
usa_id = next((e['entry_id'] for e in entries if e['noc'] == 'USA'), None)
print(f"  All entries: {[(e['entry_id'], e['noc'], e['rank']) for e in entries]}")
print(f"  FRA entry_id={fra_id}, USA entry_id={usa_id}")

# Compute trimmed mean per element (trim 1 from each end of 9)
def trimmed_mean_9(vals):
    """Trim 1 from each end of 9 values (matches ISU rule)."""
    s = sorted(vals)
    return np.mean(s[1:-1])  # drop min and max

# Get residuals for FRA and USA
def get_residuals(entry_id):
    """Returns list of (judge_pos, residual) for each element of entry_id."""
    entry_keys = [k for k in complete_keys if k[0] == entry_id]
    residuals = defaultdict(list)  # judge_pos -> [residuals across elements]
    for key in entry_keys:
        judge_goes = scores[key]
        panel_vals = [judge_goes[j] for j in judge_positions]
        tm = trimmed_mean_9(panel_vals)
        for j in judge_positions:
            residuals[j].append(judge_goes[j] - tm)
    return residuals

fra_resid = get_residuals(fra_id)
usa_resid = get_residuals(usa_id)

print(f"\n  FRA elements: {len(fra_resid[1])}, USA elements: {len(usa_resid[1])}")
print(f"\n  Per-judge Impact (residual sum) and BiasPoints(FRA,USA):")
print(f"  {'Judge':<8} {'I_j(FRA)':>10} {'I_j(USA)':>10} {'BiasPoints':>12}")
print(f"  {'-'*44}")

j1_bias = None
all_biaspoints = []
for j in judge_positions:
    i_fra = sum(fra_resid[j])
    i_usa = sum(usa_resid[j])
    bp = i_fra - i_usa
    all_biaspoints.append(bp)
    if j == 1:
        j1_bias = bp
    print(f"  J{j:<7} {i_fra:>10.3f} {i_usa:>10.3f} {bp:>12.3f}")

# ── 6. P-value for J1 via permutation on residuals ──────────────────────────
print(f"\n{'='*60}")
print("PERMUTATION TEST ON RESIDUALS (valid — exchangeability restored)")
print(f"  J1 BiasPoints(FRA,USA) = {j1_bias:.4f}")
print(f"  Panel mean BiasPoints  = {np.mean(all_biaspoints):.4f}")
print(f"  Panel std BiasPoints   = {np.std(all_biaspoints):.4f}")

# P-value: how often does a random judge (from panel) exceed |J1's BiasPoints|?
# Use all 9 judges as the reference distribution
extreme = sum(1 for bp in all_biaspoints if abs(bp) >= abs(j1_bias))
p_panel = extreme / len(all_biaspoints)
print(f"  P(|BiasPoints| >= |J1|) across panel = {p_panel:.4f}  (n=9, coarse)")

# More rigorous: permutation on FRA/USA residual labels (M=50,000)
M = 50000
rng = np.random.default_rng(20260223)

fra_resid_j1 = np.array(fra_resid[1])
usa_resid_j1 = np.array(usa_resid[1])
pooled = np.concatenate([fra_resid_j1, usa_resid_j1])
n_fra = len(fra_resid_j1)
observed_bp = sum(fra_resid_j1) - sum(usa_resid_j1)

count_extreme = 0
for _ in range(M):
    rng.shuffle(pooled)
    perm_bp = sum(pooled[:n_fra]) - sum(pooled[n_fra:])
    if abs(perm_bp) >= abs(observed_bp):
        count_extreme += 1

p_perm = (count_extreme + 1) / (M + 1)
print(f"\n  Residual-label permutation (M={M:,}, seed=20260223):")
print(f"  J1 BiasPoints(FRA,USA) = {observed_bp:.4f}")
print(f"  Exceedances = {count_extreme}, p = {p_perm:.4f}")

# ── 7. Compare to current database result ────────────────────────────────────
print(f"\n{'='*60}")
print("COMPARISON: Current DB result vs Friedman/Residual approach")

current = conn.execute("""
    SELECT bias_points, p_value, q_value_bh, judge_position, judge_name, judge_country,
           noc_a, noc_b, rank_a, rank_b
    FROM pairwise_impact_results
    WHERE event_id = ? AND judge_position = 1
      AND ((noc_a = 'FRA' AND noc_b = 'USA') OR (noc_a = 'USA' AND noc_b = 'FRA'))
""", (EVENT_ID,)).fetchall()

for row in current:
    print(f"  Current method: BiasPoints={row['bias_points']:.4f}, p={row['p_value']:.4f}, q={row['q_value_bh']:.4f}")
    print(f"  Judge: {row['judge_name']} ({row['judge_country']})")

print(f"\n  Residual method: BiasPoints={observed_bp:.4f}, p={p_perm:.4f}")
print(f"\n  BiasPoints comparison: current={current[0]['bias_points']:.4f}, residual={observed_bp:.4f}")
print(f"  (difference = {abs(current[0]['bias_points'] - observed_bp):.4f} pts)")

conn.close()
print(f"\nDone.")
