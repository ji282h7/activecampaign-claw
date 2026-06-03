"""Tests for segment_performance.analyze()."""
from __future__ import annotations

import segment_performance


def test_only_audience_events_counted():
    audience = {"1", "2"}
    activities = [
        {"event": "open", "contact": "1"},
        {"event": "click", "contact": "1"},
        {"event": "open", "contact": "2"},
        {"event": "open", "contact": "999"},  # outside audience — ignored
        {"event": "send", "contact": "1"},
    ]
    r = segment_performance.analyze(audience, activities)
    assert r["audience_size"] == 2
    assert r["open_events"] == 2
    assert r["click_events"] == 1
    assert r["send_events"] == 1
    assert r["unique_openers"] == 2
    assert r["unique_clickers"] == 1


def test_render_label():
    r = segment_performance.analyze(set(), [])
    md = segment_performance.render_markdown(r, "list=42")
    assert "list=42" in md


def test_main_missing_audience_flag_prints_friendly_message(capsys, monkeypatch):
    """When invoked without --list/--tag/--segment, exit 0 with a friendly
    explanation rather than raising SystemExit with an ERROR: prefix."""
    monkeypatch.setattr("sys.argv", ["segment_performance.py"])
    import segment_performance
    # Should NOT raise — friendly path prints + returns
    segment_performance.main()
    captured = capsys.readouterr()
    assert "Segment Performance" in captured.out
    assert "--list" in captured.out
    assert "--tag" in captured.out
    assert "--segment" in captured.out
    assert "ERROR" not in captured.out

