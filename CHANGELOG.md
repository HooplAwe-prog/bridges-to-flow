# Change log

Each entry: what changed, why (the evidence), and the effect. Milestone 4 asks for "changes
since prototype v1", so log every change from usability tests, peer reviews, and checks here.

## [0.3.0] - 2026-11-22 - Prototype v1 (Milestone 3)
### Added
- Role-based access (recruiter, hiring manager, admin) with demo mode for grading.
- Pipeline board with stage targets and stall flags.
- Incomplete-application and stalled-record notices with human keep/drop decisions.
- AI-assisted ATS → HRIS field matcher with confidence, missing-value and duplicate checks,
  and required human approval.
- Aggregate manager dashboard with small-group suppression (n < 5).
- Fairness spot check (on-time impact ratio by channel and branch) and validity check
  (held-out mapping accuracy).
- Audit log (IDs only), 60-day retention purge, single-record deletion.
- 19 automated tests.

### Decisions that differ from Milestone 2
- **Data store: SQLite instead of CSV/Google Sheets.** One local file, no external account,
  no sheet ID to protect, and it supports the audit log. Still fully deletable.
- **Scope follows the Milestone 1 problem** (ATS → HRIS handoffs) using the Milestone 2 stack
  and privacy design (aggregated manager view, role separation, logging, 60-day retention).

### Found during build
- In-sample mapping accuracy was 100%, which was circular because the synonyms were written for
  those schemas. Added a frozen held-out set: 67% accuracy, below the 0.80 stop rule, with 0
  confident mistakes. Decision: keep all mappings under human review.
- First version of the synthetic data flagged 63% of records as stalled, which made the
  fairness check meaningless. Changed the generator so about 1 in 5 records exceed their target.
- Fairness check: the planted mobile-app pattern shows up in the missing-field rate (22% vs
  5–13%) but **not** in the on-time impact ratio (0.88). The impact ratio alone missed it.

## [0.3.1] - 2026-11-22 - Align with course learning pathway
- Stop rules made measurable: each names the measure, the threshold, **who reviews**, and the
  next step (`STOP_RULES` in config; shown on Admin → Fairness & validity; RUNBOOK table).
  Evidence: the course's feedback example asks for exactly these three parts.
- README links say "Unavailable" until verified instead of using placeholder URLs, because the
  course treats placeholder links as missing work.
- MILESTONE_MAP maps the M3 knowledge, skill, and ability goals to evidence in the prototype.

## [0.3.2] - 2026-11-22 - Hosting on Hugging Face Spaces
- Added `Dockerfile`, `.dockerignore`, and Space settings in the README header, because Streamlit
  Community Cloud requires a GitHub account. Runs as user 1000; settings passed as startup flags.
- Pinned tested versions: streamlit 1.67.0, pandas 3.0.5, altair 6.3.0.
- Checked by running the same steps as the container (fresh environment, non-root user, same flags):
  health check 200, every page opens, full transfer and CSV export work.

## [Unreleased] - changes from usability testing and peer review
<!-- Add one bullet per change: what, evidence (e.g. "3 of 5 testers..."), effect. -->
