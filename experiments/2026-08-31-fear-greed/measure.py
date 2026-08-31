"""KARST-120 量度:貪恐對稱開關(價格版)。

判準文本連全部參數在提交 5944006 寫死,本腳本只是執行它——
沒有搜尋訊號、沒有擬合規則、沒有跑過任何參數掃描。

輸出:results.json(全部結果數字)、signals.csv(逐次訊號明細)。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
SPY = "SPY"

# ── 第一節寫死的參數(提交 5944006),一格不准改 ──────────────────────
LEADER_WIN = 63          # 領漲板塊:過去 63 個交易日累計回報最高
COOLDOWN = 10            # 事件去重:10 個交易日冷靜期
WINDOWS = [5, 21, 63]    # 評分窗
MAIN_WIN = 21            # 主評分窗
G1_LEADER_RSI2 = 90      # 貪-主組:領漲板塊 RSI(2) ≥ 90
G1_SPREAD_RSI2 = 90      # 貪-主組:蔓延門檻 RSI(2) ≥ 90
G1_SPREAD_N = 5          # 貪-主組:蔓延數目 ≥ 5 / 9
G2_LEADER_RSI5 = 80      # 貪-副組:領漲板塊 RSI(5) ≥ 80
G2_SPREAD_RSI5 = 70      # 貪-副組:蔓延門檻 RSI(5) ≥ 70
G2_SPREAD_N = 6          # 貪-副組:蔓延數目 ≥ 6 / 9
F1_LEADER_RSI2 = 5       # 恐-型甲:領漲板塊 RSI(2) ≤ 5
F2_SPY_RSI2 = 5          # 恐-型乙:SPY RSI(2) ≤ 5
F2_SPREAD_RSI2 = 10      # 恐-型乙:蔓延門檻 RSI(2) ≤ 10
F2_SPREAD_N = 7          # 恐-型乙:蔓延數目 ≥ 7 / 9
FEAR_EDGE_PP = 1.00      # 恐半值博關:超額 ≥ 1.00 個百分點

BEARS = [
    ("2000-02", "2000-04-01", "2002-10-31"),
    ("2008", "2007-11-01", "2009-03-31"),
    ("2018Q4", "2018-10-01", "2018-12-31"),
    ("2020", "2020-03-01", "2020-03-31"),
    ("2022", "2022-02-01", "2022-10-31"),
]


def wilder_rsi(close: np.ndarray, n: int) -> np.ndarray:
    """Wilder RSI,alpha = 1/n,首個讀數需 n+1 個交易日。"""
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


def dedup(idx: np.ndarray) -> list[int]:
    """同型訊號連續成立只計首日,一次事件後 10 個交易日冷靜期。"""
    events: list[int] = []
    last = -10**9
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
        "down_share": round(float((arr < 0).mean()), 4),
        "up_share": round(float((arr > 0).mean()), 4),
        "avg_up_pct": round(u * 100, 4),
        "avg_down_pct": round(d * 100, 4),
        "breakeven_precision": round(u / (u + d), 4) if (u + d) > 0 else None,
    }


def main() -> int:
    px = pd.read_parquet(HERE / "prices_daily.parquet")
    close = px.pivot(index="date", columns="ticker", values="close")
    opn = px.pivot(index="date", columns="ticker", values="open")
    cols = SECTORS + [SPY]
    close = close[cols].dropna()
    opn = opn.loc[close.index, cols]
    dates = close.index
    m = len(dates)

    # RSI
    rsi2 = pd.DataFrame({t: wilder_rsi(close[t].to_numpy(), 2) for t in cols}, index=dates)
    rsi5 = pd.DataFrame({t: wilder_rsi(close[t].to_numpy(), 5) for t in cols}, index=dates)

    # 領漲板塊:過去 63 個交易日累計回報最高
    ret63 = close[SECTORS] / close[SECTORS].shift(LEADER_WIN) - 1.0
    leader_ok = ret63.notna().all(axis=1)
    leader = pd.Series(index=dates, dtype=object)
    leader.loc[leader_ok] = ret63.loc[leader_ok].idxmax(axis=1)

    # 有效期:領漲板塊算得出 + RSI 讀數齊
    valid = leader_ok & rsi2[cols].notna().all(axis=1) & rsi5[cols].notna().all(axis=1)
    valid_idx = np.where(valid.to_numpy())[0]
    first_valid = int(valid_idx[0])

    # 前瞻回報:T+1 開市 → T+1+N 開市
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

    # 訊號
    rsi2_s, rsi5_s = rsi2[SECTORS], rsi5[SECTORS]
    lead_rsi2 = np.array([rsi2.iloc[i][leader.iloc[i]] if leader_ok.iloc[i] else np.nan for i in range(m)])
    lead_rsi5 = np.array([rsi5.iloc[i][leader.iloc[i]] if leader_ok.iloc[i] else np.nan for i in range(m)])
    n_hot2 = (rsi2_s >= G1_SPREAD_RSI2).sum(axis=1).to_numpy()
    n_hot5 = (rsi5_s >= G2_SPREAD_RSI5).sum(axis=1).to_numpy()
    n_cold10 = (rsi2_s <= F2_SPREAD_RSI2).sum(axis=1).to_numpy()
    spy_rsi2 = rsi2[SPY].to_numpy()

    v = valid.to_numpy()
    raw = {
        "G1": v & (lead_rsi2 >= G1_LEADER_RSI2) & (n_hot2 >= G1_SPREAD_N),
        "G2": v & (lead_rsi5 >= G2_LEADER_RSI5) & (n_hot5 >= G2_SPREAD_N),
        "F1": v & (lead_rsi2 <= F1_LEADER_RSI2),
        "F2": v & (spy_rsi2 <= F2_SPY_RSI2) & (n_cold10 >= F2_SPREAD_N),
    }
    events = {k: dedup(np.where(vv)[0]) for k, vv in raw.items()}

    # 基礎率:全部有效且算得出前瞻回報的交易日
    base = {}
    for N in WINDOWS:
        ok = v & ~np.isnan(fwd_spy[N])
        base[f"SPY_{N}"] = stats(fwd_spy[N][ok])
        okl = v & ~np.isnan(fwd_leader[N])
        base[f"LEADER_{N}"] = stats(fwd_leader[N][okl])

    bear_masks = {}
    for name, a, b in BEARS:
        bear_masks[name] = (dates >= pd.Timestamp(a)) & (dates <= pd.Timestamp(b))
    any_bear = np.zeros(m, dtype=bool)
    for mk in bear_masks.values():
        any_bear |= mk

    def score(key: str, target: str) -> dict:
        ev = events[key]
        rec: dict = {"signal_count": len(ev)}
        for N in WINDOWS:
            f = fwd_spy[N] if target == "SPY" else fwd_leader[N]
            vals = np.array([f[i] for i in ev if not np.isnan(f[i])])
            rec[f"win{N}"] = stats(vals)
            rec[f"win{N}"]["scored_count"] = int(len(vals))
        # 三個退守目的地(貪半用;恐半亦順手報)
        for N in WINDOWS:
            ld = np.array([fwd_leader[N][i] for i in ev if not np.isnan(fwd_leader[N][i])])
            sp = np.array([fwd_spy[N][i] for i in ev if not np.isnan(fwd_spy[N][i])])
            rec[f"dest{N}"] = {
                "hold_leader_mean_pct": round(float(ld.mean()) * 100, 4) if len(ld) else None,
                "to_spy_mean_pct": round(float(sp.mean()) * 100, 4) if len(sp) else None,
                "to_usd_mean_pct": 0.0,
                "n": int(len(sp)),
            }
        # 五熊逐次
        f = fwd_spy[MAIN_WIN] if target == "SPY" else fwd_leader[MAIN_WIN]
        per_bear = {}
        for name, mk in bear_masks.items():
            hits = [i for i in ev if mk[i]]
            vals = np.array([f[i] for i in hits if not np.isnan(f[i])])
            per_bear[name] = {
                "count": len(hits),
                "dates": [dates[i].strftime("%Y-%m-%d") for i in hits],
                "fwd21_mean_pct": round(float(vals.mean()) * 100, 4) if len(vals) else None,
                "fwd21_each_pct": [round(float(f[i]) * 100, 2) for i in hits if not np.isnan(f[i])],
            }
        rec["bears"] = per_bear
        # 熊市窗口以外
        out_ev = [i for i in ev if not any_bear[i]]
        vals = np.array([f[i] for i in out_ev if not np.isnan(f[i])])
        rec["non_bear"] = {"count": len(out_ev), **stats(vals)}
        rec["in_bear_count"] = len(ev) - len(out_ev)
        rec["dates"] = [dates[i].strftime("%Y-%m-%d") for i in ev]
        rec["leaders"] = [str(leader.iloc[i]) for i in ev]
        return rec

    res = {
        "meta": {
            "criteria_commit": "5944006",
            "first_date": dates[0].strftime("%Y-%m-%d"),
            "last_date": dates[-1].strftime("%Y-%m-%d"),
            "trading_days": int(m),
            "first_valid_signal_date": dates[first_valid].strftime("%Y-%m-%d"),
            "valid_days": int(v.sum()),
            "params": {
                "leader_win": LEADER_WIN, "cooldown": COOLDOWN, "windows": WINDOWS,
                "G1": [G1_LEADER_RSI2, G1_SPREAD_RSI2, G1_SPREAD_N],
                "G2": [G2_LEADER_RSI5, G2_SPREAD_RSI5, G2_SPREAD_N],
                "F1": [F1_LEADER_RSI2],
                "F2": [F2_SPY_RSI2, F2_SPREAD_RSI2, F2_SPREAD_N],
                "fear_edge_pp": FEAR_EDGE_PP,
            },
        },
        "base_rates": base,
        "greed": {"G1": score("G1", "SPY"), "G2": score("G2", "SPY")},
        "fear": {"F1": score("F1", "LEADER"), "F2": score("F2", "SPY")},
    }

    # 及格判定(照第一節寫死的三條關,主評分窗 21 日)
    verdicts = {}
    for key in ("G1", "G2"):
        r = res["greed"][key][f"win{MAIN_WIN}"]
        b = base[f"SPY_{MAIN_WIN}"]
        g1 = r.get("mean_pct", 0) < 0
        g2 = r.get("down_share", 0) > b["down_share"]
        g3 = r.get("down_share", 0) >= b["breakeven_precision"]
        verdicts[key] = {
            "gate1_turn_defensive": g1, "gate1_value": r.get("mean_pct"),
            "gate2_informative": g2, "precision": r.get("down_share"), "base_rate": b["down_share"],
            "gate3_worth_it": g3, "breakeven": b["breakeven_precision"],
            "pass": bool(g1 and g2 and g3),
        }
    for key, tgt in (("F1", "LEADER"), ("F2", "SPY")):
        r = res["fear"][key][f"win{MAIN_WIN}"]
        b = base[f"{tgt}_{MAIN_WIN}"]
        g1 = r.get("mean_pct", 0) > 0
        g2 = r.get("up_share", 0) > b["up_share"]
        edge = round(r.get("mean_pct", 0) - b["mean_pct"], 4)
        g3 = edge >= FEAR_EDGE_PP
        verdicts[key] = {
            "gate1_profitable": g1, "gate1_value": r.get("mean_pct"),
            "gate2_informative": g2, "precision": r.get("up_share"), "base_rate": b["up_share"],
            "gate3_worth_it": g3, "edge_pp": edge,
            "pass": bool(g1 and g2 and g3),
        }
    res["verdicts"] = verdicts

    (HERE / "results.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")

    rows = []
    for key, ev in events.items():
        for i in ev:
            rows.append({
                "signal": key, "date": dates[i].strftime("%Y-%m-%d"),
                "leader": str(leader.iloc[i]),
                "leader_rsi2": round(float(lead_rsi2[i]), 2),
                "leader_rsi5": round(float(lead_rsi5[i]), 2),
                "spy_rsi2": round(float(spy_rsi2[i]), 2),
                "n_hot_rsi2_ge90": int(n_hot2[i]), "n_hot_rsi5_ge70": int(n_hot5[i]),
                "n_cold_rsi2_le10": int(n_cold10[i]),
                "fwd21_spy_pct": round(float(fwd_spy[21][i]) * 100, 3) if not np.isnan(fwd_spy[21][i]) else None,
                "fwd21_leader_pct": round(float(fwd_leader[21][i]) * 100, 3) if not np.isnan(fwd_leader[21][i]) else None,
                "in_bear": bool(any_bear[i]),
            })
    pd.DataFrame(rows).sort_values(["signal", "date"]).to_csv(HERE / "signals.csv", index=False)

    print(json.dumps({"meta": res["meta"], "base": base, "verdicts": verdicts}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
