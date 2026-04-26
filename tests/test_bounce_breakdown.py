"""Tests for bounce_breakdown.analyze()."""
from __future__ import annotations

import bounce_breakdown


def test_groups_by_code_and_domain():
    bounces = [
        {"bounceCode": "550", "email": "a@gmail.com", "campaignid": "1", "tstamp": "2026-04-01"},
        {"bounceCode": "550", "email": "b@gmail.com", "campaignid": "1", "tstamp": "2026-04-01"},
        {"bounceCode": "421", "email": "c@yahoo.com", "campaignid": "1", "tstamp": "2026-04-02"},
    ]
    r = bounce_breakdown.analyze(bounces)
    assert r["total"] == 3
    assert r["by_code"]["550"] == 2
    assert r["by_code"]["421"] == 1
    assert r["by_domain"]["gmail.com"] == 2


def test_unknown_code_default():
    bounces = [{"email": "a@b.com", "campaignid": "1"}]
    r = bounce_breakdown.analyze(bounces)
    assert "unknown" in r["by_code"]


def test_render():
    r = bounce_breakdown.analyze([])
    md = bounce_breakdown.render_markdown(r)
    assert "Bounce Breakdown" in md
