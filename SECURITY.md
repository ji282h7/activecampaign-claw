# Security policy

## Reporting a vulnerability

If you discover a security issue in this skill — including credential handling,
markdown injection from API data, command-injection vectors in scripts, or
unsafe defaults — please report it privately rather than opening a public issue.

**Preferred channel:** Open a [GitHub Security Advisory](https://github.com/ji282h7/activecampaign-claw/security/advisories/new)
on the repository. Advisories are private until you and a maintainer agree to disclose.

If you cannot use Security Advisories, contact the author via the email listed
on their GitHub profile.

Please include:

- A clear description of the issue and its impact
- Reproduction steps (a minimal script or commit reference is ideal)
- Your AC plan tier and the affected endpoint(s) if relevant
- Whether the issue is exploitable in the OpenClaw agent harness, the standalone
  CLI, or both

## Response expectations

- **Acknowledgement** within 5 business days
- **Triage + initial assessment** within 14 days
- **Fix or mitigation** for critical issues within 30 days, lower-severity within 90
- **Credit in the changelog** unless you ask to remain anonymous

## Scope

In scope:

- All Python scripts in `scripts/`
- `_ac_client.py` and its handling of `AC_API_URL` / `AC_API_TOKEN`
- Markdown rendering of API response data (`sanitize()` in `_ac_client.py`)
- The state file at `~/.activecampaign-skill/state.json` and the history JSONL
- Default file permissions and storage of credentials

Out of scope:

- Vulnerabilities in ActiveCampaign's own API or infrastructure (report to AC)
- OpenClaw gateway / harness vulnerabilities (report to OpenClaw)
- Issues that require already having privileged access to the user's machine
- Social engineering of the user

## Hardening notes for users

- Use a dedicated AC integration user with the minimum permissions needed.
- AC tokens are scoped to the user that created them — rotate the token
  whenever the integration user changes.
- Tokens are stored at `~/.openclaw/openclaw.json` (mode 0600). Anyone with
  shell access to that user account can read them. Use full-disk encryption.
- The skill never sends data to third-party services — only to your own AC
  account via your own token.

## Credit / coordinated disclosure

We follow standard coordinated disclosure. If a fix lands in a public release,
we'll mention the reporter in the CHANGELOG entry unless they ask otherwise.
