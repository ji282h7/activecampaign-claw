"""Tests for accounts_audit.analyze().

Per AC v3 docs:
  /accounts -> { accounts: [{ id, name, accountUrl, owner, createdTimestamp,
                              updatedTimestamp, fields, contactCount,
                              dealCount }] }
  /accountContacts -> { accountContacts: [{ id, contact, account,
                                            jobTitle, cdate, udate }] }
  contactCount and dealCount appear when ?count_deals=true is passed.
"""
from __future__ import annotations

from datetime import datetime, timezone

import accounts_audit


def _now():
    return datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)


def test_unavailable_path():
    r = accounts_audit.analyze(
        {"unavailable": True, "reason": "accounts_feature_not_enabled"},
        now=_now(),
    )
    md = accounts_audit.render_markdown(r)
    assert "B2B Accounts not available" in md


def test_orphaned_and_no_pipeline_buckets():
    data = {
        "unavailable": False,
        "accounts": [
            {"id": "1", "name": "Acme", "owner": "1",
             "contactCount": 10, "dealCount": 3,
             "createdTimestamp": "2026-04-01T00:00:00+0000",
             "updatedTimestamp": "2026-05-01T00:00:00+0000"},
            {"id": "2", "name": "Orphan", "owner": "1",
             "contactCount": 0, "dealCount": 0,
             "createdTimestamp": "2026-01-01T00:00:00+0000",
             "updatedTimestamp": "2026-01-01T00:00:00+0000"},
            {"id": "3", "name": "NoDeals", "owner": "2",
             "contactCount": 5, "dealCount": 0,
             "createdTimestamp": "2026-04-01T00:00:00+0000",
             "updatedTimestamp": "2026-04-15T00:00:00+0000"},
        ],
        "account_contacts": [],
        "users": [
            {"id": "1", "firstName": "Ada", "lastName": "L", "email": "a@x.co"},
            {"id": "2", "firstName": "Bert", "lastName": "Z", "email": "b@x.co"},
        ],
    }
    r = accounts_audit.analyze(data, stale_days=90, now=_now())
    assert {a["id"] for a in r["orphaned"]} == {"2"}
    assert {a["id"] for a in r["no_pipeline"]} == {"3"}


def test_top_by_deals_sorted():
    data = {
        "unavailable": False,
        "accounts": [
            {"id": "1", "name": "Big", "owner": "1",
             "contactCount": 1, "dealCount": 10,
             "updatedTimestamp": "2026-05-01"},
            {"id": "2", "name": "Mid", "owner": "1",
             "contactCount": 1, "dealCount": 5,
             "updatedTimestamp": "2026-05-01"},
            {"id": "3", "name": "Small", "owner": "1",
             "contactCount": 1, "dealCount": 1,
             "updatedTimestamp": "2026-05-01"},
        ],
        "account_contacts": [],
        "users": [],
    }
    r = accounts_audit.analyze(data, now=_now())
    assert [a["id"] for a in r["top_by_deals"][:3]] == ["1", "2", "3"]


def test_owner_rollup():
    data = {
        "unavailable": False,
        "accounts": [
            {"id": "1", "name": "A", "owner": "1",
             "contactCount": 3, "dealCount": 2,
             "updatedTimestamp": "2026-05-01"},
            {"id": "2", "name": "B", "owner": "1",
             "contactCount": 1, "dealCount": 1,
             "updatedTimestamp": "2026-05-01"},
            {"id": "3", "name": "C", "owner": "2",
             "contactCount": 5, "dealCount": 0,
             "updatedTimestamp": "2026-05-01"},
        ],
        "account_contacts": [],
        "users": [
            {"id": "1", "firstName": "Ada", "lastName": "L", "email": "a@x.co"},
            {"id": "2", "firstName": "Bert", "lastName": "Z", "email": "b@x.co"},
        ],
    }
    r = accounts_audit.analyze(data, now=_now())
    by_owner = {row["owner_name"]: row for row in r["owner_rollup"]}
    assert by_owner["Ada L"]["accounts"] == 2
    assert by_owner["Ada L"]["deals"] == 3
    assert by_owner["Bert Z"]["accounts"] == 1


def test_account_contacts_counted_when_count_deals_missing():
    # Some accounts return without contactCount; we fall back to /accountContacts
    data = {
        "unavailable": False,
        "accounts": [
            {"id": "1", "name": "A", "owner": "1", "dealCount": 0,
             "updatedTimestamp": "2026-05-01"},
        ],
        "account_contacts": [
            {"id": "x1", "contact": "100", "account": "1"},
            {"id": "x2", "contact": "101", "account": "1"},
        ],
        "users": [],
    }
    r = accounts_audit.analyze(data, now=_now())
    by_id = {a["id"]: a for a in r["top_by_contacts"]}
    assert by_id["1"]["contact_count"] == 2
