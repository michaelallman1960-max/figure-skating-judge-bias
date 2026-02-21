# Data Dictionary
## ISU Figure Skating IJS Judging Bias Study
**Project:** Outlier Score Nullification Rule (OSNR)
**Database:** `figure_skating_ijs_seed.sqlite`
**Prepared:** February 2026
**Version:** 1.0

---

## 1. Overview

This document describes all data collected, stored, and derived in the study database. Tables are divided into two categories:

- **Source tables** — data extracted directly from ISU official documents (PDFs and HTML pages)
- **Derived tables** — data computed from source tables by project analysis scripts

### 1.1 Data Sources

For each of the 141 events in the database, two ISU documents were retrieved:

| Source Type | Format | What It Contains |
|-------------|--------|-----------------|
| `panel_of_judges` | HTML page (e.g., `SEG007OF.htm`) | Judge panel roster: names, positions, nationalities |
| `judges_details_pdf` | PDF (e.g., `FSKXICEDANCE_RD_JudgesDetailsperSkater.pdf`) | Full scoring details: competitor results, element-by-element scores, individual judge grades |

All source files are archived locally under `isu_pdfs/` with SHA-256 checksums recorded.

### 1.2 Competition Coverage

| Season | Competition | Events | Entries |
|--------|-------------|--------|---------|
| 2021/22 | ISU European Figure Skating Championships 2022 | 8 | 105 |
| 2021/22 | ISU World Figure Skating Championships 2022 | 8 | 185 |
| 2021/22 | Olympic Winter Games 2022 (Beijing) | 8 | 181 |
| 2022/23 | ISU European Figure Skating Championships 2023 | 8 | 175 |
| 2022/23 | ISU Four Continents Figure Skating Championships 2023 | 8 | 131 |
| 2022/23 | ISU Grand Prix of Figure Skating Final 2022/23 (Turin) | 8 | 48 |
| 2022/23 | ISU World Figure Skating Championships 2023 | 8 | 213 |
| 2023/24 | ISU European Figure Skating Championships 2024 | 8 | 199 |
| 2023/24 | ISU Four Continents Figure Skating Championships 2024 | 8 | 157 |
| 2023/24 | ISU Grand Prix of Figure Skating Final 2023/24 (Beijing) | 8 | 48 |
| 2023/24 | ISU World Figure Skating Championships 2024 | 8 | 223 |
| 2024/25 | ISU European Figure Skating Championships 2025 | 8 | 196 |
| 2024/25 | ISU Four Continents Figure Skating Championships 2025 | 8 | 136 |
| 2024/25 | ISU Grand Prix of Figure Skating Final 2024/25 (Grenoble) | 8 | 48 |
| 2024/25 | ISU World Figure Skating Championships 2025 | 8 | 219 |
| 2025/26 | Olympic Winter Games 2026 (Milano Cortina) | 13 | 174 |

**Total: 16 competitions, 141 events (133 individual + 8 team), 2,637 entries**

### 1.3 Event Coverage by Discipline

| Discipline | Segment | Events | Entries |
|-----------|---------|--------|---------|
| Ice Dance | Rhythm Dance | 17 | 363 |
| Ice Dance | Free Dance | 17 | 269 |
| Men Single Skating | Short Program | 17 | 434 |
| Men Single Skating | Free Skating | 17 | 341 |
| Pair Skating | Short Program | 17 | 248 |
| Pair Skating | Free Skating | 16 | 204 |
| Women Single Skating | Short Program | 16 | 401 |
| Women Single Skating | Free Skating | 16 | 318 |
| Team Event (4 disciplines × 2 segments) | Various | 8 | 59 |

---

## 2. Source Tables

These tables hold data extracted directly from ISU documents. No analytical transformation has been applied.

---

### 2.1 `competitions` — 17 rows

One row per competition.

| Column | Type | Description |
|--------|------|-------------|
| `competition_id` | INTEGER PK | Surrogate key |
| `season` | TEXT | ISU season string, e.g., `2025/26` |
| `name` | TEXT NOT NULL | Full competition name |
| `organizer` | TEXT | Organizing body (always ISU) |
| `location` | TEXT | City/venue, e.g., `Milano Ice Skating Arena (Milano, ITA)` |
| `start_date` | TEXT | ISO 8601 date, e.g., `2026-02-06` |
| `end_date` | TEXT | ISO 8601 date |
| `results_root_url` | TEXT | Base URL of ISU results page for this competition |

**Source:** Manually entered / scraped from ISU results index pages.

---

### 2.2 `events` — 141 rows

One row per scored segment (e.g., Men SP, Ice Dance FD).

| Column | Type | Description |
|--------|------|-------------|
| `event_id` | INTEGER PK | Surrogate key |
| `competition_id` | INTEGER NOT NULL | FK → `competitions` |
| `discipline` | TEXT NOT NULL | `Ice Dance`, `Men Single Skating`, `Pair Skating`, `Women Single Skating`, `Team Event - *` |
| `segment` | TEXT NOT NULL | `Short Program`, `Free Skating`, `Rhythm Dance`, `Free Dance` |
| `level` | TEXT | Always `Senior` in this dataset |
| `scheduled_datetime_local` | TEXT | ISO 8601 datetime with timezone offset |
| `venue` | TEXT | Venue name |
| `segment_results_url` | TEXT | URL of segment results HTML page |
| `judges_details_pdf_url` | TEXT | Direct URL to the Judges Details PDF |
| `panel_of_judges_url` | TEXT | URL of the panel-of-judges HTML page |

**Source:** ISU results website index pages; URLs extracted from HTML.

---

### 2.3 `entries` — 2,637 rows

One row per competitor/team per segment. These are the **official final scores** as published by ISU.

| Column | Type | Description |
|--------|------|-------------|
| `entry_id` | INTEGER PK | Surrogate key |
| `event_id` | INTEGER NOT NULL | FK → `events` |
| `team_name` | TEXT NOT NULL | Display name (e.g., `KAGIYAMA Yuma`, `CHOCK Madison / BATES Evan`) |
| `noc` | TEXT | IOC 3-letter National Olympic Committee code (e.g., `JPN`, `USA`) |
| `start_no` | INTEGER | Draw number (order of performance) |
| `rank` | INTEGER | Official final rank for this segment |
| `tes` | REAL | Total Element Score — sum of all element scores after trimmed-mean GOE |
| `pcs` | REAL | Program Component Score total — sum of (trimmed-mean component mark × factor) |
| `deductions` | REAL | Time/fall deductions. **Sign convention varies**: 668 entries store as negative (e.g., −1.0), 56 entries store as positive (e.g., 1.0); TSS formula accommodates both |
| `tss` | REAL | Total Segment Score = TES + PCS − \|deductions\|. Verified 100% for all 2,637 entries |
| `skater1` | TEXT | Primary skater name (redundant with team_name for singles) |
| `skater2` | TEXT | Second skater name for pairs/ice dance; NULL for singles |

**Source:** Judges Details PDF — summary results table at top of document.

**Range checks:** TSS 32.63 – 227.79; mean 92.53.

---

### 2.4 `judges` — 1,278 rows

One row per judge per event. Judges are **anonymous** in ISU documents for most competitions; names appear only at select events (OWG, some Worlds).

| Column | Type | Description |
|--------|------|-------------|
| `judge_id` | INTEGER PK | Surrogate key |
| `event_id` | INTEGER NOT NULL | FK → `events` |
| `judge_position` | TEXT NOT NULL | Panel slot: `J1` through `J9` |
| `judge_name` | TEXT | Judge full name, if disclosed; NULL if anonymous |
| `country_code` | TEXT | Judge nationality (2–3 letter code); NULL if anonymous |

**Source:** Panel-of-judges HTML page.
**Coverage:** 1,278 records across 142 events (141 scored + 1 event with two panels). All events have exactly 9 judges.

---

### 2.5 `elements` — 22,380 rows

One row per scored element per entry. An "element" is a single jump, spin, step sequence, lift, or twizzle set that appears in the program.

| Column | Type | Description |
|--------|------|-------------|
| `element_id` | INTEGER PK | Surrogate key |
| `entry_id` | INTEGER NOT NULL | FK → `entries` |
| `element_no` | INTEGER NOT NULL | Sequence position within the program (1, 2, 3, …) |
| `element_code` | TEXT NOT NULL | ISU element notation, e.g., `4T+3T`, `CCSp4`, `SqTwW4+SqTwM4`. Includes call annotations: `<` (under-rotated), `<<` (severely under-rotated), `!` (wrong edge), `q` (quarter), `*` (invalid), `e` (wrong edge), `+REP` (repeated), `+SEQ` (sequence) |
| `base_value` | REAL | Base Value (BV) in points, pre-assigned by ISU Scale of Values. Reflects the difficulty tier called by the Technical Panel. Range: 0.40 – 19.47; mean 5.08 |
| `panel_goe_points` | REAL | Trimmed-mean GOE × GOE scale factor = GOE point value added to BV |
| `panel_element_score` | REAL | Final element score = base_value + panel_goe_points |
| `goe_factor_inferred` | REAL | Inferred scale factor (panel_goe_points / trimmed_mean_goe); used for raw-score reconstruction |

**Source:** Judges Details PDF — element-by-element table.

**Note:** `base_value` is set by the Technical Panel's live call of element level/type, not the judging panel. The 9 judges score only GOE (Grade of Execution).

---

### 2.6 `element_judge_scores` — 200,715 rows

One row per element per judge: the individual GOE integer grade each of the 9 judges assigned.

| Column | Type | Description |
|--------|------|-------------|
| `element_id` | INTEGER NOT NULL PK | FK → `elements` |
| `judge_id` | INTEGER NOT NULL PK | FK → `judges` |
| `judge_goe_int` | INTEGER | Individual GOE grade: integer from −5 to +5 |

**Source:** Judges Details PDF — individual judge columns in the element table.

**Coverage:** 97.5% of elements have all 9 judge scores (21,819 / 22,380). The 2.5% gap (561 elements) reflects legitimate scoring absences: falls on jump attempts that void the element score, elements judged by fewer than 9 panelists in rare circumstances, or elements where one judge's score is not recorded. An additional 144 elements have 7 judge scores (from the 4CC 2022 Ice Dance events, which operated with a 7-judge panel).

**GOE scale:** −5 to +5 integers. A value of 0 is valid (average execution). The ISU trimmed mean drops the single highest and lowest of the 9 scores, then averages the remaining 7 (or 5 for 7-judge panels).

---

### 2.7 `pcs_components` — 9,610 rows

One row per Program Component Score component per entry. The number of components per entry varies by era and discipline (5 components pre-2022/23, 3 components from 2022/23 onward for most disciplines).

| Column | Type | Description |
|--------|------|-------------|
| `pcs_id` | INTEGER PK | Surrogate key |
| `entry_id` | INTEGER NOT NULL | FK → `entries` |
| `component_name` | TEXT NOT NULL | Component label. Current (post-2022/23): `Skating Skills`, `Composition`, `Presentation`. Legacy: `Transitions`, `Performance / Execution`, `Choreography / Composition`, `Interpretation / Timing`, etc. |
| `factor` | REAL | ISU multiplication factor applied to the trimmed-mean mark. Ice Dance: 1.33 (RD) / 1.33 (FD); Singles/Pairs: 1.0 (SP) / 2.0 (FS) / 1.6 (FS for some seasons) |
| `panel_component_avg` | REAL | Trimmed-mean component mark (panel average after dropping 1 high and 1 low of 9 judges, or 1 of 7) |

**Source:** Judges Details PDF — PCS table.

**Data quality note:** `panel_component_avg` values for Men, Women, and Pairs events are stored as integers (1.0, 2.0, … 10.0) in 6,918 components — a parser artifact. These stored averages are not used in analysis. The `entries.pcs` total (which IS correct for all entries) is used instead. Ice Dance and Team Event PCS stored averages are valid. See Section 4.2.

---

### 2.8 `pcs_judge_scores` — 86,520 rows

One row per PCS component per judge: the individual mark each of the 9 judges assigned to each component.

| Column | Type | Description |
|--------|------|-------------|
| `pcs_id` | INTEGER NOT NULL PK | FK → `pcs_components` |
| `judge_id` | INTEGER NOT NULL PK | FK → `judges` |
| `judge_mark` | REAL | Individual judge mark, scale 0.25–10.00 in 0.25 increments |

**Source:** Judges Details PDF — individual judge columns in the PCS table.

**Coverage:** 96.6% of components have all 9 judge marks (9,280 / 9,610). The 330 exceptions include: 100 components from the 4CC 2022 Ice Dance events (7-judge panels) and 230 components that appear to be a parsing artifact (10 marks stored; these are from a small number of events and are excluded from trimmed-mean validation).

**Data quality note:** For Men, Women, and Pairs events, 16,432 of the individual judge marks stored in this table are zero (0.0). A PCS mark of 0.0 is not a valid ISU score (minimum is 0.25). These zeros are a parser artifact from the singles/pairs PDF format, which differs structurally from the Ice Dance format. Ice Dance judge marks (19,726 rows) contain zero zeros and are fully valid. The LOJO counterfactual analysis uses stored `entries.pcs` for affected disciplines rather than recomputing from these judge marks.

---

### 2.9 `sources` — 44 rows

Provenance record for each source file retrieved.

| Column | Type | Description |
|--------|------|-------------|
| `source_id` | INTEGER PK | Surrogate key |
| `event_id` | INTEGER | FK → `events` (NULL for index pages) |
| `source_type` | TEXT NOT NULL | `judges_details_pdf`, `panel_of_judges`, or `event_index` |
| `url` | TEXT NOT NULL | Original URL retrieved |
| `retrieved_utc` | TEXT | ISO 8601 retrieval timestamp |
| `sha256` | TEXT | SHA-256 hash of file contents for integrity verification |
| `local_path` | TEXT | Relative path to archived local copy under `isu_pdfs/` |
| `content_type` | TEXT | MIME type (`application/pdf` or `text/plain`) |
| `bytes` | INTEGER | File size in bytes |

---

### 2.10 `ingest_runs` — 1 row

Log of database population runs.

| Column | Type | Description |
|--------|------|-------------|
| `ingest_id` | INTEGER PK | Surrogate key |
| `run_utc` | TEXT NOT NULL | ISO 8601 timestamp of ingest |
| `notes` | TEXT | Description of what was ingested |

---

### 2.11 `event_labels` — 136 rows

Key-value metadata tags for events (short display labels used in reporting).

| Column | Type | Description |
|--------|------|-------------|
| `event_id` | INTEGER NOT NULL PK | FK → `events` |
| `label_key` | TEXT NOT NULL PK | Tag name, e.g., `competition`, `event_context`, `discipline_raw`, `segment_raw`, `event_date` |
| `label_value` | TEXT NOT NULL PK | Tag value, e.g., `OWG 2026`, `Individual Event`, `2026-02-10` |

---

## 3. Derived Tables

These tables are computed from source tables by project analysis scripts. No original ISU data is stored here.

---

### 3.1 `judge_event_statistics` — 1,269 rows

Per-judge, per-event summary statistics for GOE scoring behavior. One row per judge per event (9 rows per event).

| Column | Type | Description |
|--------|------|-------------|
| `judge_id` | INTEGER NOT NULL PK | FK → `judges` |
| `event_id` | INTEGER NOT NULL PK | FK → `events` |
| `judge_position` | TEXT NOT NULL | `J1`–`J9` |
| `judge_name` | TEXT | From judges table |
| `judge_country` | TEXT | From judges table |
| `num_skaters_judged` | INTEGER | Number of competitors this judge scored |
| `num_elements_judged` | INTEGER | Total elements scored by this judge |
| `mean_goe_deviation` | REAL | Mean of (judge_goe − trimmed_mean_goe) across all elements |
| `median_goe_deviation` | REAL | Median of deviations |
| `sum_goe_deviation` | REAL | Sum of deviations |
| `bias_z_score` | REAL | Z-score of mean_goe_deviation across the panel |
| `positive_bias_count` | INTEGER | Elements where judge scored above trimmed mean |
| `negative_bias_count` | INTEGER | Elements where judge scored below trimmed mean |
| `neutral_count` | INTEGER | Elements where judge matched trimmed mean |
| `mean_absolute_deviation` | REAL | Mean of \|judge_goe − trimmed_mean_goe\| |
| `std_deviation` | REAL | Standard deviation of deviations |
| `correlation_with_panel` | REAL | Pearson r between judge scores and panel trimmed means |
| `outlier_count` | INTEGER | Elements where judge was extreme (outside ±2 SD) |
| `outlier_percentage` | REAL | outlier_count / num_elements_judged |
| `has_home_country_skaters` | BOOLEAN | Whether any competitor shares judge's country |
| `home_country_mean_goe` | REAL | Mean deviation for same-country competitors |
| `other_country_mean_goe` | REAL | Mean deviation for other-country competitors |
| `home_country_differential` | REAL | home_country_mean_goe − other_country_mean_goe |
| `home_country_z_score` | REAL | Z-score of home country differential |
| `min_goe` / `max_goe` / `goe_range` | INTEGER | Min, max, and range of this judge's GOE scores |
| `mean_goe` / `median_goe` | REAL | Central tendency of this judge's raw GOE scores |
| `num_negative_goe` / `num_zero_goe` / `num_positive_goe` | INTEGER | Counts by sign |
| `calculated_at` | TIMESTAMP | Computation timestamp |

**Computed by:** `calculate_statistics.py`

---

### 3.2 `judge_entry_totals` — 2,026 rows

Reconstructed per-judge total score for each competitor. Shows what each judge's individual marks would yield if that judge alone determined the score (no trimming).

| Column | Type | Description |
|--------|------|-------------|
| `event_id` | INTEGER NOT NULL | FK → `events` |
| `entry_id` | INTEGER NOT NULL PK | FK → `entries` |
| `judge_id` | INTEGER NOT NULL PK | FK → `judges` |
| `reconstructed_total` | REAL | TES + PCS reconstructed using only this judge's GOE and PCS marks |
| `reconstructed_tes` | REAL | TES component using only this judge's GOE marks |
| `reconstructed_pcs` | REAL | PCS component using only this judge's PCS marks |

**Computed by:** `calculate_statistics.py`

---

### 3.3 `pairwise_judge_statistics` — 269,957 rows

The core statistical table for the OSNR bias test. One row per judge per ordered pair of competitors (A, B) per event, recording the pairwise bias statistic BI(j, A, B) and its exact combinatorial p-value.

| Column | Type | Description |
|--------|------|-------------|
| `pairwise_stat_id` | INTEGER PK | Surrogate key |
| `judge_id` | INTEGER NOT NULL | FK → `judges` |
| `event_id` | INTEGER NOT NULL | FK → `events` |
| `entry_id_a` | INTEGER NOT NULL | FK → `entries` — the higher-ranked competitor (A) |
| `entry_id_b` | INTEGER NOT NULL | FK → `entries` — the lower-ranked competitor (B) |
| `skater_a_name` / `skater_a_country` / `skater_a_rank` | TEXT / TEXT / INTEGER | Denormalized identifiers for A |
| `skater_b_name` / `skater_b_country` / `skater_b_rank` | TEXT / TEXT / INTEGER | Denormalized identifiers for B |
| `judge_position` / `judge_name` / `judge_country` | TEXT | Denormalized from `judges` |
| `bias_statistic` | REAL NOT NULL | BI(j, A, B) = sum(judge_j GOE deviations for A's elements) − sum(judge_j GOE deviations for B's elements). Positive values indicate this judge favoured A relative to the panel consensus |
| `num_elements_a` / `num_elements_b` / `total_elements` | INTEGER | Element counts used in computing BI(j) |
| `p_value` | REAL | Exact one-sided p-value: `extreme_count / num_permutations`. Fully deterministic — no random sampling, no seed |
| `num_permutations` | INTEGER | Exact total combinations C(2k, k) — e.g., 48,620 for a 9-element program (k=9), 252 for k=5 |
| `test_type` | TEXT | Always `one-sided-exact` |
| `permutation_z_score` | REAL | Z-score of observed BI(j) relative to the exact null distribution |
| `extreme_count` | INTEGER | Raw numerator of p-value: number of exact splits with simulated BI(j) ≥ observed BI(j). E.g., 36 means 36 of 48,620 splits were as extreme or more extreme |
| `mean_deviation_a` / `mean_deviation_b` | REAL | Mean peer-median deviation across all elements for competitor A / B |
| `differential` | REAL | mean_deviation_a − mean_deviation_b |
| `is_significant_01` | BOOLEAN | 1 if p_value ≤ 0.01 (OSNR Tier 1 flag threshold) |
| `is_significant_001` | BOOLEAN | 1 if p_value ≤ 0.001 (OSNR Tier 2 action threshold) |
| `is_significant_bonferroni` | BOOLEAN | 1 if p_value < 0.001 / num_pairs_in_event (Bonferroni-corrected threshold; strict < intentional) |
| `calculated_at` | TIMESTAMP | Computation timestamp |

**Computed by:** `calculate_pairwise_statistics_v3.py`
**Counts:** To be confirmed after v3 run completes. V2 (Monte Carlo) found 1,775 pairs at p ≤ 0.001; v3 exact counts may differ slightly at threshold boundaries.

---

### 3.4 `raw_panel_scores` — 2,637 rows

Counterfactual scores under Regime 0 — what each competitor's TSS would have been with no trimming at all (straight average of all 9 judge GOE marks).

| Column | Type | Description |
|--------|------|-------------|
| `entry_id` | INTEGER PK | FK → `entries` |
| `raw_tes` | REAL | TES reconstructed using straight mean (not trimmed mean) of 9 GOE marks |
| `raw_pcs` | REAL | PCS reconstructed using straight mean (not trimmed mean) of 9 judge marks |
| `raw_tss` | REAL | raw_tes + raw_pcs − \|deductions\| |
| `computed_at` | TEXT | ISO 8601 computation timestamp |

**Computed by:** `calculate_raw_average.py`
**Average raw_tss = 80.13** vs. official mean of 92.53, a difference of −12.40 points. The trim raises published scores because at elite level the lowest judge GOE scores are disproportionately removed.

---

### 3.5 `lojo_scores` — 23,733 rows

Counterfactual scores under Regime 2 (LOJO: Leave-One-Judge-Out). For every event × judge × competitor combination, records what the competitor's TSS and rank would have been had that judge been removed and the trimmed mean recomputed from the remaining 8 judges (or 6 for 7-judge panels).

| Column | Type | Description |
|--------|------|-------------|
| `lojo_id` | INTEGER PK | Surrogate key |
| `event_id` | INTEGER NOT NULL | FK → `events` |
| `judge_id` | INTEGER NOT NULL | FK → `judges` — the judge being removed |
| `judge_position` | TEXT | `J1`–`J9` |
| `entry_id` | INTEGER NOT NULL | FK → `entries` |
| `cf_tss` | REAL | Counterfactual TSS with this judge removed |
| `cf_rank` | INTEGER | Counterfactual rank among all competitors in the event |
| `official_rank` | INTEGER | Official published rank |
| `rank_change` | INTEGER | cf_rank − official_rank (positive = fell, negative = rose) |

**Computed by:** `calculate_lojo_full.py`
**PCS note:** For 99 singles/pairs events where individual PCS judge marks are corrupt (parser artifact), `cf_tss = cf_tes + stored_pcs`. The TES component is fully recomputed judge-by-judge; PCS is held at the official stored value. This is recorded in `lojo_event_summary.pcs_mode`.

---

### 3.6 `lojo_event_summary` — 1,269 rows

Event-level summary of the LOJO analysis. One row per event × judge. The primary source for the Kendall tau disruption metric Δτ(j).

| Column | Type | Description |
|--------|------|-------------|
| `summary_id` | INTEGER PK | Surrogate key |
| `event_id` | INTEGER NOT NULL | FK → `events` |
| `judge_id` | INTEGER NOT NULL | FK → `judges` |
| `judge_position` | TEXT | `J1`–`J9` |
| `judge_name` | TEXT | From judges table (NULL if anonymous) |
| `n_entries` | INTEGER | Number of competitors with counterfactual TSS computed |
| `winner_changes` | INTEGER | 1 if removing this judge changes the gold medal winner; 0 otherwise |
| `podium_changes` | INTEGER | 1 if removing this judge changes the ordered top-3 result (i.e., any of gold, silver, or bronze positions is held by a different competitor, OR the same competitors appear in a different order); 0 otherwise |
| `n_rank_inversions` | INTEGER | Number of competitor pairs whose relative ranking flips under counterfactual |
| `total_pairs` | INTEGER | Total number of ordered competitor pairs C(n,2) |
| `kendall_tau_distance` | REAL | Δτ(j) = n_rank_inversions / total_pairs. Range 0–1; 0 = no disruption, 1 = all pairs inverted |
| `actual_winner_name` | TEXT | Official event winner |
| `cf_winner_name` | TEXT | Counterfactual winner with this judge removed |
| `actual_margin` | REAL | Official winning margin (1st − 2nd place TSS) |
| `cf_margin` | REAL | Counterfactual winning margin |
| `pcs_mode` | TEXT | `recomputed` (Ice Dance + Team events, 42 events) or `stored` (singles/pairs, 99 events) |

**Key results:**
- Mean Δτ(j) = 0.033; max = 0.267
- 157 winner-change judge removals (`winner_changes=1`) across the full dataset
- 478 podium-change judge removals (`podium_changes=1`) — includes reorderings within the top-3
- **153 OSNR Tier-2 flags** (podium change + p ≤ 0.001) across 47 events

**OSNR Tier 2 rule:** A judge is Tier 2 flagged when BOTH (a) `podium_changes = 1` (removing them changes any top-3 position by membership or order), AND (b) `sig001 > 0` (at least one pairwise pair reaches p ≤ 0.001). `winner_changes` is retained for reference but is not the Tier 2 criterion.

---

### 3.7 `integrity_checks` — 7 rows

Automated verification results confirming consistency between stored and recomputed values.

| Column | Type | Description |
|--------|------|-------------|
| `check_id` | INTEGER PK | Surrogate key |
| `check_name` | TEXT | Description of the check |
| `total_checked` | INTEGER | Number of records tested |
| `passed` | INTEGER | Number passing within tolerance |
| `failed` | INTEGER | Number failing |
| `pass_rate` | REAL | passed / total_checked |
| `notes` | TEXT | Explanation of methodology, tolerance, and any exceptions |
| `run_at` | TEXT | ISO 8601 computation timestamp |

**Summary of checks:**

| Check | Pass Rate |
|-------|-----------|
| TES reconstruction (element scores sum to stored TES) | 100.0% |
| TSS = TES + PCS ± deductions | 100.0% |
| PCS trimmed mean — 9-judge valid components | 100.0% |
| PCS trimmed mean — 7-judge components (4CC 2022) | 100.0% |
| GOE 9-judge full coverage | 97.5% |
| PCS 9-judge full coverage | 96.6% |
| Ice Dance PCS judge marks > 0 (no corrupt zeros) | 100.0% |

---

## 4. Known Data Limitations

### 4.1 Judge Anonymity
ISU policy conceals judge identities at most competitions. Judge names and nationalities are available only at select events where disclosure is required (Olympic Games, some World Championships). For anonymous events, `judges.judge_name` and `judges.country_code` are NULL. Statistical analysis is conducted on position (J1–J9), which is randomized each event, making position an unbiased surrogate for identity within a single event.

### 4.2 PCS Judge Marks — Singles and Pairs Events
Individual PCS judge marks in `pcs_judge_scores` are invalid (contain zeros) for all 99 Men Single, Women Single, and Pair Skating events. This is a parser artifact: the singles/pairs Judges Details PDF uses a different page layout than Ice Dance, and the PCS section was not correctly extracted. **The stored `entries.pcs` total is correct for all entries** (verified by the TSS integrity check at 100%). Analytical impact:

- BI(j) bias statistic is unaffected (computed from GOE only)
- LOJO TES counterfactuals are unaffected (computed from GOE only)
- LOJO TSS counterfactuals for singles/pairs use stored `entries.pcs` (held constant across all judge removals for a given entry); only TES varies

### 4.3 Technical Panel Calls
The `elements.base_value` reflects the Technical Panel's live determination of element type and quality level. Base values are pre-assigned by the ISU Scale of Values table; the Technical Panel calls which row of that table applies (e.g., whether a jump landed clean or with a quarter-turn under-rotation). Technical Panel calls are not recorded in this database and are outside the scope of this study.

### 4.4 Deductions Sign Convention
Deductions are stored as negative values for 668 entries and as positive values for 56 entries, reflecting an inconsistency in the original PDF format across different competitions. All formulas in the analysis accommodate both conventions. TSS verification passes at 100% using the formula: TSS = TES + PCS − |deductions|.

### 4.5 4CC 2022 Ice Dance — 7-Judge Panel
The ISU Four Continents Figure Skating Championships 2022 Ice Dance events (Rhythm Dance and Free Dance) operated with a 7-judge panel rather than the standard 9. The trimmed mean for these events drops 1 high and 1 low, averaging the remaining 5. All checks for these events use the 5-judge average formula.

### 4.6 10-Judge PCS Components
230 PCS components in the database have 10 judge marks stored. This is a parser artifact from a small number of events. These components are excluded from trimmed-mean validation checks. They represent less than 2.4% of total PCS components.

### 4.7 Competition Coverage
The database covers 16 competitions from 5 ISU seasons (2021/22 through 2025/26). It does not include ISU Grand Prix series individual events (only the Grand Prix Final), ISU Challenger Series, junior competitions, or national championships.

---

## 5. Relationships Between Tables

```
competitions ──< events ──< entries ──< elements ──< element_judge_scores
                   │              │           │              │
                   │              │           │              └── (judge_id) ──> judges
                   │              │           └── element_judge_deviations (element_id, judge_id)
                   │              │                      │
                   │              │                      └── (judge_id) ──> judges
                   │              └── pcs_components ──< pcs_judge_scores
                   │                      │
                   │                      └── (judge_id) ──> judges
                   └──────────────────────────────────────────> judges
                                          │
                              pairwise_judge_statistics (judge_id, entry_id_a, entry_id_b)
                              judge_event_statistics (judge_id, event_id)
                              judge_entry_totals (judge_id, entry_id)
                              lojo_scores (judge_id, entry_id)
                              lojo_event_summary (judge_id, event_id)
                              raw_panel_scores (entry_id)
```

---

### 3.8 `element_judge_deviations` — 202,272 rows

Peer-median deviation for every (element, judge) combination. This table stores the **Stage 2** intermediate values that the BI(j) pairwise bias test is built from. Stage 1 (raw GOE integers) is already stored in `element_judge_scores`; Stage 2 (deviations from the panel median) is stored here for full auditability and external reproducibility.

| Column | Type | Description |
|--------|------|-------------|
| `deviation_id` | INTEGER PK | Surrogate key |
| `event_id` | INTEGER NOT NULL | FK → `events` |
| `entry_id` | INTEGER NOT NULL | FK → `entries` |
| `element_id` | INTEGER NOT NULL | FK → `elements` |
| `judge_id` | INTEGER NOT NULL | FK → `judges` |
| `judge_position` | TEXT | Panel slot: `J1`–`J9` |
| `goe_int` | INTEGER NOT NULL | Judge's raw GOE score for this element (mirrors `element_judge_scores.judge_goe_int`) |
| `peer_median` | REAL NOT NULL | Median of the **other 8 judges'** GOE scores for this element — the panel consensus benchmark |
| `deviation` | REAL NOT NULL | `goe_int − peer_median` — the building block of BI(j). Positive = judge rated this competitor above consensus on this element; negative = below |

**Deviation formula** (replicates `get_deviations()` in `calculate_pairwise_statistics.py`):
```
deviation = judge's GOE integer − median of the other 8 judges' GOE on this element
```
The median is the true mathematical median of the 8 other judges' scores — the average of the 4th and 5th values when sorted ascending (SQL: average of `OFFSET 3` and `OFFSET 4`). This can produce .5 values when the two middle scores differ. Computed by `calculate_pairwise_statistics_v2.py` in `figure_skating_ijs_v2.sqlite`. Note: the original database (`figure_skating_ijs_seed.sqlite`) used SQL `LIMIT 1 OFFSET 4` (upper median = 5th value only), which always yields an integer.

**How BI(j) is derived from this table:**
For a judge J and competitor pair (A, B):
- Sum J's deviations across all elements for A → S(A)
- Sum J's deviations across all elements for B → S(B)
- BI(j) = S(A) − S(B)

**Computed by:** `populate_element_deviations.py`

**Verification:** For OWG 2026 Ice Dance Free Dance, J1 (Dabouis) vs. FRA/USA pair: sum(FRA deviations) = +1.00, sum(USA deviations) = −7.00, BI(j) = +8.00. Exact test: 36 of 48,620 splits produce BI(j) ≥ +8.00 → p = 0.000740. Stored in `pairwise_judge_statistics` as `extreme_count=36`, `num_permutations=48620`, `p_value=0.000740`. ✓

---

*End of Data Dictionary v1.1 — updated 2026-02-21 to add `element_judge_deviations` (Stage 2 audit table)*
