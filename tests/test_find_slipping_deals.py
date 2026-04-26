"""Tests for find_slipping_deals.py — deal hygiene script."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from fixtures.mock_responses import make_deals


def _make_deals_with_dates():
    """Create deals with controlled dates for predictable test results."""
    now = datetime.now(timezone.utc)
    return {
        "deals": [
            {
                "id": "1", "title": "Overdue Big Deal",
                "value": "5000000", "currency": "usd",
                "group": "1", "stage": "3", "owner": "1",
                "status": "0", "contact": "10",
                "cdate": (now - timedelta(days=60)).isoformat(),
                "mdate": (now - timedelta(days=20)).isoformat(),
                "nextdate": (now - timedelta(days=10)).isoformat(),
            },
            {
                "id": "2", "title": "Stale Small Deal",
                "value": "100000", "currency": "usd",
                "group": "1", "stage": "1", "owner": "2",
                "status": "0", "contact": "20",
                "cdate": (now - timedelta(days=45)).isoformat(),
                "mdate": (now - timedelta(days=18)).isoformat(),
                "nextdate": (now + timedelta(days=5)).isoformat(),
            },
            {
                "id": "3", "title": "Healthy Deal",
                "value": "200000", "currency": "usd",
                "group": "1", "stage": "2", "owner": "1",
                "status": "0", "contact": "30",
                "cdate": (now - timedelta(days=10)).isoformat(),
                "mdate": (now - timedelta(days=2)).isoformat(),
                "nextdate": (now + timedelta(days=15)).isoformat(),
            },
            {
                "id": "4", "title": "Missing Data Deal",
                "value": "0", "currency": "usd",
                "group": "1", "stage": "1", "owner": "0",
                "status": "0", "contact": "",
                "cdate": (now - timedelta(days=30)).isoformat(),
                "mdate": (now - timedelta(days=5)).isoformat(),
                "nextdate": None,
            },
        ]
    }


class TestFetchOpenDeals:
    def test_fetches_deals(self, ac_client_factory):
        client = ac_client_factory({"deals": make_deals(10)})
        from find_slipping_deals import fetch_open_deals
        deals = fetch_open_deals(client)
        assert len(deals) > 0


class TestAnalyzeDeals:
    def test_identifies_slipping(self, ac_client_factory, sample_state):
        deals_data = _make_deals_with_dates()
        ac_client_factory({"deals": deals_data})
        from find_slipping_deals import analyze_deals
        deals = deals_data["deals"]
        analysis = analyze_deals(deals, sample_state, stale_days=14)

        assert len(analysis["slipping"]) >= 1
        overdue_titles = [d["title"] for d in analysis["slipping"]]
        assert "Overdue Big Deal" in overdue_titles

    def test_identifies_stale(self, ac_client_factory, sample_state):
        deals_data = _make_deals_with_dates()
        from find_slipping_deals import analyze_deals
        analysis = analyze_deals(deals_data["deals"], sample_state, stale_days=14)

        stale_titles = [d["title"] for d in analysis["stale"]]
        assert "Overdue Big Deal" in stale_titles
        assert "Stale Small Deal" in stale_titles
        assert "Healthy Deal" not in stale_titles

    def test_identifies_data_issues(self, sample_state):
        deals_data = _make_deals_with_dates()
        from find_slipping_deals import analyze_deals
        analysis = analyze_deals(deals_data["deals"], sample_state, stale_days=14)

        issue_titles = [d["title"] for d in analysis["data_issues"]]
        assert "Missing Data Deal" in issue_titles
        missing = next(d for d in analysis["data_issues"] if d["title"] == "Missing Data Deal")
        assert "missing close date" in missing["issues"]
        assert "$0 value" in missing["issues"]

    def test_summary_totals(self, sample_state):
        deals_data = _make_deals_with_dates()
        from find_slipping_deals import analyze_deals
        analysis = analyze_deals(deals_data["deals"], sample_state)

        assert analysis["summary"]["total_open"] == 4
        assert analysis["summary"]["total_value_cents"] > 0

    def test_stage_distribution(self, sample_state):
        deals_data = _make_deals_with_dates()
        from find_slipping_deals import analyze_deals
        analysis = analyze_deals(deals_data["deals"], sample_state)

        assert len(analysis["stage_distribution"]) > 0

    def test_slipping_sorted_by_urgency(self, sample_state):
        deals_data = _make_deals_with_dates()
        from find_slipping_deals import analyze_deals
        analysis = analyze_deals(deals_data["deals"], sample_state)

        for i in range(len(analysis["slipping"]) - 1):
            assert (
                analysis["slipping"][i]["urgency_score"]
                >= analysis["slipping"][i + 1]["urgency_score"]
            )


class TestGenerateActions:
    def test_produces_actions(self, sample_state):
        deals_data = _make_deals_with_dates()
        from find_slipping_deals import analyze_deals, generate_actions
        analysis = analyze_deals(deals_data["deals"], sample_state)
        actions = generate_actions(analysis)

        assert len(actions) > 0
        assert any("Overdue Big Deal" in a for a in actions)


class TestFormatMarkdown:
    def test_produces_valid_markdown(self, sample_state):
        deals_data = _make_deals_with_dates()
        from find_slipping_deals import analyze_deals, format_markdown
        analysis = analyze_deals(deals_data["deals"], sample_state)
        md = format_markdown(analysis, top=10)

        assert "## Pipeline summary" in md
        assert "## Slipping deals" in md
        assert "Overdue Big Deal" in md
        assert "## Recommended actions" in md

    def test_healthy_pipeline_output(self, sample_state):
        now = datetime.now(timezone.utc)
        healthy_deals = [
            {
                "id": "1", "title": "Good Deal",
                "value": "100000", "stage": "1", "owner": "1",
                "status": "0", "contact": "1",
                "cdate": (now - timedelta(days=5)).isoformat(),
                "mdate": (now - timedelta(days=1)).isoformat(),
                "nextdate": (now + timedelta(days=30)).isoformat(),
            }
        ]
        from find_slipping_deals import analyze_deals, format_markdown
        analysis = analyze_deals(healthy_deals, sample_state)
        md = format_markdown(analysis, top=10)

        assert "None" in md or "✅" in md
