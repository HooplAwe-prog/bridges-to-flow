"""Held-out field names for the validity check.

FROZEN on 2026-11-22. These names were written without looking at the
matcher's synonym list, and the synonym list must NOT be edited to make these
pass. Tuning against this set would make the accuracy number meaningless.

If you add synonyms, measure on a NEW held-out set (ideally one a peer writes
and labels) and record both numbers in CHANGELOG.md.

Labels were assigned by the developer. Limitation: one labeler, no
inter-rater check. A peer relabeling these is a recommended next step.
"""

HOLDOUT = {
    "CandFirst": "legal_first_name",
    "CandLast": "legal_last_name",
    "GivenNm": "legal_first_name",
    "ContactEmail": "personal_email",
    "CellNumber": "phone",
    "Hm_Tel": "phone",
    "PostingID": "requisition_id",
    "JobName": "job_title",
    "BusinessUnit": "department",
    "HireDt": "start_date",
    "WorkSite": "work_location",
    "FT_PT": "employment_type",
}
