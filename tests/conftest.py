"""
Shared pytest fixtures for ActiveCampaign skill tests.

Provides:
  - ac_client: ACClient with mocked HTTP
  - tmp_state_dir: temporary state directory
  - sample_state: pre-built state.json dict
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add scripts/ and tests/ to path so tests can import skill modules and fixtures
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

from fixtures.mock_responses import (
    USERS_ME,
    LISTS,
    TAGS,
    FIELDS,
    DEAL_CUSTOM_FIELD_META,
    DEAL_GROUPS,
    DEAL_STAGES,
    AUTOMATIONS,
    CONTACTS_META_TOTAL,
    CONTACTS_META_NEW,
    SCORES,
    make_campaigns,
    make_deals,
    make_contacts_with_engagement,
    BOUNCE_LOGS,
)


@pytest.fixture
def tmp_state_dir(tmp_path):
    """Patch STATE_DIR and STATE_FILE to use a temp directory."""
    state_dir = tmp_path / ".activecampaign-skill"
    state_dir.mkdir()
    state_file = state_dir / "state.json"
    history_file = state_dir / "history.jsonl"

    insights_file = state_dir / "insights.md"

    with patch("_ac_client.STATE_DIR", state_dir), \
         patch("_ac_client.STATE_FILE", state_file), \
         patch("_ac_client.HISTORY_FILE", history_file), \
         patch("_ac_client.INSIGHTS_FILE", insights_file):
        yield state_dir


@pytest.fixture
def sample_state() -> dict:
    """A realistic state.json for testing scripts that read state."""
    return {
        "schema_version": 1,
        "account": {
            "url": "https://testco.api-us1.com",
            "regional_host": "api-us1",
        },
        "taxonomy": {
            "lists": [
                {"id": "1", "name": "Master List", "stringid": "master-list"},
                {"id": "2", "name": "Newsletter", "stringid": "newsletter"},
            ],
            "tags": [
                {"id": "1", "name": "VIP", "tagType": "contact"},
                {"id": "2", "name": "Customer", "tagType": "contact"},
                {"id": "3", "name": "Churned", "tagType": "contact"},
            ],
            "custom_fields": {
                "contacts": [
                    {"id": "1", "title": "Plan", "type": "dropdown", "options": ["Free", "Pro", "Enterprise"]},
                ],
                "deals": [
                    {"id": "1", "fieldLabel": "Contract Value", "fieldType": "currency"},
                ],
            },
            "pipelines": [
                {
                    "id": "1",
                    "name": "Sales Pipeline",
                    "stages": [
                        {"id": "1", "title": "Qualified", "order": "1"},
                        {"id": "2", "title": "Proposal", "order": "2"},
                        {"id": "3", "title": "Negotiation", "order": "3"},
                        {"id": "4", "title": "Closed Won", "order": "4"},
                    ],
                }
            ],
            "automations": [
                {"id": "1", "name": "Welcome Series", "status": "1", "entered": "450", "exited": "380"},
            ],
            "user_info": {"username": "bot", "email": "bot@testco.com"},
        },
        "baselines": {
            "open_rate_p50": 0.28,
            "open_rate_p90": 0.42,
            "click_rate_p50": 0.04,
            "click_rate_p90": 0.09,
            "bounce_rate_p50": 0.005,
            "unsub_rate_p50": 0.003,
            "best_send_window_utc": ["14:00", "15:00", "13:00"],
            "best_send_dow": ["Tue", "Wed", "Thu"],
            "avg_subject_line_length": 42,
            "top_performing_subjects": [],
            "campaign_count_90d": 10,
        },
        "list_growth": {
            "total_contacts": 4823,
            "new_30d": 164,
            "growth_rate_30d": 0.034,
        },
        "last_calibrated": "2026-04-24T12:00:00+00:00",
    }


@pytest.fixture
def state_file(tmp_state_dir, sample_state):
    """Write sample state to the temp state directory and return the path."""
    state_path = tmp_state_dir / "state.json"
    state_path.write_text(json.dumps(sample_state))
    return state_path


def _build_mock_client(route_map: dict | None = None):
    """Build an ACClient with mocked HTTP that routes by path."""
    default_routes = {
        "users/me": USERS_ME,
        "lists": LISTS,
        "tags": TAGS,
        "fields": FIELDS,
        "dealCustomFieldMeta": DEAL_CUSTOM_FIELD_META,
        "dealGroups": DEAL_GROUPS,
        "dealStages": DEAL_STAGES,
        "automations": AUTOMATIONS,
        "campaigns": make_campaigns(10),
        "contacts": CONTACTS_META_TOTAL,
        "scores": SCORES,
        "deals": make_deals(15),
    }
    if route_map:
        default_routes.update(route_map)

    def mock_request(method, path, data=None, params=None, max_retries=5):
        clean = path.split("?")[0]
        for route_key, response in default_routes.items():
            if clean == route_key or clean.endswith("/" + route_key):
                if callable(response):
                    return response(params)
                return response
        return {}

    with patch("_ac_client.ACClient.__init__", lambda self, *a, **kw: None):
        from _ac_client import ACClient
        client = ACClient.__new__(ACClient)
        client.base = "https://testco.api-us1.com/api/3"
        client.token = "test-token"
        client._request_count = 0
        client._request = mock_request
        client.get = lambda path, params=None: mock_request("GET", path, params=params)
        client.post = lambda path, payload: mock_request("POST", path, data=payload)
        client.put = lambda path, payload: mock_request("PUT", path, data=payload)
        client.delete = lambda path: mock_request("DELETE", path)
    return client


@pytest.fixture
def ac_client():
    """ACClient with mocked HTTP using default route map."""
    return _build_mock_client()


@pytest.fixture
def ac_client_factory():
    """Factory to build ACClient with custom route overrides."""
    return _build_mock_client
