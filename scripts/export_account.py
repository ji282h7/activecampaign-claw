#!/usr/bin/env python3
"""
export_account.py — Full account snapshot to JSON.

Bundles taxonomy (lists, tags, fields, pipelines, automations), and optionally
contacts and deals. Disaster-recovery / audit / migration / pre-change baseline.

Usage:
  python3 export_account.py --scope taxonomy
  python3 export_account.py --scope all --output snap.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from _ac_client import ACClient, ACClientError, emit_files


def _try_paginate(client, path, key, **kwargs):
    try:
        return client.paginate(path, key, **kwargs)
    except ACClientError as e:
        if e.status_code in (403, 404):
            return []
        raise


def fetch(client: ACClient, scope: str) -> dict:
    out = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": 1,
        "taxonomy": {
            "lists": _try_paginate(client, "lists", "lists", max_items=2000),
            "tags": _try_paginate(client, "tags", "tags", max_items=10000),
            "fields": _try_paginate(client, "fields", "fields", max_items=2000),
            "pipelines": _try_paginate(client, "dealGroups", "dealGroups", max_items=200),
            "stages": _try_paginate(client, "dealStages", "dealStages", max_items=500),
            "automations": _try_paginate(client, "automations", "automations", max_items=2000),
            "messages": _try_paginate(client, "messages", "messages", max_items=5000),
            "forms": _try_paginate(client, "forms", "forms", max_items=500),
            "segments": _try_paginate(client, "segments", "segments", max_items=2000),
            "webhooks": _try_paginate(client, "webhooks", "webhooks", max_items=500),
        },
    }
    if scope in ("contacts", "all"):
        out["contacts"] = _try_paginate(client, "contacts", "contacts", max_items=50000)
        out["fieldValues"] = _try_paginate(client, "fieldValues", "fieldValues", max_items=200000)
        out["contactTags"] = _try_paginate(client, "contactTags", "contactTags", max_items=200000)
        out["contactLists"] = _try_paginate(client, "contactLists", "contactLists", max_items=200000)
    if scope in ("deals", "all"):
        out["deals"] = _try_paginate(client, "deals", "deals", max_items=50000)
        out["dealCustomFieldData"] = _try_paginate(client, "dealCustomFieldData", "dealCustomFieldData", max_items=200000)
    return out


def main():
    parser = argparse.ArgumentParser(description="Account snapshot")
    parser.add_argument("--scope", choices=["taxonomy", "contacts", "deals", "all"], default="taxonomy")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    client = ACClient()
    data = fetch(client, args.scope)
    out = json.dumps(data, indent=2, default=str)
    if args.output:
        Path(args.output).write_text(out)
        sz = Path(args.output).stat().st_size
        print(f"Wrote {args.output} ({sz:,} bytes)")
        emit_files(args.output)
    else:
        print(out)


if __name__ == "__main__":
    main()
