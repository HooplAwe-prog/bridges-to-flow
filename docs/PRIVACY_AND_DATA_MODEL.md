# Data model & privacy

All records are synthetic: invented names, `@example.com` emails, and 555-01xx phone numbers.
The prototype collects **no** health, disability, demographic, salary, student, or personnel
performance data.

## Entities

| Table | One row per | Key fields | Who can see it |
|---|---|---|---|
| `applicants` | application | `applicant_id` (SYN-####), source system, branch, application channel, stage, status (active / dropped / transferred), complete flag, applied / stage-entered / closed timestamps, raw ATS record (JSON) | Recruiter (individual records) |
| `hris_export` | human-approved transfer | `applicant_id`, approving role, approval time, HRIS-formatted record | Recruiter |
| `audit_log` | action | timestamp, role, action, target record ID, short detail | Admin |

**Raw ATS record fields** (named differently in each synthetic source): first name, last name,
personal email, phone, requisition ID, job title, department, proposed start date, work
location, employment type. These are the minimum needed to create an HRIS record.

## Aggregation
- Hiring managers see **totals only**: counts, stalled counts, and median days by stage and
  branch. No names, emails, or IDs.
- Any group with fewer than **5** records is shown as "< 5 (hidden)" so a person can't be
  singled out (`MIN_GROUP_SIZE` in `bridge/config.py`).

## Access

| Role | Can | Cannot |
|---|---|---|
| Recruiter | View individual records, move stages, keep/drop incomplete applications, approve transfers, download HRIS export | See audit log, run purge |
| Hiring manager | View aggregate dashboard | See any individual applicant |
| Admin | Dashboard, fairness/validity checks, audit log, retention purge, single-record deletion, demo reset | (Admin sees IDs in the log, not names) |

Demo mode (default) lets anyone pick a role because the data is synthetic and the grader must not
need credentials. Setting `DEMO_MODE = "false"` in secrets turns on per-role passcodes,
compared with `hmac.compare_digest`.

## Retention & deletion
- Closed records (transferred or dropped) older than **60 days** are listed for purge on
  Admin → Data retention. Purge is a hard delete, requires a confirmation tick, and is logged.
- Any single record can be deleted on request by ID (deletion request).
- The audit log keeps record IDs only, never names or emails, so it can outlive the records it
  refers to. A test (`test_audit_log_has_no_names`) checks this.

## Secrets
- No keys or passcodes are in code or the repo. `.streamlit/secrets.toml` is in `.gitignore`;
  only `secrets.toml.example` with placeholder values is committed.
- On Streamlit Cloud, secrets go in *App settings → Secrets*.
- The prototype calls no external AI API, so there is no API key to protect.

## Human oversight built into the data flow
- The system **never fills in** a missing value. Missing required fields block approval until a
  person types the value.
- The system **never drops** an application. It sends a notice; HR decides.
- Nothing reaches `hris_export` without a person ticking the confirmation box and clicking
  Approve. Each approval is logged with role and time.

## Volunteer testers
Usability testing collects only task success, time, error count, and short notes. No names,
ages, demographics, or health/disability information. See `USABILITY_TEST_KIT.md`.
