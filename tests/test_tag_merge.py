"""Tests for tag_merge.build_plan() and execute()."""
from __future__ import annotations

import tag_merge


def _data(tags, contact_tags, automations=None, segments=None):
    return {
        "tags": tags,
        "contact_tags": contact_tags,
        "automations": automations or [],
        "segments": segments or [],
    }


def test_plan_basic_merge():
    tags = [{"id": "1", "tag": "Customer"}, {"id": "2", "tag": "customer"}]
    contact_tags = [
        {"id": "100", "contact": "A", "tag": "1"},
        {"id": "101", "contact": "B", "tag": "1"},
        {"id": "102", "contact": "B", "tag": "2"},
    ]
    plan = tag_merge.build_plan(_data(tags, contact_tags), "Customer", "customer")
    assert plan["source"]["id"] == "1"
    assert plan["target"]["id"] == "2"
    assert plan["affected_contacts"] == 2
    # Only A needs the target tag added; B already has both
    assert plan["contacts_needing_target"] == ["A"]
    assert plan["contact_tag_records_to_create"] == 1
    assert plan["contact_tag_records_to_delete"] == 2


def test_plan_missing_source_returns_suggestions():
    tags = [{"id": "1", "tag": "customer"}, {"id": "2", "tag": "Customer-Tier-1"}]
    plan = tag_merge.build_plan(_data(tags, []), "customers", "customer")
    assert "error" in plan
    assert "customer" in plan["suggestions"]


def test_plan_missing_target_returns_error():
    tags = [{"id": "1", "tag": "Customer"}]
    plan = tag_merge.build_plan(_data(tags, []), "Customer", "customer")
    assert "error" in plan
    assert "not found" in plan["error"]


def test_plan_same_tag_rejected():
    tags = [{"id": "1", "tag": "Customer"}]
    plan = tag_merge.build_plan(_data(tags, []), "Customer", "Customer")
    assert "same tag" in plan["error"]


def test_plan_detects_automation_references():
    tags = [{"id": "1", "tag": "VIP"}, {"id": "2", "tag": "vip"}]
    contact_tags = [{"id": "100", "contact": "A", "tag": "1"}]
    automations = [{"id": "5", "name": "VIP welcome", "blocks": "tag VIP applied"}]
    plan = tag_merge.build_plan(_data(tags, contact_tags, automations), "VIP", "vip")
    assert len(plan["automation_refs"]) == 1
    assert plan["automation_refs"][0]["id"] == "5"


def test_plan_detects_segment_references():
    tags = [{"id": "1", "tag": "VIP"}, {"id": "2", "tag": "vip"}]
    segments = [{"id": "9", "name": "VIPs only", "logic": "has VIP tag"}]
    plan = tag_merge.build_plan(_data(tags, [], segments=segments), "VIP", "vip")
    assert len(plan["segment_refs"]) == 1


def test_render_plan_includes_warnings_when_refs_exist():
    tags = [{"id": "1", "tag": "VIP"}, {"id": "2", "tag": "vip"}]
    automations = [{"id": "5", "name": "VIP welcome", "blocks": "VIP"}]
    plan = tag_merge.build_plan(_data(tags, [], automations), "VIP", "vip")
    md = tag_merge.render_plan(plan)
    assert "Automation references" in md
    assert "VIP welcome" in md
    assert "force-with-refs" in md


def test_render_plan_handles_error_with_suggestions():
    tags = [{"id": "1", "tag": "customer"}]
    plan = tag_merge.build_plan(_data(tags, []), "customers", "customer")
    md = tag_merge.render_plan(plan)
    assert "ERROR" in md
    assert "Did you mean" in md


def test_execute_refuses_when_refs_present_without_force(ac_client_factory):
    plan = {
        "source": {"id": "1", "name": "VIP"},
        "target": {"id": "2", "name": "vip"},
        "contacts_with_source": {},
        "contacts_needing_target": [],
        "affected_contacts": 0,
        "contact_tag_records_to_create": 0,
        "contact_tag_records_to_delete": 0,
        "automation_refs": [{"id": "5", "name": "VIP welcome"}],
        "segment_refs": [],
    }
    client = ac_client_factory({})
    try:
        tag_merge.execute(client, plan, force_with_refs=False)
        raise AssertionError("expected SystemExit")
    except SystemExit as e:
        assert "force-with-refs" in str(e)


def test_execute_calls_post_delete_in_order(ac_client_factory):
    calls = []

    def make_client():
        client = ac_client_factory({})
        client.post = lambda path, payload: calls.append(("POST", path, payload)) or {}
        client.delete = lambda path: calls.append(("DELETE", path)) or {}
        return client

    plan = {
        "source": {"id": "1", "name": "Customer"},
        "target": {"id": "2", "name": "customer"},
        "contacts_with_source": {"A": "100", "B": "101"},
        "contacts_needing_target": ["A"],
        "affected_contacts": 2,
        "contact_tag_records_to_create": 1,
        "contact_tag_records_to_delete": 2,
        "automation_refs": [],
        "segment_refs": [],
    }
    client = make_client()
    result = tag_merge.execute(client, plan, force_with_refs=False)

    posts = [c for c in calls if c[0] == "POST"]
    deletes = [c for c in calls if c[0] == "DELETE"]
    assert len(posts) == 1  # apply target to A
    assert posts[0][2]["contactTag"]["tag"] == "2"
    assert posts[0][2]["contactTag"]["contact"] == "A"
    # Two contactTag deletes (one per affected contact) + one tag delete
    assert len(deletes) == 3
    assert deletes[-1] == ("DELETE", "tags/1")
    assert result["target_applied"] == 1
    assert result["source_removed"] == 2
    assert result["tag_deleted"] is True


def test_execute_skips_tag_delete_if_detag_errors(ac_client_factory):
    from _ac_client import ACClientError

    delete_calls = []

    def failing_delete(path):
        delete_calls.append(path)
        if path.startswith("contactTags/"):
            raise ACClientError(500, "boom")
        return {}

    plan = {
        "source": {"id": "1", "name": "Customer"},
        "target": {"id": "2", "name": "customer"},
        "contacts_with_source": {"A": "100"},
        "contacts_needing_target": [],
        "affected_contacts": 1,
        "contact_tag_records_to_create": 0,
        "contact_tag_records_to_delete": 1,
        "automation_refs": [],
        "segment_refs": [],
    }
    client = ac_client_factory({})
    client.post = lambda path, payload: {}
    client.delete = failing_delete
    result = tag_merge.execute(client, plan, force_with_refs=False)
    assert result["tag_deleted"] is False
    # tags/1 is never attempted because detag failed
    assert "tags/1" not in delete_calls
