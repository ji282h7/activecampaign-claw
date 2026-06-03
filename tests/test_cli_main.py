"""Tests for the cli_main() driver in _skill/cli.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from _ac_client import ACClientError, cli_main  # noqa: E402


def _build_argv(*args: str) -> list[str]:
    return ["script.py", *args]


def test_minimal_pipeline_prints_markdown(monkeypatch, capsys):
    """fetch → analyze → render → print is the no-arg, no-output happy path."""
    monkeypatch.setenv("AC_API_URL", "https://test.api-us1.com")
    monkeypatch.setenv("AC_API_TOKEN", "tok")
    monkeypatch.setattr(sys, "argv", _build_argv())

    def fetch(client):
        return {"n": 3}
    def analyze(data):
        return {"count": data["n"]}
    def render(report):
        return f"# Result\n\n- Count: {report['count']}"

    cli_main(description="x", fetch_data=fetch, analyze=analyze, render_markdown=render)
    out = capsys.readouterr().out
    assert "# Result" in out
    assert "Count: 3" in out


def test_format_json_serializes_report(monkeypatch, capsys):
    monkeypatch.setenv("AC_API_URL", "https://test.api-us1.com")
    monkeypatch.setenv("AC_API_TOKEN", "tok")
    monkeypatch.setattr(sys, "argv", _build_argv("--format", "json"))

    def fetch(client): return {}
    def analyze(data): return {"a": 1, "b": [2, 3]}
    def render(report): return "should not be printed in json mode"

    cli_main(description="x", fetch_data=fetch, analyze=analyze, render_markdown=render)
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed == {"a": 1, "b": [2, 3]}


def test_output_path_writes_file_and_emits_trailer(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("AC_API_URL", "https://test.api-us1.com")
    monkeypatch.setenv("AC_API_TOKEN", "tok")
    outpath = tmp_path / "report.md"
    monkeypatch.setattr(sys, "argv", _build_argv("--output", str(outpath)))

    def fetch(client): return {}
    def analyze(data): return {}
    def render(report): return "# Hello"

    cli_main(description="x", fetch_data=fetch, analyze=analyze, render_markdown=render)
    assert outpath.read_text() == "# Hello"
    out = capsys.readouterr().out
    # The __SKILL_FILES__ trailer should land on stdout
    assert "__SKILL_FILES__:" in out
    assert str(outpath) in out


def test_add_arguments_callback_threads_through(monkeypatch, capsys):
    monkeypatch.setenv("AC_API_URL", "https://test.api-us1.com")
    monkeypatch.setenv("AC_API_TOKEN", "tok")
    monkeypatch.setattr(sys, "argv", _build_argv("--threshold", "42"))

    def add_args(p):
        p.add_argument("--threshold", type=int, default=10)
    def fetch(client, args):
        return {"t": args.threshold}
    def analyze(data, args):
        return {"effective_threshold": data["t"]}
    def render(report):
        return f"t={report['effective_threshold']}"

    cli_main(description="x", fetch_data=fetch, analyze=analyze,
             render_markdown=render, add_arguments=add_args)
    assert "t=42" in capsys.readouterr().out


def test_feature_unavailable_renders_friendly_on_403(monkeypatch, capsys):
    monkeypatch.setenv("AC_API_URL", "https://test.api-us1.com")
    monkeypatch.setenv("AC_API_TOKEN", "tok")
    monkeypatch.setattr(sys, "argv", _build_argv())

    def fetch(client):
        raise ACClientError(403, "Deals feature not enabled")
    def analyze(data): return data
    def render(report): return "should not be called"

    cli_main(
        description="x",
        fetch_data=fetch,
        analyze=analyze,
        render_markdown=render,
        feature_unavailable=("Deals (CRM)", "Plus", "Test report needs /deals."),
    )
    out = capsys.readouterr().out
    assert "Not available on your ActiveCampaign plan" in out
    assert "Deals (CRM)" in out
    assert "ERROR" not in out


def test_non_403_error_still_propagates(monkeypatch):
    monkeypatch.setenv("AC_API_URL", "https://test.api-us1.com")
    monkeypatch.setenv("AC_API_TOKEN", "tok")
    monkeypatch.setattr(sys, "argv", _build_argv())

    def fetch(client):
        raise ACClientError(500, "boom")
    def analyze(data): return data
    def render(report): return ""

    with pytest.raises(ACClientError):
        cli_main(
            description="x",
            fetch_data=fetch,
            analyze=analyze,
            render_markdown=render,
            feature_unavailable=("X", "Plus", "y"),
        )


def test_history_recipe_logs_entry(monkeypatch, tmp_state_dir, capsys):
    """tmp_state_dir patches STATE_DIR + HISTORY_FILE for the underlying writer."""
    monkeypatch.setenv("AC_API_URL", "https://test.api-us1.com")
    monkeypatch.setenv("AC_API_TOKEN", "tok")
    monkeypatch.setattr(sys, "argv", _build_argv())

    history_path = tmp_state_dir / "history.jsonl"

    def fetch(client): return {}
    def analyze(data): return {"foo": 7, "bar": 11}
    def render(report): return f"foo={report['foo']}"

    cli_main(
        description="x",
        fetch_data=fetch,
        analyze=analyze,
        render_markdown=render,
        history_recipe="example-recipe",
        history_metrics=lambda r: {"foo": r["foo"], "bar": r["bar"]},
    )

    assert history_path.exists()
    line = history_path.read_text().splitlines()[-1]
    entry = json.loads(line)
    assert entry["action"] == "example-recipe_executed"
    assert entry["recipe"] == "example-recipe"
    assert entry["foo"] == 7
    assert entry["bar"] == 11
