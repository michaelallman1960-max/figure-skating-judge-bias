# Frequently Asked Questions
## Statistical Audit of Figure Skating Judging — OWG 2026 and Beyond

**Michael Allman | February 2026**

*This FAQ accompanies the op-ed "The Olympics Just Ended. For the First Time, We Can Check the Judges' Work." and the research paper currently under review at Scientific Reports. It will be updated as new questions arrive.*

**Have a question?**
- **General public and media:** judgingbias@gmail.com
- **Technical and statistical questions:** github.com/michaelallman1960-max/figure-skating-judge-bias/discussions

---

## Part 1: The Basics

**What did you actually find?**

At the 2026 Olympic ice dance final, one judge's scores were so different from the rest of the judging panel that the odds of it happening by chance were roughly 1 in 3,333. When that judge's scores are removed and the result is recalculated using the remaining eight judges — exactly as the ISU's own rules specify — the gold and silver medals switch.

This is the most extreme finding across four years of elite competition data: 17 major ISU competitions, 142 events, nearly 270,000 individual judge scores. It is not the only event where a single judge's removal would have changed the podium.

---

**Is figure skating corrupt?**

This research does not claim that. A statistically anomalous score is not the same as a corrupt one. Judges can diverge from a panel for many reasons — different aesthetic preferences, different national scoring cultures, honest disagreement about a performance, or genuine error. What the framework detects is a pattern that is statistically extreme *and* outcome-determinative. Whether the cause is bias, corruption, incompetence, or bad luck is a separate question that this method cannot answer. What it can answer is: did this judge's scores change who won, and how unlikely was that pattern under a fair scoring model?

---

**Are you saying the wrong skaters won?**

The framework identifies events where, under the leave-one-judge-out calculation, the result would have been different. Whether the "corrected" result is more or less accurate than the original is not something statistics can determine — judging is inherently subjective. What the framework can say is that the outcome was sensitive to one judge's scores in a way that met a pre-specified threshold for statistical extremity. That sensitivity is worth knowing about, regardless of who "deserved" to win.

---

**Are you naming the judges?**

No. ISU competition protocols identify judges only by position number (J1 through J9), not by name or nationality. This research uses the same anonymized data. The findings describe statistical patterns in scoring, not the conduct of named individuals.

---

**Why figure skating? Does this apply to other sports?**

Figure skating is unusual in that it publishes complete judge-by-judge scores for every element of every performance — a level of transparency that most judged sports do not provide. This makes a rigorous statistical audit possible in a way that is not yet feasible for, say, gymnastics or diving, where scoring data is less granular. The framework itself is general and could be applied to any judged sport that publishes comparable data.

---

## Part 2: The Method

**How does the test work, in plain language?**

Two questions are asked for each judge in each event:

1. **How unusual are this judge's scores?** Across all the skater pairs this judge evaluated, how often did this judge rank one skater above another when every other judge ranked them the opposite way? If that disagreement rate is high enough that it would occur by random chance less than 1 in 1,000 times, the judge is flagged as statistically anomalous.

2. **Do those unusual scores change the result?** The judge's scores are removed and the event result is recomputed using the remaining eight judges. If the podium changes — any top-3 finishing position shifts — the event is classified as outcome-determinative.

Both conditions must be met to trigger a flag. A judge who scores unusually but doesn't change the result is noted in the data but not flagged. A judge whose removal would change the result but whose scores are within normal statistical range is also not flagged.

---

**What does "1 in 3,333" mean exactly?**

It is the probability that a randomly assigned judge in a nine-judge panel of the same structure would produce pairwise disagreements as large as the ones observed, if all judges were scoring without systematic bias. The calculation uses a permutation test with 10,000 draws — rigorous and reproducible on any laptop.

The pre-specified flagging threshold is 1 in 1,000 (p ≤ 0.001). The OWG 2026 ice dance finding, at roughly 1 in 3,333 (p = 0.0003), is more than three times more extreme than the threshold required to trigger a flag.

---

**Why 1 in 1,000 as your threshold? Isn't that arbitrary?**

All statistical thresholds involve a judgment call about how to balance false positives (flagging a fair judge) against false negatives (missing a genuinely anomalous one). The 1-in-1,000 threshold is common in research contexts where consequences of a false positive are significant — it is stricter than the 1-in-20 (p ≤ 0.05) standard used in many social science studies. The threshold was set before analysis began, not chosen after seeing the data, which eliminates the risk of selecting a threshold to produce a desired result.

---

**You ran 1,710 statistical tests within a single event. At a 5% significance level, wouldn't you expect roughly 85 to come back positive just by chance? You observed 367 — more than 20%. Isn't that inflated? And isn't this a non-parametric test?**

The 5% expectation only holds if every one of those 1,710 tests has no effect — meaning the entire nine-judge panel scored with zero bias. The gap between 85 and 367 is not a methodological flaw; it is part of the finding. Bias is present in this panel, and a test that detected no excess would be underpowered, not rigorous.

Two things explain the 367.

*Real signal.* Most of the excess reflects genuine scoring patterns that are unlikely under a fair model. In the OWG 2026 ice dance final, every one of the nine judges produced raw significance rates well above 5% — ranging from 11% to 32% depending on the judge. That uniformity is itself a finding about the composition of this panel.

*Correlated tests.* Each judge appears in all 190 team-pair comparisons for an event. If a judge systematically favors one nationality, that tendency shows up across many of those 190 tests simultaneously — not as one independent finding, but as a cluster of correlated ones. A single real (judge, nationality) bias can generate 15 to 30 correlated significant p-values. The raw count of 367 overstates the number of independent effects.

On the non-parametric question: the permutation test gives exact type I error control under each individual null. P(p ≤ 0.05) is exactly 0.05 for a fair test, with no distributional assumptions required. The test does not inflate false positives. The excess above 85 is genuine signal, not a statistical artifact.

The Benjamini-Hochberg correction addresses this directly. It examines the full distribution of all 1,710 p-values and finds the largest subset where the expected proportion of false discoveries stays at or below 5%. For the OWG 2026 ice dance final, that yields 21 statistically reliable findings. The most extreme — the FRA versus USA comparison for judge J1 — has p = 0.0003 and survives the correction with substantial margin.

---

**How do you handle the fact that you're testing 142 events? Doesn't that increase the odds of finding something extreme somewhere?**

Yes, and this is a real concern (called the "multiple comparisons" problem). Two things address it:

First, the dual-criterion design — requiring both statistical extremity *and* outcome-determinativeness — substantially reduces false discoveries compared to a single p-value threshold alone.

Second, the OWG 2026 ice dance finding (p = 0.0003) is extreme enough to survive a full Bonferroni correction across all 142 events, which is the most conservative possible adjustment for multiple comparisons. Even holding the entire dataset to the standard of "this single finding must be significant on its own," it passes.

---

**You said about 81% of events have at least one statistically flagged judge. Doesn't that mean the sport is broken?**

This is an important question and deserves a careful answer.

A judge being flagged at BH q ≤ 0.05 means their scoring pattern for a particular pair of competitors was statistically unusual relative to that judge's own career baseline — not that they were cheating, biased, or wrong. Elite judging panels are small (nine people), scores are correlated within a panel, and genuine disagreement about difficult performances is common. Some rate of statistical divergence is expected even in a perfectly fair system.

What matters is the subset of flagged events that are also outcome-determinative: 7 of 142 events (5%) meet both criteria — statistically significant AND large enough to change the competitive result. Whether those 7 cases reflect systematic bias, a calibration issue in scoring culture, or honest outlier variation is a question the statistics alone cannot answer. What the statistics can say is that in those events, the result was sensitive to one judge in a way that meets a high bar for concern. That is worth examining, not ignoring.

---

**You say the ISU already has an Officials Assessment Commission. How is your framework different?**

The ISU's Officials Assessment Commission (OAC) reviews judging after competitions and can identify anomalous patterns, recommend education or sanctions, and report to the Technical Committee. That process serves an important function.

The difference is timing and consequence. The OAC process is post-hoc — it takes place after results are final and medals awarded. It leads to assessments of judges, not corrections of results. And it is not public: the ISU does not routinely publish OAC findings or outcomes.

The framework described here is designed to run before medals are awarded, produce a defined outcome (verify or adjust the result), and operate under pre-specified, transparent rules. It is a complement to the OAC process, not a replacement for it.

---

## Part 3: The Governance Proposal

**What exactly are you proposing the ISU do?**

Embed a two-test statistical audit in the scoring system that runs automatically after each segment, before results are announced. If no anomaly is flagged, the result is confirmed and announced as normal. If a flag is triggered — one judge meets both the statistical threshold and the outcome-determinativeness criterion — a technical delegate performs a brief data integrity check (confirming the computation applied the rules correctly) and the result is adjusted if the threshold is confirmed.

The threshold, the procedure, and any appeal mechanism would be established in advance by the ISU and applied consistently across all events. The public announcement would state whether the result was "verified" or "adjusted" — not which judge was flagged, which remains an internal matter.

---

**What stops someone from gaming this system — scoring strategically to trigger a flag against a competitor's judge?**

The threshold is conservative enough that strategic manipulation would require a judge to score so far outside the panel's range that they would be flagging themselves. The dual-criterion requirement means a judge cannot trigger a correction by being slightly unusual — they have to be extreme enough to meet the 1-in-1,000 statistical bar AND change the podium. A judge attempting to game the system by scoring extremely would be far more likely to flag themselves than to successfully manipulate the result.

---

**Should this apply to all ISU events, or just the Olympics?**

The framework has been validated on ISU Championship-level and Olympic events — the highest-stakes tier. Applying it to all ISU-sanctioned events is a reasonable extension but a separate governance decision with different operational implications. Starting at the top of the pyramid makes sense.

---

## Part 4: About This Research

**Who are you and why should I trust this?**

I am an independent researcher. I hold an MBA from the University of Chicago Booth School of Business. I have no institutional affiliation, no research funding, and no connection to any national skating federation, athlete, or ISU official.

The findings are fully reproducible. The complete dataset, code, and methodology are publicly available at github.com/michaelallman1960-max/figure-skating-judge-bias. Any statistician can download the data and code and verify every number in this research independently. A paper describing the methodology in full is currently under review at Scientific Reports (Nature Portfolio).

---

**What data did you use?**

Judge-by-judge protocol sheets published by the ISU on its official results website (isu.org) for 17 major ISU competitions between 2022 and 2026. These sheets record every judge's score for every element and program component score in every event. The data is public, structured, and has been available throughout this period. Nothing proprietary or non-public was used.

---

**The competitions are: (for fact-checkers)**

ISU European Championships (2022, 2023, 2024, 2025), ISU Four Continents Championships (2022, 2023, 2024, 2025), ISU Grand Prix Finals (2022/23 Turin, 2023/24 Beijing, 2024/25 Grenoble), ISU World Championships (2022, 2023, 2024, 2025), Olympic Winter Games 2022 (Beijing), Olympic Winter Games 2026 (Milano-Cortina). Note: No Grand Prix Final was held in the 2021/22 season due to COVID-19.

---

**How long did this take to build?**

The statistical framework and database were built in approximately one week, using modern AI tools as a force multiplier for implementation, verification, and scale. The methodology is mine. The speed reflects what is now possible for an independent researcher with the right tools — and underscores why governing bodies with far greater resources have no excuse for not having built something like this already.

---

*Last updated: February 2026*
*Questions: judgingbias@gmail.com | github.com/michaelallman1960-max/figure-skating-judge-bias/discussions*
