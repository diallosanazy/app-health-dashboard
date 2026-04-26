"""Tests for the App Health Dashboard."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as appmod  # noqa: E402


def test_compute_metrics_shape_with_empty_feeds():
    """compute_metrics should return all keys even when feeds are empty."""
    feeds = {
        "errors": appmod.pd.DataFrame(),
        "bugs": appmod.pd.DataFrame(),
        "tickets": appmod.pd.DataFrame(),
    }
    m = appmod.compute_metrics(feeds)
    for key in [
        "errors_24h",
        "top_endpoints",
        "top_users",
        "bug_counts",
        "open_tickets",
        "closed_tickets",
        "mttf_hours",
        "feed",
        "generated_at",
    ]:
        assert key in m, f"missing key: {key}"
    assert m["bug_counts"] == {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}


def test_routes_return_200():
    """The dashboard and metrics routes should both return 200."""
    client = appmod.app.test_client()
    assert client.get("/").status_code == 200
    assert client.get("/api/metrics").status_code == 200


def test_load_feeds_with_real_data():
    """Sanity check: load the bundled sample data without exploding."""
    feeds = appmod.load_feeds()
    # All three keys present, even if empty.
    for key in ["errors", "bugs", "tickets"]:
        assert key in feeds


if __name__ == "__main__":
    test_compute_metrics_shape_with_empty_feeds()
    test_routes_return_200()
    test_load_feeds_with_real_data()
    print("OK")
