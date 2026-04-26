"""Tests for send_time_optimizer.analyze()."""
from __future__ import annotations

import send_time_optimizer


def test_best_hours_and_dow():
    # bias open events to Wed (weekday=2) at 14:00 UTC
    activities = [
        {"event": "open", "tstamp": "2026-04-01T14:00:00+00:00"} for _ in range(10)
    ] + [
        {"event": "open", "tstamp": "2026-04-02T15:00:00+00:00"} for _ in range(5)
    ] + [
        {"event": "click", "tstamp": "2026-04-04T18:00:00+00:00"} for _ in range(2)
    ]
    r = send_time_optimizer.analyze(activities)
    assert r["open_events"] == 17
    # 14:00 should be top hour
    assert r["best_hours_utc"][0] == 14


def test_empty_activities_uses_baseline_in_render():
    r = send_time_optimizer.analyze([])
    md = send_time_optimizer.render_markdown(r, {"best_send_window_utc": ["14:00"], "best_send_dow": ["Wed"]})
    assert "calibration baseline" in md
    assert "14:00" in md
