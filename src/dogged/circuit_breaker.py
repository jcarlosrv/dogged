from __future__ import annotations

import functools
import threading
import time
from collections.abc import Callable
from enum import Enum, auto

from ._types import P, R


class CircuitBreakerOpen(RuntimeError):
    def __init__(self, retry_after: float) -> None:
        super().__init__(f"circuit is open; retry after {retry_after:.3f}s")
        self.retry_after = retry_after


class _State(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


class circuit_breaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        *,
        expected_exception: type[BaseException] | tuple[type[BaseException], ...] = Exception,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be positive")
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

    def __call__(self, func: Callable[P, R]) -> Callable[P, R]:
        expected = self.expected_exception
        lock = threading.Lock()
        state = _State.CLOSED
        failures = 0
        opened_at = 0.0

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            nonlocal state, failures, opened_at

            with lock:
                if state is _State.OPEN:
                    elapsed = time.monotonic() - opened_at
                    if elapsed < self.recovery_timeout:
                        raise CircuitBreakerOpen(self.recovery_timeout - elapsed)
                    state = _State.HALF_OPEN

            try:
                result = func(*args, **kwargs)
            except expected:
                with lock:
                    failures += 1
                    if state is _State.HALF_OPEN or failures >= self.failure_threshold:
                        state = _State.OPEN
                        opened_at = time.monotonic()
                raise
            else:
                with lock:
                    failures = 0
                    state = _State.CLOSED
                return result

        return wrapper