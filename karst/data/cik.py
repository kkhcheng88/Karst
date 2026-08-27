"""上市公司的錨:SEC CIK。

D-026 第 2 條:上市公司以 SEC CIK 為錨。名單取自 SEC 公開的
``company_tickers.json``(代號→CIK 對照,無需登記或鑰匙)。

SEC 要求來訪者在 User-Agent 自報身分與聯絡方法,否則回 403。預設值只是佔位,
真正抓數前請設環境變數 ``KARST_SEC_USER_AGENT``,寫成「名稱 電郵」。

抓不到 CIK 不是致命傷:管線改用**佔位錨**(``PLACEHOLDER-<代號>``)登記該實體,
並在快照說明檔註明哪幾隻是佔位。佔位錨與真 CIK 分得開——真 CIK 是十位數字,
佔位錨永遠以 ``PLACEHOLDER-`` 起頭——日後補回真 CIK 時一眼看得出要補哪幾隻。
"""

from __future__ import annotations

import gzip
import io
import json
import os
import urllib.error
import urllib.request

from .errors import DataFetchFailed

SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_USER_AGENT_ENV = "KARST_SEC_USER_AGENT"
DEFAULT_SEC_USER_AGENT = "Karst backtesting research karst-data@example.com"

# 佔位錨的前綴:真 CIK 是十位數字,不會與此撞
PLACEHOLDER_PREFIX = "PLACEHOLDER-"


def sec_user_agent(explicit: str | None = None) -> str:
    named = explicit or os.environ.get(SEC_USER_AGENT_ENV)
    if named and named.strip():
        return named.strip()
    return DEFAULT_SEC_USER_AGENT


def placeholder_cik(ticker: str) -> str:
    """抓不到真 CIK 時的佔位錨。"""
    return f"{PLACEHOLDER_PREFIX}{ticker.strip().upper()}"


def is_placeholder(anchor: str) -> bool:
    return str(anchor).upper().startswith(PLACEHOLDER_PREFIX)


def fetch_cik_map(*, user_agent: str | None = None, timeout: float = 30.0) -> dict[str, str]:
    """抓 SEC 的代號→CIK 對照,回傳 ``{代號: 十位數 CIK}``。

    抓不到即拋 ``DataFetchFailed``——由調用方決定是否退回佔位錨,
    這一層不代它默默吞掉。
    """
    request = urllib.request.Request(
        SEC_COMPANY_TICKERS_URL,
        headers={
            "User-Agent": sec_user_agent(user_agent),
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            if response.headers.get("Content-Encoding") == "gzip":
                raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        payload = json.loads(raw.decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise DataFetchFailed(
            f"SEC 代號→CIK 對照抓不到({type(exc).__name__}: {exc});"
            f"SEC 要求 User-Agent 自報身分與聯絡方法,可設環境變數 {SEC_USER_AGENT_ENV}"
        ) from exc

    mapping: dict[str, str] = {}
    for row in payload.values():
        ticker = str(row.get("ticker", "")).strip().upper()
        cik = str(row.get("cik_str", "")).strip()
        if ticker and cik:
            mapping[ticker] = cik.zfill(10)
    if not mapping:
        raise DataFetchFailed("SEC 代號→CIK 對照回了空名單,當抓取失敗處理")
    return mapping
