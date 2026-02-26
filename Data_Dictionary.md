# Data Dictionary
## ISU Figure Skating IJS Judging Bias Study
**Project:** ISU-impact — Pairwise Style-Controlled Judge Bias Analysis
**Database:** `figure_skating_ijs_v4.sqlite`
**Prepared:** February 2026
**Version:** 2.0

---

## 1. Overview

This document describes all data collected, stored, and derived in the study database. Tables are divided into three categories:

- **Source tables** — data extracted directly from ISU official documents (PDFs and HTML pages)
- **Reference tables** — lookup data compiled from ISU Communications and rules documents
- **Derived tables** — data computed from source tables by project analysis scripts

### 1.1 Data Sources

For each event in the database, two ISU documents were retrieved:

| Source Type | Format | What It Contains |
|-------------|--------|-----------------|
| `panel_of_judges` | HTML page (e.g., `SEG007OF.htm`) | Judge panel roster: names, positions, nationalities |
| `judges_details_pdf` | PDF (e.g., `FSKXICEDANCE_FD_JudgesDetailsperSkater.pdf`) | Full scoring details: competitor results, element-by-element scores, individual judge grades |

All source files are archived locally under `isu_pdfs/` with SHA-256 checksums recorded in the `sources` table.

### 1.2 Competition Coverage

| Season | Competition | Events | Entries |
|--------|-------------|--------|---------|
| 2021/22 | ISU European Figure Skating Championships 2022 | 8 | 199 |
| 2021/22 | ISU Four Continents Figure Skating Championships 2022 | 8 | 105 |
| 2021/22 | Olympic Winter Games 2022 — Figure Skating | 8 | 181 |
| 2021/22 | ISU World Figure Skating Championships 2022 | 8 | 185 |
| 2022/23 | ISU Grand Prix of Figure Skating Final 2022/23 (Turin) | 8 | 48 |
| 2022/23 | ISU European Figure Skating Championships 2023 | 8 | 175 |
| 2022/23 | ISU Four Continents Figure Skating Championships 2023 | 8 | 131 |
| 2022/23 | ISU World Figure Skating Championships 2023 | 8 | 213 |
| 2023/24 | ISU Grand Prix of Figure Skating Final 2023/24 (Beijing) | 8 | 48 |
| 2023/24 | ISU European Figure Skating Championships 2024 | 8 | 199 |
| 2023/24 | ISU Four Continents Figure Skating Championships 2024 | 8 | 157 |
| 2023/24 | ISU World Figure Skating Championships 2024 | 8 | 223 |
| 2024/25 | ISU Grand Prix of Figure Skating Final 2024/25 (Grenoble) | 8 | 48 |
| 2024/25 | ISU European Figure Skating Championships 2025 | 8 | 196 |
| 2024/25 | ISU Four Continents Figure Skating Championships 2025 | 8 | 136 |
| 2024/25 | ISU World Figure Skating Championships 2025 | 8 | 219 |
| 2025/26 | Olympic Winter Games 2026 (Milano Cortina) — Figure Skating | 16 | 243 |

**Total: 17 competitions, 144 events (136 individual + 8 team), 2,706 entries**

Note: OWG 2026 contributes 16 events (8 individual discipline segments + 8 team event segments). All other competitions contribute 8 events (4 disciplines × 2 segments).

### 1.3 Analytical Coverage

Of 144 events, **142 were analyzed** using the ISU-impact method. Two events were excluded:

| Event ID | Competition | Segment | Reason |
|----------|-------------|---------|--------|
| 148 | ISU Four Continents 2022 | Ice Dance — Rhythm Dance | Only 7 judges (method requires 9) |
| 149 | ISU Four Continents 2022 | Ice Dance — Free Dance | Only 7 judges (method requires 9) |

### 1.4 Event Coverage by Discipline

| Discipline | Segment | Count |
|------------|---------|-------|
| Ice Dance | Rhythm Dance | 17 |
| Ice Dance | Free Dance | 17 |
| Men Single Skating | Short Program | 17 |
| Men Single Skating | Free Skating | 17 |
| Pair Skating | Short Program | 17 |
| Pair Skating | Free Skating | 17 |
| Women Single Skating | Short Program | 17 |
| Women Single Skating | Free Skating | 17 |
| Team Event (4 disciplines × 2 segments) | Various | 8 |

---

## 2. Source Tables

### 2.1 `competitions` — 17 rows

One row per competition (championship or games).

| Column | Type | Description |
|--------|------|-------------|
| `competition_id` | INTEGER PK | Surrogate key |
| `season` | TEXT | ISU season string, e.g. `"2021/22"` |
| `name` | TEXT NOT NULL | Full official competition name |
| `organizer` | TEXT | Organizing body |
| `location` | TEXT | Host city/venue |
| `start_date` | TEXT | ISO 8601 date |
| `end_date` | TEXT | ISO 8601 date |
| `results_root_url` | TEXT | Base URL for ISU results pages |

### 2.2 `events` — 144 rows

One row per skating segment (e.g., Ice Dance Free Dance at OWG 2026).

| Column | Type | Description |
|--------|------|-------------|
| `event_id` | INTEGER PK | Surrogate key |
| `competition_id` | INTEGER NOT NULL | FK → `competitions` |
| `discipline` | TEXT NOT NULL | e.g., `"Ice Dance"`, `"Men Single Skating"` |
| `segment` | TEXT NOT NULL | `"Free Dance"`, `"Short Program"`, `"Free Skating"`, `"Rhythm Dance"` |
| `level` | TEXT | `"senior"` or `"team"` |
| `scheduled_datetime_local` | TEXT | ISO 8601 datetime in local time |
| `venue` | TEXT | Venue name |
| `segment_results_url` | TEXT | URL to ISU segment results page |
| `judges_details_pdf_url` | TEXT | URL to Judges Details per Skater PDF |
| `panel_of_judges_url` | TEXT | URL to Panel of Judges HTML page |

### 2.3 `entries` — 2,706 rows

One row per competitor in an event (skater, couple, or team).

| Column | Type | Description |
|--------|------|-------------|
| `entry_id` | INTEGER PK | Surrogate key |
| `event_id` | INTEGER NOT NULL | FK → `events` |
| `team_name` | TEXT NOT NULL | Skater name(s) or team name |
| `noc` | TEXT | 3-letter NOC code (e.g., `"FRA"`, `"USA"`) |
| `start_no` | INTEGER | Starting order |
| `rank` | INTEGER | Official final rank |
| `tes` | REAL | Total Element Score (official) |
| `pcs` | REAL | Program Component Score (official panel total) |
| `deductions` | REAL | Deductions (stored as **negative** values) |
| `tss` | REAL | Total Segment Score = `tes + pcs + deductions` |
| `skater1` | TEXT | First skater name (or NULL for singles) |
| `skater2` | TEXT | Second skater name (ice dance / pairs only) |

**Sign convention:** Deductions are stored as negative numbers. TSS is computed as `tes + pcs + deductions` (addition, not subtraction).

### 2.4 `judges` — 1,305 rows

One row per judge per event (judges appear multiple times across events).

| Column | Type | Description |
|--------|------|-------------|
| `judge_id` | INTEGER PK | Surrogate key |
| `event_id` | INTEGER NOT NULL | FK → `events` |
| `judge_position` | TEXT NOT NULL | `"J1"` through `"J9"` |
| `judge_name` | TEXT | Full name (as published by ISU) |
| `country_code` | TEXT | 3-letter NOC code of judge's federation |

### 2.5 `elements` — 23,043 rows

One row per executed element per entry.

| Column | Type | Description |
|--------|------|-------------|
| `element_id` | INTEGER PK | Surrogate key |
| `entry_id` | INTEGER NOT NULL | FK → `entries` |
| `element_no` | INTEGER NOT NULL | Execution order within the program |
| `element_code` | TEXT NOT NULL | ISU element code (e.g., `"4T"`, `"SyTw4"`) |
| `base_value` | REAL | Base value in points |
| `panel_goe_points` | REAL | Panel GOE in points (sum of 7 trimmed judge GOEs × GOE factor) |
| `panel_element_score` | REAL | `base_value + panel_goe_points` |
| `goe_factor_inferred` | REAL | Inferred GOE factor = `panel_goe_points / trimmed_mean_goe` (unreliable for combined elements; see `goe_factors` table) |
| `element_info` | TEXT | Additional flags (e.g., under-rotation markers, combination notation) |

**Note on `goe_factor_inferred`:** For combined elements in ice dance (SyTw, OFT, DiSt), the trimmed mean GOE spans multiple sub-elements; `goe_factor_inferred` is unreliable for these. The `goe_factors` reference table provides the authoritative factor for all element types. ISU-impact calculations use `panel_goe_points / trimmed_mean_goe` computed directly from raw judge scores.

### 2.6 `element_judge_scores` — 206,682 rows

One row per (element, judge) pair — the raw integer GOE grade assigned by each judge.

| Column | Type | Description |
|--------|------|-------------|
| `element_id` | INTEGER PK (composite) | FK → `elements` |
| `judge_id` | INTEGER PK (composite) | FK → `judges` |
| `judge_goe_int` | INTEGER | GOE integer grade (range: −5 to +5) |

Primary key is (`element_id`, `judge_id`).

### 2.7 `pcs_components` — 9,458 rows

One row per program component per entry (5 components per entry in most events).

| Column | Type | Description |
|--------|------|-------------|
| `pcs_id` | INTEGER PK | Surrogate key |
| `entry_id` | INTEGER NOT NULL | FK → `entries` |
| `component_name` | TEXT NOT NULL | e.g., `"Skating Skills"`, `"Transitions"` |
| `factor` | REAL | Multiplication factor for this component |
| `panel_component_avg` | REAL | Panel average mark for this component |

**Note:** Individual judge PCS marks are only available for ice dance events. For singles and pairs, only panel averages are recorded. See Section 5.2.

### 2.8 `pcs_judge_scores` — 84,922 rows

One row per (component, judge) pair — individual judge PCS marks (ice dance only).

| Column | Type | Description |
|--------|------|-------------|
| `pcs_id` | INTEGER PK (composite) | FK → `pcs_components` |
| `judge_id` | INTEGER PK (composite) | FK → `judges` |
| `judge_mark` | REAL | Judge's mark for this PCS component |

Primary key is (`pcs_id`, `judge_id`).

### 2.9 `sources` — 239 rows

One row per retrieved source document, with integrity metadata.

| Column | Type | Description |
|--------|------|-------------|
| `source_id` | INTEGER PK | Surrogate key |
| `event_id` | INTEGER | FK → `events` |
| `source_type` | TEXT NOT NULL | `"panel_of_judges"` or `"judges_details_pdf"` |
| `url` | TEXT NOT NULL | Original ISU URL |
| `retrieved_utc` | TEXT | ISO 8601 UTC timestamp of retrieval |
| `sha256` | TEXT | SHA-256 hash of retrieved file |
| `local_path` | TEXT | Path to archived local copy |
| `content_type` | TEXT | HTTP Content-Type header |
| `bytes` | INTEGER | File size in bytes |

---

## 3. Reference Tables

### 3.1 `goe_factors` — 17 rows

Lookup table of official ISU GOE point-conversion factors by element type and season. Compiled from ISU Communication 2705 and related scale-of-values documents.

| Column | Type | Description |
|--------|------|-------------|
| `factor_id` | INTEGER PK | Surrogate key |
| `season` | TEXT NOT NULL | Season string (e.g., `"2021/22"`) or `"all"` for season-invariant entries |
| `discipline` | TEXT NOT NULL | Discipline or `"all"` |
| `element_pattern` | TEXT NOT NULL | Regex pattern matching element codes |
| `goe_factor` | REAL NOT NULL | GOE factor for positive GOE (points per integer grade) |
| `goe_factor_neg` | REAL | GOE factor for negative GOE (if asymmetric; NULL if symmetric) |
| `source_comm` | TEXT NOT NULL | ISU Communication number (e.g., `"ISU Comm 2705"`) |
| `notes` | TEXT | Additional clarification |

---

## 4. Derived Tables

### 4.1 `lojo_scores` — 24,269 rows

Leave-One-Judge-Out (LOJO) counterfactual results: for each judge in each event, the recalculated TSS and rank for every entry if that judge's scores were excluded from the panel computation.

**Computed by:** `calculate_lojo_full.py`

| Column | Type | Description |
|--------|------|-------------|
| `lojo_id` | INTEGER PK | Surrogate key |
| `event_id` | INTEGER NOT NULL | FK → `events` |
| `judge_id` | INTEGER NOT NULL | FK → `judges` (the excluded judge) |
| `judge_position` | TEXT | Position of excluded judge (`"J1"`–`"J9"`) |
| `entry_id` | INTEGER NOT NULL | FK → `entries` |
| `cf_tss` | REAL | Counterfactual TSS with this judge excluded |
| `cf_rank` | INTEGER | Counterfactual rank |
| `official_rank` | INTEGER | Official rank (copied for convenience) |
| `rank_change` | INTEGER | `cf_rank − official_rank` (positive = falls; negative = rises) |

**PCS note:** For singles and pairs events where individual judge PCS marks are not available, `cf_tss = cf_tes + stored_pcs`. TES is fully recomputed judge-by-judge; PCS is held at the official stored value. Recorded in `lojo_event_summary.pcs_mode`.

### 4.2 `lojo_event_summary` — 1,288 rows

Per-judge, per-event summary of LOJO results.

**Computed by:** `calculate_lojo_full.py`

| Column | Type | Description |
|--------|------|-------------|
| `summary_id` | INTEGER PK | Surrogate key |
| `event_id` | INTEGER NOT NULL | FK → `events` |
| `judge_id` | INTEGER NOT NULL | FK → `judges` |
| `judge_position` | TEXT | `"J1"`–`"J9"` |
| `judge_name` | TEXT | Judge's full name |
| `n_entries` | INTEGER | Number of entries in the event |
| `winner_changes` | INTEGER | 1 if gold medal winner changes without this judge, else 0 |
| `podium_changes` | INTEGER | Number of podium position changes without this judge |
| `n_rank_inversions` | INTEGER | Number of entry pairs where ranking order reverses |
| `total_pairs` | INTEGER | Total entry pairs (`n_entries` choose 2) |
| `kendall_tau_distance` | REAL | Kendall tau distance between official and counterfactual ranking |
| `actual_winner_name` | TEXT | Official gold medalist name |
| `cf_winner_name` | TEXT | Counterfactual gold medalist name (without this judge) |
| `actual_margin` | REAL | Official margin between 1st and 2nd place (points) |
| `cf_margin` | REAL | Counterfactual margin between 1st and 2nd |
| `pcs_mode` | TEXT | `"recomputed"` (ice dance) or `"held_official"` (singles/pairs) |

### 4.3 `pairwise_impact_results` — 271,728 rows

Core ISU-impact results: pairwise bias tests for every (judge, entry_a, entry_b) combination in every analyzed event. The ISU-impact method applies a style-adjusted quantile permutation null with M = 10,000 permutations, seed = 20260223, global CDF scope, and BH-FDR correction applied within each event.

**Computed by:** `calculate_isuimpact_v1.py`

| Column | Type | Description |
|--------|------|-------------|
| `result_id` | INTEGER PK | Surrogate key |
| `method_version` | TEXT NOT NULL | `"isuimpact_quantile_v1"` |
| `event_id` | INTEGER NOT NULL | FK → `events` |
| `judge_id` | INTEGER NOT NULL | FK → `judges` |
| `judge_position` | TEXT NOT NULL | `"J1"`–`"J9"` |
| `judge_name` | TEXT | Judge's full name |
| `judge_country` | TEXT | Judge's federation NOC code |
| `entry_id_a` | INTEGER NOT NULL | FK → `entries` (higher-ranked entry) |
| `entry_id_b` | INTEGER NOT NULL | FK → `entries` (lower-ranked entry) |
| `team_a` | TEXT | Name of entry A |
| `noc_a` | TEXT | NOC of entry A |
| `rank_a` | INTEGER | Official rank of entry A |
| `team_b` | TEXT | Name of entry B |
| `noc_b` | TEXT | NOC of entry B |
| `rank_b` | INTEGER | Official rank of entry B |
| `bias_points` | REAL NOT NULL | Signed bias: judge's marginal contribution to entry A's score advantage over entry B, relative to panel style-adjusted expectation (points) |
| `vote` | TEXT | Judge's directional vote: `"A"` (favors A), `"B"` (favors B), or `"neutral"` |
| `p_value` | REAL | One-sided permutation p-value |
| `q_value_bh` | REAL | BH-FDR adjusted q-value (within-event correction) |
| `permutations` | INTEGER | Number of permutations used (10,000) |
| `rng_seed` | INTEGER | RNG seed used (20260223) |
| `calculated_at` | TEXT | ISO 8601 UTC timestamp of calculation |

**Significance:** A result is flagged as significant at q ≤ 0.05 (BH-FDR). The outcome-determinative criterion additionally requires `bias_points > event_margin` (directional).

**Coverage:** 271,728 rows = 9 judges × C(N, 2) entry pairs × 142 analyzed events.

### 4.4 `judge_team_impacts` — 24,174 rows

Per-judge, per-entry aggregated ISU-impact scores: the net bias points each judge contributed toward or against each entry across all pairwise comparisons involving that entry.

**Computed by:** `calculate_isuimpact_v1.py`

| Column | Type | Description |
|--------|------|-------------|
| `impact_id` | INTEGER PK | Surrogate key |
| `method_version` | TEXT NOT NULL | `"isuimpact_quantile_v1"` |
| `event_id` | INTEGER NOT NULL | FK → `events` |
| `judge_id` | INTEGER NOT NULL | FK → `judges` |
| `judge_position` | TEXT NOT NULL | `"J1"`–`"J9"` |
| `judge_name` | TEXT | Judge's full name |
| `judge_country` | TEXT | Judge's federation NOC code |
| `entry_id` | INTEGER NOT NULL | FK → `entries` |
| `team` | TEXT | Entry name |
| `noc` | TEXT | Entry NOC code |
| `rank` | INTEGER | Official rank of this entry |
| `impact_points` | REAL NOT NULL | Net bias points this judge contributed toward this entry |
| `calculated_at` | TEXT | ISO 8601 UTC timestamp |

---

## 5. Known Data Limitations

### 5.1 Judge Anonymity

ISU publishes judge names and nationalities but does not publicly disclose which judge corresponds to which position number (J1–J9) at the time of competition. Judge positions are assigned anonymously in official result sheets. Names and positions used in this study are as published post-event by the ISU.

### 5.2 PCS Judge Marks — Singles and Pairs Events

Individual judge PCS marks for singles and pairs events could not be reliably extracted from the source PDFs. For these events, LOJO counterfactual TSSs are computed as `cf_tes + stored_pcs` (TES fully recomputed; PCS held at official value). Ice dance PCS judge marks are fully available and recomputed in LOJO. The `lojo_event_summary.pcs_mode` column records which treatment was applied per event.

### 5.3 Technical Panel Calls

Element base values and GOE factors reflect Technical Panel calls as published in official results. This study does not re-adjudicate Technical Panel decisions.

### 5.4 Deductions Sign Convention

Deductions in `entries.deductions` are stored as **negative** numbers. The official TSS formula is `TES + PCS + deductions` (addition). This is consistent throughout the database and all analysis scripts.

### 5.5 4CC 2022 Ice Dance — 7-Judge Panel

ISU Four Continents 2022 Ice Dance events (event_ids 148 and 149) had only 7 judges rather than the standard 9. The ISU-impact method requires a 9-judge panel; these events were excluded from analysis. They are retained in the database as source data.

### 5.6 GOE Factor for Combined Elements

For combined elements in ice dance (SyTw, OFT, DiSt), `elements.goe_factor_inferred` is unreliable because the trimmed mean spans multiple sub-element scores. All ISU-impact calculations use the effective GOE factor computed directly from raw judge scores as `panel_goe_points / trimmed_mean_goe`.

### 5.7 Grand Prix Final Entry Counts

Grand Prix Finals have 6 entries per discipline (by qualification), versus 20–30 entries at Championships. This is reflected in the lower entry counts (48 entries per 8-event GP Final).

---

## 6. Relationships Between Tables

```
competitions (competition_id)
    └── events (event_id, competition_id)
            ├── entries (entry_id, event_id)
            │       ├── elements (element_id, entry_id)
            │       │       └── element_judge_scores (element_id, judge_id)
            │       └── pcs_components (pcs_id, entry_id)
            │               └── pcs_judge_scores (pcs_id, judge_id)
            ├── judges (judge_id, event_id)
            ├── sources (source_id, event_id)
            ├── lojo_scores (lojo_id, event_id, judge_id, entry_id)
            ├── lojo_event_summary (summary_id, event_id, judge_id)
            ├── pairwise_impact_results (result_id, event_id, judge_id, entry_id_a, entry_id_b)
            └── judge_team_impacts (impact_id, event_id, judge_id, entry_id)

goe_factors (factor_id) — standalone reference table; joined by season + element_code pattern matching
```

---

## 7. Method Parameters

The ISU-impact results in `pairwise_impact_results` and `judge_team_impacts` were computed with the following parameters:

| Parameter | Value |
|-----------|-------|
| Method version | `isuimpact_quantile_v1` |
| Permutations (M) | 10,000 |
| RNG seed | 20260223 |
| CDF scope | Global (CDFs built from all 142 analyzed events) |
| Multiple testing correction | Benjamini-Hochberg FDR, applied within each event |
| Significance threshold | q ≤ 0.05 |
| Events analyzed | 142 of 144 (events 148, 149 excluded) |
| Computed | 2026-02-24 |
