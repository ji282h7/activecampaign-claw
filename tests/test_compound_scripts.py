"""Tests for the 1.8.0 compound scripts.

Compound scripts pull multiple sub-resources concurrently via fetch_many,
then assemble a single report. Tests verify:
  - analyze() handles the bulk shape correctly (with per-endpoint errors as
    sentinel dicts)
  - render_markdown() formats the combined output
  - state.json lookups resolve foreign keys to human names
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import automation_deep_dive  # noqa: E402
import contact_full_profile  # noqa: E402
import deal_full_context  # noqa: E402


class TestContactFullProfile:
    def test_renders_known_tags_and_lists(self, tmp_state_dir, sample_state):
        (tmp_state_dir / "state.json").write_text(json.dumps(sample_state))
        data = {
            "contact": {"id": "1", "email": "a@x.co", "firstName": "Ada",
                        "lastName": "L", "phone": "", "orgname": "Acme",
                        "score": "80", "cdate": "2026-05-01"},
            "bulk": {
                "contactTags": [{"tag": "1"}, {"tag": "2"}],
                "contactLists": [{"list": "1", "status": "1"},
                                 {"list": "2", "status": "2"}],   # 2 = inactive
                "contactAutomations": [
                    {"automation": "1", "status": "1", "cdate": "2026-05-10"},
                ],
                "fieldValues": [
                    {"field": "1", "value": "Pro"},
                ],
                "notes": [],
                "deals": [],
            },
        }
        r = contact_full_profile.analyze(data)
        assert r["found"] is True
        # Tag id "1" resolves to "VIP" per the sample_state taxonomy
        assert any(t["name"] == "VIP" for t in r["tags"])
        # List 2 (status != 1) should be filtered out
        assert len(r["lists"]) == 1
        assert r["lists"][0]["name"] == "Master List"
        # Automation 1 resolves
        assert r["automations"][0]["name"] == "Welcome Series"
        # Custom field id 1 → "Plan"
        assert r["fields"][0]["name"] == "Plan"
        assert r["fields"][0]["value"] == "Pro"

    def test_handles_deals_403_sentinel(self, tmp_state_dir, sample_state):
        (tmp_state_dir / "state.json").write_text(json.dumps(sample_state))
        data = {
            "contact": {"id": "1", "email": "x@x.co", "firstName": "X",
                        "lastName": "", "cdate": "2026-05-01"},
            "bulk": {
                "contactTags": [],
                "contactLists": [],
                "contactAutomations": [],
                "fieldValues": [],
                "notes": [],
                "deals": {"error": "403", "status_code": 403},
            },
        }
        r = contact_full_profile.analyze(data)
        assert r["deals"] is None
        md = contact_full_profile.render_markdown(r)
        assert "Deals feature not enabled" in md

    def test_renders_not_found(self):
        r = contact_full_profile.analyze({"contact": None})
        md = contact_full_profile.render_markdown(r)
        assert "No contact found" in md


class TestDealFullContext:
    def test_resolves_stage_via_state(self, tmp_state_dir, sample_state):
        (tmp_state_dir / "state.json").write_text(json.dumps(sample_state))
        data = {
            "deal": {"id": "100", "title": "Acme contract",
                     "value": "250000", "currency": "usd",
                     "stage": "2", "group": "1", "owner": "5",
                     "status": "0", "cdate": "2026-05-01",
                     "mdate": "2026-06-01", "nextdate": "2026-06-10",
                     "edate": "2026-06-15"},
            "contact": {"id": "50", "email": "buyer@x.co",
                        "firstName": "B", "lastName": "Z"},
            "bulk": {
                "dealCustomFieldData": [
                    {"customFieldId": "1", "fieldValue": "$2,500"},
                ],
                "dealTasks": [
                    {"id": "t1", "title": "Follow up",
                     "duedate": "2026-06-10", "status": "0"},
                ],
                "notes": [
                    {"id": "n1", "note": "Demoed today.",
                     "cdate": "2026-06-01"},
                ],
            },
        }
        r = deal_full_context.analyze(data)
        # Stage id 2 → "Proposal" in sample_state
        assert r["stage_title"] == "Proposal"
        # Pipeline 1 → "Sales Pipeline"
        assert r["pipeline"] == "Sales Pipeline"
        # Deal field id 1 → "Contract Value"
        assert r["fields"][0]["name"] == "Contract Value"
        md = deal_full_context.render_markdown(r)
        assert "Sales Pipeline" in md
        assert "Proposal" in md
        assert "Demoed today" in md

    def test_not_found(self):
        r = deal_full_context.analyze({"not_found": True, "id": "99"})
        md = deal_full_context.render_markdown(r)
        assert "No deal found" in md


class TestAutomationDeepDive:
    def test_steps_counted_by_lastblock(self):
        data = {
            "meta": {"id": "7", "name": "Welcome", "status": "1",
                     "entered": "100", "exited": "60"},
            "blocks": [
                {"id": "10", "ordernum": "1", "type": "send",  "text": "Welcome email"},
                {"id": "11", "ordernum": "2", "type": "wait",  "text": "Wait 3d"},
                {"id": "12", "ordernum": "3", "type": "send",  "text": "Day-3 email"},
            ],
            "enrollments": [
                # 2 active at block 10, 1 active at block 11, 0 at 12
                {"automation": "7", "status": "1", "lastblock": "10"},
                {"automation": "7", "status": "1", "lastblock": "10"},
                {"automation": "7", "status": "1", "lastblock": "11"},
                {"automation": "7", "status": "2", "lastblock": "12"},   # completed
            ],
        }
        r = automation_deep_dive.analyze(data)
        by_block = {s["id"]: s["active_at_step"] for s in r["steps"]}
        assert by_block["10"] == 2
        assert by_block["11"] == 1
        assert by_block["12"] == 0
        # Completed shows up in status breakdown
        assert r["by_status"]["2"] == 1
        # 3 active
        assert r["by_status"]["1"] == 3

    def test_render_shows_steps_table(self):
        r = {
            "id": "7", "name": "X", "status": "1",
            "entered": "10", "exited": "5",
            "by_status": {"1": 5},
            "steps": [{"id": "1", "ordernum": "1", "type": "send",
                       "title": "Hi", "active_at_step": 3}],
            "total_blocks": 1, "total_enrollments_sampled": 5,
        }
        md = automation_deep_dive.render_markdown(r)
        assert "Steps" in md
        assert "Hi" in md
