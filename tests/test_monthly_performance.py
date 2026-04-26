"""Tests for monthly_performance.analyze()."""
from __future__ import annotations

import monthly_performance


def test_groups_by_month():
    campaigns = [
        {"sdate": "2026-01-15T10:00:00Z", "send_amt": "100", "uniqueopens": "20", "uniquelinkclicks": "5", "unsubscribes": "1", "bounces": "1", "opens": "30", "linkclicks": "8"},
        {"sdate": "2026-01-20T10:00:00Z", "send_amt": "100", "uniqueopens": "30", "uniquelinkclicks": "5", "unsubscribes": "0", "bounces": "1", "opens": "40", "linkclicks": "10"},
        {"sdate": "2026-02-10T10:00:00Z", "send_amt": "200", "uniqueopens": "50", "uniquelinkclicks": "10", "unsubscribes": "2", "bounces": "0", "opens": "60", "linkclicks": "15"},
    ]
    r = monthly_performance.analyze(campaigns)
    by_month = {m["month"]: m for m in r["months"]}
    assert "2026-01" in by_month and "2026-02" in by_month
    jan = by_month["2026-01"]
    assert jan["sends"] == 2
    assert jan["recipients"] == 200
    assert abs(jan["open_rate"] - 0.25) < 1e-6


def test_excludes_no_sdate():
    campaigns = [
        {"sdate": None, "send_amt": "100", "uniqueopens": "20"},
        {"send_amt": "100", "uniqueopens": "20"},
    ]
    r = monthly_performance.analyze(campaigns)
    assert r["months"] == []
