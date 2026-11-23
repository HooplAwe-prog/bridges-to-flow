"""Synthetic applicant data.

Every person in this file is invented. Names are drawn from short generic
lists, emails use the reserved example.com domain, and phone numbers use the
555-01xx fictional range. No real applicant data is used anywhere.

Two patterns are planted on purpose so the checks have something to find:
  * Mobile applications are more likely to have a missing field, which tends
    to stall them. The fairness check should surface this.
  * A few people applied at two branches, so the duplicate check has work.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from .config import STAGE_SLA_DAYS, STAGES

FIRST = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Avery", "Quinn",
         "Jamie", "Drew", "Reese", "Skyler", "Rowan", "Parker", "Emerson", "Hayden",
         "Kai", "Logan", "Sage", "Blake"]
LAST = ["Rivera", "Chen", "Patel", "Okafor", "Nguyen", "Garcia", "Kim", "Smith",
        "Haddad", "Novak", "Silva", "Ito", "Mensah", "Larsen", "Cruz", "Ahmed",
        "Brooks", "Duarte", "Fischer", "Moreau"]
JOBS = [("Payroll Specialist", "Finance"), ("HR Coordinator", "Human Resources"),
        ("Warehouse Associate", "Operations"), ("Data Analyst", "Analytics"),
        ("Customer Support Rep", "Customer Service"), ("Facilities Technician", "Operations")]
BRANCHES = ["North", "South", "East", "West"]
CHANNELS = ["Online portal", "Mobile app", "Referral", "Career fair"]
EMPLOYMENT = ["Full-time", "Part-time"]

# Canonical HRIS field -> field name used by each synthetic ATS export.
SOURCE_SCHEMAS = {
    "ATS-A (Workday-style export)": {
        "legal_first_name": "Candidate_First_Name",
        "legal_last_name": "Candidate_Last_Name",
        "personal_email": "Email_Address",
        "phone": "Primary_Phone",
        "requisition_id": "Job_Requisition_ID",
        "job_title": "Job_Profile",
        "department": "Supervisory_Organization",
        "start_date": "Proposed_Start_Date",
        "work_location": "Work_Location",
        "employment_type": "Worker_Type",
    },
    "ATS-B (BambooHR-style export)": {
        "legal_first_name": "first name",
        "legal_last_name": "last name",
        "personal_email": "email",
        "phone": "mobile phone",
        "requisition_id": "requisition #",
        "job_title": "position",
        "department": "dept",
        "start_date": "anticipated start",
        "work_location": "site",
        "employment_type": "status",
    },
    "ATS-C (legacy abbreviated export)": {
        "legal_first_name": "fn",
        "legal_last_name": "lname",
        "personal_email": "eml",
        "phone": "ph_no",
        "requisition_id": "req",
        "job_title": "ttl",
        "department": "org_unit",
        "start_date": "begin_dt",
        "work_location": "loc",
        "employment_type": "emp_cls",
    },
}

REQUIRED_FIELDS = ["legal_first_name", "legal_last_name", "personal_email",
                   "requisition_id", "job_title", "department", "start_date"]


def _stage_weights() -> list[float]:
    # More people early in the funnel than late.
    return [0.18, 0.16, 0.15, 0.14, 0.11, 0.09, 0.08, 0.09]


def generate(n: int = 120, seed: int = 563, now: datetime | None = None) -> list[dict]:
    """Return n synthetic applicant rows (dicts) ready for the database."""
    rng = random.Random(seed)
    now = now or datetime.now()
    rows: list[dict] = []

    for i in range(1, n + 1):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        job, dept = rng.choice(JOBS)
        branch = rng.choice(BRANCHES)
        channel = rng.choice(CHANNELS)
        source = rng.choice(list(SOURCE_SCHEMAS))
        stage = rng.choices(STAGES, weights=_stage_weights())[0]

        applied_days_ago = rng.randint(3, 95)
        applied_at = now - timedelta(days=applied_days_ago)
        # Time already spent in the current stage: most records are within
        # their target; about one in five has waited too long.
        sla = STAGE_SLA_DAYS.get(stage, 3)
        if rng.random() < 0.8:
            in_stage = rng.randint(0, sla)
        else:
            in_stage = rng.randint(sla + 1, sla + 15)
        in_stage = min(in_stage, applied_days_ago)
        stage_entered_at = now - timedelta(days=in_stage)

        canonical = {
            "legal_first_name": first,
            "legal_last_name": last,
            "personal_email": f"{first.lower()}.{last.lower()}{i}@example.com",
            "phone": f"(555) 01{rng.randint(0, 99):02d}-{rng.randint(1000, 9999)}",
            "requisition_id": f"REQ-{rng.randint(1000, 1060)}",
            "job_title": job,
            "department": dept,
            "start_date": (now + timedelta(days=rng.randint(14, 60))).strftime("%Y-%m-%d"),
            "work_location": f"{branch} branch",
            "employment_type": rng.choice(EMPLOYMENT),
        }

        # Planted pattern: mobile applications lose a field more often.
        p_missing = 0.30 if channel == "Mobile app" else 0.10
        if rng.random() < p_missing:
            canonical[rng.choice(REQUIRED_FIELDS[2:])] = ""

        complete = all(canonical[f] for f in REQUIRED_FIELDS)
        # Incomplete records can't progress past the first stages in practice.
        if not complete and STAGES.index(stage) > 1:
            stage = rng.choice(STAGES[:2])
            stage_entered_at = applied_at + timedelta(days=rng.randint(0, 2))

        status = "transferred" if stage == "Transferred" else "active"
        if status == "active" and rng.random() < 0.06:
            status = "dropped"

        # Rename fields to match the source ATS's own export format.
        names = SOURCE_SCHEMAS[source]
        raw = {names[k]: v for k, v in canonical.items()}

        rows.append({
            "applicant_id": f"SYN-{i:04d}",
            "source_system": source,
            "branch": branch,
            "channel": channel,
            "stage": stage,
            "status": status,
            "application_complete": int(complete),
            "applied_at": applied_at.isoformat(timespec="seconds"),
            "stage_entered_at": stage_entered_at.isoformat(timespec="seconds"),
            "closed_at": (now - timedelta(days=rng.randint(0, applied_days_ago))).isoformat(timespec="seconds")
            if status != "active" else None,
            "raw_record": raw,
        })

    # Planted duplicates: same person applied at a second branch.
    for j in range(3):
        src = rows[j * 7]
        dup = dict(src)
        dup["applicant_id"] = f"SYN-{n + j + 1:04d}"
        dup["branch"] = BRANCHES[(BRANCHES.index(src["branch"]) + 1) % len(BRANCHES)]
        dup["raw_record"] = dict(src["raw_record"])
        dup["stage"] = "Screening"
        dup["status"] = "active"
        dup["closed_at"] = None
        rows.append(dup)

    return rows
