# -*- coding: utf-8 -*-
"""Shared, rate-limited SEC client for KARST-146.

SEC fair access: at most 10 requests/second and a User-Agent that identifies
the requester. Retries are capped, never unbounded.
"""
from __future__ import annotations

import threading
import time
import urllib.error
import urllib.request

UA = "Casy Limited kaho.career@gmail.com"
MAX_RPS = 8.0            # stay under the SEC's 10/s ceiling
MAX_RETRIES = 3          # hard cap, per the ticket
BACKOFF_SEC = (2, 8, 20)

_lock = threading.Lock()
_last = [0.0]


def _throttle() -> None:
    with _lock:
        gap = 1.0 / MAX_RPS
        now = time.monotonic()
        wait = _last[0] + gap - now
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.monotonic()


def get(url: str, timeout: int = 90) -> tuple[bytes | None, str]:
    """Fetch a URL. Returns (bytes, "") on success, (None, reason) on failure.

    A 404 is a permanent answer ("this CIK has no such document"), so it is not
    retried. 403/429/5xx are transient and retried up to MAX_RETRIES.
    """
    last = ""
    for attempt in range(MAX_RETRIES + 1):
        _throttle()
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept-Encoding": "gzip, deflate",
                "Host": url.split("/")[2],
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    import gzip
                    raw = gzip.decompress(raw)
                return raw, ""
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}"
            if exc.code == 404:
                return None, "HTTP 404 (no such document)"
            if exc.code in (403, 429) or exc.code >= 500:
                if attempt < MAX_RETRIES:
                    time.sleep(BACKOFF_SEC[min(attempt, len(BACKOFF_SEC) - 1)])
                    continue
            return None, last
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_SEC[min(attempt, len(BACKOFF_SEC) - 1)])
                continue
    return None, f"gave up after {MAX_RETRIES} retries ({last})"
