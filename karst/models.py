"""單一定義庫的值型別與時間戳規範化。

詞彙表(CONTEXT.md)的英文名同時是這裡的程式名:
entity id / factor / scale kind / event time / knowledge time / data snapshot。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Final

# 刻度型(scale kind, D-021 第 2 條):基數 / 序數 / 是非
SCALE_KINDS: Final[frozenset[str]] = frozenset({"cardinal", "ordinal", "boolean"})

# 實體種類:上市公司 / ETF / 虛擬籃子
ENTITY_KINDS: Final[frozenset[str]] = frozenset({"company", "etf", "basket"})

# 代號生效訖留空(至今仍然有效)時,比較用的上限日期
MAX_DATE: Final[str] = "9999-12-31"


class _NotApplicable:
    """「該股該日不參與該因子」的唯一標記(D-021 第 4 條)。

    缺失值不是 0,也不是「值為零」。本標記刻意**不可當真假值使用**——
    ``if value:`` 會即場拋錯,逼調用方寫明 ``value is NOT_APPLICABLE``,
    以免 0.0 與「不參與」在真假判斷裡混為一談。
    """

    _instance: "_NotApplicable | None" = None

    def __new__(cls) -> "_NotApplicable":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "NOT_APPLICABLE"

    def __bool__(self) -> bool:
        raise TypeError(
            "「不參與」不可當真假值使用;請寫 `value is NOT_APPLICABLE` 分辨"
            "「不參與」與「值真的是零」。"
        )


NOT_APPLICABLE: Final[_NotApplicable] = _NotApplicable()


@dataclass(frozen=True, slots=True)
class Entity:
    """實體(entity):一個不變的內部編號,代號只是它有生效期的屬性(D-026 第 2 條)。"""

    entity_id: int
    entity_kind: str
    display_name: str
    cik: str | None
    local_code: str | None


@dataclass(frozen=True, slots=True)
class TickerPeriod:
    """代號在某段日子屬於某實體。``valid_to`` 為 None 代表至今仍然有效。"""

    entity_id: int
    ticker: str
    valid_from: str
    valid_to: str | None


@dataclass(frozen=True, slots=True)
class FormulaProcedure:
    """公式派因子的產生程序:公式 + 輸入數據版本(D-021 第 6 條)。"""

    formula: str
    input_data_version: str

    kind: str = "formula"


@dataclass(frozen=True, slots=True)
class MaterialProcedure:
    """數值派因子的產生程序:材料 + 判官版本(D-021 第 6 條)。"""

    material: str
    judge_version: str

    kind: str = "material"


Procedure = FormulaProcedure | MaterialProcedure


@dataclass(frozen=True, slots=True)
class FactorVersion:
    """一個因子定義的其中一版。落庫後不可改,只可出新版(D-021 第 9 條)。

    追溯到批次(lineage depth, D-021 第 8 條)所需的三件之中,本型別佔兩件:
    因子版本編號與產生程序版本;第三件數據快照編號記在每個因子值上。
    """

    factor_version_id: int
    factor_id: int
    name: str
    family: str
    version_no: int
    parent_version_id: int | None
    scale_kind: str
    procedure: Procedure
    description: str | None
    created_at: str


@dataclass(frozen=True, slots=True)
class Snapshot:
    """數據快照(data snapshot):編號=日期+內容雜湊(D-026 第 3 條)。"""

    snapshot_id: str
    source: str
    taken_on: str
    content_hash: str
    path: str | None
    universe: tuple[str, ...]
    created_at: str


def as_date(value: date | datetime | str, field: str = "date") -> str:
    """規範化成 ``YYYY-MM-DD``。"""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        text = value.strip()
        try:
            return date.fromisoformat(text[:10]).isoformat()
        except ValueError as exc:  # pragma: no cover - 訊息路徑
            raise ValueError(f"{field} 不是有效日期:{value!r}") from exc
    raise TypeError(f"{field} 只收 date / datetime / ISO 字串,收到 {type(value).__name__}")


def as_timestamp(
    value: date | datetime | str,
    field: str = "timestamp",
    *,
    end_of_day: bool = False,
) -> str:
    """規範化成可直接字串比較的 ``YYYY-MM-DDTHH:MM:SS.ffffff``。

    只給日期時:預設當日子開頭;``end_of_day=True``(查詢截止用)當日子結尾,
    即「截至該日收工為止知道的一切」。
    """
    if isinstance(value, datetime):
        return value.isoformat(sep="T", timespec="microseconds")
    if isinstance(value, date):
        stamp = datetime.combine(value, datetime.min.time())
        return _edge(stamp, end_of_day)
    if isinstance(value, str):
        text = value.strip()
        if len(text) == 10:
            return _edge(datetime.fromisoformat(text), end_of_day)
        try:
            return datetime.fromisoformat(text).isoformat(sep="T", timespec="microseconds")
        except ValueError as exc:  # pragma: no cover - 訊息路徑
            raise ValueError(f"{field} 不是有效時間戳:{value!r}") from exc
    raise TypeError(f"{field} 只收 date / datetime / ISO 字串,收到 {type(value).__name__}")


def _edge(stamp: datetime, end_of_day: bool) -> str:
    if end_of_day:
        stamp = stamp.replace(hour=23, minute=59, second=59, microsecond=999999)
    return stamp.isoformat(sep="T", timespec="microseconds")


def open_ended(valid_to: str | None) -> str:
    """把「至今仍然有效」寫成一個可比較的上限。"""
    return MAX_DATE if valid_to is None else valid_to


def as_finite_float(value: Any, field: str = "value") -> float:
    """因子值必須是有限數:禁 NaN、禁 ±inf(D-021 第 10 條採納的三條紀律)。"""
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} 必須是有限數,收到 {value!r};缺失請不寫該列,不要寫 NaN 或 0")
    return number
