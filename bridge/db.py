"""SQLite storage and audit log.

Tables
  applicants  one row per synthetic application (raw ATS record kept as JSON)
  hris_export records a human approved for transfer, in HRIS field names
  audit_log   timestamped events: who (role), what, which record

The audit log stores applicant IDs only, never names or emails, so the log
can be kept longer than the records themselves.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from . import data
from .config import RETENTION_DAYS, STAGES

DEFAULT_PATH = Path(os.environ.get("BRIDGES_DB", Path(__file__).resolve().parent.parent / "data" / "bridges.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS applicants (
    applicant_id TEXT PRIMARY KEY,
    source_system TEXT NOT NULL,
    branch TEXT NOT NULL,
    channel TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active','dropped','transferred')),
    application_complete INTEGER NOT NULL,
    applied_at TEXT NOT NULL,
    stage_entered_at TEXT NOT NULL,
    closed_at TEXT,
    raw_record TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS hris_export (
    applicant_id TEXT PRIMARY KEY,
    approved_by_role TEXT NOT NULL,
    approved_at TEXT NOT NULL,
    record TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    role TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT,
    detail TEXT
);
"""


@contextmanager
def connect(path: Path | str = DEFAULT_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init(path: Path | str = DEFAULT_PATH, reseed: bool = False) -> None:
    """Create tables; seed synthetic data if empty (or if reseed=True)."""
    with connect(path) as c:
        c.executescript(SCHEMA)
        if reseed:
            c.executescript("DELETE FROM applicants; DELETE FROM hris_export; DELETE FROM audit_log;")
        if c.execute("SELECT COUNT(*) FROM applicants").fetchone()[0] == 0:
            for r in data.generate():
                c.execute(
                    "INSERT INTO applicants VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (r["applicant_id"], r["source_system"], r["branch"], r["channel"],
                     r["stage"], r["status"], r["application_complete"], r["applied_at"],
                     r["stage_entered_at"], r["closed_at"], json.dumps(r["raw_record"])),
                )
            _log(c, "system", "seed", None, "Loaded synthetic demo data")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _log(c: sqlite3.Connection, role: str, action: str, target: str | None, detail: str = "") -> None:
    c.execute("INSERT INTO audit_log (ts, role, action, target, detail) VALUES (?,?,?,?,?)",
              (_now(), role, action, target, detail))


def log(role: str, action: str, target: str | None = None, detail: str = "", path=DEFAULT_PATH) -> None:
    with connect(path) as c:
        _log(c, role, action, target, detail)


def applicants(path=DEFAULT_PATH) -> list[dict]:
    with connect(path) as c:
        rows = c.execute("SELECT * FROM applicants ORDER BY applicant_id").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["raw_record"] = json.loads(d["raw_record"])
        out.append(d)
    return out


def get(applicant_id: str, path=DEFAULT_PATH) -> dict | None:
    with connect(path) as c:
        r = c.execute("SELECT * FROM applicants WHERE applicant_id=?", (applicant_id,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["raw_record"] = json.loads(d["raw_record"])
    return d


def advance(applicant_id: str, role: str, path=DEFAULT_PATH) -> str:
    """Move a record one stage forward (a human action). Returns the new stage."""
    with connect(path) as c:
        stage = c.execute("SELECT stage FROM applicants WHERE applicant_id=?", (applicant_id,)).fetchone()[0]
        i = STAGES.index(stage)
        if i >= STAGES.index("Ready for HRIS"):
            raise ValueError("Use the HRIS transfer step to move past 'Ready for HRIS'.")
        new = STAGES[i + 1]
        c.execute("UPDATE applicants SET stage=?, stage_entered_at=? WHERE applicant_id=?",
                  (new, _now(), applicant_id))
        _log(c, role, "advance_stage", applicant_id, f"{stage} -> {new}")
    return new


def drop(applicant_id: str, role: str, reason: str, path=DEFAULT_PATH) -> None:
    with connect(path) as c:
        c.execute("UPDATE applicants SET status='dropped', closed_at=? WHERE applicant_id=?",
                  (_now(), applicant_id))
        _log(c, role, "drop_application", applicant_id, reason)


def keep_open(applicant_id: str, role: str, path=DEFAULT_PATH) -> None:
    """HR reviewed a stall notice and chose to keep the application open."""
    with connect(path) as c:
        c.execute("UPDATE applicants SET stage_entered_at=? WHERE applicant_id=?", (_now(), applicant_id))
        _log(c, role, "keep_open", applicant_id, "Reviewed notice; timer reset")


def transfer(applicant_id: str, hris_record: dict, role: str, path=DEFAULT_PATH) -> None:
    """Write a human-approved record to the HRIS export and close it."""
    with connect(path) as c:
        c.execute("INSERT OR REPLACE INTO hris_export VALUES (?,?,?,?)",
                  (applicant_id, role, _now(), json.dumps(hris_record)))
        c.execute("UPDATE applicants SET stage='Transferred', status='transferred', "
                  "stage_entered_at=?, closed_at=? WHERE applicant_id=?",
                  (_now(), _now(), applicant_id))
        _log(c, role, "approve_transfer", applicant_id, "Human-approved ATS -> HRIS transfer")


def hris_export(path=DEFAULT_PATH) -> list[dict]:
    with connect(path) as c:
        rows = c.execute("SELECT * FROM hris_export ORDER BY approved_at DESC").fetchall()
    return [{**json.loads(r["record"]), "applicant_id": r["applicant_id"],
             "approved_by_role": r["approved_by_role"], "approved_at": r["approved_at"]} for r in rows]


def audit(limit: int = 500, path=DEFAULT_PATH) -> list[dict]:
    with connect(path) as c:
        return [dict(r) for r in c.execute(
            "SELECT ts, role, action, target, detail FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))]


def purge_candidates(now: datetime | None = None, path=DEFAULT_PATH) -> list[str]:
    now = now or datetime.now()
    cutoff = (now - timedelta(days=RETENTION_DAYS)).isoformat(timespec="seconds")
    with connect(path) as c:
        return [r[0] for r in c.execute(
            "SELECT applicant_id FROM applicants WHERE status != 'active' AND closed_at IS NOT NULL "
            "AND closed_at < ?", (cutoff,))]


def delete(applicant_ids: list[str], role: str, reason: str, path=DEFAULT_PATH) -> int:
    """Hard-delete records (retention purge or a deletion request)."""
    with connect(path) as c:
        n = 0
        for aid in applicant_ids:
            n += c.execute("DELETE FROM applicants WHERE applicant_id=?", (aid,)).rowcount
            c.execute("DELETE FROM hris_export WHERE applicant_id=?", (aid,))
        _log(c, role, "delete_records", ",".join(applicant_ids)[:500], f"{n} deleted; {reason}")
    return n
