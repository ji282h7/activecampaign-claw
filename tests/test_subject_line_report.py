"""Tests for subject_line_report.features() + analyze()."""
from __future__ import annotations

import subject_line_report as sl


def test_feature_extraction():
    f = sl.features("%FIRSTNAME%, are you ready? 🚀")
    assert f["has_personalization"] is True
    assert f["has_question"] is True
    assert f["has_emoji"] is True
    assert f["has_urgency"] is False
    assert f["is_caps"] is False


def test_caps_detected():
    assert sl.features("BLACK FRIDAY DEAL")["is_caps"] is True


def test_urgency():
    assert sl.features("Last chance — ends today")["has_urgency"] is True


def test_pattern_lift():
    campaigns = [
        {"send_amt": "100", "uniqueopens": "30", "subject": "%FIRSTNAME%, hi"},
        {"send_amt": "100", "uniqueopens": "32", "subject": "%FIRSTNAME%, news"},
        {"send_amt": "100", "uniqueopens": "20", "subject": "Newsletter"},
        {"send_amt": "100", "uniqueopens": "22", "subject": "Update"},
    ]
    r = sl.analyze(campaigns)
    # Personalization tag present in 2, absent in 2 — lift should be positive
    pat = r["patterns"]["has_personalization"]
    assert pat["n_with"] == 2
    assert pat["n_without"] == 2
    assert pat["lift_pp"] > 0


def test_empty_campaigns():
    r = sl.analyze([])
    assert r["campaigns_analyzed"] == 0


def test_render_markdown_includes_sections():
    campaigns = [
        {"send_amt": "100", "uniqueopens": "30", "subject": "%FIRSTNAME%, hi"},
        {"send_amt": "100", "uniqueopens": "20", "subject": "Newsletter"},
    ]
    r = sl.analyze(campaigns)
    md = sl.render_markdown(r)
    assert "# Subject Line Report" in md
    assert "## Pattern lift" in md
    assert "## Length buckets" in md
