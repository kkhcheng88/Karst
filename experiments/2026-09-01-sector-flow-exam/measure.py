"""KARST-128 板塊輪動族第二考:ETF 申贖流反向計分(主 1 月流 / 副 3 月流)對揸 SPY 基線。

判準先寫死先 commit:experiments/2026-09-01-sector-flow-exam/判準.md
判準提交編號 6ef494c(2026-09-01T01:20:52+08:00),早於本票任何一次數據下載。

流數據:本目錄 flow_units_monthly.csv(fetch_flow.py 由富途月 K QFQ 反推)。
回報數據沿用 KARST-120 抓、122/127 沿用的同一批(第六次重用),回報端不准另抓:
    experiments/2026-08-31-fear-greed/prices_daily.parquet
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PRICES = HERE.parent / "2026-08-31-fear-greed" / "prices_daily.parquet"
FLOW = HERE / "flow_units_monthly.csv"

# ── 判準寫死的參數(不准在此改動,改動要走判準修訂一節)──────────────────
SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
SPY = "SPY"
N_HOLD = 3
COST_BP = 10.0
COST_SENS = [0.0, 5.0, 25.0, 50.0]
K_SIGNAL_NOISE = 2.50          # k(M=4) = Phi^-1(0.99375) = 2.4977
AMPLITUDE_PP = 1.00
HIT_BASE = N_HOLD / len(SECTORS)
MIN_MONTHS_FULL, MIN_SWITCH_FULL = 120, 30
MIN_MONTHS_SEG, MIN_SWITCH_SEG = 48, 12
LAST_HOLDING_MONTH = "2026-07"     # 面板末個完整持有月

BEAR_WINDOWS = [
    ("2000-04", "2002-10"),
    ("2007-11", "2009-03"),
    ("2018-10", "2018-12"),
    ("2020-03", "2020-03"),
    ("2022-02", "2022-10"),
]

# 反向:取流指標最細三隻。lag = 標準化窗長
GROUPS = {
    "main_flow_1m": {"name": "主組 1 個月流", "lag": 1},
    "sub_flow_3m": {"name": "副組 3 個月流", "lag": 3},
}


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


def verdict(strat, spy, ew9, hit, n_switch, min_months, min_switch) -> dict:
    n = len(strat)
    d_s, d_p, d_e = desc(strat), desc(spy), desc(ew9)
    g1 = d_s["mean_pct"] > d_e["mean_pct"]
    g2 = hit > HIT_BASE * 100
    exc_cagr = d_s["cagr_pct"] - d_p["cagr_pct"]
    exc_arith = d_s["mean_pct"] - d_p["mean_pct"]
    se = math.sqrt(d_s["std_pct"] ** 2 / n + d_p["std_pct"] ** 2 / n)
    ratio = exc_arith / se if se > 0 else float("nan")
    diff = np.asarray(strat) - np.asarray(spy)
    t_paired = (diff.mean() / (diff.std(ddof=1) / math.sqrt(n))) if n > 1 else float("nan")
    g3a = exc_cagr >= AMPLITUDE_PP
    g3b = ratio >= K_SIGNAL_NOISE
    g4 = (n >= min_months) and (n_switch >= min_switch)
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
        "count_gate_thresholds": {"min_months": min_months, "min_switches": min_switch},
        "gate1_direction": bool(g1),
        "gate2_information": bool(g2),
        "gate3a_amplitude": bool(g3a),
        "gate3b_signal_noise": bool(g3b),
        "gate4_count": bool(g4),
        "unmeasurable": not g4,
        "pass_all": bool(g1 and g2 and g3a and g3b and g4),
    }


def segment_hit(rows, gid, month_set) -> float:
    hits = slots = 0
    for r in rows:
        if r["group"] != gid or r["holding_month"] not in month_set:
            continue
        slots += N_HOLD
        hits += r["_hits"]
    return hits / slots * 100 if slots else float("nan")


def load_flow():
    """回傳 {ym: {ticker: units}} 與 {ym: {ticker: close}}(前復權)。"""
    units, closes = {}, {}
    with open(FLOW, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            tic = r["code"].split(".", 1)[1]
            if tic not in SECTORS:
                continue
            if not r["units"]:
                continue
            units.setdefault(r["ym"], {})[tic] = float(r["units"])
            closes.setdefault(r["ym"], {})[tic] = float(r["close"]) if r["close"] else None
    return units, closes


def main(first_rank_floor: str = "", out_name: str = "results.json",
         holdings_name: str = "monthly_holdings.csv", tag: str = "pre-written") -> int:
    """first_rank_floor:排名月下限。空字串 = 判準 §1.4 的機械規則(正本判定路徑)。

    非空值只用於**事後參考**(D-083 第 4 條:事後發現不當及格證據),
    寫入另一個結果檔,不覆蓋 results.json。
    """
    if not PRICES.exists():
        raise SystemExit(
            f"缺檔,響亮失敗:{PRICES} 不存在。"
            "先跑 experiments/2026-08-31-fear-greed/fetch_prices.py 重新生成,回報端不准另抓。")
    if not FLOW.exists():
        raise SystemExit(f"缺檔,響亮失敗:{FLOW} 不存在。先跑 fetch_flow.py。")

    units, closes = load_flow()

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

    me_pos = (pd.Series(np.arange(len(dates)), index=dates)
              .groupby([dates.year, dates.month]).last().to_numpy())
    me_labels = [dates[p].strftime("%Y-%m") for p in me_pos]
    label_to_k = {lab: k for k, lab in enumerate(me_labels)}
    open_arr = opn.to_numpy()
    m = len(dates)
    sec_idx = [cols.index(s) for s in SECTORS]
    spy_idx = cols.index(SPY)

    def ym_shift(ym: str, back: int) -> str:
        y, mo = int(ym[:4]), int(ym[5:7])
        idx = y * 12 + (mo - 1) - back
        return f"{idx // 12:04d}-{idx % 12 + 1:02d}"

    def flow_ok(ym: str, lag: int) -> bool:
        prev = ym_shift(ym, lag)
        return (ym in units and prev in units
                and all(t in units[ym] and units[ym][t] > 0 for t in SECTORS)
                and all(t in units[prev] and units[prev][t] > 0 for t in SECTORS))

    # ── §1.4 起始期機械規則:兩組共用同一評分期 ────────────────────────
    cand = []
    for k, lab in enumerate(me_labels):
        if k + 1 >= len(me_pos):
            continue
        if me_labels[k + 1] > LAST_HOLDING_MONTH:
            continue
        if me_pos[k] + 1 >= m or me_pos[k + 1] + 1 >= m:
            continue
        if first_rank_floor and lab < first_rank_floor:
            continue
        if flow_ok(lab, 1) and flow_ok(lab, 3):
            cand.append(k)
    if not cand:
        raise SystemExit("無任何可評分月份,響亮失敗。")
    t0_k = cand[0]
    scoring_ks = [k for k in cand if k >= t0_k]
    skipped = [me_labels[k] for k in range(t0_k, max(cand) + 1) if k not in set(cand)]

    rows, per_group = [], {}
    for gid, cfg in GROUPS.items():
        lag = cfg["lag"]
        months, strat_net, strat_gross, spy_r, ew9_r = [], [], [], [], []
        hits, hit_slots, n_switch = 0, 0, 0
        cost_variants = {f"{c:g}bp": [] for c in COST_SENS}
        prev_w = np.zeros(len(cols))
        first = True
        for k in scoring_ks:
            lab = me_labels[k]
            prev = ym_shift(lab, lag)
            f = np.array([units[lab][t] / units[prev][t] - 1.0 for t in SECTORS])
            # 美元版(口徑對照,不判定):Δu·P(t) / (u(t-lag)·P(t-lag))
            f_usd = np.array([
                (units[lab][t] - units[prev][t]) * (closes[lab].get(t) or np.nan)
                / (units[prev][t] * (closes[prev].get(t) or np.nan))
                for t in SECTORS])
            order = np.argsort(f)              # 反向:由細到大
            top = order[:N_HOLD]

            b, e = me_pos[k] + 1, me_pos[k + 1] + 1
            hold_ret_all = open_arr[e] / open_arr[b] - 1.0
            sec_ret = hold_ret_all[sec_idx]
            spy_ret = hold_ret_all[spy_idx]

            w = np.zeros(len(cols))
            for i in top:
                w[sec_idx[i]] = 1.0 / N_HOLD
            gross = float(sec_ret[top].mean())
            picks = [SECTORS[i] for i in top]
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
            usd_order = np.argsort(f_usd)
            rows.append({
                "group": gid,
                "rank_month": lab,
                "holding_month": me_labels[k + 1],
                "picks": "|".join(picks),
                "flow_top3_pct": "|".join(f"{f[i]*100:.3f}" for i in top),
                "flow_rank_all_pct": "|".join(
                    f"{SECTORS[i]}:{f[i]*100:.3f}" for i in order),
                "usd_version_picks": "|".join(SECTORS[i] for i in usd_order[:N_HOLD]),
                "gross_ret_pct": gross * 100,
                "net_ret_pct": net * 100,
                "spy_ret_pct": spy_net * 100,
                "ew9_ret_pct": float(sec_ret.mean()) * 100,
                "turnover": turnover,
                "_hits": month_hits,
            })
            prev_w, first = w, False

        months = np.array(months)
        sn, sg = np.array(strat_net), np.array(strat_gross)
        sp, ew = np.array(spy_r), np.array(ew9_r)
        hit = hits / hit_slots * 100 if hit_slots else float("nan")

        full = verdict(sn, sp, ew, hit, n_switch, MIN_MONTHS_FULL, MIN_SWITCH_FULL)
        full["gross_cagr_pct"] = desc(sg)["cagr_pct"]
        full["gross_excess_cagr_pp"] = desc(sg)["cagr_pct"] - desc(sp)["cagr_pct"]

        # 樣本外:持有月序列機械對半,奇數前半多一個月
        n = len(months)
        half = (n + 1) // 2
        seg = {}
        for tag, idx in (("in_sample", np.arange(0, half)),
                         ("out_of_sample", np.arange(half, n))):
            mset = set(months[idx])
            gr = [r for r in rows if r["group"] == gid and r["holding_month"] in mset]
            sub_switch, prevp = 0, None
            for r in gr:
                if prevp is not None and r["picks"] != prevp:
                    sub_switch += 1
                prevp = r["picks"]
            seg[tag] = verdict(sn[idx], sp[idx], ew[idx],
                               segment_hit(rows, gid, mset), sub_switch,
                               MIN_MONTHS_SEG, MIN_SWITCH_SEG)
            seg[tag]["period"] = f"{months[idx][0]}..{months[idx][-1]}"

        bears = {}
        for b0, b1 in BEAR_WINDOWS:
            mask = (months >= b0) & (months <= b1)
            if mask.sum() == 0:
                bears[f"{b0}~{b1}"] = {"n_months": 0, "note": "數據未及"}
                continue
            idx = np.where(mask)[0]
            bears[f"{b0}~{b1}"] = {
                "n_months": int(mask.sum()),
                "strategy_cum_pct": float((np.prod(1 + sn[idx]) - 1) * 100),
                "spy_cum_pct": float((np.prod(1 + sp[idx]) - 1) * 100),
                "ew9_cum_pct": float((np.prod(1 + ew[idx]) - 1) * 100),
                "excess_cum_pp": float((np.prod(1 + sn[idx]) - np.prod(1 + sp[idx])) * 100),
                "hit_rate_pct": segment_hit(rows, gid, set(months[mask])),
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

        # 順向臂(口徑對照,不判定):同一指標取最大三隻
        fwd = []
        for k in scoring_ks:
            lab = me_labels[k]
            prev = ym_shift(lab, lag)
            f = np.array([units[lab][t] / units[prev][t] - 1.0 for t in SECTORS])
            topf = np.argsort(-f)[:N_HOLD]
            b, e = me_pos[k] + 1, me_pos[k + 1] + 1
            sec_ret = (open_arr[e] / open_arr[b] - 1.0)[sec_idx]
            fwd.append(float(sec_ret[topf].mean()))
        fwd = np.array(fwd)
        forward_arm = {
            "note": "同一流指標取最大三隻(順向),口徑對照,不參與判定",
            "cagr_pct": desc(fwd)["cagr_pct"],
            "excess_cagr_vs_spy_pp": desc(fwd)["cagr_pct"] - desc(sp)["cagr_pct"],
            "mean_monthly_pct": desc(fwd)["mean_pct"],
        }

        per_group[gid] = {
            "label": cfg["name"],
            "period": f"{months[0]}..{months[-1]}",
            "full_sample": full,
            "segments": seg,
            "bear_windows": bears,
            "non_bear": nonbear,
            "quarterly_secondary_window": quarterly,
            "cost_sensitivity": cost_sens,
            "forward_arm_reference": forward_arm,
            "final_pass": bool(seg["in_sample"]["pass_all"] and seg["out_of_sample"]["pass_all"]),
        }

    out = {
        "ticket": "KARST-128",
        "run_tag": tag,
        "first_rank_floor": first_rank_floor or "(判準 §1.4 機械規則)",
        "criteria_commit": "6ef494cb1b179b80362d367eb2222e8b02facafa",
        "criteria_committed_at": "2026-09-01T01:20:52+08:00",
        "flow_file": str(FLOW),
        "price_file": str(PRICES),
        "first_rank_month": me_labels[t0_k],
        "n_scoring_months": len(scoring_ks),
        "skipped_months_incomplete_universe": skipped,
        "universe": SECTORS, "baseline": SPY,
        "params": {"n_hold": N_HOLD, "cost_bp": COST_BP, "k": K_SIGNAL_NOISE,
                   "amplitude_pp": AMPLITUDE_PP, "hit_base_pct": HIT_BASE * 100,
                   "min_months_full": MIN_MONTHS_FULL, "min_switch_full": MIN_SWITCH_FULL,
                   "min_months_seg": MIN_MONTHS_SEG, "min_switch_seg": MIN_SWITCH_SEG,
                   "direction": "reverse (buy lowest flow)"},
        "groups": per_group,
    }
    (HERE / out_name).write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    (pd.DataFrame(rows).rename(columns={"_hits": "hits_in_top3"})
        .to_csv(HERE / holdings_name, index=False, encoding="utf-8"))

    print(f"首個排名月 {me_labels[t0_k]} | 評分月數 {len(scoring_ks)} | 跳過 {len(skipped)}")
    for gid, g in per_group.items():
        f = g["full_sample"]
        print(f"\n=== {g['label']}  {g['period']} ===")
        print(f"  全樣本 {f['n_months']} 個月 | 策略年化 {f['strategy']['cagr_pct']:.2f}% "
              f"| SPY {f['spy']['cagr_pct']:.2f}% | 等權九隻 {f['ew9']['cagr_pct']:.2f}%")
        print(f"  年化超額 {f['excess_cagr_pp']:+.2f}pp | 月均超額 {f['excess_monthly_pp']:+.3f}pp "
              f"| 訊噪 {f['ratio_vs_se']:.2f}(需 {K_SIGNAL_NOISE}) | 配對 t {f['t_paired']:.2f}")
        print(f"  命中率 {f['hit_rate_pct']:.2f}%(隨機 {HIT_BASE*100:.2f}%) | 換馬 {f['n_switch']} 次")
        print(f"  順向臂年化超額 {g['forward_arm_reference']['excess_cagr_vs_spy_pp']:+.2f}pp(不判定)")
        print(f"  四關:方向{'O' if f['gate1_direction'] else 'X'} "
              f"資訊{'O' if f['gate2_information'] else 'X'} "
              f"幅度{'O' if f['gate3a_amplitude'] else 'X'} "
              f"訊噪{'O' if f['gate3b_signal_noise'] else 'X'} "
              f"次數{'O' if f['gate4_count'] else 'X'}")
        for tag in ("in_sample", "out_of_sample"):
            s = g["segments"][tag]
            print(f"  [{tag}] {s['period']} n={s['n_months']} "
                  f"年化超額 {s['excess_cagr_pp']:+.2f}pp 訊噪 {s['ratio_vs_se']:.2f} "
                  f"命中 {s['hit_rate_pct']:.2f}% -> {'及格' if s['pass_all'] else '不及格'}")
        print(f"  最終(兩段齊過先算):{'及格' if g['final_pass'] else '不及格'}")
    return 0


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) > 1 and _sys.argv[1] == "--posthoc-live":
        print("【事後參考路徑,不參與判定】起點下限 2020-01(反推序列首個活躍月)")
        raise SystemExit(main("2020-01", "results_posthoc_live_era.json",
                              "monthly_holdings_posthoc_live_era.csv",
                              "post-hoc reference, NOT a pass/fail path"))
    raise SystemExit(main())
