# -*- coding: utf-8 -*-
"""KARST-156 step 2: measure. CRITERIA.md sections 4-5, nothing else.

Outputs (out/):
  rank_corr.json    Spearman median / mean / Newey-West t, per version and period
  arms.csv          every arm x period x cost level
  random_band.json  2,000-path luck band
  controls.json     size / profitability control, both routes
  verdict.json      the three-way judgement 存在 / 不存在 / 量不出
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd
from scipy import stats

import engine

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
DATA = HERE / "data"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

DAILY = REPO / "experiments" / "2026-09-02-timing-sweep" / "data" / "daily_close.parquet"
WIN_END = pd.Timestamp("2026-08-31")
COSTS = (0.0, 15.0, 25.0, 50.0)
MAIN_BPS = 15.0
NW_LAG = 6
N_DECILE = 10
N_QUINT = 5
N_PATHS = 2000
SEED = 20260902

PERIODS = {
    "全期": (pd.Timestamp("2010-04-30"), pd.Timestamp("2026-07-31")),
    "2010-2016": (pd.Timestamp("2010-04-30"), pd.Timestamp("2016-12-31")),
    "2017-2026": (pd.Timestamp("2017-01-31"), pd.Timestamp("2026-07-31")),
}


# ------------------------------------------------------------------ stats
def nw_t(x: np.ndarray, lag: int = NW_LAG) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    T = len(x)
    if T < 12:
        return float("nan")
    m = x.mean()
    e = x - m
    s = float(e @ e) / T
    for j in range(1, lag + 1):
        g = float(e[j:] @ e[:-j]) / T
        s += 2.0 * (1.0 - j / (lag + 1.0)) * g
    if s <= 0:
        return float("nan")
    return float(m / np.sqrt(s / T))


def pct_rank(s: pd.Series) -> pd.Series:
    return s.rank(pct=True)


# ------------------------------------------------------------------ main
def main() -> None:
    daily = pd.read_parquet(DAILY)
    daily.index = pd.to_datetime(daily.index)
    dates = daily.index
    cols = list(daily.columns)
    col_of = {c: i for i, c in enumerate(cols)}
    ret_all = daily.pct_change().to_numpy()

    sig = pd.read_parquet(DATA / "signals.parquet")
    sig["month_end"] = pd.to_datetime(sig["month_end"])

    m_close = daily.resample("ME").last()
    fwd = (m_close.shift(-1) / m_close - 1.0).stack().rename("fwd").reset_index()
    fwd.columns = ["month_end", "ticker", "fwd"]
    sig = sig.merge(fwd, on=["month_end", "ticker"], how="left")

    months = sorted(sig["month_end"].unique())
    exec_day, end_i = {}, int(dates.searchsorted(WIN_END, side="right"))
    for m in months:
        pos = dates.searchsorted(pd.Timestamp(m), side="right") - 1
        if pos + 1 < end_i:
            exec_day[pd.Timestamp(m)] = pos + 1
    ret = ret_all[:end_i]
    first_exec = min(exec_day.values())

    def window(lo: pd.Timestamp, hi: pd.Timestamp) -> np.ndarray:
        a = min(v for k, v in exec_day.items() if k >= lo)
        later = [v for k, v in exec_day.items() if k > hi]
        b = min(later) if later else end_i
        w = np.zeros(end_i, dtype=bool)
        w[a:b] = True
        return w

    rows_arms, results = [], {}
    rank_corr, controls, bands = {}, {}, {}

    for ver, label in (("a", "A版 攤薄股數"), ("b", "B版 封面頁在外股數")):
        col = f"shrink_{ver}"
        for tag, sensitivity in (("主", False), ("敏感度_全剔大變動", True)):
            d = sig[["month_end", "ticker", col, "mcap", "profit", "fwd",
                     f"big_move_{ver}"]].rename(columns={col: "shrink"})
            if sensitivity:
                d = d[~d[f"big_move_{ver}"].fillna(False)]
            d = d[d["shrink"].notna()].copy()

            # ---- 4.1 rank correlation ---------------------------------
            per_month = []
            for m, g in d.groupby("month_end"):
                g = g[g["fwd"].notna()]
                if len(g) < 20:
                    continue
                rho = stats.spearmanr(g["shrink"], g["fwd"]).statistic
                per_month.append((pd.Timestamp(m), float(rho), len(g)))
            rc = pd.DataFrame(per_month, columns=["month_end", "rho", "n"])
            for pname, (lo, hi) in PERIODS.items():
                sl = rc[(rc["month_end"] >= lo) & (rc["month_end"] <= hi)]
                rank_corr[f"{ver}|{tag}|{pname}"] = {
                    "月數": int(len(sl)),
                    "中位": round(float(sl["rho"].median()), 5) if len(sl) else None,
                    "平均": round(float(sl["rho"].mean()), 5) if len(sl) else None,
                    "NW_t": round(nw_t(sl["rho"].to_numpy()), 3) if len(sl) else None,
                    "池內每月人數中位": float(sl["n"].median()) if len(sl) else None,
                }
            if sensitivity:
                continue    # sensitivity run reports rank correlation only

            # ---- 4.2 deciles ------------------------------------------
            picks = {k: {} for k in range(N_DECILE)}
            pool_picks, d1_sizes = {}, {}
            for m, g in d.groupby("month_end"):
                m = pd.Timestamp(m)
                if m not in exec_day:
                    continue
                i = exec_day[m]
                live = [t for t in g["ticker"] if t in col_of and np.isfinite(ret[i, col_of[t]])]
                g = g[g["ticker"].isin(live)]
                if len(g) < N_DECILE * 3:
                    continue
                order = g.sort_values("shrink", ascending=False)["ticker"].tolist()
                chunks = np.array_split(np.arange(len(order)), N_DECILE)
                for k, ch in enumerate(chunks):
                    picks[k][i] = [col_of[order[j]] for j in ch]
                pool_picks[i] = [col_of[t] for t in order]
                d1_sizes[i] = len(chunks[0])

            dec_g, dec_t = {}, {}
            for k in range(N_DECILE):
                g_, t_ = engine.run_one(ret, picks[k])
                dec_g[k], dec_t[k] = g_, t_
            pool_g, pool_t = engine.run_one(ret, pool_picks)

            arms = {
                f"D1 只做多({label})": (dec_g[0], dec_t[0]),
                f"D10 只做多({label})": (dec_g[9], dec_t[9]),
                f"D1-D10 長短({label})": (0.5 * dec_g[0] - 0.5 * dec_g[9],
                                          0.5 * dec_t[0] + 0.5 * dec_t[9]),
                "同池等權": (pool_g, pool_t),
            }
            for bm in ("SPY", "XLK"):
                if bm in col_of:
                    r = np.nan_to_num(ret[:, col_of[bm]], nan=0.0)
                    arms[bm] = (r, np.zeros_like(r))

            for pname, (lo, hi) in PERIODS.items():
                w = window(lo, hi)
                yrs = int(w.sum()) / engine.TRADING_DAYS_YEAR
                for name, (g_, t_) in arms.items():
                    for bps in COSTS:
                        net = engine.apply_cost(g_, t_, bps)[w]
                        rows_arms.append({
                            "版本": label, "臂": name, "分期": pname, "成本bp": bps,
                            "年化": round(float(engine.cagr(net, yrs)), 5),
                            "最大回撤": round(engine.max_drawdown(net), 4),
                            "年換手": round(float(t_[w].sum() / yrs), 3),
                        })
                    if pname == "全期":
                        results[f"{ver}|{name}"] = (g_, t_)

            # ---- 4.3 luck band ----------------------------------------
            rng = np.random.default_rng(SEED)
            width = max(d1_sizes.values())
            idx = {}
            for i, allc in pool_picks.items():
                n = d1_sizes[i]
                a = np.full((N_PATHS, width), -1, dtype=np.int64)
                arr = np.asarray(allc)
                for p in range(N_PATHS):
                    a[p, :n] = rng.choice(arr, size=n, replace=False)
                idx[i] = a
            gb, tb = engine.run_paths(ret, idx)
            band = {}
            for pname, (lo, hi) in PERIODS.items():
                w = window(lo, hi)
                yrs = int(w.sum()) / engine.TRADING_DAYS_YEAR
                for bps in COSTS:
                    nets = gb - tb * (bps / 10000.0)
                    cg = np.array([engine.cagr(nets[p][w], yrs) for p in range(N_PATHS)])
                    band[f"{pname}|{bps}bp"] = {
                        "p5": round(float(np.percentile(cg, 5)), 5),
                        "p50": round(float(np.percentile(cg, 50)), 5),
                        "p95": round(float(np.percentile(cg, 95)), 5),
                    }
            bands[label] = {"每月抽樣隻數(=D1)": int(np.median(list(d1_sizes.values()))),
                            "路徑數": N_PATHS, "百分位": band}

            # ---- 4.4 controls -----------------------------------------
            controls[label] = run_controls(d)

    pd.DataFrame(rows_arms).to_csv(OUT / "arms.csv", index=False, encoding="utf-8")
    (OUT / "rank_corr.json").write_text(json.dumps(rank_corr, ensure_ascii=False, indent=2),
                                        encoding="utf-8")
    (OUT / "random_band.json").write_text(json.dumps(bands, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    (OUT / "controls.json").write_text(json.dumps(controls, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    verdict = judge(rank_corr, controls)
    (OUT / "verdict.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))


# ------------------------------------------------------------------ controls
def run_controls(d: pd.DataFrame) -> dict:
    d = d[d["fwd"].notna()].copy()
    out: dict = {}

    def quint_spread(g: pd.DataFrame) -> float:
        if len(g) < N_QUINT * 2:
            return np.nan
        q = pd.qcut(g["shrink"].rank(method="first"), N_QUINT, labels=False)
        top = g.loc[q == N_QUINT - 1, "fwd"].mean()
        bot = g.loc[q == 0, "fwd"].mean()
        return float(top - bot)

    raw, by_size, by_prof = [], [], []
    for m, g in d.groupby("month_end"):
        raw.append(quint_spread(g))
        gs = g[g["mcap"].notna()]
        if len(gs) >= N_QUINT * N_QUINT * 2:
            sq = pd.qcut(gs["mcap"].rank(method="first"), N_QUINT, labels=False)
            vals = [quint_spread(gs[sq == k]) for k in range(N_QUINT)]
            by_size.append(np.nanmean(vals))
        gp = g[g["profit"].notna()]
        if len(gp) >= N_QUINT * N_QUINT * 2:
            pq = pd.qcut(gp["profit"].rank(method="first"), N_QUINT, labels=False)
            vals = [quint_spread(gp[pq == k]) for k in range(N_QUINT)]
            by_prof.append(np.nanmean(vals))

    raw_m = float(np.nanmean(raw))
    out["路線甲_雙重排序"] = {
        "未控制_五分位利差_月均": round(raw_m, 5),
        "未控制_NW_t": round(nw_t(np.array(raw)), 3),
        "控制規模後": round(float(np.nanmean(by_size)), 5),
        "控制規模後_NW_t": round(nw_t(np.array(by_size)), 3),
        "控制規模後_保留": round(float(np.nanmean(by_size)) / raw_m, 3) if raw_m else None,
        "控制盈利能力後": round(float(np.nanmean(by_prof)), 5),
        "控制盈利能力後_NW_t": round(nw_t(np.array(by_prof)), 3),
        "控制盈利能力後_保留": round(float(np.nanmean(by_prof)) / raw_m, 3) if raw_m else None,
    }

    uni, multi = [], []
    for m, g in d.groupby("month_end"):
        g = g.dropna(subset=["shrink", "fwd"])
        if len(g) < 30:
            continue
        y = g["fwd"].to_numpy()
        s = pct_rank(g["shrink"]).to_numpy()
        X1 = np.column_stack([np.ones(len(g)), s])
        uni.append(np.linalg.lstsq(X1, y, rcond=None)[0][1])
        gm = g.dropna(subset=["mcap", "profit"])
        if len(gm) < 30:
            continue
        y2 = gm["fwd"].to_numpy()
        X2 = np.column_stack([np.ones(len(gm)), pct_rank(gm["shrink"]).to_numpy(),
                              pct_rank(gm["mcap"]).to_numpy(),
                              pct_rank(gm["profit"]).to_numpy()])
        multi.append(np.linalg.lstsq(X2, y2, rcond=None)[0][1])

    u, mm = float(np.mean(uni)), float(np.mean(multi))
    out["路線乙_FamaMacBeth"] = {
        "單變量_shrink係數_月均": round(u, 5),
        "單變量_NW_t": round(nw_t(np.array(uni)), 3),
        "三變量_shrink係數_月均": round(mm, 5),
        "三變量_NW_t": round(nw_t(np.array(multi)), 3),
        "保留": round(mm / u, 3) if u else None,
    }
    keep = [out["路線甲_雙重排序"]["控制規模後_保留"],
            out["路線甲_雙重排序"]["控制盈利能力後_保留"],
            out["路線乙_FamaMacBeth"]["保留"]]
    keep = [k for k in keep if k is not None]
    out["保留幅度_取最低"] = round(min(keep), 3) if keep else None
    return out


# ------------------------------------------------------------------ verdict
def judge(rank_corr: dict, controls: dict) -> dict:
    out = {}
    for ver, label in (("a", "A版 攤薄股數"), ("b", "B版 封面頁在外股數")):
        rc = rank_corr.get(f"{ver}|主|全期", {})
        med, t = rc.get("中位"), rc.get("NW_t")
        keep = controls.get(label, {}).get("保留幅度_取最低")
        if med is None or t is None:
            v = "量不出"
            why = "相關度算不出來"
        elif med >= 0.015 and t >= 2.5 and keep is not None and keep >= 0.50:
            v = "存在"
            why = f"中位 {med} ≥ 0.015、NW t {t} ≥ 2.5、控制後保留 {keep} ≥ 0.50"
        elif med <= 0.005 or (keep is not None and keep < 0.30):
            v = "不存在"
            why = (f"中位 {med} ≤ 0.005" if med <= 0.005
                   else f"控制後只剩 {keep},判為規模/盈利能力的化身")
        else:
            v = "量不出"
            why = f"中位 {med}、NW t {t}、控制後保留 {keep},三條門檻並非全過亦非全敗"
        out[label] = {"判詞": v, "依據": why, "相關度中位": med, "NW_t": t,
                      "控制後保留_最低": keep}
    return out


if __name__ == "__main__":
    main()
