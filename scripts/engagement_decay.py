#!/usr/bin/env python3
"""
engagement_decay.py — Cohort retention plot: of contacts joined month N,
what % opened a campaign in months N+1..N+12.

Usage:
  python3 engagement_decay.py
  python3 engagement_decay.py --months 12 --format json
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
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


def fetch(client: ACClient, max_events: int) -> dict:
    contacts = client.paginate("contacts", "contacts", max_items=20000)
    activities = client.fetch_engagement_events(max_items=max_events)
    return {"contacts": contacts, "activities": activities}


def analyze(data: dict, months: int) -> dict:
    cohort = {}  # contact_id -> created_month_key
    for c in data["contacts"]:
        d = _parse_iso(c.get("cdate"))
        if not d:
            continue
        cohort[str(c["id"])] = d.strftime("%Y-%m")

    cohort_size = defaultdict(int)
    for k in cohort.values():
        cohort_size[k] += 1

    # of those contacts, who opened in month N+i?
    open_by_cohort_month = defaultdict(set)  # (cohort_month, offset) -> {contact_ids}
    for a in data["activities"]:
        if a.get("event") not in ("open", "click"):
            continue
        ts = _parse_iso(a.get("tstamp"))
        cid = a.get("contact")
        ckey = cohort.get(cid) if cid else None
        if not (ts and ckey):
            continue
        c_year, c_month = map(int, ckey.split("-"))
        offset = (ts.year - c_year) * 12 + (ts.month - c_month)
        if 0 <= offset <= months:
            open_by_cohort_month[(ckey, offset)].add(cid)

    cohorts_sorted = sorted(cohort_size.keys())
    rows = []
    for ck in cohorts_sorted[-12:]:
        size = cohort_size[ck]
        retained = []
        for off in range(months + 1):
            n = len(open_by_cohort_month.get((ck, off), set()))
            retained.append({"offset": off, "contacts": n, "pct": (n / size * 100) if size else 0})
        rows.append({"cohort": ck, "size": size, "retention": retained})
    return {"cohorts": rows, "months": months}


def render_markdown(r: dict) -> str:
    lines = ["# Engagement Decay (Cohort Retention)", ""]
    if not r["cohorts"]:
        lines.append("_No cohort data available._")
        return "\n".join(lines)
    header = "| Cohort | Size | " + " | ".join(f"M+{i}" for i in range(r["months"] + 1)) + " |"
    sep = "|---" + ("|---" * (r["months"] + 2)) + "|"
    lines.append(header)
    lines.append(sep)
    for c in r["cohorts"]:
        cells = [f"{c['cohort']}", str(c["size"])]
        for ret in c["retention"]:
            cells.append(f"{ret['pct']:.0f}%")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Engagement decay cohort plot")
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--max-events", type=int, default=30000)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    client = ACClient()
    data = fetch(client, args.max_events)
    r = analyze(data, args.months)
    out = json.dumps(r, indent=2) if args.format == "json" else render_markdown(r)
    if args.output:
        Path(args.output).write_text(out)
        print(f"Wrote {args.output}")
    else:
        print(out)


if __name__ == "__main__":
    main()
