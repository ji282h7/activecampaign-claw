"""Tests for data_subject_export.fetch() with mocked client."""
from __future__ import annotations

from unittest.mock import patch

import _ac_client
import data_subject_export
import pytest


def _client():
    with patch("_ac_client.ACClient.__init__", lambda self, *a, **kw: None):
        c = _ac_client.ACClient.__new__(_ac_client.ACClient)
    c.base = "https://test.api-us1.com/api/3"
    c.token = "tok"
    c._request_count = 0
    return c


def test_collects_all_per_contact_resources():
    c = _client()

    def fake_get(path, params=None):
        if path == "contacts":
            return {"contacts": [{"id": "42", "email": "subject@example.com"}]}
        return {}

    def fake_paginate(path, key, params=None, max_items=10000, **kw):
        return [{"path": path, "for_contact": params.get("filters[contact]") if params else None}]

    c.get = fake_get
    c.paginate = fake_paginate

    out = data_subject_export.fetch(c, "subject@example.com")
    assert out["contact"]["id"] == "42"
    for k in ("fieldValues", "contactTags", "contactLists", "contactAutomations"):
        assert k in out
        assert isinstance(out[k], list)


def test_missing_contact_raises():
    c = _client()
    c.get = lambda path, params=None: {"contacts": []}
    c.paginate = lambda *a, **kw: []
    with pytest.raises(SystemExit):
        data_subject_export.fetch(c, "missing@example.com")


def test_deals_403_handled_cleanly():
    c = _client()

    def fake_get(path, params=None):
        return {"contacts": [{"id": "42", "email": "x@y.com"}]}

    def fake_paginate(path, key, params=None, **kw):
        if path == "deals":
            raise _ac_client.ACClientError(403, "Deals not enabled")
        return []

    c.get = fake_get
    c.paginate = fake_paginate
    out = data_subject_export.fetch(c, "x@y.com")
    assert out["deals"] == "Deals feature not enabled"
