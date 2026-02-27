#!/usr/bin/env python3
"""calculate_lojo_full.py
Comprehensive Leave-One-Judge-Out (LOJO) analysis.
Creates lojo_scores, lojo_event_summary, integrity_checks tables.

Usage:
    python3 calculate_lojo_full.py            # full run (creates DB backup first)
    python3 calculate_lojo_full.py --dry-run  # print what would be done, no writes
"""
import argparse
import shutil
import sqlite3
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

DB_PATH = str(Path(__file__).parent / "figure_skating_ijs_v4.sqlite")


def parse_args():
    p = argparse.ArgumentParser(description="LOJO counterfactual pipeline")
    p.add_argument("--dry-run", action="store_true",
                   help="Print what would be done without writing to the database")
    return p.parse_args()


def trimmed_mean(scores, drop=1):
    if not scores: return 0.0
    s = sorted(scores)
    if len(s) <= 2 * drop: return sum(s) / len(s)
    return sum(s[drop:-drop]) / len(s[drop:-drop])


def get_events(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT e.event_id, c.name, e.discipline, e.segment
        FROM events e
        JOIN competitions c ON e.competition_id = c.competition_id
        JOIN entries en ON en.event_id = e.event_id
        JOIN elements el ON el.entry_id = en.entry_id
        JOIN element_judge_scores ejs ON ejs.element_id = el.element_id
        ORDER BY c.name, e.discipline, e.segment
    """)
    return cur.fetchall()


def get_judge_positions(conn, event_id):
    cur = conn.cursor()
    cur.execute("SELECT judge_id, judge_position, judge_name, country_code FROM judges WHERE event_id=? ORDER BY judge_position", (event_id,))
    return cur.fetchall()


def get_entries(conn, event_id):
    cur = conn.cursor()
    cur.execute("SELECT entry_id, team_name, noc, rank, tes, pcs, deductions, tss FROM entries WHERE event_id=? ORDER BY rank", (event_id,))
    return cur.fetchall()


def get_element_judge_scores(conn, entry_id):
    cur = conn.cursor()
    cur.execute("""SELECT el.element_id, ejs.judge_id, ejs.judge_goe_int
        FROM elements el JOIN element_judge_scores ejs ON ejs.element_id = el.element_id
        WHERE el.entry_id=?""", (entry_id,))
    result = {}
    for eid, jid, goe in cur.fetchall():
        result.setdefault(eid, {})[jid] = float(goe)
    return result


def get_element_base_values(conn, entry_id):
    cur = conn.cursor()
    cur.execute("SELECT element_id, base_value FROM elements WHERE entry_id=?", (entry_id,))
    return {r[0]: r[1] for r in cur.fetchall()}


def get_pcs_judge_scores(conn, entry_id):
    cur = conn.cursor()
    cur.execute("""SELECT pc.pcs_id, pjs.judge_id, pjs.judge_mark, pc.factor
        FROM pcs_components pc JOIN pcs_judge_scores pjs ON pjs.pcs_id = pc.pcs_id
        WHERE pc.entry_id=?""", (entry_id,))
    result = {}
    for pid, jid, mark, factor in cur.fetchall():
        if pid not in result: result[pid] = {"factor": factor, "judges": {}}
        result[pid]["judges"][jid] = float(mark)
    return result


def has_valid_pcs_judge_marks(conn, entry_id):
    """Returns True if PCS judge marks for this entry are valid (no zero marks)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*), SUM(CASE WHEN pjs.judge_mark = 0.0 THEN 1 ELSE 0 END)
        FROM pcs_components pc
        JOIN pcs_judge_scores pjs ON pjs.pcs_id = pc.pcs_id
        WHERE pc.entry_id = ?
    """, (entry_id,))
    row = cur.fetchone()
    total, zeros = row[0] or 0, row[1] or 0
    return total > 0 and zeros == 0


def compute_counterfactual_tss(conn, entry_id, exclude_judge_id, deductions,
                                stored_pcs=None, pcs_is_valid=True):
    """Compute counterfactual TSS with one judge removed.

    If pcs_is_valid=False (singles/pairs with corrupted PCS judge marks),
    we use stored_pcs from entries table instead of recomputing from judge marks.
    In that case cf_tss reflects only the TES counterfactual — PCS held constant.
    """
    elem_scores = get_element_judge_scores(conn, entry_id)
    base_values = get_element_base_values(conn, entry_id)
    if not elem_scores:
        print(f"  ⚠️  cf_tss=None: entry {entry_id}, judge {exclude_judge_id} — no element scores")
        return None
    tes = 0.0
    for eid, judge_goes in elem_scores.items():
        base = base_values.get(eid, 0.0)
        remaining = [g for j, g in judge_goes.items() if j != exclude_judge_id]
        if not remaining:
            print(f"  ⚠️  cf_tss=None: entry {entry_id}, judge {exclude_judge_id} — "
                  f"judge was sole scorer for element {eid}")
            return None
        tes += base + trimmed_mean(remaining)

    if pcs_is_valid:
        pcs_data = get_pcs_judge_scores(conn, entry_id)
        pcs_total = 0.0
        for pid, data in pcs_data.items():
            remaining = [m for j, m in data["judges"].items() if j != exclude_judge_id]
            if not remaining:
                print(f"  ⚠️  cf_tss=None: entry {entry_id}, judge {exclude_judge_id} — "
                      f"judge was sole PCS scorer for component {pid}")
                return None
            pcs_total += trimmed_mean(remaining) * data["factor"]
    else:
        # Use stored PCS total from entries table (unchanged across judge removals)
        pcs_total = stored_pcs if stored_pcs is not None else 0.0

    # Handle both positive and negative deduction sign conventions
    ded_abs = abs(deductions) if deductions else 0.0
    return round(tes + pcs_total - ded_abs, 2)


DDL_TABLES = [
    """CREATE TABLE IF NOT EXISTS lojo_scores (
        lojo_id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        judge_id INTEGER NOT NULL,
        judge_position TEXT,
        entry_id INTEGER NOT NULL,
        cf_tss REAL,
        cf_rank INTEGER,
        official_rank INTEGER,
        rank_change INTEGER,
        UNIQUE(event_id, judge_id, entry_id)
    )""",
    """CREATE TABLE IF NOT EXISTS lojo_event_summary (
        summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        judge_id INTEGER NOT NULL,
        judge_position TEXT,
        judge_name TEXT,
        n_entries INTEGER,
        winner_changes INTEGER,
        podium_changes INTEGER,
        n_rank_inversions INTEGER,
        total_pairs INTEGER,
        kendall_tau_distance REAL,
        actual_winner_name TEXT,
        cf_winner_name TEXT,
        actual_margin REAL,
        cf_margin REAL,
        pcs_mode TEXT DEFAULT 'recomputed',
        UNIQUE(event_id, judge_id)
    )""",
    """CREATE TABLE IF NOT EXISTS integrity_checks (
        check_id INTEGER PRIMARY KEY AUTOINCREMENT,
        check_name TEXT,
        total_checked INTEGER,
        passed INTEGER,
        failed INTEGER,
        pass_rate REAL,
        notes TEXT,
        run_at TEXT
    )"""
]


def create_tables(conn):
    """Create LOJO tables if they don't already exist.

    Uses CREATE TABLE IF NOT EXISTS — no DROP TABLE.
    Idempotency is handled by UNIQUE constraints + INSERT OR REPLACE in run_lojo_for_event().
    """
    cur = conn.cursor()
    for ddl in DDL_TABLES:
        cur.execute(ddl)
    conn.commit()
    print("Tables created / verified.")


def count_rank_inversions(official_ranks, cf_ranks):
    entry_ids = list(official_ranks.keys())
    total_pairs = len(entry_ids) * (len(entry_ids) - 1) // 2
    n_inv = 0
    for a, b in combinations(entry_ids, 2):
        off_a, off_b = official_ranks[a], official_ranks[b]
        cf_a, cf_b = cf_ranks[a], cf_ranks[b]
        if (off_a < off_b and cf_a > cf_b) or (off_a > off_b and cf_a < cf_b):
            n_inv += 1
    return n_inv, total_pairs


def run_lojo_for_event(conn, event_id, cur_write, dry_run=False):
    judges = get_judge_positions(conn, event_id)
    entries = get_entries(conn, event_id)
    if len(entries) < 2 or len(judges) < 7:
        return []

    # Only include judges who have at least one GOE score in this event
    # (some events have panel-roster judges who did not score elements)
    cur_filter = conn.cursor()
    cur_filter.execute("""
        SELECT DISTINCT ejs.judge_id
        FROM element_judge_scores ejs
        JOIN elements el ON ejs.element_id = el.element_id
        JOIN entries en ON el.entry_id = en.entry_id
        WHERE en.event_id = ?
    """, (event_id,))
    judges_with_goe = {row[0] for row in cur_filter.fetchall()}
    judges = [j for j in judges if j[0] in judges_with_goe]
    if len(judges) < 7:
        return []

    official_ranks = {}
    for e in entries:
        if e[3] is not None:
            official_ranks[e[0]] = e[3]
    if len(official_ranks) < 2:
        return []

    sorted_off = sorted(official_ranks.items(), key=lambda x: x[1])
    actual_winner_id = sorted_off[0][0]
    actual_podium_ids = {eid for eid, r in sorted_off if r <= 3}
    actual_podium_ordered = tuple(eid for eid, r in sorted_off if r <= 3)  # order-sensitive top-3
    actual_winner_name = next(e[1] for e in entries if e[0] == actual_winner_id)

    official_tss = {e[0]: e[7] for e in entries if e[7] is not None}
    off_sorted_tss = sorted(official_tss.items(), key=lambda x: x[1], reverse=True)
    actual_margin = round(off_sorted_tss[0][1] - off_sorted_tss[1][1], 2) if len(off_sorted_tss) >= 2 else None

    deductions_map = {e[0]: e[6] if e[6] is not None else 0.0 for e in entries}
    stored_pcs_map = {e[0]: e[5] if e[5] is not None else 0.0 for e in entries}
    entry_names = {e[0]: e[1] for e in entries}

    # Check PCS validity once per entry (not per judge)
    pcs_valid_map = {}
    for e in entries:
        pcs_valid_map[e[0]] = has_valid_pcs_judge_marks(conn, e[0])
    any_pcs_valid = any(pcs_valid_map.values())

    summaries = []

    for judge_id, judge_pos, judge_name, judge_country in judges:
        cf_tss_map = {}
        for e in entries:
            eid = e[0]
            pcs_valid = pcs_valid_map[eid]
            cf = compute_counterfactual_tss(
                conn, eid, judge_id, deductions_map[eid],
                stored_pcs=stored_pcs_map[eid],
                pcs_is_valid=pcs_valid
            )
            if cf is not None:
                cf_tss_map[eid] = cf
        if len(cf_tss_map) < 2:
            continue

        cf_sorted = sorted(cf_tss_map.items(), key=lambda x: x[1], reverse=True)
        cf_ranks = {eid: rank + 1 for rank, (eid, _) in enumerate(cf_sorted)}
        cf_winner_id = cf_sorted[0][0]
        cf_podium_ids = {eid for eid, r in cf_ranks.items() if r <= 3}
        cf_podium_ordered = tuple(cf_sorted[i][0] for i in range(min(3, len(cf_sorted))))  # order-sensitive
        cf_winner_name = entry_names.get(cf_winner_id, "?")

        winner_changes = int(cf_winner_id != actual_winner_id)
        podium_changes = int(cf_podium_ordered != actual_podium_ordered)  # position-sensitive: reordering counts

        common = set(official_ranks.keys()) & set(cf_ranks.keys())
        off_c = {e: official_ranks[e] for e in common}
        cf_c = {e: cf_ranks[e] for e in common}
        n_inv, total_pairs = count_rank_inversions(off_c, cf_c)
        kendall_tau = n_inv / total_pairs if total_pairs > 0 else 0.0

        cf_margin = round(cf_sorted[0][1] - cf_sorted[1][1], 2) if len(cf_sorted) >= 2 else None

        pcs_mode = "recomputed" if any_pcs_valid else "stored"

        if not dry_run:
            for eid, cf_tss_val in cf_tss_map.items():
                off_r = official_ranks.get(eid)
                cf_r = cf_ranks.get(eid)
                rc = (cf_r - off_r) if (cf_r is not None and off_r is not None) else None
                cur_write.execute(
                    "INSERT OR REPLACE INTO lojo_scores (event_id, judge_id, judge_position, entry_id, cf_tss, cf_rank, official_rank, rank_change) VALUES (?,?,?,?,?,?,?,?)",
                    (event_id, judge_id, judge_pos, eid, cf_tss_val, cf_r, off_r, rc)
                )

            cur_write.execute(
                """INSERT OR REPLACE INTO lojo_event_summary
                    (event_id, judge_id, judge_position, judge_name, n_entries, winner_changes, podium_changes,
                     n_rank_inversions, total_pairs, kendall_tau_distance, actual_winner_name, cf_winner_name,
                     actual_margin, cf_margin, pcs_mode)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (event_id, judge_id, judge_pos, judge_name or "",
                 len(cf_tss_map), winner_changes, podium_changes,
                 n_inv, total_pairs, kendall_tau,
                 actual_winner_name, cf_winner_name, actual_margin, cf_margin, pcs_mode)
            )

        summaries.append({
            "event_id": event_id, "judge_id": judge_id,
            "judge_position": judge_pos, "judge_name": judge_name or "",
            "winner_changes": winner_changes, "podium_changes": podium_changes,
            "n_rank_inversions": n_inv, "total_pairs": total_pairs,
            "kendall_tau_distance": kendall_tau,
            "actual_winner_name": actual_winner_name, "cf_winner_name": cf_winner_name,
            "actual_margin": actual_margin, "cf_margin": cf_margin,
            "n_entries": len(cf_tss_map),
            "pcs_mode": pcs_mode,
        })

    return summaries


def run_integrity_checks(conn):
    cur = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    results = []

    # Check 1: TES Reconstruction
    cur.execute("""
        SELECT COUNT(*),
               SUM(CASE WHEN ABS(en.tes - el_sum.calc_tes) <= 0.05 THEN 1 ELSE 0 END)
        FROM entries en
        JOIN (SELECT entry_id, SUM(panel_element_score) as calc_tes
              FROM elements WHERE panel_element_score IS NOT NULL GROUP BY entry_id) el_sum
        ON en.entry_id = el_sum.entry_id
        WHERE en.tes IS NOT NULL
    """)
    row = cur.fetchone()
    total, passed = (row[0] or 0), (row[1] or 0)
    results.append({"check_name": "TES Reconstruction (element scores sum to stored TES)",
        "total_checked": total, "passed": passed, "failed": total-passed,
        "pass_rate": passed/total if total else 0.0,
        "notes": "SUM(panel_element_score) vs entries.tes within 0.05", "run_at": now_str})

    # Check 2: TSS = TES + PCS + deductions
    # Deductions are stored as either negative or positive; try both signs
    cur.execute("""
        SELECT COUNT(*),
               SUM(CASE WHEN ABS((en.tes + en.pcs + en.deductions) - en.tss) <= 0.05
                          OR ABS((en.tes + en.pcs - en.deductions) - en.tss) <= 0.05
                        THEN 1 ELSE 0 END)
        FROM entries en WHERE en.tes IS NOT NULL AND en.pcs IS NOT NULL AND en.tss IS NOT NULL
    """)
    row = cur.fetchone()
    total, passed = (row[0] or 0), (row[1] or 0)
    results.append({"check_name": "TSS = TES + PCS + Deductions (either sign)",
        "total_checked": total, "passed": passed, "failed": total-passed,
        "pass_rate": passed/total if total else 0.0,
        "notes": "ABS(tes+pcs+deductions-tss)<=0.05 OR ABS(tes+pcs-deductions-tss)<=0.05", "run_at": now_str})

    # Check 3: PCS trimmed mean (9-judge, exclude integer averages which are parser artifacts)
    # 6,918 components have integer stored averages (1.0-10.0) from singles/pairs parser — exclude them
    cur.execute("""
        SELECT COUNT(*),
               SUM(CASE WHEN ABS(pc.panel_component_avg - calc.avg_mark) <= 0.02 THEN 1 ELSE 0 END)
        FROM pcs_components pc
        JOIN (SELECT pcs_id,
                     (SUM(judge_mark) - MAX(judge_mark) - MIN(judge_mark)) / (COUNT(*) - 2.0) AS avg_mark
              FROM pcs_judge_scores GROUP BY pcs_id HAVING COUNT(*) = 9) calc
        ON pc.pcs_id = calc.pcs_id
        WHERE pc.panel_component_avg IS NOT NULL
          AND pc.panel_component_avg NOT IN (0.0,1.0,2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0)
    """)
    row = cur.fetchone()
    total, passed = (row[0] or 0), (row[1] or 0)
    results.append({"check_name": "PCS Trimmed Mean (9-judge, non-integer avg components)",
        "total_checked": total, "passed": passed, "failed": total-passed,
        "pass_rate": passed/total if total else 0.0,
        "notes": "(sum-max-min)/7 vs panel_component_avg within 0.02; excludes integer averages (parser artifact)", "run_at": now_str})

    # Check 4: GOE coverage
    cur.execute("""
        SELECT COUNT(DISTINCT el.element_id),
               SUM(CASE WHEN cnt.n = 9 THEN 1 ELSE 0 END)
        FROM elements el
        LEFT JOIN (SELECT element_id, COUNT(*) as n FROM element_judge_scores GROUP BY element_id) cnt
        ON el.element_id = cnt.element_id
    """)
    row = cur.fetchone()
    total, passed = (row[0] or 0), (row[1] or 0)
    results.append({"check_name": "GOE Coverage (elements with full 9-judge scores)",
        "total_checked": total, "passed": passed, "failed": total-passed,
        "pass_rate": passed/total if total else 0.0,
        "notes": "Elements with exactly 9 GOE judge scores", "run_at": now_str})

    # Check 5: PCS coverage
    cur.execute("""
        SELECT COUNT(DISTINCT pc.pcs_id),
               SUM(CASE WHEN cnt.n = 9 THEN 1 ELSE 0 END)
        FROM pcs_components pc
        LEFT JOIN (SELECT pcs_id, COUNT(*) as n FROM pcs_judge_scores GROUP BY pcs_id) cnt
        ON pc.pcs_id = cnt.pcs_id
    """)
    row = cur.fetchone()
    total, passed = (row[0] or 0), (row[1] or 0)
    results.append({"check_name": "PCS Coverage (components with full 9 judge marks)",
        "total_checked": total, "passed": passed, "failed": total-passed,
        "pass_rate": passed/total if total else 0.0,
        "notes": "PCS components with exactly 9 judge marks", "run_at": now_str})

    cur2 = conn.cursor()
    for r in results:
        cur2.execute(
            "INSERT INTO integrity_checks (check_name, total_checked, passed, failed, pass_rate, notes, run_at) VALUES (?,?,?,?,?,?,?)",
            (r["check_name"], r["total_checked"], r["passed"], r["failed"], r["pass_rate"], r["notes"], r["run_at"])
        )
    conn.commit()
    return results


def run_three_regime_comparison(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT les.event_id, c.name, e.discipline, e.segment,
               les.judge_position, les.judge_name,
               MIN(pjs.p_value), les.kendall_tau_distance,
               les.actual_winner_name, les.cf_winner_name
        FROM lojo_event_summary les
        JOIN events e ON les.event_id = e.event_id
        JOIN competitions c ON e.competition_id = c.competition_id
        JOIN pairwise_judge_statistics pjs
            ON pjs.event_id = les.event_id AND pjs.judge_id = les.judge_id AND pjs.is_significant_001 = 1
        WHERE les.winner_changes = 1
        GROUP BY les.event_id, les.judge_id
        ORDER BY les.kendall_tau_distance DESC
    """)
    return [
        {"event_id": r[0], "competition": r[1], "discipline": r[2], "segment": r[3],
         "judge_position": r[4], "judge_name": r[5], "p_value": r[6],
         "kendall_tau": r[7], "actual_winner": r[8], "cf_winner": r[9]}
        for r in cur.fetchall()
    ]


def main():
    args = parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    cur_write = conn.cursor()

    print("=== LOJO Full Pipeline ===")
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}")

    if args.dry_run:
        print("DRY RUN — no database changes will be made")
    else:
        bak = DB_PATH + ".bak"
        shutil.copy2(DB_PATH, bak)
        print(f"Backup created: {bak}")

    create_tables(conn)

    events = get_events(conn)
    print(f"Events to process: {len(events)}")

    total_summaries = []
    winner_change_count = 0
    podium_change_count = 0

    for i, (event_id, comp_name, discipline, segment) in enumerate(events):
        try:
            summaries = run_lojo_for_event(conn, event_id, cur_write, dry_run=args.dry_run)
            total_summaries.extend(summaries)
            wc = sum(s["winner_changes"] for s in summaries)
            pc = sum(s["podium_changes"] for s in summaries)
            winner_change_count += wc
            podium_change_count += pc
            if (i + 1) % 10 == 0 or i == 0:
                dry_tag = " [DRY RUN]" if args.dry_run else ""
                print(f"  [{i+1}/{len(events)}] {comp_name} | {discipline} {segment} — "
                      f"{len(summaries)} judges, winner_changes={wc}{dry_tag}")
            if not args.dry_run:
                conn.commit()
        except Exception as exc:
            conn.rollback()
            print(f"  ❌  Event {event_id} ({comp_name} {discipline} {segment}) failed: {exc!r} — rolling back, continuing")
            continue

    print(f"\n=== LOJO Results ===")
    print(f"Total event-judge pairs: {len(total_summaries)}")
    print(f"Winner changes (LOJO): {winner_change_count}")
    print(f"Podium changes (LOJO): {podium_change_count}")

    # Kendall tau distribution
    taus = [s["kendall_tau_distance"] for s in total_summaries]
    if taus:
        avg_tau = sum(taus) / len(taus)
        max_tau = max(taus)
        high_tau = sum(1 for t in taus if t > 0.1)
        print(f"Kendall tau distance — mean: {avg_tau:.4f}, max: {max_tau:.4f}, pairs with tau>0.10: {high_tau}")

    # Top 10 most disruptive judge removals
    top10 = sorted(total_summaries, key=lambda s: s["kendall_tau_distance"], reverse=True)[:10]
    print("\n--- Top 10 Most Disruptive Judge Removals (by Kendall tau) ---")
    for s in top10:
        print(f"  Event {s['event_id']} | J{s['judge_position']} {s['judge_name'][:20]:20s} | "
              f"tau={s['kendall_tau_distance']:.4f} | winner_chg={s['winner_changes']} | "
              f"{s['actual_winner_name'][:15]} → {s['cf_winner_name'][:15]}")

    # Integrity checks (skip in dry-run — integrity_checks table may not have data to verify)
    if not args.dry_run:
        print("\n=== Integrity Checks ===")
        check_results = run_integrity_checks(conn)
        for r in check_results:
            pct = r["pass_rate"] * 100
            print(f"  {r['check_name'][:60]:60s}: {r['passed']}/{r['total_checked']} ({pct:.1f}%)")
    else:
        print("\n=== Integrity Checks === (skipped in dry-run)")

    # Three-regime comparison (legacy — requires pairwise_judge_statistics table from v1 schema)
    print("\n=== Three-Regime: OSNR Tier-2 Candidates (winner change + p≤0.001) ===")
    try:
        candidates = run_three_regime_comparison(conn)
        if candidates:
            for c in candidates:
                print(f"  {c['competition'][:30]:30s} | {c['discipline']:12s} {c['segment']:4s} | "
                      f"J{c['judge_position']} {c['judge_name'][:15]:15s} | p={c['p_value']:.4f} | "
                      f"tau={c['kendall_tau']:.4f} | {c['actual_winner'][:12]} → {c['cf_winner'][:12]}")
        else:
            print("  (none found)")
    except Exception as e:
        print(f"  (skipped — legacy section not applicable to v4 schema: {e})")

    conn.close()
    print(f"\nCompleted: {datetime.now().strftime('%H:%M:%S')}")


if __name__ == "__main__":
    main()
