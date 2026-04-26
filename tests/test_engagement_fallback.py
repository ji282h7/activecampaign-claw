"""Tests for fetch_engagement_events() — the messageActivities → linkData fallback."""

from __future__ import annotations

from unittest.mock import patch

import _ac_client
import pytest


def _client():
    with patch("_ac_client.ACClient.__init__", lambda self, *a, **kw: None):
        c = _ac_client.ACClient.__new__(_ac_client.ACClient)
        c.base = "https://test.api-us1.com/api/3"
        c.token = "test-token"
        c._request_count = 0
        return c


class TestFetchEngagementEventsPrimary:
    def test_uses_messageActivities_when_available(self):
        c = _client()
        events = [
            {"event": "open", "contact": "1", "tstamp": "2026-04-01T10:00:00Z", "campaign": "5", "email": "a@x.com"},
            {"event": "click", "contact": "2", "tstamp": "2026-04-02T11:00:00Z", "campaign": "5", "email": "b@x.com"},
        ]

        def fake_paginate(path, key, max_items=None, **kwargs):
            assert path == "messageActivities"
            return events

        with patch.object(c, "paginate", side_effect=fake_paginate):
            out = c.fetch_engagement_events(max_items=100)

        assert len(out) == 2
        assert out[0]["event"] == "open"
        assert out[0]["contact"] == "1"
        assert out[0]["campaign"] == "5"


class TestFetchEngagementEventsFallback:
    def test_falls_back_to_linkData_on_404(self):
        c = _client()
        link_events = [
            {"contact": "10", "campaign": "3", "link": "1", "email": "x@y.com", "tstamp": "2026-04-01T12:00:00Z"},
            {"contact": "11", "campaign": "3", "link": "2", "email": "y@z.com", "tstamp": "2026-04-02T13:00:00Z"},
        ]
        calls = []

        def fake_paginate(path, key, max_items=None, **kwargs):
            calls.append(path)
            if path == "messageActivities":
                raise _ac_client.ACClientError(404, "Resource not found: messageActivities")
            if path == "linkData":
                return link_events
            return []

        with patch.object(c, "paginate", side_effect=fake_paginate):
            out = c.fetch_engagement_events(max_items=100)

        assert calls == ["messageActivities", "linkData"]
        assert len(out) == 2
        assert all(e["event"] == "click" for e in out)
        assert out[0]["contact"] == "10"
        assert out[0]["link"] == "1"

    def test_propagates_non_404_errors(self):
        c = _client()

        def fake_paginate(path, key, max_items=None, **kwargs):
            raise _ac_client.ACClientError(500, "boom")

        with patch.object(c, "paginate", side_effect=fake_paginate):
            with pytest.raises(_ac_client.ACClientError) as exc:
                c.fetch_engagement_events(max_items=100)
        assert exc.value.status_code == 500


class TestFallbackEmptyResponse:
    def test_empty_messageActivities_returns_empty(self):
        c = _client()
        with patch.object(c, "paginate", return_value=[]):
            out = c.fetch_engagement_events(max_items=100)
        assert out == []
