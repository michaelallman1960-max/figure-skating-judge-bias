# OWG 2026 Ice Dance Free Dance — Statistical Analysis Walkthrough

## Introduction

The Olympic Winter Games 2026 Ice Dance Free Dance included 20 competing teams and a panel of 9 judges. This document illustrates the statistical method used by OSNR to test whether a judge's scoring pattern reflects a systematic bias toward one competitor over another. The example uses Judge 1 (Jezabel Dabouis, France) and the pair FOURNIER BEAUDRY / CIZERON (FRA) vs. CHOCK / BATES (USA) — the gold and silver medalists. The analysis shows step by step how raw scores become the BI(j) statistic and how its significance is assessed.

---

## The Raw Scores

Every judge scores every element with a GOE integer from −5 to +5. The tables below show every judge's score for every element for both teams. J1's scores are shown in **bold**.

**FOURNIER BEAUDRY / CIZERON (FRA)**

| # | Element | J1 | J2 | J3 | J4 | J5 | J6 | J7 | J8 | J9 |
|---|---------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| 1 | SyTwW4+SyTwM3 | **3** | 2 | 3 | 0 | 2 | 2 | 3 | 4 | 4 |
| 2 | OFTW3+OFTM4   | **4** | 4 | 4 | 4 | 4 | 5 | 3 | 4 | 5 |
| 3 | RoLi4         | **5** | 5 | 4 | 5 | 5 | 5 | 5 | 4 | 4 |
| 4 | DSp4          | **4** | 4 | 5 | 4 | 4 | 5 | 4 | 4 | 5 |
| 5 | CuLi4+CuLi4   | **5** | 5 | 5 | 4 | 5 | 5 | 5 | 5 | 5 |
| 6 | SeStW3+SeStM3 | **4** | 3 | 4 | 3 | 4 | 3 | 4 | 2 | 4 |
| 7 | ChAJ1         | **5** | 5 | 5 | 4 | 4 | 5 | 4 | 5 | 5 |
| 8 | ChSt1         | **5** | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| 9 | ChLi1         | **5** | 5 | 5 | 5 | 4 | 5 | 5 | 4 | 5 |

**CHOCK / BATES (USA)**

| # | Element | J1 | J2 | J3 | J4 | J5 | J6 | J7 | J8 | J9 |
|---|---------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| 1 | ChAJ1         | **4** | 4 | 4 | 5 | 5 | 5 | 4 | 5 | 5 |
| 2 | CuLi4+CuLi4   | **4** | 4 | 5 | 5 | 5 | 4 | 5 | 5 | 4 |
| 3 | SyTwW4+SyTwM4 | **3** | 4 | 3 | 3 | 4 | 5 | 5 | 3 | 4 |
| 4 | ChSt1         | **4** | 5 | 5 | 4 | 5 | 5 | 5 | 5 | 5 |
| 5 | OFTW3+OFTM3   | **3** | 4 | 4 | 3 | 4 | 4 | 4 | 4 | 4 |
| 6 | RoLi4         | **5** | 5 | 5 | 5 | 5 | 4 | 5 | 5 | 4 |
| 7 | DSp4          | **4** | 4 | 4 | 3 | 4 | 4 | 4 | 4 | 4 |
| 8 | DiStW3+DiStM3 | **3** | 4 | 3 | 3 | 4 | 4 | 4 | 4 | 4 |
| 9 | ChSl1         | **4** | 5 | 4 | 4 | 5 | 5 | 4 | 5 | 5 |

---

## The Deviation Table

For each element, the **peer median** is the true mathematical median of the *other 8 judges'* scores — the (4th + 5th sorted values) ÷ 2. This is the panel consensus for that element. J1's deviation is J1's score minus that peer median. A positive deviation means J1 scored that competitor higher than the panel consensus; negative means lower.

| # | Element | J1→FRA | Panel med (FRA) | J1 dev (FRA) | J1→USA | Panel med (USA) | J1 dev (USA) | Net gap |
|---|---------|:------:|:---------------:|:------------:|:------:|:---------------:|:------------:|:-------:|
| 1 | SyTwW4+SyTwM3 | 3 | 2.5 | +0.50 | 4 | 5.0 | −1.00 | **+1.50** |
| 2 | OFTW3+OFTM4   | 4 | 4.0 | +0.00 | 4 | 5.0 | −1.00 | **+1.00** |
| 3 | RoLi4         | 5 | 5.0 | +0.00 | 3 | 4.0 | −1.00 | **+1.00** |
| 4 | DSp4          | 4 | 4.0 | +0.00 | 4 | 5.0 | −1.00 | **+1.00** |
| 5 | CuLi4+CuLi4   | 5 | 5.0 | +0.00 | 3 | 4.0 | −1.00 | **+1.00** |
| 6 | SeStW3+SeStM3 | 4 | 3.5 | +0.50 | 5 | 5.0 | +0.00 | **+0.50** |
| 7 | ChAJ1         | 5 | 5.0 | +0.00 | 4 | 4.0 | +0.00 | **+0.00** |
| 8 | ChSt1         | 5 | 5.0 | +0.00 | 3 | 4.0 | −1.00 | **+1.00** |
| 9 | ChLi1         | 5 | 5.0 | +0.00 | 4 | 5.0 | −1.00 | **+1.00** |
| **Total** | | **40** | — | **+1.00** | **34** | — | **−7.00** | **+8.00** |

**BI(j) = S(FRA) − S(USA) = +1.00 − (−7.00) = +8.00**

---

## The Null Hypothesis

The question the test asks is: **is a BI(j) of +8.00 surprising, or could it arise by chance?**

The null hypothesis is that J1 is unbiased. An unbiased judge has no systematic tendency to deviate above or below the panel median for any particular competitor. Her deviations are random noise around the consensus — sometimes positive, sometimes negative, sometimes zero — with no pattern tied to who she is scoring. Under the null hypothesis, those 18 deviation values could have been distributed between FRA and USA in any combination. Any random reassignment of the same 18 values to the two competitors is equally plausible.

---

## The Exact Test — How Many Ways Can 18 Values Split into Two Groups of 9?

The test pools all 18 deviations together:

> **Combined pool:** [+0.50, 0, 0, 0, 0, +0.50, 0, 0, 0, −1, −1, −1, −1, −1, 0, 0, −1, −1]

Under the null hypothesis, any assignment of these 18 values to the two competitors is equally plausible. The question is: out of all possible ways to split 18 values into two groups of 9, how many produce a simulated BI(j) as large as +8.00?

The number of distinct splits is given by the combination formula:

**C(18, 9) = 18! / (9! × 9!) = 48,620**

There are exactly 48,620 ways to choose which 9 of the 18 values go to the "A group" (FRA's slot) — the remaining 9 automatically form the "B group" (USA's slot). OSNR enumerates every one of these 48,620 splits exactly, with no random sampling and no dependence on a random seed.

Here is one example split — choosing positions {1, 3, 5, 7, 9, 10, 12, 14, 16} for the A group:

> **Pool (indexed):** [+0.50, 0, 0, 0, 0, +0.50, 0, 0, 0, −1, −1, −1, −1, −1, 0, 0, −1, −1]

- A group (positions 1,3,5,7,9,10,12,14,16): +0.50, 0, 0, 0, 0, −1, −1, −1, 0 → sum = **−2.50**
- B group (remaining 9): 0, 0, +0.50, 0, 0, −1, −1, −1, −1 → sum = **−3.50**
- Simulated BI(j) = −2.50 − (−3.50) = **+1.00**

This split produces +1.00 — not as extreme as +8.00, so it does not count against us.

---

## The p-Value

OSNR evaluates all 48,620 splits and counts how many produce a simulated BI(j) ≥ +8.00. The answer is exactly **36**.

**p = 36 / 48,620 = 0.000740**

This is an exact result — not an estimate. Every one of the 48,620 possible splits has been evaluated, so there is no sampling error.

This p-value is below the OSNR Tier 2 significance threshold of p ≤ 0.001. Combined with the LOJO finding that removing J1 changes the podium (USA overtakes FRA by 0.25 points under OSNR's adjusted scoring), this event is flagged as a Tier 2 result.
