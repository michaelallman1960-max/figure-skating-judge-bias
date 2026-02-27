# Judging Bias in Figure Skating — ISU-Impact Audit Framework

**Detecting and Remedying Anomalous Judging in Competitive Figure Skating:
A Pairwise, Style-Controlled, Nonparametric Test**

Michael Allman, MBA · Independent Researcher · University of Chicago Booth School of Business

---

## Overview

This repository contains the complete data, analysis code, and documentation for a
statistical audit framework that detects systematic judging anomalies in competitive
figure skating using publicly available ISU scoring data.

The framework applies a **residual-label permutation test** (method: `isuimpact_residual_v1`)
to every pairwise judge-competitor comparison across a dataset of 17 major international
competitions (January 2022 – February 2026), including the 2022 and 2026 Olympic Winter Games.

### Key Findings

| Metric | Value |
|--------|-------|
| Competitions | 17 |
| Events analyzed | 142 |
| Competitor entries | 2,706 |
| Individual judge scores | 291,604 |
| Pairwise comparisons (residual-label method) | 271,728 |
| OWG 2026 Ice Dance FD: J1 p-value | 0.0003 (BH q = 0.012) |
| OWG 2026 Ice Dance FD: outcome-determinative | Yes — J1 bias +1.19 pts > 0.97 pt margin |
| LOJO: judge removals that change the winner | 150 of 1,288 (11.6%) |
| LOJO: judge removals that change the podium | 462 of 1,288 (35.9%) |
| LOJO: events with at least one winner-determinative judge | 27 of 144 |
| LOJO: events with at least one podium-determinative judge | 75 of 144 |

---

## Repository Structure

```
├── README.md                              # This file
├── requirements.txt                       # Python dependencies (pip install -r requirements.txt)
│
├── ── Analysis Pipeline ──
├── calculate_isuimpact_v2.py              # Primary analysis: residual-label permutation test
├── calculate_lojo_full.py                 # Leave-One-Judge-Out (LOJO) counterfactual
├── build_complete_event_workbook.py       # 12-tab Excel workbook generator (per event or all)
├── generate_official_scoring_xlsx.py      # ISU-format per-event scoring spreadsheets
├── build_v4_database.py                   # Builds figure_skating_ijs_v4.sqlite from source data
├── check_spec_params.py                   # Pre-submission gate: verifies DB/spec/paper consistency
│
├── ── Parsers ──
├── parse_singles_pairs.py                 # PDF parser — Singles and Pairs scoring sheets
├── parse_ice_dance.py                     # PDF parser — Ice Dance scoring sheets (all formats)
├── db_inserter.py                         # Database insertion module used by parsers
│
├── ── Output Generators ──
├── create_faq_document.py                 # Generates OWG2026_IceDance_FD_FAQ.docx
├── make_word_docs.py                      # Regenerates all .docx files from .md sources
│
├── ── Documentation ──
├── judge_bias_isu_judging_system.docx     # Submission draft — Scientific Reports (Nature Portfolio)
├── engineering_spec_isuimpact_v1.docx     # Developer implementation spec for independent replication
├── reproduction_checklist_isuimpact.docx  # Step-by-step replication guide
├── OWG2026_IceDance_FD_FAQ.docx           # OWG 2026 Ice Dance FD — journalist FAQ (41 Q&As)
├── faq_v1.md / .docx                      # General method FAQ
├── Data_Dictionary.md / .docx             # All 14 database table schemas and column definitions
├── database_summary.md / .docx            # Database overview — table sizes, row counts, relationships
├── glossary.md / .docx                    # Term definitions (BiasPoints, LOJO, BH-FDR, etc.)
├── pvalue_histogram.png                   # Figure 1 — p-value distribution across 271,728 tests
│
├── ── ISU Reference Materials ──
├── ISU_Comm2705_SOV_IceDance_2025-26.pdf  # ISU Scale of Values — source for GOE factors
├── ISU_Scoring_Methodology.md / .docx     # Summary of ISU trimmed-mean scoring rules
├── ISU_TrimmedMean_Research_Memo.docx     # Research memo on trimmed mean mechanics
├── IceDance_BaseValues_Reference.docx     # Ice Dance base value reference table
│
└── ── Data ──
    └── figure_skating_ijs_v4.sqlite       # Primary database (~195 MB) — see note below
```

> **Database note:** `figure_skating_ijs_v4.sqlite` (~195 MB) contains all scoring data
> plus `pairwise_impact_results` (271,728 rows, method `isuimpact_residual_v1`) and LOJO results.
> Due to GitHub file size limits, it is stored via [Git LFS](https://git-lfs.com/)
> or available as a direct download from [Releases](../../releases).

---

## Replicating the Analysis

The full analysis can be reproduced in five steps. Steps 1–2 are one-time setup; steps 3–5 reproduce all results in the paper.

### Step 1 — Install dependencies

```bash
pip install -r requirements.txt
brew install poppler   # macOS only; required for PDF parsing
```

### Step 2 — Obtain the database

The primary database (`figure_skating_ijs_v4.sqlite`, ~195 MB) is available from:
- **Zenodo:** [https://doi.org/10.5281/zenodo.18782656](https://doi.org/10.5281/zenodo.18782656) *(permanent, citable)*
- **GitHub Releases:** [Releases page](../../releases) *(direct download)*

Place the file in the repository root directory.

### Step 3 — Verify setup

```bash
python3 check_spec_params.py
```

Confirms that the database method version, RNG seed, permutation count, and event count all match the paper. All checks should pass before proceeding.

### Step 4 — Re-run the pairwise permutation test

```bash
python3 calculate_isuimpact_v2.py
```

Runs the residual-label permutation test across all 142 events (~17 minutes on M1 MacBook Pro). Populates `pairwise_impact_results` and `judge_team_impacts` in the database. **Method:** `isuimpact_residual_v1` | **Seed:** 20260223 | **M:** 10,000.

### Step 5 — Re-run the LOJO counterfactual

```bash
python3 calculate_lojo_full.py
```

Runs the Leave-One-Judge-Out counterfactual across all 144 events (~30 minutes). Populates `lojo_scores` and `lojo_event_summary` in the database.

### Generate per-event workbooks (optional)

```bash
python3 build_complete_event_workbook.py --event-id 2          # OWG 2026 Ice Dance FD
python3 build_complete_event_workbook.py --all-events          # all 142 events
python3 build_complete_event_workbook.py --all-events --dry-run  # preview without writing
```

Produces a 12-tab Excel workbook per event: raw scores, GOE/PCS breakdowns, BiasPoints table, permutation p-values, BH-corrected q-values, and LOJO counterfactual results.

---

## Statistical Method

### The ISU-Impact Bias Statistic

For judge j and scoring row r, compute the delta:

```
Δ(j, r) = F_r(actual marks) − F_r(neutralized marks)
```

where `F_r` is the ISU row scoring function (trimmed mean × factor, faithful to the
published spreadsheet) and the neutralized mark replaces judge j's mark with the
median of the other 8 judges. Aggregate over all rows for competitor T:

```
I_j(T) = Σ_r Δ(j, r)        B_j(A, B) = I_j(A) − I_j(B)
```

### Residual-Label Permutation Test

For each judge j and competitor pair (A, B):

1. Pool judge j's delta values for both entries: `d_pool = d_A ∪ d_B`
2. Under the null of no directional bias, delta labels are exchangeable across entries
   (median-of-8 neutralization removes the shared quality signal)
3. For M = 10,000 permutations: randomly split `d_pool` into groups of size |A| and |B|;
   compute `B_j^{perm}(A,B) = Σ(group A) − Σ(group B)`
4. `p = (1 + #{|B_perm| ≥ |B_obs|}) / (M + 1)`

Multiple testing: Benjamini–Hochberg FDR within event across all 9 × C(N,2) tests.

**Method tag:** `isuimpact_residual_v1` | **RNG seed:** 20260223 | **M:** 10,000

Reference: Emerson, Seltzer & Lin (2009). *Assessing Judging Bias: An Example From the
2000 Olympic Games.* The American Statistician 63(2), 124–131.

### Leave-One-Judge-Out (LOJO) Counterfactual

For each judge in each event: remove their scores, recompute trimmed means, re-rank
all competitors. A judge is *outcome-determinative* if removal changes any medal boundary.

---

## Dataset Coverage

| Competition | Years | Events |
|-------------|-------|--------|
| ISU European Figure Skating Championships | 2022–2025 | 32 |
| ISU Four Continents Figure Skating Championships | 2022–2025 | 32 |
| ISU World Figure Skating Championships | 2022–2025 | 32 |
| ISU Grand Prix of Figure Skating Final | 2022/23–2024/25 | 24 |
| Olympic Winter Games 2022 (Beijing) | 2022 | 8 |
| Olympic Winter Games 2026 (Milano–Cortina) | 2026 | 16 |
| **Total** | **2022–2026** | **142 analyzed** |

142 of 144 events analyzed; 2 excluded (4C 2022 Ice Dance RD/FD: 7-judge panels;
method requires 9). Disciplines: Men's Singles, Women's Singles, Pair Skating, Ice Dance.

---

## Reproducibility

See the **Replicating the Analysis** section above for the full step-by-step procedure.

The source PDFs are ISU 'Judges Details per Skater' documents, downloaded from the
[ISU results website](https://www.isu.org/figure-skating/results) and tracked in the
`sources` database table with SHA-256 hashes and retrieval timestamps.

For a detailed independent replication guide, see `reproduction_checklist_isuimpact.docx`.

---

## Citation

> Allman, M. (2026). *Detecting and Remedying Anomalous Judging in Competitive Figure
> Skating: A Permutation-Based Audit Framework*. [Submitted to Scientific Reports
> (Nature Portfolio).]

---

## License

- **Code:** MIT License
- **Data:** ISU scoring data sourced from publicly available ISU results documents
  compiled for research purposes.

---

## Contact

Michael Allman · University of Chicago Booth School of Business
