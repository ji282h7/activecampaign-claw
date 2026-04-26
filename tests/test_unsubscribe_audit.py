"""Tests for unsubscribe_audit.analyze()."""
from __future__ import annotations

import unsubscribe_audit


def test_unsub_link_detection():
    data = {
        "messages": [
            {"id": "1", "name": "Has link", "subject": "S", "html": "<a>click %UNSUBSCRIBE_LINK%</a>", "text": ""},
            {"id": "2", "name": "Plain unsub", "subject": "S", "html": "", "text": "unsubscribe at the bottom"},
            {"id": "3", "name": "Missing", "subject": "S", "html": "<p>no link here</p>", "text": ""},
        ],
        "forms": [],
    }
    r = unsubscribe_audit.analyze(data)
    missing_ids = {m["id"] for m in r["msg_missing"]}
    assert missing_ids == {"3"}


def test_form_optin_detection():
    data = {
        "messages": [],
        "forms": [
            {"id": "1", "name": "GDPR form", "fields": ["I agree to terms"]},
            {"id": "2", "name": "Bare form", "fields": ["email"]},
        ],
    }
    r = unsubscribe_audit.analyze(data)
    missing_ids = {f["id"] for f in r["form_missing"]}
    assert "2" in missing_ids
    assert "1" not in missing_ids
