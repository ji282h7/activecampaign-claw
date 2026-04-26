# Changelog

All notable changes to this skill are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-04-26

### Added — initial public release

**Performance analysis (24 scripts):** `campaign_postmortem`, `campaign_compare`, `link_performance`, `bounce_breakdown`, `monthly_performance`, `baseline_drift`, `campaign_velocity`, `subject_line_report`, `content_length_report`, `from_name_report`, `send_time_optimizer`, `send_frequency_report`, `domain_engagement_report`, `engagement_decay`, `stale_contact_report`, `new_subscriber_quality`, `segment_performance`, `automation_audit`, `automation_funnel`, `automation_overlap`, `stalled_automations`, `form_audit`, `mql_to_sql_handoff`, `win_loss_report`.

**Operational / hygiene (16 scripts):** `tag_audit`, `custom_field_audit`, `list_audit`, `list_overlap`, `segment_audit`, `pipeline_audit`, `automation_dependency_map`, `broken_automation_detector`, `dedupe_contacts`, `contact_completeness_report`, `role_address_finder`, `free_vs_corporate_report`, `import_validator`, `webhook_audit`, `unsubscribe_audit`, `suppression_export`.

**Compliance / migration (4 scripts):** `data_subject_export`, `export_account`, `snapshot`, `schema_diff`.

**Forecasting (2 scripts):** `send_simulator`, `list_growth_forecast`.

**Pre-existing (carried forward):** `calibrate`, `audit_list_health`, `find_hot_leads`, `find_slipping_deals`.

**Workflow recipes:** `recipes/daily-digest.md`, `recipes/deal-hygiene.md`, `recipes/list-health-audit.md`, `recipes/welcome-series.md`.

**Frameworks:** `frameworks/email-best-practices.md`, `frameworks/segmentation-theory.md`.

**API references:** `references/contacts.md`, `references/deals.md`, `references/custom-fields.md`.

### Notes on AC API limits

- `/messageActivities` is not exposed on every plan. Engagement scripts fall back to `/linkData` (clicks-only) automatically.
- Deals-dependent scripts (`pipeline_audit`, `mql_to_sql_handoff`, `win_loss_report`) require the Deals feature.
- The skill cannot send campaigns or create automations — those AC v3 endpoints don't exist; the skill produces specs.
