"""宏觀快照的序列齊全度端點(KARST-061)。

策略詳情頁的宏觀驅動器參數區要答一句話:**這套設定跟住的那份宏觀快照,有沒有
一條序列已經靜靜停止講話?** 以前這件事只寫在快照說明檔第七節,要有人去翻才
看得見——^VIX3M 停更 28 個交易日無人察覺,就是這樣發生的(假設 A-008)。

本檔刻意**自成一個小端點**,不併入 ``api_strategy.py``:齊全度問的是「那份數據
新不新」,與策略詳情那一堆運行、成績、持倉是兩件事,而且它按**宏觀快照編號**取數,
不必經過任何一次運行。分開之後,頁面上那一行壞了不會拖跨整頁策略詳情。

**門檻不在這裡寫死。** 逐條的數(尾段落後幾多個交易日、留空佔幾多)算得出來不必
門檻;「這樣算不算過關」才要門檻,而門檻是參數、沒有預設值(D-008 第 3 條)。所以
本端點預設只交數:呼叫方明明白白給了 ``maxStaleDays`` 與 ``maxMissingRatio``
兩個,才會多交一份裁決。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from karst.data.freeze import (
    DEFAULT_MACRO_ROOT,
    CompletenessThresholds,
    audit_macro_completeness,
)
from karst.data.macro import read_macro_calendar, read_macro_completeness
from karst.errors import ContractViolation


def _macro_root(reader: Any) -> Path:
    """宏觀快取根在哪。

    優先用 reader 自己那一格;沒有就由價格快取根推出來(兩者是同一個 ``data/``
    下面的兄弟目錄),再退回套件的預設。找目錄的正本仍然是登記表上那條路徑——
    ``macro_snapshot_dir`` 先看登記,這裡給的只是搬過位之後的退路。
    """
    explicit = getattr(reader, "macro_root", None)
    if explicit:
        return Path(explicit)
    snapshot_root = getattr(reader, "snapshot_root", None)
    if snapshot_root:
        return Path(snapshot_root).parent / "macro_snapshots"
    return Path(DEFAULT_MACRO_ROOT)


def _one(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key) or []
    return values[0].strip() if values and values[0].strip() else None


def _thresholds(query: dict[str, list[str]]) -> CompletenessThresholds | None:
    """兩個都給了才判;一個都沒有給就只交數。**給一半當錯**,不猜另一半。"""
    days = _one(query, "maxStaleDays")
    ratio = _one(query, "maxMissingRatio")
    if days is None and ratio is None:
        return None
    if days is None or ratio is None:
        raise ContractViolation(
            "齊全度門檻要兩個一齊給(maxStaleDays 與 maxMissingRatio);"
            "門檻沒有預設值,給一半就補不出另一半"
        )
    try:
        return CompletenessThresholds(max_stale_days=int(days), max_missing_ratio=float(ratio))
    except ValueError:
        raise ContractViolation(
            f"齊全度門檻讀不成數:maxStaleDays={days!r}、maxMissingRatio={ratio!r}"
        ) from None


def completeness(reader: Any, query: dict[str, list[str]]) -> dict[str, Any]:
    """一份宏觀快照逐條序列的齊全度。

    ``snapshot`` 是宏觀快照編號(必給)。回的每一條有兩個要緊的數:
    ``staleDays``(尾段落後主日曆幾多個交易日)與 ``missingRatio``(留空佔幾多)。
    頁面那一行用得着的摘要另有 ``worstStaleDays`` 與 ``staleSeries``,不必自己再數。
    """
    snapshot_id = _one(query, "snapshot")
    if not snapshot_id:
        raise ContractViolation("要給宏觀快照編號:/api/macro/completeness?snapshot=<編號>")

    root = _macro_root(reader)
    frame = read_macro_completeness(reader.store, snapshot_id, root=root)
    calendar = read_macro_calendar(reader.store, snapshot_id, root=root)
    thresholds = _thresholds(query)
    alerts = (
        audit_macro_completeness(frame, calendar, thresholds=thresholds)
        if thresholds is not None
        else ()
    )

    series = [
        {
            "series": str(row["series"]),
            "actual": int(row["actual"]),
            "filled": int(row["filled"]),
            "missing": int(row["missing"]),
            "missingRatio": float(row["missing_ratio"]),
            "firstActual": str(row["first_actual"]),
            "lastActual": str(row["last_actual"]),
            "staleDays": int(row["stale_days"]),
        }
        for row in frame.to_dict("records")
    ]
    stale = [item["series"] for item in series if item["staleDays"] > 0]
    return {
        "snapshotId": snapshot_id,
        "calendarStart": calendar[0] if calendar else "",
        "calendarEnd": calendar[-1] if calendar else "",
        "tradingDays": len(calendar),
        "seriesCount": len(series),
        "series": series,
        # 頁面那一行要的三個數:最舊的一條落後幾多日、哪幾條落後、留空最多那條佔幾多
        "worstStaleDays": max((item["staleDays"] for item in series), default=0),
        "worstMissingRatio": max((item["missingRatio"] for item in series), default=0.0),
        "staleSeries": stale,
        # 門檻是可選的:沒有給就只有數,沒有裁決。``thresholds`` 是 None 即
        # 「這一次沒有人給門檻」,不是「門檻是零」——兩者在頁面上要分得開。
        "thresholds": thresholds.as_dict() if thresholds is not None else None,
        "alerts": [alert.as_dict() for alert in alerts],
    }


def routes(reader: Any) -> dict[str, Callable[[Any, dict[str, list[str]]], Any]]:
    """交回本檔的端點表,由 ``server.py`` 一行併入它自己那張。"""
    return {"/api/macro/completeness": lambda handler, query: completeness(reader, query)}
