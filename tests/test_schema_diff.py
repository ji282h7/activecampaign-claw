"""Tests for schema_diff.py — local snapshot diffing."""

from __future__ import annotations

import schema_diff


class TestDiffCollection:
    def test_added_and_removed(self):
        before = [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]
        after = [{"id": "1", "name": "A"}, {"id": "3", "name": "C"}]
        d = schema_diff._diff_collection(before, after, "name")
        assert len(d["added"]) == 1
        assert d["added"][0]["id"] == "3"
        assert len(d["removed"]) == 1
        assert d["removed"][0]["id"] == "2"
        assert d["renamed"] == []

    def test_renamed(self):
        before = [{"id": "1", "name": "Original"}]
        after = [{"id": "1", "name": "Renamed"}]
        d = schema_diff._diff_collection(before, after, "name")
        assert len(d["renamed"]) == 1
        assert d["renamed"][0]["from"] == "Original"
        assert d["renamed"][0]["to"] == "Renamed"


class TestFullDiff:
    def test_status_change_detected(self):
        before = {"taxonomy": {"automations": [{"id": "1", "name": "Welcome", "status": "1"}]}}
        after = {"taxonomy": {"automations": [{"id": "1", "name": "Welcome", "status": "0"}]}}
        d = schema_diff.diff(before, after)
        sc = d["automations"]["status_changed"]
        assert len(sc) == 1
        assert sc[0]["from"] == "1"
        assert sc[0]["to"] == "0"

    def test_render_no_changes(self):
        same = {"taxonomy": {"lists": [{"id": "1", "name": "Main"}]}}
        d = schema_diff.diff(same, same)
        out = schema_diff.render_markdown(d)
        assert "No structural changes" in out

    def test_handles_taxonomy_at_top_level_or_nested(self):
        # snapshot files written by export_account.py wrap under "taxonomy";
        # raw exports may be flat. The diff should accept both.
        wrapped = {"taxonomy": {"tags": [{"id": "1", "name": "vip"}]}}
        flat = {"tags": [{"id": "1", "name": "vip"}]}
        d = schema_diff.diff(wrapped, flat)
        # both shapes should yield no diff for tags
        assert d["tags"]["added"] == []
        assert d["tags"]["removed"] == []
        assert d["tags"]["renamed"] == []
