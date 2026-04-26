#!/usr/bin/env python3
"""
link_performance.py — Per-link performance for a campaign.

Usage:
  python3 link_performance.py <campaign_id>
  python3 link_performance.py 42 --format json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _ac_client import ACClient


def _safe_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def fetch(client: ACClient, campaign_id: str) -> dict:
    campaign = client.get(f"campaigns/{campaign_id}").get("campaign", {})
    links = client.paginate(f"campaigns/{campaign_id}/links", "links", max_items=2000)
    return {"campaign": campaign, "links": links}


def analyze(data: dict) -> dict:
    c = data["campaign"]
    unique_opens = _safe_int(c.get("uniqueopens"))
    sent = _safe_int(c.get("send_amt"))

    rows = []
    total_unique_clicks = 0
    for l in data["links"]:
        uc = _safe_int(l.get("uniquelinkclicks"))
        rows.append({
            "link_id": l.get("id"),
            "url": l.get("link"),
            "name": l.get("name") or "",
            "tracked": l.get("tracked"),
            "clicks": _safe_int(l.get("linkclicks")),
            "unique_clicks": uc,
            "ctr_of_recipients": (uc / sent) if sent else 0,
            "ctr_of_opens": (uc / unique_opens) if unique_opens else 0,
        })
        total_unique_clicks += uc
    rows.sort(key=lambda x: -x["unique_clicks"])
    return {
        "campaign_id": c.get("id"),
        "campaign_name": c.get("name"),
        "total_links": len(rows),
        "total_unique_clicks": total_unique_clicks,
        "links": rows,
    }


def render_markdown(r: dict) -> str:
    lines = [
        f"# Link Performance: {r['campaign_name']} (id={r['campaign_id']})",
        "",
        f"- Total links: {r['total_links']}",
        f"- Total unique clicks: {r['total_unique_clicks']}",
        "",
        "| Link | Clicks | Unique | CTR (sent) | CTR (opens) |",
        "|---|---|---|---|---|",
    ]
    for l in r["links"]:
        url = (l["url"] or l["name"] or "")[:80]
        lines.append(
            f"| {url} | {l['clicks']} | {l['unique_clicks']} | "
            f"{l['ctr_of_recipients']*100:.2f}% | {l['ctr_of_opens']*100:.1f}% |"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Per-link performance")
    parser.add_argument("campaign_id")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    client = ACClient()
    data = fetch(client, args.campaign_id)
    r = analyze(data)
    out = json.dumps(r, indent=2) if args.format == "json" else render_markdown(r)
    if args.output:
        Path(args.output).write_text(out)
        print(f"Wrote {args.output}")
    else:
        print(out)


if __name__ == "__main__":
    main()
