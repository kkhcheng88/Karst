"""KARST-119 量度:三條判準 × 五次熊 + 債券中間級。

判準文本已於 commit 0a6ac10 寫死(research/2026-08-31-板塊安全判準與債券中間級.md
第一節),本腳本只執行該文本,不改任何參數。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]

SMA_MONTHS = 10          # 判準甲:10 個月線
FLOW_LOOKBACK = 13       # 判準乙:13 週變化
FLOW_WINDOW = 156        # 判準乙:156 週滾動窗口
FLOW_MIN_OBS = 104       # 判準乙:最低 104 週熱身
FLOW_PCTILE = 20.0       # 判準乙:百分位 <= 20
KNOW_LAG_DAYS = 10       # 判準乙:知情時點 = 截數日 + 10 個曆日
COST_FULL = 0.0010       # 每次完全換馬 10 個基點

BEARS = {
    "2000–02": ("2000-04", "2002-10"),
    "2008": ("2007-11", "2009-03"),
    "2018Q4": ("2018-10", "2018-12"),
    "2020": ("2020-03", "2020-03"),
    "2022": ("2022-02", "2022-10"),
}


# ---------------------------------------------------------------- 資料整備

def load_prices() -> pd.DataFrame:
    px = pd.read_parquet(HERE / "prices_daily.parquet")
    px["date"] = pd.to_datetime(px["date"])
    return px


def build_month_frame(px: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """回傳(月度面板, 日度開市價寬表)。

    月度面板一行一個持有月:開市價(該月第一個交易日開價)、上月末收市價。
    """
    opens = px.pivot(index="date", columns="ticker", values="open").sort_index()
    closes = px.pivot(index="date", columns="ticker", values="close").sort_index()

    # 主日曆:SPY
    cal = opens.index[opens["SPY"].notna()]
    opens = opens.loc[cal]
    closes = closes.loc[cal]

    period = cal.to_period("M")
    first_day = pd.Series(cal, index=period).groupby(level=0).first()
    last_day = pd.Series(cal, index=period).groupby(level=0).last()

    month_open = opens.loc[first_day.values]
    month_open.index = first_day.index
    month_close = closes.loc[last_day.values]
    month_close.index = last_day.index

    return (
        pd.DataFrame({"first_day": first_day, "last_day": last_day}),
        {"month_open": month_open, "month_close": month_close,
         "daily_open": opens},
    )


# ---------------------------------------------------------------- 判準甲

def trend_leg(month_close: pd.DataFrame, months: pd.PeriodIndex) -> pd.DataFrame:
    """對每個持有月,用上一個月末收市價與 10 個月線判九隻板塊的安全數。"""
    sec = month_close[SECTORS]
    sma = sec.rolling(SMA_MONTHS, min_periods=SMA_MONTHS).mean()
    safe = (sec > sma)
    valid = sma.notna().all(axis=1) & sec.notna().all(axis=1)
    safe_count = safe.sum(axis=1).where(valid)

    # 決策在上一個月末 -> 用於下一個持有月
    shifted = safe_count.shift(1)
    return pd.DataFrame({"safe_count": shifted.reindex(months)})


# ---------------------------------------------------------------- 判準乙

def flow_leg(decision_dates: pd.Series) -> pd.DataFrame:
    cot = pd.read_parquet(HERE / "cftc_tff_es.parquet").sort_values("report_date")
    cot["report_date"] = pd.to_datetime(cot["report_date"])
    net = (
        cot["asset_mgr_positions_long"] - cot["asset_mgr_positions_short"]
    ) / cot["open_interest_all"] * 100.0
    cot = cot.assign(np_pct=net.values)
    cot["d_np"] = cot["np_pct"] - cot["np_pct"].shift(FLOW_LOOKBACK)

    # 滾動百分位(含當期),窗口 156,最少 104 個 ΔNP 讀數
    vals = cot["d_np"].to_numpy()
    pct = np.full(len(vals), np.nan)
    for i in range(len(vals)):
        if np.isnan(vals[i]):
            continue
        lo = max(0, i - FLOW_WINDOW + 1)
        win = vals[lo : i + 1]
        win = win[~np.isnan(win)]
        if len(win) < FLOW_MIN_OBS:
            continue
        pct[i] = 100.0 * (win <= vals[i]).sum() / len(win)
    cot["d_np_pctile"] = pct
    cot["known_from"] = cot["report_date"] + pd.Timedelta(days=KNOW_LAG_DAYS)

    usable = cot.dropna(subset=["d_np_pctile"]).reset_index(drop=True)

    out = []
    for period, dec_date in decision_dates.items():
        elig = usable[usable["known_from"] <= dec_date]
        if elig.empty:
            out.append((period, np.nan, np.nan, pd.NaT))
            continue
        row = elig.iloc[-1]
        out.append(
            (period, row["d_np_pctile"], row["d_np"], row["report_date"])
        )
    frame = pd.DataFrame(
        out, columns=["month", "d_np_pctile", "d_np", "cot_report_date"]
    ).set_index("month")
    return frame, cot


# ---------------------------------------------------------------- 階梯回測

def month_returns(month_open: pd.DataFrame, months: pd.PeriodIndex,
                  ticker: str) -> pd.Series:
    """持有月的開對開回報。"""
    series = month_open[ticker]
    nxt = series.shift(-1)
    ret = (nxt / series - 1.0).reindex(months)
    return ret


def daily_equity(daily_open: pd.DataFrame, holdings: pd.Series,
                 cost_full: float) -> pd.Series:
    """由每日開對開回報砌淨值;持倉每月第一個交易日的開市價換馬。"""
    dates = daily_open.index
    period = dates.to_period("M")
    holdings = holdings.dropna()
    valid_months = set(holdings.index)

    mask = np.array([p in valid_months for p in period])
    dates = dates[mask]
    period = period[mask]
    if len(dates) == 0:
        return pd.Series(dtype=float)

    equity = [1.0]
    prev_hold = None
    idx = [dates[0]]
    for i in range(len(dates) - 1):
        d, d_next = dates[i], dates[i + 1]
        hold = holdings.loc[period[i]]
        val = equity[-1]
        if hold != prev_hold:
            val *= (1.0 - (cost_full if prev_hold is not None else cost_full / 2))
            prev_hold = hold
        if hold == "USD":
            r = 0.0
        else:
            o0 = daily_open.at[d, hold]
            o1 = daily_open.at[d_next, hold]
            r = o1 / o0 - 1.0 if (o0 and o1 and not np.isnan(o0) and not np.isnan(o1)) else 0.0
        equity.append(val * (1.0 + r))
        idx.append(d_next)
    return pd.Series(equity, index=pd.DatetimeIndex(idx))


def stats(curve: pd.Series) -> dict:
    if len(curve) < 2:
        return {"annual": float("nan"), "maxdd": float("nan"), "total": float("nan")}
    years = (len(curve) - 1) / 252.0
    total = curve.iloc[-1] / curve.iloc[0] - 1.0
    annual = (curve.iloc[-1] / curve.iloc[0]) ** (1.0 / years) - 1.0
    dd = curve / curve.cummax() - 1.0
    return {"annual": annual * 100, "maxdd": dd.min() * 100, "total": total * 100}


# ---------------------------------------------------------------- 主流程

def main() -> None:
    px = load_prices()
    frame, panels = build_month_frame(px)
    month_open = panels["month_open"]
    month_close = panels["month_close"]
    daily_open = panels["daily_open"]

    # 完整持有月:由 1999-01 起,最後一個要有下一個月的開價
    all_months = month_open.index
    months = all_months[(all_months >= pd.Period("1999-01")) & (all_months <= all_months[-2])]

    spy_ret = month_returns(month_open, months, "SPY")
    ief_ret = month_returns(month_open, months, "IEF")
    sec_ret = pd.DataFrame(
        {t: month_returns(month_open, months, t) for t in SECTORS}
    )
    best_sec = sec_ret.max(axis=1)

    trend = trend_leg(month_close, months)
    decision_dates = frame["last_day"].shift(1).reindex(months).dropna()
    flow, cot = flow_leg(decision_dates)
    flow = flow.reindex(months)

    panel = pd.DataFrame(
        {
            "spy_ret": spy_ret,
            "best_sector_ret": best_sec,
            "ief_ret": ief_ret,
            "safe_count": trend["safe_count"],
            "d_np_pctile": flow["d_np_pctile"],
            "d_np": flow["d_np"],
            "cot_report_date": flow["cot_report_date"],
        }
    )

    # 三條判準的訊號(NaN = 無數據)
    leg_a = panel["safe_count"].apply(lambda v: np.nan if pd.isna(v) else float(v == 0))
    leg_a1 = panel["safe_count"].apply(lambda v: np.nan if pd.isna(v) else float(v <= 1))
    leg_b = panel["d_np_pctile"].apply(
        lambda v: np.nan if pd.isna(v) else float(v <= FLOW_PCTILE)
    )
    leg_c = pd.Series(
        [
            np.nan if (pd.isna(a) or pd.isna(b)) else float(a > 0 and b > 0)
            for a, b in zip(leg_a, leg_b)
        ],
        index=panel.index,
    )
    panel["sig_A"] = leg_a
    panel["sig_A1"] = leg_a1
    panel["sig_B"] = leg_b
    panel["sig_C"] = leg_c

    # IEF 自身 10 個月線(用於三級-乙)
    ief_close = month_close["IEF"]
    ief_sma = ief_close.rolling(SMA_MONTHS, min_periods=SMA_MONTHS).mean()
    ief_safe = (ief_close > ief_sma).where(ief_sma.notna() & ief_close.notna())
    panel["ief_safe"] = ief_safe.shift(1).reindex(months)

    panel.to_csv(HERE / "monthly_panel.csv")

    results: dict = {"generated": str(pd.Timestamp.now())}

    # ---- 基礎率與打和線
    up = panel.loc[panel["spy_ret"] > 0, "spy_ret"].mean()
    dn = -panel.loc[panel["spy_ret"] < 0, "spy_ret"].mean()
    base_rate = float((panel["spy_ret"] < 0).mean() * 100)
    breakeven = float(up / (up + dn) * 100)
    up_b = panel.loc[panel["best_sector_ret"] > 0, "best_sector_ret"].mean()
    dn_b = -panel.loc[panel["best_sector_ret"] < 0, "best_sector_ret"].mean()
    results["base"] = {
        "months": int(len(panel)),
        "first_month": str(panel.index[0]),
        "last_month": str(panel.index[-1]),
        "spy_down_rate_pct": base_rate,
        "spy_mean_up_pct": float(up * 100),
        "spy_mean_down_pct": float(-dn * 100),
        "breakeven_precision_pct": breakeven,
        "bestsec_down_rate_pct": float((panel["best_sector_ret"] < 0).mean() * 100),
        "bestsec_breakeven_precision_pct": float(up_b / (up_b + dn_b) * 100),
    }

    # ---- 逐判準統計
    def score(sig: pd.Series, truth: pd.Series, subset: pd.Index | None = None) -> dict:
        s = sig if subset is None else sig.loc[subset]
        t = truth if subset is None else truth.loc[subset]
        have = s.notna()
        s, t = s[have], t[have]
        fires = s > 0
        hit = int((fires & t).sum())
        fp = int((fires & ~t).sum())
        miss = int((~fires & t).sum())
        tn = int((~fires & ~t).sum())
        n = len(s)
        prec = 100.0 * hit / (hit + fp) if (hit + fp) else float("nan")
        rec = 100.0 * hit / (hit + miss) if (hit + miss) else float("nan")
        mean_spy_when_fire = float(
            panel.loc[s.index[fires], "spy_ret"].mean() * 100
        ) if fires.any() else float("nan")
        return {
            "n_months_with_data": n,
            "n_months_no_data": int((~have).sum()),
            "fires": int(fires.sum()),
            "hit": hit, "false_alarm": fp, "miss": miss, "true_negative": tn,
            "precision_pct": prec, "recall_pct": rec,
            "fire_rate_pct": 100.0 * fires.sum() / n if n else float("nan"),
            "mean_spy_ret_when_fire_pct": mean_spy_when_fire,
        }

    truth_a = panel["spy_ret"] < 0
    truth_b = panel["best_sector_ret"] < 0

    bear_index = {}
    for name, (a, b) in BEARS.items():
        idx = panel.index[(panel.index >= pd.Period(a)) & (panel.index <= pd.Period(b))]
        bear_index[name] = idx
    all_bear = panel.index[np.zeros(len(panel), dtype=bool)]
    mask = pd.Series(False, index=panel.index)
    for idx in bear_index.values():
        mask.loc[idx] = True
    non_bear = panel.index[~mask.to_numpy()]

    results["criteria"] = {}
    for label, sig in [("A", leg_a), ("A1", leg_a1), ("B", leg_b), ("C", leg_c)]:
        entry = {
            "full_truthA": score(sig, truth_a),
            "full_truthB": score(sig, truth_b),
            "non_bear_truthA": score(sig, truth_a, non_bear),
            "bears": {n: score(sig, truth_a, idx) for n, idx in bear_index.items()},
            "first_signal_month": str(sig.dropna().index[0]) if sig.notna().any() else None,
            "fire_months": [str(m) for m in sig.index[sig > 0]],
        }
        results["criteria"][label] = entry

    # ---- 階梯回測
    def ladder(sig: pd.Series, mode: str) -> pd.Series:
        hold = []
        for m in panel.index:
            v = sig.loc[m]
            if pd.isna(v) or v == 0:
                hold.append("SPY")
            else:
                if mode == "two":
                    hold.append("USD")
                elif mode == "three_a":
                    hold.append("IEF" if not pd.isna(panel.at[m, "ief_ret"]) else "USD")
                else:  # three_b
                    safe = panel.at[m, "ief_safe"]
                    if pd.isna(panel.at[m, "ief_ret"]) or pd.isna(safe) or not safe:
                        hold.append("USD")
                    else:
                        hold.append("IEF")
        return pd.Series(hold, index=panel.index)

    def run_curve(hold: pd.Series, months_idx: pd.Index, cost: float = COST_FULL):
        return daily_equity(daily_open, hold.loc[months_idx], cost)

    results["ladders"] = {}
    for label, sig in [("A", leg_a), ("B", leg_b), ("C", leg_c)]:
        avail = sig.dropna().index
        common = avail
        entry = {"window": [str(common[0]), str(common[-1])], "months": len(common)}
        spy_hold = pd.Series("SPY", index=panel.index)
        entry["buyhold_SPY"] = stats(run_curve(spy_hold, common))
        for mode in ("two", "three_a", "three_b"):
            entry[mode] = stats(run_curve(ladder(sig, mode), common))
        # 成本敏感度(只跑兩級)
        entry["two_cost0"] = stats(run_curve(ladder(sig, "two"), common, 0.0))
        entry["two_cost25"] = stats(run_curve(ladder(sig, "two"), common, 0.0025))
        # 逐熊
        entry["bears"] = {}
        for name, idx in bear_index.items():
            idx2 = idx.intersection(common)
            if len(idx2) == 0:
                entry["bears"][name] = {"note": "無數據(判準覆蓋不到)"}
                continue
            b = {"months": len(idx2), "covered": [str(idx2[0]), str(idx2[-1])],
                 "full_window": len(idx) == len(idx2)}
            b["buyhold_SPY"] = stats(run_curve(spy_hold, idx2))
            for mode in ("two", "three_a", "three_b"):
                b[mode] = stats(run_curve(ladder(sig, mode), idx2))
            entry["bears"][name] = b
        results["ladders"][label] = entry

    # ---- 五次熊的基礎事實(不涉判準)
    results["bear_facts"] = {}
    for name, idx in bear_index.items():
        spy_hold = pd.Series("SPY", index=panel.index)
        ief_hold = pd.Series("IEF", index=panel.index)
        f = {
            "months": len(idx),
            "window": [str(idx[0]), str(idx[-1])],
            "SPY": stats(run_curve(spy_hold, idx)),
        }
        if panel.loc[idx, "ief_ret"].notna().all():
            f["IEF"] = stats(run_curve(ief_hold, idx))
        else:
            f["IEF"] = {"note": "IEF 2002-07 上市,本段無數據,不合成"}
        f["best_sector_hold_pct"] = float(
            (panel.loc[idx, [c for c in SECTORS]].add(1).prod().max() - 1) * 100
        ) if False else None
        results["bear_facts"][name] = f

    # 逐熊「整段揸住一隻」板塊表現(對照 KARST-113)
    for name, idx in bear_index.items():
        seg = sec_ret.loc[idx]
        cum = (1 + seg).prod() - 1
        results["bear_facts"][name]["sector_hold_returns_pct"] = {
            k: float(v * 100) for k, v in cum.sort_values(ascending=False).items()
        }

    with open(HERE / "results.json", "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2, default=str)

    print(json.dumps(results["base"], ensure_ascii=False, indent=2))
    for label in ("A", "A1", "B", "C"):
        c = results["criteria"][label]
        print(f"\n=== 判準 {label} 首個訊號月 {c['first_signal_month']} ===")
        print("全樣本(真值甲 SPY):", json.dumps(c["full_truthA"], ensure_ascii=False))
        print("熊市外(真值甲):", json.dumps(c["non_bear_truthA"], ensure_ascii=False))
        for n, s in c["bears"].items():
            print(f"  {n}: {json.dumps(s, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
