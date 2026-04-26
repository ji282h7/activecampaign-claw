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


def test_accepts_generator_input():
    def gen():
        yield {"id": "1", "email": "Alice@Acme.com"}
        yield {"id": "2", "email": "alice@acme.com"}
        yield {"id": "3", "email": "bob@beta.com"}

    d = dedupe_contacts.find_duplicates(gen())
    assert d["scanned"] == 3
    assert "alice@acme.com" in d["email_case_duplicates"]


def test_singletons_dropped_from_output():
    # Most contacts are unique; only one duplicate group should appear in the output.
    contacts = [{"id": str(i), "email": f"u{i}@x.com"} for i in range(100)]
    contacts.append({"id": "101", "email": "U0@X.com"})  # case-collide with id=0
    d = dedupe_contacts.find_duplicates(contacts)
    assert d["scanned"] == 101
    assert len(d["email_case_duplicates"]) == 1
    assert "u0@x.com" in d["email_case_duplicates"]
    # The 99 unique singletons must not appear in the output
    assert all(k == "u0@x.com" for k in d["email_case_duplicates"])


def test_stored_records_are_slim():
    # Even if input has many fields, output records keep only id + email.
    contacts = [
        {"id": "1", "email": "a@x.com", "firstName": "Alice", "phone": "555-1234",
         "fields": "tons of stuff", "lastEngaged": "2026-01-01"},
        {"id": "2", "email": "A@X.com", "firstName": "Alice", "phone": "555-5678"},
    ]
    d = dedupe_contacts.find_duplicates(contacts)
    cs = d["email_case_duplicates"]["a@x.com"]
    for record in cs:
        assert set(record.keys()) == {"id", "email"}
