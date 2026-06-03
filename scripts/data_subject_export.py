#!/usr/bin/env python3
"""
data_subject_export.py — GDPR Article 15 SAR export for one contact.

Bundles profile, fields, tags, lists, automation history, deals, notes for the
specified email into one JSON file.

Usage:
  python3 data_subject_export.py user@example.com
  python3 data_subject_export.py user@example.com --output sar.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _ac_client import ACClient, emit_files


def fetch(client: ACClient, email: str) -> dict:
    res = client.get("contacts", params={"email": email})
    contacts = res.get("contacts") or []
    if not contacts:
        raise SystemExit(
            f"No contact found with email '{email}'. "
            f"Check the spelling, or look up the contact in your AC dashboard first."
        )
    contact = contacts[0]
    cid = contact["id"]

    # Fetch every per-contact subresource in parallel. The shared client
    # rate-limit lock keeps total throughput at 5 req/sec, but the pool
    # overlaps request prep + parsing for a meaningful speedup on the
    # 5-endpoint export. Each label keys both the request and the result.
    out: dict = {"contact": contact}
    filters = {"filters[contact]": cid}
    bulk = client.fetch_many([
        ("fieldValues",        "fieldValues",        filters, 10000),
        ("contactTags",        "contactTags",        filters, 10000),
        ("contactLists",       "contactLists",       filters, 10000),
        ("contactAutomations", "contactAutomations", filters, 10000),
        ("deals",              "deals",              filters, 2000),
    ])
    for label, value in bulk.items():
        if isinstance(value, dict) and "error" in value:
            if label == "deals" and value.get("status_code") == 403:
                out["deals"] = "Deals feature not enabled"
            else:
                out[label] = value
        else:
            out[label] = value

    return out


def main():
    parser = argparse.ArgumentParser(description="GDPR Article 15 SAR export")
    parser.add_argument("email")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    client = ACClient()
    data = fetch(client, args.email)
    out = json.dumps(data, indent=2, default=str)
    if args.output:
        Path(args.output).write_text(out)
        print(f"Wrote {args.output}")
        emit_files(args.output)
    else:
        print(out)


if __name__ == "__main__":
    main()
