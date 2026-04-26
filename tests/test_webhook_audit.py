"""Tests for webhook_audit.analyze() with skip_probe=True."""
from __future__ import annotations

import webhook_audit


def test_inventory_no_probe():
    webhooks = [
        {"id": "1", "name": "WH-A", "url": "https://example.com/wh", "events": ["sub"], "sources": [], "listid": "1", "init": "0"},
        {"id": "2", "name": "WH-B", "url": "https://other.com/wh", "events": ["unsub"], "sources": [], "listid": "1", "init": "0"},
    ]
    r = webhook_audit.analyze(webhooks, skip_probe=True)
    assert r["total"] == 2
    assert r["unreachable"] == []
    for w in r["webhooks"]:
        assert w["probe"]["reachable"] is None


def test_invalid_url_marked_unreachable():
    webhooks = [{"id": "1", "name": "Bad", "url": "not-a-url", "events": [], "sources": [], "listid": None, "init": "0"}]
    r = webhook_audit.analyze(webhooks, skip_probe=False)
    assert len(r["unreachable"]) == 1
    assert r["unreachable"][0]["probe"]["reachable"] is False


def test_render_includes_table():
    r = webhook_audit.analyze([], skip_probe=True)
    md = webhook_audit.render_markdown(r)
    assert "Webhook Audit" in md
