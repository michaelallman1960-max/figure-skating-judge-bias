# Methodology Diagnosis — The Exchangeability Problem

## The Problem

When we run the B(j) permutation test across all 5,184 judge-pair tests (144 events × 36 pairs per event), we find:

- **Expected false positives at p ≤ 0.001 in a fair system:** ~5 (by definition of a p-value)
- **Actual results at p ≤ 0.001:** ~1,775
- **Average p-value observed:** 0.248 (expected: ~0.500 under a true null hypothesis)
- **P-value distribution:** Heavily skewed toward zero — nearly 40% of all tests fall below p = 0.2

This is approximately **355 times more significant results than a fair system would produce by chance**. The bias cannot be that strong across the board. Something is structurally wrong with the test.

---

## The Diagnosis — Plain English

The permutation test has a fundamental structural flaw called the **exchangeability violation**.

The test asks: *"If we randomly swapped judge A's and judge B's scores, how often would we see disagreements this extreme?"*

But that is the wrong question. Judge A and Judge B both watched the same skaters. Their scores are **correlated by the shared performance signal** — the fact that skater X is genuinely better than skater Y, and both judges can see it. When you randomly swap their scores in the permutation, you destroy that correlation and create a null distribution that is far too narrow — too "tidy." So when reality shows any deviation at all from perfect agreement, the test screams "significant!" even though the deviation is completely normal.

This is a documented failure mode in statistics. The genetics literature calls it **"naive permutation with shared nuisance factors."**

**The thermometer analogy:** Imagine testing whether two thermometers agree by randomly swapping their readings between rooms. Of course they would look "inconsistent" — because you destroyed the temperature signal that explains why they read what they read. The rooms are genuinely different temperatures. Swapping readings does not create a valid null; it destroys the signal that both instruments are tracking.

In figure skating, the "room temperature" is the skater's true underlying performance level. Both judges are measuring the same thing. Randomly swapping their scores between skaters destroys this signal, making the null distribution unrealistically narrow, which makes almost any real judge-to-judge difference look statistically extreme.

---

## The Good News

**The LOJO concept is sound.** The leave-one-judge-out counterfactual — remove a judge, recompute the result, see if the podium changes — is well-grounded in the statistics literature (Frandsen 2019 formalizes exactly this kind of approach). The *concept* of the Tier 2 flag is right. The problem is only in the p-value gate that feeds into it.

**The conceptual model is also correct.** The framework described — true underlying performance, judges as unbiased estimators with error, panel consensus as the best estimate of truth — is precisely the framework used in the best academic literature (Gordon & Truchon 2008; the Many-Facets Rasch Model). The right model was arrived at intuitively.

---

## Three Fix Options — From Simple to Gold Standard

### Option 1 — Residual Deviation (Simplest, Fastest)

Instead of permuting judge labels, compute each judge's deviation from the **panel trimmed mean** for each element:

```
deviation(judge_j, element_k) = judge_j_GOE(k) − trimmed_panel_mean(k)
```

Then test whether judge J's distribution of deviations across all elements has a mean significantly different from zero. This removes the shared skater quality signal first. The null hypothesis becomes clean: *"unbiased judges deviate around zero."*

This is what **Emerson, Seltzer & Lin (2009)** — the definitive methodological paper on judging bias — use, and what SkatingScores.com implements operationally.

### Option 2 — Friedman Test (Statistically Rigorous, Non-Parametric)

Treat each event as a **two-way block design**: skaters are blocks, judges are treatments. The Friedman test — non-parametric two-way ANOVA by ranks — tests whether judge effects exist after controlling for skater quality. Post-hoc Nemenyi tests identify which specific judge is the outlier.

This is the correct non-parametric framework for exactly this data structure. Its null hypothesis is precisely what we want: *"All judge score distributions are equivalent after controlling for skater quality."* This completely sidesteps the exchangeability problem.

### Option 3 — Many-Facets Rasch Model (Gold Standard)

Simultaneously estimate true skater ability, judge severity, and element difficulty on a common logit scale. Flag judges whose **fit statistics** (infit/outfit mean-squares) are outside the expected range for a model-consistent rater.

This is the most defensible approach for a peer-reviewed paper. It formalizes the conceptual model mathematically: each judge's score is an observation of the true latent performance level, modulated by the judge's known severity and Rasch-distributed noise. Software: R's `mirt` package or Linacre's FACETS.

---

## What This Means for the Paper

1. **The 1,775 number needs to come down** — substantially. Under a properly specified test the count of genuinely anomalous judge-pairs will be much smaller.

2. **The OWG 2026 ice dance finding may still hold.** A finding at p ≈ 4.6 × 10⁻⁵ on the current (inflated) test is likely to remain significant even after correcting for the inflation — but this must be verified with the corrected method.

3. **The LOJO methodology is defensible.** The outcome-determinativeness piece is sound. The problem is purely in how we identify which judges to subject to LOJO.

4. **There is a rich academic literature on exactly this problem** — Zitzewitz (2006, 2014), Emerson et al. (2009), Dumoulin & Mercier (2020) — and the paper needs to situate itself within that literature.

---

## Key Citations

- Emerson, Seltzer & Lin (2009). "Assessing Judging Bias: An Example From the 2000 Olympic Games." *The American Statistician* 63(2), 124–131. https://www.researchgate.net/publication/227368961
- Zitzewitz, E. (2006). "Nationalism in Winter Sports Judging and its Lessons for Organizational Decision Making." *Journal of Economics & Management Strategy*. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=319801
- Zitzewitz, E. (2014). "Does Transparency Reduce Favoritism and Corruption? Evidence from the Reform of Figure Skating Judging." https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1980582
- Gordon, S. & Truchon, M. (2008). "Social choice, optimal inference and figure skating." *Social Choice and Welfare*. https://link.springer.com/article/10.1007/s00355-007-0243-2
- Dumoulin & Mercier (2020). "Accuracy and National Bias of Figure Skating Judges." MIT Sloan Sports Analytics Conference. https://www.sloansportsconference.com/research-papers/accuracy-and-national-bias-of-figure-skating-judges-the-good-the-bad-and-the-ugly
- Frandsen, B. (2019). "Judging Judge Fixed Effects." NBER Working Paper 25528. https://www.nber.org/system/files/working_papers/w25528/w25528.pdf
- Kimmel et al. (2008). "Naive Application of Permutation Testing Leads to Inflated Type I Error Rates." *Genetics*. https://pmc.ncbi.nlm.nih.gov/articles/PMC2206111/
- Findlay & Ste-Marie (2004). "A Reputation Bias in Figure Skating Judging." *Psychological Science*. https://psycnet.apa.org/record/2004-12032-009
