"""Tests for custom_field_audit.analyze()."""
from __future__ import annotations

import custom_field_audit


def test_zombie_field_detected():
    data = {
        "fields": [
            {"id": "1", "title": "Used Field", "type": "text", "perstag": "USED"},
            {"id": "2", "title": "Zombie", "type": "text", "perstag": "ZOMBIE"},
        ],
        "field_values": [{"contact": str(i), "field": "1", "value": "v"} for i in range(5)],
        "automations": [{"actions": "uses %USED%"}],
        "segments": [],
        "contact_count": 100,
    }
    r = custom_field_audit.analyze(data)
    zombie_titles = {z["title"] for z in r["zombies"]}
    assert "Zombie" in zombie_titles
    assert "Used Field" not in zombie_titles


def test_low_use_unreferenced():
    data = {
        "fields": [{"id": "1", "title": "Rarely Used", "type": "text", "perstag": "X"}],
        "field_values": [{"contact": "1", "field": "1", "value": "v"}],
        "automations": [],
        "segments": [],
        "contact_count": 100,
    }
    r = custom_field_audit.analyze(data)
    assert any(f["title"] == "Rarely Used" for f in r["low_use_unreferenced"])


def test_render():
    data = {"fields": [], "field_values": [], "automations": [], "segments": [], "contact_count": 0}
    r = custom_field_audit.analyze(data)
    md = custom_field_audit.render_markdown(r)
    assert "Custom Field Audit" in md
