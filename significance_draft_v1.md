# Does Your Judge's Passport Affect Your Olympic Score?

**A statistical audit of figure skating reveals a troubling pattern — and a straightforward remedy**

*Michael Allman — February 2026*

*Draft v1 — prepared for submission to Significance Magazine*

---

On the evening of the Milano–Cortina 2026 Olympic Winter Games ice dance final, two teams separated by a fraction of a point competed for gold. Nine judges, their identities hidden from the public by rule, scored every element of every program. Their scores were averaged, a trimmed mean was computed, and a winner was declared.

What no one announced — because no one had checked — is that one of those nine judges scored in a pattern so far outside normal variation that it strains statistical credibility. The probability of observing a pattern that extreme by chance alone is approximately 1 in 3,333. And if you remove that judge from the panel and rerun the competition using the remaining eight scores, the gold and silver medals switch.

I know this because I built a system to find it.

---

## The Transparency Paradox

The International Skating Union's International Judging System (IJS), introduced after the judging scandal at the 2002 Salt Lake City Olympics, was designed to restore public trust. It succeeded in one important respect: it publishes everything. After every competition, the ISU releases the full scoring sheet — every score, from every judge, for every technical element and every program component, for every skater in every event.

This is remarkable transparency for a subjective sport. The data is publicly available and freely downloadable.

There is a catch. While the scores are public, the judges are anonymous. Each judge appears on the scoring sheet only as "J1," "J2," through "J9." The assignment of judge identities to panel positions is not disclosed. And under ISU Rule 123(5), no formal protest against a judge's evaluation is permitted.

The result is a peculiar governance gap: the data needed to detect anomalous judging is fully public, but the institutional machinery to act on it does not exist. The ISU publishes the evidence and prohibits the challenge.

---

## The Test

The question I set out to answer is deceptively simple: *can we tell, from the published scores alone, whether any judge is systematically scoring in a way that diverges from the rest of the panel — and if so, does it matter?*

The test I developed works like this. For any pair of competitors — say, Skater A and Skater B — each judge's scores can be summarised as a single number: how much higher or lower did this judge score Skater A relative to the panel average, compared to how they scored Skater B? A judge who is systematically high on Skater A and simultaneously low on Skater B will produce a large value of this statistic. The question is whether that value is larger than chance alone would produce.

To answer that question precisely, I use an exact combinatorial permutation test. Imagine taking all the scored units for this judge and scrambling them randomly between the two competitors, then recomputing the statistic. Do that for every possible scrambling — not a random sample, but every single one — and ask: how many of those scrambled arrangements produce a statistic as extreme as the one we actually observed?

If the answer is "very few," the judge's real pattern is genuinely unusual. The p-value is an exact fraction: the number of extreme arrangements divided by the total number of possible arrangements. No simulation, no random seed, no sampling error. A deterministic mathematical answer.

For a panel of nine judges with typical event sizes, the number of arrangements to check runs into the billions per event. Across 142 events, I computed approximately 265,000 individual pairwise comparisons, enumerating a total of roughly 191 billion score arrangements. Every one of them was checked exactly.

---

## What the Data Shows

The dataset covers 17 major ISU competitions from January 2022 through February 2026 — every Grand Prix Final, Four Continents Championship, European Championship, World Championship, and both the 2022 Beijing and 2026 Milano–Cortina Olympic Winter Games. It contains 2,706 individual competitor entries, 291,604 individual judge scores, and 264,854 pairwise judge-competitor comparisons across all four figure skating disciplines.

The findings are substantial. Across all events, 1,774 pairwise comparisons reach statistical significance at p ≤ 0.001 — meaning the observed pattern would occur by chance fewer than 1 in 1,000 times. In 46 events, at least one judge's removal under a leave-one-judge-out counterfactual would have changed the podium — a gold, silver, or bronze medal awarded to a different competitor.

The OWG 2026 ice dance final is the single most statistically extreme case in the entire dataset. The p-value of 0.0003 — roughly 1 in 3,333 — is not a close call. Across both the Rhythm Dance and Free Dance segments combined, the flagged judge was the single most extreme scorer for one competitor on nearly 70% of all scored units, consistently in the direction that favoured that competitor over another. Under the leave-one-judge-out counterfactual, removing this judge and recomputing the trimmed mean reverses the gold and silver medal positions.

To be clear: this analysis does not prove intent. It does not identify the judge by name or nationality. It demonstrates that a pattern exists which is statistically inconsistent with random variation, and that the pattern is outcome-determinative at the highest level of the sport.

---

## A Proposed Remedy: The OSNR

The audit framework I developed — the Outlier Score Nullification Rule, or OSNR — translates statistical findings into a pre-specified, mechanical governance rule. It operates in two tiers.

**Tier 1** (p ≤ 0.01): The judge's pattern is flagged for review. The published competition result is unchanged, but the anomaly is recorded and reported to the relevant federation. This corresponds to a 1-in-100 threshold — unusual, but not yet conclusive enough to alter an outcome.

**Tier 2** (p ≤ 0.001, and outcome-determinative): The judge's scores are automatically nullified and the competition result is recomputed using the remaining panel. This applies only when two conditions are simultaneously met: the statistical anomaly is extreme, and it actually changes who wins a medal. Both gates must be passed.

The OSNR is deliberately conservative. A judge whose scores are statistically anomalous but whose presence or absence does not change the podium is flagged but not nullified. The rule is not about punishing unusual judgment — it is about protecting competitive integrity when an anomaly is both statistically compelling and result-changing.

The rule can be applied in real time from publicly available data. No private information is required. No institutional discretion is involved. The computation is fully automated and reproducible by any independent party.

---

## One Researcher, Open Data, Public Code

I am an independent researcher — not affiliated with any university, not funded by any grant, not a professional statistician. I hold an MBA from the University of Chicago Booth School of Business. I built this framework in a week, using modern AI tools as a force multiplier to handle implementation, verification, and scale that would otherwise require a research team.

I want to be transparent about what that means. The statistical framework is mine. The methodology is mine. The findings are reproducible by anyone — and I invite that scrutiny. What AI tools enabled me to do is work at a level of rigor and scale that would previously have required an academic research group or a professional consultancy. The analysis can be replicated start-to-finish from the publicly available ISU scoring sheets and the open-source codebase I have published on GitHub.

The full database — 291,604 individual judge scores, all computed statistics, all LOJO counterfactuals — is publicly available. The code is MIT-licensed. The paper presenting the full methodology and results is forthcoming in *Scientific Reports*.

I raise the independent researcher context not as a disclaimer but as a point. If a single person with no institutional resources can build a real-time audit system for Olympic judging from publicly available data in a week, the question worth asking is why no one with considerably more resources has done so already.

---

## What Comes Next

The ISU is not obligated to adopt the OSNR. Governance reform in international sport is slow, politically complicated, and often resisted by the very bodies that would need to implement it.

But the data is public. The method is open. The findings are reproducible. And the 2026 Olympic ice dance result — as it currently stands — includes a judge whose scoring pattern places it in the most statistically extreme 0.005% of all judge-pair comparisons I examined across four years of elite competition.

The test asks one question: if you removed this judge from the panel and reran the competition, does the winner change?

For the OWG 2026 ice dance final, the answer is yes.

---

*The full paper, database, and analysis code are available at:*
*github.com/michaelallman1960-max/figure-skating-judge-bias*

*A full-length paper, "Detecting and Remedying Anomalous Judging in Competitive Figure Skating: A Permutation-Based Audit Framework," is forthcoming in Scientific Reports.*

---

**Word count:** ~1,480 words

**Author note:** AI tools (Claude, Anthropic) were used as research and implementation assistants throughout this project. All statistical methodology, analytical decisions, and findings are the author's own. The analysis is fully reproducible from publicly available data using the open-source code repository cited above.
