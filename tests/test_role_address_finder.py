"""Tests for role_address_finder.find_role_addresses()."""
from __future__ import annotations

import role_address_finder


def test_finds_role_local_parts():
    contacts = [
        {"id": "1", "email": "info@acme.com"},
        {"id": "2", "email": "support@acme.com"},
        {"id": "3", "email": "alice@acme.com"},
        {"id": "4", "email": "noreply@acme.com"},
    ]
    matches = role_address_finder.find_role_addresses(contacts)
    emails = {m["email"] for m in matches}
    assert emails == {"info@acme.com", "support@acme.com", "noreply@acme.com"}


def test_case_insensitive():
    contacts = [{"id": "1", "email": "INFO@Acme.COM"}]
    matches = role_address_finder.find_role_addresses(contacts)
    assert len(matches) == 1


def test_skips_non_email():
    contacts = [{"id": "1", "email": "not-an-email"}, {"id": "2", "email": ""}]
    matches = role_address_finder.find_role_addresses(contacts)
    assert matches == []


def test_render_no_matches():
    out = role_address_finder.render_markdown([], 100)
    assert "No role addresses detected" in out
