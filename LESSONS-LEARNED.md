# Lessons Learned — Judging Bias Project

---

## python-docx

### Unicode characters must match exactly
Word documents use non-ASCII characters that vary by context. A string comparison that looks
correct will silently fail if the actual document uses a different Unicode character.

**Always `repr()` the target paragraph before writing a replacement:**
```python
idx = p.text.find("some anchor phrase")
print(repr(p.text[idx:idx+200]))
```

Common characters to watch:
| Character | Code | Looks like |
|-----------|------|-----------|
| Curly apostrophe | `\u2019` | `'` |
| Non-breaking space | `\u00a0` | ` ` (invisible) |
| Narrow no-break space | `\u202f` | ` ` (invisible, thinner) |
| Hair space | `\u200a` | ` ` (invisible, thinnest) |
| En dash | `\u2013` | `–` |
| Em dash | `\u2014` | `—` |
| Union symbol | `\u222a` | `∪` |
| Delta | `\u0394` | `Δ` |

The same *visual* sentence may use `'` (U+0027 straight) in one paragraph and `\u2019` (curly)
in another, depending on when it was typed in Word.

### The partial-save trap
If a fix script saves early (before completing all fixes) — e.g., because fix 5 of 6 raised
an exception and the script saved on the way out — the next run will fail on fixes 1–4
because those strings have already been replaced.

**Diagnosis:** Check which fixes succeeded by searching for the new text; apply only
remaining fixes. Inline Python is cleaner than re-running the full script in these cases:
```python
doc = Document("file.docx")
p = find_para(doc, "anchor text that is still present")
replace_in_para(p, "old text", "new text")
doc.save("file.docx")
```

### Table cell access — use raw lxml, not `table.cell()`
Tables created with `OxmlElement` (or tables lacking `<w:tblGrid>`) raise `InvalidXmlError`
when accessed via python-docx's `table.cell(row, col)`. Always use lxml directly:
```python
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
for t in doc.tables:
    tbl = t._tbl
    rows = tbl.findall(f".//{{{W}}}tr")
    for row in rows:
        for tc in row.findall(f".//{{{W}}}tc"):
            cell_text = "".join(e.text or "" for e in tc.findall(f".//{{{W}}}t"))
```

### Formatting is destroyed by `replace_in_para`
The `replace_in_para` helper zeroes out all runs and puts the full text in `runs[0]`.
This loses bold, italic, font size, and superscripts/subscripts within the paragraph.
**Only use it on paragraphs that are plain text or where formatting loss is acceptable.**
For formatted paragraphs (e.g., footnotes with superscripts, mixed bold/italic), edit
at the run level instead.

---

## Statistical / Analytical Correctness

### Directional vs absolute outcome-determinative criterion
The outcome-determinative test is **directional**: `B_j(gold, silver) > margin` — positive
only. Using `ABS(B_j) > margin` incorrectly includes judges who are biased *against* the
winner (which would help the silver medalist, not the gold). Always use the directional form.

Root cause of "11 events" error: the initial SQL query used `ABS(bias_points) > margin`.
Correct count: **9 events**.

### J5 significance acknowledgment
When a judge is significant in the *opposite* direction (toward silver), that is still a
real finding that must be acknowledged — even though it does not satisfy the outcome-
determinative criterion and would *widen* the gold-silver margin if removed.
Omitting or dismissing it as "not significant" is a factual error. State it explicitly with
direction and why it does not affect the outcome-determinative conclusion.

---

## Iterative Document Editing (ChatGPT review loop)

### Verify checks vs legitimate uses of the same phrase
Absence checks ("this string should not appear") can fail if the same phrase appears in a
different valid context. Example: checking absence of "preserve judge style" failed because
§6.1 keeps "the null must preserve judge style" as a design-goal statement — only the
"null models that preserve judge style" phrasing in the Abstract/Introduction needed changing.
**Make absence checks specific enough to target only the problematic context.**

### Add `*.docx.bak_*` to `.gitignore` before writing any fix scripts
Fix scripts create `.bak_*` backups before modifying the document. Without a gitignore rule,
these accumulate as untracked files and clutter file pickers and `git status`. Add the rule
once at project setup: `*.docx.bak_*` in `.gitignore`.

### Run each fix script on a fresh backup
Each fix script makes a `.bak_*` backup before modifying the document. If the script fails
mid-run and saves a partially-modified document, restore from the backup before re-running.
The backup naming convention: `judge_bias_isu_judging_system.docx.bak_{session_name}`.

---

## Project-Specific

### Two-part test parameters (as of bfdef94)
- **Pair-level**: q ≤ 0.05 AND B_j(A,B) > margin(A,B)  [directional, not absolute]
- **Event count**: 9 events (6.3% of 142 analyzed)
- **Key pair**: J1/FRA-USA in OWG 2026 Ice Dance FD (1.19 > 0.97 pts)

### Enrichment figures (as of bfdef94, §9.5)
- 25.4% of 271,728 pairwise tests yield p ≤ 0.05 (5.07× enrichment vs pure null)
- 3.78% yield p ≤ 0.001 (37.8× enrichment vs pure null)
- Pure null reference: 5.0% and 0.10% respectively
