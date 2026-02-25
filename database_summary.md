# Figure Skating Judging Bias — Database Summary

**Primary analysis database:** `figure_skating_ijs_seed.sqlite` (ISU-impact results)
**Canonical source database:** `figure_skating_ijs_v3.sqlite` (entries, elements, LOJO)
**Location:** Judging Bias folder
**Prepared by:** Michael Allman
**Updated:** February 2026 (see Two-Database Architecture section)

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
| Events (discipline × segment combinations) | 144 |
| Skater/pair performances (entries) | 2,706 |
| Individual elements parsed | 23,043 |
| Individual judge scores (GOE + PCS combined) | 291,604 |
| Pairwise comparisons (ISU-impact, seed.sqlite) | 271,728 |
| Judges (unique per event) | 1,278+ |

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
| Women Single Skating | 32 |
| Pair Skating | 33 |
| Ice Dance | 34 |
| Team Event (Men, Women, Pairs, Ice Dance) | 8 |

---

## What Is Stored

The database contains the following tables:

**`competitions`** — one row per competition (name, year, venue).

**`events`** — one row per discipline × segment within a competition (e.g., WC2025 Women Short Program).

**`entries`** — one row per skater or pair performance, with total segment score (TSS), total element score (TES), program component score (PCS), deductions, rank, and start number.

**`judges`** — one row per judge position (J1–J9) per event, with judge name and country code where available from the scoring sheet panel header.

**`elements`** — one row per executed element, with element code, base value, panel GOE, and panel element score.

**`element_judge_scores`** — one row per judge per element: the individual GOE integer (–5 to +5) awarded by each judge. This is the primary data for bias analysis.

**`pcs_components`** — one row per program component (e.g., Skating Skills, Composition) per entry, with the component factor and panel average mark.

**`pcs_judge_scores`** — one row per judge per component: the individual mark awarded by each judge, on a scale of 0.25 to 10.00 in quarter-point increments.

**`judge_event_statistics`** — summary bias statistics (bias z-score, element count) per judge per event, computed by `calculate_statistics.py`. Contains 1,269 rows.

**`judge_entry_totals`** — per-judge per-entry aggregated GOE and PCS totals, used as inputs to the pairwise analysis.

**`pairwise_judge_statistics`** — output of the deprecated B(j) pairwise test (in `v3.sqlite`). One row per judge × pair of competitors per event. Contains 269,957 rows. **⚠️ DEPRECATED** — B(j) test has an exchangeability flaw (inflation ~560×); see `methodology_diagnosis_v1.md`.

**`pairwise_impact_results`** — core output of the current ISU-impact method (in `seed.sqlite`). 271,728 rows across 142 events. Contains bias_points, p_value, q_value_bh for each judge × pair × event.

**`judge_team_impacts`** — per-judge per-team impact summary (in `seed.sqlite`). 24,174 rows.

---

## Two-Database Architecture (as of February 2026)

| Database | Size | Use for |
|----------|------|---------|
| `figure_skating_ijs_v3.sqlite` | 104 MB | Canonical source data: entries, elements, GOE/PCS scores, LOJO results, deprecated B(j) pairwise |
| `figure_skating_ijs_seed.sqlite` | 192 MB | ISU-impact results: pairwise_impact_results (271,728 rows), judge_team_impacts (24,174 rows), goe_factors, sources |

**Use `seed.sqlite` for all new analyses.** `v3.sqlite` is retained for LOJO queries and legacy reference.

---

## Key Design Decisions

- **Event-local analysis only.** All statistics are computed within a single event's judging panel. No cross-competition judge identity linking is performed at this stage.
- **No judge identity linking across events.** Judges are identified by position (J1–J9) within each event. Name and country are stored where available but not used to merge records across events.
- **Source fidelity.** All scores are taken directly from the ISU official published scoring sheets. No imputation or estimation is performed. Where a judge score is absent (e.g., a skater withdrew mid-program), only the elements actually scored are stored.
- **Reproducible.** The full parsing pipeline (`parse_ice_dance.py`, `parse_singles_pairs.py`) and analysis scripts (`calculate_statistics.py`, `calculate_pairwise_statistics_v3.py`) are retained alongside the database and can re-generate all results from the original PDFs.
