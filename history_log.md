# History Log — Judging Bias Project
## Session and Decision Record

**Project:** OSNR — Outlier Score Notification Rule
**Researcher:** Michael Allman
**Log created:** February 22, 2026
**Purpose:** Detailed chronological record of work sessions, decisions made, documents created, and files moved or modified.

> Sessions 1–24 archived at: `archive/docs/status_reports/`

---

## Session 28 — 2026-02-22: Free Dance RDT + Reconciliation with Statistician's Analysis

**Goal:** Reconcile differences between my RD analysis and statistician's independent analysis. Turned out to be different events; extended to produce the FD analysis and upgrade both documents to use Holm correction.

### Key Findings

- **event_id=1** = OWG 2026 Ice Dance **Rhythm Dance** (23 teams, 115 elements per judge)
- **event_id=2** = OWG 2026 Ice Dance **Free Dance** (20 teams, 184 elements per judge, variable 9-10 per team)
- The two analyses were on different events with completely different judge panels — no conflict
- Underlying GOE data verified to match exactly between our DB and the statistician's analysis (every mean, SD, t-stat identical)
- One real methodological difference: statistician used **Holm** correction; my documents used **Bonferroni**. Holm adopted going forward as primary.

### FD Results (event_id=2, Holm correction)
- **J7 Isabella MICHELI**: mean −0.3478, t=−5.857, p_holm < 0.0001 *** (strongest signal; 79 neg / 77 zero / 28 pos; three −3 deviations)
- **J5 Janis ENGEL**: mean −0.2228, t=−5.000, p_holm < 0.0001 ***
- J3 marginal (p=0.0116 uncorrected, p_holm=0.081 — does not survive)
- All others: not significant

### RD Holm update (no change to conclusions)
- J1 p_holm < 0.0001, J7 p_holm < 0.0001, J2 p_holm=0.0065 — same 3 judges as before
- J6 p_holm=0.283 — confirmed not significant after correction

### Files Created/Modified
- `residual_deviation_owg2026_ice_dance_fd.md` — new
- `residual_deviation_owg2026_ice_dance_fd.docx` — new
- `residual_deviation_owg2026_ice_dance_rd.md` — updated (Holm column added, Bonferroni language updated)
- `residual_deviation_owg2026_ice_dance_rd.docx` — regenerated with Holm column

### State at Session End
- Both RD and FD analyses complete and documented
- Holm correction now standard across all RDT documents
- DB verified correct for both events (raw scores match statistician's source data exactly)

---

## Session 27 — 2026-02-22: Residual Deviation Test + peer_median DB Repair

**Goal:** Apply the Residual Deviation test to OWG 2026 Ice Dance RD, document results, and repair the `element_judge_deviations` peer_median rounding bug discovered during analysis.

### Work Done

1. **Residual Deviation documents** — created `residual_deviation_owg2026_ice_dance_rd.md` and `.docx`. Fully standalone (no BI(j) references). Addressed user's four analytical questions in Discussion section: level bias vs favoritism, why Mean/SD < 1 gives p < 0.0001, J5 rounding bug correction, over-flagging assessment with Bonferroni.

2. **peer_median bug discovered** — while investigating why J5 showed p=0.002 with stored deviations but p=0.117 from raw recomputation. Root cause: `populate_element_deviations.py` (v1) used `OFFSET 4` (5th sorted value of 8) instead of the true `(4th + 5th) / 2.0` median. 18.8% of all rows affected.

3. **DB repair** — new script `repair_element_deviations_median.py`:
   - Backed up: `figure_skating_ijs_seed.sqlite.bak`
   - Dry-run confirmed 15.3% affected in 1,000-row sample
   - Full repair: 37,732 rows updated (peer_median + deviation)
   - Verified: 36,561 half-integer peer_median values; `PRAGMA integrity_check` = ok

4. **pairwise_test_diagnosis documents** — created `pairwise_test_diagnosis.md` and `.docx` documenting the BI(j) exchangeability violation: 272,072 tests, 2,812 at p≤0.001 (~560× expected), 86/144 events with 2+ judges simultaneously flagged.

### Decisions Made
- peer_median repair targets `figure_skating_ijs_seed.sqlite` only (`figure_skating_ijs_v3.sqlite` has 0 rows in this table, no repair needed)
- Residual Deviation documents use fresh recomputation from `element_judge_scores` (not stored table) as authoritative

### Files Created/Modified
- `residual_deviation_owg2026_ice_dance_rd.md` — new
- `residual_deviation_owg2026_ice_dance_rd.docx` — new
- `pairwise_test_diagnosis.md` — new
- `pairwise_test_diagnosis.docx` — new
- `repair_element_deviations_median.py` — new
- `figure_skating_ijs_seed.sqlite` — repaired (peer_median + deviation in element_judge_deviations)
- `figure_skating_ijs_seed.sqlite.bak` — backup pre-repair

### State at Session End
- `figure_skating_ijs_seed.sqlite`: element_judge_deviations fully repaired
- `figure_skating_ijs_v3.sqlite`: canonical pairwise+LOJO database; element_judge_deviations empty (not used for pairwise stats)
- Residual Deviation test established as a working analysis tool
- Next: decide whether to implement Residual Deviation as the primary replacement for BI(j) across all 144 events

---

## Session 26 — 2026-02-22 (continuation): Excel Scoring Files — Structural Fix & Regeneration

**Goal:** Fix `generate_official_scoring_xlsx.py` so the 144 generated Excel files exactly match the structure of the reference model `OWG2026_RD_Scoring_Model.xlsx`, then regenerate all files.

### Structural Problems Found

Comparing the previously generated files to the reference model revealed multiple differences:

| Issue | Previous | Correct (reference) |
|---|---|---|
| Col F | "Info" (element_info field) | **Multiplier** (ISU GOE factor) |
| Col Q | Hardcoded Panel GOE value | Live formula `=ROUND(P/(COUNT(G:O)-2)*F,2)` |
| Extra col T | Yes (TES) | No — TES belongs in col S |
| TES placement | Col T, first element row | Col S, **last** element row per entry |
| Freeze panes | D5/D5 | G5 (Element Scores) / F5 (PCS) |
| Row heights | Row 3=30pt, Row 4=45pt | Row 3=18pt, Row 4=60pt |
| Merged cells | None | A/B/C merged across element rows and component rows per entry |
| PCS Panel Avg | 2dp `ROUND(O/7,2)` | 2dp (confirmed correct — see note below) |
| Component order | DB insertion order (Composition first for ice dance) | ISU canonical order (Skating Skills first) |

### goe_factor_inferred — Resolved

User asked whether `goe_factor_inferred` should be kept since it was "reverse-engineered." Research confirmed it is the **ISU-published GOE multiplier** from ISU Communications, hardcoded in `populate_goe_factors.py`. The name is misleading but the values are authoritative. It remains in the DB and is now displayed as **Multiplier** in column F. Rename to `goe_factor_official` remains a deferred task.

### PCS Panel Avg Precision — Critical Finding

The plan specified 4dp panel avg to match the reference model (`=ROUND(O/7,4)`). After implementing 4dp and regenerating all 144 files, verification showed **454 mismatches** (vs 7 previously).

Root cause: The ISU actually computes panel avg at **2dp** in their scoring system. The reference model's `ROUND(O/7,4)` is a display artifact. Confirmed by checking all 2,706 entries: with 2dp, zero entries have >0.02 mismatch; with 4dp, 177 entries do.

Reverted to 2dp for panel avg. This is documented here to prevent re-introduction.

### Dynamic Judge Count Formula

The reference model uses `/7` (hardcoded, assumes 9-judge panel). Our files cover FC2022 which has 7 judges. Fixed by using `COUNT(G:O)-2` (and `COUNT(F:N)-2` for PCS) — dynamically counts actual judge columns and subtracts 2 for the trimmed-mean drop.

### Script Changes (generate_official_scoring_xlsx.py — full rewrite)

- Removed: Info column (F), column T (extra TES), `panel_goe_points` hardcoded values, `element_info` field from Excel layout
- Added: `PCS_ORDER` list for canonical component sorting, `pcs_sort_key()` helper
- Col F = Multiplier (`goe_factor_inferred` value)
- Col Q = Panel GOE live formula with dynamic judge count
- Col R = Element Score formula
- Col S = TES in **last** element row per entry
- Freeze panes: G5 (Element Scores), F5 (PCS)
- Row heights: 1=22pt, 2=16pt, 3=18pt, 4=60pt
- Merged cells: A/B/C across element rows per entry; A/B/C across component rows per entry
- PCS Panel Avg: `=ROUND(O/(COUNT(F:N)-2),2)` — 2dp, dynamic divisor
- `ignoredErrors` XML patch: col S (TES sparse) and col R (PCS Total sparse)
- Summary: TES links to last element row (col S); PCS links to first component row (col R)

### Verification Results

- 144 files generated, 0 errors
- Pass rate: **99.9%** (4 entries with exactly ±0.02 mismatch)
- All 4 residual mismatches are PCS-only boundary cases: Python banker's rounding vs Excel round-half-up at exact 0.5 — irreducible

### Files Modified

- `generate_official_scoring_xlsx.py` — complete rewrite
- `excel_output/` — 144 .xlsx files regenerated

---

## How to Use This Document

This log is a running record of what was done and why. It is **not** automatically read by Claude at session start (that is MEMORY.md's job). Reference this document when you need to reconstruct why a particular decision was made, what a particular file contains, or what the state of the project was at a given point.

To ask Claude to consult this document, say: *"Read the history log first."*

---

## Session Log

---

### Session: February 22, 2026 (continuation from prior context)

**Context at session start:**
- v4 pairwise computation was live and running (~99% complete)
- `figure_skating_ijs_v3.sqlite` was the active database
- `figure_skating_ijs_seed.sqlite` was the finalized base database
- LOJO had been run previously but against the seed database, not v3

---

#### 1. Data Hierarchy Walkthrough (Levels 1–6)

**What was done:** User asked to be walked through the database hierarchy "from top to bottom" to understand what data was stored at each level.

**Six-level hierarchy established:**

| Level | Table | Count |
|---|---|---|
| 1 | Competitions | 17 |
| 2 | Events | 144 |
| 3 | Entries (competitor-events) | 2,706 |
| 4 | Judge Assignments | 1,305 rows / 198 unique judge IDs |
| 5 | Elements (GOE rows) | 23,043 |
| 6 | Element Judge Scores | 291,604 (206,682 GOE + 84,922 PCS) |

**Key clarifications made:**
- 9 judges per event × 144 events = 1,296 real judge-event assignments. 1,305 total includes 9 ghost rows (see below).
- The "198 unique judge IDs" refers to unique (event_id, judge_position) combinations that appear in the scores, not named individuals.
- Judge anonymity is preserved in the ISU system; judges are known only by position (J1–J9) within each event.

---

#### 2. The 145 vs. 144 Discrepancy Investigation

**What was done:** User flagged a discrepancy noticed earlier: the judges table appeared to reference 145 events (event IDs 1–145 or similar), while the competition roster had 144 events.

**Root cause found:** Event_id 198 is a ghost event in the judges table — 9 placeholder rows with judge positions but no associated entries, no elements, and no scores. This was an artifact of an early ingestion attempt for an OWG 2026 event that was subsequently ingested under a different event_id.

**Impact:** Zero. The 9 ghost rows have no name, no country, and no linked data. All analysis correctly uses 144 events.

**Decision:** Leave the ghost rows in place — removing them would require schema surgery with no analytical benefit.

---

#### 3. The p-Value Count and the 5,184 Test Framework

**What was done:** User worked through the arithmetic of the pairwise test framework:

- 144 events × C(9,2) = 144 × 36 = **5,184 total judge-pair p-tests**
- Under a true null (all judges unbiased): expect ~5 significant results at p ≤ 0.001
- Actual result: **2,812 significant at p ≤ 0.001** (originally ~1,775 from v3 seed run)

**User's intuition:** "The bias cannot be that strong across the board. I'm questioning either our statistic or our programming."

**This was correct.** The discrepancy prompted the statistical deep dive below.

---

#### 4. The Exchangeability Violation — Statistical Deep Dive

**What was done:** Extended research into the statistical literature to diagnose why the B(j) permutation test produces so many false positives.

**The problem identified:** The permutation test has a fundamental structural flaw called the **exchangeability violation**.

The test asks: *"If we randomly swapped judge A's and judge B's scores, how often would we see disagreements this extreme?"*

But this is the wrong question. Both judges watched the same skaters. Their scores are **correlated by the shared performance signal** — skater X is genuinely better than skater Y, and both judges can see this. When the permutation randomly swaps their scores, it destroys that correlation and creates a null distribution that is **far too narrow**. So when reality shows any deviation from perfect agreement — even perfectly normal random variation — the test flags it as significant.

**Key diagnostic numbers:**
- Expected average p-value under true null: 0.500
- Observed average p-value: 0.249
- Expected significant results at p ≤ 0.001: ~5
- Observed significant results at p ≤ 0.001: 2,812
- Ratio: approximately 562× more significant results than expected

**The thermometer analogy:** Testing whether two thermometers agree by randomly swapping their readings between rooms. Of course they look inconsistent — you destroyed the temperature signal. The rooms are genuinely different temperatures. Swapping readings doesn't create a valid null; it destroys the shared signal both instruments track.

**Literature consulted:**
- Kimmel et al. (2008), *Genetics* — "Naive Application of Permutation Testing Leads to Inflated Type I Error Rates." Names this failure mode exactly.
- Emerson, Seltzer & Lin (2009), *The American Statistician* — The definitive figure skating judging paper. Uses **residual deviation** (subtract panel mean, test residuals) — correctly handles the shared performance signal.
- Zitzewitz (2006, 2014) — Uses **regression with skater fixed effects** — equivalent approach.
- Gordon & Truchon (2008) — The correct formal model: true latent performance + judge noise.
- Frandsen (2019) — Confirms LOJO-style counterfactuals are well-grounded.
- Many-Facets Rasch Model — The gold standard for simultaneous estimation of skater ability, judge severity, and element difficulty.
- Friedman test / Generalizability Theory / ICC — All handle the two-way block structure correctly.

**Three fix options documented:**

| Option | Method | Complexity | Notes |
|---|---|---|---|
| 1 | Residual deviation | Simplest | Subtract panel trimmed mean per element; test residuals. Used by Emerson et al. and SkatingScores.com |
| 2 | Friedman test | Rigorous, non-parametric | Two-way block design; Nemenyi post-hoc for outlier ID |
| 3 | Many-Facets Rasch | Gold standard | Simultaneous latent estimation; most defensible for peer review |

**Decision:** Document the problem thoroughly before choosing a fix. No implementation yet.

**What this means for the paper:**
- The 2,812 significant pairs number will drop substantially once the test is corrected
- The OWG 2026 ice dance finding (p ≈ 4.6×10⁻⁵) likely survives correction — a 5-sigma result doesn't vanish — but must be verified
- The LOJO methodology is **unaffected** — it's sound. The problem is only in how we identify which judge-pairs to flag in Tier 1
- The paper must situate itself in the Zitzewitz/Emerson literature and acknowledge the test limitation

---

#### 5. Document Created: methodology_diagnosis_v1.md and .docx

**Decision:** Save the full diagnosis as a document before moving on. User said: *"Save The Diagnosis — Plain English as a .md file and a Word version."*

**Files created:**
- `/Users/allman/Library/CloudStorage/Dropbox/Dropbox Mike/Judging Bias/methodology_diagnosis_v1.md`
- `/Users/allman/Library/CloudStorage/Dropbox/Dropbox Mike/Judging Bias/methodology_diagnosis_v1.docx`

**make_word_docs.py updated:** Added `("methodology_diagnosis_v1.md", "Methodology Diagnosis — The Exchangeability Problem")` to the FILES list so future runs of the script regenerate the .docx automatically.

**Document sections:**
1. The Problem — the numbers
2. The Diagnosis — Plain English (including thermometer analogy)
3. The Good News — LOJO and conceptual model are sound
4. Three Fix Options — residual deviation, Friedman, Rasch
5. What This Means for the Paper
6. Key Citations with URLs

---

#### 6. OWG 2026 Ice Dance Rhythm Dance Spreadsheet Work

**What was done:** User wanted to understand the raw scoring data for the OWG 2026 ice dance Rhythm Dance event and build a clean, formula-driven working model.

**Starting point:** `OWG2026_RD_Raw_Scores.xlsx` — a two-sheet workbook:
- Sheet 1: "Rhythm Dance Raw GOE" — 23 couples × 5 elements, with J1–J9 GOE integers, hardcoded Panel GOE, Element Score, TES, PCS, TSS
- Sheet 2: "Legend"

**First step — Add PCS scores:** User asked to add PCS component data to the spreadsheet. A new "PCS Scores" sheet was added showing three components per couple (Skating Skills, Composition, Presentation) with J1–J9 marks, panel average, component score, and total PCS. This data was read from the database.

**Note:** The original `OWG2026_RD_Raw_Scores.xlsx` was kept unchanged throughout all subsequent work. A new file was created for all restructuring.

---

#### 7. GOE Multipliers — Back-Calculation

**What was done:** The spreadsheet needed a "Multiplier" column to convert trimmed mean GOE integers to GOE score points. These multipliers are not stored in the database. They were back-calculated from actual data.

**Formula:** `factor = panel_goe_points / trimmed_mean_of_judge_integers`

**Multipliers found (consistent across all 23 couples):**

| Element Type | Examples | Multiplier |
|---|---|---|
| Twizzles | SqTw, SyTw | 0.7652 |
| Step Sequences | MiSt, DiSt, CiSt | 1.0439 |
| Pattern Step | PSt | 1.1189 |
| Choreographic Step | ChRS, ChSt | 1.5005 |
| Lifts | RoLi, SlLi, StaLi, etc. | 0.4799 |

**Decision:** Use these precise back-calculated values (not rounded ISU table values) in the spreadsheet. Consistent with 23-couple sample.

---

#### 8. Spreadsheet Created: OWG2026_RD_Scoring_Model.xlsx

**User's request:** Restructure the spreadsheet into "a generic form that has all the data and calculations for any skating event" with live formulas (not hardcoded values), organized so a reader can follow the full scoring chain from raw GOE integers to TSS.

**Decision:** Build from scratch using openpyxl. Original file untouched.

**Output file:** `/Users/allman/Library/CloudStorage/Dropbox/Dropbox Mike/Judging Bias/OWG2026_RD_Scoring_Model.xlsx`

**Four sheets:**

**Sheet 1 — Summary:**
- 23 rows (one per couple), Rank / Team / NOC / TES / PCS / Deductions / TSS
- TES pulls from Element Scores sheet via formula: `='Element Scores'!S{row}`
- PCS pulls from PCS sheet via formula: `='PCS'!R{row}`
- TSS = TES + PCS + Deductions (formula)
- Deductions hardcoded 0.00 (no deductions in this event)
- Dark blue header, alternating white/light blue rows

**Sheet 2 — Element Scores (renamed from "Rhythm Dance Raw GOE"):**
- Added col F: **Multiplier** (element-type-specific, hardcoded per row)
- Added col P: **Trimmed Sum** = `SUM(G:O)-MAX(G:O)-MIN(G:O)` — 7-judge trimmed sum (formula)
- Added col Q: **Panel GOE** = `ROUND(P/7*F, 2)` — trimmed mean × multiplier (formula)
- Added col R: **Element Score** = `ROUND(E+Q, 2)` — base value + Panel GOE (formula)
- Added col S: **TES** = `SUM(R_first:R_last)` — summed across all 5 element rows, merged (formula)
- Removed old hardcoded PCS and TSS columns

**Sheet 3 — PCS (renamed from "PCS Scores"):**
- Added col O: **Trimmed Sum** = `SUM(F:N)-MAX(F:N)-MIN(F:N)` (formula)
- Added col P: **Panel Avg** = `ROUND(O/7, 2)` (formula)
- Added col Q: **Comp. Score** = `ROUND(P*E, 2)` — panel avg × factor (formula)
- Added col R: **Total PCS** = `SUM(Q_first:Q_last)` — summed across all 3 component rows, merged (formula)
- Removed old hardcoded TES/Ded/TSS columns

**Sheet 4 — Legend (unchanged)**

**Bugs encountered and fixed during build:**
1. Merged cell write error — writing to col C after merging B1:C1 raised AttributeError. Fixed by skipping merged cell writes.
2. Summary Deductions column bug — script accidentally read TSS (90.18) into Deductions column. Fixed by hardcoding 0.00 for all deductions rows in a post-processing pass.
3. PCS row reference bug — Summary sheet PCS references pointed to wrong rows because PCS sheet has 4 header rows before data, not 1. Fixed: `pcs_first_row(i) = 5 + i*3` (not `2 + i*3`). Verified rank 1 PCS reference = `='PCS'!R5`.

**Verification:** Rank 1 TSS (Fournier Beaudry/Cizeron) = 90.18 ✓ — matches official results.

---

#### 9. v4 Pairwise Run — Completion Confirmed

**What was done:** Checked status of the v4 pairwise computation (`calculate_pairwise_statistics_v4.py`) that had been running in the background.

**Result:** 144/144 events complete.

**Final pairwise statistics in `figure_skating_ijs_v3.sqlite`:**

| Metric | Count |
|---|---|
| Total pairwise rows | 272,072 |
| Significant at p ≤ 0.001 | 2,812 |
| Significant at p ≤ 0.01 | 11,847 |

**Note on the count increase:** The seed database had ~269,957 pairs and 1,775 significant. The v3 run produced 272,072 pairs and 2,812 significant. The difference reflects (a) some additional events covered, and (b) the known exchangeability inflation documented above — both v3 and seed numbers are inflated by the same structural flaw.

---

#### 10. LOJO Rerun Against v3 Database

**What was done:** The `calculate_lojo_full.py` script had its `DB_PATH` pointing to `figure_skating_ijs_seed.sqlite` rather than the v3 database. Corrected and rerun.

**File modified:** `calculate_lojo_full.py`
- Changed: `DB_PATH = "figure_skating_ijs_seed.sqlite"`
- To: `DB_PATH = "figure_skating_ijs_v3.sqlite"`

**LOJO results (v3 database):**

| Metric | Count |
|---|---|
| LOJO rows computed | 1,288 |
| Tier 2 events (podium_changes > 0 AND sig001 > 0) | 56 |
| Total podium changes across all events | 462 |
| Winner (gold) changes | 150 |

**Note:** The previous LOJO stats in MEMORY.md (153 Tier 2 events) were from the seed database and an older Tier 2 query definition. The updated 56 figure reflects the current Tier 2 rule (must have both podium_changes > 0 AND sig001 > 0 in the pairwise table) applied to the v3 database.

**Open question flagged:** The drop from 153 → 56 Tier 2 events deserves a sanity check to verify that the `is_significant_001` field is correctly populated and the JOIN query is correct. This was noted but not yet resolved.

---

#### 11. MEMORY.md Updated

**What was done:** User confirmed updating MEMORY.md with the new canonical statistics.

**File modified:** `/Users/allman/.claude/projects/-Users-allman-Library-CloudStorage-Dropbox-Dropbox-Mike-Judging-Bias/memory/MEMORY.md`

**Changes:**
- Canonical database updated: `figure_skating_ijs_v3.sqlite` (was seed)
- Final stats updated: 272,072 pairwise rows, 2,812 significant, 56 Tier 2 events
- LOJO stats updated: 1,288 rows, 462 podium changes, 150 winner changes
- OWG 2026 key finding updated: Pairs FS J6 (CHIGOGIDZE, Georgia) flips gold from Miura/Kihara (JPN) to Pavlova/Sviatchenko (HUN)
- Key files list updated
- Methodology warning added: note about exchangeability violation and pending fix
- "See Also" updated to reference `methodology_diagnosis_v1.md` and `debugging.md`

---

#### 12. History Log Created (this document)

**User's request:** *"Yes, but let's call it a history log. It is a summary of what we did and what decisions we made. Can it be reasonably detailed? It can include the decisions we made, the documents you created, what files were moved, all that. Kind of a summary of how we got to where we got to."*

**File created:** `/Users/allman/Library/CloudStorage/Dropbox/Dropbox Mike/Judging Bias/history_log.md`

**Convention for future sessions:** Append a new dated section to this file whenever significant work is done. Claude can be asked to read this file at the start of any session for full project context.

---

## Pending Work (as of February 22, 2026)

### High Priority

**1. Sanity check Tier 2 count (56 events)**
The drop from 153 → 56 Tier 2 events needs verification. Confirm:
- `is_significant_001` field is correctly populated in `pairwise_judge_statistics`
- The LOJO JOIN query correctly references this field
- The 56-event count is correct under the current Tier 2 rule definition

**2. Address the exchangeability methodology problem**
Three options exist (see methodology_diagnosis_v1.md). A decision is needed:
- Option 1 (residual deviation) — simplest, fastest to implement, used by SkatingScores.com
- Option 2 (Friedman test) — statistically rigorous, non-parametric, correct for this data structure
- Option 3 (Many-Facets Rasch) — gold standard for peer review
Once implemented, rerun pairwise statistics. The 2,812 number will drop substantially.

**3. Update paper sections 5–9 with final numbers**
All documents that cite the old statistics (1,775 significant pairs, 153 Tier 2 events) need updating once the correct methodology is implemented.

### Medium Priority

**4. Phase 2 cleanup (archive old files)**
Per the plan: archive old scripts, old logs, superseded database versions, annotated document versions. Move to `archive/` subdirectory with preserved structure.
- Safe to do now (v3 run is complete)
- Key items: `figure_skating_ijs_v2.sqlite` → `archive/databases/`; old scripts → `archive/scripts/old_versions/` etc.

**5. GitHub repo setup**
Deliverable package: `figure-skating-judge-bias/` repo with `src/`, `docs/`, `data/`, `source_pdfs/` structure. Database via Git LFS (too large for standard Git). Decision pending: public or private?

**6. Update paper and strategy documents with correct pairwise stats**
- `significance_draft_v1.md` / `.docx` — cites 1,774 significant pairs, 46 outcome-determinative events
- `journal_strategy.md` / `.docx`
- `media_strategy.md` / `.docx`
All need updating after corrected pairwise methodology is implemented.

---

## Key Numbers Reference

| Metric | Value | Notes |
|---|---|---|
| Competitions | 17 | Jan 2022 – Feb 2026 |
| Events | 144 | All disciplines, all rounds |
| Entries | 2,706 | Competitor-event pairs |
| Judge scores | 291,604 | 206,682 GOE + 84,922 PCS |
| Pairwise rows | 272,072 | From v4 run |
| Significant p ≤ 0.001 | 2,812 | **Inflated — exchangeability flaw** |
| Significant p ≤ 0.01 | 11,847 | **Inflated — same flaw** |
| LOJO rows | 1,288 | Judge-event LOJO computations |
| Tier 2 events | 56 | Podium changes AND sig001 |
| Podium changes | 462 | Across all events |
| Winner changes | 150 | Gold medal changes |
| OWG 2026 key p-value | ~4.6×10⁻⁵ | Pairs FS J6 (CHIGOGIDZE) |

---

## Key Files Reference

| File | Purpose | Status |
|---|---|---|
| `figure_skating_ijs_v3.sqlite` | Canonical database (v4 pairwise complete) | Active |
| `figure_skating_ijs_seed.sqlite` | Base database (pre-pairwise) | Superseded; keep for now |
| `streamlit_app.py` | Interactive web app | Active |
| `generate_event_report.py` | Excel report generator | Active |
| `calculate_pairwise_statistics_v4.py` | Pairwise B(j) test — current | Active |
| `calculate_lojo_full.py` | LOJO counterfactual | Active; now points to v3 |
| `parse_singles_pairs.py` | PDF parser (Singles/Pairs) | Active |
| `parse_ice_dance.py` | PDF parser (Ice Dance) | Active |
| `db_inserter.py` | Database insertion module | Active |
| `methodology_diagnosis_v1.md/.docx` | Exchangeability problem diagnosis | Created Feb 22 |
| `make_word_docs.py` | Converts .md files to .docx | Updated Feb 22 |
| `OWG2026_RD_Scoring_Model.xlsx` | Generic scoring model workbook | Created Feb 22 |
| `OWG2026_RD_Raw_Scores.xlsx` | Original raw data (read-only) | Unchanged |
| `project_documentation.md/.docx` | Full methodology documentation | Active |
| `Data_Dictionary.md/.docx` | Database field reference | Active |
| `glossary.md/.docx` | OSNR/LOJO/BI(j) definitions | Active |
| `history_log.md` | This document | Created Feb 22 |
| `MEMORY.md` | Claude session memory | Updated Feb 22 |

---

## Decisions Log (Condensed)

| Date | Decision | Rationale |
|---|---|---|
| Feb 22 | Ghost event_id 198 left in place | Zero analytical impact; removal not worth schema surgery |
| Feb 22 | Document exchangeability problem before fixing it | Need to understand the literature fully before choosing between 3 fix options |
| Feb 22 | Use exact ISU SOV factors (not back-calculated averages) | Downloaded ISU Comm 2705 PDF directly; exact factors confirmed; accuracy improved from mean diff 0.121→0.010 |
| Feb 22 | Build OWG2026_RD_Scoring_Model.xlsx from scratch (openpyxl) | Original file untouched; clean build avoids Excel quirks |
| Feb 22 | LOJO DB_PATH updated to v3 | Seed database pre-dates v4 pairwise run; v3 is canonical |
| Feb 22 | Two-document memory pattern adopted | MEMORY.md = lean dashboard read every session; history_log.md = detailed record read on demand |
| Feb 22 | Tier 2 rule: podium_changes > 0 AND sig001 > 0 | Winner-only (gold) criterion replaced; any top-3 change is material |

---

---

### Session continuation: February 22, 2026 (afternoon)

#### 13. ISU SOV PDF Downloaded and Parsed

**What was done:** Downloaded the official ISU Communication No. 2705 (Ice Dance Scale of Values, 2025-26 season) directly from the ISU server as a PDF. Extracted full text using `pdftotext -layout`. The complete GOE table for all ice dance elements is now available locally.

**File saved:** `ISU_Comm2705_SOV_IceDance_2025-26.pdf` (949 KB)

**Key findings from the official table:**
- GOE factors in ice dance are **absolute point values per integer grade**, not percentages of BV
- For paired elements (twizzles, step sequences), the combined factor = Woman's factor + Man's factor
- Twizzles: each partner L1–L4 = 0.40/grade → combined = **0.80**
- Step sequences: each partner L1–L4 = 0.52/grade → combined = **1.04** (not 1.05 as approximated)
- Pattern step: single element, all levels = **1.12**
- Lifts L1–L4: all types = **0.48**
- ChRS1: **asymmetric** — positive GOE factor = 1.50/grade, negative = 0.40/grade
- Truncated twizzle (one partner fails): only the completing partner's factor applies (0.40, not 0.80)

#### 14. Spreadsheet Factors Updated to Exact ISU Values

**File modified:** `OWG2026_RD_Scoring_Model.xlsx`

All 115 Multiplier cells in the Element Scores sheet updated with element-code-specific exact factors:
- Twizzles (full): 0.7652 → **0.80**
- Twizzles (truncated, ranks 22-23): 0.7652 → **0.40**
- Step sequences: 1.0439 → **1.04**
- Pattern step: 1.1189 → **1.12** (unchanged in effect)
- Choreographic: 1.5005 → **1.50** (unchanged in effect)
- Lifts: 0.4799 → **0.48** (unchanged in effect)

**Verification results:**
- Before: mean TES diff vs database = 0.121, max = 1.230 (ranks 22-23 were 1.1+ off)
- After: mean TES diff = **0.010**, max = **0.020**
- 17/23 couples: exact match; 6/23: 0.02 off (ISU internal rounding, irreducible)

#### 15. ISU_Scoring_Methodology.md Created (and .docx)

**File created:** `ISU_Scoring_Methodology.md` / `ISU_Scoring_Methodology.docx`

Comprehensive technical reference covering:
- Full 8-step scoring chain (level call → GOE integers → trimmed mean → factor → element score → TES → PCS → TSS)
- Exact GOE factor tables from ISU Comm 2705, with combined pair-element derivation
- Asymmetric ChRS1 GOE scale explained
- Truncated element rule documented
- Verification table (before/after accuracy)
- PCS factors for all disciplines/segments
- Ice dance vs. singles/pairs differences
- Links to all related documents

**`make_word_docs.py` updated:** `ISU_Scoring_Methodology.md` added to FILES list.

---

*Append new sessions below this line, newest at bottom.*

---

### Session: February 22, 2026 (continued — GOE Factors & Database Completeness)

**Context at session start:**
- `ISU_Scoring_Methodology.md` just completed with exact GOE factors from Comm 2705
- `OWG2026_RD_Scoring_Model.xlsx` verified to 0.010 mean TES difference
- User asked: Do we need historical SOV tables? Did factors change? How do we handle other disciplines? Should we store GOE factors in the database?

---

#### 16. Historical ISU SOV Research — Seasons 2021/22 through 2025/26

**Finding:** GOE factors changed **once**, at the 2021/22 → 2022/23 boundary (Comm 2256 → Comm 2473).
Seasons 2022/23, 2023/24, 2024/25, and 2025/26 use byte-for-byte identical GOE tables.

**Key changes at 2022/23 boundary:**
- Twizzle factor: 0.36/partner → **0.40/partner** per grade (+11%)
- Lift factor: 0.46 → **0.48** per grade (+4%)
- Step sequences restructured: combined single level (0.97/pair) → per-partner levels (**0.52/partner** = 1.04/pair)
- ChRS1 and ChAJ1: did not exist before 2022/23; introduced with asymmetric scale
- PSt: per-partner (0.48+0.48=0.96) → combined single unit (**1.12**)

**Singles & Pairs (all seasons):** GOE = **10% of base_value** per grade — universal rule, unchanged across all 5 seasons. The absolute factor per grade = ROUND(BV × 0.10, 2), and varies by element.

**ISU Communication numbers confirmed:**

| Season | Ice Dance | Singles/Pairs |
|--------|-----------|---------------|
| 2021/22 | Comm 2256 | Comm 2253 |
| 2022/23 | Comm 2473 | Comm 2475 |
| 2023/24 | Comm 2564 | Comm 2475 (no new doc) |
| 2024/25 | Comm 2647 | Comm 2656 |
| 2025/26 | Comm 2705 | Comm 2707 |

---

#### 17. ISU SOV PDFs Downloaded to source_pdfs/isu_sov/

**Folder created:** `source_pdfs/isu_sov/`

**Files downloaded (7 PDFs total):**

| File | Comm | Source |
|------|------|--------|
| `ISU_Comm2253_SOV_SinglesPairs_2019-20.pdf` | 2253 | Wayback Machine (786 KB) |
| `ISU_Comm2473_SOV_IceDance_2022-23.pdf` | 2473 | Wayback Machine (2.3 MB) |
| `ISU_Comm2475_SOV_SinglesPairs_2022-23.pdf` | 2475 | Wayback Machine (1.1 MB) |
| `ISU_Comm2564_SOV_IceDance_2023-24.pdf` | 2564 | ice-dance.com (2.2 MB) |
| `ISU_Comm2647_SOV_IceDance_2024-25.pdf` | 2647 | ISU Azure CDN (1.0 MB) |
| `ISU_Comm2656_SOV_SinglesPairs_2024-25.pdf` | 2656 | Wayback Machine (3.9 MB) |
| `ISU_Comm2707_SOV_SinglesPairs_2025-26.pdf` | 2707 | ISU Azure CDN (871 KB) |

Note: 2025/26 Ice Dance (Comm 2705) was already in root folder from previous session. Later in this session, Comm 2256 (Ice Dance 2021/22) also downloaded — confirmed SqTw old factor = 0.36/partner ✓. Full collection now **8 PDFs**, all seasons covered.

---

#### 18. goe_factors Table Created and goe_factor_inferred Populated

**Script created:** `populate_goe_factors.py`

**Database changes:**
1. New table `goe_factors` created with 17 reference rows mapping (season, discipline, element_pattern) → factor, with source ISU Communication number
2. `elements.goe_factor_inferred` populated for **all 23,043 elements** (0 NULL remaining)

**Factor assignment logic:**
- Ice Dance 2021/22 (Comm 2256): regex-matched against old element code patterns (DiSt1, MiSt2 etc. — single combined level), factors 0.36/partner twizzle, 0.97 step seq, 0.46 lift, 0.48/partner PSt
- Ice Dance 2022/23+ (Comms 2473/2564/2647/2705): modern patterns (DiStW3+DiStM3 etc.), factors 0.40/partner twizzle, 0.52/partner step seq, 0.48 lift, 1.12 PSt, 1.50 ChRS1, 0.83 other Ch elements
- Singles/Pairs (all seasons): factor = ROUND(base_value × 0.10, 2) — the 10% rule

**Spot-check verified:** OWG 2026 RD Rank 1 (Fournier Beaudry/Cizeron):
- SqTwW4+SqTwM4: stored=0.80, implied=0.80 ✓
- MiStW3+MiStM3: stored=1.04, implied=1.0448 ✓ (small ISU rounding)
- PSt4: stored=1.12, implied=1.1174 ✓
- ChRS1: stored=1.50, implied=1.5003 ✓
- RoLi4: stored=0.48, implied=0.4797 ✓

---

#### 19. Completeness Audit — Can We Reconstruct Official ISU Results?

**TES reconstruction:** PERFECT. All 2,706 entries: `SUM(base_value + panel_goe_points)` matches stored TES to within 0.01 for 100% of entries.

**PCS reconstruction (ice dance):** CORRECT. `panel_component_avg` stores correct trimmed mean; `pcs_judge_scores` stores correct 9 individual judge marks. Verified against OWG 2026 data.

**PCS reconstruction (singles/pairs):** KNOWN ISSUE. `panel_component_avg` in `pcs_components` stores an incorrect value (appears to be judge index, not score) for singles and pairs. **However:** (a) the total PCS is correctly stored in `entries.pcs`; (b) the 9 individual judge marks are correctly stored in `pcs_judge_scores`; (c) the 26% of PCS judge marks stored as 0.0 represent non-participating/absent judges. The raw marks ARE available to compute correct trimmed means.

**TSS reconstruction:** `entries.tss = entries.tes + entries.pcs + entries.deductions` — all stored directly and correctly for all 2,706 entries.

**What IS fully in the database:**
- ✅ All element base values (from ISU PDFs)
- ✅ All 9 judge GOE integers per element (core of BI(j) analysis)
- ✅ Panel GOE points (trimmed mean × factor) — official values
- ✅ TES (sum of element scores)
- ✅ PCS judge marks (9 per component) for all disciplines
- ✅ PCS totals (entries.pcs) — official values
- ✅ TSS — official values
- ✅ Deductions
- ✅ GOE factors (new: goe_factor_inferred) — official values from ISU SOV PDFs
- ✅ ISU SOV source PDFs (7 PDFs, covering all seasons and disciplines)

**What is NOT in the database / known gaps:**
- ⚠️ `panel_component_avg` for singles/pairs is incorrect (but raw marks + totals are both correct)
- ⚠️ `elements.panel_element_score` is NULL for all rows (can be computed as BV + panel_goe_points)
- ⚠️ No PCS factor stored per entry/event explicitly (ice dance factor = 1.33 always; singles SP 0.8 or 1.6 varies by era)
- ⚠️ No level-of-difficulty (GOE qualitative criterion) data stored (not relevant to quantitative audit)
- ⚠️ Historical SOV PDFs for 2021/22 ice dance (Comm 2256) not yet downloaded

---

#### Key Decisions

- **Use `goe_factor_inferred` column name** for now; rename to `goe_factor_official` after confirming all values correct
- **Singles/pairs PCS reconstruction:** Use `entries.pcs` (correct) for all analysis; `panel_component_avg` should be fixed in a future parsing patch but is not blocking any current analysis
- **Source PDFs:** All ISU SOV documents stored in `source_pdfs/isu_sov/`; Wayback Machine used for documents no longer on live ISU server (acceptable — these are official ISU publications)

---

### Session continuation: February 22, 2026 (continued — PCS Bug Fix)

#### 20. Singles/Pairs PCS Bug: Root Cause Identified and Fixed

**What was done:** Investigated, planned, and fully repaired the `panel_component_avg` corruption noted in Session 19.

**Root cause:** `_split_pcs_tokens()` in `parse_singles_pairs.py` contained a "run-together float" regex (`r'(\d+\.\d+)(?=\d)'`) that was designed to split ISU ice dance PDFs like `10.009.50`, but ISU singles/pairs PDFs never have run-together floats. The regex fired incorrectly on every normal two-decimal float, splitting `"1.33"` into `["1.3", "3"]`, `"9.00"` into `["9.0", "0"]`, etc.

**Verified by simulation:** Input `"Composition  1.33  9.00  8.50  8.25  7.75  8.75  8.25  8.25  8.50  8.50  8.43"`:
- Buggy output: `['Composition', '1.3', '3', '9.0', '0', '8.5', '0', ...]` — factor=1.3, judge marks all wrong
- Fixed output: `['Composition', '1.33', '9.00', '8.50', ...]` — factor=1.33, all marks correct

**Scope of corruption:**
- `pcs_components.factor`: truncated (1.3 instead of 1.33; 2.6 instead of 2.67; etc.)
- `pcs_components.panel_component_avg`: wrong (small integers like 1.0, 2.0, 4.0)
- `pcs_judge_scores.judge_mark`: included 0.0 and spurious low values
- **Unaffected:** `entries.pcs`, `entries.tes`, `entries.tss` (all correct — from summary row); ice dance; team events

---

#### 21. Parser Fix Applied

**File modified:** `parse_singles_pairs.py`

**Change:** Removed `_RUNON_FLOAT = re.compile(r'(\d+\.\d+)(?=\d)')` class variable (line 553) and replaced the `_split_pcs_tokens()` method body with `return line.split()`.

**Comment added** explaining why the regex was removed — for future developers.

---

#### 22. OWG 2026 Women's PDFs Downloaded

During repair, it was discovered that the OWG 2026 Women's Single Skating PDFs were missing from the `figure_skating_seed_bundle/isu_pdfs/milano2026/` folder (the Women's events had been ingested earlier from a temporary download). The PDFs were retrieved from the ISU results server:

- URL pattern: `https://results.isu.org/results/season2526/owg2026/FSKWSINGLES-----------QUAL000100--_JudgesDetailsperSkater.pdf`
- Saved as `SEG003_JudgesDetails.pdf` (Women SP, 395 KB)
- Saved as `SEG004_JudgesDetails.pdf` (Women FS, 417 KB)

Also updated `parse_singles_pairs.py` `COMPETITIONS['milano2026']['segs']` to include segs 3 and 4 (Women SP and FS).

---

#### 23. Database Repaired: repair_singles_pcs.py

**Script created:** `repair_singles_pcs.py`

**What it does:**
1. Imports the fixed `SinglesPairsParser` from `parse_singles_pairs.py`
2. Iterates all competitions/segments in `COMPETITIONS` dict
3. For each PDF, re-parses with the fixed parser and matches skaters to DB entries by name
4. Issues targeted `UPDATE pcs_components SET factor=?, panel_component_avg=?` and `DELETE + INSERT` for `pcs_judge_scores`
5. Commits after each skater to prevent partial rollbacks
6. Supports `--dry-run` and `--comp KEY` flags

**Execution notes:**
- First run caused SQLite index corruption (`sqlite_autoindex_pcs_judge_scores_1`) due to a mid-run UNIQUE constraint error. Recovered using `sqlite3 figure_skating_ijs_seed.sqlite ".recover"` which produced a clean database with the original pre-repair state.
- Second run (with per-skater commits) completed successfully.
- Also required a manual SQL fix for one edge case: Jason BROWN (WC2023 Men FS) — his Presentation component line was missed by the parser due to a PDF layout quirk; values read directly from the PDF text and inserted via Python.

**Final repair stats:** 100 events processed, 1,962 entries updated, 6,907 components repaired, 0 errors.

---

#### 24. Repair Verified

All verification queries pass:

| Check | Result |
|-------|--------|
| Distinct factor values (singles/pairs) | Only correct values: 0.8, 1.0, 1.33, 1.6, 1.67, 2.0, 2.67, 3.33 |
| Zero judge marks in `pcs_judge_scores` (singles/pairs) | **0** |
| Database integrity check | **ok** |
| Malinin WC2025 SP: stored avg ≈ computed trimmed mean | ✓ (diff < 0.005) |
| Alysa LIU WC2025 Women SP: Composition 8.43, Presentation 8.68, Skating Skills 8.29 | ✓ exact |
| 2,015 entries: `SUM(panel_component_avg × factor)` ≈ `entries.pcs` within 0.03 | **0 mismatches** |

---

#### Key Decisions

- **Repair from source PDFs** (not from re-running the full parser) — targeted update to only the 3 corrupted columns, preserving all other data
- **Per-skater commits** — prevents partial-event rollbacks if any single entry fails
- **Jason BROWN Presentation at WC2023** — manually patched from PDF text; PDF layout breaks parser on that page. Values verified against `entries.pcs` (95.84 = (9.50+9.82+9.46) × 3.33 ✓)
- **OWG 2026 Women's PDFs** — kept in `milano2026/` as `SEG003_JudgesDetails.pdf` and `SEG004_JudgesDetails.pdf` for future re-use

---

## Session 25 — 2026-02-22: Database Completeness & Source Provenance

**Goal:** Ensure the database contains everything needed to reconstruct official ISU results,
and that all data traces back to official ISU source PDFs.

**Three gaps identified and fixed:**

### 1. Ice Dance Deduction Sign Bug (56 entries)

`parse_ice_dance.py` line 591 used `abs()` on the deduction value read from the PDF,
converting negative deductions (e.g. -1.00) to positive (1.0). The `entries.tss` values
were correct (TSS was computed externally), but `entries.deductions` had the wrong sign.

**Fix:** 
- `fix_ice_dance_deductions.py` — targeted UPDATE on both seed and v3 databases
- `parse_ice_dance.py` line 591: changed `abs(float(m.group(8)))` → `float(m.group(8))`
- All 56 entries verified: `tes + pcs + deductions ≈ tss` within 0.02 for every row

**Scope:** 56 Ice Dance entries across 16 competitions, 2021/22 through 2025/26.

### 2. `element_info` Column Added to `elements` Table

The `x` second-half bonus was baked into `base_value` (math correct) but not stored
explicitly. The ISU PDF prints a separate info field per element (e.g. `x`, `< !`, `<<`).

**Fix:**
- `ALTER TABLE elements ADD COLUMN element_info TEXT` on both databases
- `parse_singles_pairs.py`: modified INSERT to write `element_info`; also fixed `x_bonus`
  token to be prepended to `info_str` (it was captured in `x_bonus` flag but not `info_tokens`)
- `backfill_element_info.py` — re-parsed all 19 competition PDFs, updated 23,043 elements
- Spot check: Malinin WC2025 SP element 4 (`4Lz+3T`): `element_info='x'`, `base_value=17.27` ✓
- 4,250 non-null element_info rows in seed DB (4,194 in v3 DB)

**Parser bug fixed:** `info_tokens` was finalized before `x_bonus` was set (second branch at
line 455 captures `x` after base_value but doesn't append to `info_tokens`). Added
`if x_bonus: info_tokens = ['x'] + info_tokens` before `info_str` join.

**Backfill bug fixed:** Initial backfill used `(competition_id, team_name)` to find
`entry_id`, returning multiple rows when a skater appears in both SP and FS. Fixed to
use `(event_id, team_name)` by resolving event_id from segment number via `SEG_TO_DISCIPLINE`.

### 3. Sources Table and Event URLs Backfilled

Only OWG 2026 had source rows in the `sources` table. All other competitions' PDFs were
on disk with no provenance.

**Fix:** `backfill_sources.py` — for each competition in COMPETITIONS dict:
- Computes sha256 and file size for each PDF and panel HTML on disk
- Constructs ISU URL from `results_root_url + filename`
- Inserts into `sources` and updates `events.judges_details_pdf_url`
- 128 PDF sources + 64 panel HTML sources added across 16 competitions
- OWG2026 Women SP/FS and Pairs FS (events 326-328) handled separately (non-standard ISU filenames)

**Final state:**
- 239 total rows in `sources`
- 152 distinct events with `judges_details_pdf` source record
- 0 events with NULL `judges_details_pdf_url`

**Warnings (expected):** `ec2020` and `fc2020` appear in COMPETITIONS dict but have no
DB entries (empty PDF folders, never ingested).

**Files created:** `fix_ice_dance_deductions.py`, `backfill_element_info.py`, `backfill_sources.py`

**Files modified:** `parse_singles_pairs.py` (element_info in INSERT, x_bonus in info_str),
`parse_ice_dance.py` (deductions sign fix)

---

## Session 29 — 2026-02-23/24: ISU-Impact Pipeline (isuimpact_quantile_v1)

**Goal:** Implement the new ISU-impact style-adjusted quantile permutation bias test for OWG 2026 Ice Dance Free Dance and store results in the database.

### Why a New Method
The B(j) pairwise test (v4) has an exchangeability violation: judges scoring the same skaters are correlated, making the null distribution too narrow and generating ~560× too many significant findings. The ISU-impact method avoids this by measuring each judge's effect through the ISU's own trimmed-mean formula, and using a career-wide quantile permutation null that preserves each judge's personal scoring style.

### New Schema
Two new tables in `figure_skating_ijs_seed.sqlite`:
- `pairwise_impact_results` — 9 × C(N,2) rows per event; stores BiasPoints, Vote, p_value, q_value_bh
- `judge_team_impacts` — 9 × N rows per event; stores each judge's ISU-score impact per competitor

### Script: `calculate_isuimpact_v1.py`
- Flags: `--event-id`, `--dry-run`, `--permutations` (default 10000), `--seed` (default 20260223), `--workers`, `--cdf-scope {global,event}`
- CDF scope = GLOBAL (career-wide): each judge's samples pooled across all events in DB
- Permutation step is row-wise: within each GOE/PCS row, percentile labels are shuffled across judges, preserving each judge's mark distribution
- BH-FDR applied across all 9 × C(N,2) tests simultaneously within event
- Method version stored as `isuimpact_quantile_v1`

### OWG 2026 FD Results (event_id=2, verified from DB)
| Metric | Value |
|--------|-------|
| FRA TSS | 135.64 |
| USA TSS | 134.67 |
| Margin | 0.97 pts |
| J1 BiasPoints(FRA,USA) | +1.19 pts |
| J1 p-value | 0.0006 |
| J1 BH q-value | 0.0446 |
| **Outcome-determinative?** | **YES — 1.19 > 0.97** |
| Significant judges | J1 (3 pairs), J4 (6), J5 (2), J6 (6), J8 (6) |

### Files Created/Modified
- `isuimpact_schema.sql` — CREATE TABLE for new tables (idempotent)
- `calculate_isuimpact_v1.py` — full pipeline
- `figure_skating_ijs_seed.sqlite` — 271,728 + 24,174 new rows inserted
- `Paired Comparison Framework/owg2026_ice_dance_FD_pairwise_bias_styleAdjQuantile_perm10000.xlsx` — Chat's analysis output (source for workbook builder)

### State at Session End
- `figure_skating_ijs_seed.sqlite`: pairwise_impact_results and judge_team_impacts fully populated for all 142 events
- OWG 2026 FD results verified against Chat's independent spreadsheet (values match)
- Open question: global vs. event-scope CDF (currently global; J5 and J7 appear in only 1 event so global ≡ event-scope for them)

---

## Session 31 — 2026-02-24: Data Pipeline Fix, Peer Review, Press Kit Submission

**Goal:** Resolve data discrepancy between database and Chat analysis file, apply peer review corrections, submit press kit to five outlets.

### Root Cause: GOE Factor Discrepancy (1.14 → 1.19)
- **Problem**: Chat analysis file used `goe_factor_inferred` (0.60) for combined elements (SyTw, OFT, DiSt). The ISU-impact pipeline uses effective factor (`panel_goe_points / trimmed_mean` ≈ 0.73).
- **Effect**: BiasPoints shifted from 1.14 to 1.19; p from 0.0007 to 0.0003; q from 0.027 to 0.034
- **Resolution**: Database is canonical. Chat analysis file RETIRED. All outputs now sourced from database.

### 10k Permutation Rerun
- Event 2 re-run: `calculate_isuimpact_v1.py --event-id 2 --permutations 10000 --seed 20260223`
- Canonical results: J1 FRA-USA BiasPoints=+1.19, p=0.0003, q=0.034
- 5 of 9 judges significant (not "all nine" as in old Chat file): J1(2), J4(6), J5(2), J6(6), J8(5) = 21 total
- Full 144-event rerun at 10k launched in background (estimated 3–5 hours)

### Peer Review (Chat) — Two Rounds
**Round 1 corrections:**
- Rewired `build_bias_workbook_from_db()` to read all bias tabs from database, not Chat file
- Updated all press materials: op-ed, cover emails, FAQ, workbook (1.14→1.19, p/q values, "5 of 9")
- Fixed op-ed CDF scope: "at the competition" → "in the database" (method uses global/career-wide CDFs)
- Fixed op-ed two-part test wording to describe both halves (impact vs panel + significance vs own history)

**Round 2 corrections (Chat's second review):**
1. FAQ exceedances off-by-one: "3 of 10,000" → "2 of 10,000 permutations exceeded, giving p=(1+2)/10,001≈0.0003"
2. FAQ BH-FDR overclaim: removed "3.4% chance this specific finding is a false positive" and "bet 19-to-1"; replaced with proper FDR language about expected proportion of false discoveries
3. Workbook ISU GOE tab: renamed "Multiplier" → "GOE Factor*"; added footnote explaining combined-element effective factor; added worked example on Method tab (SyTwW4+SyTwM3, factor 0.7258 vs stored 0.60)

### Press Kit Submitted
- NYT: Airtable form (opinion@nytimes.com bounced; exclusive through Feb 28)
- Guardian: opinion@theguardian.com
- The Athletic: Zack Pierce (zpierce@theathletic.com)
- Sportico: Lev Akabas
- Nate Silver: Silver Bulletin

### Files Modified
- `build_complete_event_workbook.py` — database-sourced bias tabs, GOE Factor* rename + footnote, worked example on Method tab
- `create_faq_document.py` — exceedances fix, BH-FDR language fix
- `oped_draft.md` — CDF scope fix, two-part test wording
- `cover_emails_2026-02-24.md` — NYT email CDF scope fix ("at the competition" → "in the database")
- `calculate_isuimpact_v1.py` — docstring validation target updated (1.144 → 1.19)

### Cleanup
- Deleted two superseded backups: `bak_isuimpact`, `bak_before_10k_rerun` (~193 MB freed)
- Retained `bak_before_full_10k` pending full rerun completion

### State at Session End
- All press materials internally consistent: 1.19 / 0.0003 / 0.034 / 5-of-9 / 21 pairs
- Full 10k rerun in progress (~144 events)
- Press kit submitted to 5 outlets
- Pending: verify full rerun, delete final backup, upload updated files to Google Drive

---

## Session 32 — 2026-02-24: Post-10k Checklist (Steps 2–4) + Documentation Update

**Goal:** Complete the post-10k cleanup and generalize the workbook builder to produce analysis workbooks for all 142 events.

### Step 2 — Cleanup
- WAL checkpoint: `PRAGMA wal_checkpoint(TRUNCATE)` returned `0|0|0` (clean)
- Deleted backup: `archive/databases/figure_skating_ijs_v4.sqlite.bak_before_full_10k`
- Fixed `post_10k_checklist.md` heading: "All 144 Event Workbooks" → "All 142 Event Workbooks"

### Step 3 — Generalize `build_complete_event_workbook.py`

Full rewrite from 1,457 hardcoded lines to a dynamic, argparse-driven script (~1,714 lines):

**New CLI:**
```
python3 build_complete_event_workbook.py                     # event_id=2 (OWG FD)
python3 build_complete_event_workbook.py --event-id 22       # single event
python3 build_complete_event_workbook.py --all-events --dry-run
python3 build_complete_event_workbook.py --all-events
```

**Key architectural changes:**
- `get_event_paths(conn, event_id)` — derives ISU xlsx from `sources` table; pattern: `{comp_dir}_{pdf_stem}.xlsx`
- `get_event_info(conn, event_id)` — dynamic metadata: comp name, discipline, segment, n_entries, n_pairs, is_ice_dance, is_owg2026
- `get_dynamic_key_findings(conn, event_id, event_info)` — queries DB for OD gold vs silver finding; returns `None` if no OD result
- `build_dynamic_event_facts()`, `build_dynamic_bias_tab_meta()` — replace hardcoded globals
- `OWG2026_JUDGE_NAMES` — constant dict (renamed from `JUDGE_MAP`); used only for OWG 2026 events
- GOE Factor* rename and footnote: conditional on `is_ice_dance`
- SyTw worked example on Method tab: conditional on `is_ice_dance`
- `build_event(event_id, dry_run=False)` — single-event build; warns+skips on missing ISU xlsx

### Step 4 — Regenerate All 142 Event Workbooks

```
python3 build_complete_event_workbook.py --all-events --dry-run   # 142/142 found, 0 missing
python3 build_complete_event_workbook.py --all-events             # 142/142 built, 0 errors
```

Deleted superseded `excel_output/owg2026_FSKXICEDANCE_FD_complete.xlsx` (old hardcoded filename).

### Documentation Update
Updated stale numbers across faq_v1, media_strategy, ip_protection to ISU-impact (replacing B(j)/OSNR):
- Events analyzed: 144 → 142
- Pairwise tests: 264,854 → 271,728
- Significant pairs: "1,774 at p≤0.001" → "9,463 at BH q≤0.05"
- Outcome-determinative events: 46 → 7
- Added ISU-impact methodology note to ip_protection.md

### State at Session End
- All 142 analyzed events have complete 12-tab workbooks in `excel_output/`
- OWG FD J1 BiasPoints=1.19 verified unchanged after rerun
- All project documentation current
- Pending: re-upload press kit to Google Drive

---

## Session 30 — 2026-02-24: Excel Workbook Builder + FAQ Document

**Goal:** Build a journalist-ready 12-tab Excel workbook merging ISU official data with the new ISU-impact pairwise results, plus a FAQ Word document.

### Key Decisions
- **12-tab structure**: Overview, Key Findings, ISU–Summary, ISU–Elements(GOE), ISU–PCS, ISU–Legend, Bias–Judge Summary, Bias–Impact by Team, Bias–Top 25 Pairs, Bias–All Pairs, Bias–Method, Glossary
- **Key Findings tab** (tab 2): outcome-determinative finding hardcoded from verified DB values; journalist-readable format with red tab
- **Glossary** (last tab): plain-English definitions of all statistical terms
- **Two-part test**: a finding is outcome-determinative only if (1) q ≤ 0.05 AND (2) |BiasPoints| > winning margin. Only J1/FRA-USA satisfies both.
- **Career-wide CDF**: each judge's scoring style calibrated against their entire career in the DB (142 events, 2022–2026); only deviations from personal pattern are flagged
- Formula rewriting: cross-sheet refs like `='Element Scores'!S13` → `='ISU – Elements (GOE)'!S13`
- ISU file loaded twice: once with formulas (for Summary cross-sheet refs) and once `data_only=True` (for color coding — formula strings block `isinstance(float)` check)

### Script: `build_complete_event_workbook.py`
Key constants/data structures:
- `KEY_FINDINGS_DATA`: hardcoded from DB — FRA TSS=135.64, USA TSS=134.67, margin=0.97, J1 bias=+1.19, p=0.0006, q=0.0446
- `BIAS_TAB_META`: per-tab title, description, column widths, center_cols, hdr_row_height, desc_font_size, numeric_cols
- `JUDGE_MAP`: J1–J9 → "Jn – Full Name" for OWG 2026 FD panel
- `TAB_CONFIG`: maps source file key + sheet name → destination tab name
- Functions: `copy_sheet_with_bias_header()`, `apply_high_low_colors(ws, ..., data_ws=None)`, `build_key_findings_sheet()`, `build_glossary_sheet()`, `build_overview_sheet()`, `lock_sheet()`

### Script: `create_faq_document.py`
- 8 categories, 41 Q&A pairs
- Audience: journalists and researchers
- Expanded BH-FDR explanation (1,710 tests × 85 false-alarm framing; 19-to-1 closing line)
- Career-wide CDF Q&A added to Statistical Methods section

### Formatting Passes Applied (3 rounds)
| Change | Value |
|--------|-------|
| Overview col A tab numbers | Centered |
| Key Findings France row height | 48 |
| ISU Summary A1 | wrap_text=True, height=40 |
| ISU Elements/PCS color coding | Fixed via data_only load |
| Bias tab row 4 header height | 22/30/36 per tab |
| Top 25 Pairs cols H–L | Centered; col I width 20→15 |
| All Pairs cols B,E,G–K | Centered; col H width 20→14 |
| All 12 sheets | Locked (no password) |
| Key Findings: Two-part test | Added as methodology row |

### Output Files
- `excel_output/owg2026_FSKXICEDANCE_FD_complete.xlsx` — 198 KB, 12 tabs
- `OWG2026_IceDance_FD_FAQ.docx` — 43 KB, 41 Q&As

### State at Session End
- Both files build cleanly from `python3 build_complete_event_workbook.py` and `python3 create_faq_document.py`
- All sheets locked (no password)
- Phase 2 pending: generalize workbook builder to accept `--event-id` and query DB dynamically

### Decisions Made
- **Cell protection**: no-password lock on all sheets; user unlocks via Review → Unprotect Sheet
- **ISU Summary row 1**: wrap_text=True preferred over font-shrink (preserves readability) or column-widening (preserves layout)
- **Tab confusion (items 10/11)**: "Bias Impact by Team" has only 5 cols (A–E); "BiasPoints_AminusB" is col I in Top 25 Pairs — fixes applied there
- **data_only load**: root cause of silent color-coding failure; documented in debugging.md Incident 5

---
