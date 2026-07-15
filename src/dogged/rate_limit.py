from __future__ import annotations

import functools
import threading
import time
from collections import deque
from collections.abc import Callable

from ._types import P, R


class RateLimitExceeded(RuntimeError):
    def __init__(self, retry_after: float) -> None:
        super().__init__(f"rate limit exceeded; retry after {retry_after:.3f}s")
        self.retry_after = retry_after


class rate_limit:
    def __init__(self, calls: int, period: float) -> None:
        if calls < 1:
            raise ValueError("calls must be at least 1")
        if period <= 0:
            raise ValueError("period must be positive")
        self.calls = calls
        self.period = period

    def __call__(self, func: Callable[P, R]) -> Callable[P, R]:
        timestamps: deque[float] = deque()
        lock = threading.Lock()

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            with lock:
                now = time.monotonic()
                while timestamps and now - timestamps[0] >= self.period:
                    timestamps.popleft()
                if len(timestamps) >= self.calls:
                    retry_after = self.period - (now - timestamps[0])
                    raise RateLimitExceeded(retry_after)
                timestamps.append(now)
            return func(*args, **kwargs)

        return wrapper