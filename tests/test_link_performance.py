"""Tests for link_performance.analyze()."""
from __future__ import annotations

import link_performance


def test_ctr_calculations():
    data = {
        "campaign": {"id": "1", "name": "Test", "send_amt": "1000", "uniqueopens": "200"},
        "links": [
            {"id": "1", "link": "https://x/a", "name": "A", "linkclicks": "50", "uniquelinkclicks": "40", "tracked": "1"},
            {"id": "2", "link": "https://x/b", "name": "B", "linkclicks": "10", "uniquelinkclicks": "5", "tracked": "1"},
        ],
    }
    r = link_performance.analyze(data)
    assert r["total_links"] == 2
    assert r["total_unique_clicks"] == 45
    # sorted desc by unique_clicks
    assert r["links"][0]["unique_clicks"] == 40
    assert abs(r["links"][0]["ctr_of_recipients"] - 0.04) < 1e-6
    assert abs(r["links"][0]["ctr_of_opens"] - 0.20) < 1e-6


def test_zero_open_zero_send_safe():
    data = {"campaign": {"send_amt": "0", "uniqueopens": "0"}, "links": []}
    r = link_performance.analyze(data)
    assert r["total_links"] == 0
