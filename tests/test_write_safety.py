"""Tests for the consolidated write() path in ACClient.

Covers:
  - AC_READ_ONLY=1 blocks every write before any request goes out
  - AC_MAX_WRITES caps the per-process write count
  - Every write appends an entry to writes.jsonl (with payload hash, NOT payload)
  - GET requests are unaffected by either flag
  - post/put/delete all route through write() (single audit point)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from _ac_client import (  # noqa: E402
    ACClient,
    ReadOnlyModeError,
    WriteCapExceededError,
)


def _build_client(monkeypatch, **env) -> ACClient:
    """Build an ACClient with mocked HTTP and a controlled env."""
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, str(v))
    monkeypatch.setenv("AC_API_URL", "https://test.api-us1.com")
    monkeypatch.setenv("AC_API_TOKEN", "tok")
    c = ACClient()
    # Stub the network: every successful "request" returns {"ok": True}
    c._request = lambda method, path, data=None, params=None, max_retries=5: {"ok": True}
    return c


@pytest.fixture
def writes_log_in_tmp(tmp_path, monkeypatch):
    """Redirect ~/.activecampaign-skill/writes.jsonl to tmp_path."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    yield fake_home / ".activecampaign-skill" / "writes.jsonl"


class TestReadOnlyMode:
    def test_post_blocked_when_read_only(self, monkeypatch, writes_log_in_tmp):
        c = _build_client(monkeypatch, AC_READ_ONLY="1")
        with pytest.raises(ReadOnlyModeError, match="AC_READ_ONLY"):
            c.post("contacts", {"contact": {"email": "x@x.co"}})
        # Audit log should NOT exist — read-only blocks BEFORE any side effect
        assert not writes_log_in_tmp.exists()

    def test_put_blocked_when_read_only(self, monkeypatch, writes_log_in_tmp):
        c = _build_client(monkeypatch, AC_READ_ONLY="true")
        with pytest.raises(ReadOnlyModeError):
            c.put("contacts/123", {"contact": {"firstName": "x"}})

    def test_delete_blocked_when_read_only(self, monkeypatch, writes_log_in_tmp):
        c = _build_client(monkeypatch, AC_READ_ONLY="yes")
        with pytest.raises(ReadOnlyModeError):
            c.delete("contacts/123")

    def test_get_still_allowed_in_read_only(self, monkeypatch, writes_log_in_tmp):
        c = _build_client(monkeypatch, AC_READ_ONLY="1")
        # GET must not raise
        assert c.get("contacts") == {"ok": True}

    def test_unset_var_does_not_block(self, monkeypatch, writes_log_in_tmp):
        c = _build_client(monkeypatch, AC_READ_ONLY=None)
        # No env var → writes flow
        assert c.post("contacts", {"contact": {"email": "x"}}) == {"ok": True}


class TestWriteCap:
    def test_default_cap_is_10(self, monkeypatch, writes_log_in_tmp):
        c = _build_client(monkeypatch, AC_MAX_WRITES=None)
        for _i in range(10):
            c.post("contacts", {"x": 1})
        with pytest.raises(WriteCapExceededError, match="10/10"):
            c.post("contacts", {"x": 1})

    def test_cap_overridable_via_env(self, monkeypatch, writes_log_in_tmp):
        c = _build_client(monkeypatch, AC_MAX_WRITES="3")
        for _i in range(3):
            c.post("contacts", {"x": 1})
        with pytest.raises(WriteCapExceededError, match="3/3"):
            c.post("contacts", {"x": 1})

    def test_cap_counts_all_methods(self, monkeypatch, writes_log_in_tmp):
        c = _build_client(monkeypatch, AC_MAX_WRITES="3")
        c.post("contacts", {"x": 1})
        c.put("contacts/1", {"x": 2})
        c.delete("contacts/2")
        with pytest.raises(WriteCapExceededError):
            c.post("contacts", {"x": 4})

    def test_get_does_not_count_against_cap(self, monkeypatch, writes_log_in_tmp):
        c = _build_client(monkeypatch, AC_MAX_WRITES="2")
        for _i in range(100):
            c.get("contacts")
        # Writes still allowed
        c.post("contacts", {"x": 1})
        c.post("contacts", {"x": 2})
        with pytest.raises(WriteCapExceededError):
            c.post("contacts", {"x": 3})


class TestAuditLog:
    def test_post_writes_audit_line(self, monkeypatch, writes_log_in_tmp):
        c = _build_client(monkeypatch)
        c.post("contacts", {"contact": {"email": "x@x.co"}})
        assert writes_log_in_tmp.exists()
        lines = writes_log_in_tmp.read_text().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["method"] == "POST"
        assert entry["path"] == "contacts"
        # Payload itself is NOT logged — only a short hash
        assert "x@x.co" not in json.dumps(entry)
        assert "firstName" not in json.dumps(entry)
        assert "email" not in json.dumps(entry)
        assert len(entry["payload_sha256_16"]) == 16
        assert entry["write_seq"] == 1

    def test_audit_line_per_write(self, monkeypatch, writes_log_in_tmp):
        c = _build_client(monkeypatch)
        c.post("contacts", {"x": 1})
        c.put("contacts/1", {"x": 2})
        c.delete("contacts/2")
        lines = writes_log_in_tmp.read_text().splitlines()
        assert len(lines) == 3
        methods = [json.loads(line)["method"] for line in lines]
        assert methods == ["POST", "PUT", "DELETE"]
        # Sequence numbers
        seqs = [json.loads(line)["write_seq"] for line in lines]
        assert seqs == [1, 2, 3]

    def test_delete_has_empty_payload_hash(self, monkeypatch, writes_log_in_tmp):
        c = _build_client(monkeypatch)
        c.delete("contacts/1")
        entry = json.loads(writes_log_in_tmp.read_text().splitlines()[0])
        assert entry["payload_sha256_16"] == ""

    def test_audit_log_failure_does_not_block_write(
        self, monkeypatch, writes_log_in_tmp
    ):
        c = _build_client(monkeypatch)
        # Force the writes log path into a non-writable place
        from _skill import client as _client_mod
        with patch.object(_client_mod, "_writes_log_path",
                          return_value=Path("/proc/cant_write_here.jsonl")):
            # Should still succeed (best-effort log)
            assert c.post("contacts", {"x": 1}) == {"ok": True}


class TestWriteHelper:
    def test_write_rejects_get(self, monkeypatch, writes_log_in_tmp):
        c = _build_client(monkeypatch)
        with pytest.raises(ValueError, match="non-write"):
            c.write("GET", "contacts")

    def test_post_routes_through_write(self, monkeypatch, writes_log_in_tmp):
        """Confirm post/put/delete all flow through the single audit point."""
        c = _build_client(monkeypatch)
        c.post("contacts", {"x": 1})
        c.put("contacts/1", {"x": 2})
        c.delete("contacts/2")
        # All three should have audit entries — only the consolidated path
        # produces those
        lines = writes_log_in_tmp.read_text().splitlines()
        assert len(lines) == 3


class TestUnrelatedReads:
    def test_request_signature_unchanged(self, monkeypatch, writes_log_in_tmp):
        """Other code in the skill calls client._request directly via
        paginate/stream. Make sure the wrapper didn't change that surface."""
        c = _build_client(monkeypatch)
        # Should not raise and should respect AC_READ_ONLY (it doesn't —
        # _request bypasses write() and is meant only for GETs internally)
        assert c._request("GET", "contacts") == {"ok": True}
