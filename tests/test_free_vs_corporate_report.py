"""Tests for free_vs_corporate_report.analyze()."""
from __future__ import annotations

import free_vs_corporate_report


def test_split_correctness():
    contacts = [
        {"email": "a@gmail.com"},
        {"email": "b@yahoo.com"},
        {"email": "c@acme.com"},
        {"email": "d@beta.io"},
        {"email": "e@gamma.org"},
    ]
    r = free_vs_corporate_report.analyze(contacts)
    assert r["free"] == 2
    assert r["corporate"] == 3
    assert abs(r["free_pct"] - 40) < 0.01


def test_invalid_emails_counted():
    contacts = [{"email": ""}, {"email": "no-at-sign"}, {"email": "x@y.com"}]
    r = free_vs_corporate_report.analyze(contacts)
    assert r["invalid"] == 2
    assert r["valid"] == 1


def test_render_consumer_lean():
    contacts = [{"email": f"u{i}@gmail.com"} for i in range(8)] + \
               [{"email": "x@acme.com"}]
    r = free_vs_corporate_report.analyze(contacts)
    md = free_vs_corporate_report.render_markdown(r)
    assert "consumer" in md.lower()


def test_render_b2b_lean():
    contacts = [{"email": f"u{i}@acme.com"} for i in range(8)] + \
               [{"email": "x@gmail.com"}]
    r = free_vs_corporate_report.analyze(contacts)
    md = free_vs_corporate_report.render_markdown(r)
    assert "b2b" in md.lower()
