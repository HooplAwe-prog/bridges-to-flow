"""Unit tests for the core logic. Run: pytest -q"""

import os
import tempfile
from pathlib import Path

import pytest

from bridge import data, db, mapping, metrics
from bridge.config import MIN_GROUP_SIZE


@pytest.fixture
def dbpath():
    d = tempfile.mkdtemp()
    p = Path(d) / "t.db"
    db.init(p)
    return p


def test_synthetic_data_is_synthetic():
    rows = data.generate()
    assert len(rows) == 123
    for r in rows:
        emails = [v for v in r["raw_record"].values() if "@" in str(v)]
        assert all(e.endswith("@example.com") for e in emails)
        assert r["applicant_id"].startswith("SYN-")


def test_generation_is_reproducible():
    from datetime import datetime
    now = datetime(2026, 11, 22)
    assert data.generate(now=now) == data.generate(now=now)


def test_mapping_in_sample_and_threshold_routing():
    for src, gold in mapping.gold_mappings().items():
        for f, truth in gold.items():
            assert mapping.suggest(f)[0] == truth, (src, f)


def test_validity_reports_unsafe_misses():
    v = metrics.validity_check()
    assert v["held_out"]["n"] == 12
    # Every wrong held-out suggestion must have been routed to a human.
    assert v["held_out"]["unsafe_misses"] == 0


def test_validate_never_fills_missing():
    rec = {f: "x" for f in mapping.HRIS_FIELDS}
    rec.update(personal_email="a@example.com", start_date="2026-12-01", department="")
    issues = mapping.validate(rec)
    assert any(i["field"] == "department" and i["severity"] == "block" for i in issues)
    assert rec["department"] == ""


def test_validate_flags_duplicates():
    rec = {f: "x" for f in mapping.HRIS_FIELDS}
    rec.update(personal_email="dup@example.com", start_date="2026-12-01")
    issues = mapping.validate(rec, [{"applicant_id": "SYN-9", "email": "DUP@example.com"}], self_id="SYN-1")
    assert any(i["severity"] == "warn" for i in issues)


def test_bad_date_blocks():
    rec = {f: "x" for f in mapping.HRIS_FIELDS}
    rec.update(personal_email="a@example.com", start_date="12/01/2026")
    assert any(i["field"] == "start_date" for i in mapping.validate(rec))


def test_transfer_logs_and_closes(dbpath):
    ready = [r for r in db.applicants(dbpath) if r["stage"] == "Ready for HRIS" and r["status"] == "active"]
    assert ready
    aid = ready[0]["applicant_id"]
    db.transfer(aid, {"legal_first_name": "x"}, "recruiter", path=dbpath)
    assert db.get(aid, dbpath)["status"] == "transferred"
    assert any(a["action"] == "approve_transfer" and a["target"] == aid for a in db.audit(path=dbpath))


def test_audit_log_has_no_names(dbpath):
    r = db.applicants(dbpath)[0]
    db.drop(r["applicant_id"], "recruiter", "test", path=dbpath)
    text = str(db.audit(path=dbpath))
    assert "@example.com" not in text


def test_advance_refuses_to_skip_human_transfer(dbpath):
    ready = [r for r in db.applicants(dbpath) if r["stage"] == "Ready for HRIS"]
    with pytest.raises(ValueError):
        db.advance(ready[0]["applicant_id"], "recruiter", path=dbpath)


def test_delete_and_purge(dbpath):
    aid = db.applicants(dbpath)[0]["applicant_id"]
    assert db.delete([aid], "admin", "test", path=dbpath) == 1
    assert db.get(aid, dbpath) is None
    assert isinstance(db.purge_candidates(path=dbpath), list)


def test_small_groups_suppressed():
    import pandas as pd
    t = pd.DataFrame({"g": ["a", "b"], "records": [MIN_GROUP_SIZE - 1, MIN_GROUP_SIZE + 3], "stalled": [1, 2]})
    s = metrics.suppress_small(t)
    assert "hidden" in str(s.loc[0, "stalled"])
    assert s.loc[1, "stalled"] == 2


def test_fairness_check_finds_planted_pattern():
    df = metrics.enrich(data.generate())
    g, summ = metrics.fairness_check(df, "channel")
    mob = g.set_index("channel").loc["Mobile app"]
    others = g[g["channel"] != "Mobile app"]["incomplete_rate"].max()
    assert mob["incomplete_rate"] > others
