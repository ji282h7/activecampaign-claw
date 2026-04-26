"""Tests for import_validator.py — pure local CSV validation."""

from __future__ import annotations

from pathlib import Path

import pytest

import import_validator


def _write_csv(tmp_path: Path, rows: list[str]) -> Path:
    p = tmp_path / "input.csv"
    p.write_text("\n".join(rows) + "\n")
    return p


class TestEmailColumnDetection:
    def test_detects_email_column(self, tmp_path):
        p = _write_csv(tmp_path, ["Email,FirstName", "a@b.com,Alice"])
        report = import_validator.analyze(p, None)
        assert report["email_column"] == "Email"
        assert report["valid_rows"] == 1

    def test_detects_email_address_column(self, tmp_path):
        p = _write_csv(tmp_path, ["Name,Email Address,Phone", "Alice,a@b.com,555"])
        report = import_validator.analyze(p, None)
        assert report["email_column"] == "Email Address"

    def test_explicit_column_override(self, tmp_path):
        p = _write_csv(tmp_path, ["work_email,personal_email", "a@work.com,b@home.com"])
        report = import_validator.analyze(p, "personal_email")
        assert report["email_column"] == "personal_email"
        assert "b@home.com" in (report["top_domains"][0][0] or "") or report["valid_rows"] == 1


class TestRowAnalysis:
    def test_counts_malformed(self, tmp_path):
        p = _write_csv(tmp_path, ["Email", "a@b.com", "not-an-email", "x@y.co"])
        report = import_validator.analyze(p, "Email")
        assert report["malformed_count"] == 1
        assert report["valid_rows"] == 2

    def test_counts_blanks(self, tmp_path):
        # Use multi-column rows so the empty value isn't a row-level blank line that
        # csv.DictReader may collapse — exercise the script's blank-value handling.
        p = _write_csv(tmp_path, ["Email,Name", "a@b.com,Alice", ",Bob", ",Carol"])
        report = import_validator.analyze(p, "Email")
        assert report["blank_emails"] == 2

    def test_detects_role_addresses(self, tmp_path):
        p = _write_csv(tmp_path, ["Email", "info@acme.com", "support@acme.com", "alice@acme.com"])
        report = import_validator.analyze(p, "Email")
        assert report["role_address_count"] == 2

    def test_detects_case_insensitive_duplicates(self, tmp_path):
        p = _write_csv(tmp_path, ["Email", "Alice@Acme.com", "alice@acme.com", "ALICE@ACME.COM"])
        report = import_validator.analyze(p, "Email")
        assert report["duplicate_count"] == 1
        assert "alice@acme.com" in report["duplicate_sample"]

    def test_free_vs_corporate_split(self, tmp_path):
        p = _write_csv(tmp_path, [
            "Email",
            "a@gmail.com", "b@yahoo.com", "c@acme.com", "d@beta.io",
        ])
        report = import_validator.analyze(p, "Email")
        assert report["free_mail_count"] == 2
        assert report["corporate_count"] == 2


class TestRender:
    def test_clean_verdict(self, tmp_path):
        p = _write_csv(tmp_path, ["Email", "alice@acme.com", "bob@beta.io"])
        report = import_validator.analyze(p, "Email")
        out = import_validator.render_markdown(report)
        assert "safe to import" in out

    def test_dirty_verdict(self, tmp_path):
        p = _write_csv(tmp_path, ["Email", "info@acme.com", "alice@acme.com"])
        report = import_validator.analyze(p, "Email")
        out = import_validator.render_markdown(report)
        assert "clean up flagged rows" in out


class TestEmptyAndEdgeCases:
    def test_no_email_column_raises(self, tmp_path):
        p = _write_csv(tmp_path, ["Name,Phone", "Alice,555"])
        with pytest.raises(SystemExit):
            import_validator.analyze(p, None)

    def test_empty_file_handled(self, tmp_path):
        p = _write_csv(tmp_path, ["Email"])
        report = import_validator.analyze(p, "Email")
        assert report["total_rows"] == 0
        assert report["valid_rows"] == 0
