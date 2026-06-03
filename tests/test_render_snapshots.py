"""Snapshot tests for representative markdown renderers.

We assert against the full output rather than substring presence, so
silent formatting drift fails loudly. Snapshots live inline (small) to
keep the test file self-contained.

If a snapshot needs updating after an intentional change:
  1. Run the test, see the diff.
  2. Replace the EXPECTED string with the new output.
  3. Re-run.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import notes_analysis  # noqa: E402
import tasks_audit  # noqa: E402


def _now() -> datetime:
    return datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)


def test_tasks_audit_friendly_unavailable_snapshot():
    """Plan-tier rendering should remain stable — no `ERROR:` reappearance."""
    md = tasks_audit.render_markdown(
        {"unavailable": True, "reason": "tasks_feature_not_enabled"}
    )
    expected_lines = [
        "# Not available on your ActiveCampaign plan",
        "",
        "**Tasks (CRM)** requires the **Plus** plan or higher on ActiveCampaign. Your current plan doesn't expose this endpoint, so this report can't be generated.",
        "",
        "*Tasks audit needs the /dealTasks endpoint.*",
        "",
        "This isn't a bug — your account just isn't on a tier that includes the feature. If you upgrade your AC plan, re-run the script and it will work without changes.",
        "",
        "Other scripts in this skill that don't depend on **Tasks (CRM)** will still work normally.",
        "",
    ]
    actual_lines = md.split("\n")
    assert actual_lines == expected_lines, (
        "Renderer drift:\n--- EXPECTED ---\n"
        + "\n".join(expected_lines)
        + f"\n--- ACTUAL ---\n{md}"
    )


def test_tasks_audit_empty_data_snapshot():
    """An empty analyze() result should render a stable shell."""
    data = {"tasks": [], "users": [], "unavailable": False}
    r = tasks_audit.analyze(data, now=_now())
    md = tasks_audit.render_markdown(r)
    expected = "\n".join([
        "# Tasks Audit",
        "",
        "- Total tasks: **0** (open: 0, completed: 0)",
        "- Overdue (open + past due date): **0**",
        "- Unassigned open tasks: **0**",
        "- Reltype breakdown: {}",
        "",
    ])
    assert md == expected, (
        f"Renderer drift:\n--- EXPECTED ---\n{expected}\n"
        f"--- ACTUAL ---\n{md}"
    )


def test_notes_analysis_empty_data_snapshot():
    data = {"notes": [], "users": []}
    r = notes_analysis.analyze(data, stale_days=30, now=_now())
    md = notes_analysis.render_markdown(r)
    expected = "\n".join([
        "# Notes Analysis",
        "",
        "- Total notes: **0**",
        "- Breakdown by reltype: {}",
        "- Notes containing action-item language: **0**",
        "- Deals whose latest note is ≥30 days old: **0**",
        "",
    ])
    assert md == expected, (
        f"Renderer drift:\n--- EXPECTED ---\n{expected}\n"
        f"--- ACTUAL ---\n{md}"
    )


def test_tasks_audit_one_overdue_task_snapshot():
    """A single-overdue scenario locks the column widths + per-user format."""
    data = {
        "tasks": [
            {"id": "1", "title": "Call back",
             "duedate": "2026-04-01T00:00:00+0000",
             "status": "0", "reltype": "Deal", "relid": "100",
             "userid": "1", "assignee_userid": "1",
             "cdate": "2026-03-25", "udate": "2026-03-25"},
        ],
        "users": [
            {"id": "1", "firstName": "Ada", "lastName": "L",
             "email": "ada@x.co"},
        ],
        "unavailable": False,
    }
    r = tasks_audit.analyze(data, now=_now())
    md = tasks_audit.render_markdown(r)
    # Lock the key structural lines, not exact whitespace of the table
    # (because day-counts depend on `now()`).
    assert "# Tasks Audit" in md
    assert "- Total tasks: **1** (open: 1, completed: 0)" in md
    assert "- Overdue (open + past due date): **1**" in md
    assert "- Unassigned open tasks: **0**" in md
    assert "- Reltype breakdown: {'Deal': 1}" in md
    assert "## Per-user workload" in md
    assert "| Ada L | 1 | 0 | 1 | 0% |" in md
    assert "## Most overdue tasks" in md
