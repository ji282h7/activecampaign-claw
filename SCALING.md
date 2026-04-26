# Scaling notes

This doc covers performance characteristics and recommendations for running the skill against large ActiveCampaign accounts (100k+ contacts).

## What scales freely with account size

These reports are bounded by taxonomy or campaign count, not contact count. Run them on any account regardless of size:

- **Taxonomy reports**: `tag_audit`, `custom_field_audit`, `list_audit`, `segment_audit`, `automation_audit`, `automation_dependency_map`, `broken_automation_detector`, `form_audit`, `webhook_audit`, `pipeline_audit`
- **Campaign analysis**: `campaign_postmortem`, `subject_line_report`, `from_name_report`, `content_length_report`, `send_time_optimizer`, `send_frequency_report`, `monthly_performance`, `baseline_drift`, `campaign_velocity`, `link_performance`, `bounce_breakdown`
- **Single-contact operations**: `data_subject_export`
- **Account snapshots**: `export_account`, `schema_diff`, `snapshot`
- **Headline numbers in `audit_list_health`** (uses `meta.total` rather than row scans)

Calibration is taxonomy-only and finishes in ~1 minute even on 1M-contact accounts.

## Contact-scanning reports and their default caps

| Script | Default cap | How to raise |
|---|---|---|
| `dedupe_contacts` | 10k | `--max-contacts N` |
| `role_address_finder` | 10k | `--max-contacts N` |
| `free_vs_corporate_report` | 10k | `--max-contacts N` |
| `contact_completeness_report` | 5k | `--max-contacts N` |
| `stale_contact_report` | 20k | edit script |
| `find_hot_leads` | 300 (post-filter) | API-side score filter; raise the constant if needed |

`audit_list_health`'s sampling pass accepts a configurable sample size for distribution math.

## Rate limits and runtime

The client throttles to **5 requests/sec** (`MAX_REQUESTS_PER_SEC` in `_ac_client.py`) — matches AC's default API limit on most plans. Pagination uses 100 records per page with a 250ms inter-page sleep, so the practical ceiling is ~4 pages/sec.

| Account size | Full scan runtime | API calls |
|---|---|---|
| 10k contacts | ~25 sec | 100 pages |
| 100k contacts | ~7 min | 1,000 pages |
| 500k contacts | ~35 min | 5,000 pages |
| 1M contacts | ~70 min | 10,000 pages |

These are best-case. AC may throttle harder on lower plans, and `offset` performance can degrade past ~100k records on some endpoints.

## Memory profile

The `paginate()` helper accumulates results into a Python list before returning. Approximate memory:

| Contact count | Approx. RAM |
|---|---|
| 10k | 15–20 MB |
| 100k | 150–200 MB |
| 1M | 1.5–2 GB |

If you're constrained on memory, scope to a list or segment first.

## Recommended workflows for large accounts

**1. Run taxonomy-bound reports freely.** Tag audits, automation hygiene, segment audits, campaign analysis — all unaffected by contact count.

**2. Scope contact-scanning reports to cohorts.** Instead of running `dedupe_contacts` against the full account, run it on a single list. Most marketing questions are naturally cohort-scoped.

**3. For one-shot full scans, plan for runtime.** GDPR-style exports or full migrations: bump `--max-contacts`, run overnight, expect ~1 hour per 150k contacts.

**4. Use snapshots for change detection.** `export_account.py` + `schema_diff.py` are taxonomy-only and weekly-cron-friendly even for huge accounts.

## What's not optimized yet

- **Streaming pagination**: `paginate()` accumulates the full list in memory. A streaming/iterator pattern would handle 1M+ accounts more cleanly.
- **Parallel cohort scans**: pagination is serial per script. Could be parallelized with rate-aware backoff.
- **Offset performance**: AC's `offset` parameter slows past ~100k records on some endpoints. Cursor-based pagination (`orders[id]=ASC&id_greater=N`) is supported on some endpoints — see `references/contacts.md`.

If your account is in the 500k+ range and any of these matter for your workflow, please file an issue at https://github.com/ji282h7/activecampaign-claw/issues.
