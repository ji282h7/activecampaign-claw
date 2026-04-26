"""
Mock ActiveCampaign API responses for testing.

Each fixture returns a dict matching the shape of the real AC v3 API response.
"""

from datetime import datetime, timedelta, timezone


def _ts(days_ago: int = 0) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.isoformat()


USERS_ME = {
    "user": {
        "username": "integration-bot",
        "email": "bot@testco.com",
        "id": "1",
    }
}

LISTS = {
    "lists": [
        {"id": "1", "name": "Master List", "stringid": "master-list"},
        {"id": "2", "name": "Newsletter", "stringid": "newsletter"},
        {"id": "3", "name": "Trial Users", "stringid": "trial-users"},
    ]
}

TAGS = {
    "tags": [
        {"id": "1", "tag": "VIP", "tagType": "contact"},
        {"id": "2", "tag": "Customer", "tagType": "contact"},
        {"id": "3", "tag": "Churned", "tagType": "contact"},
        {"id": "4", "tag": "Hot Lead", "tagType": "contact"},
    ]
}

FIELDS = {
    "fields": [
        {"id": "1", "title": "Plan", "type": "dropdown", "options": "Free||Pro||Enterprise"},
        {"id": "2", "title": "Company Size", "type": "text", "options": ""},
        {"id": "3", "title": "Last Conversion Date", "type": "date", "options": ""},
    ]
}

DEAL_CUSTOM_FIELD_META = {
    "dealCustomFieldMeta": [
        {"id": "1", "fieldLabel": "Contract Value", "fieldType": "currency"},
        {"id": "2", "fieldLabel": "Renewal Date", "fieldType": "date"},
    ]
}

DEAL_GROUPS = {
    "dealGroups": [
        {"id": "1", "title": "Sales Pipeline"},
        {"id": "2", "title": "Renewals"},
    ]
}

DEAL_STAGES = {
    "dealStages": [
        {"id": "1", "title": "Qualified", "order": "1", "group": "1"},
        {"id": "2", "title": "Proposal", "order": "2", "group": "1"},
        {"id": "3", "title": "Negotiation", "order": "3", "group": "1"},
        {"id": "4", "title": "Closed Won", "order": "4", "group": "1"},
        {"id": "5", "title": "Due for Renewal", "order": "1", "group": "2"},
        {"id": "6", "title": "Renewed", "order": "2", "group": "2"},
    ]
}

AUTOMATIONS = {
    "automations": [
        {"id": "1", "name": "Welcome Series", "status": "1", "entered": "450", "exited": "380"},
        {"id": "2", "name": "Re-engagement", "status": "1", "entered": "120", "exited": "95"},
        {"id": "3", "name": "Cart Abandonment", "status": "0", "entered": "30", "exited": "12"},
    ]
}


def make_campaigns(count: int = 10) -> dict:
    campaigns = []
    for i in range(count):
        days_ago = i * 7
        sent = 2000 + (i * 100)
        open_rate = 0.25 + (i % 5) * 0.02
        opens = int(sent * open_rate)
        clicks = int(sent * open_rate * 0.15)
        hour = 9 + (i % 8)
        dow_idx = i % 5
        dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
        dt = dt.replace(hour=hour, minute=0, second=0)

        campaigns.append({
            "id": str(i + 1),
            "name": f"Campaign {i + 1}",
            "subject": f"Test subject line number {i + 1} for testing",
            "sdate": dt.isoformat(),
            "send_amt": str(sent),
            "uniqueopens": str(opens),
            "uniquelinkclicks": str(clicks),
            "hardbounces": str(int(sent * 0.003)),
            "softbounces": str(int(sent * 0.008)),
            "unsubscribes": str(int(sent * 0.004)),
            "unsubreasons": "0",
        })
    return {"campaigns": campaigns}


CONTACTS_META_TOTAL = {
    "contacts": [],
    "meta": {"total": "4823"},
}

CONTACTS_META_NEW = {
    "contacts": [],
    "meta": {"total": "164"},
}


# --- Deals fixtures ---

def make_deals(count: int = 15) -> dict:
    deals = []
    stages = ["1", "1", "2", "2", "3", "3", "4", "1", "2", "3", "1", "2", "3", "4", "2"]
    for i in range(count):
        days_since_activity = (i * 5) % 40
        days_past_close = max(-10, (i * 3) - 15)
        value = (i + 1) * 10000
        status_val = "0" if i < 12 else "1"
        deals.append({
            "id": str(i + 1),
            "title": f"Deal {i + 1} — {'Acme' if i % 3 == 0 else 'Globex' if i % 3 == 1 else 'Initech'} Corp",
            "value": str(value),
            "currency": "usd",
            "group": "1",
            "stage": stages[i % len(stages)],
            "owner": str((i % 3) + 1),
            "status": status_val,
            "contact": str((i % 5) + 1),
            "cdate": _ts(60 + i),
            "mdate": _ts(days_since_activity),
            "nextdate": _ts(-days_past_close) if days_past_close < 0 else _ts(days_past_close),
        })
    return {"deals": deals}


DEAL_ACTIVITIES = {
    "dealActivities": [
        {"id": "1", "type": "note", "tstamp": _ts(2)},
        {"id": "2", "type": "call", "tstamp": _ts(5)},
    ]
}


# --- Contact engagement fixtures ---

def make_contacts_with_engagement(count: int = 50) -> dict:
    contacts = []
    for i in range(count):
        email_domain = ["gmail.com", "outlook.com", "yahoo.com", "acmecorp.com"][i % 4]
        days_since_last_open = (i * 8) % 365
        contacts.append({
            "id": str(i + 1),
            "email": f"user{i + 1}@{email_domain}",
            "firstName": f"User{i + 1}",
            "lastName": "Test",
            "cdate": _ts(180 + i * 3),
            "email_domain": email_domain,
            "scoreValues": [{"score_id": "1", "score_value": str(max(0, 100 - i * 5))}],
        })
    return {"contacts": contacts, "meta": {"total": str(count)}}


BOUNCE_LOGS = {
    "bounceLogs": [
        {"id": "1", "contact": "10", "campaignid": "5", "messageid": "5", "bouncetype": "hard", "email": "bounce@bad.com", "tstamp": _ts(3)},
        {"id": "2", "contact": "22", "campaignid": "7", "messageid": "7", "bouncetype": "soft", "email": "soft@slow.com", "tstamp": _ts(1)},
        {"id": "3", "contact": "33", "campaignid": "3", "messageid": "3", "bouncetype": "hard", "email": "gone@invalid.com", "tstamp": _ts(10)},
    ]
}


CONTACT_SCORE_VALUES = {
    "scoreValues": [
        {"score_id": "1", "score_value": "85", "contact_id": "1"},
    ]
}


SCORES = {
    "scores": [
        {"id": "1", "name": "Lead Score", "reltype": "contact", "status": "1"},
        {"id": "2", "name": "Deal Score", "reltype": "deal", "status": "1"},
    ]
}
