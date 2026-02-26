# Figure Skating Judging Bias — Database Summary

**Database:** `figure_skating_ijs_v4.sqlite` (~100 MB) — single canonical database
**Location:** Judging Bias folder
**Prepared by:** Michael Allman
**Updated:** February 2026

---

## What We Did

ISU "Judges Details per Skater" scoring sheets were downloaded as PDFs from the ISU's official results website for all major international figure skating competitions from 2022 through 2026. These PDFs are the authoritative public record of every judge's individual score for every element and program component in every event.

Two custom Python parsers were written to extract the data — one for Ice Dance, one for Men's Singles, Women's Singles, and Pair Skating — using a regex-based line parsing approach that handles all known ISU scoring format variants, including variable judge panel sizes (8 or 9 judges), the pre- and post-2022/23 program component score formats (5-component and 3-component), the credit highlight distribution bonus marker (x), and all combinations of technical call markers (<, <<, q, !, e, F, *, and their combined forms using | or , separators introduced in the 2024/25 season).

Data integrity was verified using a TES reconstruction check: for every entry, the sum of all parsed individual element panel scores was compared against the stored total element score. The result was a **100% pass rate across all 2,005 non-Ice Dance entries**, confirming that no elements were missed or mis-parsed. Ice Dance data was verified separately.

---

## Coverage

| Category | Count |
|---|---|
| Competitions | 17 |
| Events (discipline × segment combinations) | 144 (142 analyzed) |
| Skater/pair performances (entries) | 2,706 |
| Individual elements parsed | 23,043 |
| Individual judge GOE scores | 206,682 |
| Individual judge PCS scores (ice dance only) | 84,922 |
| Pairwise bias tests (ISU-impact) | 271,728 |
| Judge panels | 1,305 |

### Competitions Covered

| Competition | Years |
|---|---|
| ISU World Figure Skating Championships | 2022, 2023, 2024, 2025 |
| Olympic Winter Games | 2022 (Beijing), 2026 (Milano–Cortina) |
| ISU European Figure Skating Championships | 2022, 2023, 2024, 2025 |
| ISU Four Continents Figure Skating Championships | 2022, 2023, 2024, 2025 |
| ISU Grand Prix of Figure Skating Final | 2022/23 (Turin), 2023/24 (Beijing), 2024/25 (Grenoble) |

### Disciplines Covered

| Discipline | Events |
|---|---|
| Men Single Skating | 34 |
| Women Single Skating | 34 |
| Pair Skating | 34 |
| Ice Dance | 34 |
| Team Event (Men, Women, Pairs, Ice Dance) | 8 |

---

## What Is Stored

The database (`figure_skating_ijs_v4.sqlite`) contains 14 tables in three categories:

### Source tables (extracted from ISU official documents)

**`competitions`** — one row per competition (name, season, venue). 17 rows.

**`events`** — one row per discipline × segment within a competition (e.g., OWG 2026 Ice Dance Free Dance). 144 rows.

**`entries`** — one row per skater or pair performance, with TSS, TES, PCS, deductions, rank, and start number. 2,706 rows.

**`judges`** — one row per judge position (J1–J9) per event, with judge name and country code. 1,305 rows.

**`elements`** — one row per executed element, with element code, base value, panel GOE, and panel element score. 23,043 rows.

**`element_judge_scores`** — one row per judge per element: the individual GOE integer (−5 to +5) awarded by each judge. This is the primary data for bias analysis. 206,682 rows.

**`pcs_components`** — one row per program component per entry (e.g., Skating Skills), with factor and panel average mark. 9,458 rows.

**`pcs_judge_scores`** — one row per judge per component: the individual PCS mark (ice dance only). 84,922 rows.

**`sources`** — source document registry with URL, SHA-256 checksum, and retrieval timestamp for every ISU PDF and HTML file downloaded. 239 rows.

### Reference tables

**`goe_factors`** — official ISU GOE point-conversion factors by element type and season, compiled from ISU Communication 2705. 17 rows.

### Derived tables (computed by analysis scripts)

**`lojo_scores`** — Leave-One-Judge-Out counterfactual results: recalculated TSS and rank for every entry with each judge excluded. Computed by `calculate_lojo_full.py`. 24,269 rows.

**`lojo_event_summary`** — per-judge per-event LOJO summary: winner changes, podium changes, rank inversions, Kendall tau distance. 1,288 rows.

**`pairwise_impact_results`** — core output of the ISU-impact method. One row per judge × ordered pair of entries × event. Contains `bias_points`, `p_value`, `q_value_bh`. Computed by `calculate_isuimpact_v1.py` with M = 10,000 permutations, seed = 20260223, global CDF. 271,728 rows across 142 events.

**`judge_team_impacts`** — per-judge per-entry aggregated ISU-impact scores: net bias points each judge contributed toward each entry. 24,174 rows.

---

## Key Design Decisions

- **Event-local analysis only.** All statistics are computed within a single event's judging panel. No cross-competition judge identity linking is performed at this stage.
- **No judge identity linking across events.** Judges are identified by position (J1–J9) within each event. Name and country are stored where available but not used to merge records across events.
- **Source fidelity.** All scores are taken directly from the ISU official published scoring sheets. No imputation or estimation is performed. Where a judge score is absent (e.g., a skater withdrew mid-program), only the elements actually scored are stored.
- **Reproducible.** The full parsing pipeline (`parse_ice_dance.py`, `parse_singles_pairs.py`) and analysis scripts (`calculate_lojo_full.py`, `calculate_isuimpact_v1.py`, `build_complete_event_workbook.py`) are retained alongside the database and can re-generate all results from the original PDFs.
