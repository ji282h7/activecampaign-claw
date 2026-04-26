"""Tests for broken_automation_detector.analyze()."""
from __future__ import annotations

import broken_automation_detector as bad


def test_detects_missing_tag_ref():
    data = {
        "automations": [{"id": "1", "name": "Welcome"}],
        "blocks": [
            # references tag id 99 which doesn't exist
            {"automation": "1", "type": "tagadd", "params": {"tag": "99"}},
        ],
        "valid": {
            "tag": {"42"},  # 99 missing
            "field": set(),
            "list": set(),
            "message": set(),
            "automation": {"1"},
        },
    }
    r = bad.analyze(data)
    assert len(r["broken"]) == 1
    assert "99" in r["broken"][0]["broken"]["tag"]


def test_no_broken_when_refs_valid():
    data = {
        "automations": [{"id": "1", "name": "Welcome"}],
        "blocks": [{"automation": "1", "type": "tagadd", "params": {"tag": "42"}}],
        "valid": {
            "tag": {"42"}, "field": set(), "list": set(), "message": set(), "automation": {"1"},
        },
    }
    r = bad.analyze(data)
    assert r["broken"] == []


def test_render_markdown_includes_sections():
    data = {
        "automations": [{"id": "1", "name": "Welcome"}],
        "blocks": [{"automation": "1", "type": "tagadd", "params": {"tag": "99"}}],
        "valid": {
            "tag": {"42"}, "field": set(), "list": set(), "message": set(), "automation": {"1"},
        },
    }
    r = bad.analyze(data)
    md = bad.render_markdown(r)
    assert "# Broken Automation Detector" in md
    assert "Welcome" in md
    assert "Missing tag ids" in md
