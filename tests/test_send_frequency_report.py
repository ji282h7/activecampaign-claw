"""Tests for send_frequency_report.analyze()."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import send_frequency_report


def test_distribution_and_fatigue():
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    recent = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    activities = (
        # contact 1: 10 events (fatigued)
        [{"contact": "1", "tstamp": recent} for _ in range(10)]
        # contact 2: 3 events
        + [{"contact": "2", "tstamp": recent} for _ in range(3)]
    )
    data = {
        "activities": activities,
        "contacts": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
        "cutoff": cutoff,
    }
    r = send_frequency_report.analyze(data, window_days=30)
    assert r["contacts_with_sends_in_window"] == 2
    assert r["contacts_with_no_sends"] == 1
    assert r["fatigued_count_gt8"] == 1


def test_old_events_excluded():
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    old = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
    data = {
        "activities": [{"contact": "1", "tstamp": old}],
        "contacts": [{"id": "1"}],
        "cutoff": cutoff,
    }
    r = send_frequency_report.analyze(data, window_days=30)
    assert r["contacts_with_sends_in_window"] == 0


def test_render_markdown_includes_sections():
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    recent = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    data = {
        "activities": [{"contact": "1", "tstamp": recent} for _ in range(3)],
        "contacts": [{"id": "1"}, {"id": "2"}],
        "cutoff": cutoff,
    }
    r = send_frequency_report.analyze(data, window_days=30)
    md = send_frequency_report.render_markdown(r)
    assert "# Send Frequency Report" in md
    assert "## Distribution" in md
