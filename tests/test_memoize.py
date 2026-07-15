from __future__ import annotations

import time

import pytest

from dogged import memoize


def test_caches_repeated_calls() -> None:
    calls = 0

    @memoize()
    def add(a: int, b: int) -> int:
        nonlocal calls
        calls += 1
        return a + b

    assert add(2, 3) == 5
    assert add(2, 3) == 5
    assert calls == 1


def test_distinct_args_cached_separately() -> None:
    calls = 0

    @memoize()
    def add(a: int, b: int) -> int:
        nonlocal calls
        calls += 1
        return a + b

    add(2, 3)
    add(9, 9)
    assert calls == 2


def test_cache_clear_forces_recompute() -> None:
    calls = 0

    @memoize()
    def add(a: int, b: int) -> int:
        nonlocal calls
        calls += 1
        return a + b

    add(2, 3)
    add.cache_clear()
    add(2, 3)
    assert calls == 2


def test_ttl_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"t": 1000.0}
    monkeypatch.setattr(time, "monotonic", lambda: clock["t"])
    calls = 0

    @memoize(ttl=60)
    def add(a: int, b: int) -> int:
        nonlocal calls
        calls += 1
        return a + b

    add(2, 3)
    clock["t"] = 1059.0
    add(2, 3)
    assert calls == 1
    clock["t"] = 1061.0
    add(2, 3)
    assert calls == 2


def test_invalid_ttl_rejected() -> None:
    with pytest.raises(ValueError, match="ttl must be positive"):
        memoize(ttl=0)


def test_preserves_name() -> None:
    @memoize()
    def add(a: int, b: int) -> int:
        return a + b

    assert add.__name__ == "add"