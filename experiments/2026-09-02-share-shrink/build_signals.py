# -*- coding: utf-8 -*-
"""KARST-156 step 1: build the two share-shrink signals.

Follows CRITERIA.md sections 1-3 literally. No return numbers are looked at here;
this file only turns the frozen definitions into columns.

Reads (all read-only, nothing copied -- D-134):
  panel_monthly.parquet                     KARST-146 accounts panel  (A version)
  data/secfacts/CIK*.json                   KARST-146 raw companyfacts (B version)
  fourpiece-test/data/splits.parquet        KARST-148 split-event table
  timing-sweep/data/daily_close.parquet     prices (auto_adjust=true)

Writes (data/ is gitignored):
  data/signals.parquet      one row per (month_end, ticker) in the eligible pool
  out/meta.json             split / scale / flag counts
  out/flagged_big_moves.csv every |r12| >= 40% mover and what it was judged to be
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
DATA = HERE / "data"
OUT = HERE / "out"
DATA.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

PANEL = REPO / "experiments" / "2026-09-02-fundamentals-panel" / "out" / "panel_monthly.parquet"
SECFACTS = REPO / "experiments" / "2026-09-02-fundamentals-panel" / "data" / "secfacts"
SPLITS = REPO / "experiments" / "2026-09-02-fourpiece-test" / "data" / "splits.parquet"
DAILY = REPO / "experiments" / "2026-09-02-timing-sweep" / "data" / "daily_close.parquet"

FIRST_SIGNAL = pd.Timestamp("2010-04-30")   # CRITERIA sec.1
LAST_SIGNAL = pd.Timestamp("2026-07-31")
BIG_MOVE = 0.40                             # CRITERIA sec.3.4
SCALE_DEV_TOL = 0.7                         # CRITERIA sec.3.3' (訂正一)
SCALE_REPAIR_MIN = 1.5
SCALE_MIN_OBS = 6
POW10_TOL = 0.35
JUNK_FLOOR = 100.0
BAND = (1e5, 1e11)

FORMS = {"10-K", "10-Q", "20-F", "40-F"}


# ---------------------------------------------------------------- split basis
def split_factor_fn(splits: pd.DataFrame):
    sp = {s: g[["report_date", "ratio"]].to_numpy() for s, g in splits.groupby("symbol")}

    def f(sym: str, filed) -> float:
        arr = sp.get(sym)
        if arr is None or pd.isna(filed):
            return 1.0
        out = 1.0
        for d, r in arr:
            if d > filed:
                out *= float(r)
        return out

    return f, sp


def splits_in_window(sp: dict, sym: str, lo, hi) -> float:
    """Product of split ratios with report_date in (lo, hi]."""
    arr = sp.get(sym)
    if arr is None:
        return 1.0
    out = 1.0
    for d, r in arr:
        if lo < d <= hi:
            out *= float(r)
    return out


# --------------------------------------------------------------- B: cover page
def load_dei(cik: str) -> pd.DataFrame | None:
    p = SECFACTS / f"CIK{cik}.json"
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as fh:
        d = json.load(fh)
    node = d.get("facts", {}).get("dei", {}).get("EntityCommonStockSharesOutstanding")
    if not node:
        return None
    units = node.get("units", {}).get("shares")
    if not units:
        return None
    rows = []
    for r in units:
        form = r.get("form", "")
        base = form[:-2] if form.endswith("/A") else form
        if base not in FORMS:
            continue
        val = r.get("val")
        if val is None or val <= 0:
            continue
        rows.append((r["end"], r["filed"], float(val), form.endswith("/A")))
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["end", "filed", "val", "amended"])
    df["end"] = pd.to_datetime(df["end"])
    df["filed"] = pd.to_datetime(df["filed"])
    # first version wins: per `end`, earliest filed among non-amended; amended only
    # counts when the period has no original filing at all
    df = df.sort_values(["end", "amended", "filed"])
    df = df.groupby("end", as_index=False).first()
    return df[["end", "filed", "val"]]


def pit_pick(months: np.ndarray, ends: np.ndarray, fileds: np.ndarray) -> np.ndarray:
    """For each month-end: index of the record with the latest `end` among filed <= m,
    or -1 when nothing has been filed yet."""
    out = np.full(len(months), -1, dtype=np.int64)
    floor = np.datetime64("1900-01-01")
    for i, m in enumerate(months):
        mask = fileds <= m
        if not mask.any():
            continue
        out[i] = int(np.argmax(np.where(mask, ends, floor)))
    return out


# --------------------------------------------------------------- scale guard
def scale_guard(vals: np.ndarray) -> tuple[np.ndarray, int, int]:
    """CRITERIA 3.3' (訂正一). Anchor = the company's full-sample median log10.
    A magnitude constant only: it can drop an observation or rescale its unit,
    never change a retained value's direction. Real corporate actions (|dev| < 1.5)
    are explicitly protected."""
    out = vals.copy()
    repaired = dropped = 0
    ok = np.isfinite(out) & (out > 0)
    if ok.sum() < SCALE_MIN_OBS:
        return out, 0, 0
    anchor = float(np.median(np.log10(out[ok])))
    for i, v in enumerate(out):
        if not np.isfinite(v) or v <= 0:
            continue
        dev = np.log10(v) - anchor
        if abs(dev) >= SCALE_DEV_TOL:
            if v < JUNK_FLOOR:
                out[i] = np.nan
                dropped += 1
                continue
            k = int(round(dev))
            if k != 0 and abs(dev) >= SCALE_REPAIR_MIN and abs(dev - k) <= POW10_TOL:
                out[i] = v / (10.0 ** k)
                repaired += 1
        if np.isfinite(out[i]) and not (BAND[0] <= out[i] <= BAND[1]):
            out[i] = np.nan
            dropped += 1
    return out, repaired, dropped


# --------------------------------------------------------------------- main
def main() -> None:
    daily = pd.read_parquet(DAILY)
    daily.index = pd.to_datetime(daily.index)
    tradable = set(daily.columns)

    cols = ["ticker", "cik", "month_end", "in_index", "diluted_shares",
            "diluted_shares_filed", "assets", "cfo_ttm"]
    panel = pd.read_parquet(PANEL, columns=cols)
    panel["month_end"] = pd.to_datetime(panel["month_end"])
    panel["diluted_shares_filed"] = pd.to_datetime(panel["diluted_shares_filed"],
                                                   errors="coerce")
    universe = sorted(set(panel["ticker"]) & tradable)
    panel = panel[panel["ticker"].isin(universe)].sort_values(["ticker", "month_end"])
    print(f"universe {len(universe)}  panel rows {len(panel)}")

    splits = pd.read_parquet(SPLITS)
    splits["report_date"] = pd.to_datetime(splits["report_date"])
    sf, sp = split_factor_fn(splits)

    # month-end closes from the daily series (last trading day of each month)
    m_close = daily.resample("ME").last()
    month_index = pd.DatetimeIndex(sorted(panel["month_end"].unique()))
    m_close = m_close.reindex(month_index)

    # ---- A version -------------------------------------------------------
    panel["sf_a"] = [sf(t, f) for t, f in zip(panel["ticker"],
                                              panel["diluted_shares_filed"])]
    panel["shares_a"] = panel["diluted_shares"] * panel["sf_a"]

    # ---- B version -------------------------------------------------------
    cik_of = panel.groupby("ticker")["cik"].first().to_dict()
    months_np = month_index.to_numpy()
    b_frames, b_missing = [], []
    for t in universe:
        dei = load_dei(cik_of[t])
        if dei is None or dei.empty:
            b_missing.append(t)
            continue
        e_arr, f_arr = dei["end"].to_numpy(), dei["filed"].to_numpy()
        v_arr = dei["val"].to_numpy()
        pick = pit_pick(months_np, e_arr, f_arr)
        # split basis: the factor uses the filed date of the record actually picked
        adj = [v_arr[j] * sf(t, pd.Timestamp(f_arr[j])) if j >= 0 else np.nan
               for j in pick]
        b_frames.append(pd.DataFrame({"ticker": t, "month_end": month_index,
                                      "shares_b": adj}))
    print(f"B version: {len(b_frames)} tickers, {len(b_missing)} without the dei tag")
    bdf = pd.concat(b_frames, ignore_index=True) if b_frames else pd.DataFrame()
    panel = panel.merge(bdf, on=["ticker", "month_end"], how="left")

    # ---- scale guard -----------------------------------------------------
    rep_a = drop_a = rep_b = drop_b = 0
    parts = []
    for t, g in panel.groupby("ticker", sort=False):
        g = g.sort_values("month_end").copy()
        a, r1, d1 = scale_guard(g["shares_a"].to_numpy(dtype=float))
        b, r2, d2 = scale_guard(g["shares_b"].to_numpy(dtype=float))
        g["shares_a"], g["shares_b"] = a, b
        rep_a += r1; drop_a += d1; rep_b += r2; drop_b += d2
        parts.append(g)
    panel = pd.concat(parts, ignore_index=True)
    print(f"scale guard A repaired {rep_a} dropped {drop_a} | "
          f"B repaired {rep_b} dropped {drop_b}")

    # ---- 12-month change -------------------------------------------------
    prev = panel[["ticker", "month_end", "shares_a", "shares_b"]].copy()
    prev["month_end"] = (prev["month_end"] + pd.offsets.DateOffset(years=1)
                         + pd.offsets.MonthEnd(0))
    prev = prev.rename(columns={"shares_a": "shares_a_prev", "shares_b": "shares_b_prev"})
    panel = panel.merge(prev, on=["ticker", "month_end"], how="left")

    flags = []
    for ver in ("a", "b"):
        s, p = panel[f"shares_{ver}"], panel[f"shares_{ver}_prev"]
        r12 = np.where((p > 0) & (s > 0), s / p - 1.0, np.nan)
        panel[f"r12_{ver}"] = r12
        big = np.isfinite(r12) & (np.abs(r12) >= BIG_MOVE)
        keep = np.ones(len(panel), dtype=bool)
        idx = np.flatnonzero(big)
        for i in idx:
            row = panel.iloc[i]
            hi = row["month_end"]
            lo = hi - pd.offsets.DateOffset(years=1)
            ratio = splits_in_window(sp, row["ticker"], lo, hi)
            is_split = abs(ratio - 1.0) > 1e-9
            if is_split:
                keep[i] = False
            flags.append({"version": ver, "ticker": row["ticker"],
                          "month_end": hi.date().isoformat(),
                          "r12": round(float(row[f"r12_{ver}"]), 4),
                          "split_ratio_in_window": round(float(ratio), 4),
                          "verdict": "確認拆股,設缺值" if is_split else "保留(真實大額變動)"})
        panel[f"shrink_{ver}"] = np.where(keep, -panel[f"r12_{ver}"], np.nan)
        panel[f"big_move_{ver}"] = big & keep      # kept but flagged

    # ---- price cross-check: confirmed splits leave no jump in adjusted price
    checks = []
    for sym, g in splits.groupby("symbol"):
        if sym not in daily.columns:
            continue
        s = daily[sym].dropna()
        for d, r in zip(g["report_date"], g["ratio"]):
            i = s.index.searchsorted(d)
            if i < 2 or i >= len(s) - 1:
                continue
            move = abs(s.iloc[i] / s.iloc[i - 1] - 1.0)
            checks.append({"symbol": sym, "date": pd.Timestamp(d).date().isoformat(),
                           "ratio": float(r), "abs_move": round(float(move), 4)})
    chk = pd.DataFrame(checks)
    price_jump_rate = float((chk["abs_move"] > 0.25).mean()) if len(chk) else float("nan")

    # ---- eligible pool ---------------------------------------------------
    px = m_close.stack().rename("px").reset_index()
    px.columns = ["month_end", "ticker", "px"]
    panel = panel.merge(px, on=["month_end", "ticker"], how="left")
    panel["mcap"] = panel["shares_a"] * panel["px"]
    panel["profit"] = np.where(panel["assets"] > 0, panel["cfo_ttm"] / panel["assets"],
                               np.nan)

    sig = panel[(panel["month_end"] >= FIRST_SIGNAL) & (panel["month_end"] <= LAST_SIGNAL)
                & panel["in_index"] & panel["px"].notna() & (panel["px"] > 0)].copy()
    sig = sig[["month_end", "ticker", "shrink_a", "shrink_b", "big_move_a", "big_move_b",
               "mcap", "profit", "px"]]
    sig.to_parquet(DATA / "signals.parquet", index=False)

    n_a = int(sig["shrink_a"].notna().sum())
    n_b = int(sig["shrink_b"].notna().sum())
    fl = pd.DataFrame(flags)
    fl.to_csv(OUT / "flagged_big_moves.csv", index=False, encoding="utf-8")

    meta = {
        "宇宙": {"面板家數": 718, "有價代號": len(tradable), "交集": len(universe)},
        "訊號月": {"首": FIRST_SIGNAL.date().isoformat(),
                   "末": LAST_SIGNAL.date().isoformat(),
                   "月數": int(sig["month_end"].nunique())},
        "合資格格數": {"A版": n_a, "B版": n_b,
                       "池內每月人數中位": float(sig.groupby("month_end").size().median())},
        "B版缺 dei 標籤的代號數": len(b_missing),
        "B版缺標籤名單": b_missing[:50],
        "拆股基準對齊": {"事件表宗數": int(len(splits)),
                         "涵蓋代號": int(splits["symbol"].nunique())},
        "單位刻度守衛": {"A版修復": rep_a, "A版設缺值": drop_a,
                         "B版修復": rep_b, "B版設缺值": drop_b},
        "疑似拆股(|r12|>=40%)": {
            "A版標記": int((fl["version"] == "a").sum()) if len(fl) else 0,
            "A版確認拆股剔除": int(((fl["version"] == "a") &
                                    (fl["verdict"].str.startswith("確認"))).sum()) if len(fl) else 0,
            "A版保留為真實變動": int(((fl["version"] == "a") &
                                      (fl["verdict"].str.startswith("保留"))).sum()) if len(fl) else 0,
            "B版標記": int((fl["version"] == "b").sum()) if len(fl) else 0,
            "B版確認拆股剔除": int(((fl["version"] == "b") &
                                    (fl["verdict"].str.startswith("確認"))).sum()) if len(fl) else 0,
            "B版保留為真實變動": int(((fl["version"] == "b") &
                                      (fl["verdict"].str.startswith("保留"))).sum()) if len(fl) else 0,
        },
        "價格反向核對": {
            "核到的拆股事件": int(len(chk)),
            "在已調整價格上出現>25%跳動的比例": price_jump_rate,
            "說明": "比例接近零 = 價格序列確實已調整拆股,票面的價格比例法在此資料上量不到東西",
        },
    }
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
