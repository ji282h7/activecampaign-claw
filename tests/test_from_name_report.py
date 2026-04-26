"""Tests for from_name_report.analyze()."""
from __future__ import annotations

import from_name_report


def test_groups_by_from_name_and_email():
    data = {
        "campaigns": [
            {"send_amt": "100", "uniqueopens": "30", "uniquelinkclicks": "5", "fromname": "Alice", "fromemail": "a@x.com"},
            {"send_amt": "100", "uniqueopens": "20", "uniquelinkclicks": "3", "fromname": "Alice", "fromemail": "a@x.com"},
            {"send_amt": "100", "uniqueopens": "10", "uniquelinkclicks": "1", "fromname": "Bob", "fromemail": "b@x.com"},
        ],
        "messages": [],
    }
    r = from_name_report.analyze(data)
    by_name = {row["key"]: row for row in r["by_from_name"]}
    assert by_name["Alice"]["sends"] == 2
    assert by_name["Alice"]["recipients"] == 200
    assert abs(by_name["Alice"]["open_rate"] - 0.25) < 1e-6
    assert by_name["Bob"]["sends"] == 1


def test_unknown_fallback():
    data = {"campaigns": [{"send_amt": "100", "uniqueopens": "30"}], "messages": []}
    r = from_name_report.analyze(data)
    assert r["by_from_name"][0]["key"] == "(unknown)"
