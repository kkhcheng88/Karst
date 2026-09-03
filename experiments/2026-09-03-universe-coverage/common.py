# -*- coding: utf-8 -*-
"""KARST-173 共用:價格庫讀取、代號接實體、面板時點取值。全部唯讀。

判準見同目錄 CRITERIA.md;本檔只實作,不新增定義。
"""
from __future__ import annotations

import functools
import pathlib

import numpy as np
import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")
PRICE_DIR = REPO / "data" / "prices" / "daily"
PANEL = REPO / "data" / "panel" / "quarterly_v3.parquet"
UNIVERSE = REPO / "data" / "universe"
SPLITS = REPO / "experiments" / "2026-09-02-fourpiece-test" / "data" / "splits.parquet"
SP500 = REPO / "karst" / "data" / "universes" / "sp500_historical.csv"
TENBAGGERS = (REPO / "experiments" / "2026-09-02-tenbagger-scan" / "out" /
              "tenbagger_names.csv")
OUT = pathlib.Path(__file__).resolve().parent / "out"

CONTAMINATED = {"CPWR", "EP", "PARA"}   # KARST-160 RULES 第九節:拆股因子被代號重用污染


def load_prices(entity_ids: set[str] | None = None,
                since: str | None = None,
                cols: tuple[str, ...] = ("entity_id", "ticker", "date", "close",
                                         "adj_close", "series_role")) -> pd.DataFrame:
    """讀價格庫。entity_ids 與 since 都是為了不把 20.6M 列全塞進記憶體。"""
    frames = []
    for p in sorted(PRICE_DIR.glob("part_*.parquet")):
        df = pd.read_parquet(p, columns=list(cols))
        if "date" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["date"]):
            df["date"] = pd.to_datetime(df["date"])
        if entity_ids is not None:
            df = df[df["entity_id"].isin(entity_ids)]
        if since is not None:
            df = df[df["date"] >= pd.Timestamp(since)]
        if len(df):
            frames.append(df)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=list(cols))
    return out.sort_values(["entity_id", "ticker", "date"]).reset_index(drop=True)


@functools.lru_cache(maxsize=1)
def ticker_periods() -> pd.DataFrame:
    tp = pd.read_parquet(UNIVERSE / "ticker_periods.parquet")
    tp["valid_from"] = pd.to_datetime(tp["valid_from"], errors="coerce")
    tp["valid_to"] = pd.to_datetime(tp["valid_to"], errors="coerce")
    return tp


@functools.lru_cache(maxsize=1)
def price_manifest() -> pd.DataFrame:
    m = pd.read_csv(PRICE_DIR / "manifest.csv", dtype={"entity_id": str})
    m["entity_id"] = m["entity_id"].str.zfill(10)
    return m


def match_entity(ticker: str, t0: pd.Timestamp) -> tuple[str | None, str]:
    """CRITERIA 第三節:代號 + t0 落在時段內;多過一段用同實體別名閘排序。"""
    tp = ticker_periods()
    hit = tp[(tp["ticker"] == ticker)
             & (tp["valid_from"] <= t0)
             & (tp["valid_to"].isna() | (tp["valid_to"] >= t0))]
    if hit.empty:
        return None, "時段不覆蓋 t0" if (tp["ticker"] == ticker).any() else "代號表無此代號"
    if len(hit) == 1:
        return str(hit.iloc[0]["entity_id"]), "唯一"
    man = price_manifest()
    rows = {(r.entity_id, r.ticker): (r.rows if pd.notna(r.rows) else 0)
            for r in man.itertuples()}
    hit = hit.assign(
        _openended=hit["valid_to"].isna().astype(int),
        _rows=[rows.get((e, ticker), 0) for e in hit["entity_id"]])
    hit = hit.sort_values(["_openended", "_rows", "entity_id"],
                          ascending=[False, False, True])
    return str(hit.iloc[0]["entity_id"]), f"別名閘挑一({len(hit)} 段命中)"


@functools.lru_cache(maxsize=1)
def sp500_periods() -> pd.DataFrame:
    h = pd.read_csv(SP500, dtype=str).fillna("")
    h["joined_on"] = pd.to_datetime(h["joined_on"], errors="coerce")
    h["left_on"] = pd.to_datetime(h["left_on"], errors="coerce")
    return h


def in_index(ticker: str, t0: pd.Timestamp) -> bool:
    h = sp500_periods()
    hit = h[(h["ticker"] == ticker) & (h["joined_on"] <= t0)
            & (h["left_on"].isna() | (h["left_on"] >= t0))]
    return bool(len(hit))


@functools.lru_cache(maxsize=1)
def splits() -> pd.DataFrame:
    s = pd.read_parquet(SPLITS)
    s["report_date"] = pd.to_datetime(s["report_date"], errors="coerce")
    return s


def split_factor_after(ticker: str, t0: pd.Timestamp) -> tuple[float, bool]:
    """t0 之後的累積拆股因子。回傳(因子, 代號是否在拆股表內)。"""
    s = splits()
    in_table = bool((s["symbol"] == ticker).any())
    sub = s[(s["symbol"] == ticker) & (s["report_date"] > t0)]
    return float(np.prod(sub["ratio"].to_numpy())) if len(sub) else 1.0, in_table


PANEL_COLS = ["entity_id", "period_end", "filed_date", "shares_outstanding",
              "cash_and_equivalents", "short_term_investments", "liabilities",
              "lt_debt", "st_debt", "currency"]


@functools.lru_cache(maxsize=1)
def panel() -> pd.DataFrame:
    p = pd.read_parquet(PANEL, columns=PANEL_COLS)
    p = p[p["filed_date"].notna()]
    return p.sort_values(["entity_id", "filed_date", "period_end"]).reset_index(drop=True)


def panel_asof(entity_id: str, when: pd.Timestamp) -> pd.Series | None:
    """CRITERIA 第四、五節:取 filed_date <= when 的最後一列(時點正確)。"""
    p = panel()
    sub = p[(p["entity_id"] == entity_id) & (p["filed_date"] <= when)]
    if sub.empty:
        return None
    return sub.iloc[-1]


def net_cash_flags(row: pd.Series | None) -> dict:
    """CRITERIA 第五節的 N1 / N2 兩個口徑,只出符號。"""
    out = {"n1": None, "n1_reason": "no_panel_row", "n2": None, "n2_reason": "no_panel_row"}
    if row is None:
        return out
    cash = row["cash_and_equivalents"]
    sti = row["short_term_investments"]
    liab = row["liabilities"]
    ltd = row["lt_debt"]
    std = row["st_debt"]
    if pd.isna(cash):
        out["n1_reason"] = out["n2_reason"] = "cash_missing"
    else:
        if pd.isna(liab):
            out["n1_reason"] = "liabilities_missing"
        else:
            out["n1"] = bool(cash + (0.0 if pd.isna(sti) else sti) - liab > 0)
            out["n1_reason"] = "none" if not pd.isna(sti) else "sti_missing_as_zero"
        if pd.isna(ltd):
            out["n2_reason"] = "lt_debt_missing"
        else:
            out["n2"] = bool(cash - (ltd + (0.0 if pd.isna(std) else std)) > 0)
            out["n2_reason"] = "none" if not pd.isna(std) else "st_debt_missing_as_zero"
    return out
