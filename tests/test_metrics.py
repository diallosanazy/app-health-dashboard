"""Smoke tests for compute_metrics + the Flask routes."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, compute_metrics, load_feeds


def test_compute_metrics_shape():
    m = compute_metrics(load_feeds())
    assert isinstance(m["failed_logins_24h"], int)
    assert set(m["vuln_counts"]) == {"Critical", "High", "Medium", "Low"}
    assert isinstance(m["open_incidents"], int)
    assert isinstance(m["closed_incidents"], int)
    assert isinstance(m["mttr_hours"], float)
    assert isinstance(m["feed"], list)


def test_dashboard_route():
    client = app.test_client()
    r = client.get("/")
    assert r.status_code == 200
    assert b"SecOps" in r.data


def test_metrics_route():
    client = app.test_client()
    r = client.get("/api/metrics")
    assert r.status_code == 200
    data = r.get_json()
    assert "vuln_counts" in data
