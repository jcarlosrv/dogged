import time

import pytest

from dogged import retry


def test_returns_on_first_success() -> None:
    calls = 0

    @retry(times=3)
    def ok() -> str:
        nonlocal calls
        calls += 1
        return "ok"

    assert ok() == "ok"
    assert calls == 1


def test_retries_then_succeeds() -> None:
    calls = 0

    @retry(times=3)
    def flaky() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ValueError("boom")
        return "recovered"

    assert flaky() == "recovered"
    assert calls == 3


def test_reraises_after_exhaustion() -> None:
    calls = 0

    @retry(times=3)
    def always_fail() -> None:
        nonlocal calls
        calls += 1
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        always_fail()
    assert calls == 3


def test_only_retries_listed_exceptions() -> None:
    calls = 0

    @retry(times=3, exceptions=KeyError)
    def wrong_error() -> None:
        nonlocal calls
        calls += 1
        raise ValueError("not caught")

    with pytest.raises(ValueError):
        wrong_error()
    assert calls == 1


def test_preserves_metadata() -> None:
    @retry(times=2)
    def documented(x: int) -> int:
        """A documented function."""
        return x

    assert documented.__name__ == "documented"
    assert documented.__doc__ == "A documented function."


def test_backoff_delays(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(time,"sleep", lambda s: sleeps.append(s))

    @retry(times=4, delay=1.0, backoff=2.0)
    def always_fail() -> None:
        raise ValueError

    with pytest.raises(ValueError):
        always_fail()
    assert sleeps == [1.0, 2.0, 4.0]


def test_max_delay_caps_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    @retry(times=4, delay=1.0, backoff=10.0, max_delay=5.0)
    def always_fail() -> None:
        raise ValueError

    with pytest.raises(ValueError):
        always_fail()
    assert sleeps == [1.0, 5.0, 5.0]


@pytest.mark.parametrize("bad", [0, -1])
def test_rejects_bad_times(bad: int) -> None:
    with pytest.raises(ValueError):
        retry(times=bad)