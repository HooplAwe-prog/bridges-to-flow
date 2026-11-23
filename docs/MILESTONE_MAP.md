# How the milestones connect

The course pathway: **M1** establishes a feasible direction → **M2** justifies the tools →
**M3** tests a first version → **M4** demonstrates the final prototype and explains evidence,
revisions, safeguards, documentation, limits, and next steps. M3 is the baseline that M4 compares
against, so every change after v0.3.0 goes in CHANGELOG with the evidence behind it.

## What each milestone set, and where it lives now

| Milestone | What it set | Where it lives in the prototype |
|---|---|---|
| **M1 Propose** | Problem: ATS → HRIS handoffs stall and need retyping. AI assists, humans decide; no selection decisions. Notify on incomplete applications; manager chooses to drop. Never make up missing info. 0.80 stop rule. | Pipeline board; Notices; Review & transfer (blocks on missing values); stop rules in `config.py` |
| **M2 Justify tools** | Streamlit (score 127). Role separation; managers see aggregates; admin sees logs. Timestamped logging. 60-day retention. Secrets in Streamlit secrets manager. | Role gate; Team dashboard (aggregates, n < 5 hidden); Audit log; Data retention; `secrets.toml.example` |
| **M3 Test v1** (this) | 3–5 working features and a complete path; 3 tasks × 5 testers; fairness and validity checks; 2 peer reviews; prioritized action plan | README features 1–5 and end-to-end path; Fairness & validity page; `USABILITY_TEST_KIT.md`; `PEER_REVIEW_FORM.md`; CHANGELOG 0.3.0 |
| **M4 Demonstrate** | Final flow in a 5–7 min captioned demo; evidence, revisions, safeguards, operating docs, limits, next steps; working links; AI Appendix | Everything above + CHANGELOG [Unreleased] → 1.0.0, `RUNBOOK.md`, `MODEL_CARD.md` |

## Knowledge, skill, ability (from the M3 pathway)
| Pathway goal | Evidence in this prototype |
|---|---|
| **Knowledge**: usability, measurement, fairness, evidence limits | In-sample vs held-out accuracy (why 100% isn't evidence); impact ratio vs missing-field rate (one measure missed the planted pattern); stated limits on each check |
| **Skill**: build, test, synthesize feedback | Working app + 19 tests; usability test kit; peer review form with a trace-to-action-plan column |
| **Ability**: prioritize changes from observed needs | Action plan items each cite a tester count, peer comment, or check result |

## Measurable stop rules
Each names the measure, the threshold, who reviews, and what happens. See `RUNBOOK.md` or
Admin → Fairness & validity → Stop rules.

## M4 section → existing source
| M4 required section | Start from |
|---|---|
| Architecture & implementation | README layout + PRIVACY_AND_DATA_MODEL (interface = Streamlit; processing = `bridge/`; store = SQLite; integrations = simulated ATS exports and HRIS CSV; access = roles; secrets; logging = audit_log) |
| Validation & usability; changes since v1 | M3 results + CHANGELOG |
| Fairness & ethics | Fairness & validity page; PRIVACY (human review); RUNBOOK (stop rules, monitoring). Still needed: an **appeal/correction** path |
| Operations & documentation | README, RUNBOOK, CHANGELOG, MODEL_CARD |
| Limitations & technical debt | README "Known limitations"; MODEL_CARD limitations |
