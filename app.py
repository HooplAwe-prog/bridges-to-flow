"""Bridges to Flow: ATS -> HRIS handoff prototype (Milestone 3, Prototype v1).

Run locally:  streamlit run app.py
All data is synthetic. See README.md.
"""

from __future__ import annotations

import hmac

import pandas as pd
import streamlit as st

from bridge import __version__, db, mapping, metrics
from bridge.config import (INCOMPLETE_NOTICE_DAYS, MAPPING_CONFIDENCE_THRESHOLD, MIN_GROUP_SIZE,
                           RETENTION_DAYS, ROLES, STAGES, STOP_RULE_THRESHOLD, STOP_RULES)
from bridge.data import REQUIRED_FIELDS, SOURCE_SCHEMAS

st.set_page_config(page_title="Bridges to Flow", page_icon="🌉", layout="wide")
db.init()


# --------------------------------------------------------------------------- #
# Access gate
# --------------------------------------------------------------------------- #
def _secret(key, default=None):
    try:
        return st.secrets.get(key, default)
    except Exception:  # no secrets file: local dev or public demo
        return default


DEMO_MODE = str(_secret("DEMO_MODE", "true")).lower() != "false"


def sign_in() -> None:
    st.title("🌉 Bridges to Flow")
    st.write("A prototype that helps HR move approved applicants from the applicant tracking "
             "system (ATS) into the HR information system (HRIS) without retyping, while a person "
             "approves every transfer.")
    if DEMO_MODE:
        st.info("**Demo mode.** All records are synthetic (invented people, example.com emails). "
                "No passcode is needed: choose a role to see what that role can see.")
    role_label = st.radio("Sign in as", list(ROLES), index=0)
    code = ""
    if not DEMO_MODE:
        code = st.text_input("Role passcode", type="password")
    if st.button("Continue", type="primary"):
        role = ROLES[role_label]
        expected = (_secret("ROLE_PASSCODES", {}) or {}).get(role, "")
        if DEMO_MODE or (expected and hmac.compare_digest(code, expected)):
            st.session_state.role = role
            st.session_state.role_label = role_label
            db.log(role, "sign_in", detail="demo" if DEMO_MODE else "passcode")
            st.rerun()
        else:
            st.error("That passcode didn't match. Ask your administrator for access.")
            db.log(role, "sign_in_failed")


if "role" not in st.session_state:
    sign_in()
    st.stop()

ROLE = st.session_state.role


def log_view(page: str) -> None:
    seen = st.session_state.setdefault("_viewed", set())
    if page not in seen:
        seen.add(page)
        db.log(ROLE, "view", detail=page)


def status_text(row) -> str:
    """Status in words (not color alone) for accessibility."""
    if row["status"] == "dropped":
        return "Dropped"
    if row["status"] == "transferred":
        return "Transferred"
    if row.get("incomplete_notice"):
        return f"⚠ Incomplete {row['days_since_applied']} days"
    if row["stalled"]:
        return f"⚠ Stalled: {row['days_in_stage']} d (target {int(row['sla_days'])} d)"
    return "On track"


def load() -> tuple[list[dict], pd.DataFrame, dict]:
    rows = db.applicants()
    df = metrics.enrich(rows)
    names = {r["applicant_id"]: r["raw_record"] for r in rows}
    return rows, df, names


def person_fields(raw: dict, source: str) -> dict:
    """Pull name/job from a raw record regardless of its source schema."""
    m = SOURCE_SCHEMAS[source]
    return {k: raw.get(m[k], "") for k in ("legal_first_name", "legal_last_name", "personal_email", "job_title")}


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
def page_pipeline():
    log_view("Pipeline board")
    st.header("Pipeline board")
    st.caption("Every active application, its stage, and whether it has waited longer than the target "
               "for that stage. Moving a record forward is always a human action.")
    rows, df, raw = load()
    src = {r["applicant_id"]: r["source_system"] for r in rows}
    p = pd.DataFrame([person_fields(raw[a], src[a]) for a in df["applicant_id"]])
    view = pd.concat([df.reset_index(drop=True), p], axis=1)
    view["name"] = view["legal_first_name"] + " " + view["legal_last_name"]
    view["status_label"] = view.apply(status_text, axis=1)

    c1, c2, c3, c4 = st.columns(4)
    stage_f = c1.multiselect("Stage", STAGES[:-1])
    branch_f = c2.multiselect("Branch", sorted(view["branch"].unique()))
    only_flag = c3.checkbox("Only flagged records")
    show_closed = c4.checkbox("Include dropped / transferred")
    v = view if show_closed else view[view["status"] == "active"]
    if stage_f:
        v = v[v["stage"].isin(stage_f)]
    if branch_f:
        v = v[v["branch"].isin(branch_f)]
    if only_flag:
        v = v[v["status_label"].str.startswith("⚠")]

    st.write(f"Showing **{len(v)}** records.")
    st.dataframe(
        v[["applicant_id", "name", "job_title", "branch", "channel", "stage", "days_in_stage", "status_label"]]
        .rename(columns={"applicant_id": "ID", "name": "Name", "job_title": "Job", "branch": "Branch",
                         "channel": "Channel", "stage": "Stage", "days_in_stage": "Days in stage",
                         "status_label": "Status"}),
        hide_index=True, width="stretch")

    st.subheader("Move a record to the next stage")
    movable = v[(v["status"] == "active") & (v["stage"] != "Ready for HRIS") & (v["application_complete"] == 1)]
    if movable.empty:
        st.write("No records in this view can be moved forward. Incomplete applications must be "
                 "completed first; 'Ready for HRIS' records go to **Review & transfer**.")
        return
    pick = st.selectbox("Record", movable["applicant_id"],
                        format_func=lambda a: f"{a} · {movable.set_index('applicant_id').loc[a, 'name']} · "
                                              f"{movable.set_index('applicant_id').loc[a, 'stage']}")
    cur = movable.set_index("applicant_id").loc[pick, "stage"]
    nxt = STAGES[STAGES.index(cur) + 1]
    if st.button(f"Move {pick} from '{cur}' to '{nxt}'"):
        db.advance(pick, ROLE)
        st.success(f"{pick} moved to {nxt}. This action was logged.")
        st.rerun()


def page_notices():
    log_view("Notices")
    st.header("Notices")
    st.caption("The system flags records; a person decides what happens. Nothing is dropped automatically.")
    rows, df, raw = load()
    src = {r["applicant_id"]: r["source_system"] for r in rows}

    inc = df[df["incomplete_notice"]]
    st.subheader(f"Incomplete applications ({len(inc)})")
    st.write(f"These applications have been incomplete for {INCOMPLETE_NOTICE_DAYS}+ days.")
    for _, r in inc.iterrows():
        pf = person_fields(raw[r["applicant_id"]], src[r["applicant_id"]])
        schema = SOURCE_SCHEMAS[src[r["applicant_id"]]]
        missing = [f for f in REQUIRED_FIELDS if not raw[r["applicant_id"]].get(schema[f])]
        with st.expander(f"{r['applicant_id']} · {pf['legal_first_name']} {pf['legal_last_name']} · "
                         f"incomplete for {r['days_since_applied']} days"):
            st.write(f"This application has not been completed since it was started "
                     f"{r['days_since_applied']} days ago.")
            st.write("Missing: " + ", ".join(f.replace("_", " ") for f in missing))
            c1, c2 = st.columns(2)
            if c1.button("Keep open and remind later", key=f"keep_{r['applicant_id']}"):
                db.keep_open(r["applicant_id"], ROLE)
                st.rerun()
            reason = c2.selectbox("Reason to drop", ["Applicant did not respond", "Applicant withdrew",
                                                     "Position filled", "Other"], key=f"rsn_{r['applicant_id']}")
            if c2.button("Drop application", key=f"drop_{r['applicant_id']}"):
                db.drop(r["applicant_id"], ROLE, reason)
                st.rerun()

    st.subheader(f"Stalled at a stage ({int(df['stalled'].sum())})")
    stalled = df[df["stalled"] & ~df["incomplete_notice"]].sort_values("days_in_stage", ascending=False)
    st.dataframe(stalled[["applicant_id", "stage", "branch", "days_in_stage", "sla_days"]]
                 .rename(columns={"applicant_id": "ID", "stage": "Stage", "branch": "Branch",
                                  "days_in_stage": "Days in stage", "sla_days": "Target days"}),
                 hide_index=True, width="stretch")


def page_transfer():
    log_view("Review & transfer")
    st.header("Review & transfer to HRIS")
    st.caption("The system suggests how each ATS field maps to the HRIS. You confirm or change every "
               "mapping, supply anything missing, and approve. The system never invents a value.")
    rows, df, raw = load()
    ready = [r for r in rows if r["stage"] == "Ready for HRIS" and r["status"] == "active"]
    if not ready:
        st.success("No records are waiting for transfer.")
        return
    by_id = {r["applicant_id"]: r for r in ready}
    pick = st.selectbox("Record ready for HRIS", list(by_id),
                        format_func=lambda a: f"{a} · {by_id[a]['source_system']}")
    rec = by_id[pick]

    st.markdown(f"**Step 1. Check the field mapping** (source: {rec['source_system']})")
    sugg = pd.DataFrame(mapping.suggest_mapping(list(rec["raw_record"])))
    sugg["value"] = sugg["source_field"].map(rec["raw_record"])
    sugg["review"] = sugg["needs_review"].map({True: "⚠ Check this one", False: "Looks right"})
    edited = st.data_editor(
        sugg[["source_field", "value", "suggested_hris_field", "confidence", "review"]],
        column_config={
            "source_field": st.column_config.TextColumn("ATS field", disabled=True),
            "value": st.column_config.TextColumn("Value", disabled=True),
            "suggested_hris_field": st.column_config.SelectboxColumn(
                "HRIS field (you can change it)", options=list(mapping.HRIS_FIELDS), required=True),
            "confidence": st.column_config.NumberColumn("Confidence", format="%.2f", disabled=True),
            "review": st.column_config.TextColumn("Review", disabled=True),
        },
        hide_index=True, width="stretch", key=f"map_{pick}")
    st.caption(f"Suggestions under {MAPPING_CONFIDENCE_THRESHOLD:.2f} confidence are marked for review.")

    confirmed = dict(zip(edited["source_field"], edited["suggested_hris_field"]))
    dupes = [t for t in set(confirmed.values()) if list(confirmed.values()).count(t) > 1]
    if dupes:
        st.error("Two ATS fields point to the same HRIS field: " + ", ".join(dupes) + ". Fix the mapping above.")
        return

    hris = mapping.apply_mapping(rec["raw_record"], confirmed)

    st.markdown("**Step 2. Fix anything flagged**")
    others = [{"applicant_id": r["applicant_id"],
               "email": mapping.apply_mapping(r["raw_record"],
                                              {k: mapping.suggest(k)[0] for k in r["raw_record"]})["personal_email"]}
              for r in rows if r["status"] != "dropped"]
    issues = mapping.validate(hris, others, self_id=pick)
    for f in [i["field"] for i in issues if i["severity"] == "block" and "Missing" in i["message"]]:
        val = st.text_input(f"Enter {f.replace('_', ' ')} (from the applicant or hiring file)", key=f"fix_{pick}_{f}")
        if val.strip():
            hris[f] = val.strip()
    issues = mapping.validate(hris, others, self_id=pick)
    blocks = [i for i in issues if i["severity"] == "block"]
    warns = [i for i in issues if i["severity"] == "warn"]
    if not issues:
        st.success("No problems found.")
    for i in blocks:
        st.error(f"**{i['field'].replace('_', ' ')}:** {i['message']}")
    for i in warns:
        st.warning(f"**{i['field'].replace('_', ' ')}:** {i['message']}")

    st.markdown("**Step 3. Approve**")
    with st.expander("Preview the HRIS record"):
        st.json(hris)
    ok = st.checkbox("I checked each mapping and value, and this applicant is approved to move to the HRIS.",
                     key=f"ok_{pick}")
    if st.button("Approve transfer", type="primary", disabled=bool(blocks) or not ok):
        db.transfer(pick, hris, ROLE)
        st.success(f"{pick} was transferred to the HRIS export. The approval was logged.")
        st.balloons()
    if blocks:
        st.caption("Approve is turned off until every red item is fixed.")


def page_export():
    log_view("HRIS export")
    st.header("HRIS export")
    st.caption("Records a person approved. In a real deployment this would feed the HRIS; here it's a CSV.")
    ex = pd.DataFrame(db.hris_export())
    if ex.empty:
        st.write("Nothing has been transferred in this session yet.")
        return
    st.dataframe(ex, hide_index=True, width="stretch")
    st.download_button("Download CSV", ex.to_csv(index=False), "hris_export_synthetic.csv", "text/csv")
    db.log(ROLE, "view_export", detail=f"{len(ex)} rows")


def page_dashboard():
    log_view("Team dashboard")
    st.header("Team dashboard")
    st.caption(f"Totals only. No individual applicants appear here. Groups with fewer than "
               f"{MIN_GROUP_SIZE} records are hidden.")
    _, df, _ = load()
    k = metrics.kpis(df)
    c = st.columns(5)
    c[0].metric("Active applications", k["active"])
    c[1].metric("Stalled", k["stalled"])
    c[2].metric("Incomplete notices", k["incomplete_notices"])
    c[3].metric("Transferred to HRIS", k["transferred"])
    c[4].metric("Median days in stage", f"{k['median_days_in_stage']:.0f}")

    st.subheader("Where records are waiting")
    s = metrics.stage_summary(df)
    import altair as alt
    long = pd.concat([
        pd.DataFrame({"Stage": s["stage"], "Status": "On track", "Records": s["records"] - s["stalled"]}),
        pd.DataFrame({"Stage": s["stage"], "Status": "Stalled", "Records": s["stalled"]}),
    ])
    chart = (alt.Chart(long).mark_bar()
             .encode(y=alt.Y("Stage:N", sort=STAGES[:-1], title=None),
                     x=alt.X("Records:Q", title="Active records"),
                     color=alt.Color("Status:N", scale=alt.Scale(domain=["On track", "Stalled"],
                                                                 range=["#2b6cb0", "#dd6b20"])),
                     tooltip=["Stage", "Status", "Records"])
             .properties(height=260))
    st.altair_chart(chart, width="stretch")
    st.dataframe(metrics.suppress_small(s.rename(columns={"stage": "Stage"}), "records")
                 .rename(columns={"records": "Records", "stalled": "Stalled",
                                  "median_days_in_stage": "Median days", "sla_days": "Target days"}),
                 hide_index=True, width="stretch")
    st.caption("Chart and table show the same numbers; the table is the accessible version.")

    st.subheader("By branch")
    b, _ = metrics.fairness_check(df, "branch")
    st.dataframe(metrics.suppress_small(b[["branch", "records", "stalled", "median_days_in_stage"]], "records")
                 .rename(columns={"branch": "Branch", "records": "Records", "stalled": "Stalled",
                                  "median_days_in_stage": "Median days"}),
                 hide_index=True, width="stretch")


def page_checks():
    log_view("Fairness & validity")
    st.header("Fairness & validity checks")
    _, df, _ = load()

    st.subheader("1. Fairness spot check: do some groups wait longer?")
    st.write("The tool makes no hiring decisions, so this checks **process delay**: the share of active "
             "records that are on time, by group. Each group's rate is divided by the best group's rate "
             f"(the four-fifths arithmetic). Under {STOP_RULE_THRESHOLD:.2f} is flagged.")
    by = st.radio("Compare by", ["channel", "branch"], horizontal=True,
                  format_func={"channel": "Application channel", "branch": "Branch"}.get)
    g, summ = metrics.fairness_check(df, by)
    st.dataframe(g.rename(columns={by: by.title(), "records": "Records", "stalled": "Stalled",
                                   "median_days_in_stage": "Median days", "on_time_rate": "On-time rate",
                                   "impact_ratio": "Ratio to best", "flag": "Result",
                                   "incomplete_rate": "Missing-field rate"}),
                 hide_index=True, width="stretch")
    if summ["flagged_groups"]:
        st.warning(f"Flagged: {', '.join(summ['flagged_groups'])}. Check whether the missing-field rate "
                   "explains it before changing anything.")
    else:
        st.success("No eligible group is below the threshold.")
    st.caption("Limits: synthetic data with a planted pattern (mobile applications lose fields more often); "
               "operational groups only, because no demographic data is collected; small groups are noisy.")

    st.subheader("2. Validity check: is the field matcher right?")
    v = metrics.validity_check()
    c = st.columns(4)
    c[0].metric("Held-out accuracy", f"{v['held_out']['accuracy']:.0%}", help="Field names the matcher was not tuned on")
    c[1].metric("In-sample accuracy", f"{v['in_sample']['accuracy']:.0%}", help="Not evidence: the synonyms were written for these")
    c[2].metric("Wrong and NOT sent to review", v["held_out"]["unsafe_misses"])
    c[3].metric("Sent to human review", f"{v['held_out']['review_rate']:.0%}")
    if v["stop_rule_triggered"]:
        st.error(f"Stop rule: held-out accuracy is below {v['threshold']:.2f}. Keep every mapping under human "
                 "review and do not reduce oversight until accuracy improves on a new held-out set.")
    t = v["held_out"]["table"].copy()
    t["right"] = t["right"].map({True: "Right", False: "Wrong"})
    t["routed_to_review"] = t["routed_to_review"].map({True: "Yes", False: "No"})
    st.dataframe(t.rename(columns={"source_field": "Field name", "correct": "Correct HRIS field",
                                   "suggested": "Suggested", "confidence": "Confidence",
                                   "right": "Result", "routed_to_review": "Sent to review"}),
                 hide_index=True, width="stretch")
    st.caption("Limits: 12 held-out names, labeled by one person; synthetic field names.")

    st.subheader("3. Stop rules")
    st.write("Each rule names the measure, the threshold that pauses the pilot, who reviews it, and what happens next.")
    st.dataframe(pd.DataFrame(STOP_RULES).rename(columns={
        "measure": "Measure", "pauses_when": "Pauses the pilot when", "reviewed_by": "Reviewed by", "then": "Then"}),
        hide_index=True, width="stretch")


def page_audit():
    log_view("Audit log")
    st.header("Audit log")
    st.caption("Who did what, and when. Stores record IDs only, never names or emails.")
    a = pd.DataFrame(db.audit())
    act = st.multiselect("Action", sorted(a["action"].unique()) if not a.empty else [])
    if act:
        a = a[a["action"].isin(act)]
    st.dataframe(a, hide_index=True, width="stretch")
    st.download_button("Download log (CSV)", a.to_csv(index=False), "audit_log.csv", "text/csv")


def page_retention():
    log_view("Data retention")
    st.header("Data retention & deletion")
    cands = db.purge_candidates()
    st.subheader(f"Closed records older than {RETENTION_DAYS} days ({len(cands)})")
    st.write(", ".join(cands) if cands else "None right now.")
    if cands:
        sure = st.checkbox(f"Permanently delete these {len(cands)} records. This cannot be undone.")
        if st.button("Purge", disabled=not sure):
            n = db.delete(cands, ROLE, f"retention > {RETENTION_DAYS} days")
            st.success(f"Deleted {n} records. Logged.")
            st.rerun()

    st.subheader("Delete one record (deletion request)")
    aid = st.text_input("Applicant ID, e.g. SYN-0042")
    if aid:
        if db.get(aid.strip()):
            sure1 = st.checkbox(f"Permanently delete {aid.strip()}. This cannot be undone.")
            if st.button("Delete record", disabled=not sure1):
                db.delete([aid.strip()], ROLE, "deletion request")
                st.success("Deleted. Logged.")
        else:
            st.write("No record with that ID.")

    st.subheader("Reset demo")
    if st.button("Reload synthetic demo data"):
        db.init(reseed=True)
        db.log(ROLE, "reset_demo")
        st.success("Demo data reloaded.")


def page_about():
    log_view("About & privacy")
    st.header("About this prototype & your privacy")
    st.markdown(f"""
**What it does.** Tracks applications from the ATS through approvals, flags anything waiting too long,
suggests how ATS fields map to the HRIS, and lets HR approve the transfer so no one retypes data.

**What it doesn't do.** It makes **no** hiring decisions. It doesn't rank, score or recommend applicants.
It never fills in missing information or drops an application on its own.

**Data.** Every record here is synthetic. The prototype stores only the application details needed
for the handoff (name, contact, job, dates, location) and an audit log of actions with record IDs only.
No health, disability, demographic, or salary information is collected.

**Who sees what.**
- *Recruiter:* individual records, notices, mapping and transfer.
- *Hiring manager:* totals only; groups under {MIN_GROUP_SIZE} are hidden.
- *Admin:* checks, audit log, retention and deletion.

**Retention.** Closed records are purged after {RETENTION_DAYS} days. Any record can be deleted on request.

**Questions or a problem?** In a real deployment this would list the HR contact for appeals and corrections.

Version {__version__}
""")


PAGES = {
    "recruiter": {"Pipeline board": page_pipeline, "Notices": page_notices,
                  "Review & transfer": page_transfer, "HRIS export": page_export,
                  "About & privacy": page_about},
    "manager": {"Team dashboard": page_dashboard, "About & privacy": page_about},
    "admin": {"Team dashboard": page_dashboard, "Fairness & validity": page_checks,
              "Audit log": page_audit, "Data retention": page_retention, "About & privacy": page_about},
}

with st.sidebar:
    st.markdown("### 🌉 Bridges to Flow")
    st.write(f"Signed in as **{st.session_state.role_label}**")
    if DEMO_MODE:
        st.caption("Demo mode · synthetic data")
    choice = st.radio("Go to", list(PAGES[ROLE]), label_visibility="visible")
    if st.button("Switch role / sign out"):
        db.log(ROLE, "sign_out")
        for k in ("role", "role_label", "_viewed"):
            st.session_state.pop(k, None)
        st.rerun()

PAGES[ROLE][choice]()
