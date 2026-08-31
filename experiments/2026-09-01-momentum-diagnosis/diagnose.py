"""KARST-129 板塊動能死因診斷(純診斷,不是考試,不產生任何及格宣稱)。

答兩條實證題:
  題一 板塊對 SPY 的相對線,局部頂底之間平均隔幾耐(zigzag 轉折判定,三檔門檻敏感度)。
  題二 12 個月窗排出來的強板塊,買入那一刻近期相對趨勢是否已經掉頭(1/3/6 個月三個短窗),
       並比較「買入時短趨勢向上 vs 向下」兩組之後一個月的相對成績。

數據沿用 KARST-120 抓、KARST-122/127 沿用的同一批(第六次重用):
    experiments/2026-08-31-fear-greed/prices_daily.parquet
持倉紀錄重用 KARST-127 的產物:
    experiments/2026-09-01-sector-momentum-exam/monthly_holdings.csv
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PRICES = HERE.parent / "2026-08-31-fear-greed" / "prices_daily.parquet"
HOLDINGS = HERE.parent / "2026-09-01-sector-momentum-exam" / "monthly_holdings.csv"

SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
SPY = "SPY"

# 題一:zigzag 轉折幅度門檻(相對線的回撤/反彈幅度)。主口徑 15%,敏感度 10% 與 20%。
ZIGZAG_THRESHOLDS = [0.10, 0.15, 0.20]
PRIMARY_THRESHOLD = 0.15

# 題二:近期相對趨勢的三個短窗(月)
SHORT_WINDOWS = [1, 3, 6]

DAYS_PER_MONTH = 30.4375


def zigzag(values: np.ndarray, dates: pd.DatetimeIndex, theta: float):
    """標準 zigzag 轉折判定:由當前方向的極值起,反向走足 theta(比例)即確認該極值為轉折點。

    回傳 [(轉折點 index, 轉折點 date, 'peak'|'trough', 確認 index), ...],首尾未確認的端點不計。
    確認 index 是「市場走到這一日,先至知道之前那一點是頂/底」的日子——用來避免前視。
    """
    n = len(values)
    if n < 2:
        return []
    pivots = []
    hi_i = lo_i = 0
    direction = 0             # 0 未定, +1 上升段(搵頂), -1 下降段(搵底)
    for i in range(1, n):
        v = values[i]
        if direction == 0:
            if v > values[hi_i]:
                hi_i = i
            if v < values[lo_i]:
                lo_i = i
            if v <= values[hi_i] * (1 - theta):
                pivots.append((hi_i, dates[hi_i], "peak", i))
                direction, lo_i = -1, i
            elif v >= values[lo_i] * (1 + theta):
                pivots.append((lo_i, dates[lo_i], "trough", i))
                direction, hi_i = 1, i
        elif direction == 1:
            if v > values[hi_i]:
                hi_i = i
            elif v <= values[hi_i] * (1 - theta):
                pivots.append((hi_i, dates[hi_i], "peak", i))
                direction, lo_i = -1, i
        else:
            if v < values[lo_i]:
                lo_i = i
            elif v >= values[lo_i] * (1 + theta):
                pivots.append((lo_i, dates[lo_i], "trough", i))
                direction, hi_i = 1, i
    return pivots


def q(a: np.ndarray) -> dict:
    a = np.asarray(a, dtype=float)
    if len(a) == 0:
        nan = float("nan")
        return {"n": 0, "median_months": nan, "mean_months": nan,
                "q1_months": nan, "q3_months": nan, "min_months": nan, "max_months": nan}
    return {
        "n": int(len(a)),
        "median_months": float(np.median(a)),
        "mean_months": float(a.mean()),
        "q1_months": float(np.percentile(a, 25)),
        "q3_months": float(np.percentile(a, 75)),
        "min_months": float(a.min()),
        "max_months": float(a.max()),
    }


def main() -> int:
    if not PRICES.exists():
        raise SystemExit(f"缺檔,響亮失敗:{PRICES}")
    if not HOLDINGS.exists():
        raise SystemExit(f"缺檔,響亮失敗:{HOLDINGS}(應由 KARST-127 產生)")

    px = pd.read_parquet(PRICES)
    close = px.pivot(index="date", columns="ticker", values="close")
    opn = px.pivot(index="date", columns="ticker", values="open")
    cols = SECTORS + [SPY]
    close = close[cols].dropna()
    opn = opn.loc[close.index, cols]
    dates = close.index

    # 相對線:板塊含息價 ÷ SPY 含息價(即「對大市的相對表現曲線」)
    rel = close[SECTORS].div(close[SPY], axis=0)

    # ── 題一:相對週期長度 ──────────────────────────────────────────────
    leg_rows = []
    cycle_summary = {}
    for theta in ZIGZAG_THRESHOLDS:
        tag = f"{theta:.0%}"
        per_sector = {}
        up_all, dn_all, full_all = [], [], []
        for s in SECTORS:
            piv = zigzag(rel[s].to_numpy(), dates, theta)
            ups, dns = [], []
            for a, b in zip(piv, piv[1:]):
                months = (b[1] - a[1]).days / DAYS_PER_MONTH
                leg = "trough_to_peak" if a[2] == "trough" else "peak_to_trough"
                (ups if leg == "trough_to_peak" else dns).append(months)
                leg_rows.append({
                    "threshold": tag, "sector": s, "leg": leg,
                    "start": a[1].date().isoformat(), "end": b[1].date().isoformat(),
                    "months": round(months, 2),
                    "rel_change_pct": round((rel[s].iloc[b[0]] / rel[s].iloc[a[0]] - 1) * 100, 2),
                })
            fulls = [ups[i] + dns[i] for i in range(min(len(ups), len(dns)))]
            per_sector[s] = {"n_pivots": len(piv),
                             "trough_to_peak": q(ups), "peak_to_trough": q(dns),
                             "full_cycle": q(fulls)}
            up_all += ups
            dn_all += dns
            full_all += fulls
        cycle_summary[tag] = {
            "per_sector": per_sector,
            "pooled": {"trough_to_peak": q(up_all), "peak_to_trough": q(dn_all),
                       "full_cycle": q(full_all),
                       "all_legs": q(np.array(up_all + dn_all))},
        }

    pd.DataFrame(leg_rows).to_csv(HERE / "cycle_legs.csv", index=False, encoding="utf-8")

    # ── 題二:買入時點的近期相對趨勢 ────────────────────────────────────
    me_pos = (pd.Series(np.arange(len(dates)), index=dates)
              .groupby([dates.year, dates.month]).last().to_numpy())
    me_labels = [dates[p].strftime("%Y-%m") for p in me_pos]
    label_to_k = {lab: k for k, lab in enumerate(me_labels)}
    rel_me = rel.to_numpy()[me_pos]                 # (K, 9) 月末相對水平
    open_arr = opn.to_numpy()
    m = len(dates)
    sec_idx = {s: i for i, s in enumerate(SECTORS)}
    spy_col = cols.index(SPY)

    hold = pd.read_csv(HOLDINGS, encoding="utf-8")
    entry_rows = []
    for _, r in hold.iterrows():
        if bool(r["retreat_to_spy"]):
            continue                                 # 退 SPY 的月份無板塊可診斷
        hm = str(r["holding_month"])
        k1 = label_to_k[hm]                          # 持有月的月末
        k = k1 - 1                                   # 決策月末(買入前一刻)
        b, e = me_pos[k] + 1, me_pos[k1] + 1         # 次日開市買 → 下月次日開市賣
        if e >= m:
            continue
        for pick in str(r["picks"]).split("|"):
            j = sec_idx[pick]
            row = {"group": r["group"], "holding_month": hm, "pick": pick,
                   "decision_month": me_labels[k]}
            for w in SHORT_WINDOWS:
                row[f"rel_{w}m_pct"] = (rel_me[k, j] / rel_me[k - w, j] - 1) * 100 if k - w >= 0 else np.nan
            ci = cols.index(pick)
            fwd = (open_arr[e, ci] / open_arr[b, ci] - 1) - (open_arr[e, spy_col] / open_arr[b, spy_col] - 1)
            row["fwd_rel_1m_pct"] = fwd * 100
            entry_rows.append(row)

    ent = pd.DataFrame(entry_rows).dropna()

    # 題一與題二的橋:買入那一刻,距離該板塊上一個「已確認的相對頂」有幾多個月。
    # 用主口徑門檻的 zigzag 轉折點;只用決策日之前已經確認的轉折(無前視)。
    piv_by_sector = {s: zigzag(rel[s].to_numpy(), dates, PRIMARY_THRESHOLD) for s in SECTORS}
    since_peak, phase = [], []
    for _, r in ent.iterrows():
        k = label_to_k[r["decision_month"]]
        di = me_pos[k]
        # 只用決策日之前「已經確認」的轉折(p[3] = 確認日),避免前視
        prior = [p for p in piv_by_sector[r["pick"]] if p[3] <= di]
        if not prior:
            since_peak.append(np.nan)
            phase.append("未有轉折")
            continue
        last = prior[-1]
        months = (dates[di] - last[1]).days / DAYS_PER_MONTH
        if last[2] == "peak":
            since_peak.append(months)
            phase.append("已見頂(下降段)")
        else:
            since_peak.append(np.nan)
            phase.append("上升段(未見頂)")
    ent["months_since_last_peak"] = since_peak
    ent["cycle_phase_at_entry"] = phase
    ent.to_csv(HERE / "entry_state.csv", index=False, encoding="utf-8")

    entry_summary = {}
    for gid, g in ent.groupby("group"):
        d = {"n_picks": int(len(g)),
             "period": f"{g['holding_month'].min()}..{g['holding_month'].max()}",
             "windows": {}}
        for w in SHORT_WINDOWS:
            c = f"rel_{w}m_pct"
            down = g[c] < 0
            d["windows"][f"{w}m"] = {
                "share_already_down_pct": float(down.mean() * 100),
                "n_down": int(down.sum()), "n_up": int((~down).sum()),
                "median_rel_trend_pct": float(g[c].median()),
                "fwd_rel_1m_when_up_pct": float(g.loc[~down, "fwd_rel_1m_pct"].mean()),
                "fwd_rel_1m_when_down_pct": float(g.loc[down, "fwd_rel_1m_pct"].mean()),
                "fwd_gap_pp": float(g.loc[~down, "fwd_rel_1m_pct"].mean()
                                    - g.loc[down, "fwd_rel_1m_pct"].mean()),
                "win_share_when_up_pct": float((g.loc[~down, "fwd_rel_1m_pct"] > 0).mean() * 100),
                "win_share_when_down_pct": float((g.loc[down, "fwd_rel_1m_pct"] > 0).mean() * 100),
                # 離散度參考,不是及格判定(本票純診斷)
                "gap_se_pp": float(np.sqrt(
                    g.loc[~down, "fwd_rel_1m_pct"].var(ddof=1) / max((~down).sum(), 1)
                    + g.loc[down, "fwd_rel_1m_pct"].var(ddof=1) / max(down.sum(), 1))),
            }
        d["fwd_rel_1m_overall_pct"] = float(g["fwd_rel_1m_pct"].mean())
        ph = g["cycle_phase_at_entry"].value_counts(normalize=True) * 100
        d["cycle_phase_at_entry_pct"] = {k: float(v) for k, v in ph.items()}
        sp = g["months_since_last_peak"].dropna()
        d["months_since_last_peak"] = {
            "n": int(len(sp)),
            "median": float(sp.median()) if len(sp) else float("nan"),
            "mean": float(sp.mean()) if len(sp) else float("nan"),
        }
        # 用戶假設的正面對照:以多月轉折(zigzag)定義,「已見頂才買」之後一個月是否真的差
        d["fwd_rel_1m_by_phase_pct"] = {
            k: {"n": int((g["cycle_phase_at_entry"] == k).sum()),
                "fwd_rel_1m_pct": float(g.loc[g["cycle_phase_at_entry"] == k,
                                              "fwd_rel_1m_pct"].mean())}
            for k in g["cycle_phase_at_entry"].unique()
        }
        entry_summary[gid] = d

    out = {
        "ticket": "KARST-129",
        "nature": "純診斷,不是考試,不產生任何及格宣稱",
        "data_file": str(PRICES), "holdings_file": str(HOLDINGS),
        "date_range": f"{dates[0]:%Y-%m-%d}..{dates[-1]:%Y-%m-%d}",
        "zigzag_thresholds": [f"{t:.0%}" for t in ZIGZAG_THRESHOLDS],
        "primary_threshold": f"{PRIMARY_THRESHOLD:.0%}",
        "short_windows_months": SHORT_WINDOWS,
        "cycle": cycle_summary,
        "entry_state": entry_summary,
    }
    (HERE / "results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                       encoding="utf-8")

    # ── 主控台摘要 ────────────────────────────────────────────────────
    print("=== 題一 板塊對 SPY 相對線的週期長度(月)===")
    for tag, c in cycle_summary.items():
        p = c["pooled"]
        print(f"  門檻 {tag}: 合計 {p['all_legs']['n']} 段 | "
              f"單邊中位 {p['all_legs']['median_months']:.1f} 平均 {p['all_legs']['mean_months']:.1f} "
              f"(四分位 {p['all_legs']['q1_months']:.1f}~{p['all_legs']['q3_months']:.1f})")
        print(f"           底到頂 中位 {p['trough_to_peak']['median_months']:.1f}(n={p['trough_to_peak']['n']}) | "
              f"頂到底 中位 {p['peak_to_trough']['median_months']:.1f}(n={p['peak_to_trough']['n']}) | "
              f"完整週期 中位 {p['full_cycle']['median_months']:.1f}(n={p['full_cycle']['n']})")
    print(f"\n  逐板塊(主口徑 {PRIMARY_THRESHOLD:.0%},單邊中位月數):")
    ps = cycle_summary[f"{PRIMARY_THRESHOLD:.0%}"]["per_sector"]
    for s in SECTORS:
        a, b = ps[s]["trough_to_peak"], ps[s]["peak_to_trough"]
        print(f"    {s}: 底到頂 {a.get('median_months', float('nan')):.1f}(n={a['n']}) "
              f"頂到底 {b.get('median_months', float('nan')):.1f}(n={b['n']}) "
              f"完整 {ps[s]['full_cycle'].get('median_months', float('nan')):.1f}")

    print("\n=== 題二 買入那一刻,被買板塊的近期相對趨勢 ===")
    for gid, d in entry_summary.items():
        print(f"  [{gid}] {d['n_picks']} 次買入 {d['period']} | "
              f"整體之後一個月相對回報 {d['fwd_rel_1m_overall_pct']:+.3f}%")
        for w in SHORT_WINDOWS:
            x = d["windows"][f"{w}m"]
            print(f"    {w} 個月窗:已向下 {x['share_already_down_pct']:.1f}% "
                  f"(向下 {x['n_down']} / 向上 {x['n_up']}) | "
                  f"之後一個月相對:向上組 {x['fwd_rel_1m_when_up_pct']:+.3f}% "
                  f"向下組 {x['fwd_rel_1m_when_down_pct']:+.3f}% "
                  f"差 {x['fwd_gap_pp']:+.3f}pp(離散度 ±{x['gap_se_pp']:.3f})")
        print(f"    買入時週期位置(主口徑 {PRIMARY_THRESHOLD:.0%} zigzag):"
              + " ".join(f"{k} {v:.1f}%" for k, v in d["cycle_phase_at_entry_pct"].items()))
        s = d["months_since_last_peak"]
        print(f"    已見頂那批,距離上一個相對頂:中位 {s['median']:.1f} 個月 "
              f"平均 {s['mean']:.1f}(n={s['n']})")
        print("    之後一個月相對回報,按買入時週期位置分:"
              + " | ".join(f"{k} {v['fwd_rel_1m_pct']:+.3f}%(n={v['n']})"
                           for k, v in d["fwd_rel_1m_by_phase_pct"].items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
