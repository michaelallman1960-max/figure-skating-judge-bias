#!/usr/bin/env python3
"""
ISU Judges Details PDF Parser - Singles and Pairs
==================================================

Parses ISU "Judges Details per Skater" PDFs for:
  - Men Single Skating (Short Program, Free Skating)
  - Women Single Skating (Short Program, Free Skating)
  - Pair Skating (Short Program, Free Skating)

Uses a proven regex-based horizontal-line approach (same strategy as
parse_ice_dance.py) that handles all known info markers:
  x  = credit highlight distribution (10% base value bonus, already in PDF value)
  <  = under-rotated jump
  << = severely under-rotated jump
  q  = jump landed on the quarter
  !  = not clear edge (attention call)
  e  = wrong edge
  F  = fall
  *  = invalid element (REF)
  Combined markers: q F, !F, F<<, << F, etc.

Handles both name formats:
  - Modern: "Shoma UNO" (first name + SURNAME)
  - OWG2018: "HANYU Yuzuru" (SURNAME + first name)

Handles both PCS formats:
  - 5 components (2018-2022 seasons): Skating Skills, Transitions,
    Performance, Composition, Interpretation of the Music
  - 3 components (2022/23+ season): Composition, Presentation,
    Skating Skills

Handles variable judge panels (8 or 9 judges).
"""

import re
import subprocess
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

class Element:
    """One executed technical element with individual judge GOE scores."""
    __slots__ = ('element_no', 'element_code', 'info', 'x_bonus',
                 'base_value', 'panel_goe', 'scores_panel', 'judge_goe')

    def __init__(self, element_no: int, element_code: str, info: str,
                 x_bonus: bool, base_value: float, panel_goe: float,
                 scores_panel: float, judge_goe: Dict[int, int]):
        self.element_no   = element_no
        self.element_code = element_code
        self.info         = info        # raw info string, e.g. "q F", "<"
        self.x_bonus      = x_bonus    # True if x marker present
        self.base_value   = base_value
        self.panel_goe    = panel_goe
        self.scores_panel = scores_panel
        self.judge_goe    = judge_goe   # {1: int, …, 9: int}


class PCSComponent:
    """One program component score with individual judge marks."""
    __slots__ = ('component_name', 'factor', 'panel_avg', 'judge_marks')

    def __init__(self, component_name: str, factor: float,
                 panel_avg: float, judge_marks: Dict[int, float]):
        self.component_name = component_name
        self.factor         = factor
        self.panel_avg      = panel_avg
        self.judge_marks    = judge_marks  # {1: float, …, 9: float}


class SkaterPerformance:
    """Complete performance for one skater or pair."""
    __slots__ = ('rank', 'name', 'nation', 'start_no',
                 'total_score', 'element_score', 'pcs_score', 'deductions',
                 'elements', 'pcs_components')

    def __init__(self, rank: int, name: str, nation: str, start_no: int,
                 total_score: float, element_score: float,
                 pcs_score: float, deductions: float,
                 elements: List[Element],
                 pcs_components: List[PCSComponent]):
        self.rank          = rank
        self.name          = name
        self.nation        = nation
        self.start_no      = start_no
        self.total_score   = total_score
        self.element_score = element_score
        self.pcs_score     = pcs_score
        self.deductions    = deductions
        self.elements      = elements
        self.pcs_components = pcs_components


# ─────────────────────────────────────────────────────────────────────────────
# PCS component names (any of these trigger a PCS line parse)
# ─────────────────────────────────────────────────────────────────────────────
PCS_NAMES = [
    'Skating Skills',
    'Transitions',
    'Performance',
    'Composition',
    'Presentation',
    'Interpretation of the Music',
    'Interpretation',
]

# Regex to detect a PCS component line:
# The line contains one of the component names followed by spaces and a factor
PCS_PATTERN = re.compile(
    r'(?:' + '|'.join(re.escape(n) for n in PCS_NAMES) + r')\s+'
)


# ─────────────────────────────────────────────────────────────────────────────
# Main parser
# ─────────────────────────────────────────────────────────────────────────────

class SinglesPairsParser:
    """
    Parse ISU Judges Details PDFs for Men's, Women's, and Pairs events.
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # ── Text extraction ──────────────────────────────────────────────────────

    def extract_text(self) -> str:
        """Extract text using pdftotext -layout (preserves column alignment)."""
        result = subprocess.run(
            ['pdftotext', '-layout', str(self.pdf_path), '-'],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            raise RuntimeError(f"pdftotext failed: {result.stderr}")
        return result.stdout

    # ── Top-level parse ──────────────────────────────────────────────────────

    def parse(self) -> List[SkaterPerformance]:
        """Parse the entire PDF; return one SkaterPerformance per skater."""
        text = self.extract_text()
        sections = self._split_into_skaters(text)
        print(f"\n  Found {len(sections)} skater sections in {self.pdf_path.name}")

        performances = []
        for i, section in enumerate(sections, 1):
            try:
                perf = self._parse_section(section)
                if perf:
                    performances.append(perf)
                    elem_count = len(perf.elements)
                    print(f"  ✅ #{i} {perf.name} (Rank {perf.rank}) "
                          f"– {elem_count} elements, "
                          f"{len(perf.pcs_components)} PCS")
                else:
                    print(f"  ⚠️  #{i} — section parse returned None")
            except Exception as exc:
                print(f"  ❌ #{i} — error: {exc}")
                import traceback
                traceback.print_exc()

        return performances

    # ── Section splitting ────────────────────────────────────────────────────

    # A skater header line looks like (with lots of leading whitespace):
    #   "           1 Shoma UNO                    JPN   32   104.63  57.70 ..."
    # OR (OWG2018 style):
    #   "         1 HANYU Yuzuru                   JPN   25   111.68  63.18 ..."
    # OR (FC2022/Pairs style):
    #   "        1    Junhwan CHA                  KOR   14   98.96   54.37 ..."
    # Key: starts with >=5 spaces (element lines only have 3), then a digit rank,
    #      then 1+ spaces, then an uppercase letter beginning the name.
    # We do NOT want to capture element lines like "   1   4F  11.00 ..."
    # Element lines have element_no (1-13) followed immediately by element code.
    # Name lines have the full name (2+ words) before the NOC code.
    _SKATER_START = re.compile(
        r'^\s{5,}(\d{1,3})\s+'                          # rank (5+ leading spaces)
        r'([A-Z][A-Za-z\'\-]+(?:\s+[A-Za-z\'\-/]+){1,10}?)'  # name (non-greedy)
        r'\s+([A-Z]{2,3})\s+'                           # NOC code (1+ space)
        r'(\d{1,3})\s+'                                 # starting number
        r'([\d.]+)'                                     # total score (first float)
    )

    def _split_into_skaters(self, text: str) -> List[str]:
        """
        Split the full PDF text into one section per skater/pair.
        Each section ends just before the next skater starts, or at EOF.
        """
        lines = text.split('\n')
        sections: List[str] = []
        current: List[str] = []
        in_skater = False

        for line in lines:
            if self._SKATER_START.match(line):
                if in_skater and current:
                    sections.append('\n'.join(current))
                current = [line]
                in_skater = True
            elif in_skater:
                current.append(line)
                # "Deductions:" line marks the end of a skater's block
                if re.match(r'^\s{0,10}Deductions:', line):
                    sections.append('\n'.join(current))
                    current = []
                    in_skater = False

        # flush last section if file doesn't end with Deductions:
        if in_skater and current:
            sections.append('\n'.join(current))

        return sections

    # ── Per-section parse ────────────────────────────────────────────────────

    def _parse_section(self, section: str) -> Optional[SkaterPerformance]:
        """Parse one skater's block; return SkaterPerformance or None."""
        lines = section.split('\n')

        header = self._parse_header(lines)
        if header is None:
            return None

        elements   = self._parse_elements(lines)
        pcs_comps  = self._parse_pcs(lines)

        return SkaterPerformance(
            rank          = header['rank'],
            name          = header['name'],
            nation        = header['nation'],
            start_no      = header['start_no'],
            total_score   = header['total'],
            element_score = header['tes'],
            pcs_score     = header['pcs'],
            deductions    = header['deductions'],
            elements      = elements,
            pcs_components = pcs_comps,
        )

    # ── Header parse ─────────────────────────────────────────────────────────

    # Header line patterns:
    # Modern:  "   1 Shoma UNO             JPN   32   104.63   57.70   46.93   0.00"
    # OWG2018: "      1 HANYU Yuzuru       JPN   25   111.68   63.18   48.50   0.00"
    # Pairs:   "   1 Riku MIURA / Ryuichi KIHARA   JPN  22  80.72  44.66  36.06  0.00"
    # The four trailing floats are: total, element, pcs, deductions
    _HEADER_RE = re.compile(
        r'^\s{5,}(\d{1,3})\s+'                          # rank (5+ leading spaces)
        r'([A-Z][A-Za-z\'\-]+(?:\s+[A-Za-z\'\-/]+){1,10}?)'  # name (non-greedy)
        r'\s+([A-Z]{2,3})\s+'                           # NOC code (1+ space)
        r'(\d{1,3})\s+'                                 # starting number
        r'([\d.]+)\s+'                                  # total segment score
        r'([\d.]+)\s+'                                  # element score
        r'([\d.]+)\s+'                                  # pcs score
        r'(-?[\d.]+)'                                   # deductions
    )

    def _parse_header(self, lines: List[str]) -> Optional[Dict]:
        """Extract rank, name, nation, scores from the first few lines."""
        for line in lines[:8]:
            m = self._HEADER_RE.match(line)
            if m:
                return {
                    'rank'    : int(m.group(1)),
                    'name'    : m.group(2).strip(),
                    'nation'  : m.group(3),
                    'start_no': int(m.group(4)),
                    'total'   : float(m.group(5)),
                    'tes'     : float(m.group(6)),
                    'pcs'     : float(m.group(7)),
                    'deductions': float(m.group(8)),
                }
        return None

    # ── Element parse ─────────────────────────────────────────────────────────
    #
    # Element line format (pdftotext -layout output):
    #
    # Clean:
    #   "   1   4F            11.00   3.77    4  4  4  4  3  3  2  3  3    14.77"
    #
    # With x bonus:
    #   "   4   4Lz+3T        17.27 x  4.76   4  4  4  3  4  5  4  5  4    22.03"
    #   "   4   3A             8.80 X   2.51  3  3  3  3  2  3  4  4  3    11.31"
    #
    # With info marker (no x):
    #   "   2   4S<         <  7.76  -3.43  -4 -2 -4 -5 -4 -5 -4 -5 -5     4.33"
    #   "   4   3F!         !  5.30  -0.08   0 -1  1 -1 -1 -1  1  2  0     5.22"
    #   "   2   4Fq         q 11.00  -4.40  -5 -4 -4 -4 -4 -4 -4 -4 -4     6.60"
    #   "   3   3A          F  8.00  -3.54  -5 -4 -3 -5 -5 -2 -4 -5 -5     4.46"
    #   "   2   4Tq     q F 9.50  -4.75  -5 -5 -5 -5 -5 -5 -5 -5 -5       4.75"
    #   "   7   4Lz<+1Eu+3S <  15.40 X -2.10  -3 -3 -2 -2 -3 -1 -1 -2 -3  13.30"
    #
    # Element codes:
    #   Jump combos: 4Lz+3T, 4S+3T+2T, 3F+1Eu+3S
    #   Sequences:   3F+2A+SEQ
    #   Spins:       FCSp4, CSSp4, CCoSp4, FUSp4, LSp4, etc.
    #   Steps:       StSq4, ChSq1
    #
    # The strategy:
    #   1. Match leading whitespace + digit(s) for element number
    #   2. Match element code (alphanumeric + +<)
    #   3. Optionally match info token(s) (1-3 chars from [<>!qFeF*])
    #   4. Optionally match "x" or "X" bonus marker
    #   5. Match base value (float)
    #   6. Match panel GOE (signed float)
    #   7. Match 8-9 signed integers (judge GOEs)
    #   8. Match final float (scores of panel) at end
    #
    # Because the column spacing varies, we parse tokens positionally after
    # identifying the element number and code.

    # Element code characters: letters, digits, +, < (jump combos like 3Lz<)
    _ELEM_CODE_RE = re.compile(r'^[A-Za-z0-9+<]+$')

    # Info tokens: known single-char and multi-char markers
    # x/X appears separately (x bonus vs rotation/edge call)
    # | is used in 2024/25 season as separator between combined markers
    # , is used in OWG2022 and OWG2026 as separator between combined markers
    # e.g. "!|<" or "!,q" or "q,!,q" means multiple simultaneous calls
    _INFO_CHARS = set('<>!qQeEfF*|,')

    def _is_info_token(self, token: str) -> bool:
        """Return True if token looks like an info marker (but not x bonus)."""
        # x and X are handled separately as bonus markers
        if not token:
            return False
        return all(c in self._INFO_CHARS for c in token)

    def _parse_elements(self, lines: List[str]) -> List[Element]:
        """Parse all element lines from a skater's section."""
        elements = []

        for line in lines:
            elem = self._try_parse_element_line(line)
            if elem is not None:
                elements.append(elem)

        return elements

    def _try_parse_element_line(self, line: str) -> Optional[Element]:
        """
        Try to parse one element line.  Returns Element or None.

        The line must:
          - Start with whitespace
          - Have a small integer (element number 1-13)
          - Have an element code starting with a letter
          - Have numeric base value and GOE
        """
        stripped = line.lstrip()
        if not stripped:
            return None

        # Quick pre-filter: must start with a digit
        if not stripped[0].isdigit():
            return None

        parts = stripped.split()
        if len(parts) < 5:
            return None

        # ── Part 0: element number ──────────────────────────────────────────
        try:
            elem_no = int(parts[0])
        except ValueError:
            return None

        if elem_no < 1 or elem_no > 13:
            return None

        # ── Part 1: element code ────────────────────────────────────────────
        # Element codes start with either:
        #   - a digit (jumps: 4F, 3A, 3Lz+3T, pairs: 3Tw3, 3LzTh, etc.)
        #   - a letter (spins: FCSp4, CCoSp4; steps: StSq4; throws etc.)
        # Must contain at least one letter (not purely numeric)
        code = parts[1]
        if not (code[0].isdigit() or code[0].isalpha()):
            return None
        if not any(c.isalpha() for c in code):
            return None  # purely numeric — not an element code

        # Validate: element codes contain only letters, digits, +, <
        # (trailing < is part of the code in some PDFs for under-rotation
        #  embedded in the code itself — we'll strip it later)
        # Reject lines that look like headers (e.g. "Executed", "Program")
        if len(code) > 20 or any(c in code for c in (',', '.', '/')):
            return None

        # Skip known non-element words
        if code in ('Executed', 'Elements', 'Program', 'Components',
                    'Judges', 'Total', 'Deductions', 'Ref', 'Report',
                    'Skating', 'Transitions', 'Performance', 'Composition',
                    'Presentation', 'Interpretation', 'Credit', 'Under',
                    'highlight'):
            return None

        # ── Parts 2+: info markers, x bonus, base value, panel GOE, judges ─
        # We scan from index 2, collecting optional info tokens, then x/X,
        # then the base value float, then panel GOE, then judge integers,
        # then panel score float at end.

        idx = 2
        info_tokens: List[str] = []
        x_bonus = False

        # Collect info tokens (non-numeric, non-x characters)
        while idx < len(parts):
            tok = parts[idx]
            # x or X = bonus marker; stop collecting info here
            if tok in ('x', 'X'):
                x_bonus = True
                idx += 1
                break
            # Check if it's a float (base value reached)
            try:
                float(tok)
                break   # reached base value
            except ValueError:
                pass
            # Must be an info token
            if self._is_info_token(tok):
                info_tokens.append(tok)
                idx += 1
            else:
                # Unknown token — might be part of a weird element name
                # or a header word; bail out
                return None

        # Now check for x/X after info tokens (if not yet found)
        if not x_bonus and idx < len(parts) and parts[idx] in ('x', 'X'):
            x_bonus = True
            idx += 1

        # ── Base value ──────────────────────────────────────────────────────
        if idx >= len(parts):
            return None
        try:
            base_value = float(parts[idx])
            idx += 1
        except ValueError:
            return None

        # After base value, there might be another x/X (some PDFs place it here)
        if idx < len(parts) and parts[idx] in ('x', 'X'):
            x_bonus = True
            idx += 1

        # ── Panel GOE ───────────────────────────────────────────────────────
        if idx >= len(parts):
            return None
        try:
            panel_goe = float(parts[idx])
            idx += 1
        except ValueError:
            return None

        # ── Judge GOEs (8 or 9 signed integers) ────────────────────────────
        judge_goe: Dict[int, int] = {}
        j_num = 1
        while idx < len(parts) and j_num <= 9:
            tok = parts[idx]
            # Stop if we hit a non-integer (e.g. "Ref.", float panel score)
            # Judge GOEs are -5 to +5 integers
            try:
                val = int(tok)
                if -5 <= val <= 5:
                    judge_goe[j_num] = val
                    j_num += 1
                    idx += 1
                else:
                    break
            except ValueError:
                break

        # Need at least 7 judges to be a valid element line
        if len(judge_goe) < 7:
            return None

        # ── Scores of Panel (last float on the line) ────────────────────────
        # Find the last float-like token
        scores_panel = None
        remaining = parts[idx:]
        for tok in reversed(remaining):
            try:
                scores_panel = float(tok)
                break
            except ValueError:
                continue
        if scores_panel is None:
            scores_panel = base_value + panel_goe

        # ── Clean up element code ───────────────────────────────────────────
        # Some PDFs embed the under-rotation marker in the code itself:
        # e.g. "4S<" or "3Lz<<"  — strip trailing < characters from code
        # (they are already captured in info_tokens from the separate column)
        # But keep them in the code if they seem structural (like 3Lz+3T<)
        # For simplicity: just keep the code as-is; stripping would be lossy.

        # Include 'x' in info_str when the second-half bonus applies.
        # x_bonus is captured separately from info_tokens, so we add it explicitly.
        if x_bonus:
            info_tokens = ['x'] + info_tokens
        info_str = ' '.join(info_tokens)

        return Element(
            element_no   = elem_no,
            element_code = code,
            info         = info_str,
            x_bonus      = x_bonus,
            base_value   = base_value,
            panel_goe    = panel_goe,
            scores_panel = scores_panel,
            judge_goe    = judge_goe,
        )

    # ── PCS parse ─────────────────────────────────────────────────────────────
    #
    # PCS lines (5-component format):
    #   "    Skating Skills    1.00   9.50  9.25  9.75 ..."
    #   "    Interpretation of the Music   1.00   9.50 ..."
    #
    # PCS lines (3-component format):
    #   "    Composition       1.67   9.25  9.25  9.25 ..."
    #
    # Strategy:
    #   1. Check if the line contains one of the known component names
    #   2. Find the factor (float between 0.5 and 2.5)
    #   3. Collect the next 8-9 floats as judge marks (0-10 range)
    #   4. Last float on line is panel average

    def _parse_pcs(self, lines: List[str]) -> List[PCSComponent]:
        """Parse all PCS component lines."""
        components = []
        seen_names: set = set()

        for line in lines:
            comp = self._try_parse_pcs_line(line)
            if comp and comp.component_name not in seen_names:
                # Avoid duplicates (page repetition in some PDFs)
                seen_names.add(comp.component_name)
                components.append(comp)

        return components

    def _split_pcs_tokens(self, line: str) -> List[str]:
        """Split a PCS line into tokens.

        ISU singles/pairs PDFs always have spaces between values — run-together
        floats (e.g. "10.009.50") do not occur in practice.  The regex that was
        previously used here to handle them was over-broad: it matched normal
        two-decimal floats like "1.33" and split them into ["1.3", "3"], corrupting
        every PCS factor, judge mark, and panel average.  Plain split() is correct.
        """
        return line.split()

    def _try_parse_pcs_line(self, line: str) -> Optional[PCSComponent]:
        """Try to parse one PCS component line."""
        # Quick check: must contain a known component keyword
        matched_name = None
        for name in PCS_NAMES:
            if name in line:
                matched_name = name
                break
        if matched_name is None:
            return None

        # Split by whitespace, handling run-together floats
        parts = self._split_pcs_tokens(line)
        if len(parts) < 4:
            return None

        factor_idx = None
        for i, p in enumerate(parts):
            try:
                val = float(p)
                # PCS factors range:
                #   SP (post 2022/23): 1.67 (Men/Women/Pairs)
                #   SP (pre 2022/23):  1.00 or 1.20
                #   FS (post 2022/23): 3.33
                #   FS (pre 2022/23):  2.00
                #   Ice Dance:         1.25, 1.00, 0.75, etc.
                # Accept anything from 0.5 to 4.0
                if 0.5 <= val <= 4.0:
                    factor_idx = i
                    break
            except ValueError:
                continue

        if factor_idx is None:
            return None

        try:
            factor = float(parts[factor_idx])
        except (ValueError, IndexError):
            return None

        # Collect judge marks (floats in 0-10 range after the factor)
        judge_marks: Dict[int, float] = {}
        j_num = 1
        idx = factor_idx + 1
        while idx < len(parts) and j_num <= 9:
            try:
                val = float(parts[idx])
                if 0.0 <= val <= 10.5:
                    judge_marks[j_num] = val
                    j_num += 1
                    idx += 1
                else:
                    break
            except ValueError:
                break

        if len(judge_marks) < 7:
            return None

        # Panel average: last float on the line
        panel_avg = 0.0
        for tok in reversed(parts):
            try:
                panel_avg = float(tok)
                break
            except ValueError:
                continue

        return PCSComponent(
            component_name = matched_name,
            factor         = factor,
            panel_avg      = panel_avg,
            judge_marks    = judge_marks,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Database insertion
# ─────────────────────────────────────────────────────────────────────────────

def load_judge_names(panel_txt_path: Path) -> Dict[int, str]:
    """
    Load judge names from a panel_judges.txt file.
    Format:  J1: Firstname LASTNAME
    Returns {1: 'Full Name', …, 9: 'Full Name'}
    """
    names: Dict[int, str] = {}
    if not panel_txt_path.exists():
        return names

    pattern = re.compile(r'J(\d)\s*:\s*(.+)')
    with open(panel_txt_path, 'r', encoding='utf-8') as fh:
        for line in fh:
            m = pattern.search(line)
            if m:
                j_num = int(m.group(1))
                name  = m.group(2).strip()
                names[j_num] = name
    return names


def get_or_create_judge(conn: sqlite3.Connection, event_id: int,
                         j_position: str, j_name: str,
                         country: Optional[str]) -> int:
    """Insert or retrieve a judge row; return judge_id.

    Uses actual DB schema columns: judge_position, judge_name, country_code.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT judge_id FROM judges WHERE event_id=? AND judge_position=?",
        (event_id, j_position)
    )
    row = cur.fetchone()
    if row:
        # Update name if we now have a real name
        if j_name and not j_name.startswith('Judge '):
            cur.execute(
                "UPDATE judges SET judge_name=?, country_code=? WHERE judge_id=?",
                (j_name, country, row[0])
            )
        return row[0]
    cur.execute(
        "INSERT INTO judges (event_id, judge_position, judge_name, country_code) VALUES (?,?,?,?)",
        (event_id, j_position, j_name, country)
    )
    conn.commit()
    return cur.lastrowid


def insert_performance(conn: sqlite3.Connection,
                        event_id: int,
                        perf: SkaterPerformance,
                        judge_names: Dict[int, str]) -> None:
    """
    Insert one performance into the database.
    Clears any existing entry for (event_id, team_name) first to avoid dups.

    Uses actual DB schema column names from figure_skating_ijs_seed.sqlite.
    """
    cur = conn.cursor()

    # Ensure judges exist (J1-J9)
    for j_num in range(1, 10):
        j_pos  = f"J{j_num}"
        j_name = judge_names.get(j_num, f"Judge J{j_num}")
        get_or_create_judge(conn, event_id, j_pos, j_name, None)

    # Fetch judge_ids keyed by position string "J1".."J9"
    cur.execute(
        "SELECT judge_position, judge_id FROM judges WHERE event_id=? ORDER BY judge_position",
        (event_id,)
    )
    judge_id_map = {row[0]: row[1] for row in cur.fetchall()}

    # Delete any existing entry for this (event_id, team_name)
    cur.execute(
        "SELECT entry_id FROM entries WHERE event_id=? AND team_name=?",
        (event_id, perf.name)
    )
    existing = cur.fetchall()
    for (old_entry_id,) in existing:
        # Get element_ids
        cur.execute("SELECT element_id FROM elements WHERE entry_id=?", (old_entry_id,))
        elem_ids = [r[0] for r in cur.fetchall()]
        if elem_ids:
            ph = ','.join('?' * len(elem_ids))
            cur.execute(f"DELETE FROM element_judge_scores WHERE element_id IN ({ph})", elem_ids)
        cur.execute("DELETE FROM elements WHERE entry_id=?", (old_entry_id,))
        # PCS tables
        cur.execute("SELECT pcs_id FROM pcs_components WHERE entry_id=?", (old_entry_id,))
        pcs_ids = [r[0] for r in cur.fetchall()]
        if pcs_ids:
            ph2 = ','.join('?' * len(pcs_ids))
            cur.execute(f"DELETE FROM pcs_judge_scores WHERE pcs_id IN ({ph2})", pcs_ids)
        cur.execute("DELETE FROM pcs_components WHERE entry_id=?", (old_entry_id,))
        cur.execute("DELETE FROM entries WHERE entry_id=?", (old_entry_id,))

    # Insert entry — actual schema: team_name, noc, start_no, rank, tes, pcs, deductions, tss
    cur.execute("""
        INSERT INTO entries
            (event_id, team_name, noc, start_no, rank, tes, pcs, deductions, tss)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (event_id, perf.name, perf.nation, perf.start_no, perf.rank,
          perf.element_score, perf.pcs_score, perf.deductions, perf.total_score))
    entry_id = cur.lastrowid

    # Insert elements
    for elem in perf.elements:
        # element_info: raw ISU info field (e.g. 'x' for second-half bonus, '< !' for edge+downgrade)
        # NULL means no info tokens were present for this element.
        info_val = elem.info if elem.info else None
        cur.execute("""
            INSERT OR REPLACE INTO elements
                (entry_id, element_no, element_code, base_value,
                 panel_goe_points, panel_element_score, element_info)
            VALUES (?,?,?,?,?,?,?)
        """, (entry_id, elem.element_no, elem.element_code,
              elem.base_value, elem.panel_goe, elem.scores_panel, info_val))
        element_id = cur.lastrowid

        for j_num, goe_val in elem.judge_goe.items():
            j_pos    = f"J{j_num}"
            judge_id = judge_id_map.get(j_pos)
            if judge_id:
                cur.execute("""
                    INSERT OR REPLACE INTO element_judge_scores
                        (element_id, judge_id, judge_goe_int)
                    VALUES (?,?,?)
                """, (element_id, judge_id, goe_val))

    # Insert PCS components — actual schema:
    #   pcs_components: entry_id, component_name, factor, panel_component_avg
    #   pcs_judge_scores: pcs_id, judge_id, judge_mark
    for comp in perf.pcs_components:
        cur.execute("""
            INSERT OR REPLACE INTO pcs_components
                (entry_id, component_name, factor, panel_component_avg)
            VALUES (?,?,?,?)
        """, (entry_id, comp.component_name, comp.factor, comp.panel_avg))
        pcs_id = cur.lastrowid

        for j_num, mark in comp.judge_marks.items():
            j_pos    = f"J{j_num}"
            judge_id = judge_id_map.get(j_pos)
            if judge_id:
                cur.execute("""
                    INSERT OR REPLACE INTO pcs_judge_scores
                        (pcs_id, judge_id, judge_mark)
                    VALUES (?,?,?)
                """, (pcs_id, judge_id, mark))

    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Competition configuration and orchestration
# ─────────────────────────────────────────────────────────────────────────────

# Standard SEG numbering: 1=Men SP, 2=Men FS, 3=Women SP, 4=Women FS,
#                          5=Pairs SP, 6=Pairs FS, 7=ID RD, 8=ID FD
SEG_TO_DISCIPLINE = {
    1: ("Men Single Skating",   "Short Program"),
    2: ("Men Single Skating",   "Free Skating"),
    3: ("Women Single Skating", "Short Program"),
    4: ("Women Single Skating", "Free Skating"),
    5: ("Pair Skating",         "Short Program"),
    6: ("Pair Skating",         "Free Skating"),
}

# Competitions: key → (db_name, pdf_dir, {seg_num: pdf_stem or None})
# None = use standard SEG00N_JudgesDetails.pdf naming
# Explicit path = alternative filename
COMPETITIONS = {
    'wc2025': {
        'name'   : 'ISU World Figure Skating Championships 2025',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/wc2025',
        'segs'   : {1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
    },
    'wc2024': {
        'name'   : 'ISU World Figure Skating Championships 2024',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/wc2024',
        'segs'   : {1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
    },
    'wc2023': {
        'name'   : 'ISU World Figure Skating Championships 2023',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/wc2023',
        'segs'   : {1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
    },
    'wc2022': {
        'name'   : 'ISU World Figure Skating Championships 2022',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/wc2022',
        'segs'   : {1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
    },
    # WC2021 and WC2019 not in database, skip
    # 'wc2021': {...},
    # 'wc2019': {...},
    'owg2022': {
        'name'   : 'Olympic Winter Games 2022 - Figure Skating',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/owg2022',
        'segs'   : {1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
    },
    # OWG2018 not in database, skip
    # 'owg2018': {...},
    'milano2026': {
        # OWG2026: milano2026 dir has Men SP/FS + Women SP/FS + Pairs SP/FS
        'name'   : 'Olympic Winter Games 2026 (Milano Cortina) - Figure Skating',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/milano2026',
        'segs'   : {
            1: None,   # Men SP
            2: None,   # Men FS
            3: None,   # Women SP
            4: None,   # Women FS
            5: None,   # Pairs SP
            6: None,   # Pairs FS
        },
    },
    'ec2025': {
        'name'   : 'ISU European Figure Skating Championships 2025',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/ec2025',
        'segs'   : {1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
    },
    'ec2024': {
        'name'   : 'ISU European Figure Skating Championships 2024',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/ec2024',
        'segs'   : {1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
    },
    'ec2023': {
        'name'   : 'ISU European Figure Skating Championships 2023',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/ec2023',
        'segs'   : {1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
    },
    'ec2022': {
        'name'   : 'ISU European Figure Skating Championships 2022',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/ec2022',
        'segs'   : {1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
    },
    'ec2020': {
        'name'   : 'ISU European Figure Skating Championships 2020',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/ec2020',
        'segs'   : {1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
    },
    'fc2025': {
        'name'   : 'ISU Four Continents Figure Skating Championships 2025',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/fc2025',
        'segs'   : {1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
    },
    'fc2024': {
        'name'   : 'ISU Four Continents Figure Skating Championships 2024',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/fc2024',
        'segs'   : {1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
    },
    'fc2023': {
        'name'   : 'ISU Four Continents Figure Skating Championships 2023',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/fc2023',
        'segs'   : {1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
    },
    'fc2022': {
        'name'   : 'ISU Four Continents Figure Skating Championships 2022',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/fc2022',
        'segs'   : {1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
    },
    'fc2020': {
        'name'   : 'ISU Four Continents Figure Skating Championships 2020',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/fc2020',
        'segs'   : {1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
    },
    'gpf2024': {
        'name'   : 'ISU Grand Prix of Figure Skating Final 2024/25 (Grenoble)',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/gpf2024',
        'segs'   : {1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
    },
    'gpf2023': {
        'name'   : 'ISU Grand Prix of Figure Skating Final 2023/24 (Beijing)',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/gpf2023',
        'segs'   : {1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
    },
    'gpf2022': {
        'name'   : 'ISU Grand Prix of Figure Skating Final 2022/23 (Turin)',
        'pdf_dir': 'figure_skating_seed_bundle/isu_pdfs/gpf2022',
        'segs'   : {1: None, 2: None, 3: None, 4: None, 5: None, 6: None},
    },
}


def _find_pdf(pdf_dir: Path, seg_num: int,
              explicit_name: Optional[str]) -> Optional[Path]:
    """Locate the PDF for a segment."""
    if explicit_name:
        p = pdf_dir / explicit_name
        return p if p.exists() else None

    # Standard naming patterns
    for pattern in [
        f"SEG{seg_num:03d}_JudgesDetails.pdf",
        f"SEG00{seg_num}_JudgesDetails.pdf",
        f"SEG0{seg_num}_JudgesDetails.pdf",
    ]:
        p = pdf_dir / pattern
        if p.exists():
            return p
    return None


def _find_panel_txt(pdf_dir: Path, seg_num: int) -> Optional[Path]:
    """Locate the panel judges txt file for a segment."""
    for pattern in [
        f"SEG{seg_num:03d}OF_panel_judges.txt",
        f"SEG00{seg_num}OF_panel_judges.txt",
    ]:
        p = pdf_dir / pattern
        if p.exists():
            return p
    return None


def populate_competition(comp_key: str, config: dict,
                          db_path: str) -> int:
    """Parse and insert all non-Ice-Dance segments for one competition."""
    print(f"\n{'='*70}")
    print(f"POPULATING: {config['name']}")
    print(f"{'='*70}")

    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    # Resolve competition_id
    cur.execute(
        "SELECT competition_id FROM competitions WHERE name=?",
        (config['name'],)
    )
    row = cur.fetchone()
    if not row:
        print(f"  ❌ Competition not in database: {config['name']}")
        conn.close()
        return 0
    comp_id = row[0]

    # Build event lookup: (discipline, segment) → event_id
    cur.execute(
        "SELECT event_id, discipline, segment FROM events WHERE competition_id=?",
        (comp_id,)
    )
    event_map = {(r[1], r[2]): r[0] for r in cur.fetchall()}
    conn.close()

    pdf_dir = Path(config['pdf_dir'])
    if not pdf_dir.exists():
        print(f"  ❌ PDF directory not found: {pdf_dir}")
        return 0

    total = 0

    for seg_num, explicit_name in config['segs'].items():
        discipline, segment = SEG_TO_DISCIPLINE[seg_num]
        event_id = event_map.get((discipline, segment))
        if event_id is None:
            print(f"  ⚠️  SEG{seg_num:03d} ({discipline} - {segment}): "
                  f"not in database")
            continue

        pdf_path = _find_pdf(pdf_dir, seg_num, explicit_name)
        if pdf_path is None:
            print(f"  ⚠️  SEG{seg_num:03d} ({discipline} - {segment}): "
                  f"PDF not found")
            continue

        # Load judge names (best-effort)
        panel_txt = _find_panel_txt(pdf_dir, seg_num)
        judge_names = load_judge_names(panel_txt) if panel_txt else {}

        print(f"\n  --- SEG{seg_num:03d}: {discipline} - {segment} ---")
        print(f"  PDF: {pdf_path.name}")
        if judge_names:
            print(f"  Judges: {', '.join(judge_names.values())}")

        try:
            parser       = SinglesPairsParser(str(pdf_path))
            performances = parser.parse()

            conn = sqlite3.connect(db_path)
            for perf in performances:
                insert_performance(conn, event_id, perf, judge_names)
            conn.close()

            print(f"  ✅ Inserted {len(performances)} performances")
            total += len(performances)

        except Exception as exc:
            print(f"  ❌ Error: {exc}")
            import traceback
            traceback.print_exc()

    return total


def populate_all(db_path: str = 'figure_skating_ijs_seed.sqlite') -> None:
    """Populate all competitions."""
    print("\n" + "="*70)
    print("POPULATING ALL SINGLES/PAIRS COMPETITIONS")
    print("="*70)

    grand_total = 0
    for comp_key, config in COMPETITIONS.items():
        total = populate_competition(comp_key, config, db_path)
        grand_total += total

    print("\n" + "="*70)
    print(f"🎉 COMPLETE: {grand_total} total performances inserted")
    print("="*70)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    if len(sys.argv) == 1:
        # Run all competitions
        populate_all()
    elif len(sys.argv) == 2 and sys.argv[1].endswith('.pdf'):
        # Test parse a single PDF
        pdf = sys.argv[1]
        print(f"\nTest parsing: {pdf}")
        parser = SinglesPairsParser(pdf)
        perfs  = parser.parse()
        print(f"\nParsed {len(perfs)} performances.")
        for p in perfs[:3]:
            print(f"\n  Rank {p.rank}: {p.name} ({p.nation})")
            print(f"    TSS={p.total_score}  TES={p.element_score}  "
                  f"PCS={p.pcs_score}  Ded={p.deductions}")
            print(f"    Elements: {len(p.elements)}")
            for e in p.elements[:3]:
                print(f"      {e.element_no}. {e.element_code}"
                      f"{'*x*' if e.x_bonus else ''}"
                      f"{' '+e.info if e.info else ''}"
                      f"  BV={e.base_value}  GOE={e.panel_goe}"
                      f"  J={e.judge_goe}")
            print(f"    PCS: {len(p.pcs_components)} components")
            for c in p.pcs_components[:2]:
                print(f"      {c.component_name}  f={c.factor}"
                      f"  avg={c.panel_avg}  J={c.judge_marks}")
    elif len(sys.argv) == 2:
        # Run a single competition key
        key = sys.argv[1]
        if key in COMPETITIONS:
            populate_competition(key, COMPETITIONS[key], 'figure_skating_ijs_seed.sqlite')
        else:
            print(f"Unknown competition key: {key}")
            print(f"Available: {', '.join(COMPETITIONS.keys())}")
    else:
        print("Usage:")
        print("  python parse_singles_pairs.py                  # populate all")
        print("  python parse_singles_pairs.py wc2023           # one competition")
        print("  python parse_singles_pairs.py file.pdf          # test one PDF")
