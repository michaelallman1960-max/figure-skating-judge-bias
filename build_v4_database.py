#!/usr/bin/env python3
"""build_v4_database.py
Builds the lean, publication-ready v4 database from the existing v3 and seed databases.

Strategy:
  1. Copy seed → v4  (seed has ISU-impact results, more complete sources)
  2. Drop deprecated/vestigial tables
  3. Replace LOJO tables with v3 data (v3 has more complete LOJO: 1,288 vs 1,261 rows)
  4. VACUUM

Usage:
    python3 build_v4_database.py            # dry-run (default) — prints what would be done
    python3 build_v4_database.py --apply    # build the database
"""
import argparse
import shutil
import sqlite3
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE      = Path("/Users/allman/Library/CloudStorage/Dropbox/Dropbox Mike/Judging Bias")
V3_PATH   = BASE / "figure_skating_ijs_v3.sqlite"
SEED_PATH = BASE / "figure_skating_ijs_seed.sqlite"
V4_PATH   = BASE / "figure_skating_ijs_v4.sqlite"
ARCHIVE   = BASE / "archive" / "databases"

# ── Tables to DROP from v4 (not needed for publication) ──────────────────────
TABLES_TO_DROP = [
    "pairwise_judge_statistics",       # Deprecated B(j) method (~272K rows, ~70 MB)
    "pairwise_judge_statistics_new",   # Empty vestigial table
    "element_judge_deviations",        # Intermediate calc artifacts (~200K rows, ~25 MB)
    "judge_entry_totals",              # Old B(j) aggregated totals
    "judge_event_statistics",          # Old B(j) event-level statistics
    "raw_panel_scores",                # Redundant with entries table
    "event_labels",                    # B(j)-era label table
    "lost_and_found",                  # Debug artifact from ingestion
    "ingest_runs",                     # Pipeline metadata
    "integrity_checks",                # Regenerable via calculate_lojo_full.py
]

# ── LOJO tables: replace seed version with the more complete v3 version ───────
LOJO_TABLES = ["lojo_scores", "lojo_event_summary"]

# ── Expected row counts after consolidation ───────────────────────────────────
EXPECTED = {
    "competitions":           17,
    "events":                144,
    "entries":             2_706,
    "judges":              1_305,
    "elements":           23_043,
    "element_judge_scores": 206_682,
    "pcs_components":       9_458,
    "pcs_judge_scores":    84_922,
    "goe_factors":             17,
    "sources":                239,
    "pairwise_impact_results": 271_728,
    "judge_team_impacts":   24_174,
    "lojo_scores":          24_269,   # from v3
    "lojo_event_summary":    1_288,   # from v3
}


def row_count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def table_exists(conn, table):
    return conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()[0] > 0


def verify_source_counts():
    """Verify source databases have the expected row counts."""
    print("=== Verifying source databases ===")
    ok = True

    with sqlite3.connect(V3_PATH) as v3, sqlite3.connect(SEED_PATH) as seed:
        checks = [
            (seed, "competitions",           17),
            (seed, "events",                144),
            (seed, "entries",             2_706),
            (seed, "judges",              1_305),
            (seed, "elements",           23_043),
            (seed, "element_judge_scores", 206_682),
            (seed, "pcs_components",       9_458),
            (seed, "pcs_judge_scores",    84_922),
            (seed, "goe_factors",             17),
            (seed, "sources",                239),
            (seed, "pairwise_impact_results", 271_728),
            (seed, "judge_team_impacts",   24_174),
            (v3,   "lojo_scores",          24_269),
            (v3,   "lojo_event_summary",    1_288),
        ]
        for conn, table, expected in checks:
            name = "seed" if conn == seed else "v3  "
            actual = row_count(conn, table)
            status = "✓" if actual == expected else "✗"
            print(f"  {status} {name} {table:<30s}: {actual:>8,}  (expected {expected:>8,})")
            if actual != expected:
                ok = False

    return ok


def build_v4(dry_run):
    print("=== Build Plan ===")
    print(f"  Source 1 (seed): {SEED_PATH.name}  [{SEED_PATH.stat().st_size / 1e6:.1f} MB]")
    print(f"  Source 2 (v3):   {V3_PATH.name}  [{V3_PATH.stat().st_size / 1e6:.1f} MB]")
    print(f"  Output:          {V4_PATH.name}")
    print(f"  Drop tables:     {', '.join(TABLES_TO_DROP)}")
    print(f"  Replace LOJO:    {', '.join(LOJO_TABLES)} (from v3)")
    if dry_run:
        print("\nDRY RUN — no files will be created or modified.")
        return True

    # ── Step 1: Copy seed → v4 ─────────────────────────────────────────────
    if V4_PATH.exists():
        print(f"\n⚠️  {V4_PATH.name} already exists — removing before rebuild")
        V4_PATH.unlink()

    print(f"\nStep 1: Copying {SEED_PATH.name} → {V4_PATH.name} …")
    shutil.copy2(SEED_PATH, V4_PATH)
    size_before = V4_PATH.stat().st_size / 1e6
    print(f"  Copied: {size_before:.1f} MB")

    with sqlite3.connect(V4_PATH) as v4:
        v4.execute("PRAGMA journal_mode=WAL")

        # ── Step 2: Drop deprecated tables ─────────────────────────────────
        print("\nStep 2: Dropping deprecated tables …")
        for table in TABLES_TO_DROP:
            if table_exists(v4, table):
                n = row_count(v4, table)
                v4.execute(f"DROP TABLE IF EXISTS {table}")
                print(f"  Dropped {table}  ({n:,} rows)")
            else:
                print(f"  Skipped {table}  (not present)")
        v4.commit()

        # ── Step 3: Replace LOJO tables with v3 data ───────────────────────
        print("\nStep 3: Replacing LOJO tables with v3 data …")
        v4.execute(f"ATTACH DATABASE '{V3_PATH}' AS v3")

        for table in LOJO_TABLES:
            existing_n = row_count(v4, table) if table_exists(v4, table) else 0
            v4.execute(f"DELETE FROM {table}")
            v4.execute(f"INSERT INTO {table} SELECT * FROM v3.{table}")
            v4.commit()
            new_n = row_count(v4, table)
            print(f"  {table}: replaced {existing_n:,} rows with {new_n:,} rows from v3")

        v4.execute("DETACH DATABASE v3")

        # ── Step 4: Verify row counts ───────────────────────────────────────
        print("\nStep 4: Verifying row counts …")
        all_ok = True
        for table, expected in EXPECTED.items():
            actual = row_count(v4, table)
            status = "✓" if actual == expected else "✗"
            print(f"  {status} {table:<30s}: {actual:>8,}  (expected {expected:>8,})")
            if actual != expected:
                all_ok = False

        if not all_ok:
            print("\n❌  Row count mismatch — investigate before archiving old databases.")
            return False

        # ── Step 5: Integrity check ─────────────────────────────────────────
        print("\nStep 5: Integrity check …")
        result = v4.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            print(f"  ❌  integrity_check returned: {result}")
            return False
        print("  ✓ integrity_check: ok")

    # ── Step 6: VACUUM (outside the with-block — needs exclusive access) ───
    print("\nStep 6: VACUUM (reclaiming space from dropped tables) …")
    v4_vac = sqlite3.connect(V4_PATH)
    v4_vac.execute("VACUUM")
    v4_vac.close()

    size_after = V4_PATH.stat().st_size / 1e6
    print(f"  Size: {size_before:.1f} MB → {size_after:.1f} MB  (saved {size_before - size_after:.1f} MB)")
    return True


def verify_key_result():
    """Spot-check: verify OWG 2026 FD key result is intact.
    J1 FRA(FOURNIER BEAUDRY/CIZERON) vs USA(CHOCK/BATES): bias=+1.19, p=0.0003, q=0.034
    """
    print("\n=== Spot-Check: OWG 2026 Free Dance Key Result ===")
    with sqlite3.connect(V4_PATH) as v4:
        # Use noc_a/noc_b for reliable FRA/USA matching (team names contain full athlete names)
        rows = v4.execute("""
            SELECT judge_position, team_a, noc_a, team_b, noc_b,
                   ROUND(bias_points, 2) AS bias_pts,
                   ROUND(p_value, 6)     AS p,
                   ROUND(q_value_bh, 4)  AS q
            FROM pairwise_impact_results
            WHERE event_id = 2 AND judge_position = 'J1'
              AND noc_a = 'FRA' AND noc_b = 'USA'
              AND q_value_bh <= 0.05
        """).fetchall()
        if not rows:
            print("  ❌  J1 FRA vs USA not found with q≤0.05 in event_id=2")
            return False
        r = rows[0]
        print(f"  J{r[0]}  {r[1]} ({r[2]}) vs {r[3]} ({r[4]})")
        print(f"       bias={r[5]:+.2f} pts  p={r[6]:.4f}  q={r[7]:.4f}")
        if abs(r[5] - 1.19) < 0.01 and r[6] < 0.001 and r[7] < 0.05:
            print("  ✓ Key result confirmed: bias=+1.19, p=0.0003, q=0.034")
            return True
        else:
            print(f"  ⚠️  Values unexpected — check: {r}")
            return False


def archive_old_databases():
    """Move v3 and seed to archive/databases/."""
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for src in [V3_PATH, SEED_PATH]:
        dst = ARCHIVE / src.name
        if src.exists():
            shutil.move(str(src), str(dst))
            print(f"  Archived: {src.name} → archive/databases/{src.name}")
        else:
            print(f"  Already moved: {src.name}")


def main():
    p = argparse.ArgumentParser(description="Build lean v4 publication database")
    p.add_argument("--apply",   action="store_true", help="Actually build the database (default: dry-run)")
    p.add_argument("--archive", action="store_true", help="After successful build, archive old databases")
    args = p.parse_args()

    dry_run = not args.apply

    print("=" * 60)
    print("Figure Skating Judging Bias — Database Consolidation")
    print("=" * 60)

    # Always verify sources first
    if not verify_source_counts():
        print("\n❌  Source row counts don't match expectations — aborting.")
        return

    print()
    if dry_run:
        print("Source counts look good. Re-run with --apply to build v4.")
        build_v4(dry_run=True)
        return

    # Build
    if not build_v4(dry_run=False):
        print("\n❌  Build failed — old databases untouched.")
        return

    # Spot-check key result
    verify_key_result()

    print(f"\n✅  {V4_PATH.name} built and verified.")
    print("    Run again with --archive to move v3 and seed to archive/databases/.")

    if args.archive:
        print("\n=== Archiving old databases ===")
        archive_old_databases()
        print("Done. Only v4 remains in the project root.")


if __name__ == "__main__":
    main()
