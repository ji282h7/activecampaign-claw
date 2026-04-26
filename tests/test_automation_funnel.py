"""Tests for automation_funnel.analyze()."""
from __future__ import annotations

import automation_funnel


def test_funnel_counts():
    data = {
        "automation": {"id": "5", "name": "Welcome", "status": "1"},
        "blocks": [
            {"id": "100", "ordernum": "1", "type": "send", "title": "Email 1"},
            {"id": "200", "ordernum": "2", "type": "wait", "title": "Wait"},
            {"id": "300", "ordernum": "3", "type": "send", "title": "Email 2"},
        ],
        "contact_automations": [
            {"automation": "5", "status": "1", "lastblock": "100"},  # active at block 100
            {"automation": "5", "status": "1", "lastblock": "200"},  # active at 200
            {"automation": "5", "status": "1", "lastblock": "200"},  # active at 200
            {"automation": "5", "status": "2", "lastblock": "300"},  # completed at 300
        ],
    }
    r = automation_funnel.analyze(data)
    assert r["enrolled_total"] == 4
    assert r["active"] == 3
    assert r["completed"] == 1
    by_block = {b["block_id"]: b for b in r["blocks"]}
    assert by_block["100"]["contacts_at_block"] == 1
    assert by_block["200"]["contacts_at_block"] == 2
    assert by_block["300"]["contacts_at_block"] == 1


def test_zero_enrollments():
    data = {
        "automation": {"id": "1", "name": "Empty", "status": "0"},
        "blocks": [],
        "contact_automations": [],
    }
    r = automation_funnel.analyze(data)
    assert r["enrolled_total"] == 0
    assert r["completion_rate"] == 0


def test_render_markdown_includes_sections():
    data = {
        "automation": {"id": "5", "name": "Welcome", "status": "1"},
        "blocks": [
            {"id": "100", "ordernum": "1", "type": "send", "title": "Email 1"},
        ],
        "contact_automations": [
            {"automation": "5", "status": "2", "lastblock": "100"},
        ],
    }
    r = automation_funnel.analyze(data)
    md = automation_funnel.render_markdown(r)
    assert "# Automation Funnel: Welcome" in md
    assert "Per-block" in md
    assert "Email 1" in md
