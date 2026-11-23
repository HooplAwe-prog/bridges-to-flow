# Runbook & incident response

## Normal operation
| Task | How |
|---|---|
| Start locally | `streamlit run app.py` |
| Run tests | `python -m pytest -q` (expect all to pass before any deploy) |
| Reset demo data | Admin → Data retention → Reload synthetic demo data |
| Deploy a change | Push to GitHub `main`; Streamlit Cloud redeploys automatically. Add a CHANGELOG entry first. |
| Check the live link | Open it in a private/incognito window; sign in as each role. |

## Weekly checks (during a pilot)
1. Admin → Fairness & validity: record the lowest impact ratio and held-out accuracy.
2. Admin → Data retention: purge closed records older than 60 days.
3. Admin → Audit log: download a copy; look for unexpected `delete_records` or `sign_in_failed`.

## Stop rules (measurable)
Same rules as `STOP_RULES` in `bridge/config.py`, shown on Admin → Fairness & validity.

| Measure | Pauses the pilot when | Reviewed by | Then |
|---|---|---|---|
| Held-out mapping accuracy | below 0.80 (**currently 0.67: triggered**) | Admin (pilot owner), weekly; HR lead signs off before oversight is reduced | Keep 100% human review; re-test on a new held-out set after any fix |
| Wrong suggestions confident enough to skip review | 1 or more (currently 0) | Admin, same day | Pause transfers; raise review threshold above 0.75; log in CHANGELOG |
| On-time impact ratio, any group of 5+ | below 0.80 two weekly checks in a row | Admin with HR lead | Check that group's missing-field rate; fix the cause before expanding |
| Real personal data in app or repo | any | Admin, immediately; notify instructor/supervisor | Delete, rotate exposed secrets, record the incident |

## Incident response
| Incident | Do this now | Then |
|---|---|---|
| Real personal data entered | Delete the record (Admin → Delete one record); reload demo data | Note it in CHANGELOG; tell the instructor/supervisor |
| Secret committed to GitHub | Change the secret immediately; remove the file; rewrite history or recreate repo | Confirm `.gitignore` covers it |
| Wrong record transferred | Delete it from export (delete the record) and re-enter correctly | Review the mapping that caused it; add to held-out set for a future evaluation |
| App down | Check Streamlit Cloud logs; redeploy; run tests locally | Label the link "temporarily unavailable" in the submission if still down |
| Stop rule triggered | Pause any reduction in human review | Document the cause and fix in CHANGELOG and the action plan |

## Contacts
Prototype owner: the student developer (fill in in course submission, not in the repo).
