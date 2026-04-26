"""Tests for form_audit.analyze()."""
from __future__ import annotations

import form_audit


def test_per_form_engagement_metrics():
    data = {
        "forms": [
            {"id": "1", "name": "Newsletter Signup"},
            {"id": "2", "name": "Demo Request"},
        ],
        "contacts": [
            {"id": "10", "sourceid": "1"},
            {"id": "11", "sourceid": "1"},
            {"id": "20", "sourceid": "2"},
        ],
        "activities": [
            {"event": "open", "contact": "10"},
            {"event": "click", "contact": "20"},
        ],
    }
    r = form_audit.analyze(data)
    by_id = {row["id"]: row for row in r["forms"]}
    assert by_id["1"]["contacts"] == 2
    assert by_id["1"]["engaged_contacts"] == 1
    assert by_id["2"]["engaged_contacts"] == 1


def test_no_contacts_for_form():
    data = {
        "forms": [{"id": "5", "name": "Empty"}],
        "contacts": [],
        "activities": [],
    }
    r = form_audit.analyze(data)
    assert r["forms"][0]["contacts"] == 0
    assert r["forms"][0]["engagement_rate"] == 0
