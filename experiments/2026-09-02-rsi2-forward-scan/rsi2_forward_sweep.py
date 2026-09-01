"""KARST-137:RSI2 後顧對前瞻收益率對照全景掃描(用戶裁決 D-109)。

四條序列臂(KARST-136 交付的 sector_yields.csv):
  ey_lag     後顧盈利收益率
  ey_fwd     前瞻(未來四季預估)
  ey_fwd1    前瞻(未來一季年化,低洩漏對照)
  ey_fwd_hp  前瞻(剔走精度已毀成員)

**只用月底真序列**,不作任何日內或重錨推移(D-108;KARST-135 已證那種砌法混入動量)。

方向(CRITERIA.md 第二節,跑數之前已定):收益率與市盈率方向相反,所以把
收益率序列**取負號**再餵入與 KARST-135 完全相同的引擎,「買最低 RSI2」即等同
「買收益率 RSI2 最高」= 買倍數壓縮得最厲害 = 買便宜,與 135 甲式同一個經濟假設。
鏡像方向(買貴)照掃照報。

輸出:panorama.csv / plateau.csv / best_cells.csv / vbt_check.csv / meta.json
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time

import numpy as np
import pandas as pd
import vectorbt as vbt

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
PRICES = REPO / "experiments" / "2026-08-31-fear-greed" / "prices_daily.parquet"
YIELDS = REPO / "experiments" / "2026-09-02-forward-yield-build" / "sector_yields.csv"
PROD_DB = REPO / "karst.sqlite"

SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
SPY = "SPY"
COLS = SECTORS + [SPY]
NS = len(SECTORS)

COST_BP = 10.0
COST = COST_BP / 10000.0
RSI_WIN = 2
BURN = 5

BAR_SIZES = ["1M", "3M"]
HOLDS = {"1M": [1, 2, 3], "3M": [1, 2]}
N_TOP = [1, 2, 3]
ENTRY = [5, 10, 15, 20, 25, 30, 35, 40]
EXIT = [50, 55, 60, 65, 70, 75, 80, 85, 90, 95]
RSI_KINDS = ["wilder", "simple"]

SERIES_ARMS = ["ey_lag", "ey_fwd", "ey_fwd1", "ey_fwd_hp"]
# 買便宜 = 取負號後跑(買收益率 RSI2 最高);買貴 = 原序列(買收益率 RSI2 最低)
DIRECTIONS = {"買便宜": -1.0, "買貴": +1.0}
SPLIT_DATE = pd.Timestamp("2013-01-01")   # 主切法(CRITERIA 第六節)

# 重用 KARST-135 的 RSI / 引擎 / 統計,逐字相同的實作只此一份
_SRC = REPO / "experiments" / "2026-09-02-rsi2-multifreq-scan" / "rsi2_multifreq_sweep.py"


def _load_engine():
    import importlib.util
    spec = importlib.util.spec_from_file_location("k135", _SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


K135 = _load_engine()
rsi_series = K135.rsi_series
engine = K135.engine
stats = K135.stats
tstat = K135.tstat


def rsi_panel(vals: np.ndarray, kind: str) -> np.ndarray:
    out = np.full(vals.shape, np.nan)
    for j in range(vals.shape[1]):
        out[:, j] = rsi_series(vals[:, j], RSI_WIN, kind)
    return out


def main() -> None:
    t0 = time.time()
    h0 = hashlib.sha256(PROD_DB.read_bytes()).hexdigest()
    print(f"生產庫起始雜湊 {h0[:16]}", flush=True)

    px = pd.read_parquet(PRICES)
    px["date"] = pd.to_datetime(px["date"])
    close = px.pivot(index="date", columns="ticker", values="close")[COLS]
    open_ = px.pivot(index="date", columns="ticker", values="open")[COLS]
    ok = close.notna().all(axis=1) & open_.notna().all(axis=1)
    close, open_ = close[ok], open_[ok]
    dates = close.index
    m = len(dates)
    open_a = open_.to_numpy()
    sec_i = np.array([COLS.index(s) for s in SECTORS])
    spy_i = COLS.index(SPY)
    print(f"日線面板 {m} 個交易日 {dates[0].date()} .. {dates[-1].date()}", flush=True)

    # ---- 月底真序列 → 逐交易日查表(只在該月的 bar 上取用,無任何推移)----
    y = pd.read_csv(YIELDS, parse_dates=["month_end"])
    y["ym"] = y["month_end"].dt.strftime("%Y-%m")
    wmaps = {}
    for arm in SERIES_ARMS:
        w = y.pivot(index="ym", columns="series", values=arm)[SECTORS]
        wmaps[arm] = {k: v.to_numpy() for k, v in w.iterrows()}
    ym_all = np.array([f"{d.year:04d}-{d.month:02d}" for d in dates])

    panels = {}
    for arm in SERIES_ARMS:
        p = np.full((m, NS), np.nan)
        wm = wmaps[arm]
        for i in range(m):
            v = wm.get(ym_all[i])
            if v is not None:
                p[i] = v
        panels[arm] = p
        print(f"  {arm}: 日曆展開後有效格比例 {np.isfinite(p).mean():.4f}", flush=True)

    def bar_positions(size: str) -> np.ndarray:
        s = pd.Series(np.arange(m), index=dates)
        g = (s.groupby([dates.year, dates.month]) if size == "1M"
             else s.groupby([dates.year, dates.quarter]))
        return np.sort(g.last().to_numpy())

    grids = {sz: bar_positions(sz)[bar_positions(sz) + 1 < m] for sz in BAR_SIZES}

    # ---- 統一評分起點:四條臂都有值(主比較窗)----
    prep, starts = {}, []
    for size in BAR_SIZES:
        bp = grids[size]
        pv = {a: panels[a][bp] for a in SERIES_ARMS}
        rs = {}
        for a in SERIES_ARMS:
            for dname, sign in DIRECTIONS.items():
                for kind in RSI_KINDS:
                    rs[(a, dname, kind)] = rsi_panel(sign * pv[a], kind)
        prep[size] = (bp, pv, rs)
        allv = np.ones(len(bp), dtype=bool)
        for a in SERIES_ARMS:
            allv &= np.isfinite(rs[(a, "買便宜", "wilder")]).any(axis=1)
        idx = np.flatnonzero(allv)
        first = min(idx[0] + BURN, len(bp) - 1) if len(idx) else 0
        starts.append(dates[bp[first]])
    START = max(starts)
    print(f"主比較窗統一起點 {START.date()}(四臂齊備 + 各燒 {BURN} 根)", flush=True)

    rows, vbt_rows = [], []

    def run_window(tag: str, arms: list[str], start_ts: pd.Timestamp) -> None:
        for size in BAR_SIZES:
            bp0, pv0, rs0 = prep[size]
            keep = dates[bp0] >= start_ts
            bp = bp0[keep]
            rs = {k: v[keep] for k, v in rs0.items()}
            ep = bp + 1
            nb = len(bp) - 1
            rets = open_a[ep[1:]] / open_a[ep[:-1]] - 1.0
            sec_rets = rets[:, sec_i]
            spy_rets = rets[:, spy_i]
            years = (dates[ep[-1]] - dates[ep[0]]).days / 365.25
            bar_dates = dates[ep[:nb]]
            cut = int(np.searchsorted(bar_dates.to_numpy(),
                                      SPLIT_DATE.to_datetime64()))
            print(f"[{tag}/{size}] {nb} 期 {dates[ep[0]].date()}..{dates[ep[-1]].date()} "
                  f"({years:.2f} 年) 2013 切點在第 {cut} 期", flush=True)

            spy_net = spy_rets.copy()
            spy_net[0] -= COST
            ew_tgt = np.full((nb, NS, 1), 1.0 / NS)
            ew_reb = np.ones((nb, 1), dtype=bool)
            ew_net = engine(ew_tgt, ew_reb, sec_rets)[0][:, 0]
            base = {"spy": spy_net, "ew9": ew_net}
            base_stat = {k: stats(v[:, None], years) for k, v in base.items()}
            for k in base:
                rows.append(dict(window=tag, arm="-", direction="-", bar=size,
                                 rsi_kind="-", style="基線", params=k, n_periods=nb,
                                 start=str(dates[ep[0]].date()),
                                 end=str(dates[ep[-1]].date()), years=round(years, 2),
                                 cagr_pct=round(float(base_stat[k]["cagr"][0]), 4),
                                 maxdd_pct=round(float(base_stat[k]["maxdd"][0]), 3),
                                 exc_spy=np.nan, t_spy=np.nan, exc_ew9=np.nan,
                                 t_ew9=np.nan, exc_spy_h1=np.nan, exc_spy_h2=np.nan,
                                 exc_spy_pre13=np.nan, exc_spy_post13=np.nan,
                                 ann_turnover=np.nan, pct_in_mkt=np.nan, n_rebal=np.nan,
                                 N=np.nan, H=np.nan, E=np.nan, X=np.nan))

            def emit(arm, dname, kind, style, params, res, ki, extra):
                net = res["net"][:, ki]
                st = stats(net[:, None], years)
                turn = res["turn"][:, ki]
                held = res["held"][:, :, ki]
                half = nb // 2
                yr_h = years / 2.0
                h1 = (stats(net[:half, None], yr_h)["cagr"][0]
                      - stats(base["spy"][:half, None], yr_h)["cagr"][0])
                h2 = (stats(net[half:, None], yr_h)["cagr"][0]
                      - stats(base["spy"][half:, None], yr_h)["cagr"][0])
                if 5 < cut < nb - 5:
                    ypre = (bar_dates[cut - 1] - bar_dates[0]).days / 365.25
                    ypost = (bar_dates[nb - 1] - bar_dates[cut]).days / 365.25
                    pre = (stats(net[:cut, None], ypre)["cagr"][0]
                           - stats(base["spy"][:cut, None], ypre)["cagr"][0])
                    post = (stats(net[cut:, None], ypost)["cagr"][0]
                            - stats(base["spy"][cut:, None], ypost)["cagr"][0])
                else:
                    pre = post = np.nan
                rows.append(dict(
                    window=tag, arm=arm, direction=dname, bar=size, rsi_kind=kind,
                    style=style, params=params, n_periods=nb,
                    start=str(dates[ep[0]].date()), end=str(dates[ep[-1]].date()),
                    years=round(years, 2),
                    cagr_pct=round(float(st["cagr"][0]), 4),
                    maxdd_pct=round(float(st["maxdd"][0]), 3),
                    exc_spy=round(float(st["cagr"][0] - base_stat["spy"]["cagr"][0]), 4),
                    t_spy=round(float(tstat((net - base["spy"])[:, None])[0]), 3),
                    exc_ew9=round(float(st["cagr"][0] - base_stat["ew9"]["cagr"][0]), 4),
                    t_ew9=round(float(tstat((net - base["ew9"])[:, None])[0]), 3),
                    exc_spy_h1=round(float(h1), 4), exc_spy_h2=round(float(h2), 4),
                    exc_spy_pre13=round(float(pre), 4) if pre == pre else np.nan,
                    exc_spy_post13=round(float(post), 4) if post == post else np.nan,
                    ann_turnover=round(float(turn.sum() / years), 2),
                    pct_in_mkt=round(float(held.any(axis=1).mean()) * 100, 2),
                    n_rebal=int((turn > 1e-9).sum()),
                    N=extra.get("N", np.nan), H=extra.get("H", np.nan),
                    E=extra.get("E", np.nan), X=extra.get("X", np.nan)))

            for kind in RSI_KINDS:
                for arm in arms:
                    for dname in DIRECTIONS:
                        R = rs[(arm, dname, kind)][:nb]
                        fin = np.isfinite(R)
                        for H in HOLDS[size]:
                            # 甲式
                            K = len(N_TOP)
                            tgt = np.zeros((nb, NS, K))
                            reb = np.zeros((nb, K), dtype=bool)
                            order = np.where(fin, R, np.inf).argsort(axis=1)
                            nval = fin.sum(axis=1)
                            for i in range(0, nb, H):
                                for ki, N in enumerate(N_TOP):
                                    if nval[i] < N:
                                        continue
                                    tgt[i, order[i, :N], ki] = 1.0 / N
                                    reb[i, ki] = True
                            net, turn, held = engine(tgt, reb, sec_rets)
                            res = dict(net=net, turn=turn, held=held)
                            for ki, N in enumerate(N_TOP):
                                emit(arm, dname, kind, "甲", f"N={N},H={H}", res, ki,
                                     dict(N=N, H=H))
                            if kind == "wilder" and tag == "主窗":
                                vbt_rows.extend(vbt_check(size, arm, dname, H, tgt, reb,
                                                          ep, dates, open_a, sec_i,
                                                          years, net))
                            # 乙式
                            nE, nX = len(ENTRY), len(EXIT)
                            KB = nE * nX
                            Ea = np.array(ENTRY, float)[:, None].repeat(nX, 1).ravel()
                            Xa = np.array(EXIT, float)[None, :].repeat(nE, 0).ravel()
                            tgt = np.zeros((nb, NS, KB), dtype=np.float32)
                            reb = np.zeros((nb, KB), dtype=bool)
                            pos = np.zeros((NS, KB), dtype=bool)
                            hold_n = np.zeros((NS, KB), dtype=np.int32)
                            for i in range(nb):
                                rv = R[i][:, None]
                                fv = fin[i][:, None]
                                enter = (~pos) & fv & (rv < Ea[None, :])
                                leave = pos & fv & (hold_n >= H) & (rv > Xa[None, :])
                                newpos = (pos & ~leave) | enter
                                hold_n = np.where(enter, 0, hold_n + 1)
                                cnt = newpos.sum(axis=0)
                                changed = (newpos != pos).any(axis=0)
                                pos = newpos
                                with np.errstate(invalid="ignore", divide="ignore"):
                                    tgt[i] = np.where(cnt[None, :] > 0,
                                                      newpos / np.maximum(cnt[None, :], 1),
                                                      0.0)
                                reb[i] = changed
                            net, turn, held = engine(tgt.astype(float), reb, sec_rets)
                            res = dict(net=net, turn=turn, held=held)
                            for ki in range(KB):
                                emit(arm, dname, kind, "乙",
                                     f"E={int(Ea[ki])},X={int(Xa[ki])},H={H}", res, ki,
                                     dict(E=int(Ea[ki]), X=int(Xa[ki]), H=H))

    run_window("主窗", SERIES_ARMS, START)
    # ey_lag 另報一次全期(明標:不同窗,不可與前瞻臂直接相比)
    lag_start = min(dates[grids[sz][0]] for sz in BAR_SIZES)
    run_window("ey_lag全期", ["ey_lag"], lag_start)

    pan = pd.DataFrame(rows)
    pan.to_csv(HERE / "panorama.csv", index=False, encoding="utf-8-sig")
    vc = pd.DataFrame(vbt_rows)
    vc.to_csv(HERE / "vbt_check.csv", index=False, encoding="utf-8-sig")
    print(f"\npanorama {pan.shape}  vbt對照 {vc.shape} "
          f"最大年化差 {vc['abs_diff'].max():.4f} 百分點", flush=True)

    h1h = hashlib.sha256(PROD_DB.read_bytes()).hexdigest()
    meta = dict(
        ticket="KARST-137", generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        prices=str(PRICES.relative_to(REPO)), yields=str(YIELDS.relative_to(REPO)),
        sectors=SECTORS, cost_bp=COST_BP, rsi_window=RSI_WIN, burn_bars=BURN,
        bar_sizes=BAR_SIZES, holds=HOLDS, n_top=N_TOP, entry=ENTRY, exit=EXIT,
        rsi_kinds=RSI_KINDS, series_arms=SERIES_ARMS,
        directions="買便宜=取負號後買最低RSI2(即買收益率RSI2最高);買貴=鏡像",
        main_window_start=str(START.date()), split_date=str(SPLIT_DATE.date()),
        prod_db_sha256_head16_before=h0[:16], prod_db_sha256_head16_after=h1h[:16],
        prod_db_unchanged=(h0 == h1h),
        panorama_rows=int(len(pan)),
        vbt_max_abs_cagr_diff_pp=round(float(vc["abs_diff"].max()), 5),
        runtime_sec=round(time.time() - t0, 1),
    )
    (HERE / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
    print(f"生產庫收工雜湊 {h1h[:16]} 不變={h0 == h1h}  用時 {meta['runtime_sec']}s")


def vbt_check(size, arm, dname, H, tgt, reb, ep, dates, open_a, sec_i, years, hand_net):
    nbp, ns, K = tgt.shape
    idx = pd.DatetimeIndex(dates[ep[:nbp + 1]])
    pxa = open_a[ep[:nbp + 1]][:, sec_i]
    labels = [f"c{k}" for k in range(K)]
    mi = pd.MultiIndex.from_tuples([(l, s) for l in labels for s in SECTORS],
                                   names=["combo", "ticker"])
    big = np.full((nbp + 1, K * ns), np.nan)
    for k in range(K):
        big[:nbp, k * ns:(k + 1) * ns] = np.where(reb[:, k][:, None], tgt[:, :, k], np.nan)
    pf = vbt.Portfolio.from_orders(
        close=pd.DataFrame(np.tile(pxa, (1, K)), index=idx, columns=mi),
        size=pd.DataFrame(big, index=idx, columns=mi),
        size_type="targetpercent", group_by="combo", cash_sharing=True,
        call_seq="auto", fees=COST / 2.0, init_cash=100.0, freq="1D")
    vr = pf.returns()
    out = []
    for k, N in enumerate(N_TOP):
        v = vr[labels[k]].to_numpy()
        v_cagr = (np.prod(1.0 + v[1:]) ** (1.0 / years) - 1.0) * 100
        h_cagr = (np.prod(1.0 + hand_net[:, k]) ** (1.0 / years) - 1.0) * 100
        out.append(dict(bar=size, arm=arm, direction=dname, style="甲",
                        params=f"N={N},H={H}",
                        hand_cagr=round(float(h_cagr), 4),
                        vbt_cagr=round(float(v_cagr), 4),
                        abs_diff=round(abs(float(h_cagr - v_cagr)), 4)))
    return out


if __name__ == "__main__":
    main()
