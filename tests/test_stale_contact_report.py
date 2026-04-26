"""Tests for stale_contact_report.analyze()."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import stale_contact_report


def test_fresh_stale_no_engagement():
    now = datetime.now(timezone.utc)
    fresh = (now - timedelta(days=10)).isoformat()
    old = (now - timedelta(days=400)).isoformat()
    data = {
        "contacts": [
            {"id": "1", "email": "a@x.com"},
            {"id": "2", "email": "b@x.com"},
            {"id": "3", "email": "c@x.com"},
        ],
        "activities": [
            {"event": "open", "contact": "1", "tstamp": fresh},
            {"event": "click", "contact": "2", "tstamp": old},
        ],
    }
    r = stale_contact_report.analyze(data, window_days=365)
    assert r["fresh_count"] == 1
    assert r["stale_count"] == 1
    assert r["no_engagement_count"] == 1


def test_only_open_click_count_as_engagement():
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(days=10)).isoformat()
    data = {
        "contacts": [{"id": "1", "email": "a@x.com"}],
        "activities": [{"event": "send", "contact": "1", "tstamp": recent}],  # send isn't engagement
    }
    r = stale_contact_report.analyze(data, window_days=365)
    assert r["no_engagement_count"] == 1


def test_render_markdown_includes_sections():
    now = datetime.now(timezone.utc)
    fresh = (now - timedelta(days=10)).isoformat()
    old = (now - timedelta(days=400)).isoformat()
    data = {
        "contacts": [
            {"id": "1", "email": "a@x.com"},
            {"id": "2", "email": "b@x.com"},
            {"id": "3", "email": "c@x.com"},
        ],
        "activities": [
            {"event": "open", "contact": "1", "tstamp": fresh},
            {"event": "click", "contact": "2", "tstamp": old},
        ],
    }
    r = stale_contact_report.analyze(data, window_days=365)
    md = stale_contact_report.render_markdown(r)
    assert "# Stale Contact Report" in md
    assert "Stale" in md
