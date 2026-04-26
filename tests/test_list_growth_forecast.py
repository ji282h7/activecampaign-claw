"""Tests for list_growth_forecast.analyze()."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import list_growth_forecast


def test_projection_is_linear():
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(days=10)).isoformat()
    old = (now - timedelta(days=200)).isoformat()
    contacts = (
        [{"cdate": recent} for _ in range(30)]  # 30 in last 30d
        + [{"cdate": old} for _ in range(70)]
    )
    r = list_growth_forecast.analyze(contacts, window_days=30, project_days=90)
    assert r["total_contacts"] == 100
    assert r["new_in_window"] == 30
    # daily growth = 30/30 = 1/day; project 90 days → +90
    assert abs(r["daily_growth_estimate"] - 1.0) < 1e-6
    assert r["projected_change"] == 90
    assert r["projected_size"] == 190


def test_zero_window_safe():
    r = list_growth_forecast.analyze([], window_days=30, project_days=90)
    assert r["total_contacts"] == 0
    assert r["new_in_window"] == 0
    assert r["projected_change"] == 0
