"""Tests for send_simulator.simulate()."""
from __future__ import annotations

import send_simulator


def test_proportional_estimates():
    baseline = {
        "open_rate_p50": 0.30,
        "click_rate_p50": 0.05,
        "unsub_rate": 0.01,
        "bounce_rate": 0.02,
    }
    r = send_simulator.simulate(audience=10000, baseline=baseline)
    assert r["estimated_opens"] == 3000
    assert r["estimated_clicks"] == 500
    assert r["estimated_unsubs"] == 100
    assert r["estimated_bounces"] == 200


def test_uses_defaults_when_baseline_missing():
    r = send_simulator.simulate(audience=1000, baseline={})
    # defaults: 0.25 / 0.03 / 0.003 / 0.005
    assert r["estimated_opens"] == 250
    assert r["estimated_clicks"] == 30
    assert r["estimated_unsubs"] == 3
    assert r["estimated_bounces"] == 5


def test_render_includes_audience():
    r = send_simulator.simulate(audience=12000, baseline={})
    md = send_simulator.render_markdown(r)
    assert "12,000" in md
