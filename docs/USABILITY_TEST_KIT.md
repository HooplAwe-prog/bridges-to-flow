# Usability test kit (Milestone 3)

Goal: at least **5 testers × 3 tasks**. Each session takes about 15 minutes.
Collect only what's listed here: no names, ages, demographics, or health/disability information.
Give each tester a code (T1–T5).

## 1. Agreement script (read aloud, get a yes before starting)
> "Thanks for helping. I'm testing a class prototype, not you. It uses only made-up data.
> I'll give you three short tasks and time them. I'll note whether you finished, how long it
> took, any wrong clicks, and anything you say about it. I won't record your name or anything
> personal. You can skip a task or stop any time. Is that OK?"

Record: `T#: agreed (yes/no), date`. Don't record names.

## 2. Setup
- Open the live link in a fresh browser window. Start on the sign-in page.
- Don't explain the app beyond: "This tool helps HR move approved applicants into the employee system."
- Think-aloud is welcome. Don't help unless the tester is stuck for 60 seconds (that counts as a fail with assistance).

## 3. Tasks

| Task | Say this | Success means | Time limit |
|---|---|---|---|
| **T1. Find a stalled record** | "Sign in as a recruiter. Find one application that has been waiting too long, and tell me its ID and stage." | Correct ID + stage of any record marked ⚠ Stalled | 2 min |
| **T2. Transfer an approved applicant** | "Move one applicant who is ready for the HR system into it. Make sure the information is right." | Record appears on HRIS export page | 4 min |
| **T3. Read the manager view** | "Sign in as a hiring manager. Which stage has the most stalled records?" | Names the stage with the highest stalled count | 2 min |

Optional T4 (if time): "As an admin, find when the transfer you just did was recorded." Success: finds `approve_transfer` in the audit log.

## 4. Data sheet (one row per tester per task)

| Tester | Task | Success (Y / Y-assisted / N) | Time (sec) | Errors (wrong clicks / dead ends) | Observation (what they did or said) |
|---|---|---|---|---|---|
| T1 | T1 | | | | |
| T1 | T2 | | | | |
| T1 | T3 | | | | |
| … | | | | | |

Count an *error* as a click on the wrong page or control, or a wrong answer they later correct.

## 5. After all tasks (1 minute)
Ask: "On a scale of 1–5, how easy was this to use?" and "What was most confusing?"
Write the answer in a few words.

## 6. Summarize (for the report)
For each task: success rate (e.g. 4/5), median time, total errors, the 1–2 most common observations.
Then list **changes made** (or planned), each tied to evidence:
"3 of 5 testers looked for the transfer button on the Pipeline board → added a link/hint there."

Keep the raw sheet. Don't put it in the public repo if it has any identifying notes.

## Measurement limits to mention
- 5 testers, likely classmates/friends: not real HR users, so findings are about first-time use.
- Same task order for everyone → learning effects on later tasks.
- You are both developer and facilitator → possible bias in what you notice.
