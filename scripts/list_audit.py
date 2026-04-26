#!/usr/bin/env python3
"""
list_audit.py — Per-list health: subscriber count, last campaign sent, opt-in source.

Identifies lists you can retire (no recent campaigns, low subscriber count).

Usage:
  python3 list_audit.py
  python3 list_audit.py --format json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from _ac_client import ACClient


def _days_since(iso_str: str | None) -> float | None:
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 86400
    except (ValueError, TypeError):
        return None


def fetch(client: ACClient) -> dict:
    lists = client.paginate("lists", "lists", max_items=2000)
    contact_lists = client.paginate("contactLists", "contactLists", max_items=100000)
    campaigns = client.paginate("campaigns", "campaigns", max_items=2000)
    return {"lists": lists, "contact_lists": contact_lists, "campaigns": campaigns}


def analyze(data: dict) -> dict:
    by_list_active = Counter()  # status 1 = active
    by_list_unsub = Counter()
    by_list_bounce = Counter()
    for cl in data["contact_lists"]:
        lid = str(cl.get("list"))
        status = str(cl.get("status"))
        if status == "1":
            by_list_active[lid] += 1
        elif status == "2":
            by_list_unsub[lid] += 1
        elif status == "3":
            by_list_bounce[lid] += 1

    # last campaign per list (campaigns can target multiple lists via /campaignLists, but
    # `campaigns` resource often has list info inline as a list of ids)
    last_campaign = {}  # list_id -> (campaign_id, sdate)
    for c in data["campaigns"]:
        sdate = c.get("sdate") or c.get("ldate") or c.get("cdate")
        # campaign object may link to lists via various fields; many AC accounts surface "lists" array
        l_field = c.get("lists") or []
        if isinstance(l_field, list):
            target_lists = [str(x.get("list") if isinstance(x, dict) else x) for x in l_field]
        else:
            target_lists = []
        for lid in target_lists:
            cur = last_campaign.get(lid)
            if not cur or (sdate and sdate > cur[1]):
                last_campaign[lid] = (c.get("id"), sdate)

    rows = []
    for l in data["lists"]:
        lid = str(l["id"])
        active = by_list_active.get(lid, 0)
        unsub = by_list_unsub.get(lid, 0)
        bounce = by_list_bounce.get(lid, 0)
        total = active + unsub + bounce
        last = last_campaign.get(lid)
        last_sent = last[1] if last else None
        days = _days_since(last_sent) if last_sent else None
        rows.append({
            "id": lid,
            "name": l.get("name", ""),
            "active": active,
            "unsubscribed": unsub,
            "bounced": bounce,
            "total": total,
            "last_campaign_sent": last_sent,
            "days_since_last_send": int(days) if days is not None else None,
            "stale": days is None or days > 90,
        })
    rows.sort(key=lambda x: -x["active"])
    return {"lists": rows, "stale_count": sum(1 for r in rows if r["stale"])}


def render_markdown(r: dict) -> str:
    lines = [
        "# List Audit",
        "",
        f"- Total lists: {len(r['lists'])}",
        f"- Stale (no campaign in 90+ days or never): **{r['stale_count']}**",
        "",
        "| List | Active | Unsub | Bounce | Total | Days since last send |",
        "|---|---|---|---|---|---|",
    ]
    for l in r["lists"]:
        days = l["days_since_last_send"]
        days_s = "never" if days is None else f"{days}"
        lines.append(
            f"| {l['name']} | {l['active']} | {l['unsubscribed']} | "
            f"{l['bounced']} | {l['total']} | {days_s} |"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit list health")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    client = ACClient()
    data = fetch(client)
    r = analyze(data)
    out = json.dumps(r, indent=2) if args.format == "json" else render_markdown(r)
    if args.output:
        Path(args.output).write_text(out)
        print(f"Wrote {args.output}")
    else:
        print(out)


if __name__ == "__main__":
    main()
