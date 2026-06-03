"""ActiveCampaign v3 HTTP client with rate-limit handling and pagination."""

from __future__ import annotations

import json
import os
import random
import sys
import time

if sys.version_info < (3, 9):  # noqa: UP036 - friendly error for users running scripts directly
    sys.stderr.write(
        f"ERROR: Python 3.9 or newer required (you have {sys.version_info.major}.{sys.version_info.minor}).\n"
    )
    sys.exit(1)

import urllib.error
import urllib.request
from urllib.parse import urlencode


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
        """Yield records from a paginated endpoint one at a time."""
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
