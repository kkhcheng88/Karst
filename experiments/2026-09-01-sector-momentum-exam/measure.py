"""KARST-127 板塊輪動族第一考:動能計分(主 12-1 / 副 12-7)對揸 SPY 基線。

判準先寫死先 commit:experiments/2026-09-01-sector-momentum-exam/判準.md
判準提交編號 153c6a0(2026-09-01T01:01:53+08:00),早於本腳本任何一次讀取價格快照。

數據沿用 KARST-120 已抓、KARST-122 沿用的同一批(第五次重用):
    experiments/2026-08-31-fear-greed/prices_daily.parquet
若該檔不存在,先跑 experiments/2026-08-31-fear-greed/fetch_prices.py 重新生成。
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PRICES = HERE.parent / "2026-08-31-fear-greed" / "prices_daily.parquet"

# ── 判準寫死的參數(不准在此改動,改動要走判準修訂一節)──────────────────
SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
SPY = "SPY"
N_HOLD = 3                    # 持倉隻數,等權
COST_BP = 10.0                # 換馬成本(基點),乘單邊換手率
COST_SENS = [0.0, 5.0, 25.0, 50.0]
K_SIGNAL_NOISE = 2.24         # k(M=2) = Phi^-1(0.9875)
AMPLITUDE_PP = 1.00           # 幅度值博線:幾何年化超額(百分點)
HIT_BASE = N_HOLD / len(SECTORS)   # 解析隨機基準 = 3/9
MIN_MONTHS = 120
MIN_SWITCHES = 30
OOS_SPLIT = "2013-01"         # 主考場 2000-01..2012-12;樣本外 2013-01..末

BEAR_WINDOWS = [
    ("2000-04", "2002-10"),
    ("2007-11", "2009-03"),
    ("2018-10", "2018-12"),
    ("2020-03", "2020-03"),
    ("2022-02", "2022-10"),
]

GROUPS = {
    "main_12_1": {"name": "主組 12-1", "skip": 1, "look": 12},
    "sub_12_7": {"name": "副組 12-7", "skip": 6, "look": 12},
}


# ── 基本統計 ───────────────────────────────────────────────────────────
def desc(r: np.ndarray) -> dict:
    r = np.asarray(r, dtype=float)
    n = len(r)
    up = r > 0
    return {
        "n_months": int(n),
        "mean_pct": float(r.mean() * 100),
        "median_pct": float(np.median(r) * 100),
        "std_pct": float(r.std(ddof=1) * 100),
        "up_share_pct": float(up.mean() * 100),
        "mean_up_pct": float(r[up].mean() * 100) if up.any() else float("nan"),
        "mean_down_pct": float(r[~up].mean() * 100) if (~up).any() else float("nan"),
        "cagr_pct": float(((np.prod(1.0 + r)) ** (12.0 / n) - 1.0) * 100),
        "worst_month_pct": float(r.min() * 100),
    }


def verdict(strat: np.ndarray, spy: np.ndarray, ew9: np.ndarray,
            hit: float, n_switch: int) -> dict:
    """及格四關,逐關剔。strat/spy/ew9 為同一批月份的月度回報。"""
    n = len(strat)
    d_s, d_p, d_e = desc(strat), desc(spy), desc(ew9)

    # 第一關 方向關:贏等權九隻月均回報
    g1 = d_s["mean_pct"] > d_e["mean_pct"]

    # 第二關 有資訊關:命中率 > 33.33%
    g2 = hit > HIT_BASE * 100

    # 第三關 值博關(雙重)
    exc_cagr = d_s["cagr_pct"] - d_p["cagr_pct"]                 # 3a 幾何年化超額
    exc_arith = d_s["mean_pct"] - d_p["mean_pct"]                # 3b 用算術月均差
    se = math.sqrt(d_s["std_pct"] ** 2 / n + d_p["std_pct"] ** 2 / n)
    ratio = exc_arith / se if se > 0 else float("nan")
    diff = strat - spy
    t_paired = (diff.mean() / (diff.std(ddof=1) / math.sqrt(n))) if n > 1 else float("nan")
    g3a = exc_cagr >= AMPLITUDE_PP
    g3b = ratio >= K_SIGNAL_NOISE

    # 第四關 次數關
    g4 = (n >= MIN_MONTHS) and (n_switch >= MIN_SWITCHES)

    return {
        "n_months": n,
        "strategy": d_s, "spy": d_p, "ew9": d_e,
        "hit_rate_pct": hit, "hit_base_pct": HIT_BASE * 100,
        "excess_cagr_pp": exc_cagr,
        "excess_monthly_pp": exc_arith,
        "excess_monthly_x12_pp": exc_arith * 12,
        "se_pp": se, "ratio_vs_se": ratio, "k_required": K_SIGNAL_NOISE,
        "t_paired": t_paired,
        "excess_cagr_vs_ew9_pp": d_s["cagr_pct"] - d_e["cagr_pct"],
        "n_switch": n_switch,
        "gate1_direction": bool(g1),
        "gate2_information": bool(g2),
        "gate3a_amplitude": bool(g3a),
        "gate3b_signal_noise": bool(g3b),
        "gate4_count": bool(g4),
        "pass_all": bool(g1 and g2 and g3a and g3b and g4),
    }


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

    # 月末交易日的整數位置(月底取樣,沿用 KARST-122 寫法)
    me_pos = (pd.Series(np.arange(len(dates)), index=dates)
              .groupby([dates.year, dates.month]).last().to_numpy())
    me_close = close.to_numpy()[me_pos]                 # (K, 10)
    me_labels = [dates[p].strftime("%Y-%m") for p in me_pos]
    open_arr = opn.to_numpy()
    m = len(dates)
    sec_idx = [cols.index(s) for s in SECTORS]
    spy_idx = cols.index(SPY)

    look = 12
    # 持有月 k:於月末 k 決策,次一交易日開市買,下月末次一交易日開市賣
    valid_k = [k for k in range(look, len(me_pos) - 1)
               if me_pos[k] + 1 < m and me_pos[k + 1] + 1 < m]

    rows = []
    per_group = {}
    for gid, cfg in GROUPS.items():
        skip = cfg["skip"]
        months, strat_net, strat_gross, spy_r, ew9_r = [], [], [], [], []
        hits, hit_slots, n_switch, n_spy_months = 0, 0, 0, 0
        cost_variants = {f"{c:g}bp": [] for c in COST_SENS}
        prev_w = np.zeros(len(cols))
        first = True
        for k in valid_k:
            mom = me_close[k - skip, sec_idx] / me_close[k - look, sec_idx] - 1.0
            order = np.argsort(-mom)
            top = order[:N_HOLD]
            retreat = bool(np.all(mom[top] < 0))

            b, e = me_pos[k] + 1, me_pos[k + 1] + 1          # 開市買 → 開市賣
            hold_ret_all = open_arr[e] / open_arr[b] - 1.0
            sec_ret = hold_ret_all[sec_idx]
            spy_ret = hold_ret_all[spy_idx]

            w = np.zeros(len(cols))
            month_hits = 0
            if retreat:
                w[spy_idx] = 1.0
                gross = spy_ret
                picks = [SPY]
                n_spy_months += 1
            else:
                for i in top:
                    w[sec_idx[i]] = 1.0 / N_HOLD
                gross = float(sec_ret[top].mean())
                picks = [SECTORS[i] for i in top]
                # 命中率:該持有月九隻回報的前三名
                top3_actual = set(np.argsort(-sec_ret)[:N_HOLD].tolist())
                month_hits = sum(1 for i in top if int(i) in top3_actual)
                hits += month_hits
                hit_slots += N_HOLD

            turnover = float(np.abs(w - prev_w).sum() / 2.0)
            if not first and turnover > 1e-9:
                n_switch += 1
            net = gross - turnover * COST_BP / 10000.0
            for c in COST_SENS:
                cost_variants[f"{c:g}bp"].append(gross - turnover * c / 10000.0)

            spy_net = spy_ret - (COST_BP / 10000.0 if first else 0.0)

            months.append(me_labels[k + 1])
            strat_net.append(net)
            strat_gross.append(gross)
            spy_r.append(spy_net)
            ew9_r.append(float(sec_ret.mean()))
            rows.append({
                "group": gid, "holding_month": me_labels[k + 1],
                "picks": "|".join(picks), "retreat_to_spy": retreat,
                "momentum_top3": "|".join(f"{mom[i]*100:.2f}" for i in top),
                "gross_ret_pct": gross * 100, "net_ret_pct": net * 100,
                "spy_ret_pct": spy_net * 100, "ew9_ret_pct": float(sec_ret.mean()) * 100,
                "turnover": turnover, "_hits": month_hits,
            })
            prev_w, first = w, False

        months = np.array(months)
        sn, sg = np.array(strat_net), np.array(strat_gross)
        sp, ew = np.array(spy_r), np.array(ew9_r)
        hit = hits / hit_slots * 100 if hit_slots else float("nan")

        full = verdict(sn, sp, ew, hit, n_switch)
        full["n_spy_retreat_months"] = n_spy_months
        # 毛數(0bp)另報
        full["gross_cagr_pct"] = desc(sg)["cagr_pct"]
        full["gross_excess_cagr_pp"] = desc(sg)["cagr_pct"] - desc(sp)["cagr_pct"]

        # 樣本外切割:命中率同樣分段重算
        seg = {}
        for tag, mask in (("in_sample", months < OOS_SPLIT),
                          ("out_of_sample", months >= OOS_SPLIT)):
            idx = np.where(mask)[0]
            mset = set(months[mask])
            gr = [r for r in rows if r["group"] == gid and r["holding_month"] in mset]
            sub_switch, prevp = 0, None
            for r in gr:
                if prevp is not None and r["picks"] != prevp:
                    sub_switch += 1
                prevp = r["picks"]
            seg[tag] = verdict(sn[idx], sp[idx], ew[idx],
                               segment_hit(rows, gid, mset), sub_switch)
            seg[tag]["period"] = f"{months[mask][0]}..{months[mask][-1]}"

        bears = {}
        for b0, b1 in BEAR_WINDOWS:
            mask = (months >= b0) & (months <= b1)
            if mask.sum() == 0:
                continue
            idx = np.where(mask)[0]
            bears[f"{b0}~{b1}"] = {
                "n_months": int(mask.sum()),
                "strategy_cum_pct": float((np.prod(1 + sn[idx]) - 1) * 100),
                "spy_cum_pct": float((np.prod(1 + sp[idx]) - 1) * 100),
                "ew9_cum_pct": float((np.prod(1 + ew[idx]) - 1) * 100),
                "excess_cum_pp": float((np.prod(1 + sn[idx]) - np.prod(1 + sp[idx])) * 100),
                "hit_rate_pct": segment_hit(rows, gid, set(months[mask])),
                "n_spy_retreat": int(sum(1 for r in rows if r["group"] == gid
                                         and r["holding_month"] in set(months[mask])
                                         and r["retreat_to_spy"])),
            }

        nonbear_mask = np.ones(len(months), dtype=bool)
        for b0, b1 in BEAR_WINDOWS:
            nonbear_mask &= ~((months >= b0) & (months <= b1))
        idx = np.where(nonbear_mask)[0]
        nonbear = {
            "n_months": int(nonbear_mask.sum()),
            "strategy_cagr_pct": desc(sn[idx])["cagr_pct"],
            "spy_cagr_pct": desc(sp[idx])["cagr_pct"],
            "excess_cagr_pp": desc(sn[idx])["cagr_pct"] - desc(sp[idx])["cagr_pct"],
            "hit_rate_pct": segment_hit(rows, gid, set(months[nonbear_mask])),
        }

        # 副評分窗:一季(不參與判定)
        q = pd.DataFrame({"m": pd.PeriodIndex(months, freq="M"),
                          "s": sn, "p": sp}).set_index("m")
        qs = q.groupby(q.index.asfreq("Q")).apply(
            lambda d: pd.Series({"s": np.prod(1 + d["s"].values) - 1,
                                 "p": np.prod(1 + d["p"].values) - 1}))
        quarterly = {
            "n_quarters": int(len(qs)),
            "strategy_mean_pct": float(qs["s"].mean() * 100),
            "spy_mean_pct": float(qs["p"].mean() * 100),
            "excess_mean_pp": float((qs["s"].mean() - qs["p"].mean()) * 100),
            "win_share_pct": float((qs["s"] > qs["p"]).mean() * 100),
        }

        cost_sens = {kk: {"cagr_pct": desc(np.array(v))["cagr_pct"],
                          "excess_cagr_pp": desc(np.array(v))["cagr_pct"] - desc(sp)["cagr_pct"]}
                     for kk, v in cost_variants.items()}

        per_group[gid] = {
            "label": cfg["name"],
            "period": f"{months[0]}..{months[-1]}",
            "full_sample": full,
            "segments": seg,
            "bear_windows": bears,
            "non_bear": nonbear,
            "quarterly_secondary_window": quarterly,
            "cost_sensitivity": cost_sens,
            "final_pass": bool(seg["in_sample"]["pass_all"] and seg["out_of_sample"]["pass_all"]),
        }

    out = {
        "ticket": "KARST-127",
        "criteria_commit": "153c6a056e70ad32694ffaabc22536a3382ba635",
        "criteria_committed_at": "2026-09-01T01:01:53+08:00",
        "data_file": str(PRICES),
        "data_rows": int(len(px)),
        "trading_days": int(len(dates)),
        "date_range": f"{dates[0]:%Y-%m-%d}..{dates[-1]:%Y-%m-%d}",
        "universe": SECTORS, "baseline": SPY,
        "params": {"n_hold": N_HOLD, "cost_bp": COST_BP, "k": K_SIGNAL_NOISE,
                   "amplitude_pp": AMPLITUDE_PP, "hit_base_pct": HIT_BASE * 100,
                   "min_months": MIN_MONTHS, "min_switches": MIN_SWITCHES,
                   "oos_split": OOS_SPLIT},
        "groups": per_group,
    }
    (HERE / "results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    (pd.DataFrame(rows).rename(columns={"_hits": "hits_in_top3"})
        .to_csv(HERE / "monthly_holdings.csv", index=False, encoding="utf-8"))

    for gid, g in per_group.items():
        f = g["full_sample"]
        print(f"\n=== {g['label']}  {g['period']} ===")
        print(f"  全樣本 {f['n_months']} 個月 | 策略年化 {f['strategy']['cagr_pct']:.2f}% "
              f"| SPY {f['spy']['cagr_pct']:.2f}% | 等權九隻 {f['ew9']['cagr_pct']:.2f}%")
        print(f"  年化超額 {f['excess_cagr_pp']:+.2f}pp | 月均超額 {f['excess_monthly_pp']:+.3f}pp "
              f"| 訊噪 {f['ratio_vs_se']:.2f}(需 {K_SIGNAL_NOISE}) | 配對 t {f['t_paired']:.2f}")
        print(f"  命中率 {f['hit_rate_pct']:.2f}%(隨機 {HIT_BASE*100:.2f}%) "
              f"| 換馬 {f['n_switch']} 次 | 退 SPY {f['n_spy_retreat_months']} 個月")
        print(f"  四關:方向{'✓' if f['gate1_direction'] else '✗'} "
              f"資訊{'✓' if f['gate2_information'] else '✗'} "
              f"幅度{'✓' if f['gate3a_amplitude'] else '✗'} "
              f"訊噪{'✓' if f['gate3b_signal_noise'] else '✗'} "
              f"次數{'✓' if f['gate4_count'] else '✗'}")
        for tag in ("in_sample", "out_of_sample"):
            s = g["segments"][tag]
            print(f"  [{tag}] {s['period']} n={s['n_months']} "
                  f"年化超額 {s['excess_cagr_pp']:+.2f}pp 訊噪 {s['ratio_vs_se']:.2f} "
                  f"命中 {s['hit_rate_pct']:.2f}% → {'及格' if s['pass_all'] else '不及格'}")
        print(f"  最終(兩段齊過先算):{'及格' if g['final_pass'] else '不及格'}")
    return 0


def segment_hit(rows, gid, month_set) -> float:
    """該段的命中率,由逐月紀錄重算(退 SPY 的月份不計入分子分母)。"""
    hits = slots = 0
    for r in rows:
        if r["group"] != gid or r["holding_month"] not in month_set:
            continue
        if r["retreat_to_spy"]:
            continue
        slots += N_HOLD
        hits += r["_hits"]
    return hits / slots * 100 if slots else float("nan")


if __name__ == "__main__":
    raise SystemExit(main())
