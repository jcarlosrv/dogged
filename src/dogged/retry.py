from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import overload

from ._types import P, R


@overload
def retry(func: Callable[P, R], /) -> Callable[P, R]: ...


@overload
def retry(
    func: None = None,
    /,
    *,
    times: int = 3,
    exceptions: type[BaseException] | tuple[type[BaseException], ...] = Exception,
    delay: float = 0.0,
    backoff: float = 1.0,
    max_delay: float | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def retry(
    func: Callable[P, R] | None = None,
    /,
    *,
    times: int = 3,
    exceptions: type[BaseException] | tuple[type[BaseException], ...] = Exception,
    delay: float = 0.0,
    backoff: float = 1.0,
    max_delay: float | None = None,
) -> Callable[P, R] | Callable[[Callable[P, R]], Callable[P, R]]:
    if times < 1:
        raise ValueError("times must be at least 1")
    if delay < 0:
        raise ValueError("delay must be non-negative")
    if backoff < 1:
        raise ValueError("backoff must be at least 1")

    def decorator(target: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(target)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            current_delay = delay
            for attempt in range(1, times + 1):
                try:
                    return target(*args, **kwargs)
                except exceptions:
                    if attempt == times:
                        raise
                    if current_delay > 0:
                        time.sleep(current_delay)
                    current_delay *= backoff
                    if max_delay is not None:
                        current_delay = min(current_delay, max_delay)
            raise AssertionError("unreachable")  # pragma: no cover

        return wrapper

    if func is None:
        return decorator
    return decorator(func)