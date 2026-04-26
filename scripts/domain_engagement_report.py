#!/usr/bin/env python3
"""
domain_engagement_report.py — Open / click / bounce rates by recipient domain.

Joins messageActivity events to contacts, groups by email domain.
Catches one mailbox provider rate-limiting or filtering you.

Usage:
  python3 domain_engagement_report.py
  python3 domain_engagement_report.py --top 25 --format json
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from _ac_client import ACClient


def fetch(client: ACClient, max_events: int) -> dict:
    activities = client.fetch_engagement_events(max_items=max_events)
    contacts = client.paginate("contacts", "contacts", max_items=20000)
    bounces = client.paginate("bounceLogs", "bounceLogs", max_items=20000)
    return {"activities": activities, "contacts": contacts, "bounces": bounces}


def analyze(data: dict, top: int) -> dict:
    email_by_id = {str(c["id"]): (c.get("email") or "").lower() for c in data["contacts"]}

    def _domain(cid):
        e = email_by_id.get(str(cid)) or ""
        return e.split("@", 1)[1] if "@" in e else None

    open_by_domain = defaultdict(int)
    click_by_domain = defaultdict(int)
    send_by_domain = defaultdict(int)
    contacts_by_domain = defaultdict(int)
    for c in data["contacts"]:
        e = (c.get("email") or "").lower()
        if "@" in e:
            contacts_by_domain[e.split("@", 1)[1]] += 1

    for a in data["activities"]:
        d = _domain(a.get("contact"))
        if not d:
            continue
        ev = a.get("event")
        if ev == "open":
            open_by_domain[d] += 1
        elif ev == "click":
            click_by_domain[d] += 1
        elif ev == "send":
            send_by_domain[d] += 1

    bounce_by_domain = defaultdict(int)
    for b in data["bounces"]:
        d = _domain(b.get("contact"))
        if d:
            bounce_by_domain[d] += 1

    rows = []
    for d, count in sorted(contacts_by_domain.items(), key=lambda x: -x[1])[:top]:
        rows.append({
            "domain": d,
            "contacts": count,
            "opens": open_by_domain.get(d, 0),
            "clicks": click_by_domain.get(d, 0),
            "bounces": bounce_by_domain.get(d, 0),
        })
    return {"domains": rows, "total_open_events": sum(open_by_domain.values())}


def render_markdown(r: dict) -> str:
    lines = [
        "# Domain Engagement Report",
        "",
        f"Total open events analyzed: {r['total_open_events']}",
        "",
        "| Domain | Contacts | Opens | Clicks | Bounces |",
        "|---|---|---|---|---|",
    ]
    for d in r["domains"]:
        lines.append(f"| {d['domain']} | {d['contacts']} | {d['opens']} | {d['clicks']} | {d['bounces']} |")
    if not r["domains"]:
        lines.append("_(No data.)_")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Engagement by recipient domain")
    parser.add_argument("--top", type=int, default=25)
    parser.add_argument("--max-events", type=int, default=20000)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    client = ACClient()
    data = fetch(client, args.max_events)
    r = analyze(data, args.top)
    out = json.dumps(r, indent=2) if args.format == "json" else render_markdown(r)
    if args.output:
        Path(args.output).write_text(out)
        print(f"Wrote {args.output}")
    else:
        print(out)


if __name__ == "__main__":
    main()
