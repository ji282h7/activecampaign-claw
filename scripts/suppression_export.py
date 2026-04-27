#!/usr/bin/env python3
"""
suppression_export.py — Export all suppressed contacts (unsub, bounce) with timestamps.

Required for compliance audits and ESP migration. Pulls contacts with
status 2 (unsubscribed) and 3 (bounced) plus bounce log details.

Usage:
  python3 suppression_export.py
  python3 suppression_export.py --format json --output suppression.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from _ac_client import ACClient, emit_files


def fetch(client: ACClient) -> dict:
    unsubs = client.paginate("contacts", "contacts", params={"status": 2}, max_items=20000)
    bounces = client.paginate("contacts", "contacts", params={"status": 3}, max_items=20000)
    bounce_logs = client.paginate("bounceLogs", "bounceLogs", max_items=20000)
    return {"unsubs": unsubs, "bounces": bounces, "bounce_logs": bounce_logs}


def analyze(data: dict) -> dict:
    bounce_reasons = Counter()
    bounces_by_contact = {}
    for b in data["bounce_logs"]:
        cid = str(b.get("contact"))
        reason = b.get("bounceCode") or b.get("error") or "unknown"
        bounce_reasons[reason] += 1
        bounces_by_contact[cid] = {
            "code": b.get("bounceCode"),
            "error": b.get("error"),
            "tstamp": b.get("tstamp"),
        }

    unsubs = [
        {
            "id": c["id"],
            "email": c.get("email"),
            "udate": c.get("udate"),
            "cdate": c.get("cdate"),
        }
        for c in data["unsubs"]
    ]
    bounces = [
        {
            "id": c["id"],
            "email": c.get("email"),
            "bounce": bounces_by_contact.get(str(c["id"])),
        }
        for c in data["bounces"]
    ]

    return {
        "unsubscribed_count": len(unsubs),
        "bounced_count": len(bounces),
        "bounce_reason_breakdown": dict(bounce_reasons.most_common(20)),
        "unsubs": unsubs,
        "bounces": bounces,
    }


def render_markdown(r: dict) -> str:
    lines = [
        "# Suppression Export",
        "",
        f"- Unsubscribed: **{r['unsubscribed_count']}**",
        f"- Bounced: **{r['bounced_count']}**",
        "",
    ]
    if r["bounce_reason_breakdown"]:
        lines.append("## Bounce reason breakdown")
        for code, n in r["bounce_reason_breakdown"].items():
            lines.append(f"- {code}: {n}")
        lines.append("")
    if r["unsubs"]:
        lines.append(f"## Unsubscribed contacts (showing first 100 of {r['unsubscribed_count']})")
        lines.append("| ID | Email | Updated |")
        lines.append("|---|---|---|")
        for u in r["unsubs"][:100]:
            lines.append(f"| {u['id']} | {u['email']} | {u['udate']} |")
        lines.append("")
    if r["bounces"]:
        lines.append(f"## Bounced contacts (showing first 100 of {r['bounced_count']})")
        lines.append("| ID | Email | Code |")
        lines.append("|---|---|---|")
        for b in r["bounces"][:100]:
            code = (b["bounce"] or {}).get("code", "—")
            lines.append(f"| {b['id']} | {b['email']} | {code} |")
        lines.append("")
    if not r["unsubs"] and not r["bounces"]:
        lines.append("No suppressed contacts found.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Export suppressed contacts")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    client = ACClient()
    data = fetch(client)
    r = analyze(data)
    out = json.dumps(r, indent=2, default=str) if args.format == "json" else render_markdown(r)
    if args.output:
        Path(args.output).write_text(out)
        print(f"Wrote {args.output}")
        emit_files(args.output)
    else:
        print(out)


if __name__ == "__main__":
    main()
