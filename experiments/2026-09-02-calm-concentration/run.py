"""KARST-143:平穩六隻(低波動代理)的波動拖累下限,加 D-116 回調入場笨規則。

規格見同目錄 PLAN.md(跑數前已獨立 commit,commit 7df5e8d)。
只讀倉內現成原料,不接任何新數據源,不碰生產庫。

對齊紀律:分數用截至月底 t 的資料,回報一律取 t+1 月(見 PLAN 第三節)。
"""
from __future__ import annotations

import json
import pathlib
from collections import Counter

import numpy as np
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

ORACLE = HERE.parent / "2026-09-01-stock-oracle-curve"
FWD = HERE.parent / "2026-09-02-forward-yield-build"

TOP_N = 3
HOLD_M = 6
MIN_MEMBERS = 8
VOL_LONG = 36
VOL_SHORT = 24
SIDE_BP_MAIN = 15.0
SIDE_BP_GRID = [0.0, 15.0, 25.0, 50.0]
N_PATHS = 2000
SEED = 20260902
DIP_ENTRY = 0.90   # 低過 6 個月高位 10% 以上
DIP_EXIT = 0.95    # 返到高位 95% 就走
DIP_WIN = 6


# ------------------------------------------------------------------ 載入清洗
def load_monthly():
    """KARST-139 main 篩,判準原封不動搬過來。"""
    m = pd.read_parquet(ORACLE / "data" / "stock_monthly.parquet")
    dm = pd.read_parquet(ORACLE / "data" / "day_moves.parquet")
    sp = pd.read_parquet(ORACLE / "data" / "splits.parquet")
    explained = set()
    for s, me in zip(sp["symbol"], sp["month_end"]):
        for k in (-1, 0, 1):
            explained.add((s, me + pd.offsets.MonthEnd(k) if k else me))
    bad = dm[dm["max_abs_day"] >= 1.0]
    bad = [(s, me) for s, me in zip(bad["symbol"], bad["month_end"])
           if (s, me) not in explained]
    cnt = pd.Series([s for s, _ in bad]).value_counts()
    drop_syms = sorted(cnt[cnt >= 3].index.tolist())
    m = m[~m["symbol"].isin(drop_syms)].copy()
    cells = {(s, me) for s, me in bad if s not in drop_syms}
    keep = [(s, me) not in cells for s, me in zip(m["symbol"], m["month_end"])]
    m = m[keep].copy()
    return m, drop_syms


def cagr(x):
    return float(np.prod(1.0 + x) ** (12.0 / len(x)) - 1.0)


def cagr_rows(x):
    return np.prod(1.0 + x, axis=1) ** (12.0 / x.shape[1]) - 1.0


def arith_ann(x):
    return float((1.0 + np.mean(x)) ** 12 - 1.0)


def maxdd(x):
    eq = np.cumprod(1.0 + x)
    return float((eq / np.maximum.accumulate(eq) - 1.0).min())


def apply_cost(gross, side_bp, turnover):
    c = np.asarray(turnover) * 2.0 * side_bp / 10000.0
    return (1.0 + gross) * (1.0 - c) - 1.0


def stats_block(gross, univ, turnover) -> dict:
    a_ann, g_ann = arith_ann(gross), cagr(gross)
    ua, ug = arith_ann(univ), cagr(univ)
    d = {
        "月數": len(gross),
        "算術月均%": round(float(np.mean(gross)) * 100, 4),
        "月度標準差%": round(float(np.std(gross, ddof=1)) * 100, 3),
        "算術年化%": round(a_ann * 100, 2),
        "幾何年化(零成本)%": round(g_ann * 100, 2),
        "絕對波動拖累pp": round((a_ann - g_ann) * 100, 2),
        "增量拖累(對全宇宙等權)pp": round(((a_ann - g_ann) - (ua - ug)) * 100, 2),
        "最大跌幅%": round(maxdd(gross) * 100, 1),
        "平均換手率%": round(float(np.mean(turnover)) * 100, 1),
    }
    for bp in SIDE_BP_GRID:
        d[f"淨年化@{int(bp)}bp%"] = round(cagr(apply_cost(gross, bp, turnover)) * 100, 2)
    d["淨年化@15bp強制全換%"] = round(cagr(apply_cost(gross, SIDE_BP_MAIN, 1.0)) * 100, 2)
    return d


# ------------------------------------------------------------------ 分數面板
def vol_score(ret_piv: pd.DataFrame) -> pd.DataFrame:
    """月底 t 的過去 36(不足用 24)個月月度回報標準差;窗口內須全部非空。"""
    v36 = ret_piv.rolling(VOL_LONG, min_periods=VOL_LONG).std(ddof=1)
    v24 = ret_piv.rolling(VOL_SHORT, min_periods=VOL_SHORT).std(ddof=1)
    return v36.where(v36.notna(), v24)


def long_form(piv: pd.DataFrame, name: str) -> pd.DataFrame:
    s = piv.stack().dropna().rename(name).reset_index()
    s.columns = ["month_end", "symbol", name]
    return s


# ------------------------------------------------------------------ 主流程
def build(score: pd.DataFrame, score_col: str, ascending: bool, sector: dict,
          fwd_ret: pd.DataFrame):
    """score 帶 symbol/month_end/<score_col>(分數在 t);回報取 t+1。

    ascending=True 代表分數愈細愈好(波動);False 代表愈大愈好。
    """
    j = score.merge(fwd_ret, on=["symbol", "month_end"])   # fwd_ret 已是 t+1 回報
    j["etf"] = j["symbol"].map(sector)
    j = j.dropna(subset=["etf", score_col, "ret_next"])
    months, prev = [], set()
    for me, g in j.groupby("month_end", sort=True):
        cnt = g.groupby("etf").size()
        g2 = g[g["etf"].map(cnt).ge(MIN_MEMBERS)]
        if g2.empty:
            prev = set()
            continue
        g2 = g2.sort_values(score_col, ascending=ascending)
        pool = g2.groupby("etf", sort=False).head(TOP_N)
        if len(pool) < HOLD_M:
            prev = set()
            continue
        hold = (pool.nsmallest(HOLD_M, score_col) if ascending
                else pool.nlargest(HOLD_M, score_col))
        syms = set(hold["symbol"])
        turn = 1.0 if not prev else 1.0 - len(syms & prev) / HOLD_M
        months.append({
            "month_end": me,
            "n_univ": len(g),
            "n_pool": len(pool),
            "hold_ret": float(hold["ret_next"].mean()),
            "hold_syms": tuple(hold["symbol"]),
            "turnover": turn,
            "pool_ew": float(pool["ret_next"].mean()),
            "univ_ew": float(g["ret_next"].mean()),
            "pool_rets": pool["ret_next"].to_numpy(),
            "univ_rets": g["ret_next"].to_numpy(),
            "pool_syms": tuple(pool["symbol"]),
            "pool_score": pool[score_col].to_numpy(),
        })
        prev = syms
    return months


def rand_paths(months, key, rng):
    T = len(months)
    out = np.empty((N_PATHS, T))
    for j, mo in enumerate(months):
        r = mo[key]
        n = len(r)
        k = min(HOLD_M, n)
        idx = np.argsort(rng.random((N_PATHS, n)), axis=1)[:, :k]
        out[:, j] = r[idx].mean(axis=1)
    return out


def family_block(months, bench, label) -> dict:
    idx = pd.DatetimeIndex([x["month_end"] for x in months])
    gross = np.array([x["hold_ret"] for x in months])
    turn = np.array([x["turnover"] for x in months])
    pool_ew = np.array([x["pool_ew"] for x in months])
    univ_ew = np.array([x["univ_ew"] for x in months])
    rng = np.random.default_rng(SEED)
    r_pool = rand_paths(months, "pool_rets", rng)
    r_univ = rand_paths(months, "univ_rets", rng)

    blk = {
        "樣本期(分數月)": f"{idx[0].date()} 至 {idx[-1].date()}",
        "月數": len(months),
        "年數": round(len(months) / 12.0, 2),
        "每月平均宇宙隻數": round(float(np.mean([x["n_univ"] for x in months])), 1),
        "每月平均池隻數": round(float(np.mean([x["n_pool"] for x in months])), 1),
    }
    blk[label] = stats_block(gross, univ_ew, turn)
    blk["同池27等權"] = stats_block(pool_ew, univ_ew, 0.0)
    blk["全宇宙等權"] = stats_block(univ_ew, univ_ew, 0.0)
    for nm, arr in (("同池隨機六隻", r_pool), ("全宇宙隨機六隻", r_univ)):
        cs = cagr_rows(arr)
        med = int(np.argsort(cs)[len(cs) // 2])
        blk[nm] = {
            "月度標準差%(路徑中位)": round(float(np.median(np.std(arr, axis=1, ddof=1))) * 100, 3),
            "算術月均%(平均)": round(float(np.mean(arr)) * 100, 4),
            "幾何年化%(路徑中位,零成本)": round(float(np.median(cs)) * 100, 2),
            "絕對波動拖累pp(中位路徑)": round((arith_ann(arr[med]) - cagr(arr[med])) * 100, 2),
            "淨年化@15bp全換%(路徑中位)": round(
                float(np.median(cagr_rows(apply_cost(arr, SIDE_BP_MAIN, 1.0)))) * 100, 2),
        }
    blk["揀股優勢"] = {
        "六隻算術月均%": round(float(np.mean(gross)) * 100, 4),
        "同池27等權算術月均%": round(float(np.mean(pool_ew)) * 100, 4),
        "優勢pp每月": round(float(np.mean(gross) - np.mean(pool_ew)) * 100, 4),
        "優勢年化pp": round((arith_ann(gross) - arith_ann(pool_ew)) * 100, 2),
        "同池隨機六隻算術月均%": round(float(np.mean(r_pool)) * 100, 4),
        "對隨機六隻優勢pp每月": round(float(np.mean(gross) - np.mean(r_pool)) * 100, 4),
    }
    blk["副B_139原式pp"] = round(
        (cagr(univ_ew) - float(np.median(cagr_rows(r_univ)))) * 100, 2)
    ridx = idx + pd.offsets.MonthEnd(1)
    b = bench.reindex(ridx)
    blk["基準"] = {}
    for c in ("SPY", "XLK"):
        if c in b.columns:
            blk["基準"][c + "%"] = round(cagr(b[c].to_numpy()) * 100, 2)
    return blk, idx, gross, turn, pool_ew, univ_ew


# ------------------------------------------------------------------ D-116 笨規則
def dip_rule(months, close_piv, vol_piv, bench):
    """同一 27 池;低過 6 個月高位 10% 以上先准入場,返到 95% 或跌出池就走。"""
    high6 = close_piv.rolling(DIP_WIN, min_periods=DIP_WIN).max()
    slots = ["SPY"] * HOLD_M
    rows, entries, hold_len = [], 0, Counter()
    live = {}
    for mo in months:
        t = mo["month_end"]
        pool = list(mo["pool_syms"])
        pool_set = set(pool)
        px = close_piv.loc[t] if t in close_piv.index else None
        hi = high6.loc[t] if t in high6.index else None
        if px is None or hi is None:
            continue
        prev = Counter(slots)
        # 1) 離場
        kept = []
        for s in slots:
            if s == "SPY":
                continue
            h, p = hi.get(s, np.nan), px.get(s, np.nan)
            out = (s not in pool_set) or (not np.isfinite(h)) or (not np.isfinite(p)) \
                or (p >= DIP_EXIT * h)
            if out:
                live.pop(s, None)
            else:
                kept.append(s)
        # 2) 入場候選:池內、未持有、跌穿入場線,按波動由低至高
        cand = []
        for s in pool:
            if s in kept:
                continue
            h, p = hi.get(s, np.nan), px.get(s, np.nan)
            if np.isfinite(h) and np.isfinite(p) and p < DIP_ENTRY * h:
                cand.append((float(vol_piv.loc[t, s]), s))
        cand.sort()
        for _, s in cand:
            if len(kept) >= HOLD_M:
                break
            kept.append(s)
            entries += 1
            live[s] = 0
        slots = kept + ["SPY"] * (HOLD_M - len(kept))
        for s in kept:
            hold_len[s] = hold_len.get(s, 0) + 1
        cur = Counter(slots)
        changed = HOLD_M - sum((prev & cur).values())
        rows.append({
            "month_end": t,
            "n_stock": len(kept),
            "turnover": changed / HOLD_M,
            "slots": tuple(slots),
        })
    # 回報
    ret_next = {m["month_end"]: dict(zip(m["pool_syms"], m["pool_rets"])) for m in months}
    full_next = None
    gross, turn, nst = [], [], []
    idx = []
    for r in rows:
        t = r["month_end"]
        nxt = t + pd.offsets.MonthEnd(1)
        if nxt not in bench.index or not np.isfinite(bench.loc[nxt, "SPY"]):
            continue
        vals = []
        ok = True
        for s in r["slots"]:
            if s == "SPY":
                vals.append(float(bench.loc[nxt, "SPY"]))
            else:
                v = ret_next[t].get(s)
                if v is None or not np.isfinite(v):
                    ok = False
                    break
                vals.append(float(v))
        if not ok:
            continue
        idx.append(t)
        gross.append(float(np.mean(vals)))
        turn.append(r["turnover"])
        nst.append(r["n_stock"])
    gross = np.array(gross)
    turn = np.array(turn)
    idx = pd.DatetimeIndex(idx)
    b = bench.reindex(idx + pd.offsets.MonthEnd(1))
    out = {
        "樣本期(分數月)": f"{idx[0].date()} 至 {idx[-1].date()}",
        "月數": len(gross),
        "實際入場次數": entries,
        "平均填滿股票格數": round(float(np.mean(nst)), 2),
        "全部六格皆股票的月份%": round(float(np.mean(np.array(nst) == HOLD_M)) * 100, 1),
        "零格股票(全 SPY)的月份%": round(float(np.mean(np.array(nst) == 0)) * 100, 1),
        "平均每次持有月數": round(sum(hold_len.values()) / max(entries, 1), 2),
        "算術月均%": round(float(np.mean(gross)) * 100, 4),
        "月度標準差%": round(float(np.std(gross, ddof=1)) * 100, 3),
        "算術年化%": round(arith_ann(gross) * 100, 2),
        "幾何年化(零成本)%": round(cagr(gross) * 100, 2),
        "絕對波動拖累pp": round((arith_ann(gross) - cagr(gross)) * 100, 2),
        "最大跌幅%": round(maxdd(gross) * 100, 1),
        "平均換手率%": round(float(np.mean(turn)) * 100, 1),
    }
    for bp in SIDE_BP_GRID:
        out[f"淨年化@{int(bp)}bp%"] = round(cagr(apply_cost(gross, bp, turn)) * 100, 2)
    out["基準"] = {c + "%": round(cagr(b[c].to_numpy()) * 100, 2) for c in ("SPY", "XLK")}
    slot_map = {r["month_end"]: ",".join(r["slots"]) for r in rows}
    pd.DataFrame({
        "month_end": idx, "gross": gross, "turnover": turn, "n_stock": nst,
        "slots": [slot_map[t] for t in idx],
    }).to_csv(OUT / "monthly_dip.csv", index=False, encoding="utf-8-sig")
    return out


# ------------------------------------------------------------------ main
def main() -> None:
    mon, drop_syms = load_monthly()
    sector = dict(zip(mon["symbol"], mon["etf"]))
    bench = pd.read_parquet(ORACLE / "data" / "bench_monthly.parquet")

    ret_piv = mon.pivot_table(index="month_end", columns="symbol", values="ret").sort_index()
    close_piv = mon.pivot_table(index="month_end", columns="symbol", values="close").sort_index()
    vol_piv = vol_score(ret_piv)

    nxt = ret_piv.shift(-1)
    fwd_ret = long_form(nxt, "ret_next")
    vol_long = long_form(vol_piv, "vol")

    report = {"剔走的股票": drop_syms, "口徑": "PLAN.md(commit 7df5e8d)",
              "宇宙隻數(價格面板)": int(mon["symbol"].nunique())}

    # ---------- 主規則:平穩六隻(全價格面板)
    months = build(vol_long, "vol", True, sector, fwd_ret)
    blk, idx, gross, turn, pool_ew, univ_ew = family_block(months, bench, "平穩六隻")
    report["主_平穩六隻"] = blk
    pd.DataFrame({
        "month_end": idx, "six_gross": gross, "turnover": turn,
        "pool_ew": pool_ew, "univ_ew": univ_ew,
        "hold": [",".join(x["hold_syms"]) for x in months],
    }).to_csv(OUT / "monthly_calm.csv", index=False, encoding="utf-8-sig")
    top = Counter()
    for x in months:
        top.update(x["hold_syms"])
    report["主_平穩六隻"]["最常持有前15"] = [f"{s}:{n}" for s, n in top.most_common(15)]

    # ---------- D-116 回調入場笨規則(同一 27 池)
    report["D116_回調入場笨規則"] = dip_rule(months, close_piv, vol_piv, bench)

    # ---------- 對照臂
    fwd = pd.read_parquet(FWD / "data" / "member_forward.parquet")
    fwd = fwd[(fwd["month_end"] >= fwd["joined_on"]) & (fwd["month_end"] < fwd["left_on"])]
    fwd = fwd[fwd["mcap"] > 0].copy()
    fwd["ey_fwd1"] = fwd["earn_fwd1"] / fwd["mcap"]
    fwd_sc = fwd[["symbol", "month_end", "ey_fwd1"]].dropna()

    # 同尺臂:平穩規則限制在 140 的宇宙與月份
    keys = set(zip(fwd_sc["symbol"], fwd_sc["month_end"]))
    vsub = vol_long[[(s, m) in keys for s, m in
                     zip(vol_long["symbol"], vol_long["month_end"])]]
    m2 = build(vsub, "vol", True, sector, fwd_ret)
    if m2:
        b2, *_ = family_block(m2, bench, "平穩六隻")
        report["對照_同尺臂_平穩六隻限140宇宙"] = b2

    # 重對齊臂:140 價值臂(ey_fwd1)
    m3 = build(fwd_sc, "ey_fwd1", False, sector, fwd_ret)
    if m3:
        b3, *_ = family_block(m3, bench, "價值六隻")
        report["對照_重對齊_價值六隻"] = b3

    # 重對齊臂:12-1 動能(分數 t 用 t-11..t-1,回報 t+1)
    mom = (1.0 + ret_piv).shift(1).rolling(11).apply(np.prod, raw=True) - 1.0
    mom_long = long_form(mom, "mom")
    mom_long = mom_long[[(s, m) in keys for s, m in
                         zip(mom_long["symbol"], mom_long["month_end"])]]
    m4 = build(mom_long, "mom", False, sector, fwd_ret)
    if m4:
        b4, *_ = family_block(m4, bench, "動能六隻")
        report["對照_重對齊_動能六隻"] = b4

    (OUT / "results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
