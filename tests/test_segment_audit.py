"""Tests for segment_audit.analyze()."""
from __future__ import annotations

import segment_audit


def test_empty_segments_flagged():
    data = {
        "segments": [
            {"id": "1", "name": "Active", "conditions": {}},
            {"id": "2", "name": "Empty", "conditions": {}},
        ],
        "tags": {},
        "fields": {},
        "lists": {},
        "counts": {"1": 50, "2": 0},
    }
    r = segment_audit.analyze(data)
    empty_ids = {e["id"] for e in r["empty"]}
    assert "2" in empty_ids
    assert "1" not in empty_ids


def test_render():
    data = {"segments": [], "tags": {}, "fields": {}, "lists": {}, "counts": {}}
    r = segment_audit.analyze(data)
    md = segment_audit.render_markdown(r)
    assert "Segment Audit" in md
