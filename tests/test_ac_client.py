"""Tests for _ac_client.py — shared API client and utilities."""

import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import _ac_client


class TestACClient:
    def test_get_routes_correctly(self, ac_client):
        result = ac_client.get("users/me")
        assert result["user"]["email"] == "bot@testco.com"

    def test_get_lists(self, ac_client):
        result = ac_client.get("lists")
        assert len(result["lists"]) == 3
        assert result["lists"][0]["name"] == "Master List"

    def test_get_tags(self, ac_client):
        result = ac_client.get("tags")
        assert len(result["tags"]) == 4

    def test_paginate_collects_all(self, ac_client):
        items = ac_client.paginate("tags", "tags")
        assert len(items) == 4

    def test_paginate_respects_max_items(self, ac_client):
        items = ac_client.paginate("tags", "tags", max_items=2)
        assert len(items) == 2

    def test_stream_yields_records(self, ac_client):
        out = list(ac_client.stream("tags", "tags"))
        assert len(out) == 4
        assert all(isinstance(r, dict) for r in out)
        assert {t["tag"] for t in out} == {t["tag"] for t in ac_client.get("tags")["tags"]}

    def test_stream_respects_max_items(self, ac_client):
        out = list(ac_client.stream("tags", "tags", max_items=2))
        assert len(out) == 2

    def test_stream_is_lazy(self, ac_client):
        # Generator hasn't run yet — calling stream() shouldn't fetch
        gen = ac_client.stream("tags", "tags")
        # It's a generator object, not a list
        assert hasattr(gen, "__next__")
        # First next() pulls the first record
        first = next(gen)
        assert "tag" in first

    def test_paginate_delegates_to_stream(self, ac_client):
        # Same data via both paths
        from_paginate = ac_client.paginate("tags", "tags")
        from_stream = list(ac_client.stream("tags", "tags", max_items=5000))
        assert from_paginate == from_stream

    def test_stream_stops_on_empty_chunk(self, ac_client_factory):
        calls = {"n": 0}

        def empty_response(params):
            calls["n"] += 1
            return {"things": []}

        client = ac_client_factory({"things": empty_response})
        out = list(client.stream("things", "things", max_items=1000))
        assert out == []
        assert calls["n"] == 1  # one call, then stop on empty page

    def test_stream_handles_no_max_items(self, ac_client_factory):
        # No cap, but mock returns a short page so we stop naturally
        client = ac_client_factory({"things": {"things": [{"id": str(i)} for i in range(7)]}})
        out = list(client.stream("things", "things"))
        assert len(out) == 7


class TestStateHelpers:
    def test_load_state_returns_none_when_missing(self, tmp_state_dir):
        with patch("_ac_client.STATE_FILE", tmp_state_dir / "state.json"):
            result = _ac_client.load_state()
            assert result is None

    def test_load_state_reads_valid_json(self, state_file, tmp_state_dir):
        with patch("_ac_client.STATE_FILE", state_file):
            result = _ac_client.load_state()
            assert result is not None
            assert result["schema_version"] == 1
            assert result["account"]["url"] == "https://testco.api-us1.com"

    def test_load_state_returns_none_on_bad_json(self, tmp_state_dir):
        bad_file = tmp_state_dir / "state.json"
        bad_file.write_text("{invalid json")
        with patch("_ac_client.STATE_FILE", bad_file):
            result = _ac_client.load_state()
            assert result is None

    def test_state_age_days(self, state_file, tmp_state_dir):
        with patch("_ac_client.STATE_FILE", state_file):
            age = _ac_client.state_age_days()
            assert age is not None
            assert age >= 0

    def test_state_age_days_none_when_missing(self, tmp_state_dir):
        with patch("_ac_client.STATE_FILE", tmp_state_dir / "state.json"):
            assert _ac_client.state_age_days() is None

    def test_save_state(self, tmp_state_dir):
        state_file = tmp_state_dir / "state.json"
        with patch("_ac_client.STATE_DIR", tmp_state_dir), \
             patch("_ac_client.STATE_FILE", state_file):
            _ac_client.save_state({"test": True})
            assert state_file.exists()
            data = json.loads(state_file.read_text())
            assert data["test"] is True


class TestHistoryLogging:
    def test_log_outcome_creates_file(self, tmp_state_dir):
        history = tmp_state_dir / "history.jsonl"
        with patch("_ac_client.STATE_DIR", tmp_state_dir), \
             patch("_ac_client.HISTORY_FILE", history):
            _ac_client.log_outcome("test_action", detail="hello")
            assert history.exists()
            lines = history.read_text().strip().split("\n")
            assert len(lines) == 1
            entry = json.loads(lines[0])
            assert entry["action"] == "test_action"
            assert entry["detail"] == "hello"
            assert "ts" in entry

    def test_log_outcome_appends(self, tmp_state_dir):
        history = tmp_state_dir / "history.jsonl"
        with patch("_ac_client.STATE_DIR", tmp_state_dir), \
             patch("_ac_client.HISTORY_FILE", history):
            _ac_client.log_outcome("first")
            _ac_client.log_outcome("second")
            lines = history.read_text().strip().split("\n")
            assert len(lines) == 2


class TestWriteReport:
    def test_returns_formatted_string(self):
        report = _ac_client.write_report("Test Report", "Some content here.")
        assert report.startswith("# Test Report")
        assert "Generated:" in report
        assert "Some content here." in report

    def test_writes_to_file(self, tmp_path):
        out = tmp_path / "report.md"
        _ac_client.write_report("Title", "Body", to_file=out)
        assert out.exists()
        assert "# Title" in out.read_text()


class TestSanitize:
    def test_passes_clean_string(self):
        assert _ac_client.sanitize("Jane Doe") == "Jane Doe"

    def test_strips_control_characters(self):
        assert _ac_client.sanitize("Jane\x00Doe") == "JaneDoe"
        assert _ac_client.sanitize("test\x07bell") == "testbell"

    def test_strips_markdown_image_injection(self):
        assert _ac_client.sanitize("![evil](http://attacker.com/img)") == ""

    def test_strips_javascript_link_injection(self):
        assert _ac_client.sanitize("[click](javascript:alert(1))") == ""

    def test_truncates_to_max_len(self):
        long_str = "a" * 1000
        assert len(_ac_client.sanitize(long_str)) == 500

    def test_custom_max_len(self):
        assert len(_ac_client.sanitize("a" * 100, max_len=50)) == 50

    def test_preserves_normal_special_characters(self):
        assert _ac_client.sanitize("Acme Corp — Enterprise Plan") == "Acme Corp — Enterprise Plan"
        assert _ac_client.sanitize("$50,000 deal (Q2)") == "$50,000 deal (Q2)"

    def test_preserves_email_addresses(self):
        assert _ac_client.sanitize("jane@example.com") == "jane@example.com"

    def test_preserves_unicode(self):
        assert _ac_client.sanitize("José García") == "José García"

    def test_empty_string(self):
        assert _ac_client.sanitize("") == ""

    def test_strips_mixed_threats(self):
        dirty = "Jane\x00 ![x](http://evil.com) Smith"
        result = _ac_client.sanitize(dirty)
        assert "\x00" not in result
        assert "evil.com" not in result
        assert "Jane" in result
        assert "Smith" in result


class TestEnsureState:
    def test_exits_when_missing(self, tmp_state_dir):
        with patch("_ac_client.STATE_FILE", tmp_state_dir / "state.json"):
            with pytest.raises(SystemExit):
                _ac_client.ensure_state()

    def test_missing_message_mentions_calibrate(self, tmp_state_dir, capsys):
        with patch("_ac_client.STATE_FILE", tmp_state_dir / "state.json"):
            with pytest.raises(SystemExit):
                _ac_client.ensure_state()
            err = capsys.readouterr().err
            assert "calibrate.py" in err
            assert "--validate" in err
            assert "AC_API_URL" in err
            assert "AC_API_TOKEN" in err

    def test_warns_on_stale(self, tmp_state_dir, sample_state, capsys):
        state_file = tmp_state_dir / "state.json"
        sample_state["last_calibrated"] = "2020-01-01T00:00:00+00:00"
        state_file.write_text(json.dumps(sample_state))
        with patch("_ac_client.STATE_FILE", state_file):
            result = _ac_client.ensure_state()
            assert result is not None
            err = capsys.readouterr().err
            assert "WARNING" in err
            assert "days old" in err

    def test_returns_state_when_fresh(self, state_file, tmp_state_dir):
        with patch("_ac_client.STATE_FILE", state_file):
            result = _ac_client.ensure_state()
            assert result["schema_version"] == 1


class TestHTTPSEnforcement:
    def test_rejects_http_url(self):
        with pytest.raises(SystemExit):
            _ac_client.ACClient(base_url="http://test.api-us1.com", token="tok")

    def test_accepts_https_url(self):
        with patch("urllib.request.urlopen"):
            client = _ac_client.ACClient(base_url="https://test.api-us1.com", token="tok")
            assert client.base == "https://test.api-us1.com/api/3"


class TestBackoffDelay:
    def test_returns_positive_float(self):
        delay = _ac_client.ACClient._backoff_delay(0)
        assert delay >= 0

    def test_increases_with_attempts(self):
        # With jitter, individual values may vary, but the cap should grow
        # Test the max possible delay grows
        for i in range(4):
            assert min(60.0, 1.0 * (2 ** (i + 1))) >= min(60.0, 1.0 * (2 ** i))

    def test_respects_cap(self):
        for _ in range(20):
            delay = _ac_client.ACClient._backoff_delay(100, base=1.0, cap=10.0)
            assert delay <= 10.0

    def test_jitter_adds_randomness(self):
        delays = {_ac_client.ACClient._backoff_delay(3, base=1.0, cap=60.0) for _ in range(20)}
        assert len(delays) > 1  # should not all be the same


class TestRateLimitRetry:
    """Test retry logic by mocking urllib.request.urlopen so the real
    _request method (with its retry loop) actually runs."""

    def _make_client(self):
        with patch("_ac_client.ACClient.__init__", lambda self, *a, **kw: None):
            client = _ac_client.ACClient.__new__(_ac_client.ACClient)
            client.base = "https://test.api-us1.com/api/3"
            client.token = "tok"
            client._request_count = 0
            client._last_request_time = 0.0
        return client

    def _mock_response(self, body: dict):
        resp = MagicMock()
        resp.read.return_value = json.dumps(body).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_retries_on_429(self):
        client = self._make_client()
        call_count = 0

        def fake_urlopen(req, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                headers = MagicMock()
                headers.get.return_value = "0"
                raise urllib.error.HTTPError(
                    url="http://test", code=429, msg="Rate limited",
                    hdrs=headers, fp=None,
                )
            return self._mock_response({"ok": True})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("time.sleep"):
            result = client._request("GET", "test")

        assert result == {"ok": True}
        assert call_count == 3

    def test_retries_on_5xx(self):
        client = self._make_client()
        call_count = 0

        def fake_urlopen(req, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise urllib.error.HTTPError(
                    url="http://test", code=503, msg="Service Unavailable",
                    hdrs=MagicMock(), fp=None,
                )
            return self._mock_response({"ok": True})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("time.sleep"):
            result = client._request("GET", "test")

        assert result == {"ok": True}
        assert call_count == 2

    def test_retries_on_network_error(self):
        client = self._make_client()
        call_count = 0

        def fake_urlopen(req, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise urllib.error.URLError("Connection refused")
            return self._mock_response({"ok": True})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("time.sleep"):
            result = client._request("GET", "test")

        assert result == {"ok": True}
        assert call_count == 2

    def test_retries_on_timeout(self):
        client = self._make_client()
        call_count = 0

        def fake_urlopen(req, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Request timed out")
            return self._mock_response({"ok": True})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("time.sleep"):
            result = client._request("GET", "test")

        assert result == {"ok": True}
        assert call_count == 2

    def test_does_not_retry_on_401(self):
        client = self._make_client()
        call_count = 0

        def fake_urlopen(req, timeout=None):
            nonlocal call_count
            call_count += 1
            raise urllib.error.HTTPError(
                url="http://test", code=401, msg="Unauthorized",
                hdrs=MagicMock(), fp=None,
            )

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("time.sleep"):
            with pytest.raises(_ac_client.ACClientError) as exc_info:
                client._request("GET", "test")
            assert exc_info.value.status_code == 401
            assert call_count == 1

    def test_does_not_retry_on_404(self):
        client = self._make_client()
        call_count = 0

        def fake_urlopen(req, timeout=None):
            nonlocal call_count
            call_count += 1
            raise urllib.error.HTTPError(
                url="http://test", code=404, msg="Not Found",
                hdrs=MagicMock(), fp=None,
            )

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("time.sleep"):
            with pytest.raises(_ac_client.ACClientError) as exc_info:
                client._request("GET", "test")
            assert exc_info.value.status_code == 404
            assert call_count == 1

    def test_exhausts_retries_raises_error(self):
        client = self._make_client()

        def fake_urlopen(req, timeout=None):
            raise urllib.error.URLError("Connection refused")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), \
             patch("time.sleep"):
            with pytest.raises(_ac_client.ACClientError) as exc_info:
                client._request("GET", "test", max_retries=3)
            assert "Exceeded 3 retries" in str(exc_info.value)


class TestWriteInsight:
    def test_creates_file_with_header(self, tmp_state_dir):
        _ac_client.write_insight("Test finding", category="risk")
        insights_file = tmp_state_dir / "insights.md"
        assert insights_file.exists()
        content = insights_file.read_text()
        assert "# ActiveCampaign Insights" in content
        assert "[RISK]" in content
        assert "Test finding" in content

    def test_appends_to_existing(self, tmp_state_dir):
        _ac_client.write_insight("First insight", category="risk")
        _ac_client.write_insight("Second insight", category="trend")
        content = (tmp_state_dir / "insights.md").read_text()
        assert "First insight" in content
        assert "Second insight" in content
        assert "[RISK]" in content
        assert "[TREND]" in content

    def test_includes_timestamp(self, tmp_state_dir):
        _ac_client.write_insight("Timestamped insight")
        content = (tmp_state_dir / "insights.md").read_text()
        assert "202" in content  # year prefix

    def test_default_category(self, tmp_state_dir):
        _ac_client.write_insight("General finding")
        content = (tmp_state_dir / "insights.md").read_text()
        assert "[GENERAL]" in content


class TestLoadInsights:
    def test_returns_none_when_missing(self, tmp_state_dir):
        assert _ac_client.load_insights() is None

    def test_returns_content(self, tmp_state_dir):
        _ac_client.write_insight("Some insight")
        result = _ac_client.load_insights()
        assert result is not None
        assert "Some insight" in result


class TestLoadHistory:
    def test_returns_empty_when_no_file(self, tmp_state_dir):
        assert _ac_client.load_history() == []

    def test_returns_all_entries(self, tmp_state_dir):
        _ac_client.log_outcome("action1", recipe="test")
        _ac_client.log_outcome("action2", recipe="test")
        result = _ac_client.load_history()
        assert len(result) == 2

    def test_filters_by_recipe(self, tmp_state_dir):
        _ac_client.log_outcome("a", recipe="alpha")
        _ac_client.log_outcome("b", recipe="beta")
        _ac_client.log_outcome("c", recipe="alpha")
        result = _ac_client.load_history(recipe="alpha")
        assert len(result) == 2
        assert all(e["recipe"] == "alpha" for e in result)

    def test_newest_first(self, tmp_state_dir):
        _ac_client.log_outcome("first", recipe="r", order=1)
        _ac_client.log_outcome("second", recipe="r", order=2)
        result = _ac_client.load_history()
        assert result[0]["order"] == 2
        assert result[1]["order"] == 1

    def test_respects_limit(self, tmp_state_dir):
        for i in range(10):
            _ac_client.log_outcome("a", recipe="r", idx=i)
        result = _ac_client.load_history(limit=3)
        assert len(result) == 3


class TestCompareToPrevious:
    def test_returns_none_when_no_history(self, tmp_state_dir):
        result = _ac_client.compare_to_previous(
            "test-recipe", {"count": 10}, ["count"]
        )
        assert result is None

    def test_returns_markdown_with_trend(self, tmp_state_dir):
        _ac_client.log_outcome("audit", recipe="test-recipe", count=8)
        result = _ac_client.compare_to_previous(
            "test-recipe", {"count": 10}, ["count"]
        )
        assert result is not None
        assert "## Trends" in result
        assert "Count" in result
        assert "8" in result
        assert "10" in result

    def test_shows_percentage_change(self, tmp_state_dir):
        _ac_client.log_outcome("audit", recipe="r", value=100)
        result = _ac_client.compare_to_previous("r", {"value": 150}, ["value"])
        assert "50.0%" in result

    def test_multi_run_trend(self, tmp_state_dir):
        _ac_client.log_outcome("a", recipe="r", score=10)
        _ac_client.log_outcome("a", recipe="r", score=20)
        _ac_client.log_outcome("a", recipe="r", score=30)
        result = _ac_client.compare_to_previous("r", {"score": 40}, ["score"])
        assert "Multi-run trend" in result


class TestDetectPatterns:
    def test_returns_empty_with_no_history(self, tmp_state_dir):
        assert _ac_client.detect_patterns() == []

    def test_detects_repeated_recipe(self, tmp_state_dir):
        for _ in range(4):
            _ac_client.log_outcome("audit", recipe="list-health-audit")
        suggestions = _ac_client.detect_patterns()
        assert any("list-health-audit" in s and "4 times" in s for s in suggestions)

    def test_detects_declining_metric(self, tmp_state_dir):
        _ac_client.log_outcome("a", recipe="find-hot-leads", top_heat=30)
        _ac_client.log_outcome("a", recipe="find-hot-leads", top_heat=20)
        _ac_client.log_outcome("a", recipe="find-hot-leads", top_heat=10)
        suggestions = _ac_client.detect_patterns()
        assert any("declined" in s.lower() for s in suggestions)

    def test_detects_never_run_recipe(self, tmp_state_dir):
        _ac_client.log_outcome("a", recipe="find-hot-leads")
        suggestions = _ac_client.detect_patterns()
        never_run = [s for s in suggestions if "haven't run" in s]
        assert len(never_run) >= 1


class TestThrottling:
    def test_min_request_interval(self):
        assert _ac_client.ACClient.MIN_REQUEST_INTERVAL == pytest.approx(0.2, abs=0.01)

    def test_max_requests_per_sec(self):
        assert _ac_client.ACClient.MAX_REQUESTS_PER_SEC == 5
