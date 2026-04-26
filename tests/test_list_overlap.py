"""Tests for list_overlap.analyze()."""
from __future__ import annotations

import list_overlap


def test_subset_pair_detected():
    data = {
        "lists": [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}],
        # list 2 is a complete subset of list 1
        "contact_lists": [{"contact": str(i), "list": "1", "status": "1"} for i in range(20)] +
                         [{"contact": str(i), "list": "2", "status": "1"} for i in range(5)],
    }
    r = list_overlap.analyze(data, min_overlap=1)
    assert len(r["subset_pairs"]) >= 1
    sp = r["subset_pairs"][0]
    assert max(sp["a_pct_in_b"], sp["b_pct_in_a"]) >= 95


def test_only_active_status_counted():
    data = {
        "lists": [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}],
        # status=2 (unsubscribed) should NOT count
        "contact_lists": [
            {"contact": "1", "list": "1", "status": "1"},
            {"contact": "1", "list": "2", "status": "2"},
        ],
    }
    r = list_overlap.analyze(data, min_overlap=1)
    assert r["overlap_pairs"] == []


def test_min_overlap_threshold():
    data = {
        "lists": [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}],
        "contact_lists": [
            {"contact": str(i), "list": "1", "status": "1"} for i in range(2)
        ] + [
            {"contact": str(i), "list": "2", "status": "1"} for i in range(2)
        ],
    }
    r = list_overlap.analyze(data, min_overlap=10)
    assert r["overlap_pairs"] == []


def test_render_markdown_includes_sections():
    data = {
        "lists": [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}],
        "contact_lists": [{"contact": str(i), "list": "1", "status": "1"} for i in range(20)] +
                         [{"contact": str(i), "list": "2", "status": "1"} for i in range(5)],
    }
    r = list_overlap.analyze(data, min_overlap=1)
    md = list_overlap.render_markdown(r)
    assert "# List Overlap" in md
    assert "Subset pairs" in md
