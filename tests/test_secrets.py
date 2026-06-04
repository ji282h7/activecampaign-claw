"""Tests for the credential resolver in _skill/secrets.py.

The resolver is intentionally graceful: if `keyring` isn't installed,
it silently degrades to env-var-only. Tests verify both paths plus the
precedence rule (env wins over keychain).
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from _skill import secrets  # noqa: E402


class _FakeKeyring:
    """In-memory stand-in for the `keyring` module."""

    def __init__(self):
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service, key):
        return self.store.get((service, key))

    def set_password(self, service, key, value):
        self.store[(service, key)] = value

    def delete_password(self, service, key):
        if (service, key) not in self.store:
            from keyring import errors
            raise errors.PasswordDeleteError()
        del self.store[(service, key)]


def test_env_var_wins_over_keychain(monkeypatch):
    fake = _FakeKeyring()
    fake.store[(secrets.SERVICE_NAME, "AC_API_TOKEN")] = "from-keychain"
    monkeypatch.setenv("AC_API_TOKEN", "from-env")
    with patch.dict(sys.modules, {"keyring": fake}):
        assert secrets.get_credential("AC_API_TOKEN") == "from-env"


def test_keychain_used_when_env_missing(monkeypatch):
    monkeypatch.delenv("AC_API_TOKEN", raising=False)
    fake = _FakeKeyring()
    fake.store[(secrets.SERVICE_NAME, "AC_API_TOKEN")] = "from-keychain"
    with patch.dict(sys.modules, {"keyring": fake}):
        assert secrets.get_credential("AC_API_TOKEN") == "from-keychain"


def test_returns_none_when_neither_set(monkeypatch):
    monkeypatch.delenv("AC_API_TOKEN", raising=False)
    fake = _FakeKeyring()
    with patch.dict(sys.modules, {"keyring": fake}):
        assert secrets.get_credential("AC_API_TOKEN") is None


def test_keyring_missing_degrades_silently(monkeypatch):
    """Without keyring installed, env var still works; keychain returns None."""
    monkeypatch.delenv("AC_API_TOKEN", raising=False)
    # Force import to fail
    with patch.dict(sys.modules, {"keyring": None}):
        assert secrets.get_credential("AC_API_TOKEN") is None
    monkeypatch.setenv("AC_API_TOKEN", "tok")
    with patch.dict(sys.modules, {"keyring": None}):
        assert secrets.get_credential("AC_API_TOKEN") == "tok"


def test_empty_env_string_falls_through_to_keychain(monkeypatch):
    """Empty / whitespace-only env vars don't shadow the keychain."""
    monkeypatch.setenv("AC_API_TOKEN", "   ")
    fake = _FakeKeyring()
    fake.store[(secrets.SERVICE_NAME, "AC_API_TOKEN")] = "real-token"
    with patch.dict(sys.modules, {"keyring": fake}):
        assert secrets.get_credential("AC_API_TOKEN") == "real-token"


def test_set_credential_requires_keyring(monkeypatch):
    import pytest
    with patch.dict(sys.modules, {"keyring": None}):
        with pytest.raises(RuntimeError, match=r"isn.t installed"):
            secrets.set_credential("AC_API_TOKEN", "x")


def test_describe_sources_reports_correctly(monkeypatch):
    monkeypatch.setenv("AC_API_URL", "https://x.api-us1.com")
    monkeypatch.delenv("AC_API_TOKEN", raising=False)
    fake = _FakeKeyring()
    fake.store[(secrets.SERVICE_NAME, "AC_API_TOKEN")] = "stored"
    with patch.dict(sys.modules, {"keyring": fake}):
        snap = secrets.describe_sources()
    assert snap["keyring_available"] is True
    assert snap["AC_API_URL"] == "env"
    assert snap["AC_API_TOKEN"] == "keychain"


def test_describe_sources_reports_missing(monkeypatch):
    monkeypatch.delenv("AC_API_URL", raising=False)
    monkeypatch.delenv("AC_API_TOKEN", raising=False)
    fake = _FakeKeyring()
    with patch.dict(sys.modules, {"keyring": fake}):
        snap = secrets.describe_sources()
    assert snap["AC_API_URL"] == "missing"
    assert snap["AC_API_TOKEN"] == "missing"


def test_has_keyring_when_installed(monkeypatch):
    fake = _FakeKeyring()
    with patch.dict(sys.modules, {"keyring": fake}):
        assert secrets.has_keyring() is True


def test_has_keyring_when_missing():
    with patch.dict(sys.modules, {"keyring": None}):
        assert secrets.has_keyring() is False
