"""Tests for ACClient.fetch_many() concurrent pagination."""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from _ac_client import ACClient  # noqa: E402


def _make_client(monkeypatch, responses: dict, delay_per_request: float = 0.0):
    """Return an ACClient whose _request returns canned data after `delay`.

    Concurrent execution should still respect the throttle lock — but
    delay_per_request lets us measure parallelism speedups in tests by
    making serial vs parallel timing easy to distinguish.
    """
    monkeypatch.setenv("AC_API_URL", "https://test.api-us1.com")
    monkeypatch.setenv("AC_API_TOKEN", "tok")
    # Disable real throttling for the test so we measure pool overhead only
    monkeypatch.setattr(ACClient, "MIN_REQUEST_INTERVAL", 0.0)

    c = ACClient()
    seen: list[tuple[float, str]] = []
    lock = threading.Lock()

    def fake_request(method, path, data=None, params=None, max_retries=5):
        if delay_per_request:
            time.sleep(delay_per_request)
        key = path.split("?")[0]
        with lock:
            seen.append((time.monotonic(), key))
        # Return the canned shape so paginate() exits after one page
        return responses.get(key, {})

    c._request = fake_request
    c._seen = seen
    return c


def test_returns_one_entry_per_request(monkeypatch):
    c = _make_client(monkeypatch, {
        "deals":        {"deals":        [{"id": "1"}, {"id": "2"}]},
        "contactTags":  {"contactTags":  [{"id": "10"}]},
        "fieldValues":  {"fieldValues":  [{"id": "100"}, {"id": "101"}, {"id": "102"}]},
    })
    out = c.fetch_many([
        ("deals",       "deals",        None, 1000),
        ("contactTags", "contactTags",  None, 1000),
        ("fieldValues", "fieldValues",  None, 1000),
    ], max_workers=3)
    assert set(out.keys()) == {"deals", "contactTags", "fieldValues"}
    assert len(out["deals"]) == 2
    assert len(out["contactTags"]) == 1
    assert len(out["fieldValues"]) == 3


def test_per_request_error_does_not_break_siblings(monkeypatch):
    from _ac_client import ACClientError
    monkeypatch.setenv("AC_API_URL", "https://test.api-us1.com")
    monkeypatch.setenv("AC_API_TOKEN", "tok")
    monkeypatch.setattr(ACClient, "MIN_REQUEST_INTERVAL", 0.0)
    c = ACClient()

    def selective_request(method, path, data=None, params=None, max_retries=5):
        key = path.split("?")[0]
        if key == "deals":
            raise ACClientError(403, "Deals not enabled")
        return {key: [{"id": "1"}]}
    c._request = selective_request

    out = c.fetch_many([
        ("contacts", "contacts", None, 100),
        ("deals",    "deals",    None, 100),
        ("tags",     "tags",     None, 100),
    ], max_workers=3)
    assert out["contacts"] == [{"id": "1"}]
    assert out["tags"] == [{"id": "1"}]
    # deals returns an error sentinel
    assert isinstance(out["deals"], dict)
    assert out["deals"]["status_code"] == 403
    assert "error" in out["deals"]


def test_throttle_lock_serializes_concurrent_callers(monkeypatch):
    """Direct check on the throttle gate: 5 threads calling _throttle()
    simultaneously should each see ≥ MIN_REQUEST_INTERVAL spacing between
    their gate-exit times (the throttle is what enforces the rate limit)."""
    from concurrent.futures import ThreadPoolExecutor
    monkeypatch.setenv("AC_API_URL", "https://test.api-us1.com")
    monkeypatch.setenv("AC_API_TOKEN", "tok")
    monkeypatch.setattr(ACClient, "MIN_REQUEST_INTERVAL", 0.05)  # 50ms gap
    c = ACClient()
    gate_exit_times: list[float] = []
    capture_lock = threading.Lock()

    def gated_call():
        c._throttle()
        with capture_lock:
            gate_exit_times.append(time.monotonic())

    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(lambda _: gated_call(), range(5)))

    gate_exit_times.sort()
    for a, b in zip(gate_exit_times, gate_exit_times[1:]):
        assert (b - a) >= 0.04, f"Throttle race: gap {b-a:.3f}s"
