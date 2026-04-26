# AI Marketing + ActiveCampaign

[![tests](https://github.com/ji282h7/activecampaign-claw/actions/workflows/test.yml/badge.svg)](https://github.com/ji282h7/activecampaign-claw/actions/workflows/test.yml)
[![python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![release](https://img.shields.io/badge/release-1.0.0-orange)](CHANGELOG.md)
[![scripts](https://img.shields.io/badge/scripts-50-success)](#what-it-can-do)
[![tests](https://img.shields.io/badge/tests-431%20passing-brightgreen)](tests/)
[![coverage](https://img.shields.io/badge/coverage-59%25-yellow)](tests/)
[![ActiveCampaign](https://img.shields.io/badge/ActiveCampaign-v3%20API-blue)](https://developers.activecampaign.com/reference)

> An ActiveCampaign agent for marketers and sales teams. Asks questions in plain English; runs real diagnostics on your account; produces reports you'd otherwise spend a day building in spreadsheets.

## Why this exists

ActiveCampaign's UI is fine for *running* campaigns. It's frustrating for *understanding* them. The reports are scattered, the segment builder is fiddly, and there's no way to ask "of the contacts who joined in March, what % opened anything since?" without exporting CSVs and pivoting them yourself.

This skill plugs the v3 API into a Claude agent so you can just ask the question. It already knows your lists, tags, custom fields, automations, pipelines, and 90 days of campaign baselines (because calibration scans them once at install time). When you ask "find me my hottest leads" or "which subject lines actually work" or "are there dead tags I should clean up," it runs the right report against your real data and gives you a marker-friendly markdown summary.

## What it can do

### Performance analysis (you ask, it pulls)
- **Campaign postmortems** — every metric for one send, vs. your account baseline, with per-link CTR
- **Subject line analysis** — your top performers clustered by length, emoji, urgency, personalization, and ranked by lift
- **Send time optimization** — when your specific audience opens, by hour and day of week
- **Send frequency report** — who's getting fatigued (>8 sends/month) vs. who's been forgotten
- **Domain breakdown** — engagement by Gmail / Outlook / corporate; catches deliverability problems before they snowball
- **Engagement decay** — cohort retention plot; see when your list goes dead
- **From-name performance** — which sender name actually gets opened
- **Monthly trend** — opens/clicks/unsubs/bounces over time vs. baseline
- **Baseline drift detector** — pings you when a metric drops >1σ from calibrated normal

### List & contact health
- **List health audit** — bounces, role addresses, free-vs-corporate domains, suppressions to clean up
- **Duplicate finder** — case-insensitive emails, normalized phones, fuzzy name+company
- **Role address detector** — surfaces `info@`, `support@`, `noreply@` clutter
- **Field completeness** — which contacts have which fields populated, broken down by source
- **Stale contacts** — who hasn't engaged with anything in N months
- **New subscriber quality** — recent additions opening / bouncing / unsubscribing
- **List growth forecast** — linear projection of size N days out
- **Pre-import CSV validator** — catches bad emails, duplicates, role addresses *before* you import them

### Lead scoring & sales
- **Hot leads** — ranked by engagement signals (scores, recent activity, deal stage)
- **Slipping deals** — stale, overdue, or stuck in a stage too long *(needs Deals feature)*
- **MQL→SQL handoff** — who crossed the scoring threshold and got a deal vs. who didn't *(Deals)*
- **Win/loss by source** — which lists/tags/forms produce winning pipeline *(Deals)*
- **Pipeline audit** — per-stage health, value distribution, field completeness *(Deals)*

### Automation hygiene
- **Audit** — orphaned automations (active but enrolling no one), completion rates
- **Funnel** — per-step dropoff inside one automation
- **Overlap** — contacts in 3+ active automations (un-coordinated programs)
- **Stalled enrollments** — contacts whose step hasn't advanced in N days (broken Wait or If/Else)
- **Dependency map** — which automations enroll into which others
- **Broken-ref detector** — refs to deleted tags / fields / messages

### Tag, field, list & segment hygiene
- **Tag audit** — typo tags, dead tags (no automation/segment uses them), consolidation candidates that always co-occur
- **Custom field audit** — zombie fields, low-use fields, which are referenced in automations
- **Per-list audit** — size, last campaign sent, opt-in source
- **List overlap matrix** — which lists are subsets of others (probably duplicate-ish)
- **Segment audit** — empty segments, segments referencing deleted assets
- **Form audit** — quality of each form by downstream contact engagement

### Compliance & ops
- **Unsubscribe / opt-in audit** — every campaign has a working unsub link, every form mentions opt-in
- **Suppression export** — all unsubs + bounces with timestamps (for compliance audits, ESP migration)
- **GDPR Article 15 SAR** — full export of everything AC has on one contact
- **Webhook audit** — inventory + reachability probe of every configured webhook
- **Account snapshot** — full taxonomy export to JSON, versioned weekly via cron
- **Schema diff** — what changed between two snapshots (added/removed/renamed)

### Strategic advice (no API calls — domain knowledge)
- "Should this be a tag, custom field, or list?"
- "Why is my open rate dropping?"
- "What's a good RFM scoring model for a B2B account?"
- Welcome series / re-engagement / drip campaign **specs** that you build in the AC UI

## What it can't do

Be honest, AC's v3 API has real limits:

- ❌ **Cannot send campaigns or create automations** — those endpoints don't exist. The skill produces *specs* you implement in the AC UI.
- ❌ **Cannot read spam complaint data** — uses bounce + unsub spikes as proxies.
- ⚠️ **Per-event open data is not exposed on every plan.** When `/messageActivities` returns 404, engagement reports fall back to `/linkData` (clicks only). You'll see clicks-by-domain but zero opens-by-domain. This is an AC API limitation, not a bug.
- ⚠️ **Deal time-in-stage is not exposed** — pipeline reports show current state and 90-day-new only.
- 🚫 **Deals-dependent reports** (`pipeline_audit`, `mql_to_sql_handoff`, `win_loss_report`) require the Deals feature on your AC plan; they exit cleanly with a "Deals not enabled" message otherwise.

## Quick start (5 minutes)

```bash
# 1. Install the skill
openclaw skills install ji282h7/activecampaign-claw

# 2. Get your AC API URL + token: https://help.activecampaign.com/hc/en-us/articles/207317590
#    Then set them
openclaw config set env.vars.AC_API_URL "https://YOURACCOUNT.api-us1.com"
openclaw config set env.vars.AC_API_TOKEN "YOUR-TOKEN"
openclaw gateway restart

# 3. Calibrate (one-time, ~1 minute)
python3 ~/.openclaw/skills/activecampaign/scripts/calibrate.py

# 4. Try it
#    In a Claude session, ask: "Run a list health audit on my AC account"
```

Full instructions: [INSTALL.md](INSTALL.md)

## How it's organized

```
activecampaign/
├── SKILL.md                      ← agent's spec (decision tree, triggers, rules)
├── README.md                     ← you are here
├── INSTALL.md                    ← step-by-step setup
├── CHANGELOG.md
├── scripts/                      ← 50 executable scripts (run directly or via agent)
│   ├── calibrate.py              ← one-time account scan
│   ├── audit_list_health.py
│   ├── find_hot_leads.py
│   ├── find_slipping_deals.py
│   ├── campaign_postmortem.py
│   ├── tag_audit.py
│   ├── automation_funnel.py
│   ├── … 43 more …
│   └── _ac_client.py             ← shared HTTP client with rate-limit handling
├── recipes/                      ← agent-driven workflows
│   ├── daily-digest.md
│   ├── deal-hygiene.md
│   ├── list-health-audit.md
│   └── welcome-series.md
├── frameworks/                   ← embedded marketing knowledge
│   ├── email-best-practices.md
│   └── segmentation-theory.md
├── references/                   ← AC API endpoint docs
│   ├── contacts.md
│   ├── deals.md
│   └── custom-fields.md
└── tests/
```

## Example agent interaction

> **You:** Run a list health audit on my AC account.

> **Agent:** Running `audit_list_health.py`… Your account has 12,438 active contacts across 13 lists. Found:
> - 47 role addresses (info@, support@) on the main list — recommend suppress
> - 8 lists overlap >95% with `Master Contact List` — consolidation candidates
> - Bounce rate trend is +0.3pp over the last 30 days vs. baseline — investigating which campaign…
> - 3 tags applied to >50% of contacts may have lost discriminating power
>
> Want me to draft the suppression workflow, or dig into the bounce trend first?

## Where data lives

All data stays local on your machine:
- `~/.activecampaign-skill/state.json` — your calibrated taxonomy + baselines
- `~/.activecampaign-skill/history.jsonl` — record of recipes/scripts you've run
- `~/.activecampaign-skill/insights.md` — accumulated findings the agent surfaces back

Nothing is sent anywhere except your own AC account via your own token. No third-party gateways, no telemetry.

## Privacy & security

- Use a dedicated integration user when generating your token (tokens are scoped to the user that created them).
- Token storage: `~/.openclaw/openclaw.json` (file mode 0600). Be aware it's in plaintext on disk.
- Sanitization: API response data (contact names, deal titles, tag names) is sanitized before rendering to prevent markdown injection.
- The skill includes destructive operation guards: every `POST`/`PUT`/`DELETE` shows you the payload and waits for explicit confirmation before executing.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Issues and PRs welcome at https://github.com/ji282h7/activecampaign-claw

## Credits

Built on top of [OpenClaw](https://openclaw.ai) skill framework. ActiveCampaign v3 API documentation: https://developers.activecampaign.com/reference
