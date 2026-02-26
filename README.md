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
├── requirements.txt                       # Python dependencies
│
├── ── Analysis Pipeline ──
├── calculate_isuimpact_v2.py              # Primary analysis: residual-label permutation
├── calculate_lojo_full.py                 # Leave-One-Judge-Out (LOJO) counterfactual
├── build_complete_event_workbook.py       # 12-tab Excel workbook generator (per event)
├── generate_official_scoring_xlsx.py      # ISU-format per-event scoring files
├── build_v4_database.py                   # Database consolidation (already applied)
├── check_spec_params.py                   # Spec/DB parameter verification
│
├── ── Parsers ──
├── parse_singles_pairs.py                 # PDF parser — Singles and Pairs
├── parse_ice_dance.py                     # PDF parser — Ice Dance (all formats)
├── db_inserter.py                         # Database insertion module
│
├── ── Web App ──
├── streamlit_app.py                       # Interactive dashboard (4 pages)
│
├── ── Documentation ──
├── judge_bias_isu_judging_system.docx     # Submission draft (JQAS target)
├── engineering_spec_isuimpact_v1.docx     # Developer implementation spec (v1.2)
├── reproduction_checklist_isuimpact.docx  # Independent replication guide
├── OWG2026_IceDance_FD_FAQ.docx           # Journalist FAQ (41 Q&As)
├── Data_Dictionary.md / .docx            # All 14 table schemas and column definitions
├── glossary.md / .docx                   # Term definitions
├── file_inventory.md                     # Living list of all project files + status
│
├── ── Data ──
├── figure_skating_ijs_v4.sqlite           # Primary database (~195 MB)
├── source_pdfs/isu_sov/                   # ISU Scale of Values PDFs (reference)
├── excel_output/                          # 288 auto-generated workbooks (do not edit)
│
└── archive/                               # Retired scripts, old databases, legacy docs
```

> **Database note:** `figure_skating_ijs_v4.sqlite` (~195 MB) contains all scoring data
> plus pairwise_impact_results (v1 + v2 methods) and LOJO results.
> Due to GitHub file size limits, it is stored via [Git LFS](https://git-lfs.com/)
> or available as a direct download from [Releases](../../releases).

---

## Quick Start

### Requirements

```bash
pip install -r requirements.txt
brew install poppler   # for PDF parsing only (macOS)
```

### Launch the Web Dashboard

```bash
streamlit run streamlit_app.py
```

The dashboard provides four views:
1. **Competitions** — browse all 17 competitions and 142 analyzed events
2. **Event Analysis** — pairwise heatmap, LOJO counterfactual, significance summary
3. **Judge Profiles** — per-judge scoring patterns across events
4. **System-Wide Stats** — flag summary across all events

### Generate an Analysis Workbook

```bash
python3 build_complete_event_workbook.py --event-id 2          # OWG 2026 Ice Dance FD
python3 build_complete_event_workbook.py --all-events          # all 142 events
python3 build_complete_event_workbook.py --all-events --dry-run  # preview
```

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

```bash
# Verify database and spec are in sync — run before any submission commit
python3 check_spec_params.py

# Re-run pairwise analysis (~17 minutes on M1 MacBook Pro)
python3 calculate_isuimpact_v2.py

# Re-run LOJO counterfactual (~30 minutes)
python3 calculate_lojo_full.py
```

Source PDFs are ISU 'Judges Details per Skater' documents, downloaded from the
[ISU results website](https://www.isu.org/figure-skating/results).

---

## Citation

> Allman, M. (2026). *Detecting and Remedying Anomalous Judging in Competitive Figure
> Skating: A Permutation-Based Audit Framework*. [Submitted to Journal of Quantitative
> Analysis in Sports.]

---

## License

- **Code:** MIT License
- **Data:** ISU scoring data sourced from publicly available ISU results documents
  compiled for research purposes.

---

## Contact

Michael Allman · University of Chicago Booth School of Business
