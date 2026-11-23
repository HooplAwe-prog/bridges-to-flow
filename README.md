# Bridges to Flow

A working prototype that helps HR and Talent Acquisition move approved applicants from an
applicant tracking system (ATS) into the HR information system (HRIS) without retyping, while
a person reviews and approves every transfer.

IOP 563, AI in I-O Psychology · Milestone 3 (Prototype v1) · Version 0.3.3
**All data in this app is synthetic.** No real applicants, employees, or organizations.

| | |
|---|---|
| Live prototype | https://bridges-to-flow-iop563.streamlit.app/ |
| Repository | https://github.com/HooplAwe-prog/bridges-to-flow |
| Access | Demo mode: choose a role, no passcode or account needed. Hosted on Streamlit Community Cloud. |

## The problem (from Milestone 1)
Large organizations keep applicant data in one system and employee records in another.
Handoffs between recruiters, background checks, hiring managers and finance stall, and data
is retyped by hand. This prototype makes waiting records visible and moves approved records
across with human confirmation. **It makes no hiring decisions.**

## What works (Prototype v1)

| # | Feature | Who uses it | Where |
|---|---|---|---|
| 1 | **Role-based access**: recruiter, hiring manager, admin each see different pages | Everyone | Sign-in page |
| 2 | **Pipeline board**: every application's stage, days waiting, and stall flag; human moves records forward | Recruiter | Pipeline board |
| 3 | **Notices**: incomplete applications (14+ days) and stalled records; HR chooses keep or drop | Recruiter | Notices |
| 4 | **AI-assisted ATS → HRIS mapping**: suggests field matches with confidence, flags missing values and duplicates, requires human approval | Recruiter | Review & transfer, HRIS export |
| 5 | **Aggregate dashboard + governance**: totals only (small groups hidden), fairness and validity checks, audit log, retention purge and deletion | Manager, Admin | Team dashboard, Fairness & validity, Audit log, Data retention |

### End-to-end path (use this for testing and screenshots)
1. Sign in as **Recruiter**.
2. **Pipeline board**: filter to *Ready for HRIS*.
3. **Review & transfer**: pick a record, check the suggested mappings, fix any red items, tick
   the confirmation box, and click **Approve transfer**.
4. **HRIS export**: see the approved record and download the CSV.
5. Switch to **Admin** → **Audit log**: see the approval recorded with the record ID only.

## Run it locally
```bash
python -m pip install -r requirements-dev.txt
streamlit run app.py          # opens http://localhost:8501
python -m pytest -q           # 19 tests: core logic + UI click-through
```
The database (`data/bridges.db`) is created and filled with synthetic data on first run.
Admin → Data retention → **Reload synthetic demo data** resets it.

## Deploy (Streamlit Community Cloud, used for grading)
1. The code is in the public GitHub repository above. `.streamlit/secrets.toml` is never committed.
2. At share.streamlit.io: **Create app → Deploy a public app from GitHub**, repository
   `HooplAwe-prog/bridges-to-flow`, branch `main`, main file `app.py`. The live app runs on Python 3.14.10 (Community Cloud default); local tests used Python 3.13.
3. No secrets are needed; demo mode is the default. To turn on passcodes later, paste
   `.streamlit/secrets.toml.example` into *App settings → Secrets* and set `DEMO_MODE = "false"`.
4. Check the live link in a private/incognito window before submitting.

Community Cloud apps sleep after a period without visitors; the first visit wakes the app (about a
minute). Storage resets on restart, so the synthetic demo data reloads, which is intended.
The `Dockerfile` is an optional container build and is not used by Streamlit Cloud.

## Project layout
```
app.py                 Streamlit interface (pages per role)
bridge/config.py       Thresholds: stage targets, 0.80 stop rule, group size, retention
bridge/data.py         Synthetic data generator (seeded, reproducible)
bridge/db.py           SQLite storage, audit log, transfer, delete/purge
bridge/mapping.py      Field matcher + validation (the "AI-assisted" part)
bridge/holdout.py      Frozen held-out set for the validity check
bridge/metrics.py      Stall detection, aggregation, fairness and validity checks
tests/                 pytest unit + UI tests
docs/                  Privacy/data model, model card, runbook, test kit, peer review form
CHANGELOG.md           What changed and why, by version
```

## Documentation
- [Data model & privacy](docs/PRIVACY_AND_DATA_MODEL.md)
- [Model card: field matcher](docs/MODEL_CARD.md)
- [Runbook & incident response](docs/RUNBOOK.md)
- [Usability test kit](docs/USABILITY_TEST_KIT.md)
- [Peer review form](docs/PEER_REVIEW_FORM.md)
- [How the milestones connect](docs/MILESTONE_MAP.md)
- [Change log](CHANGELOG.md)

## Known limitations (v1)
- Synthetic data only; no live ATS or HRIS connection (exports are simulated).
- The field matcher is rule-based similarity, not a trained model. Held-out accuracy is below
  the 0.80 stop rule, so every mapping stays under human review (see Fairness & validity).
- Stage targets (SLA days) are placeholders, not set with a real HR team.
- Demo mode has no real authentication. Passcode mode is a basic gate, not production security.
