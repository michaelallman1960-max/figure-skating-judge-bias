# Post-10k Run Checklist

When `calculate_isuimpact_v1.py --permutations 10000` finishes, complete these steps in order.

---

## Step 1 — Verify the Run (15 min)

```python
# Query permutation counts
SELECT permutations, COUNT(DISTINCT event_id) as events
FROM pairwise_impact_results
GROUP BY permutations ORDER BY permutations;
# Expected: one row only — 10,000 | 142
# (142 events in DB; events 148 & 149 excluded — 4C 2022 Ice Dance had only 7 judges, method requires 9)
```

```bash
# Integrity check
sqlite3 figure_skating_ijs_v4.sqlite "PRAGMA integrity_check;"
# Expected: ok
```

```python
# Spot-check OWG 2026 FD key result (event_id=2)
SELECT judge_position, noc_a, noc_b, bias_points, p_value, q_value_bh, permutations
FROM pairwise_impact_results
WHERE event_id=2 AND noc_a='FRA' AND noc_b='USA'
ORDER BY judge_position;
# Expected: J1, bias=+1.19, p=0.0003, q=0.034, permutations=10000
```

```python
# Confirm total row counts unchanged
SELECT COUNT(*) FROM pairwise_impact_results;  -- 271,728
SELECT COUNT(*) FROM judge_team_impacts;        -- 24,174
SELECT COUNT(*) FROM lojo_event_summary;        -- 1,288
```

---

## Step 2 — Clean Up

- [ ] Delete `figure_skating_ijs_v4.sqlite.bak_before_full_10k` (~101 MB) from `archive/databases/`
- [ ] Update MEMORY.md: change "Full 10k rerun in progress" → confirmed complete with date
- [ ] Checkpoint WAL: `PRAGMA wal_checkpoint(TRUNCATE)`

---

## Step 3 — Generalize Workbook Builder (new session)

`build_complete_event_workbook.py` is currently hardcoded to `EVENT_ID = 2` and one specific
ISU source file. Generalize it:

- [ ] Add `--event-id` argument (argparse)
- [ ] Query DB for event metadata (competition code, segment code, event name) to construct
  the ISU source filename dynamically from `excel_output/`
- [ ] Query DB for ISU source filename pattern — verify all 142 events have a matching
  `JudgesDetailsperSkater.xlsx` in `excel_output/`
- [ ] Add `--dry-run` flag (print what would be built, don't write)
- [ ] Test on one non-OWG event before batch run
- [ ] Add `--all-events` flag for batch mode

**ISU source file naming convention to verify:**
Current known pattern: `{comp_code}_{segment_code}_JudgesDetailsperSkater.xlsx`
e.g. `owg2026_FSKXICEDANCE_FD_JudgesDetailsperSkater.xlsx`
Check whether all 142 files follow this pattern before coding the lookup.

---

## Step 4 — Regenerate All 142 Event Workbooks

Once Step 3 is done and tested:

- [ ] Dry-run: `python3 build_complete_event_workbook.py --all-events --dry-run`
  → verify all 144 source files found, no missing events
- [ ] Batch run: `python3 build_complete_event_workbook.py --all-events`
- [ ] Spot-check 3–5 output workbooks (different disciplines, different competitions)
- [ ] Verify OWG 2026 FD workbook still matches verified key result (bias=+1.19)
- [ ] Archive old raw scoring files from `excel_output/` (or overwrite in place)

---

## Step 5 — Run Full Audit

The audit report (archived at `archive/docs/audits/AUDIT-REPORT-2026-02-24.md`) specified:
*"Next audit recommended after: corrected pairwise methodology implemented."*

That means H1 (residual deviation B(j) correction) should come first.
See MEMORY.md Pending Task 6.

---

## Other Pending Items (no strict ordering)

- [ ] **Re-upload press kit** to Google Drive — workbook + FAQ + op-ed all updated since
  last upload (see MEMORY.md Press Kit Status)
- [ ] **Update stale docs** — `faq_v1`, `media_strategy`, `ip_protection` still reference
  B(j)/OSNR numbers and the "OSNR" name; update to ISU-impact numbers and terminology
- [ ] **Decide CDF scope** — global (current default) vs. event-scope for isuimpact
- [ ] **H1: Residual deviation correction** for B(j) pairwise test (separate session;
  see `methodology_diagnosis_v1.md` and archived `residual_deviation_owg2026_ice_dance_fd.md`)
- [ ] **paper_draft_v3.docx** — Section 9 ("Multi-event results") still says "TBD";
  needs populating once all workbooks are generated and H1 is done
- [ ] **Run audit** — after H1 complete; see `archive/docs/audits/AUDIT-REPORT-2026-02-24.md`
  for baseline scores to compare against

---

*Created: 2026-02-24 | Trigger: 10k permutation rerun completes*
