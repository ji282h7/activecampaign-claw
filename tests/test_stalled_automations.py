"""Tests for stalled_automations.analyze()."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import stalled_automations


def test_stalled_threshold():
    now = datetime.now(timezone.utc)
    fresh = (now - timedelta(days=2)).isoformat()
    stale = (now - timedelta(days=30)).isoformat()
    data = {
        "automations": [{"id": "1", "name": "Welcome"}],
        "contact_automations": [
            {"contact": "100", "automation": "1", "status": "1", "lastblock": "5", "lastdate": stale},
            {"contact": "200", "automation": "1", "status": "1", "lastblock": "5", "lastdate": fresh},  # not stalled
            {"contact": "300", "automation": "1", "status": "2", "lastblock": "5", "lastdate": stale},  # completed — not stalled
        ],
    }
    r = stalled_automations.analyze(data, min_days=14)
    assert r["stalled_count"] == 1
    assert r["stalled"][0]["contact"] == "100"


def test_no_stalled():
    data = {"automations": [], "contact_automations": []}
    r = stalled_automations.analyze(data, min_days=14)
    assert r["stalled_count"] == 0


def test_render_markdown_includes_sections():
    now = datetime.now(timezone.utc)
    stale = (now - timedelta(days=30)).isoformat()
    data = {
        "automations": [{"id": "1", "name": "Welcome"}],
        "contact_automations": [
            {"contact": "100", "automation": "1", "status": "1", "lastblock": "5", "lastdate": stale},
        ],
    }
    r = stalled_automations.analyze(data, min_days=14)
    md = stalled_automations.render_markdown(r)
    assert "# Stalled Automation Enrollments" in md
    assert "Stalled contacts" in md
