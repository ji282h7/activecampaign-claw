"""Tests for campaign_compare.metrics()."""
from __future__ import annotations

import campaign_compare


def test_metrics_calc():
    c = {
        "id": "1", "name": "A", "subject": "S", "send_amt": "1000",
        "uniqueopens": "300", "uniquelinkclicks": "60", "unsubscribes": "5", "bounces": "10",
    }
    m = campaign_compare.metrics(c)
    assert m["sent"] == 1000
    assert abs(m["open_rate"] - 0.30) < 1e-6
    assert abs(m["click_rate"] - 0.06) < 1e-6
    assert abs(m["click_to_open"] - 0.20) < 1e-6


def test_zero_send_safe():
    m = campaign_compare.metrics({"send_amt": "0", "uniqueopens": "0"})
    assert m["open_rate"] == 0
    assert m["click_to_open"] == 0


def test_render_table_includes_both():
    a = campaign_compare.metrics({"id": "1", "name": "First", "subject": "Hi", "send_amt": "100", "uniqueopens": "30"})
    b = campaign_compare.metrics({"id": "2", "name": "Second", "subject": "Yo", "send_amt": "100", "uniqueopens": "40"})
    md = campaign_compare.render_markdown(a, b)
    assert "First" in md and "Second" in md
