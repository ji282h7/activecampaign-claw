"""Tests for calibrate.py — account calibration script."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

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
    make_campaigns,
)


class TestFetchTaxonomy:
    def test_returns_all_sections(self, ac_client):
        from calibrate import fetch_taxonomy
        tax = fetch_taxonomy(ac_client)

        assert "lists" in tax
        assert "tags" in tax
        assert "custom_fields" in tax
        assert "pipelines" in tax
        assert "automations" in tax
        assert "user_info" not in tax

    def test_lists_parsed(self, ac_client):
        from calibrate import fetch_taxonomy
        tax = fetch_taxonomy(ac_client)
        assert len(tax["lists"]) == 3
        assert tax["lists"][0]["name"] == "Master List"

    def test_tags_parsed(self, ac_client):
        from calibrate import fetch_taxonomy
        tax = fetch_taxonomy(ac_client)
        assert len(tax["tags"]) == 4
        assert tax["tags"][0]["name"] == "VIP"

    def test_custom_fields_parsed(self, ac_client):
        from calibrate import fetch_taxonomy
        tax = fetch_taxonomy(ac_client)
        assert len(tax["custom_fields"]["contacts"]) == 3
        assert tax["custom_fields"]["contacts"][0]["title"] == "Plan"
        assert tax["custom_fields"]["contacts"][0]["options"] == ["Free", "Pro", "Enterprise"]

    def test_pipelines_have_stages(self, ac_client):
        from calibrate import fetch_taxonomy
        tax = fetch_taxonomy(ac_client)
        assert len(tax["pipelines"]) == 2
        pipeline_1 = tax["pipelines"][0]
        assert pipeline_1["name"] == "Sales Pipeline"
        assert len(pipeline_1["stages"]) == 4

    def test_automations_parsed(self, ac_client):
        from calibrate import fetch_taxonomy
        tax = fetch_taxonomy(ac_client)
        assert len(tax["automations"]) == 3
        assert tax["automations"][0]["name"] == "Welcome Series"


class TestFetchCampaignBaselines:
    def test_returns_baselines(self, ac_client):
        from calibrate import fetch_campaign_baselines
        baselines = fetch_campaign_baselines(ac_client)

        assert "open_rate_p50" in baselines
        assert "click_rate_p50" in baselines
        assert "bounce_rate_p50" in baselines
        assert "campaign_count_90d" in baselines
        assert baselines["campaign_count_90d"] > 0

    def test_open_rate_in_range(self, ac_client):
        from calibrate import fetch_campaign_baselines
        baselines = fetch_campaign_baselines(ac_client)
        assert 0 < baselines["open_rate_p50"] < 1
        assert baselines["open_rate_p50"] <= baselines["open_rate_p90"]

    def test_defaults_on_empty_campaigns(self, ac_client_factory):
        client = ac_client_factory({"campaigns": {"campaigns": []}})
        from calibrate import fetch_campaign_baselines
        baselines = fetch_campaign_baselines(client)
        assert baselines["campaign_count_90d"] == 0
        assert baselines["_note"] is not None

    def test_subject_analysis(self, ac_client):
        from calibrate import fetch_campaign_baselines
        baselines = fetch_campaign_baselines(ac_client)
        assert "avg_subject_line_length" in baselines
        assert baselines["avg_subject_line_length"] > 0
        assert "top_performing_subjects" in baselines


class TestFetchListGrowth:
    def test_returns_growth_data(self, ac_client_factory):
        def contacts_router(params):
            if params and "filters[created_after]" in params:
                return CONTACTS_META_NEW
            return CONTACTS_META_TOTAL

        client = ac_client_factory({"contacts": contacts_router})
        from calibrate import fetch_list_growth
        growth = fetch_list_growth(client)

        assert growth["total_contacts"] == 4823
        assert growth["new_30d"] == 164
        assert 0 < growth["growth_rate_30d"] < 1


class TestValidateConnection:
    def test_returns_user_info(self, ac_client):
        from calibrate import validate_connection
        result = validate_connection(ac_client)
        assert result["user"]["email"] == "bot@testco.com"

    def test_exits_on_auth_failure(self, ac_client_factory):
        def fail_auth(params=None):
            raise Exception("401 Unauthorized")

        client = ac_client_factory({"users/me": fail_auth})
        from calibrate import validate_connection
        with pytest.raises(SystemExit):
            validate_connection(client)


class TestValidateFlag:
    def test_validate_only_does_not_calibrate(self, ac_client_factory, tmp_state_dir):
        client = ac_client_factory()
        import calibrate

        with patch("sys.argv", ["calibrate.py", "--validate"]), \
             patch("calibrate.ACClient", return_value=client), \
             patch("calibrate.fetch_taxonomy") as mock_tax, \
             patch("calibrate.save_state"):
            calibrate.main()
            mock_tax.assert_not_called()

    def test_validate_shows_state_age(self, ac_client_factory, tmp_state_dir, sample_state, capsys):
        client = ac_client_factory()
        state_file = tmp_state_dir / "state.json"
        import json as _json
        state_file.write_text(_json.dumps(sample_state))
        import calibrate

        with patch("sys.argv", ["calibrate.py", "--validate"]), \
             patch("calibrate.ACClient", return_value=client), \
             patch("_ac_client.STATE_FILE", state_file):
            calibrate.main()
            out = capsys.readouterr().out
            assert "Connection valid" in out
            assert "State file exists" in out


class TestMainIntegration:
    def test_full_calibration(self, ac_client_factory, tmp_state_dir):
        def contacts_router(params):
            if params and "filters[created_after]" in params:
                return CONTACTS_META_NEW
            return CONTACTS_META_TOTAL

        client = ac_client_factory({"contacts": contacts_router})

        import calibrate
        from _ac_client import save_state, STATE_FILE

        with patch("_ac_client.STATE_DIR", tmp_state_dir), \
             patch("_ac_client.STATE_FILE", tmp_state_dir / "state.json"), \
             patch("calibrate.ACClient", return_value=client), \
             patch("calibrate.save_state") as mock_save:

            # Manually run the pieces
            tax = calibrate.fetch_taxonomy(client)
            baselines = calibrate.fetch_campaign_baselines(client)
            growth = calibrate.fetch_list_growth(client)

            assert len(tax["lists"]) == 3
            assert baselines["campaign_count_90d"] > 0
            assert growth["total_contacts"] > 0
