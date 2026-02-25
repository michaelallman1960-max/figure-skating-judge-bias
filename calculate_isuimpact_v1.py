#!/usr/bin/env python3
"""
calculate_isuimpact_v1.py

ISU-impact pairwise judge bias pipeline — method: isuimpact_quantile_v1

For each event, each judge, and each pair of competitors (A, B):
  1. Compute the ISU-impact delta for every scoring row (GOE elements + PCS components)
     by replacing the judge's mark with the median-of-the-other-8 and measuring the
     point difference through the published trimmed-mean rounding mechanism.
  2. Aggregate: I_j(T) = Σ delta_{j,r}  (all rows of competitor T)
  3. Pairwise bias: B_j(A,B) = I_j(A) - I_j(B)
  4. Permutation p-value: style-adjusted quantile permutation null (10,000 reps).
  5. BH-FDR correction within event.

Writes to: pairwise_impact_results  and  judge_team_impacts

Usage:
    python3 calculate_isuimpact_v1.py [options]
    --dry-run          Compute and print; do NOT write to DB
    --event-id N       Process only this event (validation / single-event run)
    --permutations N   Default 5000; use 10000 for publication
    --seed N           RNG seed (default 20260223)
    --workers N        Parallel processes (default 4)
    --cdf-scope S      'global' (default) or 'event'

Validation target (OWG 2026 Ice Dance Free Dance, event_id=2):
    J1 FRA vs USA: bias_points ≈ +1.19, p ≈ 0.0003, q ≈ 0.034  (10k perms, effective GOE factors)
"""

import argparse
import itertools
import math
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np
from statsmodels.stats.multitest import multipletests

# ── Constants ─────────────────────────────────────────────────────────────────

DB_PATH      = "/Users/allman/Library/CloudStorage/Dropbox/Dropbox Mike/Judging Bias/figure_skating_ijs_v4.sqlite"
SCHEMA_PATH  = "/Users/allman/Library/CloudStorage/Dropbox/Dropbox Mike/Judging Bias/isuimpact_schema.sql"
METHOD_VER   = "isuimpact_quantile_v1"
DEFAULT_SEED = 20260223
DEFAULT_PERMS = 10_000   # matches established production standard (10k used for OWG 2026 FD run)

# Map from pcs_components.component_name to our internal category key
PCS_CAT_MAP = {
    "Skating Skills": "PCS_SS",
    "Composition":    "PCS_CO",
    "Presentation":   "PCS_PR",
    "Performance":    "PCS_PE",
    "Transitions":    "PCS_TR",
    "Interpretation of the Music": "PCS_IM",
}

# ── Rounding ──────────────────────────────────────────────────────────────────

def round_half_up(x: float, n: int = 2) -> float:
    """
    Round to n decimal places using round-half-away-from-zero (Excel ROUND semantics).
    Python's built-in round() uses banker's rounding which can differ for .5 cases.
    """
    m = 10 ** n
    return math.floor(x * m + 0.5) / m


# ── ISU-exact row scoring ─────────────────────────────────────────────────────

def score_goe_row(marks9: list, base_value: float, factor: float) -> float:
    """
    Compute element score using ISU trimmed-mean mechanics (exact Excel rounding).
    TrimmedSum = SUM - MAX - MIN  (remove 1 high + 1 low from 9 judges)
    TrimmedMean = TrimmedSum / 7
    PanelGOE = round_half_up(TrimmedMean * factor, 2)
    ElementScore = round_half_up(base_value + PanelGOE, 2)
    """
    s = sorted(marks9)
    trimmed_sum = sum(s[1:8])
    trimmed_mean = trimmed_sum / 7.0
    panel_goe = round_half_up(trimmed_mean * factor)
    return round_half_up(base_value + panel_goe)


def score_pcs_row(marks9: list, factor: float) -> float:
    """
    Compute PCS component score using ISU trimmed-mean mechanics.
    PanelAvg = round_half_up(TrimmedMean, 2)
    ComponentScore = round_half_up(PanelAvg * factor, 2)
    """
    s = sorted(marks9)
    trimmed_sum = sum(s[1:8])
    trimmed_mean = trimmed_sum / 7.0
    panel_avg = round_half_up(trimmed_mean)
    return round_half_up(panel_avg * factor)


def median_of_8(marks9: list, j: int) -> float:
    """Median of the 8 values excluding position j. May be fractional (avg of 4th+5th)."""
    others = [marks9[k] for k in range(9) if k != j]
    others.sort()
    return (others[3] + others[4]) / 2.0


# ── CDF helpers ───────────────────────────────────────────────────────────────

def mark_to_percentile(x: float, sorted_cdf: np.ndarray, rng: np.random.Generator) -> float:
    """
    Convert mark x to a uniform [0,1] percentile within the judge's empirical CDF.
    Randomized within tied intervals to break ties uniformly.
    """
    n = len(sorted_cdf)
    lo = int(np.searchsorted(sorted_cdf, x, side='left'))
    hi = int(np.searchsorted(sorted_cdf, x, side='right'))
    if lo == hi:
        # x not found; shouldn't happen for observed marks — use midpoint
        return lo / n
    return rng.uniform(lo / n, hi / n)


def percentile_to_mark(u: float, sorted_cdf: np.ndarray) -> float:
    """Inverse CDF: map uniform percentile back to a mark in the judge's distribution."""
    n = len(sorted_cdf)
    idx = min(int(u * n), n - 1)
    return float(sorted_cdf[idx])


# ── Database helpers ──────────────────────────────────────────────────────────

def get_events(conn: sqlite3.Connection, event_id: int | None) -> list[int]:
    if event_id is not None:
        return [event_id]
    rows = conn.execute("SELECT event_id FROM events ORDER BY event_id").fetchall()
    return [r[0] for r in rows]


def build_all_cdfs(conn: sqlite3.Connection) -> dict:
    """
    Build per-judge CDFs for ALL judges in the database in a single pass.
    Called once at startup before the event loop.

    Returns:
        all_cdfs[judge_name][category] = np.ndarray (sorted marks)
    """
    print("Building global CDFs for all judges...", flush=True)
    names = [r[0] for r in conn.execute(
        "SELECT DISTINCT judge_name FROM judges WHERE judge_name IS NOT NULL"
    ).fetchall()]

    all_cdfs: dict = {}
    for name in names:
        all_ids = [r[0] for r in conn.execute(
            "SELECT judge_id FROM judges WHERE judge_name = ?", (name,)
        ).fetchall()]
        ph = ",".join("?" * len(all_ids))

        goe_rows = conn.execute(
            f"SELECT judge_goe_int FROM element_judge_scores WHERE judge_id IN ({ph})",
            all_ids
        ).fetchall()
        goe_marks = np.array([r[0] for r in goe_rows], dtype=float)
        if len(goe_marks) == 0:
            goe_marks = np.array([0.0])

        pcs_cdfs: dict = {}
        for comp_name, cat_key in PCS_CAT_MAP.items():
            pcs_rows = conn.execute(
                f"""SELECT pjs.judge_mark
                    FROM pcs_judge_scores pjs
                    JOIN pcs_components pc ON pjs.pcs_id = pc.pcs_id
                    WHERE pjs.judge_id IN ({ph}) AND pc.component_name = ?""",
                all_ids + [comp_name]
            ).fetchall()
            marks = np.array([r[0] for r in pcs_rows], dtype=float)
            if len(marks) > 0:
                pcs_cdfs[cat_key] = np.sort(marks)

        all_cdfs[name] = {"GOE": np.sort(goe_marks), **pcs_cdfs}

    print(f"  Built CDFs for {len(all_cdfs)} judges.", flush=True)
    return all_cdfs


def get_cdfs_for_panel(all_cdfs: dict, panel: list) -> dict:
    """
    Extract per-position CDFs for the 9 judges in this event's panel
    from the pre-built global CDF dict.

    Returns: cdfs[judge_position][category] = sorted np.ndarray
    """
    cdfs: dict = {}
    for jinfo in panel:
        pos  = jinfo["position"]
        name = jinfo.get("name")
        if name and name in all_cdfs:
            cdfs[pos] = all_cdfs[name]
        else:
            cdfs[pos] = {"GOE": np.array([0.0])}  # fallback — warns below
            if name:
                print(f"  ⚠️  {pos} ({name}): not found in prebuilt CDFs", flush=True)
    return cdfs


def build_global_cdfs(conn: sqlite3.Connection, event_id: int) -> dict:
    """
    Build per-judge empirical CDFs using all historical marks for each judge in the panel.

    Returns:
        cdfs[judge_position][category] = np.ndarray (sorted marks)

    judge_id in our DB is per-event, not per-person. We match by judge_name across events.
    Category keys: 'GOE', 'PCS_SS', 'PCS_CO', 'PCS_PR' (and any others present).
    """
    panel = conn.execute(
        "SELECT judge_id, judge_position, judge_name FROM judges WHERE event_id = ? ORDER BY judge_position",
        (event_id,)
    ).fetchall()

    cdfs = {}
    warned = []

    for judge_id, pos, name in panel:
        if name is None:
            # No name — fall back to marks from this event only
            all_ids = [judge_id]
            warned.append(f"  ⚠️  {pos}: no name — using event-scope CDF")
        else:
            all_ids_rows = conn.execute(
                "SELECT judge_id FROM judges WHERE judge_name = ?", (name,)
            ).fetchall()
            all_ids = [r[0] for r in all_ids_rows]

        # GOE marks
        placeholders = ",".join("?" * len(all_ids))
        goe_rows = conn.execute(
            f"SELECT judge_goe_int FROM element_judge_scores WHERE judge_id IN ({placeholders})",
            all_ids
        ).fetchall()
        goe_marks = np.array([r[0] for r in goe_rows], dtype=float)

        if len(goe_marks) == 0:
            warned.append(f"  ⚠️  {pos} ({name}): 0 GOE marks found")
            goe_marks = np.array([0.0])

        if len(goe_marks) < 50:
            warned.append(f"  ⚠️  {pos} ({name}): sparse GOE CDF ({len(goe_marks)} marks)")

        pcs_cdfs = {}
        for comp_name, cat_key in PCS_CAT_MAP.items():
            pcs_rows = conn.execute(
                f"""SELECT pjs.judge_mark
                    FROM pcs_judge_scores pjs
                    JOIN pcs_components pc ON pjs.pcs_id = pc.pcs_id
                    WHERE pjs.judge_id IN ({placeholders})
                      AND pc.component_name = ?""",
                all_ids + [comp_name]
            ).fetchall()
            marks = np.array([r[0] for r in pcs_rows], dtype=float)
            if len(marks) > 0:
                pcs_cdfs[cat_key] = np.sort(marks)

        cdfs[pos] = {"GOE": np.sort(goe_marks), **pcs_cdfs}

    for w in warned:
        print(w)

    return cdfs


def build_event_cdfs(conn: sqlite3.Connection, event_id: int) -> dict:
    """Per-event CDFs (fallback / alternative to global)."""
    panel = conn.execute(
        "SELECT judge_id, judge_position FROM judges WHERE event_id = ? ORDER BY judge_position",
        (event_id,)
    ).fetchall()

    cdfs = {}
    for judge_id, pos in panel:
        goe_rows = conn.execute(
            "SELECT judge_goe_int FROM element_judge_scores WHERE judge_id = ?",
            (judge_id,)
        ).fetchall()
        goe_marks = np.array([r[0] for r in goe_rows], dtype=float)
        if len(goe_marks) == 0:
            goe_marks = np.array([0.0])

        pcs_cdfs = {}
        for comp_name, cat_key in PCS_CAT_MAP.items():
            pcs_rows = conn.execute(
                """SELECT pjs.judge_mark
                   FROM pcs_judge_scores pjs
                   JOIN pcs_components pc ON pjs.pcs_id = pc.pcs_id
                   WHERE pjs.judge_id = ? AND pc.component_name = ?""",
                (judge_id, comp_name)
            ).fetchall()
            marks = np.array([r[0] for r in pcs_rows], dtype=float)
            if len(marks) > 0:
                pcs_cdfs[cat_key] = np.sort(marks)

        cdfs[pos] = {"GOE": np.sort(goe_marks), **pcs_cdfs}

    return cdfs


def load_event_data(conn: sqlite3.Connection, event_id: int):
    """
    Load GOE and PCS rows for all competitors in the event.

    Returns:
        entries: list of dicts {entry_id, rank, team_name, noc}
        rows: list of dicts {
            entry_id, row_type ('GOE'|'PCS_xx'), base_value, factor,
            marks: {judge_position: float}, category: str
        }
        panel: list of dicts {judge_id, position, name, country}
    """
    # Entries
    entry_rows = conn.execute(
        "SELECT entry_id, rank, team_name, noc FROM entries WHERE event_id = ? ORDER BY rank",
        (event_id,)
    ).fetchall()
    entries = [{"entry_id": r[0], "rank": r[1], "team": r[2], "noc": r[3]} for r in entry_rows]
    entry_ids = [e["entry_id"] for e in entries]

    if not entry_ids:
        return entries, [], []

    # Panel
    panel_rows = conn.execute(
        "SELECT judge_id, judge_position, judge_name, country_code FROM judges "
        "WHERE event_id = ? ORDER BY judge_position",
        (event_id,)
    ).fetchall()
    panel = [{"judge_id": r[0], "position": r[1], "name": r[2], "country": r[3]} for r in panel_rows]
    positions = [p["position"] for p in panel]

    # GOE data — pivot to one row per (entry_id, element_id)
    # Also fetch panel_goe_points so we can derive an accurate effective_factor per element.
    # goe_factor_inferred is wrong for certain Ice Dance combined elements (e.g. SyTw, OFT);
    # deriving factor = panel_goe_points / trimmed_mean is more reliable.
    ph = ",".join("?" * len(entry_ids))
    goe_raw = conn.execute(
        f"""SELECT e.entry_id, el.element_id, el.element_no,
                   el.base_value, el.goe_factor_inferred, el.panel_goe_points,
                   j.judge_position, ejs.judge_goe_int
            FROM element_judge_scores ejs
            JOIN judges  j  ON ejs.judge_id  = j.judge_id
            JOIN elements el ON ejs.element_id = el.element_id
            JOIN entries  e  ON el.entry_id   = e.entry_id
            WHERE e.entry_id IN ({ph})
              AND j.event_id = ?
            ORDER BY e.rank, el.element_no, j.judge_position""",
        entry_ids + [event_id]
    ).fetchall()

    # Aggregate GOE into rows; store panel_goe_points for effective_factor derivation
    goe_rows_dict = {}  # (entry_id, element_id) → dict
    for entry_id, element_id, elem_no, base_val, factor_inf, panel_goe, jpos, goe_int in goe_raw:
        key = (entry_id, element_id)
        if key not in goe_rows_dict:
            goe_rows_dict[key] = {
                "entry_id": entry_id,
                "row_type": "GOE",
                "category": "GOE",
                "element_no": elem_no,
                "base_value": float(base_val) if base_val is not None else 0.0,
                "factor_inferred": float(factor_inf) if factor_inf is not None else 1.0,
                "panel_goe_points": float(panel_goe) if panel_goe is not None else None,
                "factor": float(factor_inf) if factor_inf is not None else 1.0,  # overwritten below
                "marks": {},
            }
        goe_rows_dict[key]["marks"][jpos] = float(goe_int)

    # Derive effective_factor per GOE element from stored panel_goe_points and actual marks.
    # This corrects goe_factor_inferred for elements where it was computed incorrectly
    # (e.g. synchronized twizzle and OFT elements in Ice Dance, factor ≈ 0.72 vs stored 0.60).
    for key, row in goe_rows_dict.items():
        stored_goe = row["panel_goe_points"]
        if stored_goe is not None and len(row["marks"]) == 9:
            marks9 = sorted(row["marks"].values())
            trimmed_mean = sum(marks9[1:8]) / 7.0
            if abs(trimmed_mean) > 0.001:
                row["factor"] = stored_goe / trimmed_mean
            # else: trimmed mean is ~0; keep factor_inferred (delta will be ~0 either way)

    # PCS data
    pcs_raw = conn.execute(
        f"""SELECT e.entry_id, pc.pcs_id, pc.component_name, pc.factor,
                   j.judge_position, pjs.judge_mark
            FROM pcs_judge_scores pjs
            JOIN judges j          ON pjs.judge_id  = j.judge_id
            JOIN pcs_components pc ON pjs.pcs_id    = pc.pcs_id
            JOIN entries e         ON pc.entry_id   = e.entry_id
            WHERE e.entry_id IN ({ph})
              AND j.event_id = ?
            ORDER BY e.rank, pc.component_name, j.judge_position""",
        entry_ids + [event_id]
    ).fetchall()

    pcs_rows_dict = {}  # (entry_id, pcs_id) → dict
    for entry_id, pcs_id, comp_name, factor, jpos, mark in pcs_raw:
        key = (entry_id, pcs_id)
        cat = PCS_CAT_MAP.get(comp_name, f"PCS_{comp_name[:2].upper()}")
        if key not in pcs_rows_dict:
            pcs_rows_dict[key] = {
                "entry_id": entry_id,
                "row_type": "PCS",
                "category": cat,
                "component_name": comp_name,
                "base_value": 0.0,
                "factor": float(factor) if factor is not None else 1.0,
                "marks": {},
            }
        pcs_rows_dict[key]["marks"][jpos] = float(mark)

    # Combine, keeping only rows that have all 9 judge positions
    all_rows = []
    incomplete = 0
    for row in list(goe_rows_dict.values()) + list(pcs_rows_dict.values()):
        if len(row["marks"]) < len(positions):
            incomplete += 1
        else:
            all_rows.append(row)

    if incomplete:
        print(f"  ⚠️  event {event_id}: {incomplete} rows with <9 judge marks skipped")

    return entries, all_rows, panel


# ── Core computation ──────────────────────────────────────────────────────────

def compute_deltas(rows: list, positions: list[str]) -> np.ndarray:
    """
    Compute delta[j, r] = F_r(actual) - F_r(neutralized_j) for all rows and judges.

    Returns:
        delta: np.ndarray of shape (9, R)  where R = number of rows
        X_obs: np.ndarray of shape (R, 9)  observed marks matrix
        categories: list[str] of length R
    """
    R = len(rows)
    J = len(positions)
    pos_idx = {p: i for i, p in enumerate(positions)}

    delta = np.zeros((J, R), dtype=float)
    X_obs = np.zeros((R, J), dtype=float)
    categories = []

    for r, row in enumerate(rows):
        marks9 = [row["marks"][p] for p in positions]
        bv = row["base_value"]
        f  = row["factor"]

        # Actual score
        if row["row_type"] == "GOE":
            f_actual = score_goe_row(marks9, bv, f)
        else:
            f_actual = score_pcs_row(marks9, f)

        X_obs[r] = marks9
        categories.append(row["category"])

        for j, pos in enumerate(positions):
            med = median_of_8(marks9, j)
            marks_neut = marks9.copy()
            marks_neut[j] = med

            if row["row_type"] == "GOE":
                f_neut = score_goe_row(marks_neut, bv, f)
            else:
                f_neut = score_pcs_row(marks_neut, f)

            delta[j, r] = f_actual - f_neut

    return delta, X_obs, categories


def compute_impacts_and_bias(delta: np.ndarray, rows: list, entries: list):
    """
    Aggregate delta into I_j(T) impact totals and B_j(A,B) pairwise bias.

    Returns:
        I_obs: np.ndarray (J, N)  — impact of judge j on competitor t
        B_obs: np.ndarray (J, P)  — bias of judge j for pair p
        pairs: list of (idx_a, idx_b) tuples indexing into entries list
    """
    J = delta.shape[0]
    N = len(entries)
    entry_id_to_idx = {e["entry_id"]: i for i, e in enumerate(entries)}

    # Build (J, N) impact matrix
    I_obs = np.zeros((J, N), dtype=float)
    for r, row in enumerate(rows):
        t = entry_id_to_idx[row["entry_id"]]
        I_obs[:, t] += delta[:, r]

    # All ordered pairs (A, B) where rank_a < rank_b  →  (better, worse)
    pairs = list(itertools.combinations(range(N), 2))  # sorted by entry order (rank)
    P = len(pairs)

    B_obs = np.zeros((J, P), dtype=float)
    a_idx = np.array([p[0] for p in pairs])
    b_idx = np.array([p[1] for p in pairs])
    B_obs = I_obs[:, a_idx] - I_obs[:, b_idx]

    return I_obs, B_obs, pairs


# ── Permutation test ──────────────────────────────────────────────────────────

def run_permutation_test(
    X_obs: np.ndarray,
    B_obs: np.ndarray,
    rows: list,
    entries: list,
    cdfs: dict,
    positions: list[str],
    categories: list[str],
    n_perms: int,
    seed: int,
) -> np.ndarray:
    """
    Style-adjusted quantile permutation null.

    For each permutation:
      1. Within each row, permute the 9 percentile labels across judge positions.
      2. Map each permuted percentile back through its receiver-judge's CDF.
      3. Recompute B_j^perm(A,B) for all pairs.
      4. Accumulate exceedances: |B_perm| >= |B_obs|.

    Returns p_vals: np.ndarray (J, P)
    """
    R, J = X_obs.shape
    P = B_obs.shape[1]

    rng = np.random.default_rng(seed)

    # Build U_obs matrix (R × 9) — observed marks converted to percentiles
    U_obs = np.zeros((R, J), dtype=float)
    _warned_fallback: set = set()  # deduplicate: one warning per (position, category)
    for r in range(R):
        cat = categories[r]
        for j, pos in enumerate(positions):
            cdf_arr = cdfs.get(pos, {}).get(cat)
            if cdf_arr is None or len(cdf_arr) == 0:
                # No CDF for this category — fallback to 0.5 (neutral percentile)
                key = (pos, cat)
                if key not in _warned_fallback:
                    print(f"  ⚠️  Fallback 0.5: pos={pos}, cat={cat} — "
                          f"no career CDF available; p-values for this judge may be unreliable",
                          flush=True)
                    _warned_fallback.add(key)
                U_obs[r, j] = 0.5
            else:
                U_obs[r, j] = mark_to_percentile(X_obs[r, j], cdf_arr, rng)

    exceed = np.zeros((J, P), dtype=float)
    abs_B_obs = np.abs(B_obs)

    entry_id_to_idx = {e["entry_id"]: i for i, e in enumerate(entries)}
    pairs = list(itertools.combinations(range(len(entries)), 2))
    a_idx = np.array([p[0] for p in pairs])
    b_idx = np.array([p[1] for p in pairs])

    for perm_num in range(n_perms):
        # Build permuted marks matrix
        X_perm = np.empty((R, J), dtype=float)
        for r in range(R):
            cat = categories[r]
            perm = rng.permutation(J)
            for j in range(J):
                donor_u = U_obs[r, perm[j]]    # percentile from donor position
                cdf_arr = cdfs.get(positions[j], {}).get(cat)
                if cdf_arr is None or len(cdf_arr) == 0:
                    X_perm[r, j] = X_obs[r, j]  # no CDF — keep original
                else:
                    X_perm[r, j] = percentile_to_mark(donor_u, cdf_arr)

        # Recompute delta and B for this permutation
        delta_perm, _, _ = compute_deltas(
            [dict(row, marks={positions[j]: X_perm[r, j] for j in range(J)})
             for r, row in enumerate(rows)],
            positions
        )
        I_perm = np.zeros((J, len(entries)), dtype=float)
        for r, row in enumerate(rows):
            t = entry_id_to_idx[row["entry_id"]]
            I_perm[:, t] += delta_perm[:, r]
        B_perm = I_perm[:, a_idx] - I_perm[:, b_idx]

        exceed += (np.abs(B_perm) >= abs_B_obs)

    p_vals = (1.0 + exceed) / (n_perms + 1.0)
    return p_vals


def apply_bh_fdr(p_vals: np.ndarray) -> np.ndarray:
    """BH-FDR correction across all J×P tests within the event."""
    shape = p_vals.shape
    flat = p_vals.ravel()
    _, q_flat, _, _ = multipletests(flat, method='fdr_bh')
    return q_flat.reshape(shape)


# ── Output helpers ────────────────────────────────────────────────────────────

def format_results(
    event_id: int,
    entries: list,
    panel: list,
    I_obs: np.ndarray,
    B_obs: np.ndarray,
    p_vals: np.ndarray,
    q_vals: np.ndarray,
    pairs: list,
    n_perms: int,
    seed: int,
) -> tuple[list, list]:
    """
    Build row lists for pairwise_impact_results and judge_team_impacts.
    """
    now = datetime.now(timezone.utc).isoformat()
    J = len(panel)

    # Impact rows
    impact_rows = []
    for j, jinfo in enumerate(panel):
        for t, entry in enumerate(entries):
            impact_rows.append((
                METHOD_VER, event_id,
                jinfo["judge_id"], jinfo["position"], jinfo["name"], jinfo["country"],
                entry["entry_id"], entry["team"], entry["noc"], entry["rank"],
                float(I_obs[j, t]),
                now,
            ))

    # Pairwise result rows
    result_rows = []
    for p_idx, (a_idx, b_idx) in enumerate(pairs):
        ea = entries[a_idx]
        eb = entries[b_idx]
        for j, jinfo in enumerate(panel):
            bp   = float(B_obs[j, p_idx])
            pval = float(p_vals[j, p_idx])
            qval = float(q_vals[j, p_idx])
            vote = "A" if bp > 0 else ("B" if bp < 0 else "tie")
            result_rows.append((
                METHOD_VER, event_id,
                jinfo["judge_id"], jinfo["position"], jinfo["name"], jinfo["country"],
                ea["entry_id"], ea["team"], ea["noc"], ea["rank"],
                eb["entry_id"], eb["team"], eb["noc"], eb["rank"],
                bp, vote, pval, qval, n_perms, seed,
                now,
            ))

    return result_rows, impact_rows


def print_dry_run_summary(event_id, entries, panel, B_obs, p_vals, q_vals, pairs):
    """Print key stats and notable results."""
    sig_mask = q_vals < 0.05
    n_sig = sig_mask.sum()
    print(f"\n  event_id={event_id}: {len(entries)} competitors, {len(panel)} judges, "
          f"{len(pairs)} pairs, {B_obs.shape[1]*len(panel)} tests")
    print(f"  Significant (BH q≤0.05): {n_sig} / {B_obs.shape[1]*len(panel)}")

    # Print top 10 by |bias_points| among significant results
    J = len(panel)
    hits = []
    for j, jinfo in enumerate(panel):
        for p_idx, (a, b) in enumerate(pairs):
            if q_vals[j, p_idx] < 0.05:
                hits.append((abs(B_obs[j, p_idx]), j, p_idx, a, b))
    hits.sort(reverse=True)
    for rank, (absbp, j, p_idx, a, b) in enumerate(hits[:10], 1):
        ea = entries[a]; eb = entries[b]
        jinfo = panel[j]
        bp = B_obs[j, p_idx]
        print(f"  [{rank:2d}] {jinfo['position']} {jinfo['name'] or '?':30s}  "
              f"{ea['team']:6s} vs {eb['team']:6s}  "
              f"bias={bp:+.4f}  p={p_vals[j,p_idx]:.4f}  q={q_vals[j,p_idx]:.4f}")


# ── DB write ──────────────────────────────────────────────────────────────────

def write_results(conn, result_rows, impact_rows, event_id, dry_run):
    if dry_run:
        return
    # Log if overwriting existing rows (idempotency audit trail)
    existing = conn.execute(
        "SELECT COUNT(*) FROM pairwise_impact_results WHERE method_version=? AND event_id=?",
        (METHOD_VER, event_id)
    ).fetchone()[0]
    if existing > 0:
        print(f"  ℹ️  Overwriting {existing} existing rows for event {event_id}", flush=True)
    try:
        conn.execute(
            "DELETE FROM pairwise_impact_results WHERE method_version=? AND event_id=?",
            (METHOD_VER, event_id)
        )
        conn.execute(
            "DELETE FROM judge_team_impacts WHERE method_version=? AND event_id=?",
            (METHOD_VER, event_id)
        )
        conn.executemany(
            """INSERT INTO pairwise_impact_results
               (method_version, event_id, judge_id, judge_position, judge_name, judge_country,
                entry_id_a, team_a, noc_a, rank_a, entry_id_b, team_b, noc_b, rank_b,
                bias_points, vote, p_value, q_value_bh, permutations, rng_seed, calculated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            result_rows
        )
        conn.executemany(
            """INSERT INTO judge_team_impacts
               (method_version, event_id, judge_id, judge_position, judge_name, judge_country,
                entry_id, team, noc, rank, impact_points, calculated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            impact_rows
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise  # re-raise so caller can log and continue


# ── Per-event driver ──────────────────────────────────────────────────────────

def process_event(
    conn: sqlite3.Connection,
    event_id: int,
    n_perms: int,
    seed: int,
    cdf_scope: str,
    dry_run: bool,
    prebuilt_all_cdfs: dict | None = None,
) -> dict:
    """Process one event. Returns summary dict."""
    t0 = time.perf_counter()

    entries, rows, panel = load_event_data(conn, event_id)
    if not entries or not rows:
        return {"event_id": event_id, "status": "skipped (no data)", "elapsed": 0}

    positions = [p["position"] for p in panel]
    if len(positions) != 9:
        print(f"  event {event_id}: {len(positions)} judges (expected 9) — skipping", flush=True)
        return {"event_id": event_id, "status": f"skipped ({len(positions)} judges)", "elapsed": 0}

    # Build CDFs — use prebuilt if available (much faster for full runs)
    if prebuilt_all_cdfs is not None:
        cdfs = get_cdfs_for_panel(prebuilt_all_cdfs, panel)
    elif cdf_scope == "global":
        cdfs = build_global_cdfs(conn, event_id)
    else:
        cdfs = build_event_cdfs(conn, event_id)

    # Compute observed deltas → impacts → bias
    delta, X_obs, categories = compute_deltas(rows, positions)
    I_obs, B_obs, pairs = compute_impacts_and_bias(delta, rows, entries)

    # Permutation test
    p_vals = run_permutation_test(
        X_obs, B_obs, rows, entries, cdfs, positions, categories, n_perms, seed
    )
    q_vals = apply_bh_fdr(p_vals)

    # Format and write
    result_rows, impact_rows = format_results(
        event_id, entries, panel, I_obs, B_obs, p_vals, q_vals, pairs, n_perms, seed
    )
    write_results(conn, result_rows, impact_rows, event_id, dry_run)

    elapsed = time.perf_counter() - t0
    n_sig = (q_vals < 0.05).sum()

    if dry_run:
        print_dry_run_summary(event_id, entries, panel, B_obs, p_vals, q_vals, pairs)

    return {
        "event_id": event_id,
        "status": "ok",
        "n_entries": len(entries),
        "n_rows": len(rows),
        "n_pairs": len(pairs),
        "n_sig": int(n_sig),
        "elapsed": elapsed,
    }


# ── Fidelity check ────────────────────────────────────────────────────────────

def fidelity_check(conn: sqlite3.Connection, event_id: int, n_samples: int = 20):
    """
    Spot-check: compare our computed F_r(actual) against stored DB values.
    GOE: elements.panel_goe_points + elements.base_value = elements.panel_element_score
    PCS: pcs_components.panel_component_avg * factor
    """
    print(f"\n--- Fidelity check (event_id={event_id}) ---")

    # GOE spot-check
    goe_rows = conn.execute(
        """SELECT el.element_id, el.base_value, el.goe_factor_inferred,
                  el.panel_goe_points, el.panel_element_score, j.judge_position, ejs.judge_goe_int
           FROM element_judge_scores ejs
           JOIN judges j   ON ejs.judge_id  = j.judge_id
           JOIN elements el ON ejs.element_id = el.element_id
           JOIN entries e   ON el.entry_id   = e.entry_id
           WHERE e.event_id = ?
             AND j.event_id = ?
           ORDER BY el.element_id, j.judge_position""",
        (event_id, event_id)
    ).fetchall()

    # Group by element_id
    from collections import defaultdict
    elem_marks = defaultdict(dict)
    elem_meta  = {}
    for elem_id, bv, factor, panel_goe, panel_score, jpos, goe_int in goe_rows:
        elem_marks[elem_id][jpos] = float(goe_int)
        elem_meta[elem_id] = (float(bv or 0), float(factor or 1), float(panel_goe or 0), float(panel_score or 0))

    mismatches = 0
    checked = 0
    for elem_id, meta in list(elem_meta.items())[:n_samples]:
        bv, factor_inf, stored_goe, _panel_score = meta
        marks = elem_marks[elem_id]
        if len(marks) < 9:
            continue
        if stored_goe is None:
            continue
        marks9_raw = [marks.get(f"J{k+1}", 0.0) for k in range(9)]
        # Derive effective factor from stored panel_goe_points (corrects bad inferred values)
        marks9_sorted = sorted(marks9_raw)
        trimmed_mean = sum(marks9_sorted[1:8]) / 7.0
        eff_factor = (stored_goe / trimmed_mean) if abs(trimmed_mean) > 0.001 else factor_inf
        computed = score_goe_row(marks9_raw, bv, eff_factor)
        # Ground truth: base_value + panel_goe_points (rounded)
        stored_element_score = round_half_up(bv + stored_goe)
        checked += 1
        if abs(computed - stored_element_score) > 0.015:
            mismatches += 1
            print(f"  GOE MISMATCH elem {elem_id}: computed={computed:.2f} stored={stored_element_score:.2f} "
                  f"(bv={bv:.2f}+goe={stored_goe:.3f}, factor_inf={factor_inf:.4f} eff={eff_factor:.4f})")

    print(f"  GOE: checked {checked} elements, {mismatches} mismatches (>0.015)")

    # PCS spot-check
    pcs_rows = conn.execute(
        """SELECT pc.pcs_id, pc.component_name, pc.factor,
                  pc.panel_component_avg, j.judge_position, pjs.judge_mark
           FROM pcs_judge_scores pjs
           JOIN judges j          ON pjs.judge_id  = j.judge_id
           JOIN pcs_components pc ON pjs.pcs_id    = pc.pcs_id
           JOIN entries e         ON pc.entry_id   = e.entry_id
           WHERE e.event_id = ?
             AND j.event_id = ?
           ORDER BY pc.pcs_id, j.judge_position""",
        (event_id, event_id)
    ).fetchall()

    pcs_marks = defaultdict(dict)
    pcs_meta  = {}
    for pcs_id, comp, factor, panel_avg, jpos, mark in pcs_rows:
        pcs_marks[pcs_id][jpos] = float(mark)
        pcs_meta[pcs_id] = (float(factor or 1), float(panel_avg or 0))

    mismatches_pcs = 0
    checked_pcs = 0
    for pcs_id, (factor, stored_avg) in list(pcs_meta.items())[:n_samples]:
        marks = pcs_marks[pcs_id]
        if len(marks) < 9:
            continue
        marks9 = [marks.get(f"J{k+1}", 0.0) for k in range(9)]
        computed = score_pcs_row(marks9, factor)
        stored = round_half_up(stored_avg * factor)
        checked_pcs += 1
        if abs(computed - stored) > 0.015:
            mismatches_pcs += 1
            print(f"  PCS MISMATCH pcs {pcs_id}: computed={computed:.2f} stored={stored:.2f}")

    print(f"  PCS: checked {checked_pcs} components, {mismatches_pcs} mismatches (>0.015)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ISU-impact pairwise bias pipeline")
    parser.add_argument("--dry-run",       action="store_true",
                        help="Compute but do not write to DB")
    parser.add_argument("--event-id",      type=int, default=None,
                        help="Process only this event_id")
    parser.add_argument("--permutations",  type=int, default=DEFAULT_PERMS,
                        help=f"Permutations per event (default {DEFAULT_PERMS})")
    parser.add_argument("--seed",          type=int, default=DEFAULT_SEED,
                        help=f"RNG seed (default {DEFAULT_SEED})")
    parser.add_argument("--workers",       type=int, default=1,
                        help="Parallel workers (default 1 for now; parallelism TBD)")
    parser.add_argument("--cdf-scope",     choices=["global", "event"], default="global",
                        help="CDF scope: global (all history per judge) or event-only")
    parser.add_argument("--fidelity",      action="store_true",
                        help="Run fidelity check and exit (no permutations)")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    # Create tables if not present
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())

    # Fidelity check mode
    if args.fidelity:
        eid = args.event_id if args.event_id else 2
        fidelity_check(conn, eid)
        conn.close()
        return

    if args.dry_run:
        print(f"DRY RUN — {args.permutations} perms, seed {args.seed}, CDF={args.cdf_scope}", flush=True)
    else:
        # Backup before first write
        import shutil, os
        bak = DB_PATH + ".bak_isuimpact"
        if not os.path.exists(bak):
            print(f"Backing up DB → {os.path.basename(bak)}", flush=True)
            shutil.copy2(DB_PATH, bak)

    events = get_events(conn, args.event_id)
    print(f"Events to process: {len(events)}", flush=True)

    # Pre-build global CDFs once for full runs (avoids repeated DB queries per event)
    prebuilt = None
    if args.cdf_scope == "global" and len(events) > 1:
        prebuilt = build_all_cdfs(conn)

    total_t0 = time.perf_counter()
    summaries = []

    for i, eid in enumerate(events, 1):
        # Describe event
        row = conn.execute(
            "SELECT discipline, segment FROM events WHERE event_id=?", (eid,)
        ).fetchone()
        desc = f"{row[0]} / {row[1]}" if row else "?"
        print(f"\n[{i}/{len(events)}] event_id={eid}  {desc}  ({args.permutations} perms)", flush=True)

        # Warn on time if first event
        if i == 1 and len(events) > 1:
            t0 = time.perf_counter()

        try:
            summary = process_event(
                conn, eid, args.permutations, args.seed, args.cdf_scope, args.dry_run,
                prebuilt_all_cdfs=prebuilt
            )
        except Exception as exc:
            print(f"  ❌  Event {eid} failed: {exc!r} — skipping", flush=True)
            summaries.append({"event_id": eid, "status": f"error: {exc}", "elapsed": 0})
            continue
        summaries.append(summary)

        if summary["status"] == "ok":
            print(f"  ✓ {summary['n_entries']} competitors, {summary['n_rows']} rows, "
                  f"{summary['n_sig']} significant pairs  [{summary['elapsed']:.1f}s]", flush=True)

            # Time estimate after first event
            if i == 1 and len(events) > 1:
                elapsed_1 = time.perf_counter() - t0
                est_total = elapsed_1 * len(events)
                print(f"  Estimated total time: {est_total/60:.1f} min", flush=True)
        else:
            print(f"  — {summary['status']}", flush=True)

    total_elapsed = time.perf_counter() - total_t0
    ok_count = sum(1 for s in summaries if s["status"] == "ok")
    print(f"\nDone: {ok_count}/{len(events)} events processed in {total_elapsed:.1f}s", flush=True)

    if not args.dry_run:
        n_results = conn.execute("SELECT COUNT(*) FROM pairwise_impact_results WHERE method_version=?", (METHOD_VER,)).fetchone()[0]
        n_impacts = conn.execute("SELECT COUNT(*) FROM judge_team_impacts WHERE method_version=?", (METHOD_VER,)).fetchone()[0]
        print(f"DB rows: {n_results} pairwise_impact_results, {n_impacts} judge_team_impacts", flush=True)

    conn.close()


if __name__ == "__main__":
    main()
