"""Tests for mql_to_sql_handoff.analyze() — Deals-feature-required script."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import mql_to_sql_handoff


def test_handoff_buckets():
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(days=2)).isoformat()
    data = {
        "contacts": [],
        "scores": [
            {"contact": "1", "scoreValue": "75", "mdate": recent},  # crossed threshold
            {"contact": "2", "scoreValue": "55", "mdate": recent},  # crossed
            {"contact": "3", "scoreValue": "30", "mdate": recent},  # below threshold
        ],
        "deals": [
            {"id": "100", "contact": "1", "value": "50000", "cdate": recent},   # success
            {"id": "200", "contact": "999", "value": "20000", "cdate": recent}, # off-script (no scoring)
        ],
    }
    r = mql_to_sql_handoff.analyze(data, threshold=50, days=7)
    success_contacts = {h["contact"] for h in r["handoff_success"]}
    miss_contacts = {h["contact"] for h in r["handoff_miss"]}
    no_scoring_deals = {d["deal_id"] for d in r["deals_no_scoring"]}

    assert "1" in success_contacts
    assert "2" in miss_contacts
    assert "200" in no_scoring_deals
    assert r["contacts_crossed_threshold"] == 2


def test_outside_window_excluded():
    old = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
    data = {
        "contacts": [],
        "scores": [{"contact": "1", "scoreValue": "100", "mdate": old}],
        "deals": [],
    }
    r = mql_to_sql_handoff.analyze(data, threshold=50, days=7)
    assert r["contacts_crossed_threshold"] == 0
