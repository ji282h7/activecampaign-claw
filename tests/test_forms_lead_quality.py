"""Tests for forms_lead_quality.analyze().

Per AC v3 docs:
  /forms -> { forms: [{ id, name, subscribelist, ... }] }
  /contacts -> { contacts: [{ id, score, bounced_hard, status, udate, ... }] }
  Engagement events are normalized via ACClient.fetch_engagement_events()
  to {event, contact, tstamp, campaign?, link?, email?}.
"""
from __future__ import annotations

from datetime import datetime, timezone

import forms_lead_quality as flq


def _now():
    return datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)


def test_engagement_rate_and_avg_score():
    data = {
        "forms": [
            {"id": "1", "name": "Newsletter signup", "subscribelist": "10"},
        ],
        "contacts_by_form": {
            "1": [
                {"id": "100", "score": "50", "bounced_hard": "0", "status": "1"},
                {"id": "101", "score": "20", "bounced_hard": "0", "status": "1"},
                {"id": "102", "score": "0", "bounced_hard": "0", "status": "1"},
                {"id": "103", "score": "10", "bounced_hard": "1", "status": "1"},
            ],
        },
        "events_by_contact": {
            "100": [{"event": "open", "contact": "100"}],
            "101": [{"event": "click", "contact": "101"}],
            # 102, 103: no engagement events
        },
        "window_days": 90,
    }
    r = flq.analyze(data, now=_now())
    by_id = {f["id"]: f for f in r["forms"]}
    f1 = by_id["1"]
    assert f1["contacts_sampled"] == 4
    assert abs(f1["engagement_rate"] - 0.5) < 1e-6  # 2 / 4
    assert abs(f1["avg_score"] - 20.0) < 1e-6  # (50+20+0+10)/4
    assert abs(f1["bounce_rate"] - 0.25) < 1e-6  # 1 / 4


def test_multiple_forms_sorted_by_engagement():
    data = {
        "forms": [
            {"id": "1", "name": "High", "subscribelist": "10"},
            {"id": "2", "name": "Low", "subscribelist": "11"},
        ],
        "contacts_by_form": {
            "1": [{"id": "100", "score": "10", "bounced_hard": "0", "status": "1"}],
            "2": [{"id": "200", "score": "10", "bounced_hard": "0", "status": "1"}],
        },
        "events_by_contact": {
            "100": [{"event": "open", "contact": "100"}],
            # 200 has no engagement
        },
        "window_days": 90,
    }
    r = flq.analyze(data, now=_now())
    assert r["forms"][0]["id"] == "1"  # higher engagement first
    assert r["forms"][1]["id"] == "2"


def test_zero_contacts_dont_crash():
    data = {
        "forms": [
            {"id": "1", "name": "Empty form", "subscribelist": "10"},
        ],
        "contacts_by_form": {"1": []},
        "events_by_contact": {},
        "window_days": 90,
    }
    r = flq.analyze(data, now=_now())
    f1 = r["forms"][0]
    assert f1["contacts_sampled"] == 0
    assert f1["engagement_rate"] == 0
    assert f1["avg_score"] == 0


def test_subscribelist_extracted_from_alt_shapes():
    # subscribelist may arrive as a string, list, or {key: id} dict
    f1 = {"id": "1", "subscribelist": "5"}
    f2 = {"id": "2", "subscribelist": ["5", "6"]}
    f3 = {"id": "3", "subscribelist": {"main": "7"}}
    f4 = {"id": "4"}
    assert flq._form_subscribelists(f1) == ["5"]
    assert flq._form_subscribelists(f2) == ["5", "6"]
    assert flq._form_subscribelists(f3) == ["7"]
    assert flq._form_subscribelists(f4) == []


def test_render_markdown_includes_caveat():
    data = {
        "forms": [{"id": "1", "name": "F", "subscribelist": "10"}],
        "contacts_by_form": {
            "1": [{"id": "1", "score": "1", "bounced_hard": "0", "status": "1"}],
        },
        "events_by_contact": {},
        "window_days": 90,
    }
    md = flq.render_markdown(flq.analyze(data, now=_now()))
    assert "list-quality reading" in md
    assert "Per-form lead quality" in md
