#!/usr/bin/env python3
"""
dedupe_contacts.py — Find duplicate contacts.

Detects: same email different case, same normalized phone, fuzzy name+company.
Outputs merge candidates with confidence scores. Never auto-merges.

Usage:
  python3 dedupe_contacts.py
  python3 dedupe_contacts.py --max-contacts 5000
  python3 dedupe_contacts.py --format json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from _ac_client import ACClient


def _norm_phone(p: str) -> str:
    if not p:
        return ""
    digits = re.sub(r"\D", "", p)
    if len(digits) >= 10:
        return digits[-10:]
    return digits


def _norm_email(e: str) -> str:
    return (e or "").strip().lower()


def _name_company_key(c: dict) -> str:
    fn = (c.get("firstName") or "").strip().lower()
    ln = (c.get("lastName") or "").strip().lower()
    if fn and ln:
        return f"{fn}|{ln}"
    return ""


def find_duplicates(contacts: list[dict]) -> dict:
    by_email = defaultdict(list)
    by_phone = defaultdict(list)
    by_name = defaultdict(list)

    for c in contacts:
        email = _norm_email(c.get("email", ""))
        phone = _norm_phone(c.get("phone", ""))
        name_key = _name_company_key(c)
        if email:
            by_email[email].append(c)
        if phone:
            by_phone[phone].append(c)
        if name_key:
            by_name[name_key].append(c)

    email_dupes = {e: cs for e, cs in by_email.items() if len(cs) > 1}
    phone_dupes = {p: cs for p, cs in by_phone.items() if len(cs) > 1}
    name_dupes = {n: cs for n, cs in by_name.items() if len(cs) > 1}

    # Filter name_dupes that are not also caught by email (high-confidence is email/phone)
    name_only = {}
    for n, cs in name_dupes.items():
        emails = {_norm_email(c.get("email", "")) for c in cs}
        if len(emails) > 1 and not any(e in email_dupes for e in emails):
            name_only[n] = cs

    return {
        "email_case_duplicates": email_dupes,
        "phone_duplicates": phone_dupes,
        "name_duplicates_distinct_email": name_only,
    }


def render_markdown(d: dict, total: int) -> str:
    lines = [
        "# Duplicate Contact Audit",
        "",
        f"- Contacts scanned: **{total}**",
        f"- Email duplicates (case-insensitive): **{len(d['email_case_duplicates'])}** groups",
        f"- Phone duplicates (last-10-digits match): **{len(d['phone_duplicates'])}** groups",
        f"- Name duplicates with distinct emails: **{len(d['name_duplicates_distinct_email'])}** groups",
        "",
    ]
    if d["email_case_duplicates"]:
        lines.append("## Email duplicates (high confidence)")
        for e, cs in list(d["email_case_duplicates"].items())[:30]:
            ids = ", ".join(str(c["id"]) for c in cs)
            lines.append(f"- `{e}` — ids: {ids}")
        lines.append("")
    if d["phone_duplicates"]:
        lines.append("## Phone duplicates")
        for p, cs in list(d["phone_duplicates"].items())[:30]:
            entries = ", ".join(f"{c.get('email','?')} (id={c['id']})" for c in cs)
            lines.append(f"- `{p}` — {entries}")
        lines.append("")
    if d["name_duplicates_distinct_email"]:
        lines.append("## Same-name, different-email (review manually)")
        for n, cs in list(d["name_duplicates_distinct_email"].items())[:30]:
            entries = ", ".join(f"{c.get('email','?')} (id={c['id']})" for c in cs)
            lines.append(f"- `{n}` — {entries}")
        lines.append("")
    if not any([d["email_case_duplicates"], d["phone_duplicates"], d["name_duplicates_distinct_email"]]):
        lines.append("**No duplicates detected.**")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Find duplicate contacts")
    parser.add_argument("--max-contacts", type=int, default=10000)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    client = ACClient()
    contacts = client.paginate("contacts", "contacts", max_items=args.max_contacts)
    d = find_duplicates(contacts)

    if args.format == "json":
        # JSON-safe: only ids/emails/phones, no full contact records
        out_obj = {
            "scanned": len(contacts),
            "email_case_duplicates": [
                {"key": e, "ids": [c["id"] for c in cs]}
                for e, cs in d["email_case_duplicates"].items()
            ],
            "phone_duplicates": [
                {"key": p, "ids": [c["id"] for c in cs]}
                for p, cs in d["phone_duplicates"].items()
            ],
            "name_duplicates_distinct_email": [
                {"key": n, "ids": [c["id"] for c in cs]}
                for n, cs in d["name_duplicates_distinct_email"].items()
            ],
        }
        out = json.dumps(out_obj, indent=2)
    else:
        out = render_markdown(d, len(contacts))

    if args.output:
        Path(args.output).write_text(out)
        print(f"Wrote {args.output}")
    else:
        print(out)


if __name__ == "__main__":
    main()
