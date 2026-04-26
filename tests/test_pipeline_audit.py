"""Tests for pipeline_audit.analyze() — Deals-feature-required script."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pipeline_audit


def test_deal_aggregation_and_stage_health():
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(days=15)).isoformat()
    old = (now - timedelta(days=120)).isoformat()
    data = {
        "pipelines": [{"id": "1", "title": "Sales"}],
        "stages": [
            {"id": "10", "title": "Qualified", "group": "1"},
            {"id": "20", "title": "Negotiation", "group": "1"},
        ],
        "deals": [
            {"id": "1", "group": "1", "stage": "10", "value": "100000", "cdate": recent},
            {"id": "2", "group": "1", "stage": "10", "value": "50000", "cdate": recent},
            {"id": "3", "group": "1", "stage": "20", "value": "200000", "cdate": old},
        ],
        "fields": [{"id": "1", "fieldLabel": "Source", "fieldType": "text"}],
        "field_data": [
            {"dealId": "1", "customFieldId": "1", "fieldValue": "Form"},
        ],
    }
    r = pipeline_audit.analyze(data)
    assert r["total_deals"] == 3
    pipeline = r["pipelines"][0]
    assert pipeline["deal_count"] == 3
    assert pipeline["total_value_cents"] == 350000
    by_stage = {s["stage_id"]: s for s in r["stages"]}
    assert by_stage["10"]["deal_count"] == 2
    assert by_stage["10"]["recent_90d"] == 2
    assert by_stage["20"]["recent_90d"] == 0
    assert by_stage["20"]["stale"] is True
    # field completeness: 1 of 3 deals has the field set
    assert r["deal_field_completeness"][0]["populated_deals"] == 1


def test_render():
    data = {"pipelines": [], "stages": [], "deals": [], "fields": [], "field_data": []}
    r = pipeline_audit.analyze(data)
    md = pipeline_audit.render_markdown(r)
    assert "Pipeline Audit" in md
