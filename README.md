# SecOps Single Pane of Glass

![Dashboard preview](docs/screenshot.svg)

A lightweight security operations dashboard built with **Python (Flask) + Chart.js**.
It pulls metrics from CSV/JSON log feeds and renders them on one page so a security
team can see the state of the program at a glance — the "single pane of glass" view
incident response teams ask for.

The same data is exported to a flat CSV so it can be consumed by **Power BI** if you
want a heavier BI surface on top.

[![CI](https://github.com/diallosanazy/secops-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/diallosanazy/secops-dashboard/actions/workflows/ci.yml)

## What it shows

- **Failed logins** — count over the last 24h, grouped by source IP and user.
- **Open vulnerabilities** — count by severity (Critical / High / Medium / Low).
- **Incidents** — open vs. closed, and **mean time to respond (MTTR)** in hours.
- **Recent events feed** — the latest 20 raw events for context.

## Stack

- Python 3.10+, Flask, pandas
- Chart.js (loaded from CDN, no build step)
- Optional: Power BI Desktop reads `data/metrics_export.csv`

## Quickstart

```bash
git clone https://github.com/diallosanazy/secops-dashboard.git
cd secops-dashboard
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open <http://localhost:5000>.

The repo ships with synthetic sample data under `data/` so it works out of the box.
Drop your own `failed_logins.csv`, `vulnerabilities.csv`, and `incidents.csv` in
that folder — same column names — and refresh.

## Power BI

`data/metrics_export.csv` is rewritten on every page load. Open Power BI Desktop →
*Get Data → Text/CSV* → point at that file → build whatever visuals you like. Set a
scheduled refresh against the same folder for live dashboards.

## File layout

```
secops-dashboard/
├── app.py                 # Flask app + metric calculations
├── requirements.txt
├── data/
│   ├── failed_logins.csv
│   ├── vulnerabilities.csv
│   └── incidents.csv
└── templates/
    └── dashboard.html     # Chart.js dashboard UI
```

## Roadmap

- Pull from a SIEM (Splunk / Sentinel / Elastic) instead of CSV.
- Auth in front of the dashboard (Flask-Login + SSO).
- Slack / email alerts when MTTR exceeds a threshold.

## License

MIT
