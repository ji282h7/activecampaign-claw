#!/usr/bin/env python3
"""
automation_overlap.py — Contacts enrolled in multiple automations simultaneously.

Often a sign of un-coordinated programs all targeting the same person. Lists
contacts in 3+ active automations and pairs of automations with high audience
overlap.

Usage:
  python3 automation_overlap.py
  python3 automation_overlap.py --min-overlap 5 --format json
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from _ac_client import ACClient


def fetch(client: ACClient) -> dict:
    automations = client.paginate("automations", "automations", max_items=2000)
    contact_autos = client.paginate("contactAutomations", "contactAutomations", max_items=50000)
    return {"automations": automations, "contact_automations": contact_autos}


def analyze(data: dict, min_overlap: int) -> dict:
    name_by_id = {str(a["id"]): a.get("name") for a in data["automations"]}
    autos_by_contact = defaultdict(set)
    for ca in data["contact_automations"]:
        if str(ca.get("status")) == "1":
            autos_by_contact[str(ca.get("contact"))].add(str(ca.get("automation")))

    multi = [(cid, autos) for cid, autos in autos_by_contact.items() if len(autos) >= 3]
    pair_counts = defaultdict(int)
    for cid, autos in autos_by_contact.items():
        if len(autos) < 2:
            continue
        for a, b in combinations(sorted(autos), 2):
            pair_counts[(a, b)] += 1

    pairs = []
    for (a, b), c in pair_counts.items():
        if c < min_overlap:
            continue
        pairs.append({
            "auto_a": name_by_id.get(a, a),
            "auto_b": name_by_id.get(b, b),
            "overlap": c,
        })
    pairs.sort(key=lambda x: -x["overlap"])
    return {
        "contacts_in_3plus": len(multi),
        "samples_3plus": [
            {"contact": cid, "automations": [name_by_id.get(a, a) for a in sorted(autos)]}
            for cid, autos in multi[:20]
        ],
        "pairs": pairs,
    }


def render_markdown(r: dict) -> str:
    lines = [
        "# Automation Overlap",
        "",
        f"- Contacts in 3+ active automations: **{r['contacts_in_3plus']}**",
        f"- Pairs above min overlap threshold: {len(r['pairs'])}",
        "",
    ]
    if r["samples_3plus"]:
        lines.append("## Sample contacts in 3+ automations")
        for s in r["samples_3plus"]:
            lines.append(f"- contact={s['contact']}: {', '.join(s['automations'])}")
        lines.append("")
    if r["pairs"]:
        lines.append("## Top overlapping automation pairs")
        for p in r["pairs"][:30]:
            lines.append(f"- `{p['auto_a']}` + `{p['auto_b']}` — {p['overlap']} contacts")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Automation overlap")
    parser.add_argument("--min-overlap", type=int, default=2)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    client = ACClient()
    data = fetch(client)
    r = analyze(data, args.min_overlap)
    out = json.dumps(r, indent=2) if args.format == "json" else render_markdown(r)
    if args.output:
        Path(args.output).write_text(out)
        print(f"Wrote {args.output}")
    else:
        print(out)


if __name__ == "__main__":
    main()
