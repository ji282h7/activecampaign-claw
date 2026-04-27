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

from _ac_client import ACClient, ACClientError, emit_files


def fetch(client: ACClient, email: str) -> dict:
    res = client.get("contacts", params={"email": email})
    contacts = res.get("contacts") or []
    if not contacts:
        raise SystemExit(f"ERROR: no contact found with email {email}")
    contact = contacts[0]
    cid = contact["id"]

    out = {"contact": contact}
    for endpoint, key in [
        ("fieldValues", "fieldValues"),
        ("contactTags", "contactTags"),
        ("contactLists", "contactLists"),
        ("contactAutomations", "contactAutomations"),
    ]:
        try:
            r = client.paginate(endpoint, key, params={"filters[contact]": cid}, max_items=10000)
            out[key] = r
        except ACClientError as e:
            out[key] = {"error": str(e)}

    # deals (may 403 on accounts without Deals)
    try:
        deals = client.paginate("deals", "deals", params={"filters[contact]": cid}, max_items=2000)
        out["deals"] = deals
    except ACClientError as e:
        out["deals"] = {"error": str(e)} if e.status_code != 403 else "Deals feature not enabled"

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
