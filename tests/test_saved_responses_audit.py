"""Tests for saved_responses_audit.analyze().

/savedResponses shape: { savedResponses: [{ id, title, body, cdate, mdate }] }.
Auto-correlation tests use jaccard on tokenized HTML-stripped bodies.
"""
from __future__ import annotations

from datetime import datetime, timezone

import saved_responses_audit as sra


def _now():
    return datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)


def test_unavailable_path():
    r = sra.analyze({"unavailable": True}, now=_now())
    md = sra.render_markdown(r)
    assert "Not available on your ActiveCampaign plan" in md
    assert "Saved Responses" in md
    assert "ERROR" not in md


def test_stale_short_long_buckets():
    data = {
        "responses": [
            {"id": "1", "title": "Old", "body": "<p>" + "x" * 100 + "</p>",
             "cdate": "2024-01-01", "mdate": "2024-01-01"},
            {"id": "2", "title": "Tiny", "body": "<p>hi</p>",
             "cdate": "2026-05-01", "mdate": "2026-05-01"},
            {"id": "3", "title": "Huge", "body": "<p>" + "y" * 9000 + "</p>",
             "cdate": "2026-05-01", "mdate": "2026-05-01"},
        ],
        "unavailable": False,
    }
    r = sra.analyze(data, stale_days=365, now=_now())
    assert {s["id"] for s in r["stale"]} == {"1"}
    assert {s["id"] for s in r["too_short"]} == {"2"}
    assert {s["id"] for s in r["too_long"]} == {"3"}


def test_duplicate_detection_via_jaccard():
    common = "Hi there, thanks for reaching out. We will get back to you soon."
    data = {
        "responses": [
            {"id": "1", "title": "Auto-reply A", "body": f"<p>{common}</p>",
             "cdate": "2026-05-01", "mdate": "2026-05-01"},
            {"id": "2", "title": "Auto-reply B", "body": f"<p>{common} Cheers!</p>",
             "cdate": "2026-05-01", "mdate": "2026-05-01"},
            {"id": "3", "title": "Different",
             "body": "<p>Completely unrelated content about pricing changes.</p>",
             "cdate": "2026-05-01", "mdate": "2026-05-01"},
        ],
        "unavailable": False,
    }
    r = sra.analyze(data, duplicate_threshold=0.7, now=_now())
    pairs = {(d["a_id"], d["b_id"]) for d in r["duplicates"]}
    assert ("1", "2") in pairs
    # 1↔3 and 2↔3 should NOT be duplicates
    assert ("1", "3") not in pairs
    assert ("2", "3") not in pairs


def test_total_count():
    data = {
        "responses": [
            {"id": str(i), "title": f"R{i}",
             "body": f"<p>response number {i} with content</p>",
             "cdate": "2026-05-01", "mdate": "2026-05-01"}
            for i in range(5)
        ],
        "unavailable": False,
    }
    r = sra.analyze(data, now=_now())
    assert r["total"] == 5
