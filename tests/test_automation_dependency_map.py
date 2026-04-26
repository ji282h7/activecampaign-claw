"""Tests for automation_dependency_map.analyze()."""
from __future__ import annotations

import automation_dependency_map as adm


def test_extracts_tag_and_automation_refs_from_block_blob():
    data = {
        "automations": [
            {"id": "1", "name": "Welcome", "status": "1"},
            {"id": "2", "name": "Nurture", "status": "1"},
        ],
        "blocks": [
            # block in automation 1: applies tag id=42, then enrolls into automation 2
            {"automation": "1", "type": "tagadd", "params": {"tag": "42"}},
            {"automation": "1", "type": "startanother", "params": {"automation": "2"}},
            {"automation": "1", "type": "send", "params": {"messageid": "100"}},
        ],
        "tags": [{"id": "42", "tag": "VIP"}],
        "lists": [],
    }
    r = adm.analyze(data)
    welcome = next(a for a in r["automations"] if a["id"] == "1")
    assert "VIP" in welcome["applies_tags"]
    assert "Nurture" in welcome["enrolls_into_automations"]
    assert "100" in welcome["sends_messages"]


def test_render_no_deps():
    data = {"automations": [], "blocks": [], "tags": [], "lists": []}
    r = adm.analyze(data)
    md = adm.render_markdown(r)
    assert "Dependency Map" in md
