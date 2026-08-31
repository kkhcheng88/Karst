"""KARST-132 板塊層技術指標橫截面全景圖(依考試協議第七節、D-095/D-096)。

純探索,不是考試,**不產生任何及格宣稱**。任何一格只可入候選庫。

考的是甚麼:每月月底用一個技術指標值將九隻 SPDR 板塊 ETF 排名,揸排頭三隻等權,
對 SPY 買入持有(含息)作基線。**只考橫截面「揀邊個板塊」,不考擇時**——
均線做開關/擇時嗰格已由市況層十月線佔住(D-071、D-098 第 4 條)。

規則形狀照 D-090 已批那一套,一個字不改:
  月底收市決策 → 揸三隻等權 → 次一交易日開市成交 → 單邊換手率 × 10 個基點
  → 對 SPY 買入持有含息基線(基線期初收一次成本)
**與動能票的唯一分別**:本票拿走「前三名全為負則退 SPY」那條地板。
理由:那是擇時成分,本票明文不考擇時;拿走之後每一格都是純橫截面比較。

掃描面(一次過掃齊,不准擠牙膏式加格重跑——協議第七節第 6 條):

  甲族 RSI(Wilder 平滑)
    主格:回望 L ∈ {5,7,10,14,21,30,45,60} 日 × 方向 {高 RSI 順勢, 低 RSI 逆勢}
    旁支:門檻讀法 L ∈ {14,21,60} × 門檻 × 方向 —— **含擇時成分**
          (合資格板塊不足三隻時餘額揸 SPY),故另報,不入平原判讀。

  乙族 均線
    (b1) 價格對均線距離 P/MA(L)-1,L ∈ {20,50,100,150,200,250} × 方向
    (b2) 短長均線差 MA(s)/MA(l)-1,八組 (s,l) × 方向

  丙 參照格(不是候選,只作對照)
    12-1 動能(KARST-127/129 那條已判死的線,無 SPY 地板版)、
    等權九隻。用來回答「均線族是不是動能的另一個包裝」。

兩套會計一齊跑互相對數:
  (甲) vectorBT 1.1.0 Portfolio.from_orders(TargetPercent, cash_sharing) —— D-095 指定
  (乙) 手寫向量化 —— 與 KARST-127/129 同一套會計

數據:experiments/2026-08-31-fear-greed/prices_daily.parquet(yfinance auto_adjust=True,
含息)。回報端不准另抓數據(票面明文)。
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import vectorbt as vbt

HERE = Path(__file__).resolve().parent
PRICES = HERE.parent / "2026-08-31-fear-greed" / "prices_daily.parquet"

SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
SPY = "SPY"
N_HOLD = 3
COST_BP = 10.0

# ── 掃描面 ────────────────────────────────────────────────────────────
RSI_LOOKBACKS = (5, 7, 10, 14, 21, 30, 45, 60)
RSI_THRESH_LOOKBACKS = (14, 21, 60)
RSI_THRESH_HIGH = (50.0, 60.0, 70.0)
RSI_THRESH_LOW = (50.0, 40.0, 30.0)

MA_DIST_LENGTHS = (20, 50, 100, 150, 200, 250)
MA_PAIRS = ((5, 20), (10, 50), (20, 50), (10, 100),
            (20, 100), (20, 200), (50, 100), (50, 200))

DIRECTIONS = ("high", "low")     # high = 指標值高者順勢揸;low = 指標值低者逆勢揸

WARMUP_DAYS = 350                # 最長 MA 250 + Wilder RSI60 平滑穩定所需,全格統一


# ── 指標 ──────────────────────────────────────────────────────────────
def wilder_rsi(close: pd.DataFrame, length: int) -> pd.DataFrame:
    """Wilder 原版 RSI:平均升幅/跌幅用 alpha = 1/L 的遞歸平滑。"""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    # 全期無跌幅 → RSI 定義為 100
    rsi = rsi.where(avg_loss.notna(), np.nan)
    rsi = rsi.mask((avg_loss == 0.0) & (avg_gain > 0.0), 100.0)
    return rsi


def sma(close: pd.DataFrame, length: int) -> pd.DataFrame:
    return close.rolling(length, min_periods=length).mean()


# ── 主程序 ────────────────────────────────────────────────────────────
def main() -> int:
    if not PRICES.exists():
        raise SystemExit(
            f"缺檔,響亮失敗:{PRICES} 不存在。"
            "先跑 experiments/2026-08-31-fear-greed/fetch_prices.py 重新生成,不准另抓新數據。"
        )

    px = pd.read_parquet(PRICES)
    close = px.pivot(index="date", columns="ticker", values="close")
    opn = px.pivot(index="date", columns="ticker", values="open")
    cols = SECTORS + [SPY]
    missing = [c for c in cols if c not in close.columns]
    if missing:
        raise SystemExit(f"缺 ticker,響亮失敗:{missing}")
    close = close[cols].dropna()
    opn = opn.loc[close.index, cols]
    dates = close.index
    m = len(dates)
    close_a, open_a = close.to_numpy(), opn.to_numpy()

    sec_idx = np.array([cols.index(s) for s in SECTORS])
    spy_col = cols.index(SPY)

    me_pos = (pd.Series(np.arange(m), index=dates)
              .groupby([dates.year, dates.month]).last().to_numpy())
    me_labels = [dates[p].strftime("%Y-%m") for p in me_pos]

    # ── 先算全部指標(日線),再喺月末取樣 ─────────────────────────────
    sec_close = close[SECTORS]
    scores: dict[str, np.ndarray] = {}          # 名 → (K, 9) 月末指標值

    for L in sorted(set(RSI_LOOKBACKS) | set(RSI_THRESH_LOOKBACKS)):
        scores[f"rsi{L}"] = wilder_rsi(sec_close, L).to_numpy()[me_pos]

    for L in MA_DIST_LENGTHS:
        d = sec_close / sma(sec_close, L) - 1.0
        scores[f"madist{L}"] = d.to_numpy()[me_pos]

    for s, l in MA_PAIRS:
        d = sma(sec_close, s) / sma(sec_close, l) - 1.0
        scores[f"maxo{s}_{l}"] = d.to_numpy()[me_pos]

    me_sec_close = sec_close.to_numpy()[me_pos]
    K = len(me_pos)
    mom121 = np.full((K, len(SECTORS)), np.nan)
    for k in range(12, K):
        mom121[k] = me_sec_close[k - 1] / me_sec_close[k - 12] - 1.0
    scores["mom12_1"] = mom121

    # ── 共同評分期:全部格子都有指標、都有成交價 ───────────────────────
    k0 = next(k for k in range(K) if me_pos[k] >= WARMUP_DAYS and k >= 12)
    kmax = K - 2
    while me_pos[kmax + 1] + 1 >= m:
        kmax -= 1
    ks = np.arange(k0, kmax + 1)
    n_per = len(ks)

    for name, arr in scores.items():
        bad = np.isnan(arr[ks]).sum()
        if bad:
            raise SystemExit(f"指標 {name} 喺評分期內有 {bad} 個 NaN,響亮失敗")

    exec_rows = np.array([me_pos[k] + 1 for k in ks] + [me_pos[kmax + 1] + 1])
    exec_px = pd.DataFrame(open_a[exec_rows], columns=cols,
                           index=pd.DatetimeIndex(dates[exec_rows]))

    # ── 逐格砌目標權重 ─────────────────────────────────────────────────
    combos: list[dict] = []

    def add(family: str, label: str, score_key: str, direction: str,
            thresh: float | None = None, note: str = ""):
        combos.append(dict(family=family, label=label, score=score_key,
                           direction=direction, thresh=thresh, note=note))

    for L in RSI_LOOKBACKS:
        for d in DIRECTIONS:
            add("rsi", f"RSI{L}-{d}", f"rsi{L}", d)
    for L in MA_DIST_LENGTHS:
        for d in DIRECTIONS:
            add("ma_dist", f"MAD{L}-{d}", f"madist{L}", d)
    for s, l in MA_PAIRS:
        for d in DIRECTIONS:
            add("ma_cross", f"MAX{s}x{l}-{d}", f"maxo{s}_{l}", d)
    for d in DIRECTIONS:
        add("ref", f"MOM12_1-{d}", "mom12_1", d, note="參照格,非候選")
    for L in RSI_THRESH_LOOKBACKS:
        for T in RSI_THRESH_HIGH:
            add("rsi_thresh", f"RSI{L}>={T:g}-high", f"rsi{L}", "high", T,
                note="含擇時成分,不入平原判讀")
        for T in RSI_THRESH_LOW:
            add("rsi_thresh", f"RSI{L}<={T:g}-low", f"rsi{L}", "low", T,
                note="含擇時成分,不入平原判讀")

    weight_blocks, labels, spy_fill_months = [], [], []
    picks_log = []
    for c in combos:
        sc = scores[c["score"]]
        w = np.zeros((n_per + 1, len(cols)))
        n_spy_fill = 0
        for row, k in enumerate(ks):
            v = sc[k]
            sign = -1.0 if c["direction"] == "high" else 1.0   # argsort 升序
            order = np.argsort(sign * v, kind="stable")
            if c["thresh"] is None:
                top = order[:N_HOLD]
                w[row, sec_idx[top]] = 1.0 / N_HOLD
            else:
                elig = (v >= c["thresh"]) if c["direction"] == "high" else (v <= c["thresh"])
                cand = [i for i in order if elig[i]][:N_HOLD]
                for i in cand:
                    w[row, sec_idx[i]] = 1.0 / N_HOLD
                if len(cand) < N_HOLD:
                    w[row, spy_col] += (N_HOLD - len(cand)) / N_HOLD
                    n_spy_fill += 1
                top = np.array(cand, dtype=int)
            picks_log.append({
                "combo": c["label"], "decide_month": me_labels[k],
                "holding_month": me_labels[k + 1],
                "picks": "|".join(SECTORS[i] for i in top) if len(top) else "",
                "spy_fill_w": round(float(w[row, spy_col]), 4),
                "score_top": "|".join(f"{v[i]:.4f}" for i in top) if len(top) else "",
            })
        w[-1] = w[-2]
        weight_blocks.append(w)
        labels.append(c["label"])
        spy_fill_months.append(n_spy_fill)

    # ── (乙) 手寫向量化會計 ────────────────────────────────────────────
    px_arr = exec_px.to_numpy()
    rets = px_arr[1:] / px_arr[:-1] - 1.0                   # (n_per, 10)
    spy_ret = rets[:, spy_col].copy()
    spy_ret[0] -= COST_BP / 10000.0                          # 基線期初收一次
    ew9_ret = rets[:, sec_idx].mean(axis=1).copy()
    ew9_ret[0] -= COST_BP / 10000.0

    hand, turns = {}, {}
    for lab, w in zip(labels, weight_blocks):
        wt = w[:n_per]
        gross = (wt * rets).sum(axis=1)
        turn = np.abs(np.diff(np.vstack([np.zeros((1, len(cols))), wt]), axis=0)).sum(axis=1) / 2
        turn[0] = 1.0
        hand[lab] = gross - turn * COST_BP / 10000.0
        turns[lab] = turn

    # ── (甲) vectorBT ─────────────────────────────────────────────────
    big_w = np.concatenate(weight_blocks, axis=1)
    mi = pd.MultiIndex.from_tuples(
        [(lab, t) for lab in labels for t in cols], names=["combo", "ticker"])
    size = pd.DataFrame(big_w, index=exec_px.index, columns=mi)
    price = pd.concat({lab: exec_px for lab in labels}, axis=1)
    price.columns.names = ["combo", "ticker"]
    price = price[mi]

    pf = vbt.Portfolio.from_orders(
        close=price, size=size, size_type="targetpercent",
        group_by="combo", cash_sharing=True, call_seq="auto",
        fees=COST_BP / 2 / 10000.0, init_cash=100.0, freq="30D",
    )
    vbt_rets = pf.returns()

    # ── 匯總 ─────────────────────────────────────────────────────────
    def cagr(r):
        return (np.prod(1.0 + r) ** (12.0 / len(r)) - 1.0) * 100

    def maxdd(r):
        eq = np.cumprod(1.0 + r)
        return float((eq / np.maximum.accumulate(eq) - 1.0).min() * 100)

    spy_cagr = cagr(spy_ret)
    ew9_cagr = cagr(ew9_ret)

    rows = []
    for c, lab, nfill in zip(combos, labels, spy_fill_months):
        h = hand[lab]
        v = vbt_rets[lab].to_numpy()
        v = v[-len(h):] if len(v) > len(h) else v
        d = h - spy_ret
        sd = d.std(ddof=1)
        t = d.mean() / (sd / math.sqrt(len(d))) if sd > 0 else float("nan")
        d9 = h - ew9_ret
        s9 = d9.std(ddof=1)
        t9 = d9.mean() / (s9 / math.sqrt(len(d9))) if s9 > 0 else float("nan")
        # 子期間切割(文獻關 §1.7 第 2 條事前寫死:要求切開的兩段分別都要贏)
        half = len(h) // 2
        seg = {}
        for tag, sl in (("h1", slice(0, half)), ("h2", slice(half, None))):
            hh, ss = h[sl], spy_ret[sl]
            dd = hh - ss
            sd = dd.std(ddof=1)
            seg[f"excess_cagr_pp_{tag}"] = round(cagr(hh) - cagr(ss), 3)
            seg[f"paired_t_{tag}"] = (round(float(dd.mean() / (sd / math.sqrt(len(dd)))), 3)
                                      if sd > 0 else float("nan"))
        rows.append({**seg,
            "family": c["family"], "combo": lab, "direction": c["direction"],
            "score": c["score"], "thresh": c["thresh"], "note": c["note"],
            "n_periods": len(h),
            "cagr_pct": round(cagr(h), 3),
            "excess_cagr_pp": round(cagr(h) - spy_cagr, 3),
            "paired_t": round(t, 3),
            "excess_vs_ew9_pp": round(cagr(h) - ew9_cagr, 3),
            "paired_t_vs_ew9": round(t9, 3),
            "vol_ann_pct": round(float(h.std(ddof=1) * math.sqrt(12) * 100), 3),
            "maxdd_pct": round(maxdd(h), 2),
            "avg_turnover": round(float(turns[lab].mean()), 4),
            "spy_fill_months": nfill,
            "vbt_cagr_pct": round(cagr(v), 3),
            "vbt_excess_cagr_pp": round(cagr(v) - spy_cagr, 3),
            "vbt_minus_hand_pp": round(cagr(v) - cagr(h), 3),
        })

    grid = pd.DataFrame(rows)

    # ── 鄰域平均(CONTEXT.md:只沿連續軸取,本倉一律包含自己那一格)──────
    # 用途:判平原定孤峰。鄰域平均遠低於自己那格 = 孤峰。
    nb = {}
    for fam, key in (("rsi", "rsi"), ("ma_dist", "madist")):
        for d in DIRECTIONS:
            sub = [c for c in combos if c["family"] == fam and c["direction"] == d]
            axis = sorted(sub, key=lambda c: int(c["score"].replace(key, "")))
            for i, c in enumerate(axis):
                nbrs = axis[max(0, i - 1): i + 2]
                nb[c["label"]] = float(np.mean([
                    grid.loc[grid.combo == n["label"], "excess_cagr_pp"].iloc[0] for n in nbrs]))
    for d in DIRECTIONS:
        sub = [c for c in combos if c["family"] == "ma_cross" and c["direction"] == d]
        pairs = {c["label"]: tuple(int(x) for x in
                                   c["score"].replace("maxo", "").split("_")) for c in sub}
        shorts = sorted({p[0] for p in pairs.values()})
        longs = sorted({p[1] for p in pairs.values()})
        for lab, (s, l) in pairs.items():
            si, li = shorts.index(s), longs.index(l)
            adj_s = {shorts[j] for j in (si - 1, si, si + 1) if 0 <= j < len(shorts)}
            adj_l = {longs[j] for j in (li - 1, li, li + 1) if 0 <= j < len(longs)}
            nbrs = [k for k, (s2, l2) in pairs.items()
                    if (s2 == s and l2 in adj_l) or (l2 == l and s2 in adj_s)]
            nb[lab] = float(np.mean([
                grid.loc[grid.combo == k, "excess_cagr_pp"].iloc[0] for k in nbrs]))
    grid["neighbourhood_mean_pp"] = grid["combo"].map(lambda c: round(nb[c], 3) if c in nb else None)
    grid["peak_minus_neighbourhood_pp"] = (grid["excess_cagr_pp"] - grid["neighbourhood_mean_pp"]).round(3)

    grid.to_csv(HERE / "ta_sweep.csv", index=False, encoding="utf-8")
    picks = pd.DataFrame(picks_log)
    # 全量逐月持倉 1MB 以上,不入 git(跑本腳本即重新生成);
    # 入倉的是「主掃描超額最高八格 + 兩個參照格」的精簡版,規則揀不是手揀。
    picks.to_csv(HERE / "monthly_picks.csv", index=False, encoding="utf-8")
    focus = (grid[grid.family.isin(["rsi", "ma_dist", "ma_cross"])]
             .nlargest(8, "excess_cagr_pp")["combo"].tolist()
             + grid[grid.family == "ref"]["combo"].tolist())
    picks[picks.combo.isin(focus)].to_csv(
        HERE / "monthly_picks_focus.csv", index=False, encoding="utf-8")

    # 全景圖數表:逐族 pivot
    def dump(fam, index_col, fname):
        sub = grid[grid.family == fam].copy()
        if sub.empty:
            return
        sub["_ix"] = sub["combo"].map(lambda s: s.split("-")[0])
        for metric in ("excess_cagr_pp", "paired_t", "vbt_excess_cagr_pp", "excess_vs_ew9_pp"):
            sub.pivot(index="_ix", columns="direction", values=metric).to_csv(
                HERE / f"panorama_{fname}_{metric}.csv", encoding="utf-8")

    dump("rsi", "combo", "rsi")
    dump("ma_dist", "combo", "ma_dist")
    dump("ma_cross", "combo", "ma_cross")
    dump("rsi_thresh", "combo", "rsi_thresh")

    # 均線族是不是動能包裝:與 12-1 動能參照格逐月回報相關
    corr_rows = []
    for c, lab in zip(combos, labels):
        if c["family"] in ("ref",):
            continue
        ref = hand["MOM12_1-high"]
        corr_rows.append({"combo": lab, "family": c["family"],
                          "corr_monthly_vs_mom12_1_high":
                              round(float(np.corrcoef(hand[lab], ref)[0, 1]), 4)})
    pd.DataFrame(corr_rows).to_csv(HERE / "corr_vs_momentum.csv", index=False, encoding="utf-8")

    # ── 主控台報告 ────────────────────────────────────────────────────
    print(f"評分期:{n_per} 個持有月({me_labels[k0+1]} .. {me_labels[kmax+1]}),"
          f"全部 {len(combos)} 格固定同一段")
    print(f"SPY 買入持有(含息,期初收 10bp)年化 {spy_cagr:.2f}% | "
          f"等權九隻年化 {ew9_cagr:.2f}%")
    dv = grid["vbt_minus_hand_pp"].abs()
    print(f"vectorBT 對手寫:年化差 中位 {dv.median():.4f}pp 最大 {dv.max():.4f}pp "
          f"(相關 {np.corrcoef(grid.excess_cagr_pp, grid.vbt_excess_cagr_pp)[0,1]:.4f})")

    for fam, title in (("rsi", "甲族 RSI 橫截面排名"),
                       ("ma_dist", "乙族(b1) 價格對均線距離"),
                       ("ma_cross", "乙族(b2) 短長均線差"),
                       ("ref", "參照格"),
                       ("rsi_thresh", "旁支 RSI 門檻(含擇時成分,不入平原判讀)")):
        sub = grid[grid.family == fam]
        if sub.empty:
            continue
        print(f"\n— {title}(年化超額 pp / 配對 t,對 SPY)—")
        for d in DIRECTIONS:
            s2 = sub[sub.direction == d]
            if s2.empty:
                continue
            cells = " ".join(
                f"{r.combo.split('-')[0]}:{r.excess_cagr_pp:+6.2f}/{r.paired_t:+5.2f}"
                for r in s2.itertuples())
            print(f"  [{d:>4}] {cells}")

    core = grid[grid.family.isin(["rsi", "ma_dist", "ma_cross"])]
    b = core.loc[core.excess_cagr_pp.idxmax()]
    w = core.loc[core.excess_cagr_pp.idxmin()]
    print(f"\n主掃描 {len(core)} 格 | 最高 {b.combo}:{b.excess_cagr_pp:+.2f}pp(t {b.paired_t:+.2f})")
    print(f"           最低 {w.combo}:{w.excess_cagr_pp:+.2f}pp(t {w.paired_t:+.2f})")
    print(f"配對 t 範圍 {core.paired_t.min():+.2f} ~ {core.paired_t.max():+.2f} | "
          f"|t|>=2 格數 {(core.paired_t.abs() >= 2).sum()}/{len(core)} | "
          f"超額為正格數 {(core.excess_cagr_pp > 0).sum()}/{len(core)}")

    print("\n— 平原檢定:鄰域平均(只沿連續軸,含自己那格)與子期間切割 —")
    top = core.sort_values("excess_cagr_pp", ascending=False).head(8)
    print("  格           超額pp   t     鄰域均pp  自己減鄰域  前半pp/t      後半pp/t")
    for r in top.itertuples():
        print(f"  {r.combo:<14}{r.excess_cagr_pp:+6.2f} {r.paired_t:+5.2f} "
              f"{r.neighbourhood_mean_pp:+8.2f} {r.peak_minus_neighbourhood_pp:+9.2f}  "
              f"{r.excess_cagr_pp_h1:+6.2f}/{r.paired_t_h1:+5.2f} "
              f"{r.excess_cagr_pp_h2:+6.2f}/{r.paired_t_h2:+5.2f}")
    both = core[(core.excess_cagr_pp_h1 > 0) & (core.excess_cagr_pp_h2 > 0)]
    print(f"  兩段子期間都為正的格數:{len(both)}/{len(core)}"
          + (f" → {', '.join(both.combo)}" if len(both) else ""))

    cr = pd.DataFrame(corr_rows)
    for fam in ("ma_dist", "ma_cross", "rsi"):
        s = cr[cr.family == fam]["corr_monthly_vs_mom12_1_high"]
        print(f"與 12-1 動能(high)逐月回報相關 [{fam}]:"
              f"中位 {s.median():+.3f} 範圍 {s.min():+.3f}~{s.max():+.3f}")

    summary = {
        "n_periods": int(n_per),
        "score_window": [me_labels[k0 + 1], me_labels[kmax + 1]],
        "n_cells_total": len(combos),
        "n_cells_core": int(len(core)),
        "spy_cagr_pct": round(spy_cagr, 3),
        "ew9_cagr_pct": round(ew9_cagr, 3),
        "vbt_vs_hand_max_abs_pp": round(float(dv.max()), 4),
        "core_t_min": float(core.paired_t.min()), "core_t_max": float(core.paired_t.max()),
        "core_n_abs_t_ge_2": int((core.paired_t.abs() >= 2).sum()),
        "core_n_excess_pos": int((core.excess_cagr_pp > 0).sum()),
        "best_core": {"combo": b.combo, "excess_cagr_pp": float(b.excess_cagr_pp),
                      "paired_t": float(b.paired_t)},
        "worst_core": {"combo": w.combo, "excess_cagr_pp": float(w.excess_cagr_pp),
                       "paired_t": float(w.paired_t)},
        "data_file": str(PRICES), "cost_bp": COST_BP, "n_hold": N_HOLD,
        "warmup_days": WARMUP_DAYS,
    }
    (HERE / "results.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
