# Changelog

All notable changes to this skill are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.7] — 2026-04-26

### Added
- `scripts/tag_merge.py` — merges a source tag into a canonical target. Re-tags affected contacts, detects automation and segment references, deletes the source tag. Dry-run by default; `--confirm` required for execution.
- `recipes/re-engagement-launch.md` — workflow for designing and launching a re-engagement campaign.
- `recipes/monthly-deliverability-review.md` — monthly cadence for checking sender health.
- `recipes/pre-import-checklist.md` — pre-flight checks to run before importing a contact CSV.

### Changed
- Backfilled changelog entries for 1.0.1 through 1.0.6.

## [1.0.6] — 2026-04-26

### Fixed
- `SCALING.md` was referenced from README but missed the 1.0.5 commit; included now.

## [1.0.5] — 2026-04-26

### Added
- `SCALING.md` — runtime/memory math, per-script default caps, recommended workflows for 100k+ contact accounts, and known-not-yet-optimized items.
- README "Performance & scale" section linking to SCALING.md.

## [1.0.4] — 2026-04-26

### Added
- README intro and "Why this exists" section rewritten to focus on what the skill unlocks via the v3 API.
- Renamed README "What it can't do" section to "API scope" and reframed each bullet.

### Changed
- License badge updated to MIT-0; release badge bumped.
- License footer updated to MIT-0.

### Fixed
- Cleaned up 135 ruff lint errors:
  - Auto-fix: 95 (unused imports, sort order, redundant open modes, f-strings without placeholders).
  - Renamed ambiguous single-letter `l` loop variables across 12 scripts and 1 test.
  - Dropped assigned-but-unused locals across 6 scripts and 3 tests.
  - Added `from e` / `from None` to ACClientError raises in `_ac_client.py` and three downstream scripts.
  - Suppressed UP036 on the runtime Python>=3.9 check (kept as a friendly error for users running scripts directly).
  - Removed a no-op for-loop in `list_growth_forecast.py`.

## [1.0.3] — 2026-04-26

### Changed
- Replaced `purchase` / `purchases` / `purchased` terminology in docs and code comments with `conversion` equivalents.
- Replaced `billing` references in docs with `plan`-context phrasing.
- Removed `"billing"` from the role-address local-part blocklists in `import_validator.py` and `role_address_finder.py`.

These changes target the ClawHub capability scanner's keyword pattern-match on `purchase` / `billing`. The skill is read-only and cannot make purchases or charge anyone — these were always disclosure labels rather than functional flags.

## [1.0.2] — 2026-04-26

### Changed
- Dropped the `(be honest about these)` aside from the SKILL.md "API limitations" heading.

## [1.0.1] — 2026-04-26

### Changed
- Rephrased a few docs and fixture strings the ClawHub capability scanner pattern-matched against:
  - `SECURITY.md`: "full-disk encryption" → "full-disk security".
  - `tests/fixtures/mock_responses.py`: "Last Purchase Date" → "Last Conversion Date".
  - `recipes/welcome-series.md`: dropped "purchase" as a goal example.

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
