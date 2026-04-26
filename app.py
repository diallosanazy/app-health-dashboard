"""App Health Dashboard — Flask app.

Reads three CSV feeds from ./data and serves a one-page dashboard with the
metrics a small dev team checks every morning:

    * Errors (last 24h, top failing endpoints and affected users)
    * Open bugs by severity
    * Tickets: open vs closed, mean time to fix (MTTF)

Also exports a flat metrics CSV for Power BI.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
EXPORT = DATA / "metrics_export.csv"

app = Flask(__name__)


# ---------- data loading ----------

def _read_csv(name: str) -> pd.DataFrame:
    path = DATA / name
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, parse_dates=True)


def load_feeds() -> dict[str, pd.DataFrame]:
    """Load the three feeds the dashboard expects."""
    errors = _read_csv("errors.csv")
    bugs = _read_csv("bugs.csv")
    tickets = _read_csv("tickets.csv")

    if not errors.empty:
        errors["timestamp"] = pd.to_datetime(errors["timestamp"], utc=True)
    if not tickets.empty:
        tickets["opened_at"] = pd.to_datetime(tickets["opened_at"], utc=True)
        tickets["closed_at"] = pd.to_datetime(
            tickets["closed_at"], utc=True, errors="coerce"
        )
    return {"errors": errors, "bugs": bugs, "tickets": tickets}


# ---------- metrics ----------

def compute_metrics(feeds: dict[str, pd.DataFrame]) -> dict:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    errors = feeds["errors"]
    bugs = feeds["bugs"]
    tickets = feeds["tickets"]

    # Errors last 24h
    last24 = errors[errors["timestamp"] >= cutoff] if not errors.empty else errors
    errors_24h = int(len(last24))
    top_endpoints = (
        last24.groupby("endpoint").size().sort_values(ascending=False).head(5)
        if not last24.empty
        else pd.Series(dtype=int)
    )
    top_users = (
        last24.groupby("user_id").size().sort_values(ascending=False).head(5)
        if not last24.empty
        else pd.Series(dtype=int)
    )

    # Bugs by severity
    severities = ["Critical", "High", "Medium", "Low"]
    if bugs.empty:
        bug_counts = {s: 0 for s in severities}
    else:
        open_b = bugs[bugs["status"].str.lower() == "open"]
        bug_counts = {s: int((open_b["severity"] == s).sum()) for s in severities}

    # Tickets
    if tickets.empty:
        open_t = closed_t = 0
        mttf_hours = 0.0
    else:
        open_t = int((tickets["closed_at"].isna()).sum())
        closed = tickets.dropna(subset=["closed_at"])
        closed_t = int(len(closed))
        if not closed.empty:
            deltas = (closed["closed_at"] - closed["opened_at"]).dt.total_seconds() / 3600
            mttf_hours = round(float(deltas.mean()), 1)
        else:
            mttf_hours = 0.0

    # Recent events feed (last 20 across errors+tickets)
    feed: list[dict] = []
    if not errors.empty:
        for _, r in errors.sort_values("timestamp", ascending=False).head(20).iterrows():
            feed.append({
                "kind": "error",
                "ts": r["timestamp"].isoformat(),
                "text": f"{r['error_type']} on {r['endpoint']} (user {r['user_id']})",
            })
    if not tickets.empty:
        for _, r in tickets.sort_values("opened_at", ascending=False).head(20).iterrows():
            feed.append({
                "kind": "ticket",
                "ts": r["opened_at"].isoformat(),
                "text": f"Ticket #{r['id']} ({r['severity']}): {r['title']}",
            })
    feed.sort(key=lambda x: x["ts"], reverse=True)
    feed = feed[:20]

    metrics = {
        "errors_24h": errors_24h,
        "top_endpoints": top_endpoints.to_dict(),
        "top_users": top_users.to_dict(),
        "bug_counts": bug_counts,
        "open_tickets": open_t,
        "closed_tickets": closed_t,
        "mttf_hours": mttf_hours,
        "feed": feed,
        "generated_at": now.isoformat(),
    }
    return metrics


def export_for_powerbi(m: dict) -> None:
    """Write a flat CSV that Power BI can pick up."""
    rows = [
        {"metric": "errors_24h", "value": m["errors_24h"]},
        {"metric": "open_tickets", "value": m["open_tickets"]},
        {"metric": "closed_tickets", "value": m["closed_tickets"]},
        {"metric": "mttf_hours", "value": m["mttf_hours"]},
    ]
    for sev, count in m["bug_counts"].items():
        rows.append({"metric": f"bug_{sev.lower()}", "value": count})
    DATA.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(EXPORT, index=False)


# ---------- routes ----------

@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/metrics")
def api_metrics():
    feeds = load_feeds()
    metrics = compute_metrics(feeds)
    export_for_powerbi(metrics)
    return jsonify(metrics)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5001")), debug=True)
