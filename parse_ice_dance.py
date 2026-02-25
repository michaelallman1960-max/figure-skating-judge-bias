#!/usr/bin/env python3
"""
Ice Dance PDF Parser — Unified Multi-Format Version
====================================================

Handles all ISU Ice Dance PDF formats encountered from 2022–2026:

  FORMAT A: Vertical/old (EC/FC/WC 2022, EC/FC/WC/GPF 2023-2024, OWG 2022)
    - pdftotext (no -layout flag)
    - One value per line, columns serialized top-to-bottom
    - Sub-variants by header/score layout

  FORMAT B: Horizontal/new (WC 2023, GPF 2023/24, GPF 2024/25, EC/FC/WC 2025)
    - pdftotext -layout flag
    - Tabular format; same as singles/pairs PDFs
    - Detected when raw text contains "Rank Name" as a heading

  FORMAT C: Olympic vertical (OWG 2022, Milano 2026)
    - pdftotext (no -layout)
    - Vertical but with "NOC Code" instead of "Nation"
    - Team name and NOC appear BEFORE elements section
"""

import re
import subprocess
import sqlite3
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from pathlib import Path


PDFTOTEXT = '/opt/homebrew/bin/pdftotext'


@dataclass
class IceDanceElement:
    element_no: int
    element_code: str
    base_value: float
    goe_panel: float
    judge_goes: Dict[int, int] = field(default_factory=dict)


@dataclass
class IceDancePCSComponent:
    component_name: str
    factor: float
    panel_avg: float
    judge_marks: Dict[int, float] = field(default_factory=dict)


@dataclass
class IceDancePerformance:
    rank: int
    team_name: str
    noc: str
    start_no: int
    tss: float
    tes: float
    pcs: float
    deductions: float
    elements: List[IceDanceElement] = field(default_factory=list)
    pcs_components: List['IceDancePCSComponent'] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# UTILITY
# ─────────────────────────────────────────────────────────────────────────────

def is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


def is_int_only(s: str) -> bool:
    """True if string is an integer (not float)."""
    try:
        int(s)
        return '.' not in s
    except (ValueError, TypeError):
        return False


def pdf_to_text_raw(pdf_path: str) -> str:
    """pdftotext without -layout (vertical column dump)."""
    result = subprocess.run(
        [PDFTOTEXT, pdf_path, '-'],
        capture_output=True, text=True
    )
    return result.stdout


def pdf_to_text_layout(pdf_path: str) -> str:
    """pdftotext with -layout (preserves spatial layout)."""
    result = subprocess.run(
        [PDFTOTEXT, '-layout', pdf_path, '-'],
        capture_output=True, text=True
    )
    return result.stdout


def detect_format_from_pdf(pdf_path: str) -> str:
    """
    Detect PDF format by checking PDF text structure.

    Returns:
      'horizontal'  — tabular multi-column layout (use -layout mode)
      'vertical'    — single-column vertical dump (no -layout)

    Decision logic:
    - If raw text has "Rank Name" combined on one line → horizontal (WC2023 type)
    - If raw text has rank+name+NOC all on one line → horizontal
    - If raw text has rank on line 0, "Name" on line 2 (standalone) → VERTICAL
      UNLESS the number of blocks found is much less than team count
      (EC/FC/WC 2025: 3 teams per page → raw blocks undercount)

    Key heuristic for multi-column detection:
    - In a single-column vertical PDF: blocks found ≈ skater count
    - In a multi-column vertical PDF: blocks found ≈ skater_count / skaters_per_page

    We detect multi-column by checking if the first block in raw mode contains
    element data from MULTIPLE skaters (i.e., more than n_elements elements).
    """
    raw_text = pdf_to_text_raw(pdf_path)
    lines = [l.strip() for l in raw_text.split('\n')]

    # Signal 1: raw text has "Rank Name" combined → horizontal (WC2023)
    for line in lines[:10]:
        if 'Rank Name' in line:
            return 'horizontal'

    # Signal 2: rank + name + NOC on same line → horizontal
    for line in lines[:15]:
        stripped = line.strip()
        if ' / ' in stripped and re.match(r'^\d+\s+\w', stripped):
            parts = stripped.split()
            if any(re.match(r'^[A-Z]{3}$', p) for p in parts):
                return 'horizontal'

    # Signal 3: Check if vertical blocks undercount teams (multi-column PDF)
    # In EC/FC/WC 2025 and GPF2024/25: raw vertical has ~10 pages but 25-30 teams
    # The block splitter would find ~10 blocks (page starts), not 25-30
    # Detect this by checking: does the first 'block' contain way too many elements?
    # (because it spans multiple skaters on the same page)

    # Find how many block starts exist
    block_starts = []
    for i, line in enumerate(lines):
        if not is_int_only(line) or line == '':
            continue
        window = lines[i+1:i+9]
        if 'Name' in window:
            block_starts.append(i)

    if block_starts:
        # Check if there are significantly fewer blocks than expected teams
        # For Ice Dance events, typical counts: RD has 6-35 teams, FD has 6-25 teams
        # If blocks < 10 AND we know there should be more teams (by checking layout), use horizontal
        # Quick check: does the first block contain more than 2*max_expected_elements?
        # A normal block has 5 or 7 elements. If it has 15+, it spans multiple skaters.
        if len(block_starts) >= 1:
            first_block_end = block_starts[1] if len(block_starts) > 1 else len(lines)
            first_block = lines[block_starts[0]:first_block_end]

            # Count element codes in the block (lines that look like Ice Dance element codes)
            # Element codes: SqTw, PSt, MiSt, StaLi, ChRS, RoLi, SlLi, CuLi, CiSt, etc.
            elem_code_pattern = re.compile(r'^(SqTw|PSt|MiSt|StaLi|ChRS|RoLi|SlLi|CuLi|CiSt|1MB|kp|DiSt|StaLi|OFStW|OFStM)')
            elem_codes_found = sum(1 for l in first_block if elem_code_pattern.match(l))

            if elem_codes_found > 8:
                # More than 8 element codes in first block → spans multiple skaters → horizontal
                return 'horizontal'

    # Signal 4: Check layout text for horizontal structure
    # (only if we can't determine from raw text — avoid for known vertical PDFs)
    # For EC/FC/WC 2025: the layout mode shows "Rank    Name    Nation" heading
    # For WC2022: the layout mode ALSO shows this heading, so we need extra differentiation
    # Extra check: in layout mode, count how many skater header lines exist per page
    layout_text = pdf_to_text_layout(pdf_path)
    layout_lines = layout_text.split('\n')

    # Count pages (form feeds) and skater headers in layout
    page_count = layout_text.count('\x0c') + 1
    # Count skater header lines: lines with " / " AND a 3-letter NOC AND numeric scores
    skater_headers = 0
    for line in layout_lines:
        if ' / ' in line:
            parts = line.split()
            has_noc = any(re.match(r'^[A-Z]{3}$', p) for p in parts)
            has_scores = sum(1 for p in parts if re.match(r'^\d+\.\d+$', p))
            if has_noc and has_scores >= 2:
                skater_headers += 1

    # If skaters per page > 1.5 (i.e., multiple per page) → horizontal layout
    if page_count > 0 and skater_headers > 0:
        skaters_per_page = skater_headers / page_count
        if skaters_per_page > 1.5:
            return 'horizontal'

    return 'vertical'


def detect_format(raw_text: str) -> str:
    """
    Detect PDF format from raw text only (used when pdf_path not available).
    Falls back to 'vertical' if uncertain.
    """
    lines = [l.strip() for l in raw_text.split('\n')]

    # Horizontal: "Rank Name" combined
    for line in lines[:10]:
        if 'Rank Name' in line:
            return 'horizontal'

    # Horizontal: team name on same line as rank
    for line in lines[:15]:
        if ' / ' in line and re.match(r'^\d+\s+\w', line.strip()):
            parts = line.split()
            if any(re.match(r'^[A-Z]{3}$', p) for p in parts):
                return 'horizontal'

    return 'vertical'



# ─────────────────────────────────────────────────────────────────────────────
# PCS EXTRACTION (both formats)
# ─────────────────────────────────────────────────────────────────────────────

# Known PCS component names (all variants seen across ISU events 2022-2026)
PCS_COMPONENT_NAMES = {
    'Skating Skills',
    'Transitions',
    'Performance',
    'Composition',
    'Interpretation of the Music/Timing',
    'Interpretation of the Music',
    'Interpretation',
    'Presentation',
    'Choreography',
    'Timing',
}


def _is_pcs_component_line(line: str) -> Optional[str]:
    """
    If this line (stripped) starts with a known PCS component name, return that name.
    Otherwise return None.
    Used for horizontal-format parsing where each component is one tabular line.
    """
    stripped = line.strip()
    for name in PCS_COMPONENT_NAMES:
        if stripped.startswith(name):
            return name
    return None


def extract_pcs_horizontal(section: str) -> List['IceDancePCSComponent']:
    """
    Extract PCS components from a horizontal-format (-layout) skater section.

    Lines look like:
        "       Skating Skills                               0.80    9.75    9.75  ..."
        "       Composition                                  1.33    9.50    9.75  ..."
    Pattern: component_name, then factor float, then 9 judge marks, then trimmed mean.
    """
    import re as _re
    components = []
    for line in section.split('\n'):
        comp_name = _is_pcs_component_line(line)
        if comp_name is None:
            continue
        # Extract all floats from the rest of the line (after the component name)
        rest = line.strip()[len(comp_name):]
        nums = _re.findall(r'[-+]?\d+\.\d+', rest)
        if len(nums) < 2:
            continue
        # First float is factor, then up to 9 judge marks, last is the trimmed mean
        try:
            factor = float(nums[0])
        except ValueError:
            continue
        # The remaining floats: up to 9 judge marks then the trimmed mean (last)
        mark_floats = nums[1:]  # everything after factor
        if len(mark_floats) < 2:
            continue
        # Last value = trimmed mean (panel_avg)
        panel_avg = float(mark_floats[-1])
        # Everything before last = judge marks (up to 9)
        raw_marks = mark_floats[:-1]
        judge_marks = {}
        for j_idx, val_str in enumerate(raw_marks[:9], 1):
            try:
                judge_marks[j_idx] = float(val_str)
            except ValueError:
                pass
        components.append(IceDancePCSComponent(
            component_name=comp_name,
            factor=factor,
            panel_avg=panel_avg,
            judge_marks=judge_marks,
        ))
    return components


def extract_pcs_vertical(block: List[str]) -> List['IceDancePCSComponent']:
    """
    Extract PCS components from a vertical-format (no -layout) skater block.

    The PCS section in vertical format:
      "Program Components"
      "Composition"        <- component names listed one per line
      "Presentation"
      "Skating Skills"
      "Judges Total Program Component Score (factored)"
      [GOE, J1..J9 labels interleaved with element integers]
      "Factor"
      1.33                 <- factor values (n_comp floats)
      1.33
      1.33
      [groups of n_comp floats, one group per judge column]
      "Ref."
      [n_comp trimmed means]
      [total factored PCS]
      "Deductions:"

    Judge mark groups come in batches of n_comp floats separated by blanks,
    one batch per judge (J1..J9 order).
    """
    # Find "Program Components" label
    pc_idx = None
    for i, line in enumerate(block):
        if line.strip() == 'Program Components':
            pc_idx = i
            break
    if pc_idx is None:
        return []

    SKIP_LABELS = {'GOE', 'J1', 'J2', 'J3', 'J4', 'J5', 'J6', 'J7', 'J8', 'J9',
                   'Ref.', 'Ref', 'Factor',
                   'Judges Total Program Component Score (factored)',
                   'Judges Total Program Components Score (factored)',
                   'Total Program Component Score (factored)',
                   '', 'Deductions:', 'Deductions', '#', 'Name', 'NOC', 'Code',
                   'Starting', 'Number', 'Info', 'Rank', 'Base', 'Value',
                   'Executed Elements', '# Executed Elements'}

    # Collect component names listed after "Program Components"
    comp_names = []
    j = pc_idx + 1
    while j < len(block):
        v = block[j].strip()
        if v in SKIP_LABELS:
            j += 1
            break
        if v == '':
            j += 1
            continue
        if 'Judges Total' in v:
            j += 1
            break
        is_comp = any(v.startswith(name) for name in PCS_COMPONENT_NAMES)
        if is_comp:
            comp_names.append(v)
            j += 1
        elif is_float(v) or is_int_only(v):
            break
        else:
            j += 1

    n_comp = len(comp_names)
    if n_comp == 0:
        return []

    # Find "Factor" label after "Program Components"
    factor_idx = None
    for i in range(pc_idx, len(block)):
        if block[i].strip() == 'Factor':
            factor_idx = i
            break
    if factor_idx is None:
        return []

    # Collect factor values (n_comp floats after "Factor")
    factors = []
    k = factor_idx + 1
    while k < len(block) and len(factors) < n_comp:
        v = block[k].strip()
        if v == '':
            k += 1
            continue
        if is_float(v) and not is_int_only(v):
            factors.append(float(v))
            k += 1
        else:
            break

    if len(factors) < n_comp:
        factors.extend([1.33] * (n_comp - len(factors)))

    # After factor values, collect judge mark groups.
    # Groups of n_comp floats, one group per judge (up to 9).
    # Groups may be separated by blank lines.
    judge_mark_groups = []
    while k < len(block) and len(judge_mark_groups) < 9:
        # Skip blanks
        while k < len(block) and block[k].strip() == '':
            k += 1
        if k >= len(block):
            break
        v = block[k].strip()
        # Stop at non-float markers
        if v in ('Ref.', 'Ref', 'Deductions:', 'Deductions', 'Name', 'NOC',
                 'Starting', 'Number', 'Total', 'Program', 'Components'):
            break
        if not is_float(v):
            break
        # Collect n_comp consecutive floats (allowing blanks within group)
        group = []
        g_k = k
        while g_k < len(block) and len(group) < n_comp:
            gv = block[g_k].strip()
            if gv == '':
                g_k += 1
                continue
            if is_float(gv) and not is_int_only(gv):
                group.append(float(gv))
                g_k += 1
            else:
                break
        if len(group) == n_comp:
            judge_mark_groups.append(group)
            k = g_k
        else:
            break

    # Find "Ref." and collect trimmed means
    ref_idx = None
    for i in range(factor_idx, len(block)):
        if block[i].strip() in ('Ref.', 'Ref'):
            ref_idx = i
            break

    panel_avgs = []
    if ref_idx is not None:
        k2 = ref_idx + 1
        while k2 < len(block) and len(panel_avgs) < n_comp:
            v = block[k2].strip()
            if v == '':
                k2 += 1
                continue
            if is_float(v) and not is_int_only(v):
                panel_avgs.append(float(v))
                k2 += 1
            else:
                break

    if len(panel_avgs) < n_comp:
        panel_avgs.extend([0.0] * (n_comp - len(panel_avgs)))

    # Assemble IceDancePCSComponent objects
    components = []
    for ci, comp_name in enumerate(comp_names):
        judge_marks = {}
        for j_idx, group in enumerate(judge_mark_groups, 1):
            if ci < len(group):
                judge_marks[j_idx] = group[ci]
        components.append(IceDancePCSComponent(
            component_name=comp_name,
            factor=factors[ci] if ci < len(factors) else 1.33,
            panel_avg=panel_avgs[ci] if ci < len(panel_avgs) else 0.0,
            judge_marks=judge_marks,
        ))
    return components


# ─────────────────────────────────────────────────────────────────────────────
# FORMAT B: HORIZONTAL PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_horizontal_pdf(pdf_path: str) -> List[IceDancePerformance]:
    """
    Parse Ice Dance PDFs with horizontal (tabular) layout.
    Equivalent to singles/pairs parser format.
    """
    text = pdf_to_text_layout(pdf_path)
    performances = []

    # Split into per-skater sections
    # A skater section starts with a line matching:  "    <rank>   <NAME / NAME>  <NOC>  <start_no>  ..."
    sections = _split_horizontal_sections(text)
    print(f"    Found {len(sections)} horizontal sections")

    for i, section in enumerate(sections):
        perf = _parse_horizontal_section(section)
        if perf:
            performances.append(perf)
        else:
            # Try to get team name for error reporting
            m = re.search(r'\d+\s+([A-Z][A-Za-z\s/]+?)\s+[A-Z]{3}\s+\d+', section[:200])
            name_guess = m.group(1).strip() if m else '?'
            print(f"    ⚠️  Section {i+1} failed (name~'{name_guess}')")

    return performances


def _split_horizontal_sections(text: str) -> List[str]:
    """Split horizontal text into one section per skater.

    Skater header lines look like:
        "       1   Charlene GUIGNARD / Marco FABBRI    ITA    30    84.23    47.38    36.85    0.00"
    Key features:
      - Starts with spaces + integer + spaces
      - Contains " / " (team partner separator) or is a long mixed-case name
      - Has a 3-letter NOC code as one of the tokens
      - Ends with 3-4 floating-point scores
    """
    sections = []
    current = []
    in_skater = False

    for line in text.split('\n'):
        # Candidate: line starts with spaces, then an integer, then spaces, then uppercase
        if re.match(r'^\s{2,}\d+\s+[A-Z]', line) and 'Rank' not in line and 'Executed' not in line:
            parts = line.split()
            # Must be a skater header, not an element line.
            # Skater header has " / " in the name (ice dance teams)
            # AND has a 3-letter NOC code somewhere in the middle
            is_skater_header = False

            # Check for team format: "rank Name / Name NOC start_no tss tes pcs ded"
            if ' / ' in line:
                # Find if there's a 3-letter uppercase token
                has_noc = any(re.match(r'^[A-Z]{3}$', p) for p in parts)
                # And has 3+ numeric values at end
                nums_at_end = sum(1 for p in parts[-5:] if re.match(r'^\d+\.?\d*$', p))
                if has_noc and nums_at_end >= 3:
                    is_skater_header = True

            if is_skater_header:
                if current and in_skater:
                    sections.append('\n'.join(current))
                current = [line]
                in_skater = True
                continue

        if in_skater:
            current.append(line)
            # End of section at deduction line
            if re.match(r'^\s+Deductions:', line):
                sections.append('\n'.join(current))
                current = []
                in_skater = False

    # Don't forget the last section if not terminated
    if current and in_skater:
        sections.append('\n'.join(current))

    return sections


def _parse_horizontal_section(section: str) -> Optional[IceDancePerformance]:
    """Parse one horizontal-format skater section."""
    lines = section.split('\n')
    if not lines:
        return None

    # --- Parse header line ---
    # Pattern: "    <rank>   <Name / Name>   <NOC>   <start_no>   <TSS>   <TES>   <PCS>   <ded>"
    # Ice Dance team names contain " / " (slash with spaces)
    header = None
    for line in lines[:5]:
        # Try ice dance team format first (has " / " in name)
        # Deductions can be negative (e.g., -1.00 for falls)
        m = re.search(
            r'^\s+(\d+)\s+(.+?/\s*.+?)\s+([A-Z]{3})\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(-?[\d.]+)',
            line
        )
        if m:
            header = {
                'rank': int(m.group(1)),
                'name': m.group(2).strip(),
                'noc': m.group(3),
                'start_no': int(m.group(4)),
                'tss': float(m.group(5)),
                'tes': float(m.group(6)),
                'pcs': float(m.group(7)),
                'deductions': float(m.group(8))  # Negative from PDF (e.g. -1.00 for falls)
            }
            break

    if not header:
        return None

    # --- Parse elements ---
    elements = []
    for line in lines:
        # Element lines: "   1   SqTwW4+SqTwM4      7.34    2.86    4  3  4  4  3  3  4  3  4    10.20"
        # Or:            "   1   PSt1                7.45   -0.52    0  1 -1  0  0 -1  0  0  0     6.93"
        # Or (with Info marker): "   5   RoLi4    >    5.30    1.10   3  3  2  2  2  2  3    6.40"
        # Or (with ! marker):   "   7   ChTw1          !       1.10   1.90   2  2  3  3  2  2  3    3.00"
        # Or (with S marker):   "   3   PStW2+PStM2    S       6.96   2.63   1  4  3  3  2  3  3    9.59"
        # Or (with F marker):   "   4   RoLi4           F      5.30   1.90   2  4  5  5  4  4  3    7.20"
        # Or (with !F marker):  "   2   ChSt1           !F     1.10   1.90   2  2  3  3  2  2  3    3.00"
        # Or (with F<< marker): "   3   1MBB+kpYYNN    F<<    4.00  -2.04  -3 -4 -3 -3 -4 -3  -4    1.96"
        # Or (with < marker):   "   1   1MBB+kpNNYN    <      4.00  -0.51   0 -1  0 -1  0 -1  -1    3.49"
        # Or (code ends in >):  "   7   SlLi4+RoLi4>   >     10.90   1.37   1  2  2  2  1  1   1   12.27"
        #   Info column markers: > (bonus), ! (attention), S (separation), F (fall), < / << (under-rotation),
        #   and combinations like !F, F<<. The element code itself may also end in >.
        #   Strategy: strip any trailing > from element code, then skip an optional info token
        #   (any non-digit, non-hyphen token) before the base value.
        m = re.match(r'^\s+(\d+)\s+([A-Za-z0-9+>]+?)\s+(?:[><!A-Z]{1,3}\s+)?([\d.]+)\s+(-?[\d.]+)\s+(.*)', line)
        if m:
            elem_no = int(m.group(1))
            elem_code = m.group(2).rstrip('>')  # Strip trailing > (bonus marker embedded in code)
            base_val = float(m.group(3))
            goe_panel = float(m.group(4))
            rest = m.group(5).split()

            # Parse J1..J9 (up to 9 integers, possibly followed by "Ref." and panel score)
            # Negative GOE values like -1, -2 are valid
            judge_goes = {}
            for j_idx, val in enumerate(rest[:9], 1):
                try:
                    goe_val = int(val)
                    if -5 <= goe_val <= 5:
                        judge_goes[j_idx] = goe_val
                    else:
                        break  # Hit the panel score or ref
                except ValueError:
                    break  # Hit "Ref." or other text

            elements.append(IceDanceElement(
                element_no=elem_no,
                element_code=elem_code,
                base_value=base_val,
                goe_panel=goe_panel,
                judge_goes=judge_goes
            ))

    if not elements:
        return None

    # Extract PCS components from the horizontal section text
    pcs_comps = extract_pcs_horizontal(section)

    return IceDancePerformance(
        rank=header['rank'],
        team_name=header['name'],
        noc=header['noc'],
        start_no=header['start_no'],
        tss=header['tss'],
        tes=header['tes'],
        pcs=header['pcs'],
        deductions=header['deductions'],
        elements=elements,
        pcs_components=pcs_comps,
    )


# ─────────────────────────────────────────────────────────────────────────────
# FORMAT A: VERTICAL PARSER
# ─────────────────────────────────────────────────────────────────────────────

def split_into_blocks(lines: List[str]) -> List[List[str]]:
    """
    Split vertical text into per-skater blocks.
    A block starts when we see a standalone integer AND 'Name' appears within 8 lines.
    """
    block_starts = []
    for i, line in enumerate(lines):
        if not is_int_only(line) or line == '':
            continue
        window = lines[i+1:i+9]
        if 'Name' in window:
            block_starts.append(i)

    if not block_starts:
        return []

    blocks = []
    for idx, start in enumerate(block_starts):
        end = block_starts[idx + 1] if idx + 1 < len(block_starts) else len(lines)
        blocks.append(lines[start:end])

    return blocks


def parse_vertical_block(block: List[str]) -> Optional[IceDancePerformance]:
    """
    Parse one vertical-format skater block.
    Handles multiple sub-variants automatically.
    """
    try:
        rank = int(block[0])
    except (ValueError, IndexError):
        return None

    # --- Detect sub-variant by NOC position ---
    # Variant C (Olympic): has "NOC" / "Code" labels before team name
    # Variant A (standard): has "Nation" label, team name AFTER "Nation"
    # Variant A-new (FC2025 style): has "# Executed Elements" combined, team name right after "Name"

    has_noc_code = 'NOC' in block[:30] and 'Code' in block[:30]
    has_combined_hash = any(l == '# Executed Elements' for l in block[:20])
    has_separate_hash = '#' in block[:20] and 'Executed Elements' not in [block[i] for i in range(min(20, len(block)))]

    if has_noc_code:
        return _parse_olympic_block(block, rank)
    elif has_combined_hash:
        return _parse_new_vertical_block(block, rank)
    else:
        return _parse_old_vertical_block(block, rank)


def _split_olympic_block_into_skaters(block: List[str]) -> List[List[str]]:
    """
    Split an Olympic-format block (which may contain multiple skaters on one page)
    into individual skater sub-blocks.

    In Olympic PDFs (OWG2022, Milano2026), each page has 3 skaters but the page starts
    with shared column headers (Name, NOC Code, Starting Number, ...).
    Each individual skater's data starts with their team name (a line containing "/").

    The structure within a block is:
      [page header labels: Name, NOC, Code, Starting Number, Total Segment Score, etc.]
      TEAM_NAME_1 / PARTNER_NAME_1
      NOC_1
      start_no_1
      tss_1
      tes_1
      pcs_1
      deductions_1
      # (or # Executed Elements)
      Executed Elements   (optional label)
      1, 2, 3, 4, 5
      element_codes...
      Info, Rank, Base, Value, base_values, GOE, judge scores...
      [repeated header labels for next skater]
      TEAM_NAME_2 / PARTNER_NAME_2
      ...
    """
    HEADER_LABELS = {'Name', 'NOC', 'Code', 'Starting', 'Number', 'Total', 'Segment',
                     'Score', 'Element', 'Program', 'Component', 'Score (factored)', 'Deductions',
                     'Total Program', 'Component Score', '(factored)', 'Total Program Component',
                     'Total\nProgram', '#', 'Executed Elements', '# Executed Elements',
                     'Judges Details per Skater', 'Ice Dance', 'Rhythm Dance', 'Free Dance',
                     'Figure Skating', 'Patinage artistique', 'Danse sur glace',
                     'Danse rythmique', 'Danza su ghiaccio', 'Danza ritmica',
                     'Pattinaggio di figura'}

    # Find all team name positions — lines containing " / " with len > 10
    # that are NOT Chinese/French text or program component labels
    CHINESE_FRENCH_MARKERS = {'花样滑冰', '冰上舞蹈', '韵律舞', 'Patinage', 'Danse', 'Danza', 'Pattinaggio'}
    # Program component names that contain "/" (false positives)
    PROGRAM_COMPONENT_MARKERS = {'Interpretation', 'Timing', 'Music', 'Skating Skills',
                                  'Performance', 'Composition', 'Transitions', 'Choreography'}

    team_name_positions = []
    for i, line in enumerate(block):
        v = line.strip()
        if '/' in v and len(v) > 10:
            # Check it's not Chinese/French/Italian text
            is_lang_line = any(m in v for m in CHINESE_FRENCH_MARKERS)
            if is_lang_line:
                continue
            # Check it's not a program component label
            is_component = any(m in v for m in PROGRAM_COMPONENT_MARKERS)
            if is_component:
                continue
            # Check that it's a real team name: first word is all-caps
            # e.g., "PAPADAKIS Gabriella / CIZERON Guillaume"
            first_part = v.split('/')[0].strip()
            first_word = first_part.split()[0] if first_part.split() else ''
            if first_word and first_word.isupper() and len(first_word) > 2:
                team_name_positions.append(i)

    if not team_name_positions:
        return [block]  # Return whole block if no teams found

    # Split block at each team name position, but include enough context before
    # (the header labels that precede each team's data)
    sub_blocks = []
    for idx, pos in enumerate(team_name_positions):
        # Sub-block starts at the team name position
        # Sub-block ends just before the next team name (or end of block)
        end = team_name_positions[idx + 1] if idx + 1 < len(team_name_positions) else len(block)
        sub_blocks.append(block[pos:end])

    return sub_blocks


def _parse_olympic_skater(lines: List[str], rank: int) -> Optional[IceDancePerformance]:
    """
    Parse one skater's data from an Olympic-format sub-block.
    The sub-block starts with the team name line.

    Structure:
      TEAM_NAME / PARTNER_NAME   (line 0)
      blank
      NOC_CODE
      blank
      start_no (int)
      blank
      tss (float)
      blank
      tes (float)
      blank
      pcs (float)
      blank
      deductions (float)
      blank
      # (or # Executed Elements)
      blank
      Executed Elements (optional)
      blank
      1, 2, 3, 4, 5 (element numbers)
      blank
      element_codes...
      Info, Rank, Base, Value
      base_values...
      GOE, J1..J9
      goe_panels...
      judge scores...
    """
    if not lines:
        return None

    team_name = lines[0].strip()
    if '/' not in team_name:
        return None

    HEADER_LABELS = {'Name', 'NOC', 'Code', 'Starting', 'Number', 'Total', 'Segment',
                     'Score', 'Element', 'Program', 'Component', 'Score (factored)', 'Deductions',
                     'Total Program', 'Component Score', '(factored)', 'Total Program Component'}
    ELEM_SKIP = {'Executed Elements', '# Executed Elements', 'Info', 'Rank', 'Name',
                 'NOC', 'Code', 'Starting', 'Number'}
    SKIP_KEYWORDS = {'Info', 'Rank', 'Base', 'Value', 'GOE', 'Program', 'Components',
                     'Factor', 'Executed', 'Elements', 'Deductions', '#', 'Starting',
                     'Number', 'Total', 'Score', '# Executed Elements', 'NOC', 'Code',
                     'Composition', 'Presentation', 'Skating Skills', 'Performance',
                     'Interpretation', 'Ref.', 'Ref', 'Name'}

    j = 1  # Skip team name line
    noc = ''
    start_no = 0
    tss = 0.0
    tes = 0.0
    pcs = 0.0
    deductions = 0.0

    # Find NOC (3-letter uppercase alpha)
    while j < len(lines):
        v = lines[j].strip()
        if v == '' or v in HEADER_LABELS: j += 1; continue
        if len(v) == 3 and v.isupper() and v.isalpha():
            noc = v; j += 1; break
        j += 1

    # Collect 5 numeric values: start_no, tss, tes, pcs, deductions
    score_vals = []
    while j < len(lines) and len(score_vals) < 5:
        v = lines[j].strip()
        if v == '': j += 1; continue
        if v in HEADER_LABELS or v in ('#', '# Executed Elements', 'Executed Elements'): break
        if is_float(v):
            score_vals.append(float(v)); j += 1
        else:
            break

    if len(score_vals) >= 4:
        start_no = int(score_vals[0])
        tss = score_vals[1]; tes = score_vals[2]; pcs = score_vals[3]
        if len(score_vals) >= 5: deductions = score_vals[4]

    # Find "#" or "# Executed Elements"
    hash_j = None
    for k in range(j, len(lines)):
        v = lines[k].strip()
        if v in ('#', '# Executed Elements', 'Executed Elements'):
            hash_j = k; break

    if hash_j is None:
        return None

    # Collect element numbers (skipping "Executed Elements" label)
    k = hash_j + 1
    elem_numbers = []
    while k < len(lines):
        v = lines[k].strip()
        if v == '' or v in ELEM_SKIP: k += 1; continue
        if is_int_only(v) and int(v) == len(elem_numbers) + 1:
            elem_numbers.append(int(v)); k += 1
        else:
            break

    n_elements = len(elem_numbers)
    if n_elements == 0:
        return None

    # Skip blanks
    while k < len(lines) and lines[k].strip() == '': k += 1

    # Collect element codes.
    # Two sub-formats:
    #
    # OWG2022: codes appear DIRECTLY after element numbers
    #   [...elem_numbers...] SqTwW4+... 1MB4+... ... Info Rank Base Value
    #   k now points to first element code (e.g., 'SqTwW4+SqTwM4')
    #
    # Milano2026: a leaked deduction float + Info + Rank labels appear
    #   BETWEEN element numbers and element codes
    #   [...elem_numbers...] 0.00 Info Rank SqTwW4+... 1MB4+... ... Base Value
    #   k now points to '0.00' or 'Info'
    #
    # Detection: if the first non-empty non-blank item at k is a float or
    #   a label word (Info, Rank, etc.), it's Milano2026 style → find 'Rank' first.
    # Otherwise it's OWG2022 style → collect directly.

    elem_codes = []
    first_v = ''
    ki = k
    while ki < len(lines):
        v = lines[ki].strip()
        if v == '': ki += 1; continue
        first_v = v; break

    is_milano_style = (is_float(first_v) or
                       first_v in {'Info', 'Rank', 'Nation', '#', 'Executed Elements'})

    if is_milano_style:
        # Find the 'Rank' label that precedes element codes
        rank_label_idx = None
        for ki2 in range(k, min(k + 30, len(lines))):
            if lines[ki2].strip() == 'Rank':
                rank_label_idx = ki2; break

        if rank_label_idx is not None:
            kc = rank_label_idx + 1
            while kc < len(lines) and len(elem_codes) < n_elements:
                v = lines[kc].strip()
                if v == '': kc += 1; continue
                if v in SKIP_KEYWORDS: kc += 1; continue
                if is_float(v) or is_int_only(v): break
                elem_codes.append(v); kc += 1
        # If no Rank label found, fallthrough to direct collection

    if not elem_codes:
        # Direct collection (OWG2022 style — codes immediately follow element numbers)
        while k < len(lines) and len(elem_codes) < n_elements:
            v = lines[k].strip()
            if v == '': k += 1; continue
            if v in SKIP_KEYWORDS or is_float(v): break
            elem_codes.append(v); k += 1

    # Base values: N floats after "Value" label
    base_values = []
    try:
        val_idx = next(i for i, l in enumerate(lines) if l.strip() == 'Value'
                       and i > 0 and lines[i-1].strip() == 'Base')
        k2 = val_idx + 1
        while k2 < len(lines) and len(base_values) < n_elements:
            v = lines[k2].strip()
            if v == '': k2 += 1; continue
            if is_float(v): base_values.append(float(v))
            else: break
            k2 += 1
    except StopIteration:
        base_values = [0.0] * n_elements

    if len(base_values) < n_elements:
        base_values.extend([0.0] * (n_elements - len(base_values)))

    if len(elem_codes) != n_elements:
        return None

    # GOE panels and judge scores
    goe_panels, judge_goe_blocks = _extract_goe_data(lines, n_elements)

    elements = _assemble_elements(elem_numbers, elem_codes, base_values, goe_panels, judge_goe_blocks)

    pcs_comps = extract_pcs_vertical(lines)

    return IceDancePerformance(
        rank=rank, team_name=team_name, noc=noc,
        start_no=start_no, tss=tss, tes=tes, pcs=pcs, deductions=deductions,
        elements=elements,
        pcs_components=pcs_comps,
    )


def _parse_olympic_block(block: List[str], rank: int) -> Optional[IceDancePerformance]:
    """
    Parse Olympic-format vertical block (single skater wrapper).
    Calls _parse_olympic_skater for the actual parsing.
    NOTE: This function is only used for single-skater-per-block cases now.
    For multi-skater blocks, use parse_olympic_pdf() directly.
    """
    # Split into individual skater sub-blocks
    sub_blocks = _split_olympic_block_into_skaters(block)
    if not sub_blocks:
        return None
    # Parse the first sub-block (the one matching this rank)
    return _parse_olympic_skater(sub_blocks[0], rank)


def _parse_new_vertical_block(block: List[str], rank: int) -> Optional[IceDancePerformance]:
    """
    Parse new-style vertical block (FC2025, EC2025, WC2025 single-skater-per-page).
    Structure:
      rank, blank, "Name", team_name, blank, "# Executed Elements",
      1, 2, 3, 4, 5, blank, "Nation", blank, "Info", blank, "Rank", blank,
      elem_codes..., blank, "Starting", "Number", blank, score_labels...,
      start_no, blank, tss, blank, tes, blank, pcs, blank, noc, "Base", "Value",
      base_values..., blank, "Program Components", blank, "Total Deductions", ded,
      "Ref.", blank, "GOE", blank, J1..J9, blank, goe_panels, judge_blocks...
    """
    # Team name: right after "Name" (possibly with "Nation" label in between)
    # Formats seen:
    #   "Name", blank, team_name               (most common)
    #   "Name", blank, "Nation", blank, team_name  (some EC2025 blocks)
    team_name = None
    try:
        name_idx = block.index('Name')
        SKIP_LABELS = {'Nation', 'Info', 'Rank', '# Executed Elements', '#',
                       'Executed Elements', 'Program Components', 'Starting', 'Number'}
        for j in range(name_idx + 1, min(name_idx + 15, len(block))):
            v = block[j].strip()
            if v == '': continue
            if v in SKIP_LABELS: continue
            # Skip float values (deductions from previous skater)
            if is_float(v) and not '/' in v: continue
            # Skip 3-letter NOC codes
            if len(v) == 3 and v.isupper() and v.isalpha(): continue
            # Accept as team name: contains "/" or is a long mixed-case string
            if '/' in v and len(v) > 5:
                team_name = v
                break
            if len(v) > 8:
                team_name = v
                break
    except ValueError:
        return None

    if not team_name:
        return None

    # Element numbers: right after "# Executed Elements"
    try:
        hash_idx = next(i for i, l in enumerate(block) if l == '# Executed Elements')
    except StopIteration:
        return None

    elem_numbers = []
    j = hash_idx + 1
    while j < len(block):
        v = block[j].strip()
        if v == '': j += 1; continue
        if is_int_only(v) and int(v) == len(elem_numbers) + 1:
            elem_numbers.append(int(v))
            j += 1
        else:
            break

    n_elements = len(elem_numbers)
    if n_elements == 0:
        return None

    # Element codes: appear AFTER the "Nation", "Info", "Rank" labels block
    # In EC2025 new format:  ...elem_numbers..., [deduction_float], blank, "Info", blank, "Rank", blank, [codes]
    # Skip forward until we've passed all the label section (find "Rank" label, then codes follow)
    SKIP_KEYWORDS_LABELS = {'Nation', 'Info', 'Rank', 'Base', 'Value', 'GOE', 'Program', 'Components',
                             'Factor', 'Executed', 'Elements', 'Deductions', '#', 'Starting',
                             'Number', 'Total', 'Score', '# Executed Elements', 'Composition',
                             'Presentation', 'Skating Skills', 'Performance', 'Ref.', 'Ref',
                             'Segment', 'Element', 'Score (factored)', 'Total Deductions',
                             'Total Program Component'}

    # Find the "Rank" label that appears after the element numbers section
    # Element codes appear right after "Rank" label
    rank_label_idx = None
    for k in range(j, min(j + 30, len(block))):
        if block[k] == 'Rank':
            rank_label_idx = k
            # Make sure this is the Rank label after Info (not a score)
            # Verify Info appears somewhere before this
            break

    elem_codes = []
    if rank_label_idx is not None:
        j = rank_label_idx + 1
        while j < len(block) and len(elem_codes) < n_elements:
            v = block[j].strip()
            if v == '': j += 1; continue
            if v in SKIP_KEYWORDS_LABELS:
                j += 1; continue
            if is_float(v) or is_int_only(v): break
            elem_codes.append(v)
            j += 1
    else:
        # Fallback: original approach (skip floats)
        while j < len(block) and len(elem_codes) < n_elements:
            v = block[j].strip()
            if v == '': j += 1; continue
            if v in SKIP_KEYWORDS_LABELS:
                j += 1; continue
            if is_float(v) or is_int_only(v): break
            elem_codes.append(v)
            j += 1

    # NOC: 3-letter code that appears before "Base"/"Value" section
    noc = ''
    try:
        base_idx = next(i for i, l in enumerate(block) if l == 'Value' and i > 0 and block[i-1] == 'Base')
        # NOC is immediately before "Base"
        for k in range(base_idx - 1, max(0, base_idx - 5), -1):
            v = block[k].strip()
            if v == '': continue
            if len(v) == 3 and v.isupper() and v.isalpha():
                noc = v
                break
    except StopIteration:
        pass

    # Scores: start_no, TSS, TES, PCS appear before NOC
    # The pattern in FC2025: after "Score (factored)" label: blank, start_no, blank, tss, blank, tes, blank, pcs
    start_no = 0
    tss = 0.0
    tes = 0.0
    pcs = 0.0
    deductions = 0.0

    try:
        sf_idx = next(i for i, l in enumerate(block) if l == 'Score (factored)')
        score_vals = []
        k = sf_idx + 1
        while k < len(block) and len(score_vals) < 4:
            v = block[k].strip()
            if v == '': k += 1; continue
            if is_float(v):
                score_vals.append(float(v))
            else:
                break
            k += 1
        if len(score_vals) >= 4:
            start_no = int(score_vals[0])
            tss = score_vals[1]
            tes = score_vals[2]
            pcs = score_vals[3]
        elif len(score_vals) == 3:
            tss = score_vals[0]; tes = score_vals[1]; pcs = score_vals[2]
    except StopIteration:
        # Try "(factored)" as separate line
        try:
            fac_idx = next(i for i, l in enumerate(block) if l == '(factored)')
            score_vals = []
            k = fac_idx + 1
            while k < len(block) and len(score_vals) < 4:
                v = block[k].strip()
                if v == '': k += 1; continue
                if is_float(v): score_vals.append(float(v))
                else: break
                k += 1
            if len(score_vals) >= 4:
                start_no = int(score_vals[0]); tss = score_vals[1]; tes = score_vals[2]; pcs = score_vals[3]
            elif len(score_vals) == 3:
                tss = score_vals[0]; tes = score_vals[1]; pcs = score_vals[2]
        except StopIteration:
            pass

    # Deductions
    try:
        ded_idx = next(i for i, l in enumerate(block) if l in ('Total Deductions', 'Deductions:'))
        for k in range(ded_idx + 1, min(ded_idx + 4, len(block))):
            v = block[k].strip()
            if v == '': continue
            if is_float(v): deductions = float(v); break
    except StopIteration:
        pass

    # Base values
    base_values = []
    try:
        val_idx = next(i for i, l in enumerate(block) if l == 'Value' and i > 0 and block[i-1] == 'Base')
        k = val_idx + 1
        while k < len(block) and len(base_values) < n_elements:
            v = block[k].strip()
            if v == '': k += 1; continue
            if is_float(v): base_values.append(float(v))
            else: break
            k += 1
    except StopIteration:
        base_values = [0.0] * n_elements

    if len(base_values) < n_elements:
        base_values.extend([0.0] * (n_elements - len(base_values)))

    if len(elem_codes) != n_elements:
        return None

    # GOE panels and judge scores
    goe_panels, judge_goe_blocks = _extract_goe_data(block, n_elements)

    elements = _assemble_elements(elem_numbers, elem_codes, base_values, goe_panels, judge_goe_blocks)

    pcs_comps = extract_pcs_vertical(block)

    return IceDancePerformance(
        rank=rank, team_name=team_name, noc=noc,
        start_no=start_no, tss=tss, tes=tes, pcs=pcs, deductions=deductions,
        elements=elements,
        pcs_components=pcs_comps,
    )


def _parse_old_vertical_block(block: List[str], rank: int) -> Optional[IceDancePerformance]:
    """
    Parse old-style vertical block (EC/FC/WC 2022, EC/FC/WC/GPF 2023-2024).
    Structure:
      rank, blank, "Name", blank, "Nation", blank, team_name,
      blank, "#", blank, "Executed Elements", blank, 1, 2, 3, 4, 5,
      blank, elem_codes..., blank, "Info", blank, "Rank", blank, "Base", "Value",
      base_values..., blank, "Program Components", blank, NOC, blank, "Starting", "Number",
      blank, score_labels..., start_no, tss, tes, pcs, ...
    """
    team_name = None
    noc = None

    # Team name: first non-empty, non-keyword line after 'Nation' label
    try:
        nation_idx = block.index('Nation')
        for j in range(nation_idx + 1, min(nation_idx + 10, len(block))):
            v = block[j].strip()
            if v == '': continue
            if v in ('#', 'Executed Elements', 'Info', 'Rank', 'Base', 'Value',
                     'Program', 'Components', 'Name', 'Nation', '# Executed Elements'):
                continue
            if len(v) == 3 and v.isupper() and v.isalpha(): continue  # Skip NOC codes
            team_name = v
            break
    except ValueError:
        return None

    if not team_name:
        return None

    # NOC: 3-letter code after 'Program Components' label
    try:
        pc_idx = block.index('Program Components')
        for j in range(pc_idx + 1, min(pc_idx + 6, len(block))):
            v = block[j].strip()
            if v and len(v) == 3 and v.isupper() and v.isalpha():
                noc = v
                break
    except ValueError:
        noc = ''
        # Fallback: first 3-letter uppercase after team name
        if team_name in block:
            tn_idx = block.index(team_name)
            for j in range(tn_idx + 1, min(tn_idx + 60, len(block))):
                v = block[j].strip()
                if v and len(v) == 3 and v.isupper() and v.isalpha():
                    noc = v
                    break

    # Element numbers: after '#' label, skipping 'Executed Elements' label
    elem_numbers = []
    hash_idx = None
    try:
        hash_idx = block.index('#')
    except ValueError:
        try:
            hash_idx = next(i for i, l in enumerate(block) if l == '# Executed Elements')
        except StopIteration:
            pass

    if hash_idx is None:
        return None

    j = hash_idx + 1
    while j < len(block):
        v = block[j].strip()
        if v == '': j += 1; continue
        if is_int_only(v) and int(v) == 1: break
        j += 1  # Skip labels like "Executed Elements"

    while j < len(block) and len(elem_numbers) < 10:
        v = block[j].strip()
        if v == '': j += 1; continue
        if is_int_only(v) and int(v) == len(elem_numbers) + 1:
            elem_numbers.append(int(v)); j += 1
        else:
            break

    n_elements = len(elem_numbers)
    if n_elements == 0:
        return None

    # Element codes: N non-numeric lines after element numbers
    # Skip element numbers first
    j2 = hash_idx + 1
    while j2 < len(block):
        v = block[j2].strip()
        if v == '': j2 += 1; continue
        if is_int_only(v) and int(v) == 1: break
        j2 += 1

    nums_skipped = 0
    while j2 < len(block) and nums_skipped < n_elements:
        v = block[j2].strip()
        if v == '': j2 += 1; continue
        if is_int_only(v): nums_skipped += 1; j2 += 1; continue
        break

    while j2 < len(block) and block[j2].strip() == '':
        j2 += 1

    SKIP_KEYWORDS = {'Info', 'Rank', 'Base', 'Value', 'Name', 'Nation', 'GOE',
                     'Program', 'Components', 'Factor', 'Executed', 'Elements',
                     'Deductions', '#', 'Starting', 'Number', 'Total', 'Score',
                     '# Executed Elements', 'Executed Elements', 'Composition',
                     'Presentation', 'Skating Skills', 'Performance', 'Ref.', 'Ref',
                     'Segment', 'Element', 'Deductions:'}

    elem_codes = []
    while j2 < len(block) and len(elem_codes) < n_elements:
        v = block[j2].strip()
        if v == '': j2 += 1; continue
        if v not in SKIP_KEYWORDS and not is_float(v):
            elem_codes.append(v)
        elif v in SKIP_KEYWORDS:
            j2 += 1; continue
        j2 += 1

    if len(elem_codes) != n_elements:
        return None

    # Base values
    base_values = []
    try:
        val_idx = next(i for i, l in enumerate(block) if l == 'Value' and i > 0 and block[i-1] == 'Base')
        j3 = val_idx + 1
        while j3 < len(block) and len(base_values) < n_elements:
            v = block[j3].strip()
            if v == '': j3 += 1; continue
            if is_float(v): base_values.append(float(v))
            else: break
            j3 += 1
    except StopIteration:
        base_values = [0.0] * n_elements

    if len(base_values) < n_elements:
        base_values.extend([0.0] * (n_elements - len(base_values)))

    # Scores: start_no, TSS, TES, PCS
    start_no = 0; tss = 0.0; tes = 0.0; pcs = 0.0; deductions = 0.0

    # Try "Score (factored)" first
    for sf_label in ('Score (factored)', '(factored)'):
        try:
            sf_idx = next(i for i, l in enumerate(block) if l == sf_label)
            score_vals = []
            k = sf_idx + 1
            while k < len(block) and len(score_vals) < 4:
                v = block[k].strip()
                if v == '': k += 1; continue
                if is_float(v): score_vals.append(float(v))
                else: break
                k += 1
            if len(score_vals) >= 4:
                start_no = int(score_vals[0]); tss = score_vals[1]; tes = score_vals[2]; pcs = score_vals[3]
                break
            elif len(score_vals) == 3:
                tss = score_vals[0]; tes = score_vals[1]; pcs = score_vals[2]
                break
        except StopIteration:
            continue

    # Starting Number fallback
    if start_no == 0:
        try:
            num_idx = next(i for i, l in enumerate(block) if l == 'Number' and i > 0 and block[i-1] == 'Starting')
            k = num_idx + 1
            while k < len(block):
                v = block[k].strip()
                if v == '': k += 1; continue
                if is_int_only(v): start_no = int(v); break
                k += 1
        except StopIteration:
            pass

    # Deductions
    try:
        ded_idx = next(i for i, l in enumerate(block) if l in ('Deductions:', 'Total Deductions'))
        for k in range(ded_idx + 1, min(ded_idx + 5, len(block))):
            v = block[k].strip()
            if v == '': continue
            if is_float(v): deductions = float(v); break
    except StopIteration:
        pass

    # GOE panels and judge scores
    goe_panels, judge_goe_blocks = _extract_goe_data(block, n_elements)

    elements = _assemble_elements(elem_numbers, elem_codes, base_values, goe_panels, judge_goe_blocks)

    pcs_comps = extract_pcs_vertical(block)

    return IceDancePerformance(
        rank=rank, team_name=team_name, noc=noc or '',
        start_no=start_no, tss=tss, tes=tes, pcs=pcs, deductions=deductions,
        elements=elements,
        pcs_components=pcs_comps,
    )


def _extract_goe_data(block: List[str], n_elements: int) -> Tuple[List[float], List[List[int]]]:
    """
    Extract GOE panel averages and per-judge GOE integer arrays from a block.
    Works for all vertical format variants.
    """
    GOE_SKIP = {'J1','J2','J3','J4','J5','J6','J7','J8','J9','Ref.','Ref',
                'Scores of', 'Panel', 'Ref Scores of'}

    goe_panels = []
    judge_goe_blocks = []

    try:
        goe_idx = block.index('GOE')
    except ValueError:
        return goe_panels, judge_goe_blocks

    j = goe_idx + 1
    # Skip J1..J9 labels
    while j < len(block):
        v = block[j].strip()
        if v == '' or v in GOE_SKIP: j += 1; continue
        break

    # Collect N GOE panel floats (non-integer floats)
    while j < len(block) and len(goe_panels) < n_elements:
        v = block[j].strip()
        if v == '': j += 1; continue
        if is_float(v) and not is_int_only(v):
            goe_panels.append(float(v)); j += 1
        elif is_int_only(v) and -5 <= int(v) <= 5:
            break  # Hit judge scores already
        else:
            break

    if len(goe_panels) < n_elements:
        goe_panels.extend([0.0] * (n_elements - len(goe_panels)))

    # Collect 9 judge GOE blocks (each N integers)
    while j < len(block) and len(judge_goe_blocks) < 9:
        while j < len(block) and block[j].strip() == '':
            j += 1
        if j >= len(block):
            break

        int_block = []
        k = j
        while k < len(block) and len(int_block) < n_elements:
            v = block[k].strip()
            if v == '': break
            if is_int_only(v):
                val = int(v)
                if -5 <= val <= 5:
                    int_block.append(val); k += 1
                else:
                    break
            else:
                break

        if len(int_block) == n_elements:
            judge_goe_blocks.append(int_block)
            j = k
        else:
            j = k + 1

    return goe_panels, judge_goe_blocks


def _assemble_elements(
    elem_numbers: List[int],
    elem_codes: List[str],
    base_values: List[float],
    goe_panels: List[float],
    judge_goe_blocks: List[List[int]]
) -> List[IceDanceElement]:
    """Assemble element objects from parsed components."""
    elements = []
    n = len(elem_numbers)
    for idx in range(n):
        judge_goes = {}
        for j_num in range(1, 10):
            if j_num - 1 < len(judge_goe_blocks):
                blk = judge_goe_blocks[j_num - 1]
                if idx < len(blk):
                    judge_goes[j_num] = blk[idx]

        elements.append(IceDanceElement(
            element_no=elem_numbers[idx],
            element_code=elem_codes[idx],
            base_value=base_values[idx],
            goe_panel=goe_panels[idx] if idx < len(goe_panels) else 0.0,
            judge_goes=judge_goes
        ))
    return elements


# ─────────────────────────────────────────────────────────────────────────────
# TOP-LEVEL PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_ice_dance_pdf(pdf_path: str, fmt: str = None) -> List[IceDancePerformance]:
    """Auto-detect format and parse Ice Dance PDF.

    Args:
        pdf_path: Path to the PDF file
        fmt: Optional format override: 'horizontal', 'vertical', or None (auto-detect)
    """
    if fmt is None:
        fmt = detect_format_from_pdf(pdf_path)
    print(f"    Format: {fmt}")

    if fmt == 'horizontal':
        return parse_horizontal_pdf(pdf_path)
    else:
        # Vertical: split into blocks then parse each
        raw_text = pdf_to_text_raw(pdf_path)
        lines = [l.strip() for l in raw_text.split('\n')]
        blocks = split_into_blocks(lines)
        print(f"    Found {len(blocks)} vertical blocks")

        # Detect if this is an Olympic format by checking first block
        is_olympic = (len(blocks) > 0 and
                      'NOC' in blocks[0][:30] and 'Code' in blocks[0][:30])

        performances = []
        if is_olympic:
            # Olympic PDFs have multiple skaters per block.
            # Extract all skater sub-blocks across all page blocks.
            all_sub_blocks = []
            for block in blocks:
                sub_blocks = _split_olympic_block_into_skaters(block)
                all_sub_blocks.extend(sub_blocks)

            print(f"    Olympic format: {len(all_sub_blocks)} skater sub-blocks across {len(blocks)} page blocks")

            for i, sub_block in enumerate(all_sub_blocks):
                # Use unified Olympic skater parser (handles both OWG2022 and Milano2026 styles)
                perf = _parse_olympic_skater(sub_block, i + 1)
                if perf:
                    performances.append(perf)
                else:
                    name_guess = sub_block[0].strip() if sub_block else '?'
                    print(f"    ⚠️  Sub-block {i+1} failed (name~'{name_guess[:40]}')")

            # Fix ranks: sort by TSS descending, assign ranks 1..N
            if performances:
                performances.sort(key=lambda p: p.tss, reverse=True)
                for idx, perf in enumerate(performances):
                    perf.rank = idx + 1
        else:
            for i, block in enumerate(blocks):
                perf = parse_vertical_block(block)
                if perf:
                    performances.append(perf)
                else:
                    name_guess = next((l for l in block if '/' in l or
                                       (l and l[0].isupper() and len(l) > 5)), '?')
                    print(f"    ⚠️  Block {i+1} failed (name~'{name_guess}')")

        return performances


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE POPULATION
# ─────────────────────────────────────────────────────────────────────────────

def load_judges_from_txt(txt_path: str, event_id: int, db_path: str) -> int:
    """Load judge names from panel_judges.txt file into the judges table."""
    if not Path(txt_path).exists():
        return 0

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Delete existing (possibly generic) judges for this event
    cursor.execute("DELETE FROM judges WHERE event_id = ?", (event_id,))

    judges_loaded = 0
    with open(txt_path) as f:
        for line in f:
            line = line.strip()
            # Pattern: "J1: Mr. Name SURNAME" or "J1: Ms. Name SURNAME"
            m = re.match(r'^(J[1-9]):\s+(?:Mr\.|Ms\.|Dr\.)?\s*(.+)$', line)
            if m:
                pos = m.group(1)
                name = m.group(2).strip()
                cursor.execute("""
                    INSERT OR REPLACE INTO judges (event_id, judge_position, judge_name)
                    VALUES (?, ?, ?)
                """, (event_id, pos, name))
                judges_loaded += 1

    conn.commit()
    conn.close()
    return judges_loaded


def populate_ice_dance_event(pdf_path: str, event_id: int, db_path: str,
                              judges_txt: str = None, fmt: str = None) -> int:
    """Parse PDF and populate database for one Ice Dance event."""
    print(f"  Parsing: {Path(pdf_path).name}")

    # Load judges from txt if provided and missing
    if judges_txt:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM judges WHERE event_id = ?", (event_id,))
        n_judges = cursor.fetchone()[0]
        conn.close()
        if n_judges == 0:
            n = load_judges_from_txt(judges_txt, event_id, db_path)
            if n > 0:
                print(f"    Loaded {n} judges from {Path(judges_txt).name}")

    performances = parse_ice_dance_pdf(pdf_path, fmt=fmt)

    if not performances:
        print(f"  ❌ No performances parsed")
        return 0

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get judges for this event
    cursor.execute("""
        SELECT judge_id, judge_position FROM judges WHERE event_id = ?
        ORDER BY judge_position
    """, (event_id,))
    judges = {pos: jid for jid, pos in cursor.fetchall()}

    # Clear existing entries
    cursor.execute("""
        DELETE FROM element_judge_scores WHERE element_id IN (
            SELECT el.element_id FROM elements el
            JOIN entries e ON el.entry_id = e.entry_id
            WHERE e.event_id = ?
        )
    """, (event_id,))
    cursor.execute("""
        DELETE FROM elements WHERE entry_id IN (
            SELECT entry_id FROM entries WHERE event_id = ?
        )
    """, (event_id,))
    cursor.execute("DELETE FROM entries WHERE event_id = ?", (event_id,))

    inserted = 0
    scores_inserted = 0
    for perf in performances:
        cursor.execute("""
            INSERT INTO entries (event_id, team_name, noc, start_no, rank, tes, pcs, deductions, tss)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (event_id, perf.team_name, perf.noc, perf.start_no,
              perf.rank, perf.tes, perf.pcs, perf.deductions, perf.tss))
        entry_id = cursor.lastrowid
        inserted += 1

        for elem in perf.elements:
            cursor.execute("""
                INSERT INTO elements (entry_id, element_no, element_code, base_value, panel_goe_points)
                VALUES (?, ?, ?, ?, ?)
            """, (entry_id, elem.element_no, elem.element_code,
                  elem.base_value, elem.goe_panel))
            element_id = cursor.lastrowid

            for j_num, goe_int in elem.judge_goes.items():
                j_pos = f'J{j_num}'
                judge_id = judges.get(j_pos)
                if judge_id:
                    cursor.execute("""
                        INSERT OR REPLACE INTO element_judge_scores
                        (element_id, judge_id, judge_goe_int)
                        VALUES (?, ?, ?)
                    """, (element_id, judge_id, goe_int))
                    scores_inserted += 1

    # ── Insert PCS components and judge marks ────────────────────────────────
    pcs_comps_inserted = 0
    pcs_scores_inserted = 0

    # Re-fetch entry_ids (entries were just re-inserted above)
    cursor.execute(
        "SELECT entry_id, start_no, rank FROM entries WHERE event_id = ?",
        (event_id,)
    )
    entry_map = {(row[1], row[2]): row[0] for row in cursor.fetchall()}

    for perf in performances:
        eid = entry_map.get((perf.start_no, perf.rank))
        if eid is None:
            # Fallback: match by team_name
            cursor.execute(
                "SELECT entry_id FROM entries WHERE event_id = ? AND team_name = ?",
                (event_id, perf.team_name)
            )
            row = cursor.fetchone()
            eid = row[0] if row else None
        if eid is None:
            continue

        for comp in perf.pcs_components:
            cursor.execute("""
                INSERT INTO pcs_components (entry_id, component_name, factor, panel_component_avg)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(entry_id, component_name) DO UPDATE SET
                    factor = excluded.factor,
                    panel_component_avg = excluded.panel_component_avg
            """, (eid, comp.component_name, comp.factor, comp.panel_avg))
            cursor.execute(
                "SELECT pcs_id FROM pcs_components WHERE entry_id = ? AND component_name = ?",
                (eid, comp.component_name)
            )
            pcs_row = cursor.fetchone()
            if not pcs_row:
                continue
            pcs_id = pcs_row[0]
            pcs_comps_inserted += 1

            for j_num, mark in comp.judge_marks.items():
                j_pos = f'J{j_num}'
                judge_id = judges.get(j_pos)
                if judge_id:
                    cursor.execute("""
                        INSERT INTO pcs_judge_scores (pcs_id, judge_id, judge_mark)
                        VALUES (?, ?, ?)
                        ON CONFLICT(pcs_id, judge_id) DO UPDATE SET
                            judge_mark = excluded.judge_mark
                    """, (pcs_id, judge_id, mark))
                    pcs_scores_inserted += 1

    conn.commit()
    conn.close()

    n_elems = sum(len(p.elements) for p in performances)
    full_cov = sum(1 for p in performances for e in p.elements if len(e.judge_goes) == 9)
    print(f"  OK {inserted} performances | {n_elems} elements | "
          f"{scores_inserted} GOE scores | {pcs_comps_inserted} PCS comps | "
          f"{pcs_scores_inserted} PCS judge scores | {full_cov}/{n_elems} full 9-judge")
    return inserted


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    DB_PATH = 'figure_skating_ijs_seed.sqlite'
    PDF_BASE = 'figure_skating_seed_bundle/isu_pdfs'

    # (comp_name_LIKE, segment, pdf_dir, pdf_file, judges_txt_or_None, fmt_override)
    #
    # fmt_override values:
    #   'vertical'   — single-column vertical dump (no -layout); sub-variant auto-detected
    #                  old (# / Executed Elements separate): EC/FC/WC 2022, EC/FC/GPF2022/23,
    #                                                        EC/FC/GPF2023/24, WC2024
    #                  new (# Executed Elements combined): GPF2024/25, EC/FC/WC2025
    #                  olympic (NOC Code header): OWG2022, Milano2026
    #   'horizontal' — tabular multi-column layout (-layout flag): WC2023 only
    ICE_DANCE_EVENTS = [
        # ── 2021/22 ──────────────────────────────────────────────────────────
        # All events use 'horizontal' (-layout) parser: better team coverage and full 9-judge scores.
        ('%European%2022%',             'Rhythm Dance', 'ec2022',    'SEG007_JudgesDetails.pdf', None,       'horizontal'),
        ('%European%2022%',             'Free Dance',   'ec2022',    'SEG008_JudgesDetails.pdf', None,       'horizontal'),
        ('%Four Continents%2022%',      'Rhythm Dance', 'fc2022',    'SEG007_JudgesDetails.pdf', None,       'horizontal'),
        ('%Four Continents%2022%',      'Free Dance',   'fc2022',    'SEG008_JudgesDetails.pdf', None,       'horizontal'),
        ('%World%2022%',                'Rhythm Dance', 'wc2022',    'SEG007_JudgesDetails.pdf', None,       'horizontal'),
        ('%World%2022%',                'Free Dance',   'wc2022',    'SEG008_JudgesDetails.pdf', None,       'horizontal'),
        ('%Olympic Winter Games 2022%', 'Rhythm Dance', 'owg2022',   'SEG007_JudgesDetails.pdf', None,       'horizontal'),
        ('%Olympic Winter Games 2022%', 'Free Dance',   'owg2022',   'SEG008_JudgesDetails.pdf', None,       'horizontal'),
        # ── 2022/23 ──────────────────────────────────────────────────────────
        ('%European%2023%',             'Rhythm Dance', 'ec2023',    'SEG007_JudgesDetails.pdf', None,       'horizontal'),
        ('%European%2023%',             'Free Dance',   'ec2023',    'SEG008_JudgesDetails.pdf', None,       'horizontal'),
        ('%Four Continents%2023%',      'Rhythm Dance', 'fc2023',    'SEG007_JudgesDetails.pdf', None,       'horizontal'),
        ('%Four Continents%2023%',      'Free Dance',   'fc2023',    'SEG008_JudgesDetails.pdf', None,       'horizontal'),
        ('%Grand Prix%2022/23%',        'Rhythm Dance', 'gpf2022',   'SEG007_JudgesDetails.pdf', None,       'horizontal'),
        ('%Grand Prix%2022/23%',        'Free Dance',   'gpf2022',   'SEG008_JudgesDetails.pdf', None,       'horizontal'),
        ('%World%2023%',                'Rhythm Dance', 'wc2023',    'SEG007_JudgesDetails.pdf', None,       'horizontal'),
        ('%World%2023%',                'Free Dance',   'wc2023',    'SEG008_JudgesDetails.pdf', None,       'horizontal'),
        # ── 2023/24 ──────────────────────────────────────────────────────────
        ('%European%2024%',             'Rhythm Dance', 'ec2024',    'SEG007_JudgesDetails.pdf', None,       'horizontal'),
        ('%European%2024%',             'Free Dance',   'ec2024',    'SEG008_JudgesDetails.pdf', None,       'horizontal'),
        ('%Four Continents%2024%',      'Rhythm Dance', 'fc2024',    'SEG007_JudgesDetails.pdf', None,       'horizontal'),
        ('%Four Continents%2024%',      'Free Dance',   'fc2024',    'SEG008_JudgesDetails.pdf', None,       'horizontal'),
        ('%Grand Prix%2023/24%',        'Rhythm Dance', 'gpf2023',   'SEG007_JudgesDetails.pdf', None,       'horizontal'),
        ('%Grand Prix%2023/24%',        'Free Dance',   'gpf2023',   'SEG008_JudgesDetails.pdf', None,       'horizontal'),
        ('%World%2024%',                'Rhythm Dance', 'wc2024',    'SEG007_JudgesDetails.pdf',
         'figure_skating_seed_bundle/isu_pdfs/wc2024/SEG007OF_panel_judges.txt',                            'horizontal'),
        ('%World%2024%',                'Free Dance',   'wc2024',    'SEG008_JudgesDetails.pdf',
         'figure_skating_seed_bundle/isu_pdfs/wc2024/SEG008OF_panel_judges.txt',                            'horizontal'),
        # ── 2024/25 ──────────────────────────────────────────────────────────
        ('%European%2025%',             'Rhythm Dance', 'ec2025',    'SEG007_JudgesDetails.pdf', None,       'horizontal'),
        ('%European%2025%',             'Free Dance',   'ec2025',    'SEG008_JudgesDetails.pdf', None,       'horizontal'),
        ('%Four Continents%2025%',      'Rhythm Dance', 'fc2025',    'SEG007_JudgesDetails.pdf', None,       'horizontal'),
        ('%Four Continents%2025%',      'Free Dance',   'fc2025',    'SEG008_JudgesDetails.pdf', None,       'horizontal'),
        ('%Grand Prix%2024/25%',        'Rhythm Dance', 'gpf2024',   'SEG007_JudgesDetails.pdf', None,       'horizontal'),
        ('%Grand Prix%2024/25%',        'Free Dance',   'gpf2024',   'SEG008_JudgesDetails.pdf', None,       'horizontal'),
        ('%World%2025%',                'Rhythm Dance', 'wc2025',    'SEG007_JudgesDetails.pdf', None,       'horizontal'),
        ('%World%2025%',                'Free Dance',   'wc2025',    'SEG008_JudgesDetails.pdf', None,       'horizontal'),
        # ── 2025/26 ──────────────────────────────────────────────────────────
        ('%Milano%',                    'Rhythm Dance', 'milano2026','SEG007_JudgesDetails.pdf', None,       'horizontal'),
        ('%Milano%',                    'Free Dance',   'milano2026','SEG008_JudgesDetails.pdf', None,       'horizontal'),
    ]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\n" + "="*60)
    print("ICE DANCE ELEMENT RE-PARSER (Unified Multi-Format)")
    print("="*60)

    total_events = 0
    failed = []

    for comp_frag, segment, pdf_dir, pdf_file, judges_txt, fmt in ICE_DANCE_EVENTS:
        cursor.execute("""
            SELECT ev.event_id, c.name FROM events ev
            JOIN competitions c ON ev.competition_id = c.competition_id
            WHERE c.name LIKE ? AND ev.discipline = 'Ice Dance' AND ev.segment = ?
        """, (comp_frag, segment))
        row = cursor.fetchone()

        if not row:
            print(f"\n⚠️  No event: {comp_frag} / {segment}")
            failed.append(f"No event: {comp_frag} / {segment}")
            continue

        event_id, comp_name = row
        pdf_path = f'{PDF_BASE}/{pdf_dir}/{pdf_file}'
        judges_path = judges_txt  # May be None

        print(f"\n{'─'*60}")
        print(f"{comp_name} — {segment} (event_id={event_id})")

        if not Path(pdf_path).exists():
            print(f"  ❌ PDF not found: {pdf_path}")
            failed.append(f"PDF missing: {pdf_path}")
            continue

        n = populate_ice_dance_event(pdf_path, event_id, DB_PATH, judges_txt=judges_path, fmt=fmt)
        if n > 0:
            total_events += 1
        else:
            failed.append(f"No data: {comp_name} {segment}")

    conn.close()

    print("\n" + "="*60)
    print(f"✅ Successfully parsed {total_events}/{len(ICE_DANCE_EVENTS)} Ice Dance events")
    if failed:
        print(f"⚠️  {len(failed)} issues:")
        for f in failed:
            print(f"   - {f}")
    print("="*60)


if __name__ == '__main__':
    import os
    os.chdir('/Users/allman/Library/CloudStorage/Dropbox/Dropbox Mike/Judging Bias')
    main()
