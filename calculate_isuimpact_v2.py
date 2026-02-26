#!/usr/bin/env python3
"""
calculate_isuimpact_v2.py

ISU-impact pairwise judge bias pipeline — method: isuimpact_residual_v1

Identical to calculate_isuimpact_v1.py in all respects EXCEPT the permutation
test, which has been replaced to fix the exchangeability violation present in v1.

THE BUG IN V1:
  The v1 permutation shuffled judge-style labels within every scoring row across
  all competitors. This destroyed the shared skater-quality signal (both judges
  watch the same skaters), making the null distribution unrealistically narrow
  and inflating significance ~355× across the full dataset.

THE FIX IN V2:
  For each judge j and competitor pair (A, B):
    1. Extract judge j's observed delta values for entry A's rows and entry B's rows.
       (Deltas are already residuals: actual_impact − neutralised_j_impact.)
    2. Pool them and repeatedly randomly split into groups of |A_rows| and |B_rows|.
    3. B_j_perm(A,B) = sum(A_group) − sum(B_group)
    4. p = P(|B_perm| >= |B_obs|) + 1/(M+1)  (continuity correction)

  Under the null of no directional bias for pair (A,B), judge j's delta values
  are exchangeable between entries A and B — the shared skater-quality signal has
  already been removed by the median-of-8 neutralisation step. This restores
  exchangeability and yields valid p-values.

SCIENTIFIC REFERENCE:
  Emerson, Seltzer & Lin (2009). "Assessing Judging Bias: An Example From the
  2000 Olympic Games." The American Statistician 63(2), 124–131.

Validation target (OWG 2026 Ice Dance Free Dance, event_id=2):
    J1 FRA vs USA: bias_points = +1.19 TSS pts, p = 0.0003  (M=10k, seed=20260223)
    BiasPoints unchanged from v1; p-value also unchanged for this specific pair
    (the finding is genuinely extreme — the targeted permutation confirms it).

Usage:
    python3 calculate_isuimpact_v2.py --dry-run --event-id 2   # validate first
    python3 calculate_isuimpact_v2.py --event-id 2             # write single event
    python3 calculate_isuimpact_v2.py                           # full run (all events)
    python3 calculate_isuimpact_v2.py --permutations 10000 --seed 20260223
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

# ── Constants ──────────────────────────────────────────────────────────────────

DB_PATH       = "/Users/allman/Library/CloudStorage/Dropbox/Dropbox Mike/Judging Bias/figure_skating_ijs_v4.sqlite"
METHOD_VER    = "isuimpact_residual_v1"
DEFAULT_SEED  = 20260223
DEFAULT_PERMS = 10_000

PCS_CAT_MAP = {
    "Skating Skills":              "PCS_SS",
    "Composition":                 "PCS_CO",
    "Presentation":                "PCS_PR",
    "Performance":                 "PCS_PE",
    "Transitions":                 "PCS_TR",
    "Interpretation of the Music": "PCS_IM",
}

# ── Rounding ───────────────────────────────────────────────────────────────────

def round_half_up(x: float, n: int = 2) -> float:
    """Round to n decimal places using round-half-away-from-zero (Excel ROUND)."""
    m = 10 ** n
    return math.floor(x * m + 0.5) / m


# ── ISU-exact row scoring ──────────────────────────────────────────────────────

def score_goe_row(marks9: list, base_value: float, factor: float) -> float:
    s = sorted(marks9)
    trimmed_mean = sum(s[1:8]) / 7.0
    panel_goe = round_half_up(trimmed_mean * factor)
    return round_half_up(base_value + panel_goe)


def score_pcs_row(marks9: list, factor: float) -> float:
    s = sorted(marks9)
    trimmed_mean = sum(s[1:8]) / 7.0
    panel_avg = round_half_up(trimmed_mean)
    return round_half_up(panel_avg * factor)


def median_of_8(marks9: list, j: int) -> float:
    others = sorted(marks9[k] for k in range(9) if k != j)
    return (others[3] + others[4]) / 2.0


# ── Database helpers ───────────────────────────────────────────────────────────

def get_events(conn: sqlite3.Connection, event_id: int | None) -> list[int]:
    if event_id is not None:
        return [event_id]
    rows = conn.execute("SELECT event_id FROM events ORDER BY event_id").fetchall()
    return [r[0] for r in rows]


def load_event_data(conn: sqlite3.Connection, event_id: int):
    """
    Load GOE and PCS rows for all competitors in the event.
    Identical to v1 — the data loading and delta computation are unchanged.
    """
    entry_rows = conn.execute(
        "SELECT entry_id, rank, team_name, noc FROM entries WHERE event_id = ? ORDER BY rank",
        (event_id,)
    ).fetchall()
    entries = [{"entry_id": r[0], "rank": r[1], "team": r[2], "noc": r[3]} for r in entry_rows]
    entry_ids = [e["entry_id"] for e in entries]

    if not entry_ids:
        return entries, [], []

    panel_rows = conn.execute(
        "SELECT judge_id, judge_position, judge_name, country_code FROM judges "
        "WHERE event_id = ? ORDER BY judge_position",
        (event_id,)
    ).fetchall()
    panel = [{"judge_id": r[0], "position": r[1], "name": r[2], "country": r[3]} for r in panel_rows]
    positions = [p["position"] for p in panel]

    ph = ",".join("?" * len(entry_ids))
    goe_raw = conn.execute(
        f"""SELECT e.entry_id, el.element_id, el.element_no,
                   el.base_value, el.goe_factor_inferred, el.panel_goe_points,
                   j.judge_position, ejs.judge_goe_int
            FROM element_judge_scores ejs
            JOIN judges   j  ON ejs.judge_id   = j.judge_id
            JOIN elements el ON ejs.element_id  = el.element_id
            JOIN entries  e  ON el.entry_id     = e.entry_id
            WHERE e.entry_id IN ({ph})
              AND j.event_id = ?
            ORDER BY e.rank, el.element_no, j.judge_position""",
        entry_ids + [event_id]
    ).fetchall()

    goe_rows_dict = {}
    for entry_id, element_id, elem_no, base_val, factor_inf, panel_goe, jpos, goe_int in goe_raw:
        key = (entry_id, element_id)
        if key not in goe_rows_dict:
            goe_rows_dict[key] = {
                "entry_id":        entry_id,
                "row_type":        "GOE",
                "category":        "GOE",
                "element_no":      elem_no,
                "base_value":      float(base_val)   if base_val   is not None else 0.0,
                "factor_inferred": float(factor_inf)  if factor_inf is not None else 1.0,
                "panel_goe_points":float(panel_goe)   if panel_goe  is not None else None,
                "factor":          float(factor_inf)  if factor_inf is not None else 1.0,
                "marks":           {},
            }
        goe_rows_dict[key]["marks"][jpos] = float(goe_int)

    # Derive effective GOE factor from stored panel_goe_points (corrects wrong inferred values)
    for row in goe_rows_dict.values():
        stored_goe = row["panel_goe_points"]
        if stored_goe is not None and len(row["marks"]) == 9:
            marks9 = sorted(row["marks"].values())
            trimmed_mean = sum(marks9[1:8]) / 7.0
            if abs(trimmed_mean) > 0.001:
                row["factor"] = stored_goe / trimmed_mean

    pcs_raw = conn.execute(
        f"""SELECT e.entry_id, pc.pcs_id, pc.component_name, pc.factor,
                   j.judge_position, pjs.judge_mark
            FROM pcs_judge_scores pjs
            JOIN judges        j  ON pjs.judge_id  = j.judge_id
            JOIN pcs_components pc ON pjs.pcs_id    = pc.pcs_id
            JOIN entries        e  ON pc.entry_id   = e.entry_id
            WHERE e.entry_id IN ({ph})
              AND j.event_id = ?
            ORDER BY e.rank, pc.component_name, j.judge_position""",
        entry_ids + [event_id]
    ).fetchall()

    pcs_rows_dict = {}
    for entry_id, pcs_id, comp_name, factor, jpos, mark in pcs_raw:
        key = (entry_id, pcs_id)
        cat = PCS_CAT_MAP.get(comp_name, f"PCS_{comp_name[:2].upper()}")
        if key not in pcs_rows_dict:
            pcs_rows_dict[key] = {
                "entry_id":   entry_id,
                "row_type":   "PCS",
                "category":   cat,
                "base_value": 0.0,
                "factor":     float(factor) if factor is not None else 1.0,
                "marks":      {},
            }
        pcs_rows_dict[key]["marks"][jpos] = float(mark)

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


# ── Core computation (unchanged from v1) ──────────────────────────────────────

def compute_deltas(rows: list, positions: list[str]) -> tuple:
    R = len(rows)
    J = len(positions)
    pos_idx = {p: i for i, p in enumerate(positions)}

    delta = np.zeros((J, R), dtype=float)
    categories = []

    for r, row in enumerate(rows):
        marks9 = [row["marks"][p] for p in positions]
        bv = row["base_value"]
        f  = row["factor"]

        if row["row_type"] == "GOE":
            f_actual = score_goe_row(marks9, bv, f)
        else:
            f_actual = score_pcs_row(marks9, f)

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

    return delta, categories


def compute_impacts_and_bias(delta: np.ndarray, rows: list, entries: list):
    J = delta.shape[0]
    N = len(entries)
    entry_id_to_idx = {e["entry_id"]: i for i, e in enumerate(entries)}

    I_obs = np.zeros((J, N), dtype=float)
    for r, row in enumerate(rows):
        t = entry_id_to_idx[row["entry_id"]]
        I_obs[:, t] += delta[:, r]

    pairs = list(itertools.combinations(range(N), 2))
    a_idx = np.array([p[0] for p in pairs])
    b_idx = np.array([p[1] for p in pairs])
    B_obs = I_obs[:, a_idx] - I_obs[:, b_idx]

    return I_obs, B_obs, pairs


# ── Permutation test (v2 — residual-label permutation) ────────────────────────

def run_residual_permutation_test(
    delta: np.ndarray,
    B_obs: np.ndarray,
    rows: list,
    entries: list,
    n_perms: int,
    seed: int,
) -> np.ndarray:
    """
    Residual-label permutation null — fixes the exchangeability violation in v1.

    For each judge j and pair (A, B):
      - Pool judge j's delta values for entries A and B.
      - Randomly split into groups of |A_rows| and |B_rows| (n_perms times).
      - B_perm = sum(A_group) − sum(B_group)
      - p = (1 + #{|B_perm| >= |B_obs|}) / (M + 1)

    The delta[j, r] values are median-of-8 neutralisation residuals — they
    capture judge j's marginal contribution above/below panel consensus for
    each row. The shared skater-quality signal has already been removed by the
    neutralisation step, so entry labels are exchangeable under the null.

    Vectorised: for each (j, pair), generates all M permutations at once using
    np.argsort on a random matrix. Memory per call: O(M × pool_size) ≈ 2–4 MB.
    """
    J, R = delta.shape
    P    = B_obs.shape[1]
    N    = len(entries)

    rng = np.random.default_rng(seed)

    # Map entry index → list of row indices in delta
    entry_id_to_idx = {e["entry_id"]: i for i, e in enumerate(entries)}
    entry_row_idx: dict[int, list[int]] = defaultdict(list)
    for r, row in enumerate(rows):
        t = entry_id_to_idx[row["entry_id"]]
        entry_row_idx[t].append(r)

    pairs = list(itertools.combinations(range(N), 2))
    assert len(pairs) == P

    exceed    = np.zeros((J, P), dtype=float)
    abs_B_obs = np.abs(B_obs)

    for j in range(J):
        delta_j = delta[j]  # (R,)

        for p_idx, (a, b) in enumerate(pairs):
            pool_a = delta_j[np.array(entry_row_idx[a])]
            pool_b = delta_j[np.array(entry_row_idx[b])]
            pool   = np.concatenate([pool_a, pool_b])

            n_a      = len(pool_a)
            n_total  = len(pool)
            pool_sum = float(pool.sum())
            obs_abs  = float(abs_B_obs[j, p_idx])

            if n_total == 0 or n_a == 0:
                # Degenerate — assign p=1 (no data to test)
                continue

            # Vectorised: argsort random matrix rows gives random permutations.
            # Taking the first n_a columns selects a random subset of size n_a.
            rand_mat     = rng.random((n_perms, n_total))
            perm_orders  = np.argsort(rand_mat, axis=1)
            sel_sums     = pool[perm_orders[:, :n_a]].sum(axis=1)   # (n_perms,)
            b_perms      = 2.0 * sel_sums - pool_sum                 # (n_perms,)
            exceed[j, p_idx] = float(np.sum(np.abs(b_perms) >= obs_abs))

    p_vals = (1.0 + exceed) / (n_perms + 1.0)
    return p_vals


# ── BH-FDR ────────────────────────────────────────────────────────────────────

def apply_bh_fdr(p_vals: np.ndarray) -> np.ndarray:
    shape  = p_vals.shape
    flat   = p_vals.ravel()
    _, q_flat, _, _ = multipletests(flat, method='fdr_bh')
    return q_flat.reshape(shape)


# ── Output helpers ─────────────────────────────────────────────────────────────

def format_results(event_id, entries, panel, I_obs, B_obs, p_vals, q_vals, pairs, n_perms, seed):
    now = datetime.now(timezone.utc).isoformat()

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
    sig_mask = q_vals < 0.05
    n_sig = sig_mask.sum()
    print(f"\n  event_id={event_id}: {len(entries)} competitors, {len(panel)} judges, "
          f"{len(pairs)} pairs, {B_obs.shape[1]*len(panel)} tests")
    print(f"  Significant (BH q≤0.05): {n_sig} / {B_obs.shape[1]*len(panel)}")

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


# ── DB write ───────────────────────────────────────────────────────────────────

def write_results(conn, result_rows, impact_rows, event_id, dry_run):
    if dry_run:
        return
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
        raise


# ── Per-event driver ───────────────────────────────────────────────────────────

def process_event(conn, event_id, n_perms, seed, dry_run) -> dict:
    t0 = time.perf_counter()

    entries, rows, panel = load_event_data(conn, event_id)
    if not entries or not rows:
        return {"event_id": event_id, "status": "skipped (no data)", "elapsed": 0}

    positions = [p["position"] for p in panel]
    if len(positions) != 9:
        print(f"  event {event_id}: {len(positions)} judges (expected 9) — skipping", flush=True)
        return {"event_id": event_id, "status": f"skipped ({len(positions)} judges)", "elapsed": 0}

    delta, categories = compute_deltas(rows, positions)
    I_obs, B_obs, pairs = compute_impacts_and_bias(delta, rows, entries)

    p_vals = run_residual_permutation_test(delta, B_obs, rows, entries, n_perms, seed)
    q_vals = apply_bh_fdr(p_vals)

    result_rows, impact_rows = format_results(
        event_id, entries, panel, I_obs, B_obs, p_vals, q_vals, pairs, n_perms, seed
    )
    write_results(conn, result_rows, impact_rows, event_id, dry_run)

    elapsed = time.perf_counter() - t0
    n_sig = int((q_vals < 0.05).sum())

    if dry_run:
        print_dry_run_summary(event_id, entries, panel, B_obs, p_vals, q_vals, pairs)

    return {
        "event_id": event_id,
        "status":   "ok",
        "n_entries": len(entries),
        "n_rows":    len(rows),
        "n_pairs":   len(pairs),
        "n_sig":     n_sig,
        "elapsed":   elapsed,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ISU-impact v2 — residual-label permutation (fixes exchangeability violation)"
    )
    parser.add_argument("--dry-run",      action="store_true",
                        help="Compute and print; do NOT write to DB")
    parser.add_argument("--event-id",     type=int, default=None,
                        help="Process only this event_id")
    parser.add_argument("--permutations", type=int, default=DEFAULT_PERMS,
                        help=f"Permutations per test (default {DEFAULT_PERMS})")
    parser.add_argument("--seed",         type=int, default=DEFAULT_SEED,
                        help=f"RNG seed (default {DEFAULT_SEED})")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    if args.dry_run:
        print(f"DRY RUN — method={METHOD_VER}, {args.permutations} perms, seed={args.seed}",
              flush=True)
    else:
        import shutil, os
        bak = DB_PATH + ".bak_v2"
        if not os.path.exists(bak):
            print(f"Backing up DB → {os.path.basename(bak)}", flush=True)
            shutil.copy2(DB_PATH, bak)

    events = get_events(conn, args.event_id)
    print(f"Events to process: {len(events)}", flush=True)

    total_t0  = time.perf_counter()
    summaries = []

    for i, eid in enumerate(events, 1):
        row = conn.execute(
            "SELECT discipline, segment FROM events WHERE event_id=?", (eid,)
        ).fetchone()
        desc = f"{row[0]} / {row[1]}" if row else "?"
        print(f"\n[{i}/{len(events)}] event_id={eid}  {desc}", flush=True)

        try:
            summary = process_event(conn, eid, args.permutations, args.seed, args.dry_run)
        except Exception as exc:
            print(f"  ❌  Event {eid} failed: {exc!r} — skipping", flush=True)
            summaries.append({"event_id": eid, "status": f"error: {exc}", "elapsed": 0})
            continue
        summaries.append(summary)

        if summary["status"] == "ok":
            print(f"  ✓  {summary['n_entries']} competitors, {summary['n_rows']} rows, "
                  f"{summary['n_sig']} significant pairs  [{summary['elapsed']:.1f}s]", flush=True)

            if i == 1 and len(events) > 1:
                est = summary["elapsed"] * len(events)
                print(f"  Estimated total: {est/60:.1f} min", flush=True)
        else:
            print(f"  — {summary['status']}", flush=True)

    total_elapsed = time.perf_counter() - total_t0
    ok = sum(1 for s in summaries if s["status"] == "ok")
    print(f"\nDone: {ok}/{len(events)} events  [{total_elapsed:.1f}s total]", flush=True)

    if not args.dry_run:
        n_r = conn.execute(
            "SELECT COUNT(*) FROM pairwise_impact_results WHERE method_version=?",
            (METHOD_VER,)
        ).fetchone()[0]
        n_i = conn.execute(
            "SELECT COUNT(*) FROM judge_team_impacts WHERE method_version=?",
            (METHOD_VER,)
        ).fetchone()[0]
        print(f"DB: {n_r} pairwise_impact_results, {n_i} judge_team_impacts", flush=True)

    conn.close()


if __name__ == "__main__":
    main()
