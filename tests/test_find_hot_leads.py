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

    # find_hot_leads now uses the bulk endpoints /scoreValues and
    # /contactTags and joins client-side (was: 2 per-contact calls per
    # contact, which was O(N) requests). Fixture mirrors the bulk shape.
    score_values = [
        {"contact": str(i), "score_id": "1",
         "score_value": str(max(0, 100 - (i - 1) * 10))}
        for i in range(1, 21)
    ]
    contact_tags = [
        {"contact": str(i), "tag": "1" if i <= 5 else "3"}
        for i in range(1, 21)
    ]

    routes = {
        "contacts": contacts,
        "deals": deals,
        "scoreValues": {"scoreValues": score_values},
        "contactTags": {"contactTags": contact_tags},
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


class TestMaxContactsAndPlanGating:
    """Locks in the bulk-endpoint refactor + the new --max-contacts cap +
    graceful 403 on /deals."""

    def test_max_contacts_is_respected(self, ac_client_factory):
        """max_contacts limits the contacts paged in, even when more exist."""
        contacts = [{"id": str(i), "email": f"u{i}@example.com",
                     "firstName": "F", "lastName": "L",
                     "cdate": "2026-01-01", "mdate": "2026-01-01"}
                    for i in range(1, 51)]
        routes = {
            "contacts": {"contacts": contacts, "meta": {"total": "50"}},
            "scoreValues": {"scoreValues": []},
            "contactTags": {"contactTags": []},
        }
        client = ac_client_factory(routes)
        from find_hot_leads import fetch_contacts_with_scores
        result = fetch_contacts_with_scores(client, max_contacts=10)
        assert len(result) == 10

    def test_bulk_endpoint_join_picks_best_score(self, ac_client_factory):
        """When a contact has multiple score rules, the highest wins."""
        contacts = [{"id": "42", "email": "x@x.co",
                     "firstName": "X", "lastName": "Y",
                     "cdate": "2026-01-01", "mdate": "2026-01-01"}]
        routes = {
            "contacts": {"contacts": contacts, "meta": {"total": "1"}},
            "scoreValues": {"scoreValues": [
                {"contact": "42", "score_id": "1", "score_value": "30"},
                {"contact": "42", "score_id": "2", "score_value": "92"},
                {"contact": "42", "score_id": "3", "score_value": "60"},
            ]},
            "contactTags": {"contactTags": [{"contact": "42", "tag": "7"}]},
        }
        client = ac_client_factory(routes)
        from find_hot_leads import fetch_contacts_with_scores
        result = fetch_contacts_with_scores(client, max_contacts=10)
        assert len(result) == 1
        assert result[0]["score"] == 92
        assert "7" in result[0]["tag_ids"]

    def test_deals_unavailable_returns_empty_mapping(self, ac_client_factory):
        """When /deals returns 403 (Lite plan), scoring still works without it."""
        from _ac_client import ACClientError
        client = ac_client_factory({})

        def raising(_method, _path, **_kw):
            raise ACClientError(403, "Deals not enabled")
        client._request = raising
        client.get = lambda path, params=None: raising("GET", path, params=params)

        from find_hot_leads import fetch_open_deals_by_contact
        result = fetch_open_deals_by_contact(client)
        assert result == {}

    def test_deals_500_still_raises(self, ac_client_factory):
        from _ac_client import ACClientError
        client = ac_client_factory({})

        def raising(_method, _path, **_kw):
            raise ACClientError(500, "boom")
        client._request = raising
        client.get = lambda path, params=None: raising("GET", path, params=params)

        import pytest
        from find_hot_leads import fetch_open_deals_by_contact
        with pytest.raises(ACClientError):
            fetch_open_deals_by_contact(client)

