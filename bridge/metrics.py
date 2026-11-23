"""Aggregation, stall detection, fairness check, and validity check."""

from __future__ import annotations

from datetime import datetime
from statistics import median

import pandas as pd

from .config import (INCOMPLETE_NOTICE_DAYS, MAPPING_CONFIDENCE_THRESHOLD, MIN_GROUP_SIZE,
                     STAGE_SLA_DAYS, STAGES, STOP_RULE_THRESHOLD)
from . import mapping
from .holdout import HOLDOUT


def _days_since(iso: str, now: datetime) -> int:
    return (now - datetime.fromisoformat(iso)).days


def enrich(rows: list[dict], now: datetime | None = None) -> pd.DataFrame:
    """Add days_in_stage, sla, stalled, incomplete_notice to each record."""
    now = now or datetime.now()
    df = pd.DataFrame([{k: v for k, v in r.items() if k != "raw_record"} for r in rows])
    if df.empty:
        return df
    df["days_in_stage"] = df["stage_entered_at"].map(lambda s: _days_since(s, now))
    df["days_since_applied"] = df["applied_at"].map(lambda s: _days_since(s, now))
    df["sla_days"] = df["stage"].map(lambda s: STAGE_SLA_DAYS.get(s))
    active = df["status"] == "active"
    df["stalled"] = active & df["sla_days"].notna() & (df["days_in_stage"] > df["sla_days"].fillna(0))
    df["incomplete_notice"] = active & (df["application_complete"] == 0) & \
        (df["days_since_applied"] >= INCOMPLETE_NOTICE_DAYS)
    return df


def stage_summary(df: pd.DataFrame) -> pd.DataFrame:
    act = df[df["status"] == "active"]
    out = (act.groupby("stage")
              .agg(records=("applicant_id", "count"),
                   stalled=("stalled", "sum"),
                   median_days_in_stage=("days_in_stage", "median"))
              .reindex(STAGES[:-1]).fillna(0).reset_index())
    out["records"] = out["records"].astype(int)
    out["stalled"] = out["stalled"].astype(int)
    out["sla_days"] = out["stage"].map(STAGE_SLA_DAYS)
    return out


def suppress_small(table: pd.DataFrame, count_col: str = "records") -> pd.DataFrame:
    """Blank out rows whose group is smaller than MIN_GROUP_SIZE."""
    t = table.copy()
    small = t[count_col] < MIN_GROUP_SIZE
    for c in t.columns:
        if c not in (t.columns[0],):
            t[c] = t[c].astype(object)
            t.loc[small, c] = f"< {MIN_GROUP_SIZE} (hidden)"
    return t


def fairness_check(df: pd.DataFrame, by: str) -> tuple[pd.DataFrame, dict]:
    """Does the process move some groups through on time less often than others?

    Favorable outcome = an active record is NOT stalled. For each group we take
    its on-time rate, then divide by the best group's rate (impact ratio, the
    same arithmetic as the four-fifths rule). A ratio under 0.80 is flagged.

    This checks the *process delay*, not hiring decisions: the tool makes no
    selection decisions. Groups here are operational (branch, application
    channel), not protected characteristics, because the prototype does not
    collect demographic data.
    """
    act = df[df["status"] == "active"]
    g = act.groupby(by).agg(records=("applicant_id", "count"),
                            stalled=("stalled", "sum"),
                            median_days_in_stage=("days_in_stage", "median")).reset_index()
    g["on_time_rate"] = (1 - g["stalled"] / g["records"]).round(3)
    eligible = g[g["records"] >= MIN_GROUP_SIZE]
    best = eligible["on_time_rate"].max() if not eligible.empty else 0
    g["impact_ratio"] = (g["on_time_rate"] / best).round(3) if best else None
    g["flag"] = g.apply(lambda r: "Below 0.80 - review" if r["records"] >= MIN_GROUP_SIZE
                        and r["impact_ratio"] is not None and r["impact_ratio"] < STOP_RULE_THRESHOLD
                        else ("Too few to judge" if r["records"] < MIN_GROUP_SIZE else "OK"), axis=1)
    # Missing-field rate helps explain *why* a group stalls more.
    g["incomplete_rate"] = act.groupby(by)["application_complete"].apply(lambda s: round(1 - s.mean(), 3)).values
    eligible = g[g["records"] >= MIN_GROUP_SIZE]
    summary = {
        "min_ratio": float(eligible["impact_ratio"].min()) if not eligible.empty else None,
        "flagged_groups": g.loc[g["flag"].str.startswith("Below"), by].tolist(),
    }
    return g, summary


def validity_check() -> dict:
    """How often is the matcher's first suggestion right?

    Two sets:
      in-sample  - the three synthetic schemas the synonyms were written for
                   (expected to be high; NOT evidence of generalization)
      held-out   - frozen field names the matcher was not tuned on

    Also reports the number of wrong suggestions that were confident enough
    to skip human review ("unsafe misses"), which is the error that matters
    most for this tool.
    """
    def run(gold: dict[str, str]) -> dict:
        rows = []
        for f, truth in gold.items():
            s, c = mapping.suggest(f)
            rows.append({"source_field": f, "correct": truth, "suggested": s, "confidence": c,
                         "right": s == truth, "routed_to_review": c < MAPPING_CONFIDENCE_THRESHOLD})
        df = pd.DataFrame(rows)
        unsafe = df[(~df["right"]) & (~df["routed_to_review"])]
        return {"table": df, "accuracy": round(df["right"].mean(), 3),
                "n": len(df), "unsafe_misses": len(unsafe),
                "review_rate": round(df["routed_to_review"].mean(), 3)}

    in_sample_gold = {}
    for g in mapping.gold_mappings().values():
        in_sample_gold.update(g)
    ins = run(in_sample_gold)
    hold = run(HOLDOUT)
    return {
        "in_sample": ins,
        "held_out": hold,
        "stop_rule_triggered": hold["accuracy"] < STOP_RULE_THRESHOLD,
        "threshold": STOP_RULE_THRESHOLD,
    }


def kpis(df: pd.DataFrame) -> dict:
    act = df[df["status"] == "active"]
    transferred = df[df["status"] == "transferred"]
    return {
        "active": int(len(act)),
        "stalled": int(act["stalled"].sum()),
        "incomplete_notices": int(df["incomplete_notice"].sum()),
        "transferred": int(len(transferred)),
        "median_days_in_stage": float(median(act["days_in_stage"])) if len(act) else 0.0,
    }
