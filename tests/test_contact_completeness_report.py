"""Tests for contact_completeness_report.analyze()."""
from __future__ import annotations

import contact_completeness_report as ccr


def test_builtin_field_counts():
    data = {
        "contacts": [
            {"id": "1", "firstName": "A", "lastName": "B", "phone": "555"},
            {"id": "2", "firstName": "C", "lastName": "", "phone": ""},
            {"id": "3", "firstName": "", "lastName": "D", "phone": ""},
        ],
        "fields": [],
        "field_values": [],
    }
    r = ccr.analyze(data)
    assert r["total_contacts"] == 3
    assert r["builtin"]["firstName"]["populated"] == 2
    assert r["builtin"]["lastName"]["populated"] == 2
    assert r["builtin"]["phone"]["populated"] == 1


def test_custom_field_counts():
    data = {
        "contacts": [{"id": str(i), "firstName": "x"} for i in range(10)],
        "fields": [{"id": "1", "title": "Industry", "type": "dropdown"}],
        "field_values": [
            {"contact": "1", "field": "1", "value": "Tech"},
            {"contact": "2", "field": "1", "value": "Finance"},
            {"contact": "3", "field": "1", "value": ""},  # blank should not count
        ],
    }
    r = ccr.analyze(data)
    assert r["custom_fields"][0]["populated"] == 2
    assert abs(r["custom_fields"][0]["pct"] - 20.0) < 0.01
