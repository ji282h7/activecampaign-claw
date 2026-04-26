"""Tests for audit_list_health.py — list health audit script."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fixtures.mock_responses import (
    BOUNCE_LOGS,
    make_campaigns,
    make_contacts_with_engagement,
)


class TestDomainDistribution:
    def test_parses_domains(self, ac_client_factory):
        contacts_data = make_contacts_with_engagement(50)
        client = ac_client_factory({"contacts": contacts_data})
        from audit_list_health import collect_domain_distribution
        result = collect_domain_distribution(client, sample_size=50)

        assert result["total_sampled"] == 50
        assert "gmail.com" in result["domains"]
        assert "outlook.com" in result["domains"]
        assert result["domains"]["gmail.com"]["count"] > 0

    def test_detects_concentration_risk(self, ac_client_factory):
        contacts = {
            "contacts": [
                {"id": str(i), "email": f"user{i}@monopoly.com"}
                for i in range(50)
            ],
            "meta": {"total": "50"},
        }
        client = ac_client_factory({"contacts": contacts})
        from audit_list_health import collect_domain_distribution
        result = collect_domain_distribution(client, sample_size=50)

        assert result["concentration_risk"] is not None
        assert result["concentration_risk"]["domain"] == "monopoly.com"
        assert result["concentration_risk"]["pct"] == 1.0

    def test_no_risk_when_distributed(self, ac_client_factory):
        contacts = make_contacts_with_engagement(50)
        client = ac_client_factory({"contacts": contacts})
        from audit_list_health import collect_domain_distribution
        result = collect_domain_distribution(client, sample_size=50)
        assert result["concentration_risk"] is None


class TestBounceData:
    def test_collects_bounces(self, ac_client_factory):
        def bounce_router(params):
            return BOUNCE_LOGS

        routes = {}
        for i in range(1, 11):
            routes[f"contacts/{i}/bounceLogs"] = BOUNCE_LOGS

        client = ac_client_factory(routes)
        from audit_list_health import collect_bounce_data
        result = collect_bounce_data(client, [str(i) for i in range(1, 11)])

        assert result["hard_bounces"] > 0
        assert result["soft_bounces"] > 0


class TestCampaignHealth:
    def test_returns_recent_campaigns(self, ac_client_factory):
        client = ac_client_factory({"campaigns": make_campaigns(5)})
        from audit_list_health import collect_campaign_health
        result = collect_campaign_health(client)

        assert len(result["recent_campaigns"]) > 0
        for c in result["recent_campaigns"]:
            assert "open_rate" in c
            assert "click_rate" in c
            assert 0 <= c["open_rate"] <= 1


class TestGenerateReport:
    def test_produces_complete_report(self, sample_state):
        from audit_list_health import generate_report

        domains = {
            "domains": {"gmail.com": {"count": 200, "pct": 0.40}},
            "total_sampled": 500,
            "concentration_risk": None,
        }
        bounces = {"hard_bounces": 5, "soft_bounces": 3, "multi_bounce_contacts": ["10", "22"]}
        campaigns = {
            "recent_campaigns": [
                {"name": "Test", "sent": 1000, "open_rate": 0.30,
                 "click_rate": 0.05, "bounce_rate": 0.003, "unsub_rate": 0.002},
            ]
        }

        report = generate_report(sample_state, domains, bounces, campaigns)

        assert "headline" in report
        assert "risks" in report
        assert "actions" in report
        assert report["headline"]["total_contacts"] == 4823
        assert report["headline"]["hard_bounces"] == 5

    def test_flags_risk_on_low_open_rate(self, sample_state):
        from audit_list_health import generate_report

        domains = {"domains": {}, "total_sampled": 0, "concentration_risk": None}
        bounces = {"hard_bounces": 0, "soft_bounces": 0, "multi_bounce_contacts": []}
        campaigns = {
            "recent_campaigns": [
                {"name": "Bad", "sent": 1000, "open_rate": 0.10,
                 "click_rate": 0.01, "bounce_rate": 0.01, "unsub_rate": 0.001},
            ]
        }

        report = generate_report(sample_state, domains, bounces, campaigns)
        assert len(report["risks"]) > 0
        assert any("open rate" in r.lower() or "Open rate" in r for r in report["risks"])


class TestFormatMarkdown:
    def test_produces_valid_markdown(self, sample_state):
        from audit_list_health import format_markdown, generate_report

        domains = {
            "domains": {"gmail.com": {"count": 200, "pct": 0.40}},
            "total_sampled": 500,
            "concentration_risk": None,
        }
        bounces = {"hard_bounces": 5, "soft_bounces": 3, "multi_bounce_contacts": ["10"]}
        campaigns = {
            "recent_campaigns": [
                {"name": "Campaign 1", "sent": 1000, "open_rate": 0.28,
                 "click_rate": 0.04, "bounce_rate": 0.003, "unsub_rate": 0.002},
            ]
        }

        report = generate_report(sample_state, domains, bounces, campaigns)
        md = format_markdown(report, "testco.api-us1.com")

        assert "## Headline metrics" in md
        assert "4,823" in md
        assert "gmail.com" in md
