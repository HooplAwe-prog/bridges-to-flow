"""Central settings. Change values here, then note the change in CHANGELOG.md."""

# Pipeline stages, in order. "Transferred" means the record was approved by a
# human and written to the (synthetic) HRIS export.
STAGES = [
    "Applied",
    "Screening",
    "Interview scheduled",
    "Background check",
    "Hiring manager approval",
    "Finance approval",
    "Ready for HRIS",
    "Transferred",
]

# Service-level targets: days a record may sit in a stage before it is flagged
# as stalled. These are placeholders for the prototype; a real deployment would
# set them with the HR team.
STAGE_SLA_DAYS = {
    "Applied": 7,
    "Screening": 5,
    "Interview scheduled": 10,
    "Background check": 14,
    "Hiring manager approval": 5,
    "Finance approval": 5,
    "Ready for HRIS": 3,
}

# Days an application may stay incomplete before HR is notified. HR decides
# whether to drop it; the system never drops anyone on its own.
INCOMPLETE_NOTICE_DAYS = 14

# Mapping suggestions below this confidence go to a human for review.
MAPPING_CONFIDENCE_THRESHOLD = 0.75

# Stop rule from Milestone 1: if mapping accuracy, or any group's ratio on the
# fairness check, falls below 0.80, the pilot pauses for review.
STOP_RULE_THRESHOLD = 0.80

# Dashboard groups smaller than this are hidden so individuals can't be
# singled out from aggregate views.
MIN_GROUP_SIZE = 5

# Retention: closed records (transferred or dropped) older than this are
# eligible for purge. Matches the 60-day window in Milestone 2.
RETENTION_DAYS = 60

# Measurable stop rules: the measure, the threshold that pauses the pilot, who
# reviews the result, and what happens. Shown in the app (Admin > Fairness &
# validity) and in docs/RUNBOOK.md. Keep the two in step.
STOP_RULES = [
    {"measure": "Held-out mapping accuracy (share of first suggestions that are right)",
     "pauses_when": f"below {STOP_RULE_THRESHOLD:.2f}",
     "reviewed_by": "Admin (pilot owner), weekly; HR lead signs off before oversight is reduced",
     "then": "Keep 100% human review of mappings; re-test on a new held-out set after any fix"},
    {"measure": "Wrong mapping suggestions confident enough to skip review",
     "pauses_when": "1 or more",
     "reviewed_by": "Admin, the same day it is found",
     "then": f"Pause transfers; raise the review threshold above {MAPPING_CONFIDENCE_THRESHOLD:.2f}; log in CHANGELOG"},
    {"measure": "On-time impact ratio for any group of 5+ (branch or channel)",
     "pauses_when": f"below {STOP_RULE_THRESHOLD:.2f} two weekly checks in a row",
     "reviewed_by": "Admin with the HR lead",
     "then": "Check the missing-field rate for that group; fix the cause before expanding the pilot"},
    {"measure": "Real (non-synthetic) personal data found in the app or repository",
     "pauses_when": "any",
     "reviewed_by": "Admin, immediately; notify the instructor/supervisor",
     "then": "Delete it, rotate any exposed secret, record the incident"},
]

ROLES = {
    "Recruiter (HR / Talent Acquisition)": "recruiter",
    "Hiring manager": "manager",
    "Admin": "admin",
}
