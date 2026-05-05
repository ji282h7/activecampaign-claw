"""Tests for sales_rep_performance.analyze().

Fixtures match real shapes:
  - /users: id, firstName, lastName, username, email
  - /deals: id, owner (userid), status (0=open, 1=won, 2=lost, 3=hot),
           value (cents)
  - /dealTasks: id, status, assignee_userid, userid, duedate, cdate, udate
  - /notes: id, note, reltype, relid, userid, cdate, mdate
"""
from __future__ import annotations

from datetime import datetime, timezone

import sales_rep_performance as srp


def _now():
    return datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)


def _data():
    return {
        "users": [
            {"id": "1", "firstName": "Ada", "lastName": "L",
             "email": "ada@x.co", "username": "ada"},
            {"id": "2", "firstName": "Bert", "lastName": "Z",
             "email": "b@x.co", "username": "bert"},
        ],
        "deals": [
            {"id": "10", "owner": "1", "status": "0", "value": 0},
            {"id": "11", "owner": "1", "status": "1", "value": 250000},
            {"id": "12", "owner": "1", "status": "1", "value": 150000},
            {"id": "13", "owner": "1", "status": "2", "value": 0},
            {"id": "20", "owner": "2", "status": "0", "value": 0},
        ],
        "deal_tasks": [
            {"id": "t1", "assignee_userid": "1", "userid": "1", "status": "0",
             "duedate": "2026-04-01T00:00:00+0000",
             "cdate": "2026-03-01", "udate": "2026-03-01"},
            {"id": "t2", "assignee_userid": "1", "userid": "1", "status": "1",
             "duedate": "2026-04-15T00:00:00+0000",
             "cdate": "2026-03-01", "udate": "2026-04-10"},
            {"id": "t3", "assignee_userid": "2", "userid": "2", "status": "0",
             "duedate": "2026-06-01T00:00:00+0000",
             "cdate": "2026-04-01", "udate": "2026-04-01"},
        ],
        "notes": [
            {"id": "n1", "note": "Got on a call.", "reltype": "Deal",
             "relid": "10", "userid": "1", "cdate": "2026-05-01",
             "mdate": "2026-05-01"},
            {"id": "n2", "note": "Long detailed note here describing the conversation.",
             "reltype": "Deal", "relid": "11", "userid": "1",
             "cdate": "2026-05-01", "mdate": "2026-05-01"},
        ],
        "deals_unavailable": False,
    }


def test_per_rep_deals_aggregation():
    r = srp.analyze(_data(), now=_now())
    by_uid = {row["userid"]: row for row in r["reps"]}
    ada = by_uid["1"]
    assert ada["deals_open"] == 1
    assert ada["deals_won"] == 2
    assert ada["deals_lost"] == 1
    assert abs(ada["win_rate"] - 2 / 3) < 1e-6
    assert ada["avg_won_value_cents"] == 200000  # (250000 + 150000) / 2


def test_task_overdue_counted():
    r = srp.analyze(_data(), now=_now())
    by_uid = {row["userid"]: row for row in r["reps"]}
    assert by_uid["1"]["tasks_overdue"] == 1
    assert by_uid["1"]["tasks_completed"] == 1
    assert by_uid["2"]["tasks_overdue"] == 0


def test_notes_aggregated_per_user():
    r = srp.analyze(_data(), now=_now())
    by_uid = {row["userid"]: row for row in r["reps"]}
    assert by_uid["1"]["notes_count"] == 2
    assert by_uid["2"]["notes_count"] == 0


def test_activity_score_sorts_reps():
    r = srp.analyze(_data(), now=_now())
    # Ada: 2 notes + 1 task completed * 2 = 4. Bert: 0. Ada should come first.
    assert r["reps"][0]["userid"] == "1"


def test_deals_unavailable_path():
    data = {
        "users": [{"id": "1", "firstName": "Ada", "lastName": "L", "email": "a@x.co"}],
        "notes": [{"id": "n1", "note": "x", "reltype": "Subscriber",
                   "relid": "501", "userid": "1", "cdate": "2026-05-01",
                   "mdate": "2026-05-01"}],
        "deals_unavailable": True,
    }
    r = srp.analyze(data, now=_now())
    assert r["deals_unavailable"] is True
    md = srp.render_markdown(r)
    assert "Deals + tasks unavailable" in md
    assert "Avg note length" in md


def test_user_with_no_activity_present():
    r = srp.analyze(_data(), now=_now())
    by_uid = {row["userid"]: row for row in r["reps"]}
    bert = by_uid["2"]
    assert bert["deals_open"] == 1
    assert bert["activity_score"] == 0
