"""Tests for automation_overlap.analyze()."""
from __future__ import annotations

import automation_overlap


def test_three_plus_detection():
    data = {
        "automations": [
            {"id": "1", "name": "A"},
            {"id": "2", "name": "B"},
            {"id": "3", "name": "C"},
        ],
        "contact_automations": [
            {"contact": "100", "automation": "1", "status": "1"},
            {"contact": "100", "automation": "2", "status": "1"},
            {"contact": "100", "automation": "3", "status": "1"},
            {"contact": "200", "automation": "1", "status": "1"},  # only 1 — not flagged
        ],
    }
    r = automation_overlap.analyze(data, min_overlap=1)
    assert r["contacts_in_3plus"] == 1
    assert r["samples_3plus"][0]["contact"] == "100"


def test_pair_overlap_count():
    data = {
        "automations": [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}],
        "contact_automations": [
            {"contact": "1", "automation": "1", "status": "1"},
            {"contact": "1", "automation": "2", "status": "1"},
            {"contact": "2", "automation": "1", "status": "1"},
            {"contact": "2", "automation": "2", "status": "1"},
        ],
    }
    r = automation_overlap.analyze(data, min_overlap=2)
    assert len(r["pairs"]) == 1
    assert r["pairs"][0]["overlap"] == 2


def test_render_markdown_includes_sections():
    data = {
        "automations": [
            {"id": "1", "name": "A"},
            {"id": "2", "name": "B"},
            {"id": "3", "name": "C"},
        ],
        "contact_automations": [
            {"contact": "100", "automation": "1", "status": "1"},
            {"contact": "100", "automation": "2", "status": "1"},
            {"contact": "100", "automation": "3", "status": "1"},
        ],
    }
    r = automation_overlap.analyze(data, min_overlap=1)
    md = automation_overlap.render_markdown(r)
    assert "# Automation Overlap" in md
    assert "Sample contacts in 3+ automations" in md
