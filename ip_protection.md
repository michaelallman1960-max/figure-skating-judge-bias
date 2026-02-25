# Intellectual Property Protection Guide
## For a Figure Skating Judging Bias Researcher

**Prepared for:** Michael Allman, Independent Researcher
**Project:** "Detecting and Remedying Anomalous Judging in Competitive Figure Skating: A Permutation-Based Audit Framework"
**Date:** 2026-02-21
**Disclaimer:** This guide is for informational purposes only and does not constitute legal advice. For decisions with material consequences — especially around enforcement, commercialization, or responding to legal threats — consult a licensed intellectual property attorney.

> **Methodology note (updated 2026-02-24):** The published method is now called **ISU-impact** (style-adjusted quantile permutation null, M=10,000). The original B(j) pairwise permutation test (referred to as "OSNR" in early drafts) has been retired due to an exchangeability violation. References to "OSNR" in the trademark analysis section (Section 4) remain accurate for IP purposes — they describe the name you previously used and may still wish to protect.

---

## ⚠️ Defamation Language — Standing Reminder

*Repeat this before every publication, interview, or public statement:*

| ✅ SAY THIS | ❌ NEVER SAY THIS |
|------------|-----------------|
| "statistically anomalous scoring pattern" | "biased" |
| "statistically extreme" | "corrupt" |
| "outlier relative to the panel" | "cheating" |
| "the data is inconsistent with random variation" | "intentional" |
| "removing this judge changes the result" | "this judge handed the medal to X" |
| "the framework flags this event" | "this judge should be sanctioned" |

**The rule:** Describe what the statistics show. Never assert what they cannot prove — which is intent.

---

## Table of Contents

1. [What You Own — Plain Language Analysis](#1-what-you-own)
2. [Copyright — Practical Guide](#2-copyright)
3. [The MIT License on the Code — Is It Right?](#3-the-mit-license)
4. [The OSNR Framework — Protecting the Name and Concept](#4-the-osnr-framework)
5. [Open Access and Your Rights at Scientific Reports](#5-open-access-and-scientific-reports)
6. [The Database — Specific Considerations](#6-the-database)
7. [Risk Areas](#7-risk-areas)
8. [Recommended Actions — Prioritized](#8-recommended-actions)
9. [The "AI-Assisted" Question](#9-the-ai-assisted-question)

---

## 1. What You Own

Here is a plain-language accounting of your IP position across each deliverable.

### The Paper Text — You Own It, Fully

The academic paper — its prose, framing, arguments, figures, tables, and structure — is your original creative work. Copyright attached automatically the moment you wrote it. No registration, no notice, no filing required. Under US law (17 U.S.C. § 102), original works of authorship are protected from the moment of creation and fixed in a tangible medium.

What this means practically: you can publish it, reproduce it, post it to your website, post it to SSRN, cite it, and quote from it — until and unless you sign those rights away to a journal. See Section 5 for why Scientific Reports is favorable on this point.

### The Software Code — You Own It, MIT Licensed

Your Python codebase is protected by copyright the same way the paper is. You own the source code. The MIT license you have applied to it is a grant of permission to others — it does not transfer ownership to anyone. You remain the copyright holder. The MIT license simply tells the world what they are allowed to do with your code without asking you.

This is the correct distinction: **ownership** (you keep it forever) versus **license** (a set of permissions you grant to others).

### The Database as a Compiled Work — You Own the Structure, Not the Scores

This is the most nuanced area. US copyright law (Feist Publications v. Rural Telephone Service, 499 US 340, 1991) establishes a clear rule: **facts are not copyrightable**. The ISU scores themselves — the raw numbers judges assigned to skaters — are facts. You cannot own them.

What you *do* own:

- **The selection** of which competitions, events, and score categories to include
- **The schema** — the structure of your SQLite database, the table design, the field names, the relationships
- **The computed fields** — BI(j) bias indices, p-values, LOJO counterfactuals, pairwise statistics, tier classifications, and every other derived value you calculated
- **The creative arrangement** — how you organized 291,604 individual judge scores into a coherent analytical structure

US copyright law protects compilations if the selection and arrangement reflect originality. Feist requires only a "modicum of creativity." Your schema and computed fields clear that bar comfortably. The computed statistics (p-values, LOJO results, OSNR tier flags) are particularly strong because they result from your analytical choices, not from the ISU's data.

### The OSNR Framework as a Concept — This Is Where IP Gets Complicated

The short answer: **ideas and methods are not copyrightable**. Copyright protects expression, not the underlying concept. You cannot copyright "a two-tier audit framework using permutation testing and leave-one-judge-out counterfactuals."

What you can protect:

- The specific **written description** of the framework (copyright on the paper)
- The **name** "OSNR" or "Outlier Score Nullification Rule" — potentially via trademark, but read Section 4 carefully before pursuing this
- **Priority** — the fact that you published first and can prove it (see Section 4)

What you cannot protect: the general idea that one could use statistical outlier detection to audit judging. Once published, others can implement OSNR-style frameworks without your permission. This is how academic publication works — you get credit and priority, not a monopoly on the method.

### The Underlying ISU Scoring Data — You Do Not Own This

To be completely clear: the individual scores assigned by judges at ISU competitions are facts published by the ISU. You do not own them, and you cannot restrict others from accessing or using them. The ISU publishes this data publicly on its website as part of official competition protocols. Collecting, downloading, and analyzing public facts is legal research, not misappropriation.

The ISU might disagree with how their data is characterized in your findings, but that is a different question (see Section 7 on defamation risk).

### Computed Fields and Derived Statistics — Strong, but Not Bulletproof

Your derived values (BI(j) scores, p-values, LOJO counterfactuals, tier flags) occupy favorable territory. They result from your methodological choices, your code, your analytical decisions. A court would most likely find these protectable as original expression. However, there is a genuine legal debate about whether purely computational outputs — numbers produced by an algorithm applied to facts — are original enough for copyright. The stronger your argument, the more the output reflects creative methodological judgment rather than mechanical calculation.

Practical advice: do not lose sleep over this. The risk that anyone will reproduce your derived statistics without attribution is low. The risk that you could not defend against such reproduction is even lower given the totality of your compilation.

---

## 2. Copyright — Practical Guide

### How Copyright Attaches Automatically

Under the Copyright Act of 1976 (as amended), copyright protection begins automatically when an original work is created and fixed in a tangible medium. For your paper, this means the moment you save a draft. For your code, the moment you commit it. No registration, no copyright notice, no filing with any government agency is required for protection to exist.

A copyright notice (© 2026 Michael Allman) is good practice but not legally required since the US joined the Berne Convention in 1989. Still, include it — it defeats any "innocent infringer" defense if someone later claims they did not know the work was protected.

### When to Register with the US Copyright Office — And Why It Matters

Registration is optional, but it matters for enforcement. Here is what registration buys you:

**Before infringement occurs:** If you register before someone infringes, you can sue for statutory damages (up to $150,000 per willful infringement) and attorney's fees, without having to prove actual financial harm. This is significant. Proving actual damages from someone reproducing an academic paper is difficult.

**After infringement occurs:** You can still register, but you can only recover actual damages (typically minimal for academic works) and cannot recover attorney's fees.

**The practical calculus:** For an academic paper submitted to Scientific Reports, registration is unlikely to matter much. The journal's CC BY 4.0 license means anyone can reuse with attribution anyway. The main scenario where registration would matter is if someone reproduced your work commercially without attribution — possible, but not the primary risk here.

**What to register:** If you decide to register, register the paper and the database as separate works. Code can also be registered (the Copyright Office accepts deposits of source code). Filing fee is currently $65 per work for online registration at copyright.gov.

**Timing recommendation:** If you want registration, do it before submission to Scientific Reports, while you still have full flexibility over the work. You can register unpublished works.

### What Happens to Your Copyright When a Journal Publishes Your Paper — CRITICAL

This is one of the most important things to understand about academic publishing, and most researchers do not know it until it is too late.

**Traditional journal model (Elsevier, Springer, many others):** When you submit and your paper is accepted, you typically sign a Copyright Transfer Agreement (CTA). You give the journal all of your copyright. After signing, you no longer own your paper. You may not legally post it to your own website, post it to arXiv, distribute copies to colleagues, or reuse figures from it in your next paper — without the journal's permission, which they may grant or deny.

This is not hypothetical. Authors have received takedown notices from Elsevier for posting their own papers on ResearchGate.

**Scientific Reports / Nature Portfolio model:** Scientific Reports publishes under Creative Commons Attribution 4.0 International (CC BY 4.0). Under this model:
- **You retain full copyright.** You are always identified as the copyright holder.
- Scientific Reports receives a license to publish, but you do not surrender ownership.
- You can post the final published version anywhere, immediately, with no embargo.
- Others can reproduce, adapt, and build on your work — but must attribute you.

This is a materially better arrangement for an independent researcher. You get the journal's brand and peer review credibility without giving up any rights.

**Verify before you sign:** Always read the actual publication agreement. Journal policies can change. Confirm that Scientific Reports' current agreement matches the CC BY 4.0 policy before you sign anything.

### How to Assert Copyright

On the paper: Include on the first page or in a footer:
```
© 2026 Michael Allman. Published under CC BY 4.0.
```

On the database: Include a LICENSE file or README notice:
```
Database © 2026 Michael Allman.
Licensed under Creative Commons Attribution 4.0 International (CC BY 4.0).
Underlying ISU competition scores are facts in the public domain.
Compiled data, schema, and derived statistics are original works of the author.
```

On the code: The MIT license file in your repository already handles this. Make sure the year and your name are correct in the LICENSE file.

### Creative Commons License Options — Which One for the Database?

Creative Commons licenses are designed for creative works and compilations, not code. Here is a brief comparison for your database:

| License | Others Can Reuse? | Must Attribute You? | Can Use Commercially? | Must Share-Alike? |
|---------|-------------------|---------------------|----------------------|-------------------|
| CC BY 4.0 | Yes | Yes | Yes | No |
| CC BY-SA 4.0 | Yes | Yes | Yes | Yes — derivatives must use same license |
| CC BY-NC 4.0 | Yes | Yes | No | No |
| CC0 (public domain dedication) | Yes | No requirement | Yes | No |

**Recommendation: CC BY 4.0 for your database.**

Reasons:
- Attribution is required, which protects your credit and establishes the citation record
- It is the most permissive option that still protects attribution
- It is consistent with the CC BY 4.0 license Scientific Reports uses for the paper — same license family, consistent message
- It is the norm for open research data and is what data repositories (Zenodo, Figshare, Dryad) recommend
- CC BY-NC would restrict commercial use, but would also make it harder for other researchers to use your data freely — unnecessarily restrictive for your goals
- CC BY-SA (share-alike) creates complications for derivatives — not worth the complexity

---

## 3. The MIT License on the Code — Is It Right?

### What the MIT License Grants Others

The MIT license is one of the most permissive open-source licenses. It grants anyone the right to:
- Use your code for any purpose, including commercial use
- Copy and distribute it
- Modify it
- Sublicense it (incorporate it into differently-licensed projects)
- Sell software that includes it

The only condition: they must include your copyright notice and the MIT license text in any distribution.

### What You Retain Under the MIT License

You retain copyright. You remain the author. But you grant an irrevocable license to anyone to do almost anything with the code. "Irrevocable" means you cannot later decide MIT was a mistake and demand the code back.

### Whether MIT Is the Right Choice

For your purposes, MIT is defensible and probably correct. Here is the comparison:

**MIT vs. GPL:**
GPL (GNU General Public License) requires that derivative works also be released under GPL — the "copyleft" or "viral" condition. This prevents anyone from incorporating your code into a proprietary product. If you want to ensure your work remains open forever, GPL is stronger. If you want maximum adoption (including by commercial sports analytics firms who might use your audit framework), MIT wins.

For an academic researcher whose primary goal is citation, adoption, and influence, MIT typically generates more usage than GPL, because commercial developers can use it freely.

**MIT vs. Apache 2.0:**
Apache 2.0 is similar to MIT but adds explicit patent rights (the license grants a patent license from contributors). It also includes an explicit patent termination clause — if a user sues you for patent infringement, they lose their Apache license. This is more protective in a patent-litigation context. For a figure skating research tool, patent litigation risk is negligible. MIT is simpler and equally appropriate.

**MIT vs. CC BY 4.0 (for code):**
Creative Commons licenses are not recommended for software. CC BY 4.0 is not designed to address software-specific concerns (source code disclosure, binary distribution, etc.). Use MIT or Apache for code; use CC for data and documents.

**Recommendation: MIT is correct for this codebase.**

You are an independent researcher wanting maximum adoption. You are not building a commercial product. MIT maximizes the chance that other researchers, sports analysts, and journalists use and cite your tools. If commercial use without payment bothers you, you can add a non-binding request for attribution in the README, but you cannot change the license without affecting existing users.

### How to Display the MIT License Notice Properly

Your GitHub repository should have:

1. A file named `LICENSE` (no extension) in the root directory containing the standard MIT license text with your name and year:

```
MIT License

Copyright (c) 2026 Michael Allman

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

2. A brief mention in your README:
```
## License
Code: MIT License © 2026 Michael Allman
Database: CC BY 4.0 © 2026 Michael Allman
Paper: CC BY 4.0 © 2026 Michael Allman (upon publication in Scientific Reports)
```

---

## 4. The OSNR Framework — Protecting the Name and Concept

### Can You Trademark "OSNR" or "Outlier Score Nullification Rule"?

Technically, you could file a trademark application with the USPTO for "OSNR" as a service mark (marks for services) or trademark (marks for goods). The filing fee is approximately $250–$350 per class.

However, before pursuing this, consider several practical obstacles:

**Prior use in other fields:** "OSNR" is a widely used acronym in telecommunications — it stands for "Optical Signal-to-Noise Ratio." The USPTO would likely cite prior registrations or common use in that field when examining your application in any overlapping class. This does not necessarily defeat your application (the goods/services must be related for trademark confusion to matter), but it complicates it.

**Distinctiveness:** Trademarks must be distinctive — either inherently (invented words like "Xerox") or through acquired distinctiveness (secondary meaning built over time). An acronym for a descriptive phrase ("Outlier Score Nullification Rule") faces scrutiny because it describes what the thing does. Descriptive marks are harder to register.

**What would you enforce?** Trademark protects against consumer confusion in commerce. If another researcher publishes a paper using "OSNR" to mean something different in a sports analytics context, you could potentially object. But the practical enforcement mechanism is academic norms (citation, attribution), not trademark law. Filing and maintaining a trademark costs money and attention you would be better spending on research.

**The honest assessment:** For an academic framework, trademark is almost never the right tool. The academic community does not work on trademark principles. Priority and attribution are established through publication records, citations, and academic reputation — not registered marks.

### Prior Art Considerations

Before publication, it is worth doing a basic search to confirm no one has published a substantially similar framework under any name. Searches to conduct:

- Google Scholar: "judge bias permutation test figure skating," "judge outlier detection sports scoring," "leave-one-out judge scoring"
- arXiv (stat.AP section): search for figure skating, sports judging, and related terms
- SportRxiv and related preprint servers

If you find prior work that resembles OSNR, you need to know about it before peer review finds it for you. The goal is not to prove you have nothing to cite — it is to understand the landscape so you can correctly position your contribution.

Based on what is publicly known about figure skating analytics research, there is no published framework that combines permutation-based pairwise testing with leave-one-judge-out counterfactuals in a two-tier audit system. The field has prior work on judge bias detection (Looney & Wann, various ISU internal studies, Zitzewitz 2006 on Olympic judging), but OSNR as you have structured it appears to be original.

### Priority Date — What It Is and What It Means

"Priority date" in the academic context means the earliest date you can prove you conceived and fixed the framework. This matters if someone later claims they invented a similar approach first.

Your priority evidence:

- **GitHub commit history** on `michaelallman1960-max/figure-skating-judge-bias` — timestamped, immutable, and public
- **Journal submission date** at Scientific Reports — also timestamped
- **SSRN or preprint posting** (if you do this before journal submission — recommended)
- **This project directory** with file modification timestamps

What "establishing priority" means in practice: if a competitor later publishes something very similar and claims they invented it, you can point to your GitHub commits, your preprint, your submission date, and say "I was first." In academic disputes, this is resolved through the academic community's judgment, not courts. Having a clear, public, timestamped record is your protection.

**Practical step:** Post a preprint to SSRN or arXiv before or simultaneous with journal submission. This creates a public, timestamped record with a permanent URL. It also accelerates community awareness.

### Why the Publication Record Is More Valuable Than a Trademark

In academia, the currency is citation and attribution. A framework becomes "yours" not because you filed a trademark, but because:

1. You published first (priority)
2. Others cite your paper when they use the framework
3. The framework is associated with your name in the literature

If you publish in Scientific Reports and your paper is cited 50 times over five years, "OSNR" becomes associated with Allman (2026) in the literature. That is more durable protection than a trademark. Trademarks must be maintained, renewed, and actively enforced. Citations accumulate passively.

The investment in publishing a clear, well-documented paper is worth far more than filing a trademark application.

---

## 5. Open Access and Your Rights at Scientific Reports

### What CC BY 4.0 Means When Scientific Reports Publishes Your Paper

When Scientific Reports publishes under CC BY 4.0, the following is true:

**You retain copyright.** The paper says "© 2026 Michael Allman" (or similar). Scientific Reports receives a license to publish, distribute, and make the paper available, but you remain the legal owner of the copyright.

**Anyone can reuse the paper** — including for commercial purposes — as long as they:
- Give appropriate credit (cite you as the author)
- Provide a link to the CC BY 4.0 license
- Indicate if they made changes

**You can do anything with your own paper**, immediately upon publication:
- Post the final published PDF on your personal website
- Post it to SSRN, Academia.edu, ResearchGate
- Include figures and text in subsequent papers
- Distribute copies at conferences
- Send it to journalists without restriction
- Include it in your portfolio

There is no embargo period. No restrictions on self-archiving. No "personal use only" clauses.

### Comparing Scientific Reports to Traditional Journals

| | Scientific Reports (CC BY 4.0) | Traditional Subscription Journal |
|---|---|---|
| Who owns copyright after publication? | You do | Journal does |
| Can you post the final PDF online? | Yes, immediately | Typically no, or after 6-24 month embargo |
| Can others reuse without asking you? | Yes, with attribution | No (must license from journal) |
| Is the paper behind a paywall? | No | Yes |
| Article processing charge (APC)? | Yes (~$2,490 as of 2025) | No (but subscription access is expensive) |

For your purposes — an independent researcher wanting maximum visibility, citation, and public access — Scientific Reports' model is clearly superior. The APC is real money, but weigh it against the value of retaining full rights and having zero access barriers for readers.

### What You Cannot Do Under CC BY 4.0

The CC BY 4.0 license does not require attribution when *you* reproduce your own work — you are the copyright holder and need no license. But it does mean:

- You cannot later claim the paper is "all rights reserved" — the CC BY 4.0 grant is irrevocable
- You cannot prevent someone from translating your paper into another language and publishing it (as long as they attribute you)
- You cannot prevent a news outlet from excerpting your findings (they would need to attribute you)

For an academic researcher seeking impact, none of these restrictions should concern you. The irrevocability of CC BY 4.0 is a feature, not a bug — it means your paper will always be freely accessible.

---

## 6. The Database — Specific Considerations

### What Is and Is Not Protectable

**Not protectable (facts in the public domain):**
- Individual judge scores as published by the ISU
- Skater names, competition dates, event names
- Raw TES and PCS component scores from official protocols

**Protectable (your original contribution):**
- The selection of 17 competitions across 2022–2026 and the curatorial decisions about what to include
- The database schema: table structure, field names, foreign key relationships, data types
- The computed BI(j) bias index values
- p-values from permutation testing
- LOJO (Leave-One-Judge-Out) counterfactual results
- OSNR tier classifications and flags
- The pairwise pair calculations (269,957 pairs)
- Any normalization or standardization choices
- The deduction sign convention (stored as negative numbers, summed in TSS)

The Feist standard requires only a "modicum of creativity" in selection and arrangement. Your schema and derived fields easily meet this standard.

### Recommended License for the Database: CC BY 4.0

Apply CC BY 4.0 to the database. Include a LICENSE.txt file in any distribution of the database containing the standard CC BY 4.0 text, and include a README that clarifies:

```
This database is licensed under Creative Commons Attribution 4.0 International
(CC BY 4.0). See LICENSE.txt.

The database contains:
- ISU figure skating competition scores (2022–2026), which are factual records
  in the public domain
- Original schema, computed fields, and derived statistics © 2026 Michael Allman,
  which are protectable under copyright

When citing this database, please use the citation format below.
```

### Recommended Citation Format

Specify exactly how you want to be cited. Researchers who use your database without guidance may cite it poorly or inconsistently. Provide a citation in your README and paper:

```
Allman, M. (2026). Figure Skating IJS Judging Bias Database [Data set].
GitHub. https://github.com/michaelallman1960-max/figure-skating-judge-bias
```

Or, if you deposit to Zenodo (see below):
```
Allman, M. (2026). Figure Skating IJS Judging Bias Database (v1.0) [Data set].
Zenodo. https://doi.org/10.5281/zenodo.XXXXXXX
```

### Should You Get a DataCite DOI?

A DOI (Digital Object Identifier) for your dataset serves two purposes:

1. **Citability:** A DOI is a persistent, citable identifier. Papers can cite `doi:10.xxxx/xxxxx` and the link will resolve indefinitely, even if your GitHub URL changes.
2. **Discoverability:** Datasets with DOIs are indexed in academic databases.

The easiest path: deposit your database to **Zenodo** (zenodo.org), which is free, run by CERN, and automatically assigns a DOI. Zenodo integrates with GitHub — you can create a release on GitHub and Zenodo will automatically archive it and assign a DOI.

**Recommendation:** Do this. It takes about 30 minutes, it is free, and it significantly increases the citability and perceived credibility of your dataset. Do it when you submit the paper.

---

## 7. Risk Areas

### ISU Claiming Ownership of "Their" Data

The ISU publishes official competition protocols on its website. These are factual records of public competitions. Under US law (Feist) and the laws of most countries, facts are not copyrightable.

The ISU cannot prevent you from:
- Collecting and analyzing published score protocols
- Publishing analyses of their data
- Distributing a database of their published scores

What the ISU could theoretically do:
- Argue that their website's terms of service prohibit scraping (common in terms of service, but generally unenforceable for public factual data under US law)
- Issue a cease-and-desist claiming copyright in their published protocols

**How to respond to an ISU cease-and-desist:** Do not panic and do not comply immediately. Consult an IP attorney. The ISU's legal position on public factual data is weak under US law, but a C&D is designed to create chilling effects on people who cannot afford to fight. Your use of public competition data for research purposes is well within the bounds of fair use and is consistent with how academic researchers have always worked with publicly published data. The ISU's real leverage, if any, would be reputational — they could try to pressure you through skating federation channels, not courts.

### Someone Copying the OSNR Framework Without Attribution

This is the most realistic risk. A researcher or journalist reads your paper, finds the framework useful, applies it to a different sport, and does not cite you.

Your mitigation:
- A clear, well-documented published paper with a specific framework name and defined methodology
- A preprint record predating any potential copying
- Active engagement with the research community so your work is known

Your remedy if it happens:
- Contact the person directly (most cases of non-attribution are oversight, not malice)
- Contact their institution's research integrity office if they refuse to add a citation
- Write to the journal's editor

This is an academic integrity matter, not a legal matter, in most cases. Your legal remedy (copyright infringement) is technically available but practically difficult and expensive to pursue for a missing citation.

### Someone Using Your Code Commercially Under MIT License

Under the MIT license, commercial use is explicitly permitted. A sports analytics company could take your code, integrate it into a paid product, and sell it — without paying you and without releasing their modifications.

Is this OK? It depends on your goals. If your goal is maximum impact and adoption, this is a feature — commercial adoption validates the framework and spreads it widely. If you want to prevent commercial use without compensation, you should have chosen a more restrictive license (GPL does not prevent commercial use either, but it does require derivatives to be open source; a commercial license would require paying you).

**The honest answer:** You cannot change the MIT license on code that has already been distributed under it. If commercial use without compensation bothers you, you can release future versions (v2.0+) under a different license (dual-licensing under MIT and a commercial license is possible), but existing users of v1.0 under MIT retain their rights permanently.

For most independent researchers, the answer is: let it go. If a company uses your code to build something, they will cite your paper, which is what you actually want.

### Defamation Risk from Specific Findings About Specific Judges

This is your most significant legal risk, and it deserves careful attention.

Figure skating judges are private individuals, not public officials. The legal standard for defamation claims by private individuals is lower than for public figures. If a specific judge claims that your publication damaged their reputation by falsely portraying them as biased, they might have a viable defamation claim — depending on how your findings are framed.

**How to minimize this risk:**

1. **Distinguish findings from accusations.** "Judge X's scores were statistically anomalous under the OSNR framework" is a factual statement about data. "Judge X is corrupt" or "Judge X intentionally cheated" is an accusation of intent that you cannot prove from statistical analysis alone.

2. **Be precise about what your statistics show and do not show.** Your permutation-based test detects outlier scores relative to a judge's peers. It does not prove intent, bias, corruption, or misconduct. Say this explicitly and repeatedly in the paper.

3. **Avoid the word "bias" when "statistical anomaly" will do.** "Bias" implies intent. "Statistical outlier" or "anomalous scoring pattern" describes what you actually measured.

4. **Use aggregate framing where possible.** "Events with significant pairwise statistics in which removing the outlier judge changes podium outcomes" is more defensible than "Judge X handed the gold medal to Skater Y."

5. **The truth defense.** Truth is an absolute defense against defamation. If your statistics accurately report what happened, you are protected. But you need to be sure your statistics are correct and that your interpretive claims stay within what the data can actually support.

6. **If your paper names specific judges in the context of Tier 2 flags, consider whether that level of specificity is necessary for the scientific contribution.** The methodology paper may be more defensible with anonymized case studies; the Significance Magazine article for a general audience requires especially careful framing.

**If you receive a legal threat related to specific findings:** Consult an attorney immediately. Do not respond to the threatening party directly. Defamation cases against researchers publishing accurate, well-sourced research findings are rare and generally unsuccessful, but they are expensive to defend.

### What to Do If ISU or a Federation Sends a Cease-and-Desist

1. Do not comply or agree to anything in writing without consulting an attorney.
2. Do not immediately take down material.
3. Document everything — save the C&D letter.
4. Assess the claim: is it about copyright (unlikely to succeed on public factual data), defamation (more serious — evaluate whether your claims are defensible), or terms of service (evaluate how you collected the data).
5. Consider reaching out to the Electronic Frontier Foundation (EFF) or a law school IP clinic. Researchers facing C&D letters for legitimate academic research sometimes receive pro bono assistance.

---

## 8. Recommended Actions — Prioritized

### What to Do NOW (Before Submission)

**Priority 1 — Immediate:**
- [ ] Verify that your GitHub repository has a correct `LICENSE` file with your name and 2026 as the copyright year
- [ ] Add a README section clearly stating the license for both code (MIT) and database (CC BY 4.0)
- [ ] Include a copyright notice in the paper manuscript (© 2026 Michael Allman)
- [ ] Review the paper for language that could be interpreted as accusing specific judges of intent — ensure all claims stay within what your statistics can actually support *(periodic reminder: say "statistically anomalous pattern," never "biased," "corrupt," or "intentional")*

**Priority 2 — Before or at submission (DECIDED ✅):**
- [ ] Post preprint to **both SSRN and arXiv** simultaneously with journal submission — establishes public priority date *(decided 2026-02-21)*
- [ ] Create **Zenodo DOI** for the database — free, ~30 min, makes dataset permanently citable; cite the DOI in the paper itself *(decided 2026-02-21)*
- [ ] Apply **CC BY 4.0** license to the database — add LICENSE file and README notice *(decided 2026-02-21)*
- [ ] Include a clear, specific citation format for the database in your README and paper

**Priority 3 — Good practice:**
- [ ] Read the actual Scientific Reports publication agreement before signing — confirm it matches CC BY 4.0 author-retains-copyright policy
- [ ] Add a data availability statement to the paper pointing to the GitHub repository and Zenodo DOI

### What to Do Upon Acceptance at Scientific Reports

- [ ] Read the publication agreement carefully before signing
- [ ] Confirm you are not being asked to sign a copyright transfer — if you are, this contradicts Scientific Reports' stated CC BY 4.0 policy and you should contact the journal
- [ ] Update the Zenodo deposit with the accepted manuscript version if needed
- [ ] Post the final published PDF to your personal website and SSRN once published
- [ ] Add the DOI and full citation to your GitHub README

### What to Do If You Ever Commercialize the Framework

If you develop a paid product (a consulting service, a commercial software tool, an audit service for sports federations) based on OSNR:

- [ ] Consult an IP attorney at that point — the stakes justify the cost
- [ ] Consider releasing the commercial software under a dual license (MIT for open-source users, commercial license for paying customers)
- [ ] Consider whether to seek a trademark on "OSNR" or a product name at that point — it becomes more relevant in a commercial context
- [ ] The paper and database remain CC BY 4.0 — you cannot revoke those licenses, but you can offer commercial support and implementation services

### Whether to Consult an IP Attorney

**You probably do not need an attorney right now.** The steps above are within your ability to implement correctly, and the risks are manageable through good writing practices and standard licensing choices.

**You should consult an attorney if:**
- You receive any legal communication (cease-and-desist, legal notice) from the ISU, a national federation, a judge, or anyone else related to this research
- You decide to commercialize the framework
- You want to register copyright with the US Copyright Office (an attorney can help, though it is also straightforward to do yourself)
- The paper names specific individuals in contexts that could be read as defamatory and you want a defamation review before publication
- You are unsure about the publication agreement you are asked to sign

For the defamation question specifically — given that your research identifies specific judging anomalies that could damage individual reputations — a one-hour consultation with an IP/media attorney before submission is worth considering. It is not essential, but it would give you confidence in how you have framed the findings.

---

## 9. The "AI-Assisted" Question

### Does Using AI Tools Affect Your Copyright Ownership?

This is an evolving area of law, and the US Copyright Office has issued guidance (most recently in 2024) that is relevant here.

**The current US Copyright Office position:**
- Works created entirely by AI without human authorship are not copyrightable
- Works where a human author uses AI as a tool — but makes creative choices about selection, arrangement, expression, and content — are copyrightable by the human author
- The key question is whether there is "sufficient human authorship" in the final work

**For your paper:** You developed the research question, designed the methodology, collected and analyzed the data, and made all the substantive intellectual choices. The creative and intellectual authorship is yours. Your copyright is not affected by AI tool use.

**For your code:** The same principle applies. You designed the algorithms, specified the logic, reviewed and modified the output, and integrated everything into a working system. Copyright is yours.

### The AI Disclosure Debate — Decided Position (2026-02-21)

**The author's initial position:** Did not want to disclose AI assistance in the manuscript, viewing it as potentially undermining peer review reception.

**After discussion, agreed position:** Use the middle-path disclosure language below. Rationale accepted by the author:
- Scientific Reports has an explicit, mandatory AI disclosure policy — non-disclosure risks retraction even if the science is correct
- The risk is asymmetric: disclosure costs nothing material; non-disclosure caught post-publication could destroy the project entirely
- The middle-path language is accurate, compliant, and frames AI correctly as an implementation tool — not a research substitute

**Agreed disclosure language (for Acknowledgments or Methods):**

> "Standard computational tools, including AI-assisted coding environments, were used in the implementation of the analysis. All research design, data collection, statistical methodology, analytical decisions, and conclusions are the work of the author."

This is truthful, complies with journal policy, and frames AI as a tool — analogous to Python or statistical libraries — rather than as the researcher. It does not concede anything about intellectual ownership.

**Decision to revisit:** Before final submission, review Scientific Reports' current AI policy precisely and confirm this language meets their specific requirements. Do not finalize wording until then.

### The AI Narrative — A Strategic Asset Outside the Paper

**The author's insight (2026-02-21):** The AI story is not just a compliance item — it is a compelling second narrative running underneath the science. The surface story is the figure skating finding. The deeper story is what it represents: a smart, dedicated individual using AI as a force multiplier to produce expert-quality research that would previously have required an academic team, a research budget, and institutional support.

This narrative belongs prominently in:
- **The Significance Magazine piece** — the independent researcher angle is already woven into the draft
- **The op-ed** — "I built this alone, using modern AI tools, in months" is a powerful closing beat
- **Press interviews** — journalists will find the "AI-enabled independent researcher" angle as interesting as the figure skating finding itself
- **MIT Sloan and conference talks** — this is a proof-of-concept for a broader argument about how AI is democratizing expert research
- **The personal brand** — Michael Allman as an example of how modern tools allow smart, motivated individuals to push ideas forward without institutional gatekeeping

**The framing to use everywhere outside the journal paper:**
> "What AI allowed me to do is work at a level of rigor and scale that would previously have required an academic research group or professional consultancy. The statistical framework is mine. The methodology is mine. The findings are reproducible by anyone. What changed is that I didn't need a team to get here."

**What NOT to say:** "AI did the analysis" or "I used ChatGPT to find bias." Be specific and accurate: AI tools assisted with implementation, iteration, and efficiency. The intellectual choices, the framework design, the methodological decisions, and the interpretation are entirely the author's.

**The two-layer story:**
- Layer 1 (the science): A statistical audit of Olympic figure skating reveals structural vulnerabilities that have gone undetected — and a remedy that can be applied in real time
- Layer 2 (the meta-story): This was produced by one person, working independently, using AI as a force multiplier — a demonstration of what is now possible outside traditional institutions

### What You Must Be Able to Do Regardless

Whether you disclose or not, you must be able to:
- Explain every methodological choice in the paper under questioning from a reviewer
- Reproduce the analysis independently if asked
- Defend every statistical claim from first principles

These conditions are met for this project. The intellectual work is genuinely the author's.

---

## Summary: Your IP Position in One Page

| Asset | Who Owns It | How Protected | License |
|-------|-------------|---------------|---------|
| Paper text | You | Copyright (automatic) | CC BY 4.0 (upon publication in Scientific Reports) |
| Python codebase | You | Copyright (automatic) | MIT License |
| Database schema + computed fields | You | Copyright (automatic) | CC BY 4.0 |
| ISU raw scores in the database | No one owns facts | N/A — public domain | N/A |
| OSNR framework concept | No one can own a method | Priority through publication | N/A |
| "OSNR" name | Potentially trademarkable, but not worth pursuing now | Publication priority | N/A |

**Your most important actions:**
1. Post a preprint before or at submission
2. Get a Zenodo DOI for the database
3. Read the Scientific Reports publication agreement carefully
4. Write defensibly about specific judges — distinguish statistical findings from intent claims

**Your most important rights:**
- Under CC BY 4.0, you retain copyright in your paper even after publication
- Under MIT, you remain the copyright holder of your code
- Your compiled database (schema + derived statistics) is protectable even though the underlying facts are not

---

*This guide was prepared for informational purposes on 2026-02-21. It does not constitute legal advice. Laws change, journal policies change, and individual circumstances vary. Consult a licensed intellectual property attorney for decisions with material legal or financial consequences.*
