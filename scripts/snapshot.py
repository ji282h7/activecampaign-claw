#!/usr/bin/env python3
"""
snapshot.py — Versioned weekly account snapshot.

Wraps export_account.py with a date-stamped filename and a manifest entry.
Pairs with schema_diff.py for "what changed since last week".

Usage:
  python3 snapshot.py
  python3 snapshot.py --scope all --dir ~/.activecampaign-skill/snapshots
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from _ac_client import ACClient
from export_account import fetch as export_fetch  # type: ignore

DEFAULT_DIR = Path.home() / ".activecampaign-skill" / "snapshots"


def main():
    parser = argparse.ArgumentParser(description="Versioned account snapshot")
    parser.add_argument("--scope", choices=["taxonomy", "contacts", "deals", "all"], default="taxonomy")
    parser.add_argument("--dir", default=str(DEFAULT_DIR))
    args = parser.parse_args()

    out_dir = Path(args.dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"snapshot-{stamp}-{args.scope}.json"

    client = ACClient()
    data = export_fetch(client, args.scope)
    out_path.write_text(json.dumps(data, indent=2, default=str))
    sz = out_path.stat().st_size

    manifest = out_dir / "manifest.jsonl"
    with manifest.open("a") as f:
        f.write(json.dumps({
            "snapshot": out_path.name,
            "stamp": stamp,
            "scope": args.scope,
            "bytes": sz,
            "counts": {
                "lists": len(data.get("taxonomy", {}).get("lists", [])),
                "tags": len(data.get("taxonomy", {}).get("tags", [])),
                "fields": len(data.get("taxonomy", {}).get("fields", [])),
                "automations": len(data.get("taxonomy", {}).get("automations", [])),
                "contacts": len(data.get("contacts", [])) if "contacts" in data else None,
                "deals": len(data.get("deals", [])) if "deals" in data else None,
            },
        }) + "\n")
    print(f"Wrote {out_path} ({sz:,} bytes)")


if __name__ == "__main__":
    main()
