# Changelog

All notable changes to this skill are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.2] — 2026-05-05

### Changed
- Documentation polish.

## [1.1.1] — 2026-05-05

### Changed
- Documentation polish.

## [1.1.0] — 2026-05-05

### Added
- `scripts/tasks_audit.py` — overdue tasks, completion rate per user, unassigned tasks. Uses `/dealTasks` with `filters[reltype]=Deal|Subscriber` (covers contact tasks too — there is no separate `/contactTasks` endpoint in v3). Exits cleanly on 403 for non-Plus accounts.
- `scripts/notes_analysis.py` — content analysis across `/notes`: action-item extraction, per-user note count + median length, stale-note flag for deals, top recurring vocabulary.
- `scripts/sales_rep_performance.py` — per-rep scoreboard combining `/users`, `/deals`, `/dealTasks`, `/notes`: open / won / lost deals, win rate, avg won value, open + overdue tasks, notes count, composite activity score. Falls back to notes-only view on Lite plans (no /deals).
- `scripts/template_audit.py` — campaign template audit using `/templates` cross-referenced with `/campaigns`: unused, stale, per-template avg open rate, length-distribution outliers.
- `scripts/saved_responses_audit.py` — sales-reply library audit using `/savedResponses` (Plus+): stale entries, length outliers, near-duplicate detection via jaccard on tokenized HTML-stripped bodies.
- `scripts/accounts_audit.py` — B2B Accounts audit (Plus+) using `/accounts` (with `count_deals=true`) + `/accountContacts`: orphaned accounts, no-pipeline accounts, top accounts by deals/contacts, per-owner rollup. Exits cleanly on 403 if the Accounts feature isn't enabled.
- `scripts/forms_lead_quality.py` — per-form lead quality reconstructed from each form's `subscribelist` membership + recent engagement events. Caveat documented inline: AC v3 has no `/formSubmissions` endpoint, so this is a list-quality reading rather than a strict per-submission reading when a list has multiple opt-in sources.
- 36 new unit tests + 28 smoke tests across the 7 new scripts. Fixtures match the JSON shapes documented in the AC v3 reference for `/dealTasks`, `/notes`, `/users`, `/templates`, `/savedResponses`, `/accounts`, `/accountContacts`, and `/forms`.

### Changed
- README "What it can do" — added the Sales / CRM section and a Marketing-content hygiene section.
- SKILL.md — added a "Sales / CRM scripts" decision-tree row group.

## [1.0.20] — 2026-05-05

### Changed
- Documentation polish.

## [1.0.19] — 2026-05-05

### Changed
- Restructured top of SKILL.md so the marketplace listing leads with user-facing content: tagline → "What it does" (capabilities by category) → "Examples" → "What makes this skill different" → "Setup". The agent-routing sections ("Use this skill when..." / "Do NOT use this skill when...") moved down into a single "When to invoke this skill" section right before "Critical operating rules", where they belong as agent spec.

## [1.0.18] — 2026-05-05

### Changed
- Removed the "READ FIRST — Response format rules" preamble from the top of SKILL.md. Its content (R1/R2/R3) was already restated by rules 12 and 13 under "Critical operating rules" further down. The preamble was dominating the clawhub.ai listing page; deleting the duplicate lets the listing lead with the human-facing intro.
- Removed the coverage badge from README.md.

## [1.0.17] — 2026-04-26

### Added
- `_ac_client.emit_files(*paths)` — prints a structured trailer line `__SKILL_FILES__:[...]` (JSON array of absolute paths) so the agent has a deterministic landmark to grep for instead of hunting through prose. 3 new tests cover trailer format, multi-path emission, and JSON validity.
- New "READ FIRST — Response format rules" preamble at the top of SKILL.md (rules R1–R3). Restates the most-violated rules above the decision tree so they get attention earlier in the prompt. Lists every observed forbidden trailing-label variant explicitly: `Files:`, `Output:`, `Current snapshot:`, `Latest pointer:`, `Saved to:`, `Backup record:`, `Results:`, `I saved the [thing] here:`.

### Changed
- `snapshot.py`, `suppression_export.py`, `export_account.py`, `data_subject_export.py`, `audit_list_health.py`, `find_hot_leads.py` now call `emit_files()` after writing their output files. Existing `Wrote /path` lines are preserved for backwards-compat.
- Rule #12 updated to reference the structured trailer alongside the human-readable `Wrote ` lines.

## [1.0.16] — 2026-04-26

### Changed
- Strengthened SKILL.md rule #12 with two new hard rules:
  - **Pass through `Wrote /path` lines verbatim.** Every script that writes a file prints these to stdout; the agent must scan for `Wrote `, `Saved to `, `Output:` substrings and reproduce every match in the response.
  - **Forbidden trailing labels enumerated explicitly.** `Files:`, `Output:`, `Current snapshot:`, `Latest pointer:`, `Saved to:`, `Results:`, etc. — any of these followed by no content marks the response as broken.
- Added a real "snapshot trail-off" example pulled from observed agent output, with both bad and good versions including the actual `~/.activecampaign-skill/snapshots/...json`, `manifest.jsonl`, and LaunchAgent paths.
- Codified required response structure for file-writing scripts: 1-line summary → enumerated paths → 2-3 line content summary → next-step offer.

## [1.0.15] — 2026-04-26

### Changed
- Generalized SKILL.md rule #12 to catch any trailing-label/colon pattern, not just `"saved here:"`. The previous wording missed the `"Files:"` variant observed in suppression_export. Rule now: any line introducing output (`Files:`, `Output:`, `Results:`, `Saved to:`, etc.) must be followed by the actual content in the same response. Includes "list every file path" requirement for multi-file exports and an explicit "no files written — output printed inline above" fallback for stdout-only scripts.

## [1.0.14] — 2026-04-26

### Added
- SKILL.md operating rule #13: always prefer named scripts in `scripts/` over inline Python heredocs. Reasons: scripts handle pagination, rate limits, retries, sanitization, history logging, and consistent markdown — ad-hoc inline Python skips all of that and dumps raw heredoc text to the harness progress line.
- SKILL.md operating rule #14: narrate before exec. Before running anything, say one human sentence describing what you're about to do, so the user has something readable to anchor on while the harness's technical progress line ("exec → python3 …") fires.

## [1.0.13] — 2026-04-26

### Added
- New SKILL.md operating rule (#12): when the agent saves a file, the response must include the absolute path AND a content summary on the same line. Fixes responses that ended mid-sentence with "I saved the audit here:" and no path. Includes good/bad examples.

## [1.0.12] — 2026-04-26

### Added
- 26 new `render_markdown()` tests across previously-untested scripts: `automation_audit`, `automation_funnel`, `automation_overlap`, `baseline_drift`, `broken_automation_detector`, `campaign_postmortem`, `campaign_velocity`, `contact_completeness_report`, `content_length_report`, `domain_engagement_report`, `engagement_decay`, `form_audit`, `from_name_report`, `link_performance`, `list_audit`, `list_growth_forecast`, `list_overlap`, `monthly_performance`, `mql_to_sql_handoff`, `new_subscriber_quality`, `send_frequency_report`, `stale_contact_report`, `stalled_automations`, `subject_line_report`, `unsubscribe_audit`, `win_loss_report`.
- 9 new `main()` integration tests in `tests/test_main_integration.py` covering the most-used scripts: `import_validator`, `audit_list_health`, `find_hot_leads`, `dedupe_contacts`, `tag_merge`. Each patches `sys.argv`, mocks `ACClient` where needed, runs `main()`, and verifies output. Also covers error paths (missing CSV, unknown source tag).

### Changed
- Coverage: 59% → 66%. Test count: 455 → 490.

## [1.0.11] — 2026-04-26

### Changed
- `dedupe_contacts.py` now uses `stream()` with slim records (id + email only) keyed by email/phone/name. Singletons sit in lookup maps until promoted to the duplicate output; full records never accumulate. Peak memory drops from ~1.5–2 GB on 1M-contact accounts to ~150 MB. `find_duplicates()` accepts any iterable; return dict now includes a `scanned` count.
- SCALING.md: documented why `audit_list_health` (already sample-bounded) and `contact_completeness_report` (streaming would force a 600× slowdown via per-contact field-value lookups) are intentionally still buffered.

### Added
- 3 new tests for `dedupe_contacts`: accepts a generator input, drops singletons from the output, and stores slim records only.

## [1.0.10] — 2026-04-26

### Added
- `ACClient.stream(path, key, params, limit_per_page, max_items)` — generator that yields records one at a time. `paginate()` is now a thin wrapper around it (`return list(self.stream(...))`); behavior unchanged for existing callers.

### Changed
- `role_address_finder.py`, `free_vs_corporate_report.py`, `stale_contact_report.py` now use `stream()` for the contact scan. Memory peak drops from O(N) to <1 MB regardless of contact count. `stale_contact_report.analyze()` also bounds its output samples to 50 records (counts come from explicit counters).
- SCALING.md updated with the new memory profile and remaining adoption gaps.

## [1.0.9] — 2026-04-26

### Changed
- Replaced the single bare-bones "Example agent interaction" in README with two concrete examples that show range: hot-leads ranking (analysis) and tag merge (maintenance with destructive-op confirm flow).

## [1.0.8] — 2026-04-26

### Changed
- Excluded `.github/` from the published bundle (workflow files are only used by the GitHub repo).

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
- Wording cleanup across docs and examples; minor adjustment to the role-address local-part blocklist.

## [1.0.2] — 2026-04-26

### Changed
- Dropped the `(be honest about these)` aside from the SKILL.md "API limitations" heading.

## [1.0.1] — 2026-04-26

### Changed
- Wording polish in `SECURITY.md`, `tests/fixtures/mock_responses.py`, and `recipes/welcome-series.md`.

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
