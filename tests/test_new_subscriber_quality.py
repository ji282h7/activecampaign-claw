"""Tests for new_subscriber_quality.analyze()."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import new_subscriber_quality


def test_engagement_metrics_for_recent_cohort():
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(days=10)).isoformat()
    old = (now - timedelta(days=200)).isoformat()
    data = {
        "contacts": [
            {"id": "1", "cdate": recent, "status": "1"},
            {"id": "2", "cdate": recent, "status": "2"},  # unsub
            {"id": "3", "cdate": recent, "status": "3"},  # bounced
            {"id": "4", "cdate": old, "status": "1"},      # outside window
        ],
        "activities": [
            {"event": "open", "contact": "1"},
            {"event": "click", "contact": "1"},
        ],
    }
    r = new_subscriber_quality.analyze(data, days=30)
    assert r["new_contacts"] == 3
    assert r["opened_at_least_once"] == 1
    assert r["clicked_at_least_once"] == 1
    assert r["unsubscribed"] == 1
    assert r["bounced"] == 1


def test_zero_new_contacts():
    data = {"contacts": [], "activities": []}
    r = new_subscriber_quality.analyze(data, days=30)
    assert r["new_contacts"] == 0
    assert r["open_rate_of_new"] == 0
