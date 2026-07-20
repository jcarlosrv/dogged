from typing import assert_type

import pytest

from dogged import memoize, retry
from dogged.memoize import Memoized


def test_retry_bare_form_retries() -> None:
    calls = 0

    @retry
    def flaky() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ValueError("boom")
        return "ok"

    assert flaky() == "ok"
    assert calls == 3


def test_retry_called_form_still_works() -> None:
    calls = 0

    @retry(times=2)
    def flaky() -> str:
        nonlocal calls
        calls += 1
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        flaky()
    assert calls == 2


def test_memoize_bare_form_caches() -> None:
    calls = 0

    @memoize
    def double(x: int) -> int:
        nonlocal calls
        calls += 1
        return x * 2

    assert double(3) == 6
    assert double(3) == 6
    assert calls == 1
    double.cache_clear()
    assert double(3) == 6
    assert calls == 2


def test_memoize_called_form_still_works() -> None:
    calls = 0

    @memoize(ttl=60)
    def double(x: int) -> int:
        nonlocal calls
        calls += 1
        return x * 2

    assert double(3) == 6
    assert double(3) == 6
    assert calls == 1


def test_static_types_are_preserved() -> None:
    @retry
    def bare_retry(x: int, /) -> str:
        return str(x)

    @retry(times=2)
    def called_retry(x: int, /) -> str:
        return str(x)

    @memoize
    def bare_memo(x: int, /) -> str:
        return str(x)

    @memoize(ttl=60)
    def called_memo(x: int, /) -> str:
        return str(x)

    assert_type(bare_retry(1), str)
    assert_type(called_retry(1), str)
    assert_type(bare_memo, Memoized[[int], str])
    assert_type(called_memo, Memoized[[int], str])