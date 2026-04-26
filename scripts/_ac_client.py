#!/usr/bin/env python3
"""
Shared ActiveCampaign v3 API client and utilities.

All scripts in this skill import from here. Provides:
  - ACClient: HTTP client with rate-limit handling and pagination
  - State file helpers: load_state(), state_age_days(), ensure_state()
  - History logging: log_outcome()
  - Report output: write_report()
"""

from __future__ import annotations

import json
import os
import random
import re
import sys
import tempfile
import time

if sys.version_info < (3, 9):  # noqa: UP036 - friendly error for users running scripts directly
    sys.stderr.write(
        f"ERROR: Python 3.9 or newer required (you have {sys.version_info.major}.{sys.version_info.minor}).\n"
    )
    sys.exit(1)
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

STATE_DIR = Path.home() / ".activecampaign-skill"
STATE_FILE = STATE_DIR / "state.json"
HISTORY_FILE = STATE_DIR / "history.jsonl"
INSIGHTS_FILE = STATE_DIR / "insights.md"


class ACClientError(Exception):
    """Raised on non-retryable API errors."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


class ACClient:
    """ActiveCampaign v3 API client with rate-limit handling, exponential
    backoff, network error resilience, and proactive throttling."""

    MAX_REQUESTS_PER_SEC = 5
    MIN_REQUEST_INTERVAL = 1.0 / MAX_REQUESTS_PER_SEC  # 0.2s between requests

    def __init__(self, base_url: str | None = None, token: str | None = None):
        url = base_url or os.environ.get("AC_API_URL", "")
        tok = token or os.environ.get("AC_API_TOKEN", "")
        if not url or not tok:
            sys.stderr.write(
                "ERROR: AC_API_URL and AC_API_TOKEN must be set "
                "(as env vars or constructor args).\n"
            )
            sys.exit(1)
        if not url.startswith("https://"):
            sys.stderr.write(
                "ERROR: AC_API_URL must use HTTPS. "
                "Sending API tokens over plain HTTP exposes credentials.\n"
            )
            sys.exit(1)
        self.base = url.rstrip("/") + "/api/3"
        self.token = tok
        self._request_count = 0
        self._last_request_time = 0.0

    def _throttle(self) -> None:
        """Proactive rate limiter — ensures we stay under 5 req/sec."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.monotonic()

    @staticmethod
    def _backoff_delay(attempt: int, base: float = 1.0, cap: float = 60.0) -> float:
        """Exponential backoff with full jitter: random(0, min(cap, base * 2^attempt))."""
        delay = min(cap, base * (2 ** attempt))
        return random.uniform(0, delay)

    def _request(self, method: str, path: str, data: bytes | None = None,
                 params: dict | None = None, max_retries: int = 5) -> dict:
        url = f"{self.base}/{path}"
        if params:
            url += "?" + urlencode(params)
        headers = {
            "Api-Token": self.token,
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(url, method=method, headers=headers, data=data)

        retryable_http_codes = {429, 500, 502, 503, 504}
        last_error: Exception | None = None

        for attempt in range(max_retries):
            self._throttle()
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    self._request_count += 1
                    body = resp.read()
                    if not body:
                        return {}
                    return json.loads(body)

            except urllib.error.HTTPError as e:
                last_error = e
                if e.code == 429:
                    retry_after = int(e.headers.get("Retry-After", "0"))
                    delay = max(retry_after, self._backoff_delay(attempt))
                    sys.stderr.write(
                        f"  ⚠ Rate limited on {path}. "
                        f"Retry {attempt + 1}/{max_retries} in {delay:.1f}s\n"
                    )
                    time.sleep(delay)
                    continue
                if e.code in retryable_http_codes:
                    delay = self._backoff_delay(attempt)
                    sys.stderr.write(
                        f"  ⚠ Server error {e.code} on {path}. "
                        f"Retry {attempt + 1}/{max_retries} in {delay:.1f}s\n"
                    )
                    time.sleep(delay)
                    continue
                if e.code == 422:
                    body = e.read().decode("utf-8", errors="replace")
                    raise ACClientError(422, body) from e
                if e.code in (401, 403):
                    raise ACClientError(
                        e.code,
                        "Authentication failed. Check AC_API_URL and AC_API_TOKEN.",
                    ) from e
                if e.code == 404:
                    raise ACClientError(404, f"Resource not found: {path}") from e
                raise ACClientError(e.code, str(e)) from e

            except urllib.error.URLError as e:
                last_error = e
                delay = self._backoff_delay(attempt, base=2.0)
                sys.stderr.write(
                    f"  ⚠ Network error on {path}: {e.reason}. "
                    f"Retry {attempt + 1}/{max_retries} in {delay:.1f}s\n"
                )
                time.sleep(delay)
                continue

            except (TimeoutError, OSError) as e:
                last_error = e
                delay = self._backoff_delay(attempt, base=2.0)
                sys.stderr.write(
                    f"  ⚠ Timeout/connection error on {path}. "
                    f"Retry {attempt + 1}/{max_retries} in {delay:.1f}s\n"
                )
                time.sleep(delay)
                continue

        if isinstance(last_error, urllib.error.HTTPError):
            raise ACClientError(
                last_error.code,
                f"Exceeded {max_retries} retries on {path} (last: HTTP {last_error.code})",
            )
        raise ACClientError(
            0,
            f"Exceeded {max_retries} retries on {path} "
            f"(last error: {last_error})",
        )

    def get(self, path: str, params: dict | None = None) -> dict:
        return self._request("GET", path, params=params)

    def post(self, path: str, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        return self._request("POST", path, data=data)

    def put(self, path: str, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        return self._request("PUT", path, data=data)

    def delete(self, path: str) -> dict:
        return self._request("DELETE", path)

    def stream(self, path: str, key: str, params: dict | None = None,
               limit_per_page: int = 100, max_items: int | None = None):
        """Yield records from a paginated endpoint one at a time.

        Memory-bounded alternative to paginate(). Use when callers can
        aggregate as they read (filters, tallies, single-pass scans).

        max_items=None means "no cap — keep going until the API returns
        an empty page or a short page." Pass an int to cap.
        """
        params = dict(params or {})
        params["limit"] = limit_per_page
        offset = 0
        yielded = 0
        while max_items is None or yielded < max_items:
            params["offset"] = offset
            resp = self.get(path, params)
            chunk = resp.get(key, [])
            if not chunk:
                break
            for record in chunk:
                yield record
                yielded += 1
                if max_items is not None and yielded >= max_items:
                    return
            if len(chunk) < limit_per_page:
                break
            offset += limit_per_page
            time.sleep(0.25)

    def paginate(self, path: str, key: str, params: dict | None = None,
                 limit_per_page: int = 100, max_items: int = 5000) -> list:
        return list(self.stream(path, key, params, limit_per_page, max_items))

    def fetch_engagement_events(self, max_items: int = 30000, quiet: bool = False) -> list:
        """Return a normalized list of engagement events.

        Tries /messageActivities first (full open + click event log on plans
        that expose it). On 404 falls back to /linkData (clicks only) so
        click-driven analysis still works on accounts without messageActivities.

        When the fallback is used, a one-line banner is printed to stderr so
        downstream report consumers know that "0 opens" reflects the API plan,
        not their account. Pass quiet=True to suppress.

        Each event has: {event, contact, tstamp, campaign?, link?, email?}
        """
        try:
            raw = self.paginate("messageActivities", "messageActivities", max_items=max_items)
            return [
                {
                    "event": (e.get("event") or "").lower(),
                    "contact": str(e.get("contact")) if e.get("contact") else None,
                    "tstamp": e.get("tstamp"),
                    "campaign": str(e.get("campaign")) if e.get("campaign") else None,
                    "email": e.get("email"),
                }
                for e in raw
            ]
        except ACClientError as e:
            if e.status_code != 404:
                raise
        # fallback: linkData (click events only)
        if not quiet:
            sys.stderr.write(
                "NOTE: AC plan doesn't expose /messageActivities — "
                "falling back to /linkData (click events only, no open events).\n"
            )
        raw = self.paginate("linkData", "linkData", max_items=max_items)
        return [
            {
                "event": "click",
                "contact": str(d.get("contact")) if d.get("contact") else None,
                "tstamp": d.get("tstamp"),
                "campaign": str(d.get("campaign")) if d.get("campaign") else None,
                "link": str(d.get("link")) if d.get("link") else None,
                "email": d.get("email"),
            }
            for d in raw
        ]


_UNSAFE_PATTERN = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"
    r"|!\[[^\]]*\]\((?:[^()]*|\([^()]*\))*\)"
    r"|\[[^\]]*\]\(javascript:(?:[^()]*|\([^()]*\))*\)"
)


def sanitize(value: str, max_len: int = 500) -> str:
    """Strip control characters and markdown injection patterns from API data."""
    cleaned = _UNSAFE_PATTERN.sub("", value)
    return cleaned[:max_len]


def _ensure_state_dir() -> None:
    """Create the state directory with restricted permissions."""
    if not STATE_DIR.exists():
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        os.chmod(STATE_DIR, 0o700)


def load_state() -> dict | None:
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def state_age_days() -> float | None:
    state = load_state()
    if not state or "last_calibrated" not in state:
        return None
    try:
        cal = datetime.fromisoformat(state["last_calibrated"])
        if cal.tzinfo is None:
            cal = cal.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - cal).total_seconds() / 86400
    except (ValueError, TypeError):
        return None


def ensure_state(max_age_days: int = 30) -> dict:
    state = load_state()
    if state is None:
        sys.stderr.write(
            "ERROR: State file not found.\n"
            "\n"
            "Set AC_API_URL and AC_API_TOKEN, then run calibration:\n"
            "  python3 scripts/calibrate.py --validate   # check creds\n"
            "  python3 scripts/calibrate.py              # build state.json\n"
            "\n"
            "See INSTALL.md for credential setup options.\n"
        )
        sys.exit(1)
    age = state_age_days()
    if age is not None and age > max_age_days:
        sys.stderr.write(
            f"WARNING: State file is {age:.0f} days old "
            f"(calibrated {age:.0f} days ago). "
            "Results may not reflect recent account changes.\n"
            "  Recalibrate: python3 scripts/calibrate.py\n"
        )
    return state


def save_state(state: dict) -> None:
    _ensure_state_dir()
    fd, tmp_path = tempfile.mkstemp(dir=STATE_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, indent=2)
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, STATE_FILE)
    except BaseException:
        os.unlink(tmp_path)
        raise


def log_outcome(action: str, **kwargs) -> None:
    _ensure_state_dir()
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        **kwargs,
    }
    fd = os.open(HISTORY_FILE, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a") as f:
        f.write(json.dumps(entry) + "\n")


def write_report(title: str, content: str, to_file: Path | None = None) -> str:
    report = f"# {title}\nGenerated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n{content}"
    if to_file:
        to_file.parent.mkdir(parents=True, exist_ok=True)
        to_file.write_text(report)
    return report


def write_insight(insight: str, category: str = "general") -> None:
    """Append a significant finding to insights.md."""
    _ensure_state_dir()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = f"\n### [{category.upper()}] {ts}\n\n{insight}\n"
    if not INSIGHTS_FILE.exists():
        header = (
            "# ActiveCampaign Insights\n\n"
            "Persistent findings from automated analyses. "
            "This file survives conversation compaction.\n"
        )
        fd = os.open(INSIGHTS_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(header)
    fd = os.open(INSIGHTS_FILE, os.O_WRONLY | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a") as f:
        f.write(entry)


def load_insights() -> str | None:
    if not INSIGHTS_FILE.exists():
        return None
    try:
        return INSIGHTS_FILE.read_text()
    except OSError:
        return None


def load_history(recipe: str | None = None, limit: int = 50) -> list[dict]:
    """Read history.jsonl, optionally filtered by recipe. Returns newest first."""
    if not HISTORY_FILE.exists():
        return []
    entries = []
    try:
        with open(HISTORY_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if recipe is None or entry.get("recipe") == recipe:
                        entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    entries.reverse()
    return entries[:limit]


def compare_to_previous(recipe: str, current_metrics: dict[str, float],
                        metric_keys: list[str]) -> str | None:
    """Compare current run metrics to previous runs. Returns markdown or None."""
    history = load_history(recipe=recipe, limit=10)
    if not history:
        return None
    prev = history[0]
    prev_ts = prev.get("ts", "unknown")
    lines = ["## Trends\n"]
    lines.append(f"Compared to previous run ({prev_ts[:10]}):\n")
    lines.append("| Metric | Previous | Current | Change |")
    lines.append("|---|---|---|---|")
    has_data = False
    for key in metric_keys:
        curr_val = current_metrics.get(key)
        prev_val = prev.get(key)
        if curr_val is None or prev_val is None:
            continue
        try:
            curr_f = float(curr_val)
            prev_f = float(prev_val)
        except (ValueError, TypeError):
            continue
        has_data = True
        diff = curr_f - prev_f
        arrow = "+" if diff > 0 else ""
        if prev_f != 0:
            pct = (diff / abs(prev_f)) * 100
            lines.append(
                f"| {key.replace('_', ' ').title()} | {prev_f:,.0f} | "
                f"{curr_f:,.0f} | {arrow}{diff:,.0f} ({arrow}{pct:.1f}%) |"
            )
        else:
            lines.append(
                f"| {key.replace('_', ' ').title()} | {prev_f:,.0f} | "
                f"{curr_f:,.0f} | {diff:+,.0f} |"
            )
    if not has_data:
        return None
    if len(history) >= 3:
        lines.append("\n**Multi-run trend** (last 3 runs):\n")
        for key in metric_keys:
            vals = []
            for h in history[:3]:
                v = h.get(key)
                if v is not None:
                    try:
                        vals.append(float(v))
                    except (ValueError, TypeError):
                        pass
            if len(vals) >= 3:
                vals.reverse()
                trend = "rising" if vals[-1] > vals[0] else "falling" if vals[-1] < vals[0] else "stable"
                lines.append(f"- {key.replace('_', ' ').title()}: {' → '.join(str(int(v)) for v in vals)} ({trend})")
    return "\n".join(lines)


def detect_patterns(limit: int = 50) -> list[str]:
    """Analyze history.jsonl for recurring patterns. Returns suggestion strings."""
    all_history = load_history(limit=limit)
    if not all_history:
        return []
    suggestions = []
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent_recipes = [
        e["recipe"] for e in all_history
        if e.get("recipe") and e.get("ts", "") >= week_ago
    ]
    recipe_counts = Counter(recent_recipes)
    for recipe, count in recipe_counts.items():
        if count >= 3:
            suggestions.append(
                f"You've run '{recipe}' {count} times this week. "
                f"Consider setting up a scheduled routine to automate this."
            )
    recipe_groups: dict[str, list[dict]] = {}
    for e in all_history:
        r = e.get("recipe")
        if r:
            recipe_groups.setdefault(r, []).append(e)
    decline_metrics = {
        "find-hot-leads": ("top_heat", "Top heat score"),
        "list-health-audit": ("total_contacts", "Total contacts"),
        "deal-hygiene": ("total_open", "Open deals"),
    }
    for recipe, (metric_key, metric_label) in decline_metrics.items():
        runs = recipe_groups.get(recipe, [])[:3]
        if len(runs) < 3:
            continue
        vals = []
        for r in runs:
            v = r.get(metric_key)
            if v is not None:
                try:
                    vals.append(float(v))
                except (ValueError, TypeError):
                    break
        if len(vals) == 3 and vals[0] < vals[1] < vals[2]:
            suggestions.append(
                f"{metric_label} has declined 3 runs in a row "
                f"({int(vals[2])} → {int(vals[1])} → {int(vals[0])}). "
                f"Investigate root cause."
            )
    known_recipes = {"find-hot-leads", "deal-hygiene", "list-health-audit"}
    run_recipes = {e.get("recipe") for e in all_history if e.get("recipe")}
    never_run = known_recipes - run_recipes
    for recipe in sorted(never_run):
        suggestions.append(
            f"You haven't run '{recipe}' yet. It may surface useful insights about your account."
        )
    return suggestions


def env_or_die(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        sys.stderr.write(f"ERROR: {key} environment variable not set.\n")
        sys.exit(1)
    return val
