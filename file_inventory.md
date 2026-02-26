# Project File Inventory
**Judging Bias — ISU-Impact Audit Framework**
_Last updated: 2026-02-26 | Maintained by: update this file whenever a file is created, archived, or significantly changed_

---

## How to use this file
- Add a row whenever a file is **created**, **archived**, or **renamed**
- Change **Status** immediately when a file becomes outdated or is superseded
- "Needs update" = content is stale but still the right file; schedule the fix
- "Delete" = no longer needed; remove file and this row together

Status values: `current` · `needs-update` · `outdated` · `delete`

---

## 1. Database

| File | Description | Status | Last modified |
|------|-------------|--------|---------------|
| `figure_skating_ijs_v4.sqlite` | **Primary database** — 14 tables, 142 analyzed events, all scoring data + pairwise_impact_results (v1 + v2) + LOJO results (~195 MB) | current | 2026-02-26 |
| `figure_skating_seed_bundle/` | Seed data bundle (ISU-impact inputs, used to build v4 DB) | current | 2026-02-25 |

---

## 2. Analysis Scripts (Python)

| File | Description | Status | Last modified |
|------|-------------|--------|---------------|
| `calculate_isuimpact_v2.py` | **Primary analysis script** — residual-label permutation method (isuimpact_residual_v1); M=10,000, seed=20260223. No CDF — pools judge deltas and permutes labels. Writes to `pairwise_impact_results` + `judge_team_impacts`. | current | 2026-02-26 |
| `calculate_isuimpact_v1.py` | Retired v1 script — quantile permutation null (exchangeability flaw). Kept for reference/reproducibility. Do not re-run. | outdated | 2026-02-24 |
| `calculate_lojo_full.py` | LOJO (Leave-One-Judge-Out) counterfactual — removes each judge, re-ranks, writes to `lojo_scores` + `lojo_event_summary`. ~30 min runtime. | current | 2026-02-24 |
| `friedman_test_event2.py` | One-off validation: Friedman + Nemenyi test on event_id=2 (OWG 2026 Ice Dance FD). Confirms J1 significant (χ²=69.98, p<0.001). Not part of main pipeline. | current | 2026-02-26 |
| `check_spec_params.py` | Validates that all method parameters in code match engineering_spec. Run before any submission commit. | current | 2026-02-26 |
| `build_complete_event_workbook.py` | Generates 12-tab Excel analysis workbook per event. Supports `--event-id`, `--dry-run`, `--all-events`, `--method-version`. Filters all DB queries by method_version (default: isuimpact_residual_v1). All sheets locked (no password). | current | 2026-02-26 |
| `generate_official_scoring_xlsx.py` | Generates ISU-format per-event scoring files (144 files, one per event including excluded). | current | 2026-02-22 |
| `build_v4_database.py` | Database consolidation script — merged v3 (LOJO) + seed (ISU-impact) into v4. Dry-run by default, `--apply` to build. Already run; v4 DB is live. | current | 2026-02-24 |
| `create_faq_document.py` | Generates `OWG2026_IceDance_FD_FAQ.docx` journalist FAQ (8 categories, 41 Q&As). Values hardcoded from verified DB query. | current | 2026-02-24 |
| `make_word_docs.py` | Converts all `.md` docs to `.docx` counterparts via python-docx. Run after editing any `.md` file. | current | 2026-02-26 |
| `fix_chatgpt_issues_2_to_6.py` | One-shot fix script — first ChatGPT review (Session 31): Table 5 directionality, event counts 11→9, Valieva note, page numbers. | archive-candidate | 2026-02-26 |
| `fix_section6_cleanup.py` | One-shot fix script — second ChatGPT review (Session 31): strip stale §6.2/6.3/6.4, OWG null attribution, Appendix A v1 tag, Table 2 footnote, CDF scope removal, Table A softening, Table 1 caption. | archive-candidate | 2026-02-26 |
| `fix_third_review.py` | One-shot fix script — third ChatGPT review (Session 31): "Nine" correction, Table 3 caption, LOJO 144 sentence, event-local clarification, Appendix A miscalibration, §6.2 pooling justification. | archive-candidate | 2026-02-26 |
| `fix_fourth_review.py` | One-shot fix script — fourth ChatGPT review (Session 31): J5 factual correction, §6.2 dependence sentence, margin definition, §9.5 uniform density, Appendix A simplification, null models phrasing. | archive-candidate | 2026-02-26 |
| `fix_fifth_review.py` | One-shot fix script — fifth ChatGPT review (Session 31): exchangeability formalization, pure-null qualifier, p-value histogram generation + Figure 1 insertion. | archive-candidate | 2026-02-26 |

---

## 3. Parser Scripts (Python)

| File | Description | Status | Last modified |
|------|-------------|--------|---------------|
| `parse_singles_pairs.py` | PDF parser — Singles and Pairs ISU scoring sheets → DB inserts | current | 2026-02-22 |
| `parse_ice_dance.py` | PDF parser — Ice Dance ISU scoring sheets (all formats) → DB inserts | current | 2026-02-22 |
| `db_inserter.py` | Database insertion module shared by parsers | current | 2026-02-16 |

---

## 4. App / Utility Scripts

| File | Description | Status | Last modified |
|------|-------------|--------|---------------|
| `streamlit_app.py` | Interactive web dashboard — 4 pages (Competitions, Event Analysis, Judge Profiles, System-Wide Stats). Uses v3-era `_event_loader.py` shim; full refactor to v4 pending. | needs-update | 2026-02-26 |
| `_event_loader.py` | Compatibility shim — `load_event_data()` extracted from archived `generate_event_report.py`. Queries some v3-era tables (`pairwise_judge_statistics`, `judge_event_statistics`). Stopgap until Streamlit refactor. | needs-update | 2026-02-26 |

---

## 5. Technical Documentation (source `.md` + generated `.docx`)

_Rule: edit the `.md` file, then run `python3 make_word_docs.py` to regenerate `.docx`._

| File (md + docx) | Description | Status | Last modified |
|------------------|-------------|--------|---------------|
| `Data_Dictionary` | All 14 table schemas, column definitions, data types. Last verified against v4 DB. | current | 2026-02-26 |
| `database_summary` | High-level DB architecture: table list, row counts, pipeline description. | current | 2026-02-26 |
| `glossary` | Term definitions: ISU-impact, LOJO, BiasPoints, Tier 1/2, etc. | current | 2026-02-26 |
| `methodology_diagnosis_v1` | Root-cause analysis of exchangeability flaw in v1 B(j) test; rationale for switching to residual-label permutation. Historical reference. | current | 2026-02-26 |
| `ISU_Scoring_Methodology` | Reference doc: how IJS trimmed-mean scoring works, GOE factors, PCS, deductions. | current | 2026-02-22 |
| `reproduction_checklist_isuimpact` (.docx only) | Step-by-step independent replication spec. Updated to residual-label permutation method (v2). | current | 2026-02-26 |
| `engineering_spec_isuimpact_v1` (.docx only) | Developer implementation guide — v1.2, residual-label permutation method. Seed, M, and method version verified by `check_spec_params.py`. | current | 2026-02-26 |
| `project_documentation` | Comprehensive methodology and architecture overview. May be partially outdated (pre-v2). | needs-update | 2026-02-24 |
| `debugging.md` | Bug fix history — root causes and resolutions for all non-trivial incidents. | current | 2026-02-24 |
| `history_log` | Full session-by-session work log (Sessions 1–24 archived). | current | 2026-02-24 |
| `post_10k_checklist.md` | Post-10k-run verification checklist (completed 2026-02-24). Historical reference. | current | 2026-02-24 |

---

## 6. The Paper

| File | Description | Status | Last modified |
|------|-------------|--------|---------------|
| `judge_bias_isu_judging_system.docx` | **Submission draft** — main academic paper (JQAS target). Five rounds of ChatGPT review applied (Sessions 31). Event count corrected 11→9, J5 factual error fixed, Figure 1 (p-value histogram) added, exchangeability formalized, structural/attribution cleanup. Latest: commit bfdef94. | current | 2026-02-26 |
| `pvalue_histogram.png` | Figure 1 in paper — histogram of 271,728 permutation p-values (isuimpact_residual_v1). Red bar = p≤0.05 (25.4%); blue bars = upper tail; dashed line = pure null reference. Generated by `fix_fifth_review.py`. | current | 2026-02-26 |
| `significance_draft_v1` (md + docx) | Significance Magazine article draft (~1,480 words). Describes retired exact combinatorial test throughout; needs full method rewrite. | needs-update | 2026-02-26 |

---

## 7. Press / Media Documents

| File | Description | Status | Last modified |
|------|-------------|--------|---------------|
| `OWG2026_IceDance_FD_FAQ.docx` | Journalist FAQ — OWG 2026 Ice Dance FD finding (43 KB, 41 Q&As). Updated 2026-02-26: method = isuimpact_residual_v1, q = 0.012. Press-ready. | current | 2026-02-26 |
| `faq_v1` (md + docx) | General FAQ — broader methodology and findings. | current | 2026-02-24 |
| `oped_draft` (md + docx) | Op-ed draft for general publication. | current | 2026-02-24 |
| `media_strategy` (md + docx) | Press outreach strategy and outlet list. | current | 2026-02-24 |
| `pitch_drafts_2026-02-23.md` | Pitch email drafts for journalists (NYT, Guardian, Athletic, Sportico). | current | 2026-02-23 |
| `cover_emails_2026-02-24` (md + docx) | Cover emails sent with press kit (2026-02-24). | current | 2026-02-24 |
| `revenue_strategy` (md + docx) | Monetization and licensing strategy. | current | 2026-02-24 |
| `ip_protection` (md + docx) | Intellectual property protection memo. | current | 2026-02-24 |
| `journal_strategy` (md + docx) | Journal submission strategy (JQAS primary; fallback sequence). | current | 2026-02-24 |

---

## 8. Reference Documents (.docx, not generated from .md)

| File | Description | Status | Last modified |
|------|-------------|--------|---------------|
| `ISU_TrimmedMean_Research_Memo.docx` | Research memo on ISU trimmed-mean calculation methodology. | current | 2026-02-18 |
| `IceDance_BaseValues_Reference.docx` | Ice dance element base values reference table. | current | 2026-02-18 |
| `project_documentation.docx` | Comprehensive project overview (may be pre-v2). | needs-update | 2026-02-21 |

---

## 9. Source Data

| File/Directory | Description | Status | Last modified |
|----------------|-------------|--------|---------------|
| `source_pdfs/isu_sov/` | ISU Scale of Values PDFs (8 files, 2025-26 season). Live reference for parsers. | current | 2026-02-22 |
| `ISU_Comm2705_SOV_IceDance_2025-26.pdf` | ISU Communication 2705 — Ice Dance SOV 2025-26. Reference for base values. | current | 2026-02-22 |
| `Literature Review/` | Academic papers and references (35 items). Read-only reference library. | current | 2026-02-18 |
| `excel_output/` | 288 files: 144 ISU scoring xlsx + 142 analysis workbooks + 2 misc. Auto-generated; do not edit. | current | 2026-02-26 |

---

## 10. Configuration / Setup

| File | Description | Status | Last modified |
|------|-------------|--------|---------------|
| `requirements.txt` | Python dependencies. Missing `python-docx>=1.1.0`; v1→v2 comment stale. | needs-update | 2026-02-24 |
| `.gitignore` | Git ignore rules — includes `*.sqlite`, `*.sqlite.bak*`, `__pycache__/`, etc. | current | 2026-02-26 |
| `.gitattributes` | Git LFS configuration for large files. | current | 2026-02-21 |

---

## 11. Archive (do not edit, do not delete)

| Directory/File | Description |
|----------------|-------------|
| `archive/` | Archived scripts, databases, docs, logs. See `archive/` subdirectory for contents. |
| `archive/generate_event_report.py` | Original Excel report generator (superseded by `build_complete_event_workbook.py`). Source of `_event_loader.py`. |
| `archive/databases/` | v3 and seed SQLite databases (superseded by v4). |
| `archive/docs/` | Historical status reports, old specs. |
| `archive/analysis/` | Old analysis scripts. |
| `archive/scripts/` | Old utility scripts. |
| `archive/templates/` | Old HTML dashboard (superseded by Streamlit). |
| `archive/Launch Dashboard.app` | Archived macOS launcher app. |
| `archive/Stop Dashboard Server.app` | Archived macOS stop-server app. |

---

## Project Documentation Files

| File | Description | Status |
|------|-------------|--------|
| `LESSONS-LEARNED.md` | Hard-won patterns, debugging insights, python-docx gotchas, statistical correctness notes. | current |
| `history_log.md` | Full session history (Sessions 1–31+); Sessions 1–24 in `archive/docs/status_reports/`. | current |
| `debugging.md` | Active incident writeups and recovery procedures (Incidents 1–5). | current |

---

## Files Deleted This Session
| File | Reason | Date |
|------|--------|------|
| `figure_skating_ijs_v4.sqlite.bak_v2` | 104 MB backup no longer needed; gitignored | 2026-02-26 |
