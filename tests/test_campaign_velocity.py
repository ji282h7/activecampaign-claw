"""Tests for campaign_velocity.analyze()."""
from __future__ import annotations

from datetime import datetime, timezone

import campaign_velocity


def test_groups_by_list_and_computes_gaps():
    data = {
        "campaigns": [
            {"sdate": "2026-01-01T10:00:00+00:00", "send_amt": "100", "lists": [{"list": "1"}]},
            {"sdate": "2026-01-08T10:00:00+00:00", "send_amt": "100", "lists": [{"list": "1"}]},
            {"sdate": "2026-01-15T10:00:00+00:00", "send_amt": "100", "lists": [{"list": "1"}]},
        ],
        "lists": [{"id": "1", "name": "Main"}],
        "window_start": datetime(2025, 1, 1, tzinfo=timezone.utc),
    }
    r = campaign_velocity.analyze(data, days=365)
    by_list = {row["list_id"]: row for row in r["by_list"]}
    assert by_list["1"]["sends"] == 3
    assert abs(by_list["1"]["avg_gap_days"] - 7) < 0.1


def test_no_lists_in_window():
    data = {"campaigns": [], "lists": [{"id": "1", "name": "A"}], "window_start": datetime(2025, 1, 1, tzinfo=timezone.utc)}
    r = campaign_velocity.analyze(data, days=90)
    assert r["by_list"] == []
    assert r["total_campaigns"] == 0


def test_render_markdown_includes_sections():
    data = {
        "campaigns": [
            {"sdate": "2026-01-01T10:00:00+00:00", "send_amt": "100", "lists": [{"list": "1"}]},
            {"sdate": "2026-01-08T10:00:00+00:00", "send_amt": "100", "lists": [{"list": "1"}]},
        ],
        "lists": [{"id": "1", "name": "Main"}],
        "window_start": datetime(2025, 1, 1, tzinfo=timezone.utc),
    }
    r = campaign_velocity.analyze(data, days=365)
    md = campaign_velocity.render_markdown(r)
    assert "# Campaign Velocity" in md
    assert "Main" in md
