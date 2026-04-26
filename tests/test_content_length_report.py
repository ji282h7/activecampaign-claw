"""Tests for content_length_report.analyze()."""
from __future__ import annotations

import content_length_report as clr


def test_strip_html():
    out = clr._strip_html("<p>Hello <b>world</b></p>")
    assert "Hello" in out and "world" in out
    assert "<" not in out


def test_word_count_and_cta_correlation():
    data = {
        "campaigns": [
            {"id": "1", "subject": "S", "send_amt": "100", "uniqueopens": "20", "uniquelinkclicks": "5", "messages": [{"id": "100"}]},
            {"id": "2", "subject": "S", "send_amt": "100", "uniqueopens": "15", "uniquelinkclicks": "2", "messages": [{"id": "200"}]},
        ],
        "messages": [
            {"id": "100", "html": "<p>Short body. <a>Click here</a></p>"},
            {"id": "200", "html": "<p>" + "word " * 400 + "<a>buy now</a> <a>shop now</a></p>"},
        ],
    }
    r = clr.analyze(data)
    assert len(r["rows"]) == 2
    short = [row for row in r["rows"] if row["word_count"] < 100][0]
    long_ = [row for row in r["rows"] if row["word_count"] >= 300][0]
    assert short["cta_count"] == 1
    assert long_["cta_count"] >= 2


def test_empty_input():
    r = clr.analyze({"campaigns": [], "messages": []})
    assert r["rows"] == []
