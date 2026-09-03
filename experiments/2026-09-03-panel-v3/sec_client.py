# -*- coding: utf-8 -*-
"""KARST-172 共用的證監會取數客戶端(照 KARST-146 experiments/2026-09-02-fundamentals-panel
/sec_client.py 一字沿用,只加一個「403 出現就加長退讓」的計數器)。

證監會公平取用:每秒不超過 10 個請求,User-Agent 要認得出是誰。重試有硬上限,不無限跑。
"""
from __future__ import annotations

import threading
import time
import urllib.error
import urllib.request

UA = "Casy Limited kaho.career@gmail.com"
MAX_RPS = 8.0            # 留在證監會 10/s 上限之下
MAX_RETRIES = 3
BACKOFF_SEC = (2, 8, 20)

_lock = threading.Lock()
_last = [0.0]
_penalty = [0.0]         # 撞過 403 之後額外拉長的間隔
FORBIDDEN_COUNT = [0]


def _throttle() -> None:
    with _lock:
        gap = 1.0 / MAX_RPS + _penalty[0]
        now = time.monotonic()
        wait = _last[0] + gap - now
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.monotonic()


def get(url: str, timeout: int = 90) -> tuple[bytes | None, str, int]:
    """回 (bytes, "", http_code) 或 (None, 原因, http_code)。

    404 是永久答案(這個 CIK 沒有這份文件),不重試;403/429/5xx 是暫時的,
    重試最多 MAX_RETRIES 次,而且每撞一次 403 就把全域間隔拉長,不停跑。
    """
    last, code = "", 0
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
                return raw, "", resp.status
        except urllib.error.HTTPError as exc:
            code = exc.code
            last = f"HTTP {exc.code}"
            if exc.code == 404:
                return None, "HTTP 404 (no such document)", 404
            if exc.code == 403:
                FORBIDDEN_COUNT[0] += 1
                _penalty[0] = min(_penalty[0] + 0.25, 2.0)
            if exc.code in (403, 429) or exc.code >= 500:
                if attempt < MAX_RETRIES:
                    time.sleep(BACKOFF_SEC[min(attempt, len(BACKOFF_SEC) - 1)])
                    continue
            return None, last, code
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_SEC[min(attempt, len(BACKOFF_SEC) - 1)])
                continue
    return None, f"gave up after {MAX_RETRIES} retries ({last})", code
