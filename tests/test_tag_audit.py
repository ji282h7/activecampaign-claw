"""Tests for tag_audit.analyze()."""
from __future__ import annotations

import tag_audit


def test_rare_and_dead_tags_detected():
    data = {
        "tags": [
            {"id": "1", "tag": "popular"},
            {"id": "2", "tag": "rare-typo"},
            {"id": "3", "tag": "dead"},
        ],
        "contact_tags": [{"contact": str(i), "tag": "1"} for i in range(50)] +
                        [{"contact": "1", "tag": "2"}],
        "automations": [{"name": "Welcome", "actions": "uses popular"}],
        "segments": [],
    }
    r = tag_audit.analyze(data, rare_threshold=5, common_threshold=0.5)
    rare_names = {t["name"] for t in r["rare"]}
    dead_names = {t["name"] for t in r["dead"]}
    assert "rare-typo" in rare_names
    assert "dead" in dead_names
    # popular is referenced + not rare
    assert "popular" not in rare_names
    assert "popular" not in dead_names


def test_consolidation_detection():
    # two tags that always co-occur on >= 5 contacts
    data = {
        "tags": [{"id": "1", "tag": "a"}, {"id": "2", "tag": "b"}],
        "contact_tags": [{"contact": str(i), "tag": str(t)} for i in range(10) for t in (1, 2)],
        "automations": [],
        "segments": [],
    }
    r = tag_audit.analyze(data, rare_threshold=5, common_threshold=0.99)
    assert len(r["consolidation"]) == 1
    assert r["consolidation"][0]["co_count"] == 10


def test_render_includes_sections():
    data = {"tags": [], "contact_tags": [], "automations": [], "segments": []}
    r = tag_audit.analyze(data, 5, 0.5)
    md = tag_audit.render_markdown(r)
    assert "Tag Audit" in md


def test_analyze_accepts_preaggregated_shape():
    """The streaming fetch_data now returns tag_count + contact_tag_pairs
    instead of the raw contact_tags list. analyze() must accept both."""
    from collections import Counter, defaultdict
    data = {
        "tags": [
            {"id": "1", "tag": "popular"},
            {"id": "2", "tag": "rare-typo"},
        ],
        # Pre-aggregated by fetch_data while streaming
        "tag_count": Counter({"1": 50, "2": 1}),
        "contact_tag_pairs": defaultdict(set, {
            **{str(i): {"1"} for i in range(50)},
            "0": {"1", "2"},
        }),
        "automations": [{"name": "Welcome", "actions": "uses popular"}],
        "segments": [],
    }
    r = tag_audit.analyze(data, rare_threshold=5, common_threshold=0.5)
    rare_names = {t["name"] for t in r["rare"]}
    assert "rare-typo" in rare_names
    assert r["total_tagged_contacts"] == 50
