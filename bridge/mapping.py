"""AI-assisted field mapping from an ATS export to the HRIS schema.

How it works (see MODEL_CARD.md):
  1. Normalize each source field name (lowercase, split into word tokens,
     expand common abbreviations).
  2. Score it against every HRIS field's known synonyms using a blend of
     character similarity (difflib) and token overlap.
  3. Suggest the best match with a confidence score. Suggestions under the
     confidence threshold are marked "needs review".

The matcher only proposes. A recruiter confirms every mapping before
anything is written to the HRIS export, and the system never invents a value
for a missing field.
"""

from __future__ import annotations

import re
from datetime import datetime
from difflib import SequenceMatcher

from .config import MAPPING_CONFIDENCE_THRESHOLD
from .data import REQUIRED_FIELDS, SOURCE_SCHEMAS

HRIS_FIELDS = {
    "legal_first_name": ["legal first name", "first name", "given name", "candidate first name", "forename"],
    "legal_last_name": ["legal last name", "last name", "surname", "family name", "candidate last name"],
    "personal_email": ["personal email", "email", "email address", "e mail"],
    "phone": ["phone", "phone number", "primary phone", "mobile phone", "telephone"],
    "requisition_id": ["requisition id", "job requisition id", "requisition number", "req id"],
    "job_title": ["job title", "position", "job profile", "title", "role"],
    "department": ["department", "supervisory organization", "org unit", "division", "team"],
    "start_date": ["start date", "proposed start date", "anticipated start", "hire date", "begin date"],
    "work_location": ["work location", "location", "site", "office", "branch"],
    "employment_type": ["employment type", "worker type", "employee class", "status", "fte type"],
}

# Abbreviations commonly seen in legacy exports.
ABBREVIATIONS = {
    "fn": "first name", "fname": "first name", "ln": "last name", "lname": "last name",
    "eml": "email", "ph": "phone", "no": "number", "req": "requisition", "ttl": "title",
    "org": "organization", "dt": "date", "loc": "location", "emp": "employee",
    "cls": "class", "dept": "department", "#": "number", "id": "id",
}


def normalize(name: str) -> str:
    name = name.replace("#", " number ")
    tokens = re.findall(r"[a-zA-Z]+", re.sub(r"([a-z])([A-Z])", r"\1 \2", name).lower())
    expanded = []
    for t in tokens:
        expanded.extend(ABBREVIATIONS.get(t, t).split())
    return " ".join(expanded)


def _score(a: str, b: str) -> float:
    char = SequenceMatcher(None, a, b).ratio()
    ta, tb = set(a.split()), set(b.split())
    token = len(ta & tb) / len(ta | tb) if ta | tb else 0.0
    return round(max(char, 0.5 * char + 0.5 * token), 3)


def suggest(source_field: str) -> tuple[str, float]:
    """Best HRIS field for one source field name, with confidence 0-1."""
    norm = normalize(source_field)
    best, best_score = "", 0.0
    for field, synonyms in HRIS_FIELDS.items():
        s = max(_score(norm, normalize(syn)) for syn in synonyms + [field])
        if s > best_score:
            best, best_score = field, s
    return best, best_score


def suggest_mapping(source_fields: list[str]) -> list[dict]:
    rows = []
    for f in source_fields:
        target, conf = suggest(f)
        rows.append({
            "source_field": f,
            "suggested_hris_field": target,
            "confidence": conf,
            "needs_review": conf < MAPPING_CONFIDENCE_THRESHOLD,
        })
    return rows


def apply_mapping(raw: dict, mapping: dict[str, str]) -> dict:
    """mapping: source_field -> hris_field (as confirmed by a human)."""
    out = {f: "" for f in HRIS_FIELDS}
    for src, value in raw.items():
        tgt = mapping.get(src)
        if tgt:
            out[tgt] = value
    return out


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate(hris_record: dict, others: list[dict] | None = None, self_id: str | None = None) -> list[dict]:
    """Return a list of issues. Each issue: field, severity, message.

    severity "block" = transfer cannot be approved until a human fixes it.
    severity "warn"  = human should look, but may approve.
    """
    issues = []
    for f in REQUIRED_FIELDS:
        if not str(hris_record.get(f, "")).strip():
            issues.append({"field": f, "severity": "block",
                           "message": "Missing. HR must supply this value; the system will not fill it in."})
    email = hris_record.get("personal_email", "")
    if email and not EMAIL_RE.match(email):
        issues.append({"field": "personal_email", "severity": "block", "message": "Not a valid email format."})
    sd = hris_record.get("start_date", "")
    if sd:
        try:
            datetime.strptime(sd, "%Y-%m-%d")
        except ValueError:
            issues.append({"field": "start_date", "severity": "block", "message": "Date must be YYYY-MM-DD."})
    if email and others:
        dups = [o["applicant_id"] for o in others
                if o["applicant_id"] != self_id and o.get("email", "").lower() == email.lower()]
        if dups:
            issues.append({"field": "personal_email", "severity": "warn",
                           "message": f"Possible duplicate applicant: {', '.join(dups)}. Confirm with the other branch."})
    return issues


def gold_mappings() -> dict[str, dict[str, str]]:
    """Hand-labeled correct answers for each synthetic source schema.

    source_system -> {source_field: correct_hris_field}. Used by the validity
    check to measure how often the matcher's first suggestion is right.
    """
    return {src: {v: k for k, v in fields.items()} for src, fields in SOURCE_SCHEMAS.items()}
