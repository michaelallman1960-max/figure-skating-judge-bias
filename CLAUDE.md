# CLAUDE.md — Judging Bias Project

Project-specific conventions for the ISU Figure Skating Judging Bias study.
Global conventions live in `~/CLAUDE.md`. This file takes precedence where there is overlap.

---

## Project Identity

- **Goal:** Detect systematic judging bias in ISU figure skating using a residual-label permutation test
- **Paper target:** JQAS (Journal of Quantitative Analysis in Sports)
- **Method tag:** `isuimpact_residual_v1` — residual-label permutation (Emerson et al. 2009)
- **Database:** `figure_skating_ijs_v4.sqlite` (~195 MB) — single canonical source of truth

---

## Active Conventions

- **Deductions are stored as negative numbers.** TSS = TES + PCS + ded (addition, not subtraction).
- **Significance threshold uses `<=` (not strict `<`).** `p <= 0.05`, `q <= 0.05` everywhere.
- **Current method:** `isuimpact_residual_v1` — residual-label permutation. Do not confuse with `isuimpact_quantile_v1` (retired, exchangeability flaw).
- **Primary analysis script:** `calculate_isuimpact_v2.py`. The v1 script is retired — do not re-run it.
- **All 12 output tabs in workbooks are locked** (no password) via openpyxl `ws.protection.enable()`.
- **ISU GOE tab column:** "GOE Factor*" with footnote re combined elements.
- **FAQ language:** BH-FDR = expected proportion of false discoveries, not per-finding probability.
- **Outcome-determinative test (two-part):** q ≤ 0.05 AND B_j(A,B) > pair's own TSS margin (directional, not absolute).

---

## Documentation Sync Rule

After editing any `.md` file, run:
```bash
python3 make_word_docs.py
```
This regenerates all corresponding `.docx` files. Never edit `.docx` files directly.

---

## Key Numbers (as of commit a2c05fb)

- 142 events analyzed (144 in DB; 2 excluded — 4C 2022 Ice Dance RD/FD, only 7 judges)
- 271,728 pairwise tests (isuimpact_residual_v1)
- M = 10,000 permutations, seed = 20260223, global CDF scope
- OWG 2026 Ice Dance FD (event_id=2): J1 BiasPoints(FRA,USA)=+1.19, p=0.0003, q=0.012
- 9 outcome-determinative events (6.3% of 142)
- LOJO: 150/1,288 judge removals change the winner (11.6%)

---

## Pre-Submission Check

Always run before any submission commit:
```bash
python3 check_spec_params.py
```
Exit code 0 = all parameters verified. This checks DB method version, seed, permutation count, event count, and scans the engineering spec + reproduction checklist for stale language.

---

## Database Safety

- **Always back up before any bulk DB operation:** `cp figure_skating_ijs_v4.sqlite figure_skating_ijs_v4.sqlite.bak`
- Repair scripts must be idempotent: unconditional `DELETE` before `INSERT`
- `sqlite3` does not auto-commit — always call `conn.commit()` explicitly

---

## Known Technical Debt

- `streamlit_app.py` and `_event_loader.py` use v3-era tables; full refactor to v4 deferred
- `significance_draft_v1.md` describes retired exact combinatorial test; needs method rewrite before Significance Magazine submission
