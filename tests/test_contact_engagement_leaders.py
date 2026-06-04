"""Tests for contact_engagement_leaders.analyze().

Fast aggregator: takes a list of normalized engagement events (the shape
ACClient.fetch_engagement_events produces), counts per contact, returns
the top N by clicks / opens / sum.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import contact_engagement_leaders as cel  # noqa: E402


def _ns(by="both", limit=10, window_days=30, max_events=30000):
    return argparse.Namespace(by=by, limit=limit, window_days=window_days,
                              max_events=max_events)


def _ts_iso(days_ago):
    from datetime import timedelta
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def test_ranks_by_clicks_when_by_clicks():
    data = {
        "events": [
            {"event": "click", "contact": "1", "tstamp": _ts_iso(1)},
            {"event": "click", "contact": "1", "tstamp": _ts_iso(2)},
            {"event": "click", "contact": "1", "tstamp": _ts_iso(3)},
            {"event": "open",  "contact": "2", "tstamp": _ts_iso(1)},
            {"event": "open",  "contact": "2", "tstamp": _ts_iso(2)},
            {"event": "click", "contact": "2", "tstamp": _ts_iso(1)},
        ],
    }
    r = cel.analyze(data, _ns(by="clicks", limit=3))
    assert r["top"][0]["contact_id"] == "1"
    assert r["top"][0]["clicks"] == 3
    # contact 2 has 1 click in this window
    assert r["top"][1]["contact_id"] == "2"
    assert r["top"][1]["clicks"] == 1


def test_ranks_by_opens_when_by_opens():
    data = {
        "events": [
            {"event": "click", "contact": "1", "tstamp": _ts_iso(1)},
            {"event": "open",  "contact": "2", "tstamp": _ts_iso(1)},
            {"event": "open",  "contact": "2", "tstamp": _ts_iso(2)},
            {"event": "open",  "contact": "3", "tstamp": _ts_iso(1)},
        ],
    }
    r = cel.analyze(data, _ns(by="opens", limit=3))
    assert r["top"][0]["contact_id"] == "2"
    assert r["top"][0]["opens"] == 2


def test_ranks_by_sum_when_by_both():
    data = {
        "events": [
            {"event": "click", "contact": "1", "tstamp": _ts_iso(1)},
            {"event": "click", "contact": "1", "tstamp": _ts_iso(1)},
            {"event": "open",  "contact": "2", "tstamp": _ts_iso(1)},
            {"event": "open",  "contact": "2", "tstamp": _ts_iso(1)},
            {"event": "open",  "contact": "2", "tstamp": _ts_iso(1)},
            {"event": "click", "contact": "2", "tstamp": _ts_iso(1)},
        ],
    }
    r = cel.analyze(data, _ns(by="both", limit=2))
    # contact 2 has 1 click + 3 opens = 4 total; contact 1 has 2 clicks
    assert r["top"][0]["contact_id"] == "2"
    assert r["top"][0]["total"] == 4


def test_excludes_events_outside_window():
    data = {
        "events": [
            {"event": "click", "contact": "1", "tstamp": _ts_iso(10)},
            {"event": "click", "contact": "1", "tstamp": _ts_iso(100)},  # out of 30d
            {"event": "click", "contact": "1", "tstamp": _ts_iso(200)},  # out
        ],
    }
    r = cel.analyze(data, _ns(by="clicks", window_days=30))
    assert r["top"][0]["clicks"] == 1


def test_empty_window_renders_friendly():
    r = cel.analyze({"events": []}, _ns())
    md = cel.render_markdown(r)
    assert "no engagement events" in md


def test_render_table_shape():
    data = {
        "events": [{"event": "click", "contact": "1", "tstamp": _ts_iso(1)}],
    }
    r = cel.analyze(data, _ns(by="clicks", limit=1))
    r["top"][0]["email"] = "x@x.co"
    r["top"][0]["name"] = "X Y"
    md = cel.render_markdown(r)
    assert "Top 1 contacts by clicks" in md
    assert "X Y" in md
    assert "x@x.co" in md


def test_unknown_contact_id_falls_through_without_crash():
    data = {
        "events": [
            {"event": "click", "contact": None, "tstamp": _ts_iso(1)},
            {"event": "click", "contact": "1", "tstamp": _ts_iso(1)},
        ],
    }
    r = cel.analyze(data, _ns(by="clicks", limit=3))
    # Contact None is ignored
    assert len(r["top"]) == 1
    assert r["top"][0]["contact_id"] == "1"
