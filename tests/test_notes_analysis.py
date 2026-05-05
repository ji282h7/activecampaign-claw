"""Tests for notes_analysis.analyze().

Fixture matches /notes shape per AC v3 docs:
  https://developers.activecampaign.com/reference/retrieve-list-of-all-notes
Per-item: id, note, relid, reltype (Deal|Subscriber|Activity), userid,
is_draft, cdate, mdate.
"""
from __future__ import annotations

from datetime import datetime, timezone

import notes_analysis


def _now():
    return datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)


def test_reltype_breakdown_and_user_aggregation():
    data = {
        "notes": [
            {"id": "1", "note": "Met today.", "reltype": "Deal", "relid": "10",
             "userid": "1", "cdate": "2026-05-01", "mdate": "2026-05-01"},
            {"id": "2", "note": "Customer asked.", "reltype": "Subscriber", "relid": "501",
             "userid": "1", "cdate": "2026-05-02", "mdate": "2026-05-02"},
            {"id": "3", "note": "Activity log.", "reltype": "Activity", "relid": "9",
             "userid": "2", "cdate": "2026-05-03", "mdate": "2026-05-03"},
        ],
        "users": [
            {"id": "1", "firstName": "Ada", "lastName": "L", "email": "ada@x.co"},
            {"id": "2", "firstName": "Bert", "lastName": "Z", "email": "b@x.co"},
        ],
    }
    r = notes_analysis.analyze(data, now=_now())
    assert r["total_notes"] == 3
    assert r["by_reltype"] == {"Deal": 1, "Subscriber": 1, "Activity": 1}
    by_user = {u["userid"]: u for u in r["users"]}
    assert by_user["1"]["count"] == 2
    assert by_user["2"]["count"] == 1
    assert by_user["1"]["name"] == "Ada L"


def test_action_item_detection():
    data = {
        "notes": [
            {"id": "1", "note": "Need to follow up next week", "reltype": "Deal",
             "relid": "1", "userid": "1", "cdate": "2026-05-01", "mdate": "2026-05-01"},
            {"id": "2", "note": "Schedule a call with them", "reltype": "Deal",
             "relid": "2", "userid": "1", "cdate": "2026-05-01", "mdate": "2026-05-01"},
            {"id": "3", "note": "Met for coffee, all good", "reltype": "Deal",
             "relid": "3", "userid": "1", "cdate": "2026-05-01", "mdate": "2026-05-01"},
            {"id": "4", "note": "Send the proposal tomorrow", "reltype": "Deal",
             "relid": "4", "userid": "1", "cdate": "2026-05-01", "mdate": "2026-05-01"},
        ],
        "users": [{"id": "1"}],
    }
    r = notes_analysis.analyze(data, now=_now())
    assert r["action_items_count"] == 3  # 1, 2, 4 — not 3
    ids = {a["id"] for a in r["action_items"]}
    assert ids == {"1", "2", "4"}


def test_stale_deals_threshold():
    data = {
        "notes": [
            {"id": "1", "note": "old", "reltype": "Deal", "relid": "100",
             "userid": "1", "cdate": "2026-01-01", "mdate": "2026-01-01"},
            {"id": "2", "note": "fresh", "reltype": "Deal", "relid": "200",
             "userid": "1", "cdate": "2026-05-04", "mdate": "2026-05-04"},
        ],
        "users": [],
    }
    r = notes_analysis.analyze(data, stale_days=30, now=_now())
    stale_ids = {d["deal_id"] for d in r["stale_deals"]}
    assert "100" in stale_ids
    assert "200" not in stale_ids


def test_top_words_strips_stopwords():
    data = {
        "notes": [
            {"id": "1", "note": "the customer needs the proposal urgently",
             "reltype": "Deal", "relid": "1", "userid": "1",
             "cdate": "2026-05-01", "mdate": "2026-05-01"},
        ],
        "users": [],
    }
    r = notes_analysis.analyze(data, now=_now())
    words = dict(r["top_words"])
    assert "the" not in words
    assert "customer" in words
    assert "proposal" in words


def test_render_handles_empty_data():
    r = notes_analysis.analyze({"notes": [], "users": []}, now=_now())
    md = notes_analysis.render_markdown(r)
    assert "Notes Analysis" in md
    assert "Total notes: **0**" in md
