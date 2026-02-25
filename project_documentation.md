> ⚠️ **DEPRECATION NOTICE (February 2026)**
> The B(j) pairwise test described throughout this document has a known exchangeability
> violation (inflation factor ~560×). See `methodology_diagnosis_v1.md` for full details.
> **Current primary method:** ISU-impact (`calculate_isuimpact_v1.py`, `seed.sqlite`).
> This document is retained for historical reference only.

---

# Project Documentation: Judging Bias in Competitive Figure Skating
## A Complete Record of What Was Built, How, and What Was Found

**Author:** Michael Allman, MBA
**Project:** Detecting and Remedying Anomalous Judging in Competitive Figure Skating
**Date:** February 2026

---

## 1. Project Overview

This project builds a complete, reproducible statistical audit framework for detecting anomalous judging in ISU-sanctioned figure skating competitions. Starting from publicly available ISU scoring PDFs, the project constructs a structured database, runs permutation-based statistical tests across all competitor pairs in all events, computes leave-one-judge-out counterfactuals, and produces the empirical foundation for an academic paper proposing the Outlier Score Nullification Rule (OSNR).

The entire pipeline — from raw PDF to final p-value — is implemented in Python and SQLite, using only freely available tools, and is fully reproducible from the source files.

---

## 2. Data Sources

### 2.1 What Was Collected

All data come from the ISU's official results website. The ISU publishes, for every sanctioned international competition, a "Judges Details per Skater" PDF for each event segment. These PDFs are the authoritative public record of every judge's individual GOE score for every technical element, and every judge's individual mark for every program component, for every competitor in the event.

### 2.2 Coverage

| Competition | Years Collected |
|---|---|
| ISU World Figure Skating Championships | 2022, 2023, 2024, 2025 |
| Olympic Winter Games | 2022 (Beijing), 2026 (Milano–Cortina) |
| ISU European Figure Skating Championships | 2022, 2023, 2024, 2025 |
| ISU Four Continents Figure Skating Championships | 2022, 2023, 2024, 2025 |
| ISU Grand Prix of Figure Skating Final | 2022/23, 2023/24, 2024/25 |

**Total: 17 competitions, spanning the 2021/22 through 2025/26 seasons.**

### 2.3 Disciplines

Four disciplines: Men's Singles, Women's Singles, Pair Skating, Ice Dance. Each has two segments (Short Program / Rhythm Dance; Free Skating / Free Dance). Eight additional Team Event segments from OWG2026 are stored in the database but excluded from the primary analysis.

---

## 3. Database Construction

### 3.1 Schema

The data are stored in a relational SQLite database: `figure_skating_ijs_seed.sqlite`

**Tables:**

| Table | Description |
|---|---|
| `competitions` | One row per competition (name, year, location) |
| `events` | One row per discipline × segment × competition |
| `entries` | One row per competitor (or pair/team) per event, with final rank and TSS |
| `elements` | One row per technical element executed, with base value, GOE, technical call markers |
| `element_judge_scores` | One row per judge per element — the raw GOE scores |
| `pcs_judge_scores` | One row per judge per PCS component per entry |
| `pcs_components` | Component names and factor weights by discipline/segment/era |
| `judges` | Judge names and country codes by event |
| `judge_entry_totals` | Computed TES, PCS, TSS per judge per entry (for LOJO) |
| `judge_event_statistics` | Summary statistics per judge per event (LOJO results) |
| `pairwise_judge_statistics` | Full pairwise test results: BI(j), p-value, z-score for every judge × pair |
| `sources` | Source PDF filenames and ingest run metadata |
| `ingest_runs` | Log of parser runs |
| `event_labels` | Human-readable competition/event labels |

**Views:**

| View | Description |
|---|---|
| `v_pairwise_event_summary` | Aggregated pairwise results by event |
| `v_pairwise_judge_summary` | Aggregated pairwise results by judge |
| `v_fra_minus_usa_by_judge` | Specific France vs. USA differential by judge (OWG2026 case study) |

### 3.2 Final Database Counts

| Item | Count |
|---|---|
| Competitions | 17 |
| Events (discipline × segment) | 141 |
| Competitor/pair performances (entries) | 2,637 |
| Technical elements | 22,380 |
| Individual judge GOE scores | 200,715 |
| Individual judge PCS marks | 66,794 |
| Pairwise test statistics | 264,854 |
| Judge event records (LOJO) | 1,269 |

---

## 4. Parsing Pipeline

### 4.1 Two Custom Parsers

Two Python parsers extract structured data from the ISU PDFs using `pdftotext` (poppler) to convert PDFs to fixed-width text, then regex-based line parsing to extract scores.

**`parse_ice_dance.py`** — Handles Ice Dance events (Rhythm Dance and Free Dance segments)
**`parse_singles_pairs.py`** — Handles Men's Singles, Women's Singles, and Pair Skating

### 4.2 Format Variants Handled

The parsers handle all ISU scoring format variations encountered in the dataset:

| Variant | Description |
|---|---|
| Variable panel size | 8 judges (some COVID-era events), 9 judges (standard) |
| PCS format change | 5 components (pre-2022/23) vs. 3 components (2022/23 onward) |
| Bonus marker `x` | Credit/highlight distribution bonus; multiplies base value by 1.10 |
| Standard technical call markers | `<`, `<<`, `q`, `!`, `e`, `F`, `*` |
| Combined markers (2024/25 season) | Pipe-separated: `!|<`, `q|q`, `q|<` |
| Combined markers (OWG2022, OWG2026) | Comma-separated: `!,q`, `q,<`, `<<,*`, `q,!,q` |
| Name format (OWG2018) | `SURNAME Firstname` (legacy format) |
| Name format (modern) | `Firstname SURNAME` |

### 4.3 Bugs Fixed During Development

Two bugs were identified and fixed during development:

**Bug 1 — Pipe marker `|` not recognized:**
The 2024/25 ISU PDFs introduced combined call markers using a pipe character as separator (e.g., `!|<`, `q|q`). The parser's `_INFO_CHARS` set did not include `|`, causing affected elements to be silently skipped. Fixed by adding `|` to `_INFO_CHARS`.

**Bug 2 — Comma marker `,` not recognized:**
OWG2022 and OWG2026 PDFs use comma-separated combined markers (e.g., `!,q`, `q,<`, `<<,*`). The comma was not in `_INFO_CHARS`, causing the same silent-skip failure. Fixed by adding `,` to `_INFO_CHARS`.

**Effect of fixes:** Before fixes, 40 entries failed the TES reconstruction check. After fixes: 0 failures (100% pass rate across 2,005 non-Ice Dance entries).

### 4.4 Data Integrity Verification

**TES Reconstruction Check:** For every entry in the database, the sum of all individual element panel scores (as stored) was compared to the stored Total Element Score from the official PDF. A match within floating-point rounding tolerance (±0.05 points) confirms that all elements were correctly identified, parsed, and stored.

**Result: 100% pass rate across all non-Ice Dance entries (2,005 entries).** Ice Dance verified by analogous procedure.

---

## 5. Statistical Analysis Pipeline

### 5.1 Script: `calculate_statistics.py`

Computes per-judge, per-event summary statistics: peer deviations, mean GOE and PCS marks by judge, and stores 1,269 judge-event records in `judge_event_statistics`.

### 5.2 Script: `calculate_pairwise_statistics.py`

**Note:** This script has been updated to v2 (`calculate_pairwise_statistics_v2.py`) targeting `figure_skating_ijs_v2.sqlite`. See v2 change note in the Method section below.

**Purpose:** For every judge in every event, computes the BI(j) bias statistic and a permutation p-value for every pairwise combination of competitors.

**Method:**
1. For each competitor pair (A, B) in an event, compute BI(j, A, B) = sum of judge j's peer-median deviations on A's elements minus sum on B's elements. The peer-median benchmark for each element is the true mathematical median of the other 8 judges' GOE scores — the average of the 4th and 5th values when sorted ascending — which can produce .5 values when those two scores differ.
2. Run the exact combinatorial permutation test: combine all of judge j's peer-median deviations for competitors A and B into one pool (18 values for a 9-element program, k values per competitor), then enumerate ALL C(2k, k) distinct ways to split the combined pool into an A-group of k values and a B-group of k values. For k=9: C(18,9) = 48,620 splits. For k=5: C(10,5) = 252 splits. For k=12: C(24,12) = 2,704,156 splits. For each split, recompute the simulated BI(j). No random seed. Fully deterministic.
3. Compute one-sided exact p-value: p = extreme_count / total_combinations, where extreme_count is the number of splits with simulated BI(j) as extreme or more extreme than observed. Because all splits are evaluated, this is an exact fraction with no sampling error.
4. Apply Bonferroni correction for multiple comparisons across all C(n,2) pairs per event.

**v2 change:** The original script (`calculate_pairwise_statistics.py`) used SQL `LIMIT 1 OFFSET 4` which picks the 5th sorted value (the upper median) rather than the true mathematical median. The v2 script corrects this and also fixes significance thresholds from strict `<` to `<=` for both 0.01 and 0.001 cutoffs. The original database (`figure_skating_ijs_seed.sqlite`) is preserved; v2 results are in `figure_skating_ijs_v2.sqlite`.

**v3 change:** The v2 script used a Monte Carlo permutation test (100,000 random shuffles, seed=42). The v3 script (`calculate_pairwise_statistics_v3.py`) replaces this with an exact combinatorial enumeration, evaluating all C(2k, k) splits deterministically. Results are stored in `figure_skating_ijs_v3.sqlite`. The new `extreme_count` column stores the raw numerator of each exact p-value (e.g., 36 of 48,620). The `num_permutations` column stores C(2k,k) (e.g., 48,620). The `test_type` column reads `one-sided-exact`.

**Scale of computation:**
- 141 events
- Up to 741 pairwise combinations per event (Men's with 39 competitors)
- 9 judges per event
- Exact splits enumerated per test: C(2k,k) — e.g., 48,620 for k=9; 2,704,156 for k=12
- Total splits enumerated: variable by event and program length

**Runtime (v3):** Approximately 2–3 hours on a standard Mac laptop, running in background. The exact enumeration is faster than the Monte Carlo v2 run (20 hours) for most events because C(18,9) = 48,620 << 100,000. Longer programs (k=12) take ~1 second per judge pair.

**Output:** 269,957 pairwise test statistics stored in `pairwise_judge_statistics` (v2 database).

**Resume capability:** The script checks which events already have complete data and skips them, enabling safe restart after interruption.

### 5.3 Script: `calculate_lojo.py`

**Purpose:** Leave-one-judge-out (LOJO) counterfactual — for every judge in every event, compute what the final rankings would have been if that judge's scores were excluded.

**Method:**
1. Remove judge j's scores from every element and component in the event.
2. Recompute the trimmed mean for each scored unit using the remaining m−1 judges (still dropping 1 highest and 1 lowest from the remaining scores).
3. Recompute each competitor's TES, PCS, and TSS under the counterfactual.
4. Re-rank all competitors by counterfactual TSS.
5. Compare counterfactual ranking to official ranking; flag `winner_changes=1` if gold medal changes, `podium_changes=1` if any of the ordered top-3 positions change (including reorderings of the same three competitors).

**Output:**
- `lojo_results.csv` — 1,269 rows, one per judge per event, with actual and counterfactual rankings, margins, and change flags
- `lojo_podium_changes.csv` — 510 rows, one per judge removal that changes any podium position

---

## 6. Results

### 6.1 LOJO Summary Results

| Metric | Value |
|---|---|
| Total events analyzed | 144 |
| Total individual judge removals analyzed | 1,288 |
| Judge removals that change the gold medal winner (`winner_changes`) | 157 (12.2%) |
| Judge removals that change any ordered top-3 position (`podium_changes`) | 478 (37.1%) |
| OSNR Tier 2 flags (podium_changes + p ≤ 0.001) | 153 across 47 events |

### 6.2 LOJO Results by Competition

**✅ Stable** = no judge removal changes any podium position
**△ Podium changes** = at least one judge removal changes an ordered top-3 position (including reorderings)
**⚠️ WINNER CHANGES** = at least one judge removal changes the gold medal winner

| Competition | Event | Segment | Result |
|---|---|---|---|
| Europeans 2022 | Ice Dance | Free Dance | ✅ Stable |
| Europeans 2022 | Ice Dance | Rhythm Dance | ✅ Stable |
| Europeans 2022 | Men | Free Skating | ⚠️ WINNER CHANGES (2 judges) |
| Europeans 2022 | Men | Short Program | ⚠️ WINNER CHANGES (1 judge) |
| Europeans 2022 | Pairs | Free Skating | △ Podium changes (1 judge) |
| Europeans 2022 | Pairs | Short Program | ✅ Stable |
| Europeans 2022 | Women | Free Skating | ⚠️ WINNER CHANGES (2 judges) |
| Europeans 2022 | Women | Short Program | ✅ Stable |
| Europeans 2023 | Ice Dance | Free Dance | ⚠️ WINNER CHANGES (6 judges) |
| Europeans 2023 | Ice Dance | Rhythm Dance | ⚠️ WINNER CHANGES (2 judges) |
| Europeans 2023 | Men | Free Skating | ⚠️ WINNER CHANGES (7 judges) |
| Europeans 2023 | Men | Short Program | △ Podium changes (8 judges) |
| Europeans 2023 | Pairs | Free Skating | △ Podium changes (6 judges) |
| Europeans 2023 | Pairs | Short Program | ✅ Stable |
| Europeans 2023 | Women | Free Skating | ⚠️ WINNER CHANGES (9 judges) |
| Europeans 2023 | Women | Short Program | ⚠️ WINNER CHANGES (1 judge) |
| Europeans 2024 | Ice Dance | Free Dance | △ Podium changes (1 judge) |
| Europeans 2024 | Ice Dance | Rhythm Dance | ✅ Stable |
| Europeans 2024 | Men | Free Skating | △ Podium changes (3 judges) |
| Europeans 2024 | Men | Short Program | △ Podium changes (3 judges) |
| Europeans 2024 | Pairs | Free Skating | ⚠️ WINNER CHANGES (9 judges) |
| Europeans 2024 | Pairs | Short Program | ✅ Stable |
| Europeans 2024 | Women | Free Skating | △ Podium changes (1 judge) |
| Europeans 2024 | Women | Short Program | △ Podium changes (4 judges) |
| Europeans 2025 | Ice Dance | Free Dance | ⚠️ WINNER CHANGES (9 judges) |
| Europeans 2025 | Ice Dance | Rhythm Dance | ✅ Stable |
| Europeans 2025 | Men | Free Skating | ⚠️ WINNER CHANGES (1 judge) |
| Europeans 2025 | Men | Short Program | ✅ Stable |
| Europeans 2025 | Pairs | Free Skating | △ Podium changes (8 judges) |
| Europeans 2025 | Pairs | Short Program | △ Podium changes (6 judges) |
| Europeans 2025 | Women | Free Skating | △ Podium changes (6 judges) |
| Europeans 2025 | Women | Short Program | ⚠️ WINNER CHANGES (5 judges) |
| Four Continents 2022 | Ice Dance | Free Dance | ✅ Stable |
| Four Continents 2022 | Ice Dance | Rhythm Dance | ✅ Stable |
| Four Continents 2022 | Men | Free Skating | △ Podium changes (6 judges) |
| Four Continents 2022 | Men | Short Program | ✅ Stable |
| Four Continents 2022 | Pairs | Free Skating | △ Podium changes (9 judges) |
| Four Continents 2022 | Pairs | Short Program | △ Podium changes (9 judges) |
| Four Continents 2022 | Women | Free Skating | △ Podium changes (3 judges) |
| Four Continents 2022 | Women | Short Program | △ Podium changes (5 judges) |
| Four Continents 2023 | Ice Dance | Free Dance | ✅ Stable |
| Four Continents 2023 | Ice Dance | Rhythm Dance | ✅ Stable |
| Four Continents 2023 | Men | Free Skating | ⚠️ WINNER CHANGES (9 judges) |
| Four Continents 2023 | Men | Short Program | ✅ Stable |
| Four Continents 2023 | Pairs | Free Skating | ⚠️ WINNER CHANGES (9 judges) |
| Four Continents 2023 | Pairs | Short Program | ⚠️ WINNER CHANGES (2 judges) |
| Four Continents 2023 | Women | Free Skating | ✅ Stable |
| Four Continents 2023 | Women | Short Program | ⚠️ WINNER CHANGES (8 judges) |
| Four Continents 2024 | Ice Dance | Free Dance | ✅ Stable |
| Four Continents 2024 | Ice Dance | Rhythm Dance | ✅ Stable |
| Four Continents 2024 | Men | Free Skating | ✅ Stable |
| Four Continents 2024 | Men | Short Program | ✅ Stable |
| Four Continents 2024 | Pairs | Free Skating | ⚠️ WINNER CHANGES (7 judges) |
| Four Continents 2024 | Pairs | Short Program | △ Podium changes (6 judges) |
| Four Continents 2024 | Women | Free Skating | △ Podium changes (8 judges) |
| Four Continents 2024 | Women | Short Program | ✅ Stable |
| Four Continents 2025 | Ice Dance | Free Dance | ✅ Stable |
| Four Continents 2025 | Ice Dance | Rhythm Dance | ✅ Stable |
| Four Continents 2025 | Men | Free Skating | ⚠️ WINNER CHANGES (8 judges) |
| Four Continents 2025 | Men | Short Program | ✅ Stable |
| Four Continents 2025 | Pairs | Free Skating | ⚠️ WINNER CHANGES (8 judges) |
| Four Continents 2025 | Pairs | Short Program | △ Podium changes (9 judges) |
| Four Continents 2025 | Women | Free Skating | ✅ Stable |
| Four Continents 2025 | Women | Short Program | ✅ Stable |
| GP Final 2022/23 | Ice Dance | Free Dance | ✅ Stable |
| GP Final 2022/23 | Ice Dance | Rhythm Dance | ⚠️ WINNER CHANGES (6 judges) |
| GP Final 2022/23 | Men | Free Skating | ⚠️ WINNER CHANGES (1 judge) |
| GP Final 2022/23 | Men | Short Program | ✅ Stable |
| GP Final 2022/23 | Pairs | Free Skating | ⚠️ WINNER CHANGES (9 judges) |
| GP Final 2022/23 | Pairs | Short Program | ⚠️ WINNER CHANGES (8 judges) |
| GP Final 2022/23 | Women | Free Skating | ✅ Stable |
| GP Final 2022/23 | Women | Short Program | △ Podium changes (7 judges) |
| GP Final 2023/24 | Ice Dance | Free Dance | ✅ Stable |
| GP Final 2023/24 | Ice Dance | Rhythm Dance | ✅ Stable |
| GP Final 2023/24 | Men | Free Skating | △ Podium changes (9 judges) |
| GP Final 2023/24 | Men | Short Program | △ Podium changes (7 judges) |
| GP Final 2023/24 | Pairs | Free Skating | △ Podium changes (1 judge) |
| GP Final 2023/24 | Pairs | Short Program | ✅ Stable |
| GP Final 2023/24 | Women | Free Skating | ✅ Stable |
| GP Final 2023/24 | Women | Short Program | ✅ Stable |
| GP Final 2024/25 | Ice Dance | Free Dance | △ Podium changes (9 judges) |
| GP Final 2024/25 | Ice Dance | Rhythm Dance | ✅ Stable |
| GP Final 2024/25 | Men | Free Skating | ⚠️ WINNER CHANGES (6 judges) |
| GP Final 2024/25 | Men | Short Program | △ Podium changes (6 judges) |
| GP Final 2024/25 | Pairs | Free Skating | ✅ Stable |
| GP Final 2024/25 | Pairs | Short Program | ✅ Stable |
| GP Final 2024/25 | Women | Free Skating | △ Podium changes (6 judges) |
| GP Final 2024/25 | Women | Short Program | ⚠️ WINNER CHANGES (9 judges) |
| Worlds 2022 | Ice Dance | Free Dance | ✅ Stable |
| Worlds 2022 | Ice Dance | Rhythm Dance | ✅ Stable |
| Worlds 2022 | Men | Free Skating | ✅ Stable |
| Worlds 2022 | Men | Short Program | ✅ Stable |
| Worlds 2022 | Pairs | Free Skating | ✅ Stable |
| Worlds 2022 | Pairs | Short Program | ⚠️ WINNER CHANGES (9 judges) |
| Worlds 2022 | Women | Free Skating | ✅ Stable |
| Worlds 2022 | Women | Short Program | ✅ Stable |
| Worlds 2023 | Ice Dance | Free Dance | ⚠️ WINNER CHANGES (2 judges) |
| Worlds 2023 | Ice Dance | Rhythm Dance | ✅ Stable |
| Worlds 2023 | Men | Free Skating | ⚠️ WINNER CHANGES (7 judges) |
| Worlds 2023 | Men | Short Program | △ Podium changes (8 judges) |
| Worlds 2023 | Pairs | Free Skating | ⚠️ WINNER CHANGES (8 judges) |
| Worlds 2023 | Pairs | Short Program | △ Podium changes (9 judges) |
| Worlds 2023 | Women | Free Skating | ⚠️ WINNER CHANGES (9 judges) |
| Worlds 2023 | Women | Short Program | ✅ Stable |
| Worlds 2024 | Ice Dance | Free Dance | ⚠️ WINNER CHANGES (9 judges) |
| Worlds 2024 | Ice Dance | Rhythm Dance | ✅ Stable |
| Worlds 2024 | Men | Free Skating | △ Podium changes (8 judges) |
| Worlds 2024 | Men | Short Program | △ Podium changes (2 judges) |
| Worlds 2024 | Pairs | Free Skating | ⚠️ WINNER CHANGES (7 judges) |
| Worlds 2024 | Pairs | Short Program | △ Podium changes (8 judges) |
| Worlds 2024 | Women | Free Skating | △ Podium changes (8 judges) |
| Worlds 2024 | Women | Short Program | △ Podium changes (8 judges) |
| Worlds 2025 | Ice Dance | Free Dance | ✅ Stable |
| Worlds 2025 | Ice Dance | Rhythm Dance | ✅ Stable |
| Worlds 2025 | Men | Free Skating | ✅ Stable |
| Worlds 2025 | Men | Short Program | ⚠️ WINNER CHANGES (8 judges) |
| Worlds 2025 | Pairs | Free Skating | △ Podium changes (9 judges) |
| Worlds 2025 | Pairs | Short Program | ✅ Stable |
| Worlds 2025 | Women | Free Skating | △ Podium changes (7 judges) |
| Worlds 2025 | Women | Short Program | ⚠️ WINNER CHANGES (3 judges) |
| OWG 2022 (Beijing) | Ice Dance | Free Dance | ✅ Stable |
| OWG 2022 (Beijing) | Ice Dance | Rhythm Dance | ✅ Stable |
| OWG 2022 (Beijing) | Men | Free Skating | △ Podium changes (9 judges) |
| OWG 2022 (Beijing) | Men | Short Program | ✅ Stable |
| OWG 2022 (Beijing) | Pairs | Free Skating | ⚠️ WINNER CHANGES (9 judges) |
| OWG 2022 (Beijing) | Pairs | Short Program | ⚠️ WINNER CHANGES (2 judges) |
| OWG 2022 (Beijing) | Women | Free Skating | ⚠️ WINNER CHANGES (9 judges) |
| OWG 2022 (Beijing) | Women | Short Program | ⚠️ WINNER CHANGES (9 judges) |
| OWG 2026 (Milano–Cortina) | Ice Dance | Free Dance | ⚠️ WINNER CHANGES (3 judges) |
| OWG 2026 (Milano–Cortina) | Ice Dance | Rhythm Dance | ✅ Stable |
| OWG 2026 (Milano–Cortina) | Men | Free Skating | △ Podium changes (9 judges) |
| OWG 2026 (Milano–Cortina) | Men | Short Program | △ Podium changes (8 judges) |
| OWG 2026 (Milano–Cortina) | Pairs | Short Program | △ Podium changes (9 judges) |

*(Note: OWG2026 Team Event segments are stored in the database but excluded from the primary analysis. OWG2026 Pairs Free Skating and Women's events not yet in database at time of analysis.)*

### 6.3 Pairwise Analysis Summary

- **264,854** pairwise test statistics computed across 141 events
- Each test: one BI(j) statistic + one exact permutation p-value (all C(2k,k) splits enumerated) for one judge × one competitor pair
- Bonferroni-corrected significance threshold varies by event field size
- Detailed results available in `pairwise_judge_statistics` table in the database

---

## 7. Output Files

| File | Description |
|---|---|
| `figure_skating_ijs_seed.sqlite` | Main database (88 MB) — all parsed scores, all statistical results |
| `lojo_results.csv` | 1,288 rows: LOJO results for every judge in every event |
| `lojo_podium_changes.csv` | Filtered view: events and judges where LOJO removal changes any ordered top-3 position |
| `pairwise_all_output.log` | Console log of the full pairwise analysis run |
| `lojo_output.log` | Console log of the LOJO analysis run |
| `parse_singles_pairs_run3.log` | Console log of the final parser run (100% TES pass) |

---

## 8. Python Scripts

| Script | Purpose |
|---|---|
| `parse_singles_pairs.py` | Parser for Men's, Women's, and Pairs ISU PDFs |
| `parse_ice_dance.py` | Parser for Ice Dance ISU PDFs |
| `calculate_statistics.py` | Per-judge, per-event summary statistics |
| `calculate_pairwise_statistics.py` | Full pairwise permutation test across all events |
| `calculate_lojo.py` | Leave-one-judge-out counterfactual analysis |
| `create_all_competitions.py` | Populates competition and event metadata in database |
| `populate_all_2016_2026.py` | Coordinates parsing runs across all competitions |
| `deduplicate_entries.py` | Removes duplicate entries from database |

---

## 9. Supporting Documents

| Document | Description |
|---|---|
| `database_summary.md` / `.docx` | 1-page summary of what the database contains |
| `scoring_summary.md` / `.docx` | Explanation of the ISU scoring system (IJS) |
| `glossary.md` / `.docx` | Glossary of figure skating, statistical, and database terms |
| `literature_review.md` / `.docx` | 59-reference annotated bibliography |
| `paper_draft_v1.md` | Working paper draft (Sections 1–4, Appendices A–B, References) |
| `paper_draft_v2.docx` | Latest Word version of the paper draft |

---

## 10. Paper Draft Status

### Completed Sections
- **Abstract** — placeholder (to be completed once empirical sections are written)
- **Section 1: Introduction** — complete
- **Section 2: Background** — complete (2.1 IJS system, 2.2 governance gap, 2.3 prior literature with 4 subsections)
- **Section 3: Statistical Framework** — complete (3.1 notation, 3.2 BI(j) statistic, 3.3 permutation test, 3.4 pairwise extension, 3.5 LOJO counterfactual, 3.6 OSNR two-tier rule)
- **Section 4: Data** — complete (4.1 source, 4.2 parsing, 4.3 integrity verification, 4.4 coverage, 4.5 judge identification)
- **Appendix A:** Extreme-rank statistic (supplementary)
- **Appendix B:** Permutation pseudocode
- **References:** Complete bibliography

### Sections Still To Write
- **Section 5: Empirical Results** — requires pairwise + LOJO results (now available ✅)
- **Section 6: Case Study** — Milano–Cortina 2026 Ice Dance (requires pairwise results ✅)
- **Section 7: Policy Implications** — OSNR implementation
- **Section 8: Limitations and Future Work**
- **Section 9: Conclusion**
- **Abstract** — final version

### Target Journal
JQAS (*Journal of Quantitative Analysis in Sports*) as first submission target; MAS (*Mathematics and Statistics*) as fallback.

---

## 11. Key Methodological Decisions

| Decision | Rationale |
|---|---|
| Within-unit permutation (not across-unit) | Preserves empirical score distribution per element; no parametric assumption needed |
| Peer deviation (not raw scores) | Controls for element difficulty and judge-level leniency |
| Bonferroni correction | Conservative; appropriate for a governance rule where false positives are costly |
| Exact combinatorial enumeration | All C(2k,k) splits enumerated (e.g., 48,620 for k=9); p-values are exact fractions, fully deterministic, no seed |
| Event-local analysis only | Avoids false positives from cross-event aggregation; implementable from a single scoring sheet |
| LOJO materiality threshold | Separates statistical anomaly from competitive impact; Tier 2 requires both |
| No cross-event judge identity linking | Normative choice: OSNR must not require a dossier on named judges |

---

## 12. Reproducibility

All components needed to reproduce the full analysis from scratch:

1. **Source PDFs** — downloaded from ISU results website; stored in project folder
2. **Parser scripts** — `parse_singles_pairs.py`, `parse_ice_dance.py`
3. **Database** — `figure_skating_ijs_seed.sqlite` (or rebuild using parsers)
4. **Analysis scripts** — `calculate_pairwise_statistics.py`, `calculate_lojo.py`
5. **Tools required** — Python 3.8+, poppler (`pdftotext`), SQLite3, standard Python libraries only (no paid or proprietary dependencies)

*Repository URL to be provided upon publication.*

---

*Documentation compiled: February 2026*
*All computations performed on a standard Mac laptop.*
