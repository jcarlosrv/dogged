from __future__ import annotations

import time

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from dogged import (
    CircuitBreakerOpen,
    RateLimitExceeded,
    circuit_breaker,
    memoize,
    rate_limit,
    retry,
)


@given(
    times=st.integers(min_value=1, max_value=8),
    failures=st.integers(min_value=0, max_value=12),
)
def test_retry_attempt_count_is_bounded(times: int, failures: int) -> None:
    calls = 0

    @retry(times=times)
    def flaky() -> str:
        nonlocal calls
        calls += 1
        if calls <= failures:
            raise ValueError("boom")
        return "ok"

    if failures < times:
        assert flaky() == "ok"
        assert calls == failures + 1
    else:
        with pytest.raises(ValueError):
            flaky()
        assert calls == times

@given(values=st.lists(st.integers(), min_size=1, max_size=25))
def test_memoize_matches_undecorated_function(values: list[int]) -> None:
    calls = 0

    def square(x: int) -> int:
        return x * x

    @memoize
    def cached_square(x: int) -> int:
        nonlocal calls
        calls += 1
        return square(x)

    assert [cached_square(v) for v in values] == [square(v) for v in values]
    assert calls == len(set(values))

@given(a=st.integers(), b=st.integers())
def test_memoize_key_ignores_kwarg_order(a: int, b: int) -> None:
    calls = 0

    @memoize
    def combine(*, left: int, right: int) -> tuple[int, int]:
        nonlocal calls
        calls += 1
        return left, right

    assert combine(left=a, right=b) == combine(right=b, left=a)
    assert calls == 1

@given(
    calls=st.integers(min_value=1, max_value=10),
    extra=st.integers(min_value=1, max_value=4),
)
def test_rate_limit_allows_exactly_calls_per_period(calls: int, extra: int) -> None:
    period = 3600.0

    @rate_limit(calls, period)
    def ping() -> int:
        return 1

    for _ in range(calls):
        assert ping() == 1

    for _ in range(extra):
        with pytest.raises(RateLimitExceeded) as excinfo:
            ping()
        assert 0 < excinfo.value.retry_after <= period

@given(threshold=st.integers(min_value=1, max_value=8))
def test_breaker_opens_after_threshold_and_stops_calling(threshold: int) -> None:
    calls = 0

    @circuit_breaker(failure_threshold=threshold, recovery_timeout=3600.0)
    def always_fails() -> None:
        nonlocal calls
        calls += 1
        raise ValueError("boom")

    for _ in range(threshold):
        with pytest.raises(ValueError):
            always_fails()
    assert calls == threshold

    with pytest.raises(CircuitBreakerOpen):
        always_fails()
    assert calls == threshold

@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    times=st.integers(min_value=2, max_value=6),
    delay=st.floats(min_value=0.01, max_value=1.0),
    backoff=st.floats(min_value=1.0, max_value=3.0),
    max_delay=st.floats(min_value=0.01, max_value=2.0),
)
def test_retry_sleep_schedule_is_capped_and_monotonic(
    monkeypatch: pytest.MonkeyPatch,
    times: int,
    delay: float,
    backoff: float,
    max_delay: float,
) -> None:
    slept: list[float] = []
    monkeypatch.setattr(time, "sleep", slept.append)

    @retry(times=times, delay=delay, backoff=backoff, max_delay=max_delay)
    def always_fails() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError):
        always_fails()

    assert len(slept) == times - 1
    assert slept == sorted(slept)
    assert all(s <= max_delay for s in slept)