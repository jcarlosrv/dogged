# dogged

Zero-dependency, strictly-typed resilience decorators for Python.

`retry` | `timeout` | `memoize` | `rate_limit` | `circuit_breaker`

Requires Python 3.11+. MIT licensed.

## Why

Resilience patterns are easy to write badly and tedious to write well. Most
implementations either pull in a large framework, lose your function's type
signature, or quietly swallow exceptions. `dogged` is a small library that
does one thing: composable decorators that preserve types exactly, with no
runtime dependencies.

Every decorator is fully typed with `ParamSpec`, so the decorated function
keeps its parameter names, argument types, and return type. The package ships
`py.typed` and the source is clean under `mypy --strict`.

## Install

```
git clone https://github.com/jcarlosrv/dogged
cd dogged
pip install -e ".[dev]"
```

## Quick start

```python
from dogged import retry

@retry(times=3, delay=0.5, backoff=2.0)
def fetch_user(user_id: int) -> dict[str, int]:
    return call_flaky_api(user_id)
```

Three attempts, waiting 0.5s then 1.0s between them. If all three fail, the
last exception is re-raised unchanged.

## Decorators

### `@retry`

Retries a function when it raises. Accepts a bare form and a configured form:

```python
@retry
def bare() -> str: ...

@retry(times=5, delay=1.0, backoff=2.0, max_delay=10.0)
def configured() -> str: ...
```

- `times` (default 3) total attempts, not extra attempts
- `exceptions` (default `Exception`) exception type or tuple to catch
- `delay` (default 0.0) seconds before the first retry
- `backoff` (default 1.0) multiplier applied to the delay each attempt
- `max_delay` (default `None`) ceiling on the delay

Narrow what you catch with `exceptions`:

```python
@retry(times=3, exceptions=(ConnectionError, TimeoutError))
def fetch() -> bytes: ...
```

### `@timeout`

Raises `TimeoutError` if the call exceeds the given number of seconds.

```python
@timeout(5.0)
def slow_query() -> list[str]: ...
```

### `@memoize`

Caches results by arguments, with an optional TTL. Also has both forms:

```python
@memoize
def square(x: int) -> int: ...

@memoize(ttl=300.0)
def load_config(key: str) -> str: ...
```

Clear the cache with `.cache_clear()`, which is visible to type checkers:

```python
square.cache_clear()
```

TTL is measured with `time.monotonic()`, so cache expiry is unaffected by
system clock changes.

### `@rate_limit`

Allows at most `calls` invocations per `period` seconds, using a sliding
window. Raises `RateLimitExceeded` when the budget is spent.

```python
from dogged import rate_limit, RateLimitExceeded

@rate_limit(calls=100, period=60.0)
def send_message(text: str) -> None: ...
```

`RateLimitExceeded` carries `.retry_after`, the seconds until a slot frees up.

### `@circuit_breaker`

Stops calling a failing dependency instead of hammering it. After
`failure_threshold` consecutive failures the circuit opens and calls fail fast
with `CircuitBreakerOpen` without invoking the function. After
`recovery_timeout` seconds one probe call is allowed through: if it succeeds
the circuit closes, if it fails the circuit reopens.

```python
from dogged import circuit_breaker, CircuitBreakerOpen

@circuit_breaker(failure_threshold=5, recovery_timeout=30.0)
def query_service() -> dict[str, str]: ...
```

`CircuitBreakerOpen` carries `.retry_after`. Any success resets the failure
count, so the threshold counts consecutive failures.

## Composing

Decorators stack, and the exceptions are designed to cooperate.
`RateLimitExceeded` and `CircuitBreakerOpen` both subclass `RuntimeError`, so
`@retry` catches them by default:

```python
@retry(times=5, delay=1.0)
@rate_limit(calls=100, period=60.0)
def call_api() -> str: ...
```

Applied bottom-up: the rate limiter wraps the function, and `retry` wraps the
rate limiter. A rejected call backs off and tries again once the window slides,
rather than failing outright.

## Typing

The decorators are transparent to type checkers:

```python
@retry(times=3)
def parse(raw: str) -> dict[str, int]: ...

reveal_type(parse)        # (raw: str) -> dict[str, int]
parse(123)                # error: incompatible argument type
```

Notable details:

- `ParamSpec` and `TypeVar` preserve the full signature, not `(*args, **kwargs)`
- `@overload` gives `@retry` and `@memoize` precise types in both bare and
  configured form, with no unions leaking to callers
- `@memoize` returns a `Memoized` `Protocol`, so `.cache_clear()` and
  `.__name__` type-check on the decorated function
- the test suite uses `typing.assert_type` to pin inferred types, so a typing
  regression fails the build

## Limitations

These are deliberate trade-offs, documented rather than hidden.

- **`@timeout` cannot kill the running function.** It runs the call on a daemon
  thread and stops waiting after the deadline. The overrun thread keeps running
  until it finishes on its own. Python offers no safe way to terminate a thread,
  and a signal-based implementation would be Unix-only and main-thread-only.
- **`@circuit_breaker` may allow more than one probe.** The wrapped function is
  called outside the lock, so under concurrency several threads can enter the
  half-open state together. Holding the lock across the call would serialize
  every invocation, which is a worse trade. Breaker state stays consistent.
- **`@memoize` requires hashable arguments** and the cache is unbounded, the
  same constraints as `functools.lru_cache` without `maxsize`.
- **`@rate_limit` is per-process.** It is not a distributed rate limiter.

## Development

```
pip install -e ".[dev]"
ruff check .
mypy --strict src tests
pytest
```

## License

MIT
