from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import Protocol, cast

from ._types import P, R, R_co


class Memoized(Protocol[P, R_co]):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R_co: ...
    def cache_clear(self) -> None: ...


def memoize(ttl: float | None = None) -> Callable[[Callable[P, R]], Memoized[P, R]]:
    if ttl is not None and ttl <= 0:
        raise ValueError("ttl must be positive")

    def decorator(func: Callable[P, R]) -> Memoized[P, R]:
        cache: dict[object, tuple[R, float]] = {}

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            key: object = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()
            cached = cache.get(key)
            if cached is not None:
                value, stored_at = cached
                if ttl is None or now - stored_at < ttl:
                    return value
            result = func(*args, **kwargs)
            cache[key] = (result, now)
            return result

        def cache_clear() -> None:
            cache.clear()

        wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]
        return cast("Memoized[P, R]", wrapper)

    return decorator