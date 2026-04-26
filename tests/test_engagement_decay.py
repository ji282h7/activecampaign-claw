"""Tests for engagement_decay.analyze()."""
from __future__ import annotations

import engagement_decay


def test_cohort_offsets():
    # contact 1 joined Jan, opened in Jan (M+0) and Feb (M+1)
    data = {
        "contacts": [
            {"id": "1", "cdate": "2026-01-15T10:00:00Z"},
            {"id": "2", "cdate": "2026-01-20T10:00:00Z"},
        ],
        "activities": [
            {"event": "open", "contact": "1", "tstamp": "2026-01-25T10:00:00Z"},
            {"event": "click", "contact": "1", "tstamp": "2026-02-15T10:00:00Z"},
            {"event": "open", "contact": "2", "tstamp": "2026-02-15T10:00:00Z"},
        ],
    }
    r = engagement_decay.analyze(data, months=12)
    assert len(r["cohorts"]) == 1  # only Jan cohort
    cohort = r["cohorts"][0]
    assert cohort["cohort"] == "2026-01"
    assert cohort["size"] == 2
    # M+0: contact 1 open in Jan → 1/2 = 50%
    assert abs(cohort["retention"][0]["pct"] - 50) < 0.01
    # M+1: both contacts had Feb activity
    assert abs(cohort["retention"][1]["pct"] - 100) < 0.01


def test_no_cohorts():
    data = {"contacts": [], "activities": []}
    r = engagement_decay.analyze(data, months=12)
    assert r["cohorts"] == []


def test_render_markdown_includes_sections():
    data = {
        "contacts": [
            {"id": "1", "cdate": "2026-01-15T10:00:00Z"},
            {"id": "2", "cdate": "2026-01-20T10:00:00Z"},
        ],
        "activities": [
            {"event": "open", "contact": "1", "tstamp": "2026-01-25T10:00:00Z"},
            {"event": "open", "contact": "2", "tstamp": "2026-02-15T10:00:00Z"},
        ],
    }
    r = engagement_decay.analyze(data, months=6)
    md = engagement_decay.render_markdown(r)
    assert "# Engagement Decay (Cohort Retention)" in md
    assert "2026-01" in md
