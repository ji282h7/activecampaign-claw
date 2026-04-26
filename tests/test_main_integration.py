"""End-to-end main() tests for the most-used scripts.

Each test patches sys.argv, mocks ACClient where needed, and verifies that
main() runs cleanly and emits expected content. These catch CLI-flag bugs
and integration regressions that unit tests miss.
"""
from __future__ import annotations

import csv
import json
from unittest.mock import patch

import pytest

# ---------- import_validator (no AC client needed) ----------

class TestImportValidatorMain:
    def _write_csv(self, tmp_path, rows):
        p = tmp_path / "test.csv"
        with p.open("w", newline="") as f:
            w = csv.writer(f)
            for r in rows:
                w.writerow(r)
        return p

    def test_runs_and_prints_markdown(self, tmp_path, capsys):
        csv_path = self._write_csv(tmp_path, [
            ["Email"],
            ["alice@acme.com"],
            ["bob@beta.com"],
            ["info@acme.com"],
            ["malformed"],
        ])
        import import_validator

        with patch("sys.argv", ["import_validator.py", str(csv_path)]):
            import_validator.main()
            out = capsys.readouterr().out
            assert "Import Validation" in out
            assert "Verdict" in out

    def test_json_format(self, tmp_path, capsys):
        csv_path = self._write_csv(tmp_path, [["Email"], ["a@b.com"]])
        import import_validator

        with patch("sys.argv", ["import_validator.py", str(csv_path), "--format", "json"]):
            import_validator.main()
            out = capsys.readouterr().out
            data = json.loads(out)
            assert data["valid_rows"] == 1

    def test_missing_file_exits(self, tmp_path):
        import import_validator
        with patch("sys.argv", ["import_validator.py", str(tmp_path / "nope.csv")]):
            with pytest.raises(SystemExit):
                import_validator.main()


# ---------- audit_list_health ----------

class TestAuditListHealthMain:
    def test_runs_and_prints_markdown(self, ac_client_factory, state_file, capsys):
        client = ac_client_factory()
        import audit_list_health

        with patch("sys.argv", ["audit_list_health.py", "--format", "json"]), \
             patch("audit_list_health.ACClient", return_value=client), \
             patch("audit_list_health.write_insight"), \
             patch("audit_list_health.log_outcome"):
            audit_list_health.main()
            out = capsys.readouterr().out
            data = json.loads(out)
            assert "headline" in data
            assert "risks" in data
            assert "actions" in data


# ---------- find_hot_leads ----------

class TestFindHotLeadsMain:
    def test_runs_and_prints_json(self, ac_client_factory, state_file, capsys):
        client = ac_client_factory()
        import find_hot_leads

        with patch("sys.argv", ["find_hot_leads.py", "--format", "json", "--top", "5"]), \
             patch("find_hot_leads.ACClient", return_value=client), \
             patch("find_hot_leads.write_insight"), \
             patch("find_hot_leads.log_outcome"):
            find_hot_leads.main()
            out = capsys.readouterr().out
            data = json.loads(out)
            assert isinstance(data, list)


# ---------- dedupe_contacts ----------

class TestDedupeContactsMain:
    def test_runs_and_prints_markdown(self, ac_client_factory, capsys):
        client = ac_client_factory()
        import dedupe_contacts

        with patch("sys.argv", ["dedupe_contacts.py"]), \
             patch("dedupe_contacts.ACClient", return_value=client):
            dedupe_contacts.main()
            out = capsys.readouterr().out
            assert "Duplicate Contact Audit" in out

    def test_json_format(self, ac_client_factory, capsys):
        client = ac_client_factory()
        import dedupe_contacts

        with patch("sys.argv", ["dedupe_contacts.py", "--format", "json"]), \
             patch("dedupe_contacts.ACClient", return_value=client):
            dedupe_contacts.main()
            out = capsys.readouterr().out
            data = json.loads(out)
            assert "scanned" in data
            assert "email_case_duplicates" in data


# ---------- tag_merge ----------

class TestTagMergeMain:
    def test_dry_run_prints_plan(self, ac_client_factory, capsys):
        # Set up tags + contact_tags so the planner finds both source and target
        # plus contacts to re-tag.
        tags = {"tags": [
            {"id": "1", "tag": "Customer"},
            {"id": "2", "tag": "customer"},
        ]}
        contact_tags = {"contactTags": [
            {"id": "100", "contact": "A", "tag": "1"},
            {"id": "101", "contact": "B", "tag": "1"},
        ]}
        client = ac_client_factory({
            "tags": tags,
            "contactTags": contact_tags,
            "automations": {"automations": []},
            "segments": {"segments": []},
        })
        import tag_merge

        with patch("sys.argv", ["tag_merge.py",
                                "--source", "Customer",
                                "--target", "customer"]), \
             patch("tag_merge.ACClient", return_value=client):
            tag_merge.main()
            out = capsys.readouterr().out
            assert "Tag merge plan" in out
            assert "dry-run" in out
            # Should NOT have called any destructive API
            # (confirmed by the absence of "Executing merge" in stdout)
            assert "Executing merge" not in out

    def test_unknown_source_exits(self, ac_client_factory):
        client = ac_client_factory({
            "tags": {"tags": [{"id": "1", "tag": "customer"}]},
            "contactTags": {"contactTags": []},
            "automations": {"automations": []},
            "segments": {"segments": []},
        })
        import tag_merge

        with patch("sys.argv", ["tag_merge.py",
                                "--source", "DoesNotExist",
                                "--target", "customer"]), \
             patch("tag_merge.ACClient", return_value=client):
            with pytest.raises(SystemExit):
                tag_merge.main()
