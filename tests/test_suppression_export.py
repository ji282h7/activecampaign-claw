"""Tests for suppression_export.analyze()."""
from __future__ import annotations

import suppression_export


def test_aggregates_unsubs_bounces_and_codes():
    data = {
        "unsubs": [
            {"id": "1", "email": "a@x.com", "udate": "2026-04-01", "cdate": "2026-01-01"},
        ],
        "bounces": [
            {"id": "2", "email": "b@x.com"},
            {"id": "3", "email": "c@x.com"},
        ],
        "bounce_logs": [
            {"contact": "2", "bounceCode": "550", "tstamp": "2026-04-01"},
            {"contact": "3", "bounceCode": "421", "tstamp": "2026-04-01"},
        ],
    }
    r = suppression_export.analyze(data)
    assert r["unsubscribed_count"] == 1
    assert r["bounced_count"] == 2
    assert "550" in r["bounce_reason_breakdown"]


def test_render_empty():
    data = {"unsubs": [], "bounces": [], "bounce_logs": []}
    r = suppression_export.analyze(data)
    md = suppression_export.render_markdown(r)
    assert "No suppressed contacts" in md
