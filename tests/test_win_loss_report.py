"""Tests for win_loss_report.analyze() — Deals-feature-required script."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import win_loss_report


def test_aggregates_won_lost():
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(days=10)).isoformat()
    data = {
        "deals": [
            {"id": "1", "contact": "10", "status": "2", "value": "100000", "cdate": (now - timedelta(days=20)).isoformat(), "edate": recent, "mdate": recent},
            {"id": "2", "contact": "11", "status": "3", "value": "50000", "cdate": (now - timedelta(days=15)).isoformat(), "edate": recent, "mdate": recent},
        ],
        "contact_lists": [
            {"contact": "10", "list": "1", "status": "1"},
            {"contact": "11", "list": "1", "status": "1"},
        ],
        "cutoff": now - timedelta(days=90),
    }
    r = win_loss_report.analyze(data)
    assert r["total_won"] == 1
    assert r["total_lost"] == 1
    assert r["total_won_value_cents"] == 100000
    by_list = {row["list"]: row for row in r["by_source_list"]}
    assert by_list["1"]["won"] == 1
    assert by_list["1"]["lost"] == 1
    assert abs(by_list["1"]["win_rate"] - 0.5) < 1e-6


def test_no_list_fallback():
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(days=10)).isoformat()
    data = {
        "deals": [
            {"id": "1", "contact": "10", "status": "2", "value": "100000", "cdate": recent, "edate": recent, "mdate": recent},
        ],
        "contact_lists": [],
        "cutoff": now - timedelta(days=90),
    }
    r = win_loss_report.analyze(data)
    assert r["by_source_list"][0]["list"] == "(no list)"
