"""Tests for domain_engagement_report.analyze()."""
from __future__ import annotations

import domain_engagement_report as der


def test_groups_by_domain():
    data = {
        "contacts": [
            {"id": "1", "email": "a@gmail.com"},
            {"id": "2", "email": "b@gmail.com"},
            {"id": "3", "email": "c@acme.com"},
        ],
        "activities": [
            {"event": "open", "contact": "1"},
            {"event": "click", "contact": "1"},
            {"event": "open", "contact": "3"},
        ],
        "bounces": [{"contact": "2"}],
    }
    r = der.analyze(data, top=10)
    by_domain = {row["domain"]: row for row in r["domains"]}
    assert by_domain["gmail.com"]["contacts"] == 2
    assert by_domain["gmail.com"]["opens"] == 1
    assert by_domain["gmail.com"]["clicks"] == 1
    assert by_domain["gmail.com"]["bounces"] == 1
    assert by_domain["acme.com"]["opens"] == 1


def test_top_limit_respected():
    data = {
        "contacts": [{"id": str(i), "email": f"u{i}@d{i}.com"} for i in range(30)],
        "activities": [],
        "bounces": [],
    }
    r = der.analyze(data, top=5)
    assert len(r["domains"]) == 5
