"""Tests for find_hot_leads.py — hot lead ranking script."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fixtures.mock_responses import (
    make_contacts_with_engagement,
    make_deals,
)


def _build_lead_test_client(ac_client_factory):
    contacts = make_contacts_with_engagement(20)
    deals = make_deals(10)

    routes = {
        "contacts": contacts,
        "deals": deals,
    }
    for i in range(1, 21):
        routes[f"contacts/{i}/scoreValues"] = {
            "scoreValues": [
                {"score_id": "1", "score_value": str(max(0, 100 - (i - 1) * 10))}
            ]
        }
        routes[f"contacts/{i}/contactTags"] = {
            "contactTags": [
                {"tag": "1"} if i <= 5 else {"tag": "3"}
            ]
        }

    return ac_client_factory(routes)


class TestFetchContactsWithScores:
    def test_enriches_contacts(self, ac_client_factory):
        client = _build_lead_test_client(ac_client_factory)
        from find_hot_leads import fetch_contacts_with_scores
        contacts = fetch_contacts_with_scores(client, max_contacts=20)

        assert len(contacts) == 20
        assert contacts[0]["score"] == 100
        assert contacts[0]["email"].startswith("user1@")
        assert len(contacts[0]["tag_ids"]) > 0


class TestFetchOpenDeals:
    def test_groups_by_contact(self, ac_client_factory):
        deals = make_deals(10)
        client = ac_client_factory({"deals": deals})
        from find_hot_leads import fetch_open_deals_by_contact
        result = fetch_open_deals_by_contact(client)

        assert isinstance(result, dict)
        total_deals = sum(len(v) for v in result.values())
        assert total_deals > 0


class TestScoreLeads:
    def test_ranks_by_heat(self, ac_client_factory, sample_state):
        client = _build_lead_test_client(ac_client_factory)
        from find_hot_leads import (
            fetch_contacts_with_scores,
            fetch_open_deals_by_contact,
            score_leads,
        )
        contacts = fetch_contacts_with_scores(client, max_contacts=20)
        deals = fetch_open_deals_by_contact(client)
        leads = score_leads(contacts, deals, sample_state)

        assert len(leads) > 0
        # Should be sorted by heat descending
        for i in range(len(leads) - 1):
            assert leads[i]["heat"] >= leads[i + 1]["heat"]

    def test_applies_min_score_filter(self, ac_client_factory, sample_state):
        client = _build_lead_test_client(ac_client_factory)
        from find_hot_leads import (
            fetch_contacts_with_scores,
            fetch_open_deals_by_contact,
            score_leads,
        )
        contacts = fetch_contacts_with_scores(client, max_contacts=20)
        deals = fetch_open_deals_by_contact(client)

        all_leads = score_leads(contacts, deals, sample_state, min_score=0)
        high_leads = score_leads(contacts, deals, sample_state, min_score=80)

        assert len(high_leads) <= len(all_leads)
        for lead in high_leads:
            assert lead["heat"] >= 80

    def test_signals_populated(self, ac_client_factory, sample_state):
        client = _build_lead_test_client(ac_client_factory)
        from find_hot_leads import (
            fetch_contacts_with_scores,
            fetch_open_deals_by_contact,
            score_leads,
        )
        contacts = fetch_contacts_with_scores(client, max_contacts=20)
        deals = fetch_open_deals_by_contact(client)
        leads = score_leads(contacts, deals, sample_state)

        top_lead = leads[0]
        assert len(top_lead["signals"]) > 0
        assert top_lead["action"] != ""


class TestFormatMarkdown:
    def test_produces_table(self, ac_client_factory, sample_state):
        client = _build_lead_test_client(ac_client_factory)
        from find_hot_leads import (
            fetch_contacts_with_scores,
            fetch_open_deals_by_contact,
            format_markdown,
            score_leads,
        )
        contacts = fetch_contacts_with_scores(client, max_contacts=20)
        deals = fetch_open_deals_by_contact(client)
        leads = score_leads(contacts, deals, sample_state)
        md = format_markdown(leads, top=5)

        assert "## Top leads by heat score" in md
        assert "| Rank |" in md
        assert "## Signal details" in md

    def test_empty_leads(self):
        from find_hot_leads import format_markdown
        md = format_markdown([], top=5)
        assert "No leads found" in md
