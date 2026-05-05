"""Tests for template_audit.analyze().

Per AC v3 docs:
  /templates -> { templates: [{ id, name, subject, content, cdate, mdate }] }
  /campaigns -> { campaigns: [{ id, name, send_amt, uniqueopens, ... }] }
"""
from __future__ import annotations

from datetime import datetime, timezone

import template_audit


def _now():
    return datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)


def test_unused_and_stale_detected():
    data = {
        "templates": [
            {"id": "1", "name": "Used", "subject": "Sub", "content": "x" * 500,
             "cdate": "2026-04-01", "mdate": "2026-05-01"},
            {"id": "2", "name": "Unused", "subject": "Sub", "content": "y" * 500,
             "cdate": "2025-01-01", "mdate": "2025-01-01"},
        ],
        "campaigns": [
            {"id": "100", "name": "Used Campaign", "templateid": "1",
             "send_amt": 1000, "uniqueopens": 250},
        ],
    }
    r = template_audit.analyze(data, stale_days=180, now=_now())
    unused_ids = {t["id"] for t in r["unused"]}
    assert "2" in unused_ids
    assert "1" not in unused_ids
    stale_ids = {t["id"] for t in r["stale"]}
    assert "2" in stale_ids


def test_avg_open_rate_calculation():
    data = {
        "templates": [
            {"id": "1", "name": "T", "subject": "S", "content": "x" * 500,
             "cdate": "2026-05-01", "mdate": "2026-05-01"},
        ],
        "campaigns": [
            {"id": "100", "name": "A", "templateid": "1",
             "send_amt": 1000, "uniqueopens": 200},
            {"id": "101", "name": "B", "templateid": "1",
             "send_amt": 500, "uniqueopens": 100},
        ],
    }
    r = template_audit.analyze(data, now=_now())
    by_id = {t["id"]: t for t in r["templates"]}
    # both campaigns have 20% open rate
    assert abs(by_id["1"]["avg_open_rate"] - 0.20) < 1e-6
    assert by_id["1"]["campaign_uses"] == 2


def test_short_and_long_buckets():
    data = {
        "templates": [
            {"id": "1", "name": "Tiny", "subject": "", "content": "hi",
             "cdate": "2026-05-01", "mdate": "2026-05-01"},
            {"id": "2", "name": "Big", "subject": "", "content": "z" * 60000,
             "cdate": "2026-05-01", "mdate": "2026-05-01"},
            {"id": "3", "name": "OK", "subject": "", "content": "a" * 1000,
             "cdate": "2026-05-01", "mdate": "2026-05-01"},
        ],
        "campaigns": [],
    }
    r = template_audit.analyze(data, now=_now())
    assert {t["id"] for t in r["too_short"]} == {"1"}
    assert {t["id"] for t in r["too_long"]} == {"2"}


def test_alternate_template_id_field():
    # Some campaigns historically reference 'designid' instead of templateid
    data = {
        "templates": [
            {"id": "5", "name": "X", "subject": "S", "content": "x" * 500,
             "cdate": "2026-05-01", "mdate": "2026-05-01"},
        ],
        "campaigns": [
            {"id": "100", "name": "Y", "designid": "5",
             "send_amt": 100, "uniqueopens": 30},
        ],
    }
    r = template_audit.analyze(data, now=_now())
    by_id = {t["id"]: t for t in r["templates"]}
    assert by_id["5"]["campaign_uses"] == 1


def test_render_includes_top_templates():
    data = {
        "templates": [
            {"id": "1", "name": "Top", "subject": "S", "content": "x" * 500,
             "cdate": "2026-05-01", "mdate": "2026-05-01"},
        ],
        "campaigns": [
            {"id": "100", "name": "C", "templateid": "1",
             "send_amt": 1000, "uniqueopens": 250},
        ],
    }
    md = template_audit.render_markdown(template_audit.analyze(data, now=_now()))
    assert "Top templates by campaign use" in md
    assert "Top" in md
