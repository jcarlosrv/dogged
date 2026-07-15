from __future__ import annotations

import time

import pytest

from dogged import CircuitBreakerOpen, circuit_breaker


class Boom(Exception):
    pass


def test_passes_through_when_closed() -> None:
    @circuit_breaker(failure_threshold=3, recovery_timeout=10.0)
    def ok() -> str:
        return "ok"

    assert ok() == "ok"
    assert ok() == "ok"


def test_opens_after_threshold_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"t": 0.0}
    monkeypatch.setattr(time, "monotonic", lambda: clock["t"])
    calls = 0

    @circuit_breaker(failure_threshold=3, recovery_timeout=10.0)
    def flaky() -> None:
        nonlocal calls
        calls += 1
        raise Boom

    for _ in range(3):
        with pytest.raises(Boom):
            flaky()
    with pytest.raises(CircuitBreakerOpen):
        flaky()
    assert calls == 3


def test_stays_open_until_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"t": 0.0}
    monkeypatch.setattr(time, "monotonic", lambda: clock["t"])

    @circuit_breaker(failure_threshold=1, recovery_timeout=10.0)
    def flaky() -> None:
        raise Boom

    with pytest.raises(Boom):
        flaky()
    clock["t"] = 9.0
    with pytest.raises(CircuitBreakerOpen):
        flaky()


def test_half_open_success_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"t": 0.0}
    monkeypatch.setattr(time, "monotonic", lambda: clock["t"])
    fail = True

    @circuit_breaker(failure_threshold=1, recovery_timeout=10.0)
    def svc() -> str:
        if fail:
            raise Boom
        return "ok"

    with pytest.raises(Boom):
        svc()
    clock["t"] = 11.0
    fail = False
    assert svc() == "ok"
    assert svc() == "ok"


def test_half_open_failure_reopens(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"t": 0.0}
    monkeypatch.setattr(time, "monotonic", lambda: clock["t"])

    @circuit_breaker(failure_threshold=1, recovery_timeout=10.0)
    def flaky() -> None:
        raise Boom

    with pytest.raises(Boom):
        flaky()
    clock["t"] = 11.0
    with pytest.raises(Boom):
        flaky()
    clock["t"] = 12.0
    with pytest.raises(CircuitBreakerOpen):
        flaky()


def test_success_resets_failure_count(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"t": 0.0}
    monkeypatch.setattr(time, "monotonic", lambda: clock["t"])
    should_fail = True

    @circuit_breaker(failure_threshold=3, recovery_timeout=10.0)
    def svc() -> str:
        if should_fail:
            raise Boom
        return "ok"

    for _ in range(2):
        with pytest.raises(Boom):
            svc()
    should_fail = False
    assert svc() == "ok"
    should_fail = True
    for _ in range(2):
        with pytest.raises(Boom):
            svc()
    with pytest.raises(Boom):
        svc()


def test_only_expected_exceptions_count(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"t": 0.0}
    monkeypatch.setattr(time, "monotonic", lambda: clock["t"])

    @circuit_breaker(failure_threshold=1, recovery_timeout=10.0, expected_exception=Boom)
    def svc() -> None:
        raise ValueError("unexpected")

    for _ in range(3):
        with pytest.raises(ValueError):
            svc()
    with pytest.raises(ValueError):
        svc()


def test_retry_after_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"t": 0.0}
    monkeypatch.setattr(time, "monotonic", lambda: clock["t"])

    @circuit_breaker(failure_threshold=1, recovery_timeout=10.0)
    def flaky() -> None:
        raise Boom

    with pytest.raises(Boom):
        flaky()
    clock["t"] = 4.0
    with pytest.raises(CircuitBreakerOpen) as excinfo:
        flaky()
    assert excinfo.value.retry_after == pytest.approx(6.0)


def test_invalid_threshold_rejected() -> None:
    with pytest.raises(ValueError, match="failure_threshold must be at least 1"):
        circuit_breaker(failure_threshold=0)


def test_invalid_timeout_rejected() -> None:
    with pytest.raises(ValueError, match="recovery_timeout must be positive"):
        circuit_breaker(recovery_timeout=0.0)


def test_preserves_name() -> None:
    @circuit_breaker()
    def svc() -> str:
        return "ok"

    assert svc.__name__ == "svc"