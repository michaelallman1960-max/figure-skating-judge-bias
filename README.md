# Judging Bias in Figure Skating — OSNR Audit Framework

**Detecting and Remedying Anomalous Judging in Competitive Figure Skating: A Permutation-Based Audit Framework**

Michael Allman, MBA · Independent Researcher · University of Chicago Booth School of Business

---

## Overview

This repository contains the complete data, analysis code, and documentation for a statistical audit framework — the **Outlier Score Nullification Rule (OSNR)** — that detects systematic judging anomalies in competitive figure skating using publicly available ISU scoring data.

The framework applies an **exact combinatorial permutation test** to every pairwise judge-competitor comparison across a dataset of 17 major international competitions (January 2022 – February 2026), including the 2022 and 2026 Olympic Winter Games.

### Key Findings

| Metric | Value |
|--------|-------|
| Competitions | 17 |
| Events (discipline × segment) | 142 analyzed (144 in DB; 2 excluded — 4C 2022 Ice Dance had 7-judge panels) |
| Competitor entries | 2,706 |
| Individual judge scores | 291,604 |
| Pairwise comparisons (ISU-impact method) | 271,728 |
| OWG 2026 Ice Dance FD: J1 p-value | 0.0003 (BH q = 0.034) |
| OWG 2026 Ice Dance FD: outcome-determinative | Yes — J1 bias +1.19 pts > 0.97 pt margin |
| LOJO podium changes | 462 |
| LOJO gold medal changes | 150 |

> ⚠️ **Methodology Note (February 2026):** The B(j) pairwise test described in some sections
> of this README is **deprecated** due to a known exchangeability flaw (~560× inflation).
> The current primary method is **ISU-impact** (`calculate_isuimpact_v1.py`, `seed.sqlite`).
> Numbers referencing "2,812 significant at p≤0.001" or "264,854 pairwise comparisons" are
> from the deprecated method and will be updated once the corrected residual deviation test is run.

---

## Repository Structure

```
├── README.md                    # This file
├── requirements.txt             # Python dependencies (pip install -r requirements.txt)
├── launch_dashboard.sh          # One-click launcher for the Streamlit web app
│
├── src/
│   ├── streamlit_app.py                      # Interactive web dashboard (4 pages)
│   ├── generate_event_report.py              # Excel report generator (7-tab workbook)
│   ├── calculate_pairwise_statistics_v3.py   # Exact combinatorial permutation test
│   ├── calculate_lojo_full.py                # Leave-One-Judge-Out counterfactual
│   ├── parse_singles_pairs.py                # PDF parser — Singles and Pairs
│   ├── parse_ice_dance.py                    # PDF parser — Ice Dance (all formats)
│   └── db_inserter.py                        # Database insertion module
│
├── docs/
│   ├── project_documentation.md  # Comprehensive methodology and architecture
│   ├── Data_Dictionary.md        # All database fields and table schemas
│   ├── glossary.md               # Definitions: OSNR, LOJO, BI(j), Tier 1/2
│   ├── BI_Calculation_Method.docx
│   ├── Data_Dictionary.docx
│   ├── glossary.docx
│   └── analysis_queries.sql      # Example SQL queries for database exploration
│
├── data/
│   └── figure_skating_ijs.sqlite  # Complete database (~104 MB; see note below)
│
└── source_pdfs/
    └── figure_skating_seed_bundle/
        └── isu_pdfs/              # All ISU source PDFs organized by competition
            ├── owg2026/
            ├── owg2022/
            ├── wc2025/
            └── ...
```

> **Database note:** `figure_skating_ijs.sqlite` (~104 MB) contains all scoring data plus pairwise statistics. Due to GitHub file size limits, it is stored via [Git LFS](https://git-lfs.com/) or available as a direct download from [Releases](../../releases).

---

## Quick Start

### Requirements

```bash
pip install -r requirements.txt
brew install poppler   # for PDF parsing only (macOS)
```

### Launch the Web Dashboard

```bash
streamlit run src/streamlit_app.py
```

The dashboard provides four views:
1. **Competitions** — browse all 17 competitions and 142 analyzed events
2. **Event Analysis** — OSNR pairwise heatmap, LOJO counterfactual, significance summary for any event
3. **Judge Profiles** — per-judge scoring patterns across events
4. **System-Wide Stats** — Tier 1 and Tier 2 flag summary across the full dataset

### Generate an Excel Report

```bash
python src/generate_event_report.py
```

Produces a 7-tab Excel workbook for any event with raw scores, element deviations, BI(j) statistics, permutation p-values, and LOJO counterfactual results.

---

## Statistical Method

### The B(j) Bias Statistic

For a given judge j and competitor pair (A, B), the bias statistic is:

```
B(j, A, B) = mean{ d(u, j) : u ∈ elements of A } − mean{ d(u, j) : u ∈ elements of B }
```

where `d(u, j)` is judge j's deviation from the panel consensus on element u (peer deviation).

### Exact Combinatorial Permutation Test

For a program with k elements per competitor:

1. Pool all 2k peer deviations (A's k + B's k)
2. Enumerate **all C(2k, k)** distinct splits of the pool into two equal groups:
   - k = 9 elements (Free Dance, Short Program): **C(18,9) = 48,620 splits**
   - k = 12 elements (Free Skating): **C(24,12) = 2,704,156 splits**
3. Compute simulated B_sim for each split
4. **p-value = extreme_count / C(2k, k)** — exact fraction, not an estimate

No random seed. No sampling error. Fully deterministic.

### Two-Tier OSNR Decision Rule

| Tier | Condition | Action |
|------|-----------|--------|
| Tier 1 | p ≤ 0.01 | Flag for integrity panel review; result provisional |
| Tier 2 | p ≤ 0.001 **AND** LOJO removes judge changes podium | Automatic score adjustment (replace judge scores with trimmed panel mean) |

### Leave-One-Judge-Out (LOJO) Counterfactual

For each judge in each event: remove their scores, recompute trimmed means, re-rank all competitors. A judge is *outcome-determinative* if their removal changes any medal boundary result.

---

## Dataset Coverage

| Competition | Years | Events |
|-------------|-------|--------|
| ISU European Figure Skating Championships | 2022–2025 | 32 |
| ISU Four Continents Figure Skating Championships | 2022–2025 | 32 |
| ISU World Figure Skating Championships | 2022–2025 | 32 |
| ISU Grand Prix of Figure Skating Final | 2022/23, 2023/24, 2024/25 | 24 |
| Olympic Winter Games 2022 (Beijing) | 2022 | 8 |
| Olympic Winter Games 2026 (Milano–Cortina) | 2026 | 16 |
| **Total** | **2022–2026** | **142 analyzed** |

Disciplines: Men's Singles, Women's Singles, Pair Skating, Ice Dance (each: Short Program + Free Skating/Dance + Rhythm Dance).

---

## Reproducibility

All results are reproducible from the source PDFs:

```bash
# Re-run pairwise analysis (WARNING: ~17–18 hours on a standard laptop)
python src/calculate_pairwise_statistics_v3.py

# Re-run LOJO counterfactual (~30 minutes)
python src/calculate_lojo_full.py
```

Source PDFs in `source_pdfs/` are the original ISU documents, downloaded from the [ISU results website](https://www.isu.org/figure-skating/results).

---

## Citation

> Allman, M. (2026). *Detecting and Remedying Anomalous Judging in Competitive Figure Skating: A Permutation-Based Audit Framework*. [Submitted to Journal of Quantitative Analysis in Sports.]

---

## License

- **Code:** MIT License
- **Data:** ISU scoring data is sourced from publicly available ISU results documents compiled for research purposes.

---

## Contact

Michael Allman · University of Chicago Booth School of Business
