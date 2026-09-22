"""Per-source call limits (逐來源速率上限): rate, concurrency, timeout, retry with backoff.

Every network call an adapter makes goes through :func:`call` with the name of the
external source it hits. The limits are process-wide: members refreshed in parallel
share one budget per source, so widening the member pool never multiplies the load
on a provider. A call that runs out of time raises ``TimeoutError('... timed out')``
and one refused with HTTP 429 after its retries raises :class:`RateLimited`; both are
reported through the port's coverage as ``cause=timeout`` / ``rate_limited``.

The numbers below are defaults, each with its reason; they are the one place to tune.
"""
from __future__ import annotations

import threading
import time
import urllib.error
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Limit:
    rate: float         # calls started per second
    concurrency: int    # calls in flight at once
    timeout: float      # seconds one attempt may take
    retries: int        # extra attempts after a timeout / 429 / connection failure
    backoff: float      # seconds before the first retry; doubled for each next one


LIMITS = {
    # Longbridge OpenAPI quote API: 10 calls/s and 5 concurrent per account (vendor docs).
    'longbridge': Limit(rate=10, concurrency=5, timeout=20, retries=2, backoff=1.0),
    # Public RSS has no published quota; 2/s per host keeps 200 members inside two minutes
    # of feed time while staying far below anything a public endpoint would throttle.
    'yahoo_rss': Limit(rate=2, concurrency=4, timeout=12, retries=2, backoff=2.0),
    'google_news_rss': Limit(rate=2, concurrency=4, timeout=12, retries=2, backoff=2.0),
    # SEC fair-access policy: at most 10 requests/s; 8 leaves headroom for other clients.
    'edgar': Limit(rate=8, concurrency=4, timeout=60, retries=1, backoff=1.5),
}


class RateLimited(RuntimeError):
    """The provider kept answering 429 after every retry."""
    status = 429


class _Gate:
    def __init__(self, limit):
        self.limit = limit
        self.slots = threading.BoundedSemaphore(limit.concurrency)
        self.lock = threading.Lock()
        self.next_start = 0.0

    def wait_turn(self):
        with self.lock:
            now = time.monotonic()
            start = max(now, self.next_start)
            self.next_start = start + 1.0 / self.limit.rate
        if start > now:
            time.sleep(start - now)


_gates, _gates_lock = {}, threading.Lock()
# Runs each attempt so the caller can stop waiting at the timeout.
# ponytail: a vendor call that hangs past its timeout keeps its worker thread until the
# vendor returns; 64 workers absorb that. A cancellable client is the upgrade.
_attempts = ThreadPoolExecutor(max_workers=64, thread_name_prefix='karst-source')


def _gate(source):
    with _gates_lock:
        gate = _gates.get(source)
        if gate is None or gate.limit != LIMITS[source]:
            gate = _gates[source] = _Gate(LIMITS[source])
        return gate


def transient(exc):
    """Worth retrying: out of time, throttled, or the connection itself failed."""
    if isinstance(exc, (TimeoutError, RateLimited, ConnectionError)):
        return True
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code == 429 or exc.code >= 500
    return isinstance(exc, urllib.error.URLError)


def _throttled(exc):
    return 429 in (getattr(exc, 'code', None), getattr(exc, 'status', None))


def call(source, function, *args, **kwargs):
    """``function(*args, **kwargs)`` under ``source``'s limits; the last failure is raised."""
    limit, gate = LIMITS[source], _gate(source)
    for attempt in range(limit.retries + 1):
        with gate.slots:
            gate.wait_turn()
            future = _attempts.submit(function, *args, **kwargs)
            try:
                return future.result(timeout=limit.timeout)
            except FutureTimeout:
                error = TimeoutError(f'{source} call timed out after {limit.timeout:g} s')
            except Exception as exc:  # noqa: BLE001 - classified and re-raised below
                error = exc
        if not transient(error) or attempt == limit.retries:
            if _throttled(error):
                raise RateLimited(f'{source} rate limited (HTTP 429) after {attempt + 1} attempts') from error
            raise error
        time.sleep(limit.backoff * 2 ** attempt)
    raise AssertionError('unreachable')


def configure(**changes):
    """Override fields of every source's limit (benchmarks and tests); returns the old table."""
    old = dict(LIMITS)
    for source, limit in old.items():
        LIMITS[source] = replace(limit, **changes)
    return old
