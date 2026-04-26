"""Tests for campaign_postmortem.analyze()."""
from __future__ import annotations

import campaign_postmortem


def test_metrics_computation():
    data = {
        "campaign": {
            "id": "42",
            "name": "Test",
            "subject": "Hello",
            "send_amt": "1000",
            "opens": "300",
            "uniqueopens": "250",
            "linkclicks": "60",
            "uniquelinkclicks": "40",
            "unsubscribes": "5",
            "bounces": "10",
            "sdate": "2026-04-01T12:00:00Z",
        },
        "links": [
            {"link": "https://x.com/a", "name": "A", "linkclicks": "30", "uniquelinkclicks": "20"},
            {"link": "https://x.com/b", "name": "B", "linkclicks": "30", "uniquelinkclicks": "20"},
        ],
        "activities": [],
    }
    baseline = {"open_rate_p50": 0.20, "click_rate_p50": 0.03, "unsub_rate": 0.005}
    r = campaign_postmortem.analyze(data, baseline)
    assert r["sent"] == 1000
    assert abs(r["metrics"]["open_rate"] - 0.25) < 1e-6
    assert abs(r["metrics"]["click_rate"] - 0.04) < 1e-6
    assert abs(r["vs_baseline"]["open_rate_delta_pp"] - 5.0) < 1e-6
    # links sorted by unique clicks desc
    assert r["links"][0]["unique_clicks"] == 20
    assert len(r["links"]) == 2


def test_zero_send_handled():
    data = {"campaign": {"send_amt": "0"}, "links": [], "activities": []}
    r = campaign_postmortem.analyze(data, {})
    assert r["metrics"]["open_rate"] == 0
    assert r["metrics"]["click_rate"] == 0
