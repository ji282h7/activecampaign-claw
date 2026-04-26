"""Tests for automation_audit.analyze()."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import automation_audit


def test_completion_rate_and_orphan_detection():
    now = datetime.now(timezone.utc)
    recent = (now - timedelta(days=2)).isoformat()
    old = (now - timedelta(days=400)).isoformat()
    data = {
        "automations": [
            {"id": "1", "name": "Active", "status": "1"},
            {"id": "2", "name": "Orphan", "status": "1"},
            {"id": "3", "name": "Disabled", "status": "0"},
        ],
        "contact_automations": [
            # automation 1 — recent enrollments, mix of statuses
            {"automation": "1", "status": "1", "adddate": recent},  # active
            {"automation": "1", "status": "2", "adddate": recent},  # completed
            {"automation": "1", "status": "2", "adddate": recent},  # completed
            # automation 2 — only OLD enrollments → orphan
            {"automation": "2", "status": "2", "adddate": old},
        ],
    }
    r = automation_audit.analyze(data, window_days=30)
    by_id = {a["id"]: a for a in r["automations"]}
    assert by_id["1"]["enrolled_total"] == 3
    assert abs(by_id["1"]["completion_rate"] - 2 / 3) < 0.01
    assert by_id["1"]["recent_enrollments"] == 3
    # orphan flagged: status=1 but recent=0
    orphan_ids = {a["id"] for a in r["orphaned_active"]}
    assert "2" in orphan_ids
    assert "1" not in orphan_ids
    assert "3" not in orphan_ids  # status=0 not flagged as orphan
