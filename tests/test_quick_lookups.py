"""Tests for the quick-lookup scripts shipped in 1.7.0.

Each script is built around a single API call. Tests verify:
  - analyze() produces the right shape on hit + miss
  - render_markdown() formats the result
  - state.json fast paths in tag_lookup / automation_lookup work without
    touching the API
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import automation_lookup  # noqa: E402
import contact_by_id  # noqa: E402
import contact_lookup  # noqa: E402
import contact_recent  # noqa: E402
import deal_by_id  # noqa: E402
import last_campaign  # noqa: E402
import tag_lookup  # noqa: E402


class TestContactLookup:
    def test_returns_found_when_one_result(self):
        data = {"contacts": [
            {"id": "1", "email": "a@x.co", "firstName": "Ada",
             "lastName": "L", "phone": "555-0100", "orgname": "Acme",
             "score": "82", "cdate": "2026-05-01", "mdate": "2026-06-01",
             "bounced_hard": "0", "bounced_soft": "0", "udate": ""},
        ]}
        r = contact_lookup.analyze(data)
        assert r["found"] is True
        assert r["id"] == "1"
        assert r["email"] == "a@x.co"
        assert r["first_name"] == "Ada"

    def test_returns_not_found_when_empty(self):
        r = contact_lookup.analyze({"contacts": []})
        assert r["found"] is False

    def test_render_not_found(self):
        md = contact_lookup.render_markdown({"found": False})
        assert "No contact found" in md

    def test_render_found(self):
        r = {
            "found": True, "id": "1", "email": "a@x.co",
            "first_name": "Ada", "last_name": "L", "phone": "555",
            "orgname": "Acme", "score": "82", "cdate": "2026-05-01",
            "mdate": "2026-06-01", "bounced_hard": "0", "bounced_soft": "0",
        }
        md = contact_lookup.render_markdown(r)
        assert "Ada L (a@x.co)" in md
        assert "ID: **1**" in md


class TestContactRecent:
    def test_returns_limited_count(self):
        data = {
            "contacts": [
                {"id": str(i), "email": f"u{i}@x.co", "firstName": f"U{i}",
                 "lastName": "L", "cdate": f"2026-06-0{i}",
                 "score": "10", "orgname": ""}
                for i in range(1, 6)
            ],
            "limit": 5,
        }
        r = contact_recent.analyze(data)
        assert len(r["contacts"]) == 5
        assert r["limit"] == 5
        assert r["contacts"][0]["email"] == "u1@x.co"

    def test_render_includes_header_and_rows(self):
        data = {"contacts": [
            {"id": "1", "email": "a@x.co", "firstName": "A", "lastName": "L",
             "cdate": "2026-06-01", "score": "10", "orgname": "Acme"},
        ], "limit": 5}
        md = contact_recent.render_markdown(contact_recent.analyze(data))
        assert "Most recent 5 contacts" in md
        assert "a@x.co" in md

    def test_empty_result_renders_placeholder(self):
        data = {"contacts": [], "limit": 5}
        md = contact_recent.render_markdown(contact_recent.analyze(data))
        assert "_no contacts_" in md


class TestContactById:
    def test_returns_found(self):
        data = {"contact": {"id": "42", "email": "x@x.co",
                            "firstName": "X", "lastName": "Y",
                            "phone": "", "orgname": "", "score": "0",
                            "cdate": "2026-05-01", "mdate": "2026-05-01",
                            "bounced_hard": "0", "bounced_soft": "0"},
                "id": "42"}
        r = contact_by_id.analyze(data)
        assert r["found"] is True
        assert r["id"] == "42"

    def test_not_found(self):
        r = contact_by_id.analyze({"not_found": True, "id": "99"})
        assert r["found"] is False
        md = contact_by_id.render_markdown(r)
        assert "No contact found with id `99`" in md


class TestDealById:
    def test_renders_status_human_label(self):
        data = {"deal": {"id": "10", "title": "Big Deal", "value": "500000",
                         "currency": "usd", "stage": "3", "group": "1",
                         "owner": "1", "contact": "100", "status": "1",
                         "cdate": "", "mdate": "", "nextdate": "",
                         "edate": "2026-06-15"}, "id": "10"}
        r = deal_by_id.analyze(data)
        md = deal_by_id.render_markdown(r)
        assert "won" in md
        assert "$5,000.00" in md

    def test_not_found(self):
        r = deal_by_id.analyze({"not_found": True, "id": "99"})
        md = deal_by_id.render_markdown(r)
        assert "No deal found" in md


class TestTagLookup:
    def test_state_match_returns_source_state(self, tmp_state_dir, sample_state):
        # Write the state file so _lookup_in_state can read it
        import json
        (tmp_state_dir / "state.json").write_text(json.dumps(sample_state))
        data = {"source": "state",
                "tags": [t for t in sample_state["taxonomy"]["tags"]
                         if t["name"].lower() == "vip"],
                "query": "VIP"}
        r = tag_lookup.analyze(data)
        assert r["source"] == "state"
        assert len(r["matches"]) == 1
        assert r["matches"][0]["name"] == "VIP"

    def test_no_match_renders_friendly(self):
        r = tag_lookup.analyze({"source": "live", "tags": [], "query": "ghost"})
        md = tag_lookup.render_markdown(r)
        assert "No matching tags." in md


class TestAutomationLookup:
    def test_state_first_path(self, tmp_state_dir, sample_state):
        import json
        (tmp_state_dir / "state.json").write_text(json.dumps(sample_state))
        data = {"source": "state",
                "automations": sample_state["taxonomy"]["automations"],
                "query": "welcome"}
        r = automation_lookup.analyze(data)
        assert r["matches"][0]["name"] == "Welcome Series"

    def test_status_label_renders(self):
        r = {"source": "live", "query": "x",
             "matches": [{"id": "5", "name": "X", "status": "1",
                          "entered": "100", "exited": "10"}]}
        md = automation_lookup.render_markdown(r)
        assert "active" in md


class TestLastCampaign:
    def test_metrics_computed(self):
        data = {"campaigns": [
            {"id": "100", "name": "Newsletter", "subject": "Hi",
             "fromname": "Ada", "fromemail": "ada@x.co",
             "sdate": "2026-06-01",
             "send_amt": "1000", "uniqueopens": "250",
             "uniquelinkclicks": "50", "bounces": "5"},
        ]}
        r = last_campaign.analyze(data)
        assert r["found"] is True
        assert abs(r["open_rate"] - 0.25) < 1e-9
        assert abs(r["click_rate"] - 0.05) < 1e-9
        assert r["bounces"] == 5

    def test_no_campaigns_renders_friendly(self):
        r = last_campaign.analyze({"campaigns": []})
        assert r.get("found") is False
        md = last_campaign.render_markdown(r)
        assert "No sent campaigns found" in md


class TestContactMostEngaged:
    def test_default_by_score(self):
        import contact_most_engaged
        data = {
            "contacts": [
                {"id": "1", "email": "a@x.co", "firstName": "Ada",
                 "lastName": "L", "orgname": "Acme", "score": "92",
                 "mdate": "2026-06-01", "cdate": "2026-05-01"},
                {"id": "2", "email": "b@x.co", "firstName": "B",
                 "lastName": "", "orgname": "", "score": "75",
                 "mdate": "2026-05-20", "cdate": "2026-04-15"},
            ],
            "by": "score",
            "limit": 5,
        }
        r = contact_most_engaged.analyze(data)
        assert r["by"] == "score"
        assert len(r["contacts"]) == 2
        assert r["contacts"][0]["score"] == "92"

    def test_by_recent_label(self):
        import contact_most_engaged
        md = contact_most_engaged.render_markdown({
            "by": "recent", "limit": 3, "contacts": []
        })
        assert "by last activity" in md

    def test_empty_renders_placeholder(self):
        import contact_most_engaged
        md = contact_most_engaged.render_markdown({
            "by": "score", "limit": 5, "contacts": []
        })
        assert "_no contacts_" in md
