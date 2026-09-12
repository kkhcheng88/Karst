# -*- coding: utf-8 -*-
"""KARST-222 票 A 共用:逐檔掃描 `data/prices/daily/part_*.parquet` 的價格層。

**為什麼要另寫一支**:直接把 16 檔(2,065 萬列)一次讀入再 groupby/rank,峰值記憶體
足以把工序打死(上一工人 15:37 就是這樣被系統中止)。`part_*.parquet` 已核實**按 entity
分檔、無 entity 跨檔**(見執行紀錄),所以逐檔做 shift/rolling 與整批做完全等價。

本檔只讀價格,不改任何既有檔。兩個入口:
  - `state_at(date_set)`:只在指定日期留列,回傳 (逐 entity 每日狀態表, first_px 表)。
    shift(21/147/273)、252 日高、60 日成交額中位走勢全部在**該檔內**完成。
  - `price_arrays(entity_filter)`:回傳 entity → (日期, 還原收市, 收市, 開市) 的 numpy 陣列。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\projects\Karst")
PRICES = ROOT / "data" / "prices" / "daily"
PX_FROM = pd.Timestamp("2013-06-01")
FORWARD_DAYS = 273          # ret12 需要 273 個交易日前的價


def parts() -> list[Path]:
    return sorted(PRICES.glob("part_*.parquet"))


def _load_primary(p: Path, cols: list[str]) -> pd.DataFrame:
    d = pd.read_parquet(p, columns=["entity_id", "date", "series_role"] + cols)
    d = d[(d["series_role"] == "primary")]
    d = d[["entity_id", "date"] + cols]
    d["date"] = pd.to_datetime(d["date"])
    d = d[d["date"] >= PX_FROM]
    d = d.dropna(subset=["adj_close"])
    return d.sort_values(["entity_id", "date"], kind="stable").reset_index(drop=True)


def state_at(date_set: set) -> tuple[pd.DataFrame, dict]:
    """回傳 (df[entity_id,date,ret6,ret12,rank6,rank12,dist52,dv60], first_px dict)。"""
    keep = {pd.Timestamp(x) for x in date_set}
    frames = []
    first_px: dict[str, pd.Timestamp] = {}
    for p in parts():
        d = _load_primary(p, ["adj_close", "close", "volume"])
        if not len(d):
            continue
        for eid, g in d.groupby("entity_id", sort=False):
            first_px[eid] = g["date"].iloc[0]
        gp = d.groupby("entity_id", sort=False)["adj_close"]
        d["ret6"] = gp.shift(21) / gp.shift(147) - 1.0
        d["ret12"] = gp.shift(21) / gp.shift(273) - 1.0
        d["dist52"] = d["adj_close"] / gp.transform(
            lambda s: s.rolling(252, min_periods=60).max()) - 1.0
        d["dv"] = d["close"] * d["volume"]
        d["dv60"] = d.groupby("entity_id", sort=False)["dv"].transform(
            lambda s: s.rolling(60, min_periods=20).mean())
        sel = d[d["date"].isin(keep)]
        frames.append(sel[["entity_id", "date", "ret6", "ret12", "dist52", "dv60"]].copy())
        del d, sel
    out = pd.concat(frames, ignore_index=True)
    del frames
    out["rank6"] = out.groupby("date")["ret6"].rank(pct=True)
    out["rank12"] = out.groupby("date")["ret12"].rank(pct=True)
    return out, first_px


def price_arrays(entity_filter: set | None = None) -> dict:
    """entity → (日期(np.datetime64[D]), 還原收市, 收市, 開市)。供逐事件查價。"""
    out: dict[str, tuple] = {}
    for p in parts():
        d = _load_primary(p, ["adj_close", "close", "open"])
        if entity_filter is not None:
            d = d[d["entity_id"].isin(entity_filter)]
        if not len(d):
            continue
        for eid, g in d.groupby("entity_id", sort=False):
            out[eid] = (g["date"].values.astype("datetime64[D]"),
                        g["adj_close"].to_numpy(dtype="float64"),
                        g["close"].to_numpy(dtype="float64"),
                        g["open"].to_numpy(dtype="float64"))
        del d
    return out


def np_dates(series) -> np.ndarray:
    return pd.to_datetime(series, errors="coerce").values.astype("datetime64[D]")
