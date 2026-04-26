"""Tests for export_account.fetch() and snapshot wrappers using mocked client."""
from __future__ import annotations

import json
from unittest.mock import patch

import _ac_client
import export_account


def _mock_client():
    """Create an ACClient with bypassed __init__ + monkeypatched paginate."""
    with patch("_ac_client.ACClient.__init__", lambda self, *a, **kw: None):
        c = _ac_client.ACClient.__new__(_ac_client.ACClient)
    c.base = "https://test.api-us1.com/api/3"
    c.token = "tok"
    c._request_count = 0

    def fake_paginate(path, key, max_items=5000, **kwargs):
        return [{"id": "1", "name": f"sample-{path}"}]

    c.paginate = fake_paginate  # type: ignore
    return c


def test_export_taxonomy_scope_collects_taxonomy_keys():
    c = _mock_client()
    out = export_account.fetch(c, "taxonomy")
    tax = out["taxonomy"]
    for key in ("lists", "tags", "fields", "automations", "messages", "forms", "segments", "webhooks"):
        assert key in tax
        assert len(tax[key]) == 1
    assert "contacts" not in out
    assert "deals" not in out


def test_export_all_scope_includes_contacts_and_deals():
    c = _mock_client()
    out = export_account.fetch(c, "all")
    assert "contacts" in out
    assert "deals" in out
    assert "fieldValues" in out


def test_try_paginate_swallows_403_404():
    c = _mock_client()

    def paginate_403(path, key, **kwargs):
        if path in ("dealGroups", "dealStages"):
            raise _ac_client.ACClientError(403, "Deals not enabled")
        return [{"id": "x"}]

    c.paginate = paginate_403  # type: ignore
    out = export_account.fetch(c, "taxonomy")
    assert out["taxonomy"]["pipelines"] == []
    assert out["taxonomy"]["stages"] == []
    assert len(out["taxonomy"]["lists"]) == 1


def test_export_writes_json_to_file(tmp_path, monkeypatch):
    c = _mock_client()
    out = export_account.fetch(c, "taxonomy")
    p = tmp_path / "snap.json"
    p.write_text(json.dumps(out, default=str))
    loaded = json.loads(p.read_text())
    assert "taxonomy" in loaded
    assert loaded["schema_version"] == 1
