"""因子預測力:對齊因子值與未來回報,算逐日 Spearman 等級相關(IC)與滾動 ICIR(KARST-066)。

依 research/2026-08-29-alpha158-feasibility.md 第五節裁定的路線:不整套引入
alphalens(它的輸入形狀天生只認單一時間戳,Karst 的因子表是雙時間戳),自寫一層薄的
對齊 + 相關運算,對接 ``karst.factorstore`` 的長表與 ``karst.data.snapshots`` 的
K 線面板。

對齊怎樣做(D-021)
------------------

一個因子值「可以拿來做什麼」,由它的**可執行時點**決定——知情時點之後下一根可
交易 K 線的開市。所以回報起點**不是知情當日的收價**,而是可執行時點那根 K 線的
開價;沒有可執行時點的值(該快照日曆上沒有下一根 K 線)本來就沒有辦法變成一次
交易,對齊時直接不算。

持有期怎樣量(N 是參數,呼叫方給,本檔不設預設值)
--------------------------------------------------

「N 個交易日的持有期回報」= 第 1 個交易日(可執行時點那一根)的**開價買入**,
持有到第 N 個交易日(含首日在內,共 N 根 K 線)的**收價賣出**。所以 ``horizon=1``
是「當日開至當日收」,``horizon=5`` 是「一個交易周,周一開至周五收」,``horizon=21``
約一個月。這個換算法子本身是本票的實作裁定(不是另一條裁決),原因是與研究票
research/2026-08-29-factor-horizon-evidence.md 結語建議的「1、5、21 個交易日」
講法對得上——那份研究講的正是持有幾多個交易日,不是隔幾多日進場。

IC 的橫斷面怎樣分組
--------------------

逐日 Spearman 等級相關,按**知情時點那一日**分組(不是事件時點,亦不是可執行
時點)——這正是「按知情時點對齊未來回報」那句話的意思:同一個知情時點(通常
等於事件時點那一日,因為日線因子的知情時點就是事件那日的收工)之下,橫向比較
全部實體的因子值排名與各自其後 N 日回報排名有幾相近。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .errors import ContractViolation

#: 對齊表的欄。``factor_value`` / ``forward_return`` 的名刻意不沿用因子長表的
#: ``value`` ——同一張表裡兩個數值欄,不能再叫一個含糊的「value」。
ALIGNED_COLUMNS = (
    "factor_version_id",
    "entity_id",
    "knowledge_time",
    "factor_value",
    "forward_return",
)

_REQUIRED_FACTOR_COLUMNS = frozenset(
    {"factor_version_id", "entity_id", "knowledge_time", "executable_time", "value"}
)
_REQUIRED_PRICE_COLUMNS = frozenset({"date", "entity_id", "open", "close"})


def align_factor_to_forward_returns(
    factor_long: pd.DataFrame,
    price_frame: pd.DataFrame,
    *,
    horizon: int,
) -> pd.DataFrame:
    """組出「(知情時點, 實體) → 因子值」與「→ 未來 N 日回報」的對齊表。

    ``factor_long`` 是 ``FactorValueStore.read_long`` 的原樣輸出(或同形狀的表);
    ``price_frame`` 是 ``karst.data.snapshots.read_price_frame`` 的原樣輸出
    (日線長表,要有 ``open``、``close`` 兩欄)。``horizon`` 是持有期的交易日數,
    無預設——見本檔文首「持有期怎樣量」。

    沒有可執行時點的值、可執行時點不在這份價格面板日曆上、或者持有期跨出了
    面板的尾巴,一律不進對齊表——不是報錯,是那一列本來就對不出一個回報。
    """
    if int(horizon) != horizon or horizon < 1:
        raise ContractViolation(f"持有期窗口要是正整數(交易日數),收到 {horizon!r}")
    horizon = int(horizon)

    missing_factor = _REQUIRED_FACTOR_COLUMNS - set(factor_long.columns)
    if missing_factor:
        raise ContractViolation(f"因子長表缺欄位:{'、'.join(sorted(missing_factor))}")
    missing_price = _REQUIRED_PRICE_COLUMNS - set(price_frame.columns)
    if missing_price:
        raise ContractViolation(f"價格長表缺欄位:{'、'.join(sorted(missing_price))}")

    executable = factor_long.dropna(subset=["executable_time"]).reset_index(drop=True)
    if executable.empty or price_frame.empty:
        return pd.DataFrame({column: pd.Series(dtype="object") for column in ALIGNED_COLUMNS})

    prices = price_frame.copy()
    prices["date"] = pd.to_datetime(prices["date"])
    open_panel = prices.pivot(index="date", columns="entity_id", values="open").sort_index()
    close_panel = prices.pivot(index="date", columns="entity_id", values="close").sort_index()
    calendar = open_panel.index.to_numpy()
    if len(calendar) == 0:
        return pd.DataFrame({column: pd.Series(dtype="object") for column in ALIGNED_COLUMNS})

    entity_columns = open_panel.columns.to_numpy()
    entity_pos = {int(entity): position for position, entity in enumerate(entity_columns)}

    entry_dates = pd.to_datetime(executable["executable_time"]).dt.normalize().to_numpy()
    entry_idx = np.searchsorted(calendar, entry_dates)
    in_range = entry_idx < len(calendar)
    matched = np.zeros(len(executable), dtype=bool)
    matched[in_range] = calendar[entry_idx[in_range]] == entry_dates[in_range]

    exit_idx = entry_idx + (horizon - 1)
    matched &= exit_idx < len(calendar)

    entity_ids = executable["entity_id"].to_numpy()
    col_idx = np.array([entity_pos.get(int(entity), -1) for entity in entity_ids])
    matched &= col_idx >= 0

    safe_entry_idx = np.where(matched, entry_idx, 0)
    safe_exit_idx = np.where(matched, exit_idx, 0)
    safe_col_idx = np.where(matched, col_idx, 0)

    open_values = open_panel.to_numpy("float64")
    close_values = close_panel.to_numpy("float64")
    entry_open = open_values[safe_entry_idx, safe_col_idx]
    exit_close = close_values[safe_exit_idx, safe_col_idx]

    with np.errstate(invalid="ignore", divide="ignore"):
        forward_return = exit_close / entry_open - 1.0

    matched &= np.isfinite(entry_open) & np.isfinite(exit_close) & (entry_open != 0)

    out = pd.DataFrame(
        {
            "factor_version_id": executable["factor_version_id"].to_numpy(),
            "entity_id": entity_ids,
            "knowledge_time": executable["knowledge_time"].to_numpy(),
            "factor_value": executable["value"].to_numpy("float64"),
            "forward_return": forward_return,
        }
    )
    return out.loc[matched].reset_index(drop=True)


def daily_ic(aligned: pd.DataFrame) -> pd.DataFrame:
    """逐日 Spearman 等級相關,按因子版本 × 知情時點那一日分組。

    回一張 ``factor_version_id``、``date``、``ic``、``n``(當日參與橫斷面的實體數)
    的表。等級相關算法與 ``pandas.Series.corr(method="spearman")`` 同一套(排名後
    做 Pearson,同分取平均名次),但用 groupby 聚合一次過向量化算完,不逐組起
    python 迴圈呼叫——158 條因子 × 幾千個交易日這個量級,逐組呼叫會慢到不可用。
    當日不足兩個實體、或者當日全部實體同值(排名無變異)即該日 IC 留空(NaN),
    不當作 0。
    """
    required = {"factor_version_id", "knowledge_time", "factor_value", "forward_return"}
    missing = required - set(aligned.columns)
    if missing:
        raise ContractViolation(f"對齊表缺欄位:{'、'.join(sorted(missing))}")
    if aligned.empty:
        return pd.DataFrame(columns=["factor_version_id", "date", "ic", "n"])

    work = aligned.copy()
    work["date"] = pd.to_datetime(work["knowledge_time"]).dt.normalize()
    keys = ["factor_version_id", "date"]

    work["rank_x"] = work.groupby(keys)["factor_value"].rank()
    work["rank_y"] = work.groupby(keys)["forward_return"].rank()
    work["xy"] = work["rank_x"] * work["rank_y"]
    work["x2"] = work["rank_x"] ** 2
    work["y2"] = work["rank_y"] ** 2

    grouped = work.groupby(keys)
    n = grouped.size().rename("n")
    sx = grouped["rank_x"].sum()
    sy = grouped["rank_y"].sum()
    sxy = grouped["xy"].sum()
    sx2 = grouped["x2"].sum()
    sy2 = grouped["y2"].sum()

    numerator = n * sxy - sx * sy
    denom = np.sqrt((n * sx2 - sx**2) * (n * sy2 - sy**2))
    with np.errstate(invalid="ignore", divide="ignore"):
        ic = numerator / denom
    ic = ic.where((n >= 2) & (denom != 0))

    out = pd.DataFrame({"n": n, "ic": ic}).reset_index()
    return out.sort_values(keys).reset_index(drop=True)


def rolling_icir(daily: pd.DataFrame, *, window: int) -> pd.DataFrame:
    """滾動 IC 均值 / 標準差(ICIR = 均值 / 標準差),按因子版本分組,交易日為單位。

    ``window`` 是滾動窗口的交易日數,無預設值——呼叫方要答的事。窗口未滿的
    開頭幾日留空,不用不足一窗的樣本充數。
    """
    if int(window) != window or window < 2:
        raise ContractViolation(f"滾動窗口要是至少 2 的正整數(交易日數),收到 {window!r}")
    window = int(window)

    required = {"factor_version_id", "date", "ic"}
    missing = required - set(daily.columns)
    if missing:
        raise ContractViolation(f"逐日 IC 表缺欄位:{'、'.join(sorted(missing))}")
    if daily.empty:
        return pd.DataFrame(columns=["factor_version_id", "date", "ic_mean", "ic_std", "icir"])

    pieces: list[pd.DataFrame] = []
    for version_id, group in daily.sort_values("date").groupby("factor_version_id", sort=True):
        ordered = group.set_index("date")["ic"]
        ic_mean = ordered.rolling(window, min_periods=window).mean()
        ic_std = ordered.rolling(window, min_periods=window).std(ddof=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            icir = ic_mean / ic_std
        pieces.append(
            pd.DataFrame(
                {
                    "factor_version_id": version_id,
                    "date": ordered.index,
                    "ic_mean": ic_mean.to_numpy(),
                    "ic_std": ic_std.to_numpy(),
                    "icir": icir.to_numpy(),
                }
            )
        )
    return pd.concat(pieces, ignore_index=True)


def summarize_ic(daily: pd.DataFrame) -> pd.DataFrame:
    """全期摘要:每個因子版本的 IC 均值、標準差、ICIR、樣本日數(有定義的 IC 天數)。

    ``n_days`` 數的是「當日 IC 算得出」的日數,不是橫斷面日曆的全部日數——
    當日不足兩個實體、或者橫斷面無變異的那幾日不算進分母。
    """
    required = {"factor_version_id", "ic"}
    missing = required - set(daily.columns)
    if missing:
        raise ContractViolation(f"逐日 IC 表缺欄位:{'、'.join(sorted(missing))}")
    if daily.empty:
        return pd.DataFrame(columns=["factor_version_id", "ic_mean", "ic_std", "icir", "n_days"])

    valid = daily.dropna(subset=["ic"])
    if valid.empty:
        out = daily[["factor_version_id"]].drop_duplicates().reset_index(drop=True)
        out["ic_mean"] = np.nan
        out["ic_std"] = np.nan
        out["icir"] = np.nan
        out["n_days"] = 0
        return out

    grouped = valid.groupby("factor_version_id")["ic"]
    summary = grouped.agg(ic_mean="mean", ic_std=lambda s: s.std(ddof=1), n_days="count")
    summary = summary.reset_index()
    with np.errstate(invalid="ignore", divide="ignore"):
        summary["icir"] = summary["ic_mean"] / summary["ic_std"]
    return summary[["factor_version_id", "ic_mean", "ic_std", "icir", "n_days"]]
