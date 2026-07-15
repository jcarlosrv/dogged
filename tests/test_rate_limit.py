from __future__ import annotations

import time

import pytest

from dogged import RateLimitExceeded, rate_limit


def test_allows_up_to_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"t": 0.0}
    monkeypatch.setattr(time, "monotonic", lambda: clock["t"])

    @rate_limit(calls=3, period=1.0)
    def ping() -> str:
        return "ok"

    assert ping() == "ok"
    assert ping() == "ok"
    assert ping() == "ok"


def test_rejects_over_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"t": 0.0}
    monkeypatch.setattr(time, "monotonic", lambda: clock["t"])

    @rate_limit(calls=2, period=1.0)
    def ping() -> str:
        return "ok"

    ping()
    ping()
    with pytest.raises(RateLimitExceeded):
        ping()


def test_window_slides(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"t": 0.0}
    monkeypatch.setattr(time, "monotonic", lambda: clock["t"])

    @rate_limit(calls=1, period=1.0)
    def ping() -> str:
        return "ok"

    assert ping() == "ok"
    clock["t"] = 1.0
    assert ping() == "ok"


def test_retry_after_within_period(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"t": 0.0}
    monkeypatch.setattr(time, "monotonic", lambda: clock["t"])

    @rate_limit(calls=1, period=1.0)
    def ping() -> str:
        return "ok"

    ping()
    clock["t"] = 0.25
    with pytest.raises(RateLimitExceeded) as excinfo:
        ping()
    assert excinfo.value.retry_after == pytest.approx(0.75)


def test_independent_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"t": 0.0}
    monkeypatch.setattr(time, "monotonic", lambda: clock["t"])

    @rate_limit(calls=1, period=1.0)
    def a() -> str:
        return "a"

    @rate_limit(calls=1, period=1.0)
    def b() -> str:
        return "b"

    assert a() == "a"
    assert b() == "b"


def test_invalid_calls_rejected() -> None:
    with pytest.raises(ValueError, match="calls must be at least 1"):
        rate_limit(calls=0, period=1.0)


def test_invalid_period_rejected() -> None:
    with pytest.raises(ValueError, match="period must be positive"):
        rate_limit(calls=1, period=0.0)


def test_preserves_name() -> None:
    @rate_limit(calls=1, period=1.0)
    def ping() -> str:
        return "ok"

    assert ping.__name__ == "ping"