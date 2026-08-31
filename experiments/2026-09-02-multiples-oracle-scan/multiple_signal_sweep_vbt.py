"""KARST-133 第二步:把板塊倍數序列當價格用,一次過掃齊四族訊號(D-101/D-103)。

序列口徑(D-103):**只用一條** —— 真實盈利按公布日滯後入帳的後顧倍數
(`pe_lag`,即當年當時真係睇得到嗰個數)。神諭版兩條對齊已跑但不作任何主張。

四族(加一族基線):
  E 基線·平貴水平   score = 倍數水平本身
  A 均值回歸        score = 對自身歷史的 z 分 / 百分位(回望窗 L)
  B 序列擺盪        score = 倍數序列的 RSI(窗 W)
  C 倍數趨勢        score = 倍數在 W 個月內的變動率
兩種底:abs = 板塊自己的倍數;rel = 板塊倍數 ÷ 大市倍數
兩個方向:各族的分數取正負兩邊都掃

規則形狀照已批:月底決策、次一交易日開市價成交、揸最高分三隻等權、
對照 SPY(含息)與等權九隻、10bp 單邊換手成本。
**不設退守 SPY 地板**——那條規則(D-071)是為動能而設的「前三名全負」,
倍數分數沒有對應的天然零線,加進去等於偷混一條擇時訊號。

回報面板重用 experiments/2026-08-31-fear-greed/prices_daily.parquet,不另抓。
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd
import vectorbt as vbt

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
PRICES = REPO / "experiments" / "2026-08-31-fear-greed" / "prices_daily.parquet"
MULT = HERE / "data" / "sector_multiples.parquet"

SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
SPY = "SPY"
N_HOLD = 3
COST_BP = 10.0
ALIGN = "pe_lag"          # D-103:唯一一條序列

LOOKBACKS = [12, 24, 36, 48, 60, 84, 120]   # A 族回望窗(月)
RSI_WINS = [3, 6, 9, 12, 14, 18, 24]        # B 族 RSI 窗(月)
TREND_WINS = [1, 3, 6, 9, 12, 18, 24]       # C 族趨勢窗(月)


def rsi(s: pd.Series, w: int) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0).rolling(w).mean()
    dn = (-d.clip(upper=0)).rolling(w).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def build_scores(mw: pd.DataFrame, relw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """回傳 {格名: 分數表(月 × 板塊)};分數愈高愈買。"""
    out: dict[str, pd.DataFrame] = {}
    for base, W in (("abs", mw), ("rel", relw)):
        for sign, dname in ((-1.0, "低"), (1.0, "高")):
            # E 基線:平貴水平
            out[f"E-水平-{base}-{dname}"] = sign * W
            # A 均值回歸:z 分與百分位
            for L in LOOKBACKS:
                mu = W.rolling(L).mean()
                sd = W.rolling(L).std()
                out[f"A-z{L}-{base}-{dname}"] = sign * (W - mu) / sd
                out[f"A-p{L}-{base}-{dname}"] = sign * W.rolling(L).rank(pct=True)
            # B 序列 RSI
            for w in RSI_WINS:
                out[f"B-rsi{w}-{base}-{dname}"] = sign * W.apply(lambda s: rsi(s, w))
            # C 倍數趨勢
            for w in TREND_WINS:
                out[f"C-trd{w}-{base}-{dname}"] = sign * (W / W.shift(w) - 1.0)
    return out


def main() -> None:
    px = pd.read_parquet(PRICES)
    px["date"] = pd.to_datetime(px["date"])
    cols = SECTORS + [SPY]
    close = px.pivot(index="date", columns="ticker", values="close")[cols]
    open_ = px.pivot(index="date", columns="ticker", values="open")[cols]
    dates = close.index
    sec_idx = np.array([cols.index(s) for s in SECTORS])
    spy_col = cols.index(SPY)

    # 月底交易日位置
    me_pos = (pd.Series(np.arange(len(dates)), index=dates)
              .groupby([dates.year, dates.month]).last().to_numpy())
    me_ym = [f"{dates[p].year:04d}-{dates[p].month:02d}" for p in me_pos]

    # ---- 倍數序列 ----
    mu = pd.read_parquet(MULT)
    mu["month_end"] = pd.to_datetime(mu["month_end"])
    mu["ym"] = mu["month_end"].dt.strftime("%Y-%m")
    wide = mu.pivot(index="ym", columns="series", values=ALIGN)
    mkt = wide["MKT"]
    mw = wide[SECTORS].reindex(me_ym)
    relw = mw.div(mkt.reindex(me_ym), axis=0)
    print(f"倍數序列 {mw.shape}, 有效格比例 {mw.notna().mean().mean():.3f}")

    scores = build_scores(mw, relw)
    print(f"掃描格數 {len(scores)}")

    open_a = open_.to_numpy()
    m = len(dates)
    # 每格都要同一段評分期:由最長回望窗之後開始
    warm = max(max(LOOKBACKS), max(RSI_WINS), max(TREND_WINS))
    k0 = warm
    kmax = len(me_pos) - 2
    while me_pos[kmax + 1] + 1 >= m:
        kmax -= 1
    ks = np.arange(k0, kmax + 1)
    exec_rows = np.array([me_pos[k] + 1 for k in ks] + [me_pos[kmax + 1] + 1])
    exec_px = pd.DataFrame(open_a[exec_rows], columns=cols,
                           index=pd.DatetimeIndex(dates[exec_rows]))
    n_per = len(ks)
    print(f"評分期 {me_ym[k0]} .. {me_ym[kmax + 1]},共 {n_per} 個月")

    # ---- 逐格砌權重 ----
    labels, weight_blocks = [], []
    for lab, sc in scores.items():
        arr = sc.to_numpy()
        w = np.zeros((n_per + 1, len(cols)))
        n_valid = 0
        for row, k in enumerate(ks):
            v = arr[k]
            good = np.where(~np.isnan(v))[0]
            if len(good) < N_HOLD:
                w[row, spy_col] = 1.0        # 分數不足以排名 → 揸 SPY,不當作訊號
                continue
            n_valid += 1
            top = good[np.argsort(-v[good])[:N_HOLD]]
            w[row, sec_idx[top]] = 1.0 / N_HOLD
        w[-1] = w[-2]
        weight_blocks.append(w)
        labels.append(lab)

    # ---- 手寫向量化(正本)----
    rets = exec_px.to_numpy()[1:] / exec_px.to_numpy()[:-1] - 1.0
    spy_ret = rets[:, spy_col].copy()
    spy_ret[0] -= COST_BP / 10000.0
    ew9 = rets[:, sec_idx].mean(axis=1).copy()
    ew9[0] -= COST_BP / 10000.0

    hand = {}
    turns = {}
    for lab, w in zip(labels, weight_blocks):
        wt = w[:n_per]
        gross = (wt * rets).sum(axis=1)
        turn = np.abs(np.diff(np.vstack([np.zeros((1, len(cols))), wt]),
                              axis=0)).sum(axis=1) / 2
        turn[0] = 1.0
        hand[lab] = gross - turn * COST_BP / 10000.0
        turns[lab] = turn

    # ---- vectorBT 對照臂(D-095 指定工具)----
    big_w = np.concatenate(weight_blocks, axis=1)
    mi = pd.MultiIndex.from_tuples([(l, t) for l in labels for t in cols],
                                   names=["combo", "ticker"])
    size = pd.DataFrame(big_w, index=exec_px.index, columns=mi)
    price = pd.concat({l: exec_px for l in labels}, axis=1)
    price.columns.names = ["combo", "ticker"]
    price = price[mi]
    pf = vbt.Portfolio.from_orders(
        close=price, size=size, size_type="targetpercent",
        group_by="combo", cash_sharing=True, call_seq="auto",
        fees=COST_BP / 2 / 10000.0, init_cash=100.0, freq="30D",
    )
    vbt_rets = pf.returns()
    print("vectorBT 掃描完成")

    def cagr(r):
        return (np.prod(1.0 + r) ** (12.0 / len(r)) - 1.0) * 100

    spy_c, ew9_c = cagr(spy_ret), cagr(ew9)

    # 實際月度前三名(命中率用)
    sec_rets = rets[:, sec_idx]
    actual_top = [set(np.argsort(-sec_rets[i])[:N_HOLD].tolist())
                  for i in range(n_per)]

    rows = []
    for lab, w in zip(labels, weight_blocks):
        h = hand[lab]
        fam, param, base, dname = lab.split("-")
        d = h - spy_ret
        t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d))) if d.std() > 0 else 0.0
        d9 = h - ew9
        t9 = d9.mean() / (d9.std(ddof=1) / np.sqrt(len(d9))) if d9.std() > 0 else 0.0
        wt = w[:n_per]
        hits = hit_slots = 0
        for i in range(n_per):
            picked = {int(j) for j in range(len(sec_idx))
                      if wt[i, sec_idx[j]] > 0}
            if picked:
                hits += len(picked & actual_top[i])
                hit_slots += N_HOLD
        v = vbt_rets[lab].to_numpy()
        rows.append({
            "family": fam, "param": param, "base": base, "direction": dname,
            "label": lab, "n_periods": n_per,
            "cagr_pct": round(cagr(h), 3),
            "excess_spy_pp": round(cagr(h) - spy_c, 3),
            "excess_ew9_pp": round(cagr(h) - ew9_c, 3),
            "paired_t_spy": round(float(t), 3),
            "paired_t_ew9": round(float(t9), 3),
            "hit_rate_pct": round(100 * hits / hit_slots, 2) if hit_slots else float("nan"),
            "avg_turnover": round(float(np.mean(turns[lab])), 4),
            "vbt_cagr_pct": round(cagr(v), 3),
            "vbt_minus_hand_pp": round(cagr(v) - cagr(h), 3),
        })

    grid = pd.DataFrame(rows)
    grid.to_csv(HERE / "signal_sweep.csv", index=False, encoding="utf-8")

    print(f"\n基準:SPY {spy_c:.2f}% / 等權九隻 {ew9_c:.2f}%  "
          f"(命中基礎率 {100*N_HOLD/len(SECTORS):.2f}%)")
    print(f"vbt 對手寫:中位差 {grid['vbt_minus_hand_pp'].median():.4f}pp,"
          f"最大 {grid['vbt_minus_hand_pp'].abs().max():.4f}pp")

    print("\n=== 逐族全景(對等權九隻的超額,百分點)===")
    for fam in ["E", "A", "B", "C"]:
        g = grid[grid.family == fam]
        print(f"\n[{fam} 族] {len(g)} 格  超額中位 {g.excess_ew9_pp.median():+.2f}pp  "
              f"最好 {g.excess_ew9_pp.max():+.2f}pp  最差 {g.excess_ew9_pp.min():+.2f}pp  "
              f"正數格 {(g.excess_ew9_pp > 0).sum()}/{len(g)}  "
              f"|t|>=2 格 {(g.paired_t_ew9.abs() >= 2).sum()}")
        for (b, d), gg in g.groupby(["base", "direction"]):
            s = gg.sort_values("param")
            print(f"   {b}/{d}: " + "  ".join(
                f"{r.param}={r.excess_ew9_pp:+.2f}" for r in s.itertuples()))

    # ---- 鄰域平均(平原 vs 孤峰;只沿連續軸)----
    nb = []
    for (fam, base, dname), g in grid.groupby(["family", "base", "direction"]):
        if fam == "E":
            continue
        g = g.copy()
        g["axis"] = g["param"].str.extract(r"(\d+)").astype(int)
        # A 族有 z / p 兩種正規化,分開排
        g["kind"] = g["param"].str.extract(r"^([a-z]+)")
        for kind, gk in g.groupby("kind"):
            gk = gk.sort_values("axis").reset_index(drop=True)
            v = gk["excess_ew9_pp"].to_numpy()
            for i in range(len(gk)):
                lo, hi = max(0, i - 1), min(len(gk), i + 2)
                nb.append({
                    "family": fam, "kind": kind, "base": base, "direction": dname,
                    "axis": int(gk.axis[i]), "label": gk.label[i],
                    "excess_ew9_pp": float(v[i]),
                    "neighbourhood_mean_pp": round(float(v[lo:hi].mean()), 3),
                    "t_ew9": float(gk.paired_t_ew9[i]),
                })
    nbd = pd.DataFrame(nb)
    nbd.to_csv(HERE / "neighbourhood.csv", index=False, encoding="utf-8")

    print("\n=== 鄰域平均最高十格(平原候選)===")
    print(nbd.sort_values("neighbourhood_mean_pp", ascending=False)
          .head(10).to_string(index=False))

    # ---- 橫截面分散度(換宇宙比例尺)----
    disp = pd.DataFrame({
        "ym": [me_ym[k + 1] for k in ks],
        "cs_std_pp": sec_rets.std(axis=1, ddof=1) * 100,
        "max_minus_min_pp": (sec_rets.max(axis=1) - sec_rets.min(axis=1)) * 100,
    })
    disp.to_csv(HERE / "dispersion.csv", index=False, encoding="utf-8")
    disp["year"] = disp["ym"].str[:4]
    print("\n=== 九隻板塊月回報橫截面分散度 ===")
    print(f"全期中位:截面標準差 {disp.cs_std_pp.median():.2f}pp,"
          f"最高減最低 {disp.max_minus_min_pp.median():.2f}pp")
    print(disp.groupby("year")[["cs_std_pp", "max_minus_min_pp"]]
          .median().round(2).to_string())


if __name__ == "__main__":
    main()
