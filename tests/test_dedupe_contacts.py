"""Tests for dedupe_contacts.find_duplicates()."""
from __future__ import annotations

import dedupe_contacts


def test_email_case_duplicates():
    contacts = [
        {"id": "1", "email": "Alice@Acme.com"},
        {"id": "2", "email": "alice@acme.com"},
        {"id": "3", "email": "bob@beta.com"},
    ]
    d = dedupe_contacts.find_duplicates(contacts)
    assert len(d["email_case_duplicates"]) == 1
    assert "alice@acme.com" in d["email_case_duplicates"]


def test_phone_normalized_match():
    contacts = [
        {"id": "1", "email": "a@x.com", "phone": "(415) 555-1234"},
        {"id": "2", "email": "b@y.com", "phone": "415-555-1234"},
        {"id": "3", "email": "c@z.com", "phone": "+1 415 555 1234"},
    ]
    d = dedupe_contacts.find_duplicates(contacts)
    assert len(d["phone_duplicates"]) == 1


def test_name_dupes_with_distinct_emails():
    contacts = [
        {"id": "1", "email": "j.smith@a.com", "firstName": "John", "lastName": "Smith"},
        {"id": "2", "email": "john.smith@b.com", "firstName": "John", "lastName": "Smith"},
        {"id": "3", "email": "jane@c.com", "firstName": "Jane", "lastName": "Smith"},
    ]
    d = dedupe_contacts.find_duplicates(contacts)
    assert "john|smith" in d["name_duplicates_distinct_email"]


def test_render():
    out = dedupe_contacts.render_markdown(
        {"email_case_duplicates": {}, "phone_duplicates": {}, "name_duplicates_distinct_email": {}},
        total=0,
    )
    assert "No duplicates detected" in out
