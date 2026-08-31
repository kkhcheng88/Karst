"""KARST-122 量度:恐慌極端重定位(風險開之內的加注/入場時機)。

判準文本連全部參數在提交 ef4fc5d 寫死(research/2026-08-31-恐慌極端重定位.md 第一節),
本腳本只是執行它——沒有搜尋訊號、沒有擬合規則、沒有跑過任何參數掃描。

數據沿用 KARST-120 已抓的同一批日線(../2026-08-31-fear-greed/prices_daily.parquet)。
輸出:results.json(全部結果數字)、signals.csv(逐次訊號明細)。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PRICES = HERE.parent / "2026-08-31-fear-greed" / "prices_daily.parquet"
SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
SPY = "SPY"

# ── 第一節寫死的參數(提交 ef4fc5d),一格不准改 ──────────────────────
SMA_MONTHS = 10        # 風險開:SPY 月末收市 ≥ 最近 10 個月末收市簡單平均
PCT_WIN = 504          # 恐慌讀數:RSI(2) 的 504 個交易日滾動百分位
RSI_N = 2              # 只用 RSI(2)
LEADER_WIN = 63        # 領漲板塊:過去 63 個交易日累計回報最高
COOLDOWN = 10          # 事件去重:10 個交易日冷靜期
MAIN_WIN = 63          # 主評分窗(一季)
SUB_WIN = 21           # 副評分窗(一月)
WINDOWS = [MAIN_WIN, SUB_WIN]
P1_SPY_PCT = 2.0       # 主組:SPY 恐慌讀數 ≤ 2.0 百分位
P1_SPREAD_PCT = 10.0   # 主組:蔓延門檻 ≤ 10.0 百分位
P1_SPREAD_N = 7        # 主組:蔓延數目 ≥ 7 / 9
P2_LEADER_PCT = 2.0    # 副組:領漲板塊恐慌讀數 ≤ 2.0 百分位
EDGE_PP = 1.00         # 值博關 3a:超額 ≥ 1.00 個百分點
EDGE_SE_MULT = 2.0     # 值博關 3b:超額 ≥ 2 倍自身標準誤

BEARS = [
    ("2000-02", "2000-04-01", "2002-10-31"),
    ("2008", "2007-11-01", "2009-03-31"),
    ("2018Q4", "2018-10-01", "2018-12-31"),
    ("2020", "2020-03-01", "2020-03-31"),
    ("2022", "2022-02-01", "2022-10-31"),
]


def wilder_rsi(close: np.ndarray, n: int) -> np.ndarray:
    """Wilder RSI,alpha = 1/n,首個讀數需 n+1 個交易日。(與 KARST-120 同一函式)"""
    m = len(close)
    out = np.full(m, np.nan)
    if m <= n:
        return out
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_g = gain[:n].mean()
    avg_l = loss[:n].mean()
    out[n] = 100.0 if avg_l == 0 else 100.0 - 100.0 / (1.0 + avg_g / avg_l)
    for i in range(n, m - 1):
        avg_g = (avg_g * (n - 1) + gain[i]) / n
        avg_l = (avg_l * (n - 1) + loss[i]) / n
        if avg_l == 0:
            out[i + 1] = 100.0
        elif avg_g == 0:
            out[i + 1] = 0.0
        else:
            out[i + 1] = 100.0 - 100.0 / (1.0 + avg_g / avg_l)
    return out


def rolling_pct_rank(x: np.ndarray, win: int) -> np.ndarray:
    """當日讀數在最近 win 個交易日讀數之中的百分位(含當日),只用當日及之前,無前視。"""
    m = len(x)
    out = np.full(m, np.nan)
    for i in range(m):
        j = i - win + 1
        if j < 0:
            continue
        w = x[j:i + 1]
        if np.isnan(w).any():
            continue
        out[i] = (w <= x[i]).sum() / win * 100.0
    return out


def dedup(idx: np.ndarray) -> list[int]:
    """同型訊號連續成立只計首日,一次事件後 10 個交易日冷靜期。"""
    events: list[int] = []
    last = -10 ** 9
    for i in idx:
        if i - last > COOLDOWN:
            events.append(int(i))
            last = int(i)
    return events


def stats(arr: np.ndarray) -> dict:
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return {"n": 0}
    up = arr[arr > 0]
    dn = arr[arr < 0]
    u = float(up.mean()) if len(up) else 0.0
    d = float(-dn.mean()) if len(dn) else 0.0
    return {
        "n": int(len(arr)),
        "mean_pct": round(float(arr.mean()) * 100, 4),
        "median_pct": round(float(np.median(arr)) * 100, 4),
        "sd_pct": round(float(arr.std(ddof=1)) * 100, 4) if len(arr) > 1 else None,
        "se_pct": round(float(arr.std(ddof=1)) / np.sqrt(len(arr)) * 100, 4) if len(arr) > 1 else None,
        "up_share": round(float((arr > 0).mean()), 4),
        "down_share": round(float((arr < 0).mean()), 4),
        "avg_up_pct": round(u * 100, 4),
        "avg_down_pct": round(d * 100, 4),
        "breakeven_precision": round(u / (u + d), 4) if (u + d) > 0 else None,
    }


def main() -> int:
    px = pd.read_parquet(PRICES)
    close = px.pivot(index="date", columns="ticker", values="close")
    opn = px.pivot(index="date", columns="ticker", values="open")
    cols = SECTORS + [SPY]
    close = close[cols].dropna()
    opn = opn.loc[close.index, cols]
    dates = close.index
    m = len(dates)

    # ── 恐慌讀數:RSI(2) 的 504 日滾動百分位 ──────────────────────────
    rsi2 = pd.DataFrame({t: wilder_rsi(close[t].to_numpy(), RSI_N) for t in cols}, index=dates)
    pct = pd.DataFrame({t: rolling_pct_rank(rsi2[t].to_numpy(), PCT_WIN) for t in cols}, index=dates)

    # ── 領漲板塊 ────────────────────────────────────────────────────
    ret63 = close[SECTORS] / close[SECTORS].shift(LEADER_WIN) - 1.0
    leader_ok = ret63.notna().all(axis=1)
    leader = pd.Series(index=dates, dtype=object)
    leader.loc[leader_ok] = ret63.loc[leader_ok].idxmax(axis=1)

    # ── 風險開:SPY 月末收市 ≥ 最近 10 個月末收市簡單平均,決定其後一個月 ──
    me_idx = pd.Series(np.arange(m), index=dates).groupby([dates.year, dates.month]).last()
    me_pos = me_idx.to_numpy()
    me_close = close[SPY].to_numpy()[me_pos]
    me_sma = pd.Series(me_close).rolling(SMA_MONTHS).mean().to_numpy()
    me_on = me_close >= me_sma  # NaN 比較為 False,即熱身期算作未定
    me_valid = ~np.isnan(me_sma)

    risk_on = np.zeros(m, dtype=bool)
    risk_defined = np.zeros(m, dtype=bool)
    for k in range(len(me_pos)):
        if not me_valid[k]:
            continue
        start = me_pos[k] + 1
        end = me_pos[k + 1] if k + 1 < len(me_pos) else m - 1
        if start > end:
            continue
        risk_defined[start:end + 1] = True
        risk_on[start:end + 1] = bool(me_on[k])

    # ── 有效期:百分位齊 + 領漲板塊算得出 + 風險開狀態已定 ──────────────
    valid = (
        leader_ok.to_numpy()
        & pct[cols].notna().all(axis=1).to_numpy()
        & risk_defined
    )
    valid_idx = np.where(valid)[0]
    first_valid = int(valid_idx[0])

    # ── 前瞻回報:T+1 開市 → T+1+N 開市 ─────────────────────────────
    def fwd(ticker_per_day, N: int) -> np.ndarray:
        out = np.full(m, np.nan)
        for i in range(m):
            j, k = i + 1, i + 1 + N
            if k >= m:
                break
            t = ticker_per_day[i]
            if t is None or (isinstance(t, float) and np.isnan(t)):
                continue
            e, x = opn[t].iloc[j], opn[t].iloc[k]
            if np.isfinite(e) and np.isfinite(x) and e > 0:
                out[i] = x / e - 1.0
        return out

    spy_series = [SPY] * m
    leader_series = [leader.iloc[i] if leader_ok.iloc[i] else None for i in range(m)]
    fwd_spy = {N: fwd(spy_series, N) for N in WINDOWS}
    fwd_leader = {N: fwd(leader_series, N) for N in WINDOWS}

    # ── 訊號 ────────────────────────────────────────────────────────
    pct_s = pct[SECTORS]
    lead_pct = np.array([pct.iloc[i][leader.iloc[i]] if leader_ok.iloc[i] else np.nan for i in range(m)])
    spy_pct = pct[SPY].to_numpy()
    n_cold = (pct_s <= P1_SPREAD_PCT).sum(axis=1).to_numpy()

    raw = {
        "P1": valid & (spy_pct <= P1_SPY_PCT) & (n_cold >= P1_SPREAD_N),
        "P2": valid & (lead_pct <= P2_LEADER_PCT),
    }
    events = {k: dedup(np.where(v)[0]) for k, v in raw.items()}

    # ── 熊市窗口 ────────────────────────────────────────────────────
    bear_masks = {name: (dates >= pd.Timestamp(a)) & (dates <= pd.Timestamp(b)) for name, a, b in BEARS}
    any_bear = np.zeros(m, dtype=bool)
    for mk in bear_masks.values():
        any_bear |= mk

    # ── 四個母體 ────────────────────────────────────────────────────
    universes = {
        "main_riskon_exbear": valid & risk_on & ~any_bear,   # 主成績
        "riskon_inbear": valid & risk_on & any_bear,          # 熊內,分開列
        "riskon_all": valid & risk_on,                        # 參考
        "riskoff": valid & ~risk_on,                          # 風險關,對照
        "all": valid,                                         # 全樣本
    }

    base_rates = {}
    for uname, umask in universes.items():
        base_rates[uname] = {}
        for N in WINDOWS:
            ok = umask & ~np.isnan(fwd_spy[N])
            base_rates[uname][f"SPY_{N}"] = stats(fwd_spy[N][ok])
            okl = umask & ~np.isnan(fwd_leader[N])
            base_rates[uname][f"LEADER_{N}"] = stats(fwd_leader[N][okl])

    def score(key: str, target: str, umask: np.ndarray) -> dict:
        f_by_win = fwd_spy if target == "SPY" else fwd_leader
        ev = [i for i in events[key] if umask[i]]
        rec: dict = {"signal_count": len(ev),
                     "dates": [dates[i].strftime("%Y-%m-%d") for i in ev]}
        for N in WINDOWS:
            f = f_by_win[N]
            vals = np.array([f[i] for i in ev if not np.isnan(f[i])])
            rec[f"win{N}"] = stats(vals)
            rec[f"win{N}"]["scored_count"] = int(len(vals))
        return rec

    results_by_universe = {}
    for uname, umask in universes.items():
        results_by_universe[uname] = {
            "P1": score("P1", "SPY", umask),
            "P2": score("P2", "LEADER", umask),
        }

    # ── 及格判定:主成績母體、主評分窗 63 日 ────────────────────────
    U = "main_riskon_exbear"
    verdicts = {}
    for key, tgt in (("P1", "SPY"), ("P2", "LEADER")):
        r = results_by_universe[U][key][f"win{MAIN_WIN}"]
        b = base_rates[U][f"{tgt}_{MAIN_WIN}"]
        if r.get("n", 0) == 0:
            verdicts[key] = {"pass": False, "note": "主成績母體之內無訊號"}
            continue
        g1 = r["mean_pct"] > 0
        g2 = r["up_share"] > b["up_share"]
        edge = round(r["mean_pct"] - b["mean_pct"], 4)
        se = float(np.sqrt((r["se_pct"] or 0) ** 2 + (b["se_pct"] or 0) ** 2))
        g3a = edge >= EDGE_PP
        g3b = edge >= EDGE_SE_MULT * se
        verdicts[key] = {
            "target": tgt,
            "signal_count": r["n"],
            "gate1_profitable": bool(g1), "gate1_mean_pct": r["mean_pct"],
            "gate2_informative": bool(g2), "precision": r["up_share"], "base_up_share": b["up_share"],
            "edge_pp": edge, "edge_se_pp": round(se, 4),
            "gate3a_edge_ge_1pp": bool(g3a),
            "gate3b_edge_ge_2se": bool(g3b), "needed_2se_pp": round(EDGE_SE_MULT * se, 4),
            "gate3_double_hurdle": bool(g3a and g3b),
            "pass": bool(g1 and g2 and g3a and g3b),
        }

    # ── 五熊逐次 ────────────────────────────────────────────────────
    bears_detail = {}
    for name, mk in bear_masks.items():
        d = {}
        for key, tgt in (("P1", "SPY"), ("P2", "LEADER")):
            f = fwd_spy[MAIN_WIN] if tgt == "SPY" else fwd_leader[MAIN_WIN]
            hits = [i for i in events[key] if mk[i] and valid[i]]
            vals = np.array([f[i] for i in hits if not np.isnan(f[i])])
            d[key] = {
                "count": len(hits),
                "riskon_count": int(sum(1 for i in hits if risk_on[i])),
                "items": [{"date": dates[i].strftime("%Y-%m-%d"),
                           "risk_on": bool(risk_on[i]),
                           "leader": str(leader.iloc[i]),
                           "fwd63_pct": round(float(f[i]) * 100, 2) if not np.isnan(f[i]) else None}
                          for i in hits],
                "fwd63_mean_pct": round(float(vals.mean()) * 100, 4) if len(vals) else None,
            }
        bears_detail[name] = d

    res = {
        "meta": {
            "criteria_commit": "ef4fc5d",
            "prices_from": "KARST-120 experiments/2026-08-31-fear-greed/prices_daily.parquet",
            "first_date": dates[0].strftime("%Y-%m-%d"),
            "last_date": dates[-1].strftime("%Y-%m-%d"),
            "trading_days": int(m),
            "first_valid_signal_date": dates[first_valid].strftime("%Y-%m-%d"),
            "valid_days": int(valid.sum()),
            "riskon_days": int((valid & risk_on).sum()),
            "riskoff_days": int((valid & ~risk_on).sum()),
            "main_universe_days": int(universes["main_riskon_exbear"].sum()),
            "params": {
                "sma_months": SMA_MONTHS, "pct_win": PCT_WIN, "rsi_n": RSI_N,
                "leader_win": LEADER_WIN, "cooldown": COOLDOWN,
                "main_win": MAIN_WIN, "sub_win": SUB_WIN,
                "P1": [P1_SPY_PCT, P1_SPREAD_PCT, P1_SPREAD_N],
                "P2": [P2_LEADER_PCT],
                "edge_pp": EDGE_PP, "edge_se_mult": EDGE_SE_MULT,
            },
        },
        "base_rates": base_rates,
        "by_universe": results_by_universe,
        "verdicts": verdicts,
        "bears": bears_detail,
        "overlap_same_day": int(len(set(events["P1"]) & set(events["P2"]))),
    }

    (HERE / "results.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")

    rows = []
    for key, ev in events.items():
        for i in ev:
            rows.append({
                "signal": key,
                "date": dates[i].strftime("%Y-%m-%d"),
                "risk_on": bool(risk_on[i]),
                "in_bear": bool(any_bear[i]),
                "leader": str(leader.iloc[i]),
                "spy_pct": round(float(spy_pct[i]), 2),
                "leader_pct": round(float(lead_pct[i]), 2),
                "n_cold_le10pct": int(n_cold[i]),
                "fwd63_spy_pct": round(float(fwd_spy[MAIN_WIN][i]) * 100, 3) if not np.isnan(fwd_spy[MAIN_WIN][i]) else None,
                "fwd63_leader_pct": round(float(fwd_leader[MAIN_WIN][i]) * 100, 3) if not np.isnan(fwd_leader[MAIN_WIN][i]) else None,
                "fwd21_spy_pct": round(float(fwd_spy[SUB_WIN][i]) * 100, 3) if not np.isnan(fwd_spy[SUB_WIN][i]) else None,
                "fwd21_leader_pct": round(float(fwd_leader[SUB_WIN][i]) * 100, 3) if not np.isnan(fwd_leader[SUB_WIN][i]) else None,
            })
    pd.DataFrame(rows).sort_values(["signal", "date"]).to_csv(HERE / "signals.csv", index=False)

    print(json.dumps({"meta": res["meta"], "verdicts": verdicts}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
