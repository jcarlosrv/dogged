from __future__ import annotations

import functools
import threading
from collections.abc import Callable

from ._types import P, R


def timeout(seconds: float) -> Callable[[Callable[P, R]], Callable[P, R]]:
    if seconds <= 0:
        raise ValueError("seconds must be positive")

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            result: dict[str, R] = {}
            failure: dict[str, BaseException] = {}

            def run() -> None:
                try:
                    result["value"] = func(*args, **kwargs)
                except BaseException as exc:
                    failure["error"] = exc

            worker = threading.Thread(target=run, daemon=True)
            worker.start()
            worker.join(seconds)
            if worker.is_alive():
                raise TimeoutError(f"{func.__name__} exceeded timeout of {seconds}s")
            if "error" in failure:
                raise failure["error"]
            return result["value"]

        return wrapper

    return decorator