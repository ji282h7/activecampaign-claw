#!/usr/bin/env python3
"""
send_frequency_report.py — Distribution of sends-per-contact-per-30-days.

Counts how many distinct sends each contact received in the trailing window.
Flags fatigued (>8/month) and forgotten (<1/month) contacts.

Usage:
  python3 send_frequency_report.py
  python3 send_frequency_report.py --window-days 30 --format json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from _ac_client import ACClient


def _parse_iso(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def fetch(client: ACClient, window_days: int, max_events: int) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    activities = client.fetch_engagement_events(max_items=max_events)
    contacts = client.paginate("contacts", "contacts", max_items=10000)
    return {"activities": activities, "contacts": contacts, "cutoff": cutoff}


def analyze(data: dict, window_days: int) -> dict:
    sends_per_contact = Counter()
    for a in data["activities"]:
        ts = _parse_iso(a.get("tstamp"))
        if not ts or ts < data["cutoff"]:
            continue
        cid = a.get("contact")
        if cid:
            sends_per_contact[cid] += 1

    distribution = Counter()
    for n in sends_per_contact.values():
        distribution[n] += 1

    total_contacts = len(data["contacts"])
    contacts_with_sends = len(sends_per_contact)
    contacts_no_sends = total_contacts - contacts_with_sends
    over_threshold = sum(1 for n in sends_per_contact.values() if n > 8)
    return {
        "window_days": window_days,
        "total_contacts": total_contacts,
        "contacts_with_sends_in_window": contacts_with_sends,
        "contacts_with_no_sends": contacts_no_sends,
        "fatigued_count_gt8": over_threshold,
        "distribution": dict(sorted(distribution.items())),
    }


def render_markdown(r: dict) -> str:
    lines = [
        f"# Send Frequency Report (last {r['window_days']} days)",
        "",
        f"- Total contacts: {r['total_contacts']:,}",
        f"- Contacts who received >=1 send: {r['contacts_with_sends_in_window']:,}",
        f"- Contacts with no sends in window: {r['contacts_with_no_sends']:,}",
        f"- Fatigue risk (>8 sends in window): **{r['fatigued_count_gt8']}**",
        "",
        "## Distribution",
        "| Sends in window | Contacts |",
        "|---|---|",
    ]
    for k, v in r["distribution"].items():
        lines.append(f"| {k} | {v} |")
    if not r["distribution"]:
        lines.append("_(No send activity events available.)_")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Sends per contact distribution")
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--max-events", type=int, default=20000)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    client = ACClient()
    data = fetch(client, args.window_days, args.max_events)
    r = analyze(data, args.window_days)
    out = json.dumps(r, indent=2, default=str) if args.format == "json" else render_markdown(r)
    if args.output:
        Path(args.output).write_text(out)
        print(f"Wrote {args.output}")
    else:
        print(out)


if __name__ == "__main__":
    main()
