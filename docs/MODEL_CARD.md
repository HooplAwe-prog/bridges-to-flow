# Model card: ATS → HRIS field matcher

| | |
|---|---|
| Component | `bridge/mapping.py` → `suggest()` |
| Version | 0.3.0 (Prototype v1) |
| Type | Rule-based similarity matcher (no trained model, no external AI service) |
| Output | Suggested HRIS field + confidence score 0–1 for each ATS field name |
| Generates content? | No. It suggests labels; it never creates or fills in values. |

## Intended use
Help a recruiter map ATS export columns to HRIS fields faster. A person confirms every
mapping before any record is transferred.

## Out of scope
Any decision about applicants (screening, ranking, scoring, recommending, or rejecting).
Filling in missing applicant data.

## How it works
1. Normalize the field name: split CamelCase and underscores, lowercase, expand common
   abbreviations (`fn` → first name, `dt` → date).
2. Compare it with each HRIS field's synonym list using character similarity (Python
   `difflib`) blended with word overlap.
3. Return the best match. Below **0.75** confidence the row is marked "⚠ Check this one."

## Evaluation (run live on Admin → Fairness & validity)

| Set | n | Top-1 accuracy | Wrong but not sent to review | Sent to review |
|---|---|---|---|---|
| In-sample (3 synthetic schemas the synonyms were written for) | 30 | 100% | 0 | — |
| Held-out (frozen 2026-11-22, not used for tuning) | 12 | 67% | 0 | 83% |

**Reading these numbers.** In-sample accuracy is *not* evidence the matcher generalizes,
because the synonym list was written for those schemas. Held-out accuracy (67%) is **below the
0.80 stop rule**, so the prototype must keep every mapping under human review. The key safety
result is that none of the four held-out mistakes was confident enough to skip review.

## Limitations
- 12 held-out names, labeled by one person (the developer). No second rater yet.
- Synthetic field names; real exports may be messier (merged columns, other languages).
- Confidence scores are similarity values, not calibrated probabilities.

## Monitoring & stop rule
Measure: held-out top-1 accuracy. Threshold: below 0.80 pauses any reduction in human review
(triggered now at 0.67). Reviewer: the admin/pilot owner weekly, with HR lead sign-off before
oversight changes. A single confident wrong suggestion pauses transfers the same day. Re-evaluate on a **new** held-out set after
any change to the synonym list, and record both numbers in CHANGELOG.md.
