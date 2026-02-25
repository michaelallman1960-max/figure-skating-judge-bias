# ISU Ice Dance Scoring Methodology
## Complete Technical Reference — OSNR Project

**Source:** ISU Communication No. 2705 (Scale of Values, Ice Dance, 2025-26 Season) — read directly from downloaded PDF;
OWG2026_RD_Element1_Walkthrough.docx; verified against figure_skating_ijs_v3.sqlite
**Verified:** February 22, 2026 — exact GOE factors extracted from official SOV table, confirmed against OWG 2026 Ice Dance RD
(23 couples × 5 elements = 115 element observations; 17/23 exact match, 6/23 within 0.02 due to ISU internal rounding)
**PDF saved locally:** `ISU_Comm2705_SOV_IceDance_2025-26.pdf`

---

## 1. The Official ISU Document

The authoritative source for all element base values and GOE factors is:

> **ISU Communication No. 2705**
> "ICE DANCE Scale of Values valid as of July 1, 2025"
> Published June 3, 2025. Replaces ISU Communication No. 2647 (2024-25 season).

URLs:
- Governance copy: `https://isu-d8g8b4b7ece7aphs.a03.azurefd.net/isudamcontainer/CMS/Corporate-Site/Governance/Transparency/ISU-Communications/2705-ISU-SOV-IceDance-2025-26-Final-1746603209-5758.pdf`
- Handbook copy: `https://isu-d8g8b4b7ece7aphs.a03.azurefd.net/isudamcontainer/CMS/Corporate-Site/Sports-Rules/Figure-Skating-Rules/Handbooks-Ice-Dance/2705-ISU-SOV-IceDance-2025-26-updated-June2-1759232287-4354.pdf`

A new Scale of Values is published each season (effective July 1). Base values and GOE
factors can change between seasons.

---

## 2. Full Scoring Chain: Raw GOE Integers → TSS

### Step 1 — Technical Panel sets element levels
Before judging begins, the Technical Panel (separate from judges) calls the level
achieved (L1–L4) for each element based on prescribed difficulty features. The level
determines the Base Value (BV) from the Scale of Values table. The BV is fixed for the
entire panel — judges have no influence over it.

### Step 2 — Nine judges award GOE integers
Each judge independently awards a GOE of −5 to +5 for each element. Judges cannot
see each other's scores. This produces 9 raw integers per element.

### Step 3 — Trimmed mean GOE
Drop the single highest and single lowest GOE score. Sum the remaining 7. Divide by 7.

```
trimmed_sum = SUM(all 9 scores) − MAX(score) − MIN(score)
trimmed_mean = trimmed_sum / 7
```

The result is a decimal (e.g., 3.00, 2.86, −1.14). This is on the −5 to +5 scale.
The ISU's own language (from isu.org/figure-skating-rules/):
*"The highest and lowest score of each element or program component are ignored and the
average will be taken from the remainder, generating the trimmed mean (average score)."*

The trimmed mean is a unitless number; it must be converted to points in Step 4.

### Step 4 — Convert trimmed mean GOE to points (the GOE factor)
Multiply the trimmed mean by a pre-published GOE factor specific to the element type.
The factor converts "integer grades" into "scoring points."

```
panel_goe_points = ROUND(trimmed_mean × GOE_factor, 2)
element_score    = ROUND(base_value + panel_goe_points, 2)
```

**For ice dance, the GOE factor is an absolute number of points per integer grade,
set in the ISU Scale of Values. It is NOT a percentage of the base value.**
(This differs from singles/pairs skating, where the GOE factor is 10% of BV per grade.)

### Step 5 — Element Score
```
element_score = base_value + panel_goe_points
```

### Step 6 — Total Element Score (TES)
```
TES = SUM(element_score) across all elements in the program
```
5 elements in Rhythm Dance; 9 elements (typically) in Free Dance.

### Step 7 — Program Component Scores (PCS)
Same trimmed-mean structure, but:
- Judges award decimal marks from 0.25 to 10.00 (in 0.25 increments)
- Three components: Skating Skills, Composition, Presentation (post-2022/23 rules)
- Each component's trimmed mean is multiplied by a discipline/segment factor

```
trimmed_mean_component = (SUM(9 marks) − MAX − MIN) / 7
component_score = ROUND(trimmed_mean_component × pcs_factor, 2)
PCS = SUM(component_score) across all 3 components
```

PCS factor for Ice Dance: **1.33** for both Rhythm Dance and Free Dance (2025-26 season).

### Step 8 — Total Segment Score (TSS)
```
TSS = TES + PCS + deductions
```
Deductions are stored as negative numbers; TSS formula adds them (so a −1.00 deduction
reduces TSS by 1.00).

---

## 3. GOE Factors for Ice Dance Elements (2025-26 Season)

### 3a. Exact GOE Factors — from ISU Communication No. 2705

The ISU SOV table defines GOE values for each element at each level as absolute point
amounts. The factor per integer of trimmed mean GOE is read directly from the +1 column.

**Key structural insight:** For paired elements (twizzles, step sequences), each partner
has an individual GOE factor from the SOV. The combined factor applied to the panel's
trimmed mean GOE = Woman's factor + Man's factor.

#### Sequential Twizzles (SqTw) — from ISU Comm 2705

| Partner level | BV (per partner) | Factor per grade (from +1 col) |
|---|---|---|
| Basic (B) | 1.05 | 0.16 |
| Level 1 | 2.67 | **0.40** |
| Level 2 | 2.92 | **0.40** |
| Level 3 | 3.30 | **0.40** |
| Level 4 | 3.67 | **0.40** |

Combined element factor = Woman factor + Man factor. All L1–L4 combinations give
combined factor = **0.80** (0.40 + 0.40).

| Combined element | Combined BV | Combined factor |
|---|---|---|
| SqTwW4+SqTwM4 | 7.34 | **0.80** |
| SqTwW3+SqTwM4 | 6.97 | **0.80** |
| SqTwW3+SqTwM3 | 6.60 | **0.80** |
| SqTwW1+SqTwM4 | 6.34 | **0.80** |

**Truncated twizzle** (one partner fails to complete — no level awarded):
The Man's contribution is 0 points and 0 factor. Only the Woman's factor applies.
e.g., `SqTwW4+SqTwM` (M truncated): BV = 3.67 (W4 only), factor = **0.40** (W4 only).
Confirmed from data: ranks 22-23, factor = 0.40 exactly. ✓

#### Synchronized Twizzles (SyTw) — from ISU Comm 2705

| Level | BV (per partner) | Factor per grade |
|---|---|---|
| Basic | 0.80 | 0.12 |
| L1 | 2.42 | **0.36** |
| L2 | 2.67 | **0.36** |
| L3 | 3.05 | **0.36** |
| L4 | 3.42 | **0.36** |

Combined L4+L4: BV = 6.84, factor = **0.72**.

#### Step Sequences (MiSt, DiSt, CiSt, SeSt) — from ISU Comm 2705

| Level | BV (per partner) | Factor per grade |
|---|---|---|
| Basic | 2.25 | 0.34 |
| L1 | 3.48 | **0.52** |
| L2 | 3.73 | **0.52** |
| L3 | 4.10 | **0.52** |
| L4 | 4.48 | **0.52** |

Combined factor for all L1–L4 combinations = **1.04** (0.52 + 0.52).

| Combined element | Combined BV | Combined factor |
|---|---|---|
| MiStW3+MiStM3 | 8.20 | **1.04** |
| MiStW3+MiStM2 | 7.83 | **1.04** |
| MiStW2+MiStM2 | 7.46 | **1.04** |
| MiStW2+MiStM1 | 7.21 | **1.04** |
| MiStW1+MiStM1 | 6.96 | **1.04** |

#### Pattern Step Sequence (PSt) — single unit, from ISU Comm 2705

| Level | BV | Factor per grade |
|---|---|---|
| Basic | 5.00 | 0.75 |
| L1 | 7.45 | **1.12** |
| L2 | 7.95 | **1.12** |
| L3 | 8.70 | **1.12** |
| L4 | 9.45 | **1.12** |

Factor is identical across all levels (1.12). ✓

#### Lifts (RoLi, SlLi, StaLi, CuLi, CoLi) — from ISU Comm 2705

| Level | BV | Factor per grade |
|---|---|---|
| Basic | 1.15 | 0.17 |
| L1 | 3.20 | **0.48** |
| L2 | 3.95 | **0.48** |
| L3 | 4.70 | **0.48** |
| L4 | 5.45 | **0.48** |

All lift types (Rotational, Straight Line, Stationary, Curve) have identical factors. ✓

#### Choreographic Elements — from ISU Comm 2705

The GOE scale for choreographic elements is **asymmetric** — the positive steps are
larger than the negative steps. This is an intentional ISU design to reward creativity
without harshly penalizing it.

| Element | BV | GOE -1 | GOE +1 | GOE +5 |
|---|---|---|---|---|
| ChRS1 (Choreographic Rhythm Sequence) | 2.00 | −0.40 | **+1.50** | +7.50 |
| ChSt1 (Choreographic Character Step Seq.) | 1.10 | −0.22 | **+0.83** | +4.15 |
| ChLi1 (Choreographic Lift) | 1.10 | −0.22 | **+0.83** | +4.15 |

For positive GOE: factor = 1.50 per grade (ChRS1), 0.83 per grade (ChSt1, ChLi1).
For negative GOE: factor = 0.40 per grade (ChRS1), 0.22 per grade (ChSt1, ChLi1).
The formula `ROUND(trimmed_mean × factor, 2)` uses the positive factor for positive
trimmed means and the negative factor for negative trimmed means.

**Important:** In the OWG 2026 RD, all ChRS1 had positive trimmed means, so factor = 1.50
throughout. For programs with negative ChRS1 execution, the correct factor is 0.40.

### 3b. Verification Against Database

After applying exact ISU factors element-by-element from the SOV table:

| Metric | Value |
|---|---|
| Couples with TES diff < 0.01 (exact) | 17 / 23 |
| Couples with TES diff = 0.02 | 6 / 23 |
| Mean absolute TES difference | 0.010 points |
| Maximum TES difference | 0.020 points |

The remaining 0.02 gap in 6 couples is a floating-point / intermediate-rounding
artefact: the ISU likely rounds at a slightly different decimal point internally.
This is mathematically irreducible without knowing the ISU's exact computation order.

**Previous accuracy (back-calculated averages):** mean diff = 0.121, max = 1.230
**Current accuracy (exact ISU SOV factors):** mean diff = 0.010, max = 0.020 ✓

### 3b. Why Earlier Back-Calculated Factors Were Slightly Wrong

Our initial back-calculated "multipliers" (0.7652 for twizzles, 1.0439 for step seqs)
were averages computed across all couples using `factor = panel_goe_points / trimmed_mean`.
These were pulled off by:

1. **Twizzles:** The two truncated-element cases (ranks 22-23, factor=0.40, not 0.80)
   dragged the average below 0.80.
2. **Step sequences:** The exact factor from SOV is 1.04, not 1.04x — the slight
   variation observed (1.037–1.047) was rounding noise in the ISU's official scores,
   not a real variation in the factor.
3. **All elements:** At small trimmed means, dividing panel_goe_points by trimmed_mean
   amplifies any rounding in panel_goe_points, producing noisy estimates.

---

## 4. Correct Factors for the OWG2026_RD_Scoring_Model.xlsx Spreadsheet

The spreadsheet Multiplier column (col F) contains the GOE factor per element row.
Values are now set to exact ISU SOV figures, element-by-element:

| Element type | Factor | Source |
|---|---|---|
| SqTw (all L1-L4 combinations) | **0.80** | 0.40 W + 0.40 M |
| SqTw truncated (one partner, no level) | **0.40** | Only the completing partner counts |
| MiSt, DiSt, CiSt, SeSt (all L1-L4) | **1.04** | 0.52 W + 0.52 M |
| PSt (all levels) | **1.12** | Single unit, from SOV |
| ChRS1 (positive GOE) | **1.50** | Asymmetric SOV table |
| All lifts L1-L4 | **0.48** | Single unit, from SOV |

**The formula in the spreadsheet** (Panel GOE column = col Q):
```
=ROUND(P{row}/7*F{row}, 2)
```
where P is the Trimmed Sum (not yet divided by 7). Dividing by 7 gives the trimmed
mean; multiplying by the factor gives GOE points. ✓

**Accuracy achieved:** 17/23 couples match database exactly; 6/23 differ by 0.02 due
to ISU internal rounding order (irreducible without access to their source code).

---

## 5. Why the Database TES Differs Slightly from Spreadsheet TES

After correcting the factors to 0.80 / 1.05 / 1.12 / 1.50 / 0.48, a small residual
difference may remain for step sequences and pattern steps because:

1. The step sequence factor is not exactly 1.05 — it varies from 1.037 to 1.047
   by level. Using 1.05 slightly overestimates GOE for lower-level pairs.
2. The database values come directly from the official ISU PDF (parsed exactly).
   The ISU may apply additional rounding at an intermediate stage not visible in
   the public protocol.
3. The pattern step factor of 1.12 appears exact across all levels — no correction
   needed there.

**Bottom line:** The database is authoritative. The spreadsheet is a working model
that replicates the ISU calculation to ±0.10 for most couples; exact match requires
the full ISU SOV PDF to extract the precise per-level GOE tables.

---

## 6. PCS Factor Reference

| Discipline | Segment | PCS Factor | Components |
|---|---|---|---|
| Ice Dance | Rhythm Dance | **1.33** | Skating Skills, Composition, Presentation |
| Ice Dance | Free Dance | **1.33** | Skating Skills, Composition, Presentation |
| Men / Women | Short Program | 1.00 | Skating Skills, Transitions, Performance, Composition, Interpretation |
| Men / Women | Free Skating | 2.00 | (same 5 components) |
| Pairs | Short Program | 0.80 | (same 5 components) |
| Pairs | Free Skating | 1.60 | (same 5 components) |

Note: The 5-component structure was replaced with 3 components for ice dance starting
in the 2022-23 season. All events in our database from 2022-23 onward use 3 components.

---

## 7. Key Differences: Ice Dance vs. Singles/Pairs Scoring

| Feature | Singles / Pairs | Ice Dance |
|---|---|---|
| GOE scale | −5 to +5 (since 2018-19) | −5 to +5 |
| GOE factor basis | **10% of BV per grade** (varies by element) | **Fixed absolute factor** per element type |
| Elements per program | Short: 7–8; Free: 12–13 | RD: 5; FD: 9 |
| Component count | 5 components | 3 components (post-2022-23) |
| PCS factor | SP: 1.00 (M/W); FS: 2.00 (M/W) | 1.33 (both segments) |
| Level setting | Technical Panel, real-time | Technical Panel, real-time |
| Trimmed mean | Drop 1 high, 1 low of 9 | Drop 1 high, 1 low of 9 |

---

## 8. Document Links and Related Files

| Document | Contents |
|---|---|
| `OWG2026_RD_Element1_Walkthrough.docx` | Step-by-step scoring walkthrough for gold team, element 1 |
| `IceDance_BaseValues_Reference.docx` | Element types, what determines level, BV concepts |
| `ISU_TrimmedMean_Research_Memo.docx` | ISU's own language on trimmed mean; literature citations |
| `BI_Calculation_Method.docx` | How the OSNR BI(j) statistic is computed |
| `OWG2026_RD_Scoring_Model.xlsx` | Working spreadsheet: live formulas for all 23 couples |
| `OWG2026_RD_Raw_Scores.xlsx` | Original raw data (unchanged, hardcoded values) |
| `methodology_diagnosis_v1.md` | Why the current permutation test is statistically flawed |

---

*OSNR Project — Michael Allman — February 22, 2026*
