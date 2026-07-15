import time

import pytest

from dogged import timeout


def test_returns_within_limit() -> None:
    @timeout(1.0)
    def fast() -> str:
        return "done"

    assert fast() == "done"


def test_raises_on_overrun() -> None:
    @timeout(0.05)
    def slow() -> str:
        time.sleep(1.0)
        return "too late"

    with pytest.raises(TimeoutError):
        slow()


def test_propagates_inner_exception() -> None:
    @timeout(1.0)
    def boom() -> None:
        raise ValueError("inner")

    with pytest.raises(ValueError, match="inner"):
        boom()


def test_passes_arguments() -> None:
    @timeout(1.0)
    def add(a: int, b: int) -> int:
        return a + b

    assert add(2, 3) == 5


def test_preserves_metadata() -> None:
    @timeout(1.0)
    def documented() -> None:
        """Docs."""

    assert documented.__name__ == "documented"
    assert documented.__doc__ == "Docs."


def test_rejects_nonpositive_seconds() -> None:
    with pytest.raises(ValueError):
        timeout(0)