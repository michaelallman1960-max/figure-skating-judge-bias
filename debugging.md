# Debugging & Lessons Learned
## Figure Skating Judging Bias Project

*Last updated: February 24, 2026 (Session 30)*

---

## Incident 1: v3 Pairwise Run — Combinatorial Explosion (Feb 21, 2026)

### What Happened
The v3 pairwise script (`calculate_pairwise_statistics_v3.py`) was launched to compute exact permutation p-values across all 144 events. After 10+ hours it had completed only 19 of 144 events (~13%) and was estimated to take 75 more hours to finish. It was killed.

### Root Cause
The `exact_permutation_test()` function enumerated all C(2k, k) combinations in a **pure Python loop**. For small events (k=8–9 elements, short programs), this is fast: C(18,9) = 48,620 iterations — trivial. For large events (k=12 elements, free skates and free dances with many skaters), it explodes: C(24,12) = 2,704,156 iterations **per judge-pair comparison**, multiplied by hundreds of pairs per event. A single large event could require hundreds of millions of Python loop iterations.

The first several events were small team-event segments and short programs, so they completed in seconds. This created false confidence. The catastrophic slowdown hit only when the script reached the large free dance and free skate finals.

### Key Numbers
| Event type | Skaters | Pairs | k | C(2k,k) | Approx ops |
|---|---|---|---|---|---|
| SP, 6 skaters | 15 | 105 | 8 | 12,870 | 1.4M |
| FS, 40 skaters | 780 | 780 | 9 | 48,620 | 38M |
| FD, 24 couples | 276 | 276 | 12 | 2,704,156 | **747M** |

### Lesson Learned
**Always time-test on the largest event before starting a full run.** A 2-minute test on the largest event (World Championships Free Dance, 24+ couples) would have revealed the problem immediately. Instead, the early fast events created false confidence.

**Checklist before any long computation run:**
1. Identify the largest event in the dataset (most skaters × most elements)
2. Run a single-event timing test on that event
3. Extrapolate to full dataset runtime
4. Only then launch the full run

### Fix Applied: v4 Script
`calculate_pairwise_statistics_v4.py` implements three fixes:

**Fix 1 — NumPy vectorization (biggest win, 10–50x):**
Replace the Python loop with a single NumPy matrix operation:
```python
idx_array  = np.array(list(combinations(range(n), ka)), dtype=np.intp)
a_sums     = pool[idx_array].sum(axis=1)   # all C(n,ka) sums at once in C
sim_bi_all = 2.0 * a_sums - total_sum
extreme    = int(np.sum(sim_bi_all >= observed_bi))  # vectorized comparison
```
The combination enumeration still happens, but all arithmetic runs in compiled C via NumPy rather than interpreted Python. Speedup: 10–50x.

**Fix 2 — Monte Carlo fallback for large k (eliminates worst-case events):**
For k > 11 (C(22,11) = 705,432 — the exact threshold where vectorized enumeration is fast enough), switch to 500,000 stratified random samples with fixed seed=42:
```python
shuffled    = np.argsort(rng.random((MC_SAMPLES, n)), axis=1)
subset_sums = pool[shuffled[:, :ka]].sum(axis=1)
```
Reproducible, accurate to p ≈ 10⁻⁵, labeled `test_type='one-sided-mc500k'` in DB.

**Fix 3 — Batch inserts (executemany):**
Collect all stats for an event in memory, write once with `executemany()` instead of one `INSERT` per pair. Reduces DB round-trips by ~100x per event.

**Fix 4 — Parallel execution:**
8 worker processes via `ProcessPoolExecutor` with `fork` context. Events are fully independent; each worker opens its own DB connection.

### Bug Encountered During v4 Development
Initial v4 had an `IndexError` on large events: `index 13 is out of bounds for axis 0 with size 13`.

**Cause:** The original v3 code assumed `len(deviations_a) == len(deviations_b)` (set `k = len(deviations_a)` and generated combinations from `range(2*k)`). When skaters have different numbers of scored elements (which occurs in some events), `pool` has `ka + kb` elements but `range(2*ka)` could exceed pool bounds.

**Fix:** Track `ka` and `kb` separately; generate combinations from `range(ka + kb)` with subset size `ka`. The fix is a one-line change:
```python
# WRONG (v3 assumption):
k = len(deviations_a)
combinations(range(2*k), k)          # breaks if len(b) != len(a)

# CORRECT (v4):
ka, kb = len(deviations_a), len(deviations_b)
combinations(range(ka + kb), ka)     # always correct
```

### v4 Validation Results
| Test | Event | Skaters | Time | Notes |
|---|---|---|---|---|
| Small event | GP Final 2025 SP (id=70) | 6 | 0.11s | ✅ |
| Large event | WC2024 Men SP (id=22) | 40 | 4.6s | ✅ (was ~30min in v3) |
| Spot-check | OWG 2026 Ice Dance FD (id=2) | 24 | 23.8s | ✅ p=2.17×10⁻⁵ confirmed |

### Parallelism Note
`ProcessPoolExecutor` with `fork` context on macOS does work and spawns 8 workers. However, output is only written to the log file when futures complete — the log appears empty during execution. Use the database row count as the true progress indicator:
```sql
SELECT COUNT(DISTINCT event_id) as events_done, COUNT(*) as total_rows
FROM pairwise_judge_statistics;
```

---

## Standing Rules for Future Computation Runs

1. **Time-test on the largest event first.** Always. No exceptions.
2. **Check DB row count for parallel runs** — the log may not flush until workers complete.
3. **Clear partial data before rerunning** — use `DELETE FROM pairwise_judge_statistics` to ensure a clean slate. The resume logic (skipping already-done events) is a safety net, not a substitute.
4. **Never kill a run and rerun on the same DB without clearing** — partial event data can cause inconsistent counts.
5. **After any full rerun, re-run `calculate_lojo_full.py`** — LOJO results depend on pairwise significance flags; they must be recomputed after any change to pairwise statistics.
6. **Spot-check the OWG 2026 Ice Dance FD finding after every rerun** — this is the anchor result. Expected: p ≈ 2–5×10⁻⁵ for the most extreme judge-pair, outcome-determinative under LOJO.

---

---

## Incident 2: Singles/Pairs PCS Data Corrupted by Parser Regex (Feb 22, 2026)

### What Happened
All `pcs_components.factor`, `pcs_components.panel_component_avg`, and `pcs_judge_scores.judge_mark` values for singles and pairs were wrong. The factors were truncated (1.3 instead of 1.33; 2.6 instead of 2.67; etc.) and the panel averages were small integers (1.0, 2.0, 4.0 instead of 8–10). Found during the completeness audit: `SUM(panel_component_avg × factor)` produced totals of 10–20 instead of matching `entries.pcs` (~30–100).

**Not affected:** `entries.pcs`, `entries.tes`, `entries.tss` (correct — read from summary row independently). Ice dance (separate parser). Team events.

### Root Cause
`_split_pcs_tokens()` in `parse_singles_pairs.py` contained:
```python
_RUNON_FLOAT = re.compile(r'(\d+\.\d+)(?=\d)')

def _split_pcs_tokens(self, line: str) -> List[str]:
    fixed = self._RUNON_FLOAT.sub(r'\1 ', line)
    return fixed.split()
```
The regex was intended to split ice dance run-together floats like `10.009.50`. But ISU singles/pairs PDFs always have spaces between values. The regex fired on every normal two-decimal float: `"1.33"` → `["1.3", "3"]`, `"9.00"` → `["9.0", "0"]`. This shifted all subsequent token positions, misidentifying the factor and all judge marks.

**The deceptive part:** `entries.pcs` came out correct because the parser reads it from a separate summary row (`71.37  90.03`) that doesn't go through `_split_pcs_tokens()`. So no top-level number was wrong — only the per-component detail.

### Fix
`parse_singles_pairs.py`, `_split_pcs_tokens()`: removed the regex, replaced with `return line.split()`. ISU singles/pairs PDFs are always space-separated. Comment explains why.

### Repair Procedure
1. `cp figure_skating_ijs_seed.sqlite figure_skating_ijs_seed.sqlite.bak` — backup first
2. Run `repair_singles_pcs.py` (created for this fix) — re-parses all PDFs with fixed parser, issues targeted UPDATE + DELETE/INSERT
3. Verify: `PRAGMA integrity_check;` → `ok`
4. Verify: 0 zero marks, 0 mismatches on `SUM(panel_avg × factor)` vs `entries.pcs`

### SQLite Corruption Encountered During Repair
The first repair attempt had a bug (UNIQUE constraint on re-insert without DELETE). This caused:
- Some `pcs_judge_scores` rows to be written before the exception
- The implicit transaction to roll back, but leaving the B-tree index out of sync with table data
- `PRAGMA integrity_check` reported: `non-unique entry in index sqlite_autoindex_pcs_judge_scores_1`
- `"database disk image is malformed"` error on subsequent run

**Recovery:**
```bash
sqlite3 figure_skating_ijs_seed.sqlite ".recover" | sqlite3 figure_skating_ijs_seed_recovered.sqlite
sqlite3 figure_skating_ijs_seed_recovered.sqlite "PRAGMA integrity_check;"  # → ok
# Verify row counts match expected, then swap files
```
`.recover` reconstructs a clean DB from raw page data, discarding corrupted indexes.

### Edge Case: Jason BROWN WC2023 Men FS Presentation
The parser extracted only 2 of 3 PCS components for this entry — Presentation's line immediately follows Composition in the PDF with insufficient whitespace separation. The repair script logged a warning and skipped it, leaving the corrupted row in place. Fix applied manually:
1. `pdftotext -raw SEG002_JudgesDetails.pdf -` to extract raw text
2. Located Presentation line: `avg=9.82, marks={J1:10.00, J2:9.50, J3:9.75, J4:9.50, J5:10.00, J6:10.00, J7:9.50, J8:10.00, J9:10.00}`
3. Cross-checked: `(9.50 + 9.82 + 9.46) × 3.33 = 95.84` ✓ matches `entries.pcs`
4. Inserted directly via Python/sqlite3

### Key Lessons
1. **Always verify that stored data reconstructs official results** after any new ingest. The check `SUM(panel_component_avg * factor) ≈ entries.pcs` is cheap and catches silent corruption.
2. **Assumptions don't transfer between parsers.** `parse_ice_dance.py` and `parse_singles_pairs.py` are separate. A feature correct for one may be wrong for the other (ice dance has run-together floats; singles/pairs does not).
3. **Python sqlite3 does not auto-commit DML.** Always commit explicitly at the smallest safe granularity (per-skater, not per-event). Repair scripts must be idempotent: unconditional DELETE before INSERT.
4. **OWG 2026 PDFs use non-standard filenames** (`FSKWSINGLES-----------QUAL000100--_JudgesDetailsperSkater.pdf`, not `SEG003_JudgesDetails.pdf`). Find actual filenames from the competition index HTML at `results.isu.org/results/season2526/owg2026/`.
5. **After any repair run, check for `⚠️` warnings** — they indicate entries that were silently skipped and need manual follow-up.

---

---

## Incident 3: PCS Panel Avg Precision — Reference Model Mismatch (Feb 22, 2026, Session 26)

### What Happened
When rewriting `generate_official_scoring_xlsx.py` to match `OWG2026_RD_Scoring_Model.xlsx`, the reference model's PCS Panel Avg formula was `=ROUND(O/7,4)` — 4 decimal places. The script was updated to use 4dp. After regenerating all 144 files, verification went from 7 mismatches to **454 mismatches** (83.2% pass rate).

### Root Cause
The reference model uses 4dp as a display convention — it's a blank template never actually calculated by the ISU. The ISU's actual scoring system computes `panel_avg` at **2 decimal places**. The stored `entries.pcs` values in the database match the 2dp computation path, not 4dp.

Confirmed by exhaustive check across all 2,706 entries:
- 2dp: 0 entries with >0.02 mismatch (85 at exactly ±0.02 — banker's rounding boundary)
- 4dp: 177 entries with >0.02 mismatch, 1,457 at the boundary

### Fix
Reverted Panel Avg formula to `=ROUND(O/(COUNT(F:N)-2),2)` with `number_format='0.00'`.

### Lesson
**Don't trust a blank reference model's formula precision.** The reference model `OWG2026_RD_Scoring_Model.xlsx` was never computed by the ISU — it's a template with example formulas. When the reference contradicts the official stored results, the stored results win. Always verify formula output against `entries.pcs` (or `entries.tes`) before shipping.

---

---

## Incident 4: `element_judge_deviations.peer_median` — Wrong Median Formula (Feb 22, 2026, Session 27)

### What Happened
While applying the Residual Deviation test to OWG 2026 Ice Dance RD (event_id=1), Judge J5 appeared significant (p=0.002, mean deviation=−0.18) using stored `element_judge_deviations` values. Recomputing from raw `element_judge_scores` via `numpy.median()` gave p=0.117 (not significant, mean=−0.08). Investigating the discrepancy revealed the stored peer_median values were systematically wrong.

### Root Cause
`populate_element_deviations.py` (v1 script, in archive) computed peer_median using:
```sql
ORDER BY ejs2.judge_goe_int LIMIT 1 OFFSET 4
```
This always returns the **5th** sorted value of the 8 peer scores. For an even number of values, the true median is the average of the 4th and 5th sorted values. When those two values differ (e.g., 4 judges score 3, 4 judges score 4), the correct median is **3.5** but the v1 script stored **4.0** — a systematic overstatement of 0.5.

A v2 script existed that computed the correct (4th+5th)/2.0 formula, but the seed database had been populated with v1.

### Scale
- 37,732 of 200,715 rows in `element_judge_deviations` (18.8%) had wrong `peer_median` and `deviation`
- 36,561 of those now correctly contain half-integer values (±0.5, ±1.5) after repair
- The remaining 1,171 were "wrong formula, same result" cases (when 4th and 5th values happen to be equal)
- The error was a systematic downward bias in stored deviations (scores appeared more negative than they were)

### Fix
New script `repair_element_deviations_median.py`:
1. Backup: `cp figure_skating_ijs_seed.sqlite figure_skating_ijs_seed.sqlite.bak`
2. Dry-run confirmed 15.3% affected in first 1,000 rows
3. Full repair: recomputed correct `(val4+val5)/2.0` from `element_judge_scores`, updated all 37,732 affected rows, committed per-event
4. Verified: 36,561 half-integer peer_median values now exist; `PRAGMA integrity_check` = ok

### Key Lessons
1. **Median of an even number of values is never just the Nth value.** The true median of 8 values is `(4th + 5th) / 2.0`. An OFFSET-based SQL approach only works correctly if you fetch both middle values and average them.
2. **Always recompute from raw data when debugging statistical anomalies.** The raw `element_judge_scores` table was always correct; only the derived `element_judge_deviations` table was wrong.
3. **v2 scripts aren't always applied.** The correct v2 formula existed in the archive but the table was never repopulated with it.

---

---

## Incident 5: `apply_high_low_colors()` Silent No-Op — openpyxl formula strings (Feb 24, 2026)

### What Happened
After adding green/pink color coding for high/low judge marks in ISU – Elements (GOE) and ISU – PCS tabs, the function ran without errors but produced no colored cells in the output workbook.

### Root Cause
`apply_high_low_colors()` checks `isinstance(cell.value, (int, float))` to identify numeric judge marks. But the ISU source file (`owg2026_FSKXICEDANCE_FD_JudgesDetailsperSkater.xlsx`) was loaded with:
```python
isu_wb = openpyxl.load_workbook(ISU_FILE)   # without data_only=True
```
When `data_only=False` (the default), openpyxl returns formula strings (e.g. `"=7"`, or a formula referencing another cell) instead of their computed values. These strings fail the `isinstance(float)` check, so every row is silently skipped.

The ISU source was deliberately loaded without `data_only=True` because the Summary tab has cross-sheet formula references (`='Element Scores'!S13`) that need to be rewritten and preserved as formulas. Loading with `data_only=True` for that case would return `None` for all un-cached cells.

### Fix
Load the ISU file **twice** in `main()`:
```python
isu_wb      = openpyxl.load_workbook(ISU_FILE)              # formulas (for Summary remap)
isu_wb_data = openpyxl.load_workbook(ISU_FILE, data_only=True)  # values (for color coding)
```

Change `apply_high_low_colors()` to accept an optional `data_ws` argument:
```python
def apply_high_low_colors(ws, col_start, col_end, data_start_row, data_ws=None):
    src = data_ws if data_ws is not None else ws
    # read values from src, apply fills to ws
```

Call with the data-only worksheet:
```python
apply_high_low_colors(dst_ws, 7, 15, 5, data_ws=isu_wb_data["Element Scores"])
apply_high_low_colors(dst_ws, 6, 14, 5, data_ws=isu_wb_data["Program Component Scores"])
```

### Key Lesson
**Whenever openpyxl reads a workbook for formula strings AND numeric values, load it twice.** The `data_only=True` flag is required for any code that checks `isinstance(value, (int, float))`. A workbook loaded without `data_only` returns formula strings (or `None` for uncached cells) rather than computed values. This fails silently — the code runs without error but produces no output.

---

## Script Version History

| Script | Status | Notes |
|---|---|---|
| `calculate_pairwise_statistics.py` | Archived | v1 — Monte Carlo, 100k samples |
| `calculate_pairwise_statistics_v2.py` | Archived | v2 — true median fix, <= thresholds |
| `calculate_pairwise_statistics_v3.py` | Superseded | v3 — exact test, Python loop (too slow) |
| `calculate_pairwise_statistics_v4.py` | Superseded | v4 — exact test, NumPy vectorized, parallel (exchangeability flaw) |
| `calculate_isuimpact_v1.py` | **Current** | ISU-impact quantile permutation null (correct method) |
| `generate_official_scoring_xlsx.py` | **Current** | Generates 144 per-event ISU Excel files; 99.9% verification pass rate |
| `build_complete_event_workbook.py` | **Current** | Generates 12-tab journalist-ready workbook for a single event |
| `create_faq_document.py` | **Current** | Generates FAQ Word document for journalists/researchers |
| `repair_element_deviations_median.py` | Done | One-time repair for peer_median rounding bug (37,732 rows fixed Feb 22) |
