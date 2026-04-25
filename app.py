"""SecOps Single Pane of Glass — Flask app.

Reads three CSV feeds from ./data and serves a one-page dashboard with the
metrics a security operations team checks every morning:

    * Failed logins (last 24h, top source IPs and users)
    * Open vulnerabilities by severity
    * Incidents: open vs closed, mean time to respond (MTTR)

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
    logins = _read_csv("failed_logins.csv")
    vulns = _read_csv("vulnerabilities.csv")
    incidents = _read_csv("incidents.csv")

    if not logins.empty:
        logins["timestamp"] = pd.to_datetime(logins["timestamp"], utc=True)
    if not incidents.empty:
        incidents["opened_at"] = pd.to_datetime(incidents["opened_at"], utc=True)
        incidents["closed_at"] = pd.to_datetime(
            incidents["closed_at"], utc=True, errors="coerce"
        )
    return {"logins": logins, "vulns": vulns, "incidents": incidents}


# ---------- metrics ----------

def compute_metrics(feeds: dict[str, pd.DataFrame]) -> dict:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    logins = feeds["logins"]
    vulns = feeds["vulns"]
    incidents = feeds["incidents"]

    # Failed logins last 24h
    last24 = logins[logins["timestamp"] >= cutoff] if not logins.empty else logins
    failed_logins_24h = int(len(last24))
    top_login_ips = (
        last24.groupby("source_ip").size().sort_values(ascending=False).head(5)
        if not last24.empty
        else pd.Series(dtype=int)
    )
    top_login_users = (
        last24.groupby("username").size().sort_values(ascending=False).head(5)
        if not last24.empty
        else pd.Series(dtype=int)
    )

    # Vulnerabilities by severity
    severities = ["Critical", "High", "Medium", "Low"]
    if vulns.empty:
        vuln_counts = {s: 0 for s in severities}
    else:
        open_v = vulns[vulns["status"].str.lower() == "open"]
        vuln_counts = {s: int((open_v["severity"] == s).sum()) for s in severities}

    # Incidents
    if incidents.empty:
        open_inc = closed_inc = 0
        mttr_hours = 0.0
    else:
        open_inc = int((incidents["closed_at"].isna()).sum())
        closed = incidents.dropna(subset=["closed_at"])
        closed_inc = int(len(closed))
        if not closed.empty:
            deltas = (closed["closed_at"] - closed["opened_at"]).dt.total_seconds() / 3600
            mttr_hours = round(float(deltas.mean()), 1)
        else:
            mttr_hours = 0.0

    # Recent events feed (last 20 across logins+incidents)
    feed: list[dict] = []
    if not logins.empty:
        for _, r in logins.sort_values("timestamp", ascending=False).head(20).iterrows():
            feed.append({
                "kind": "login",
                "ts": r["timestamp"].isoformat(),
                "text": f"Failed login {r['username']} from {r['source_ip']}",
            })
    if not incidents.empty:
        for _, r in incidents.sort_values("opened_at", ascending=False).head(20).iterrows():
            feed.append({
                "kind": "incident",
                "ts": r["opened_at"].isoformat(),
                "text": f"Incident #{r['id']} ({r['severity']}): {r['title']}",
            })
    feed.sort(key=lambda x: x["ts"], reverse=True)
    feed = feed[:20]

    metrics = {
        "failed_logins_24h": failed_logins_24h,
        "top_login_ips": top_login_ips.to_dict(),
        "top_login_users": top_login_users.to_dict(),
        "vuln_counts": vuln_counts,
        "open_incidents": open_inc,
        "closed_incidents": closed_inc,
        "mttr_hours": mttr_hours,
        "feed": feed,
        "generated_at": now.isoformat(),
    }
    return metrics


def export_for_powerbi(m: dict) -> None:
    """Write a flat CSV that Power BI can pick up."""
    rows = [
        {"metric": "failed_logins_24h", "value": m["failed_logins_24h"]},
        {"metric": "open_incidents", "value": m["open_incidents"]},
        {"metric": "closed_incidents", "value": m["closed_incidents"]},
        {"metric": "mttr_hours", "value": m["mttr_hours"]},
    ]
    for sev, count in m["vuln_counts"].items():
        rows.append({"metric": f"vuln_{sev.lower()}", "value": count})
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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
