# Glossary of Terms
## Figure Skating Judging Bias Analysis

**Prepared by:** Michael Allman
**Last verified:** 2026-02-26

---

## Part I — Figure Skating Terms

**Base Value (BV)**
A fixed point value assigned by the ISU to each technical element, reflecting its difficulty. Base values are updated periodically. A quadruple jump has a higher base value than a triple of the same type. The base value is the starting point for calculating an element's score before GOE is applied.

**Bonferroni Correction**
A statistical adjustment applied when conducting multiple hypothesis tests simultaneously. The significance threshold is divided by the number of tests performed to control the family-wise error rate — i.e., to limit the probability of finding even one false positive by chance across many tests. In the pairwise analysis, the threshold is p < 0.001 divided by the number of competitor pairs in the event.

**Composition**
One of the three program components scored under the post-2022/23 IJS rules. Reflects the choreographic and structural quality of the program, including the use of space, pattern, and relationship to the music.

**Credit for Highlight Distribution (x)**
A marker applied to elements performed in the second half of a free skating or free dance program. The base value of the element is multiplied by 1.10 (a 10% bonus) to reward the additional difficulty of performing demanding elements later in the program when fatigue is greater.

**Deductions**
Point penalties subtracted from the Total Segment Score for rule violations. The most common is –1.00 point per fall. Other deductions may apply for time violations, costume failures, music with lyrics (where prohibited), or illegal elements.

**Downgraded Jump (<<)**
A technical call applied when a jump is under-rotated by half a revolution or more. The element is reassigned to the next lower jump (e.g., a quadruple becomes a triple), significantly reducing the base value.

**Element Score**
The score awarded for a single technical element. Calculated as:
> Element Score = Base Value + Panel GOE

**Factor**
A multiplier applied to each Program Component Score average before it is added to the PCS total. Factors vary by discipline, segment, and era. Higher factors give PCS greater weight in the total score for longer, more demanding programs.

**Fall (F)**
A technical call marker indicating the skater fell during or immediately after an element. A fall results in a –1.00 point deduction from the Total Segment Score and typically produces negative GOE scores from the judges.

**Free Dance (FD)**
The second and longer segment of an Ice Dance competition, equivalent to the Free Skating segment in singles and pairs. Teams have greater creative freedom in choreography and music choice.

**Free Skating (FS)**
The second and longer competitive segment for Men's Singles, Women's Singles, and Pair Skating. Men skate for approximately 4 minutes 30 seconds, women and pairs for approximately 4 minutes.

**GOE — Grade of Execution**
An integer score from –5 to +5 awarded by each judge for every technical element, reflecting the quality of its execution relative to the base difficulty. A GOE of 0 indicates neutral execution; positive scores reflect good execution; negative scores reflect errors.

**IJS — International Judging System**
The scoring system introduced by the ISU in 2004 following the judging scandal at the 2002 Salt Lake City Winter Olympics. Replaced the previous 6.0 system. Uses a cumulative points-based approach with separate technical and component scores, a panel of anonymous judges, and a trimmed mean to reduce the influence of outlying scores.

**Interpretation of the Music**
One of the five program components scored under the pre-2022/23 IJS rules. Reflects the accuracy with which the skater's movements reflect the music's rhythm, character, nuance, and style.

**ISU — International Skating Union**
The international governing body for competitive figure skating, speed skating, and short track speed skating. Headquartered in Lausanne, Switzerland. Responsible for setting the rules, technical requirements, and scoring system for all international figure skating competitions.

**Not Clear Edge (!)**
A technical call marker indicating that a jump was taken off on an incorrect or unclear edge, but not clearly enough to warrant the more severe wrong-edge call. Does not reduce the base value but typically results in negative GOE from judges.

**Panel GOE**
The trimmed mean of the nine individual judge GOE scores for a single element — the highest and lowest scores are discarded and the remaining seven are averaged. This is the GOE value that appears on the official scoring sheet and is used in calculating the element score.

**PCS — Program Component Score**
A score reflecting the overall quality of skating beyond individual technical elements. Judges award a mark from 0.25 to 10.00 in quarter-point increments for each program component. The panel average (trimmed mean) is multiplied by a factor and summed across components to produce the PCS total.

**Performance**
One of the five program components under the pre-2022/23 IJS rules. Reflects the physical, emotional, and intellectual involvement of the skater in conveying the intent of the music and program.

**Permutation Test**
A non-parametric statistical test used to assess the significance of an observed statistic. In a standard permutation test, the observed data are randomly rearranged many times to build an empirical null distribution. In this analysis, an **exact** permutation test is used instead: rather than random sampling, every possible split of the combined deviation pool is enumerated completely. For a 9-element program, there are C(18, 9) = 48,620 distinct ways to split 18 deviation values into two groups of 9. The exact p-value is the fraction of these 48,620 splits that produce a simulated BI(j) as extreme as or more extreme than the one observed — for example, 36/48,620 = 0.000740. Because all splits are evaluated, the result is fully deterministic with no random seed and no sampling error.

**Presentation**
One of the three program components scored under the post-2022/23 IJS rules. Reflects the overall performance quality — physical and emotional expression, projection, and connection to the music and audience.

**Rhythm Dance (RD)**
The first and shorter segment of an Ice Dance competition, equivalent to the Short Program in singles and pairs. Each season the ISU specifies required rhythms and patterns that all teams must incorporate.

**Short Program (SP)**
The first and shorter competitive segment for Men's Singles, Women's Singles, and Pair Skating. Each discipline has required elements that must be performed.

**Skating Skills**
A program component scored in all disciplines under both the pre- and post-2022/23 rules. Reflects the technical quality of skating — cleanness and sureness of edges, turns, steps, balance, and ice coverage.

**Technical Panel**
A separate panel from the judging panel, responsible for identifying and calling technical elements — determining what element was attempted, whether it was executed cleanly, and applying technical call markers (<, <<, q, !, e, F, x, *). The Technical Panel's calls affect base values but not GOE scores, which remain the judges' domain.

**TES — Total Element Score**
The sum of all individual element scores for a segment. Each element score equals its base value plus the panel GOE.

**Transitions**
One of the five program components under the pre-2022/23 IJS rules. Reflects the variety, difficulty, and quality of connecting movements, steps, and positions used between required elements.

**Trimmed Mean**
The averaging method used by the IJS to reduce the influence of outlying scores. For a panel of nine judges, the highest and lowest scores are discarded and the remaining seven are averaged. For eight judges, the highest and lowest are discarded and the remaining six are averaged. Applied separately to GOE scores for each element and to marks for each program component.

**TSS — Total Segment Score**
The overall score for one segment of competition. Calculated as:
> TSS = TES + PCS − Deductions

The TSS from both segments (Short Program + Free Skating, or Rhythm Dance + Free Dance) are summed to determine the final competition result.

**Under-Rotated Jump (<)**
A technical call applied when a jump is under-rotated by a quarter to half a revolution. The base value is reduced (typically by approximately 30%).

**Wrong Edge (e)**
A technical call indicating that a jump was clearly taken off on the wrong edge (e.g., a Flip jumped from an outside rather than inside edge). Reduces the base value and typically produces negative GOE.

---

## Part II — Statistical and Analytical Terms

**B(j) — Bias Statistic**
The core statistic used in this analysis to measure a judge's directional bias when scoring two competitors. For judge j comparing competitor A to competitor B:
> B(j) = mean GOE deviation of j for A's elements − mean GOE deviation of j for B's elements

where each judge's GOE deviation for an element is that judge's score minus the panel average for that element. A positive B(j) means judge j scored A higher relative to the panel than they scored B.

**Exchangeability**
The statistical assumption underlying the permutation test used in this analysis. Under the null hypothesis of no bias, a judge's GOE scores are assumed to be exchangeable across competitors within an event — i.e., randomly re-assigning which scores belong to which competitor should produce statistics no more extreme than those observed. Violations of this assumption (e.g., if element difficulty differs systematically between competitors) are addressed by using within-element deviations rather than raw scores.

**False Positive Rate**
The probability that a judge is flagged as biased when in fact no bias exists. Controlled by the choice of significance threshold and the Bonferroni correction.

**LOJO — Leave-One-Judge-Out**
A counterfactual analysis in which one judge's scores are removed from the calculation and the event result is recomputed without them. Used to assess whether any single judge's scores were outcome-determinative — i.e., whether removing them would have changed the competition result.

**Null Distribution**
The distribution of a test statistic under the assumption that there is no effect (no bias). In this analysis, the null distribution of B(j) is built empirically through permutation.

**Operating Characteristics**
The statistical properties of a test procedure across many applications — including the false positive rate (Type I error), the power to detect true bias (Type II error), and how these vary with sample size (number of elements) and effect size.

**OSNR — Outlier Score Nullification Rule**
The two-tier policy remedy proposed in this analysis:
- **Tier 1 (Flag):** A judge whose B(j) statistic is significant at p < 0.01 is flagged for review.
- **Tier 2 (Nullify):** A judge whose B(j) is significant at p < 0.001 AND whose scores are outcome-determinative (their removal changes the result) has their scores replaced by the panel average, and the result is recalculated.

**p-value**
The probability of observing a test statistic as extreme as or more extreme than the one observed, under the null hypothesis of no bias. A small p-value indicates that the observed statistic is unlikely to have arisen by chance.

**Pairwise Analysis**
An extension of the B(j) statistic to all possible pairs of competitors within an event, rather than only the gold–silver boundary. For an event with n competitors, there are C(n, 2) = n(n−1)/2 pairwise comparisons. Each is tested separately for each judge, with Bonferroni correction applied across all pairs.

**Within-Unit Permutation**
The specific permutation method used in this analysis. Rather than shuffling scores across elements (which would ignore element difficulty), the judge labels are shuffled within each element independently. This preserves the structure of the data — the difficulty of each element, the number of elements per competitor — while randomizing which judge's score is attributed to which position.

**Z-Score**
A standardized measure of how many standard deviations an observed statistic lies from the mean of the null distribution. Used here to summarize how extreme a judge's B(j) statistic is relative to what would be expected by chance.

---

## Part III — Database Terms

**`competitions`**
Database table. One row per competition event (e.g., ISU World Figure Skating Championships 2025). Stores the competition name, season year, and venue.

**`element_judge_scores`**
Database table. One row per judge per element per entry. The primary data table for bias analysis. Stores the individual GOE integer (–5 to +5) awarded by each judge for each executed element. Contains 200,715 rows.

**`elements`**
Database table. One row per executed technical element. Stores the element code, base value, panel GOE (trimmed mean), and panel element score. Contains 22,380 rows.

**`entries`**
Database table. One row per skater or pair performance in a given event segment. Stores team name, nationality, start number, rank, TES, PCS, deductions, and TSS. Contains 2,637 rows.

**`events`**
Database table. One row per discipline × segment combination within a competition (e.g., WC2025 Women's Short Program). Stores discipline name, segment name, and links to the competition. Contains 141 rows.

**`judge_entry_totals`**
Database table. Per-judge per-entry aggregated GOE and PCS totals, used as inputs to the pairwise analysis.

**`judge_event_statistics`**
Database table. Summary bias statistics per judge per event, including bias z-score and element count, computed by the statistics calculation script. Contains 1,269 rows.

**`judges`**
Database table. One row per judge position (J1–J9) per event. Stores judge position label, name (where available from the scoring sheet), and country code. Contains 1,278 rows.

**`pairwise_judge_statistics`**
Database table. The core output of the bias analysis. One row per judge × pair of competitors per event. Stores the BI(j) statistic, exact combinatorial p-value, z-score, mean deviations for each competitor, significance flags at p ≤ 0.01, p ≤ 0.001, and Bonferroni-corrected thresholds, plus `extreme_count` (the raw numerator, e.g. 36) and `num_permutations` (the exact denominator C(2k,k), e.g. 48,620).

**`pcs_components`**
Database table. One row per program component per entry. Stores the component name, the factor applied, and the panel average mark (trimmed mean of nine judge marks). Contains 7,396 rows.

**`pcs_judge_scores`**
Database table. One row per judge per program component per entry. Stores the individual mark (0.25–10.00) awarded by each judge. Contains 66,794 rows.

**Element Code**
A standardized abbreviation identifying the type and level of a technical element. Examples: `4Lz` = quadruple Lutz jump; `3F+3T` = triple Flip combined with triple Toe Loop; `CCoSp4` = Change Combination Spin level 4; `StSq3` = Step Sequence level 3; `3Tw4` = throw triple jump (pairs) level 4.

**Event-Local Analysis**
A design decision in this analysis: all statistical tests are computed within a single event's judging panel. No cross-competition judge identity linking is performed. Judges are identified by position (J1–J9) within each event rather than by name across events.

**TES Reconstruction Check**
A data integrity verification procedure. For every entry in the database, the sum of all individual element panel scores was compared against the stored TES value. A 100% pass rate (zero discrepancies across 2,005 non-Ice Dance entries) confirms that all elements were correctly parsed and stored.
