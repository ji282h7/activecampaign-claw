"""Tests for tasks_audit.analyze().

Fixtures match real /dealTasks response shape per AC v3 docs:
  https://developers.activecampaign.com/reference/list-all-tasks
Each item: id, title, note, duedate, status (1=complete, 0=incomplete),
relid, reltype (Deal|Subscriber), userid, assignee_userid, cdate, udate.
"""
from __future__ import annotations

from datetime import datetime, timezone

import tasks_audit


def _now():
    return datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)


def test_overdue_detection():
    data = {
        "tasks": [
            {
                "id": "1", "title": "Call back", "duedate": "2026-04-01T00:00:00+0000",
                "status": "0", "reltype": "Deal", "relid": "10",
                "userid": "1", "assignee_userid": "1",
                "cdate": "2026-03-25", "udate": "2026-03-25",
            },
            {
                "id": "2", "title": "Future task", "duedate": "2026-06-01T00:00:00+0000",
                "status": "0", "reltype": "Deal", "relid": "11",
                "userid": "1", "assignee_userid": "1",
                "cdate": "2026-05-01", "udate": "2026-05-01",
            },
            {
                "id": "3", "title": "Done", "duedate": "2026-04-10T00:00:00+0000",
                "status": "1", "reltype": "Subscriber", "relid": "501",
                "userid": "2", "assignee_userid": "2",
                "cdate": "2026-04-01", "udate": "2026-04-08",
            },
        ],
        "users": [
            {"id": "1", "firstName": "Ada", "lastName": "Lovelace", "email": "ada@x.co"},
            {"id": "2", "firstName": "Bert", "lastName": "Z", "email": "b@x.co"},
        ],
        "unavailable": False,
    }
    r = tasks_audit.analyze(data, now=_now())
    assert r["total_tasks"] == 3
    assert r["open"] == 2
    assert r["completed"] == 1
    assert r["overdue"] == 1
    assert r["overdue_tasks"][0]["id"] == "1"
    assert r["overdue_tasks"][0]["days_overdue"] >= 30
    assert r["by_reltype"] == {"Deal": 2, "Subscriber": 1}


def test_per_user_aggregation_and_completion_rate():
    data = {
        "tasks": [
            {"id": "1", "status": "1", "reltype": "Deal", "userid": "1", "assignee_userid": "1",
             "cdate": "2026-04-01", "udate": "2026-04-05", "duedate": None},
            {"id": "2", "status": "1", "reltype": "Deal", "userid": "1", "assignee_userid": "1",
             "cdate": "2026-04-01", "udate": "2026-04-08", "duedate": None},
            {"id": "3", "status": "0", "reltype": "Deal", "userid": "1", "assignee_userid": "1",
             "cdate": "2026-04-01", "udate": "2026-04-01",
             "duedate": "2026-04-15T00:00:00+0000"},
            {"id": "4", "status": "0", "reltype": "Deal", "userid": "2", "assignee_userid": "2",
             "cdate": "2026-04-01", "udate": "2026-04-01",
             "duedate": "2026-06-01T00:00:00+0000"},
        ],
        "users": [
            {"id": "1", "firstName": "A", "lastName": "L", "email": "a@x.co", "username": "a"},
            {"id": "2", "firstName": "B", "lastName": "M", "email": "b@x.co", "username": "b"},
        ],
        "unavailable": False,
    }
    r = tasks_audit.analyze(data, now=_now())
    by_user = {u["userid"]: u for u in r["users"]}
    assert by_user["1"]["completed"] == 2
    assert by_user["1"]["open"] == 1
    assert by_user["1"]["overdue"] == 1
    assert abs(by_user["1"]["completion_rate"] - 2 / 3) < 1e-6
    assert by_user["2"]["overdue"] == 0


def test_unassigned_bucket_when_no_userid():
    data = {
        "tasks": [
            {"id": "x", "status": "0", "reltype": "Deal",
             "userid": None, "assignee_userid": None,
             "cdate": "2026-04-01", "udate": "2026-04-01",
             "duedate": "2026-04-01T00:00:00+0000"},
        ],
        "users": [],
        "unavailable": False,
    }
    r = tasks_audit.analyze(data, now=_now())
    assert r["unassigned_open"] == 1
    by_user = {u["userid"]: u for u in r["users"]}
    assert "unassigned" in by_user
    assert by_user["unassigned"]["name"] == "(unassigned)"


def test_completion_age_median():
    data = {
        "tasks": [
            {"id": str(i), "status": "1", "reltype": "Deal",
             "userid": "1", "assignee_userid": "1",
             "cdate": f"2026-04-0{i}", "udate": f"2026-04-{(i+5):02d}"}
            for i in range(1, 6)
        ],
        "users": [{"id": "1"}],
        "unavailable": False,
    }
    r = tasks_audit.analyze(data, now=_now())
    assert r["median_completion_age_days"] == 5


def test_unavailable_renders_friendly_message():
    md = tasks_audit.render_markdown({"unavailable": True, "reason": "tasks_feature_not_enabled"})
    assert "Tasks feature not enabled" in md
    assert "403" in md


def test_render_includes_user_table():
    data = {
        "tasks": [
            {"id": "1", "status": "0", "reltype": "Deal", "userid": "1",
             "assignee_userid": "1", "cdate": "2026-04-01", "udate": "2026-04-01",
             "duedate": "2026-06-01T00:00:00+0000"},
        ],
        "users": [{"id": "1", "firstName": "Ada", "lastName": "L", "email": "a@x.co"}],
        "unavailable": False,
    }
    md = tasks_audit.render_markdown(tasks_audit.analyze(data, now=_now()))
    assert "Per-user workload" in md
    assert "Ada L" in md
