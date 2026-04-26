"""Tests for list_audit.analyze()."""
from __future__ import annotations

import list_audit


def test_per_list_status_counts():
    data = {
        "lists": [{"id": "1", "name": "Main"}, {"id": "2", "name": "DNC"}],
        "contact_lists": [
            {"contact": "10", "list": "1", "status": "1"},  # active
            {"contact": "11", "list": "1", "status": "1"},  # active
            {"contact": "12", "list": "1", "status": "2"},  # unsub
            {"contact": "13", "list": "1", "status": "3"},  # bounced
            {"contact": "14", "list": "2", "status": "2"},  # unsub
        ],
        "campaigns": [],
    }
    r = list_audit.analyze(data)
    by_id = {row["id"]: row for row in r["lists"]}
    assert by_id["1"]["active"] == 2
    assert by_id["1"]["unsubscribed"] == 1
    assert by_id["1"]["bounced"] == 1
    assert by_id["1"]["total"] == 4


def test_stale_when_no_campaign():
    data = {
        "lists": [{"id": "1", "name": "Main"}],
        "contact_lists": [{"contact": "10", "list": "1", "status": "1"}],
        "campaigns": [],
    }
    r = list_audit.analyze(data)
    assert r["stale_count"] == 1
    assert r["lists"][0]["stale"] is True


def test_render_markdown_includes_sections():
    data = {
        "lists": [{"id": "1", "name": "Main"}],
        "contact_lists": [{"contact": "10", "list": "1", "status": "1"}],
        "campaigns": [],
    }
    r = list_audit.analyze(data)
    md = list_audit.render_markdown(r)
    assert "# List Audit" in md
    assert "Main" in md
