"""Tests for baseline_drift.aggregate() and analyze()."""
from __future__ import annotations

import baseline_drift


def test_aggregate_excludes_zero_send():
    campaigns = [
        {"send_amt": "1000", "uniqueopens": "300", "uniquelinkclicks": "40", "unsubscribes": "5"},
        {"send_amt": "0", "uniqueopens": "0", "uniquelinkclicks": "0", "unsubscribes": "0"},  # excluded
        {"send_amt": "500", "uniqueopens": "100", "uniquelinkclicks": "20", "unsubscribes": "2"},
    ]
    r = baseline_drift.aggregate(campaigns)
    assert r["campaigns"] == 3  # count includes all, but rates only from sent
    # mean(0.30, 0.20) = 0.25
    assert abs(r["open_rate_mean"] - 0.25) < 1e-6


def test_drift_significance():
    current = {"campaigns": 5, "open_rate_mean": 0.20, "click_rate_mean": 0.02, "unsub_rate_mean": 0.001}
    baseline = {"open_rate_p50": 0.30, "click_rate_p50": 0.04, "unsub_rate": 0.005}
    r = baseline_drift.analyze(current, baseline)
    open_drift = next(d for d in r["drifts"] if d["metric"] == "open_rate_mean")
    assert open_drift["significant"] is True  # 10pp drop > 5pp threshold


def test_no_drift_when_aligned():
    current = {"campaigns": 5, "open_rate_mean": 0.30, "click_rate_mean": 0.04, "unsub_rate_mean": 0.005}
    baseline = {"open_rate_p50": 0.30, "click_rate_p50": 0.04, "unsub_rate": 0.005}
    r = baseline_drift.analyze(current, baseline)
    assert all(d["significant"] is False for d in r["drifts"])


def test_render_markdown_includes_sections():
    current = {"campaigns": 5, "open_rate_mean": 0.20, "click_rate_mean": 0.02, "unsub_rate_mean": 0.001}
    baseline = {"open_rate_p50": 0.30, "click_rate_p50": 0.04, "unsub_rate": 0.005}
    r = baseline_drift.analyze(current, baseline)
    md = baseline_drift.render_markdown(r)
    assert "# Baseline Drift Check" in md
    assert "Campaigns in current window: 5" in md
