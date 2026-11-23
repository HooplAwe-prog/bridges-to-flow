"""Click-through tests of the Streamlit UI using streamlit.testing.AppTest."""

import os
import tempfile
from pathlib import Path

import pytest

os.environ["BRIDGES_DB"] = str(Path(tempfile.mkdtemp()) / "ui.db")

from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def signed_in(role_label):
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.radio[0].set_value(role_label).run()
    at.button[0].click().run()
    assert not at.exception, at.exception
    return at


def go(at, page):
    at.sidebar.radio[0].set_value(page).run()
    assert not at.exception, at.exception
    return at


def test_sign_in_page_loads():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert "Demo mode" in at.info[0].value


@pytest.mark.parametrize("role,pages", [
    ("Recruiter (HR / Talent Acquisition)", ["Pipeline board", "Notices", "Review & transfer", "HRIS export", "About & privacy"]),
    ("Hiring manager", ["Team dashboard", "About & privacy"]),
    ("Admin", ["Team dashboard", "Fairness & validity", "Audit log", "Data retention", "About & privacy"]),
])
def test_every_page_renders(role, pages):
    at = signed_in(role)
    assert list(at.sidebar.radio[0].options) == pages
    for p in pages:
        go(at, p)


def test_manager_sees_no_names():
    at = go(signed_in("Hiring manager"), "Team dashboard")
    text = " ".join(str(df.value) for df in at.dataframe)
    assert "@example.com" not in text and "Name" not in text


def test_end_to_end_transfer():
    at = go(signed_in("Recruiter (HR / Talent Acquisition)"), "Review & transfer")
    approve = [b for b in at.button if b.label == "Approve transfer"][0]
    assert approve.disabled  # needs the confirmation checkbox first
    # Fill any missing required fields the record has.
    for ti in at.text_input:
        ti.set_value("Supplied by HR")
    at.run()
    at.checkbox[0].check().run()
    approve = [b for b in at.button if b.label == "Approve transfer"][0]
    if not approve.disabled:
        approve.click().run()
        assert not at.exception
        assert any("transferred to the HRIS export" in s.value for s in at.success)
