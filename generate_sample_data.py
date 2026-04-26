"""Generate fresh sample data for the dashboard.

Run with `python3 generate_sample_data.py` to overwrite the CSVs in ./data
with new realistic-looking errors/bugs/tickets centered on "right now". This
is what keeps the dashboard from going stale on the demo.
"""
from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

random.seed(42)

DATA = Path(__file__).resolve().parent / "data"
DATA.mkdir(exist_ok=True)

NOW = datetime.now(timezone.utc).replace(microsecond=0)


def _ts_within_24h() -> str:
    minutes = random.randint(0, 60 * 24)
    return (NOW - timedelta(minutes=minutes)).isoformat()


def _ts_within_30d() -> datetime:
    minutes = random.randint(0, 60 * 24 * 30)
    return (NOW - timedelta(minutes=minutes)).replace(microsecond=0)


# -------------------- errors.csv --------------------

ENDPOINTS = [
    "/api/login", "/api/checkout", "/api/profile", "/api/search",
    "/api/upload", "/api/messages", "/api/notifications",
]
ERROR_TYPES = [
    "TimeoutError", "ValidationError", "PermissionDenied",
    "DatabaseError", "NullReferenceException", "RateLimitExceeded",
]
USERS = ["u_1042", "u_2087", "u_3331", "u_4408", "u_5519", "u_6670", "u_7782"]

with (DATA / "errors.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["timestamp", "endpoint", "user_id", "error_type"])
    for _ in range(130):
        w.writerow([
            _ts_within_24h(),
            random.choice(ENDPOINTS),
            random.choice(USERS),
            random.choice(ERROR_TYPES),
        ])

# -------------------- bugs.csv ---------------------

with (DATA / "bugs.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "component", "severity", "title", "status", "first_seen"])
    severities = ["Critical"] * 0 + ["High"] * 15 + ["Medium"] * 28 + ["Low"] * 82
    components = ["web", "api", "auth", "billing", "search", "notifications"]
    bug_titles = [
        "Layout overflow on mobile",
        "Slow query on /api/search",
        "Missing aria-label on form input",
        "Stale cache after deploy",
        "Crash on logout while uploading",
        "Date picker off-by-one in EST",
    ]
    for i, sev in enumerate(severities, start=1):
        w.writerow([
            f"BUG-{i:04d}",
            random.choice(components),
            sev,
            random.choice(bug_titles),
            "open",
            _ts_within_30d().isoformat(),
        ])

# -------------------- tickets.csv ------------------

TICKET_TITLES = [
    "Checkout latency above SLO",
    "Login failure rate spike",
    "Image upload timing out",
    "Notifications not delivering",
    "Profile page returns 500 for some users",
    "Search results showing duplicates",
]

with (DATA / "tickets.csv").open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "title", "severity", "opened_at", "closed_at"])
    for i in range(1, 31):
        opened = _ts_within_30d()
        closed = ""
        # ~83% closed, average ~1.5 days to fix
        if random.random() < 0.83:
            closed_dt = opened + timedelta(hours=random.randint(2, 96))
            if closed_dt > NOW:
                closed_dt = NOW
            closed = closed_dt.isoformat()
        w.writerow([
            f"TKT-{i:04d}",
            random.choice(TICKET_TITLES),
            random.choice(["Low", "Medium", "High", "Critical"]),
            opened.isoformat(),
            closed,
        ])

print(f"Wrote {DATA}/errors.csv, bugs.csv, tickets.csv")
