#!/usr/bin/env python3
"""
Database Insertion Module
==========================

Takes parsed PDF data and inserts into the SQLite database.
Handles judges, entries, elements, and all judge scores.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from pdf_parser_v2 import JudgesDetailsPDFParser, SkaterPerformance, Element, PCSComponent

class DatabaseInserter:
    """Insert parsed competition data into database"""

    def __init__(self, db_path: str = 'figure_skating_ijs_seed.sqlite'):
        self.db_path = db_path

    def get_or_create_judge(self, conn: sqlite3.Connection, event_id: int,
                           judge_position: str, judge_name: str,
                           noc: Optional[str] = None) -> int:
        """Get existing judge_id or create new judge for this event"""
        cursor = conn.cursor()

        # Try to find existing judge for this event and position
        cursor.execute("""
            SELECT judge_id FROM judges
            WHERE event_id = ? AND judge_position = ?
        """, (event_id, judge_position))
        row = cursor.fetchone()

        if row:
            return row[0]

        # Create new judge
        cursor.execute("""
            INSERT INTO judges (event_id, judge_position, judge_name, country_code)
            VALUES (?, ?, ?, ?)
        """, (event_id, judge_position, judge_name, noc))
        return cursor.lastrowid

    def insert_performance(self, conn: sqlite3.Connection, event_id: int,
                          perf: SkaterPerformance, judge_map: Dict[int, str]) -> int:
        """Insert one skater's performance and return entry_id"""
        cursor = conn.cursor()

        # Insert entry (using actual database schema)
        cursor.execute("""
            INSERT INTO entries
            (event_id, team_name, noc, start_no, rank, tes, pcs, deductions, tss)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            perf.name,
            perf.nation,
            perf.start_no,
            perf.rank,
            perf.element_score,
            perf.pcs_score,
            perf.deductions,
            perf.total_score
        ))

        entry_id = cursor.lastrowid

        # Insert elements and judge scores (using actual database schema)
        for elem in perf.elements:
            cursor.execute("""
                INSERT INTO elements
                (entry_id, element_no, element_code, base_value,
                 panel_goe_points, panel_element_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entry_id,
                elem.element_no,
                elem.element_code,
                elem.base_value,
                elem.goe_panel,
                elem.scores_panel
            ))

            element_id = cursor.lastrowid

            # Insert judge GOE scores (using actual database schema)
            for judge_pos, goe_value in elem.judge_goes.items():
                if judge_pos in judge_map:
                    judge_name = judge_map[judge_pos]
                    judge_position = f"J{judge_pos}"
                    judge_id = self.get_or_create_judge(conn, event_id, judge_position, judge_name)

                    cursor.execute("""
                        INSERT INTO element_judge_scores
                        (element_id, judge_id, judge_goe_int)
                        VALUES (?, ?, ?)
                    """, (element_id, judge_id, goe_value))

        # Insert PCS components and judge scores
        for comp in perf.pcs_components:
            cursor.execute("""
                INSERT INTO pcs_components
                (entry_id, component_name, panel_score, factor)
                VALUES (?, ?, ?, ?)
            """, (
                entry_id,
                comp.component_name,
                comp.panel_score,
                comp.factor
            ))

            pcs_id = cursor.lastrowid

            # Insert judge PCS scores (using actual database schema)
            for judge_pos, pcs_value in comp.judge_scores.items():
                if judge_pos in judge_map:
                    judge_name = judge_map[judge_pos]
                    judge_position = f"J{judge_pos}"
                    judge_id = self.get_or_create_judge(conn, event_id, judge_position, judge_name)

                    cursor.execute("""
                        INSERT INTO pcs_judge_scores
                        (pcs_id, judge_id, judge_mark)
                        VALUES (?, ?, ?)
                    """, (pcs_id, judge_id, pcs_value))

        return entry_id

    def insert_segment(self, event_id: int, pdf_path: Path,
                      judge_panel_path: Path) -> int:
        """Parse PDF and insert all data for one segment"""

        print(f"\n  Parsing: {pdf_path.name}")

        # Parse PDF
        parser = JudgesDetailsPDFParser(pdf_path)
        performances = parser.parse()

        if not performances:
            print(f"    ⚠️  No performances parsed")
            return 0

        # Load judge panel mapping
        judge_map = {}
        if judge_panel_path.exists():
            with open(judge_panel_path, 'r') as f:
                for line in f:
                    if line.startswith('J'):
                        parts = line.strip().split(':', 1)
                        if len(parts) == 2:
                            judge_pos = int(parts[0][1:])  # "J1" -> 1
                            judge_name = parts[1].strip()
                            judge_map[judge_pos] = judge_name

        # Insert into database
        conn = sqlite3.connect(self.db_path)
        inserted_count = 0

        try:
            for perf in performances:
                self.insert_performance(conn, event_id, perf, judge_map)
                inserted_count += 1

            conn.commit()
            print(f"    ✅ Inserted {inserted_count} performances")

        except Exception as e:
            conn.rollback()
            print(f"    ❌ Error: {e}")
            inserted_count = 0

        finally:
            conn.close()

        return inserted_count

    def insert_competition(self, comp_code: str) -> Dict[str, int]:
        """Insert all segments for a competition"""

        # Map competition codes to event IDs and PDF patterns
        EVENT_MAP = {
            'wc2024': {
                'comp_id': 3,
                'segments': {
                    'FSKMSINGLES_SP': ('Men Single Skating', 'Short Program', 'SEG001OF'),
                    'FSKMSINGLES_FS': ('Men Single Skating', 'Free Skating', 'SEG002OF'),
                    'FSKWSINGLES_SP': ('Women Single Skating', 'Short Program', 'SEG003OF'),
                    'FSKWSINGLES_FS': ('Women Single Skating', 'Free Skating', 'SEG004OF'),
                    'FSKXPAIRS_SP': ('Pair Skating', 'Short Program', 'SEG005OF'),
                    'FSKXPAIRS_FS': ('Pair Skating', 'Free Skating', 'SEG006OF'),
                    'FSKXICEDANCE_RD': ('Ice Dance', 'Rhythm Dance', 'SEG007OF'),
                    'FSKXICEDANCE_FD': ('Ice Dance', 'Free Dance', 'SEG008OF'),
                }
            },
            'wc2025': {
                'comp_id': 4,
                'segments': {
                    'FSKMSINGLES_SP': ('Men Single Skating', 'Short Program', 'SEG001OF'),
                    'FSKMSINGLES_FS': ('Men Single Skating', 'Free Skating', 'SEG002OF'),
                    'FSKWSINGLES_SP': ('Women Single Skating', 'Short Program', 'SEG003OF'),
                    'FSKWSINGLES_FS': ('Women Single Skating', 'Free Skating', 'SEG004OF'),
                    'FSKXPAIRS_SP': ('Pair Skating', 'Short Program', 'SEG005OF'),
                    'FSKXPAIRS_FS': ('Pair Skating', 'Free Skating', 'SEG006OF'),
                    'FSKXICEDANCE_RD': ('Ice Dance', 'Rhythm Dance', 'SEG007OF'),
                    'FSKXICEDANCE_FD': ('Ice Dance', 'Free Dance', 'SEG008OF'),
                }
            }
        }

        if comp_code not in EVENT_MAP:
            print(f"❌ Unknown competition: {comp_code}")
            return {}

        comp_info = EVENT_MAP[comp_code]
        comp_id = comp_info['comp_id']

        print(f"\n{'='*60}")
        print(f"Inserting Competition: {comp_code}")
        print(f"{'='*60}")

        # Get event IDs from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        event_ids = {}
        for pdf_pattern, seg_info in comp_info['segments'].items():
            discipline, segment, panel_code = seg_info
            cursor.execute("""
                SELECT event_id FROM events
                WHERE competition_id = ? AND discipline = ? AND segment = ?
            """, (comp_id, discipline, segment))

            row = cursor.fetchone()
            if row:
                event_ids[pdf_pattern] = (row[0], panel_code)

        conn.close()

        # Process each segment
        pdf_dir = Path('figure_skating_seed_bundle/isu_pdfs') / comp_code
        results = {}

        for pdf_pattern, (event_id, panel_code) in event_ids.items():
            # Find PDF using exact pattern
            pdf_path = pdf_dir / f"{pdf_pattern}_JudgesDetails.pdf"

            if not pdf_path.exists():
                print(f"\n  ⚠️  No PDF found: {pdf_path.name}")
                continue

            judge_panel_path = pdf_dir / f"{panel_code}_panel_judges.txt"

            count = self.insert_segment(event_id, pdf_path, judge_panel_path)
            results[pdf_pattern] = count

        return results


def main():
    print("\n" + "="*60)
    print("Database Insertion - WC 2024 & WC 2025")
    print("="*60 + "\n")

    inserter = DatabaseInserter()

    # Insert WC 2024
    print("\n🔵 Processing World Championships 2024...")
    results_2024 = inserter.insert_competition('wc2024')

    # Insert WC 2025
    print("\n🔵 Processing World Championships 2025...")
    results_2025 = inserter.insert_competition('wc2025')

    # Summary
    total_inserted = sum(results_2024.values()) + sum(results_2025.values())

    print("\n" + "="*60)
    print("INSERTION COMPLETE")
    print("="*60)
    print(f"\n✅ WC 2024: {sum(results_2024.values())} performances")
    print(f"✅ WC 2025: {sum(results_2025.values())} performances")
    print(f"\n📊 Total: {total_inserted} performances inserted")

    # Database stats
    conn = sqlite3.connect('figure_skating_ijs_seed.sqlite')
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM entries")
    print(f"\n📈 Database now has:")
    print(f"   Total entries: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM elements")
    print(f"   Total elements: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM element_judge_scores")
    print(f"   Total judge scores: {cursor.fetchone()[0]}")

    conn.close()


if __name__ == '__main__':
    main()
