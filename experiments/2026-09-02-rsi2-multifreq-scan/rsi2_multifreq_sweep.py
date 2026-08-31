"""KARST-135:RSI2 多頻全景掃描(用戶明令 D-107,倍數線探索第一步)。

RSI 窗固定 2 根 bar。bar 尺寸掃 1D / 3D / 1W / 1M / 3M。
兩臂:mult = 板塊倍數序列(月錨 pe_lag + ETF 日價月內推移);price = ETF 價格序列。
訊號兩式:甲 = 橫截面買 RSI2 最低 N 隻;乙 = 門檻式 RSI2<E 入、>X 出。
持有/調倉窗 H 與 bar 尺寸相稱。成本 10bp 逐次如實計。基線 SPY 含息 + 九隻等權。

方法預登記見 research/2026-09-02-RSI2多頻倍數全景.md 第二節(提交 d16cb29,早於本次執行)。

輸出:
  panorama.csv   逐格成績(兩臂)
  contrast.csv   逐格對照臂比較(重合率、Jaccard、成績差)
  rsi_corr.csv   兩臂 RSI2 讀數相關(bar × 口徑 × 板塊)
  plateau.csv    每族最強格的鄰域穩健性(平原/孤峰)
  vbt_check.csv  vectorBT 對照(甲式全部格)
  meta.json      口徑、樣本期、雜湊
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
MULT_CSV = REPO / "experiments" / "2026-09-02-multiples-oracle-scan" / "sector_multiples.csv"
PROD_DB = REPO / "karst.sqlite"

SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
SPY = "SPY"
COLS = SECTORS + [SPY]
NS = len(SECTORS)

COST_BP = 10.0
COST = COST_BP / 10000.0
RSI_WIN = 2                      # 票面寫死,不掃
BURN = 5                         # 每個 bar 尺寸燒 5 根 bar

BAR_SIZES = ["1D", "3D", "1W", "1M", "3M"]
HOLDS = {"1D": [1, 2, 3, 5, 10], "3D": [1, 2, 3], "1W": [1, 2, 3, 4],
         "1M": [1, 2, 3], "3M": [1, 2]}
N_TOP = [1, 2, 3]                                        # 甲式
ENTRY = [5, 10, 15, 20, 25, 30, 35, 40]                  # 乙式入場門檻
EXIT = [50, 55, 60, 65, 70, 75, 80, 85, 90, 95]          # 乙式出場門檻
RSI_KINDS = ["wilder", "simple"]
# mult      = 票面規定砌法(月錨 pe_lag + 月內 ETF 日價比例推移)
# price     = ETF 價格序列(對照臂)
# mult_raw  = 直接用月底 pe_lag 正本;只在 1M / 3M 有意義(口徑陷阱檢查,非票面要求)
ARMS = ["mult", "price", "mult_raw"]
RAW_BARS = {"1M", "3M"}


def arms_for(size: str) -> list[str]:
    return ["mult", "price"] + (["mult_raw"] if size in RAW_BARS else [])


def pairs_for(size: str) -> list[tuple[str, str]]:
    p = [("mult", "price")]
    if size in RAW_BARS:
        p += [("mult_raw", "price"), ("mult_raw", "mult")]
    return p


# ----------------------------------------------------------------- RSI

def rsi_series(x: np.ndarray, w: int, kind: str) -> np.ndarray:
    """單條序列的 RSI(w)。x 含 NaN(斷線)時重設遞迴,不跨洞。"""
    n = len(x)
    out = np.full(n, np.nan)
    d = np.full(n, np.nan)
    d[1:] = x[1:] - x[:-1]
    # 斷線:任一端 NaN 則該次變動未定義
    up = np.where(np.isnan(d), np.nan, np.maximum(d, 0.0))
    dn = np.where(np.isnan(d), np.nan, np.maximum(-d, 0.0))

    if kind == "simple":
        s = pd.Series(up)
        t = pd.Series(dn)
        au = s.rolling(w).mean().to_numpy()
        ad = t.rolling(w).mean().to_numpy()
    else:  # wilder:斷洞處重設
        au = np.full(n, np.nan)
        ad = np.full(n, np.nan)
        cu = cd = np.nan
        run = 0            # 連續有效變動的根數
        buf_u: list[float] = []
        buf_d: list[float] = []
        for i in range(n):
            if np.isnan(up[i]):
                cu = cd = np.nan
                run = 0
                buf_u.clear()
                buf_d.clear()
                continue
            run += 1
            if run < w:
                buf_u.append(up[i])
                buf_d.append(dn[i])
                continue
            if run == w:
                buf_u.append(up[i])
                buf_d.append(dn[i])
                cu = float(np.mean(buf_u))
                cd = float(np.mean(buf_d))
            else:
                cu = (cu * (w - 1) + up[i]) / w
                cd = (cd * (w - 1) + dn[i]) / w
            au[i] = cu
            ad[i] = cd

    with np.errstate(divide="ignore", invalid="ignore"):
        rs = np.where(ad > 0, au / ad, np.nan)
        out = 100.0 - 100.0 / (1.0 + rs)
    both0 = (au == 0) & (ad == 0)
    out = np.where((ad == 0) & (au > 0), 100.0, out)
    out = np.where((au == 0) & (ad > 0), 0.0, out)
    out = np.where(both0, 50.0, out)
    out = np.where(np.isnan(au) | np.isnan(ad), np.nan, out)
    return out


def rsi_panel(vals: np.ndarray, kind: str) -> np.ndarray:
    """(nb, NS) 序列面板 → (nb, NS) RSI2。"""
    out = np.full(vals.shape, np.nan)
    for j in range(vals.shape[1]):
        out[:, j] = rsi_series(vals[:, j], RSI_WIN, kind)
    return out


# ----------------------------------------------------------------- 引擎

def engine(targets: np.ndarray, rebal: np.ndarray, rets: np.ndarray):
    """向量化組合引擎。

    targets (nb, NS, K) 目標權重(每格已歸一,和為 1 或 0)
    rebal   (nb, K)     該 bar 是否調倉
    rets    (nb, NS)    該 bar 的板塊回報(成交開市價對開市價)
    回傳    net (nb,K) 淨回報、turn (nb,K) 換手、held (nb,NS,K) 持倉旗
    """
    nb, ns, K = targets.shape
    w = np.zeros((ns, K))
    net = np.empty((nb, K))
    turn = np.empty((nb, K))
    held = np.zeros((nb, ns, K), dtype=bool)
    for i in range(nb):
        do = rebal[i]
        neww = np.where(do[None, :], targets[i], w)
        t = 0.5 * np.abs(neww - w).sum(axis=0)
        gross = (neww * rets[i][:, None]).sum(axis=0)
        net[i] = gross - t * COST
        turn[i] = t
        held[i] = neww > 1e-12
        denom = 1.0 + gross
        denom = np.where(np.abs(denom) < 1e-9, 1.0, denom)
        w = neww * (1.0 + rets[i][:, None]) / denom
    return net, turn, held


def stats(net: np.ndarray, years: float) -> dict[str, np.ndarray]:
    eq = np.cumprod(1.0 + net, axis=0)
    cagr = eq[-1] ** (1.0 / years) - 1.0
    peak = np.maximum.accumulate(eq, axis=0)
    dd = (eq / peak - 1.0).min(axis=0)
    return {"cagr": cagr * 100.0, "maxdd": dd * 100.0, "final": eq[-1]}


def tstat(d: np.ndarray) -> np.ndarray:
    sd = d.std(axis=0, ddof=1)
    sd = np.where(sd <= 0, np.nan, sd)
    return d.mean(axis=0) / (sd / np.sqrt(d.shape[0]))


# ----------------------------------------------------------------- 主程序

def main() -> None:
    t0 = time.time()
    h0 = hashlib.sha256(PROD_DB.read_bytes()).hexdigest()
    print(f"生產庫起始雜湊 {h0[:16]}")

    px = pd.read_parquet(PRICES)
    px["date"] = pd.to_datetime(px["date"])
    close = px.pivot(index="date", columns="ticker", values="close")[COLS]
    open_ = px.pivot(index="date", columns="ticker", values="open")[COLS]
    ok = close.notna().all(axis=1) & open_.notna().all(axis=1)
    close, open_ = close[ok], open_[ok]
    dates = close.index
    m = len(dates)
    print(f"日線面板 {m} 個交易日 {dates[0].date()} .. {dates[-1].date()}")

    close_a = close.to_numpy()
    open_a = open_.to_numpy()
    sec_i = np.array([COLS.index(s) for s in SECTORS])
    spy_i = COLS.index(SPY)

    # ---- 月度倍數 → 日頻倍數(月錨 + 月內價格比例推移)----
    mu = pd.read_csv(MULT_CSV)
    mu["month_end"] = pd.to_datetime(mu["month_end"])
    mu["ym"] = mu["month_end"].dt.strftime("%Y-%m")
    wide = mu.pivot(index="ym", columns="series", values="pe_lag")[SECTORS]
    wide = wide.replace(0.0, np.nan)          # 0.0 = 未定義,當 null

    ym_all = pd.Index([f"{d.year:04d}-{d.month:02d}" for d in dates])
    me_pos = pd.Series(np.arange(m), index=ym_all).groupby(level=0).last()
    me_pos = me_pos.sort_index()

    # 每個交易日的錨:嚴格早於該日的最後一個月底交易日
    anchor_pos = np.full(m, -1, dtype=int)
    mp = me_pos.to_numpy()
    myms = me_pos.index.to_numpy()
    k = -1
    for i in range(m):
        while k + 1 < len(mp) and mp[k + 1] < i:
            k += 1
        anchor_pos[i] = mp[k] if k >= 0 else -1
    anchor_ym = np.where(anchor_pos >= 0, ym_all.to_numpy()[np.maximum(anchor_pos, 0)], None)

    pe_anchor = np.full((m, NS), np.nan)
    wmap = {y: wide.loc[y].to_numpy() for y in wide.index}
    for i in range(m):
        y = anchor_ym[i]
        if y is not None and y in wmap:
            pe_anchor[i] = wmap[y]
    base_px = np.where(anchor_pos[:, None] >= 0,
                       close_a[np.maximum(anchor_pos, 0)][:, sec_i], np.nan)
    daily_pe = pe_anchor * close_a[:, sec_i] / base_px
    cov = np.isfinite(daily_pe).mean()
    print(f"日頻倍數面板有效格比例 {cov:.4f}")

    price_panel = close_a[:, sec_i]

    # 當月 pe_lag 正本(只在月底交易日有意義,供 mult_raw 用)
    cur_pe = np.full((m, NS), np.nan)
    yarr = ym_all.to_numpy()
    for i in range(m):
        y = yarr[i]
        if y in wmap:
            cur_pe[i] = wmap[y]

    # ---- bar 格 ----
    def bar_positions(size: str) -> np.ndarray:
        if size == "1D":
            return np.arange(m)
        if size == "3D":
            return np.arange(0, m, 3)
        s = pd.Series(np.arange(m), index=dates)
        if size == "1W":
            g = s.groupby([dates.isocalendar().year, dates.isocalendar().week])
        elif size == "1M":
            g = s.groupby([dates.year, dates.month])
        else:
            g = s.groupby([dates.year, dates.quarter])
        return np.sort(g.last().to_numpy())

    grids = {}
    for size in BAR_SIZES:
        bp = bar_positions(size)
        bp = bp[bp + 1 < m]                     # 需要有下一個交易日開市成交
        grids[size] = bp

    # ---- 統一評分起點(跨 bar 尺寸可比)----
    starts = []
    prep = {}
    for size in BAR_SIZES:
        bp = grids[size]
        pv = {"mult": daily_pe[bp], "price": price_panel[bp]}
        if size in RAW_BARS:
            pv["mult_raw"] = cur_pe[bp]
        rs = {}
        for arm in arms_for(size):
            for kind in RSI_KINDS:
                rs[(arm, kind)] = rsi_panel(pv[arm], kind)
        prep[size] = (bp, pv, rs)
        valid = np.zeros(len(bp), dtype=bool)
        for key, r in rs.items():
            valid |= np.isfinite(r).any(axis=1)
        idx = np.flatnonzero(valid)
        first = idx[0] + BURN if len(idx) else 0
        first = min(first, len(bp) - 1)
        starts.append(dates[bp[first]])
    START = max(starts)
    print(f"統一評分起點 {START.date()}(各 bar 尺寸暖身後最遲者)")

    rows, contrast_rows, corr_rows, vbt_rows, vbt_jobs = [], [], [], [], []

    for size in BAR_SIZES:
        bp, pv, rs = prep[size]
        keep = dates[bp] >= START
        bp = bp[keep]
        rs = {k2: v[keep] for k2, v in rs.items()}
        arms = arms_for(size)
        pvk = {a: pv[a][keep] for a in arms}
        ep = bp + 1
        nb = len(bp) - 1                       # 最後一根 bar 冇下一期回報
        rets = open_a[ep[1:]] / open_a[ep[:-1]] - 1.0
        sec_rets = rets[:, sec_i]
        spy_rets = rets[:, spy_i]
        years = (dates[ep[-1]] - dates[ep[0]]).days / 365.25
        print(f"[{size}] {nb} 期 {dates[ep[0]].date()} .. {dates[ep[-1]].date()} ({years:.2f} 年)")

        # 基線
        spy_tgt = np.zeros((nb, NS, 1))
        spy_reb = np.zeros((nb, 1), dtype=bool)
        # SPY 用獨立算式(唔喺板塊面板內)
        spy_net = spy_rets.copy()
        spy_net[0] -= COST
        ew_tgt = np.full((nb, NS, 1), 1.0 / NS)
        ew_reb = np.ones((nb, 1), dtype=bool)
        ew_net, ew_turn, _ = engine(ew_tgt, ew_reb, sec_rets)
        ew_net = ew_net[:, 0]
        base = {"spy": spy_net, "ew9": ew_net}
        base_stat = {k2: stats(v[:, None], years) for k2, v in base.items()}
        for k2 in base:
            rows.append(dict(arm="-", bar=size, rsi_kind="-", style="基線",
                             params=k2, n_periods=nb,
                             start=str(dates[ep[0]].date()), end=str(dates[ep[-1]].date()),
                             years=round(years, 2),
                             cagr_pct=round(float(base_stat[k2]["cagr"][0]), 4),
                             maxdd_pct=round(float(base_stat[k2]["maxdd"][0]), 3),
                             exc_spy=np.nan, t_spy=np.nan, exc_ew9=np.nan, t_ew9=np.nan,
                             ann_turnover=np.nan, pct_in_mkt=np.nan, n_rebal=np.nan))

        # 兩臂 RSI 相關
        for kind in RSI_KINDS:
            for a1, a2 in pairs_for(size):
                a, b = rs[(a1, kind)], rs[(a2, kind)]
                for j, s in enumerate(SECTORS):
                    mask = np.isfinite(a[:nb, j]) & np.isfinite(b[:nb, j])
                    pear = spear = mad = np.nan
                    if mask.sum() > 10:
                        x, y = a[:nb, j][mask], b[:nb, j][mask]
                        pear = round(float(np.corrcoef(x, y)[0, 1]), 4)
                        spear = round(float(pd.Series(x).corr(pd.Series(y),
                                                             method="spearman")), 4)
                        mad = round(float(np.abs(x - y).mean()), 3)
                    corr_rows.append(dict(bar=size, rsi_kind=kind,
                                          pair=f"{a1}|{a2}", sector=s,
                                          n=int(mask.sum()), pearson=pear,
                                          spearman=spear, mean_abs_diff=mad))

        for kind in RSI_KINDS:
            R = {a: rs[(a, kind)][:nb] for a in arms}
            fin = {a: np.isfinite(R[a]) for a in arms}

            for H in HOLDS[size]:
                # ---------- 甲式:橫截面買 RSI2 最低 N 隻 ----------
                res_a: dict[str, dict] = {}
                for arm in arms:
                    r_ = R[arm]
                    f_ = fin[arm]
                    K = len(N_TOP)
                    tgt = np.zeros((nb, NS, K))
                    reb = np.zeros((nb, K), dtype=bool)
                    order = np.where(f_, r_, np.inf).argsort(axis=1)
                    nval = f_.sum(axis=1)
                    for i in range(nb):
                        if i % H != 0:
                            continue
                        for ki, N in enumerate(N_TOP):
                            if nval[i] < N:
                                continue          # 有效板塊不足 → 沿用上期,不新開倉
                            pick = order[i, :N]
                            tgt[i, pick, ki] = 1.0 / N
                            reb[i, ki] = True
                    net, turn, held = engine(tgt, reb, sec_rets)
                    res_a[arm] = dict(net=net, turn=turn, held=held, tgt=tgt, reb=reb)
                    if kind == "wilder":      # D-095 指定工具:vectorBT 對照
                        vbt_rows.extend(vbt_check(size, arm, H, tgt, reb, ep, dates,
                                                  open_a, sec_i, years, net))

                for ki, N in enumerate(N_TOP):
                    rec = {}
                    for arm in arms:
                        rec[arm] = emit(rows, arm, size, kind, "甲", f"N={N},H={H}",
                                        res_a[arm], ki, nb, years, base, base_stat,
                                        dates, ep, extra=dict(N=N, H=H))
                    for a1, a2 in pairs_for(size):
                        contrast_rows.append(contrast(size, kind, "甲", f"N={N},H={H}",
                                                      res_a, ki, rec, dict(N=N, H=H),
                                                      a1, a2))
                    vbt_jobs.append((size, kind, "甲", f"N={N},H={H}", H, N))

                # ---------- 乙式:門檻進出 ----------
                nE, nX = len(ENTRY), len(EXIT)
                K = nE * nX
                Ea = np.array(ENTRY, float)[:, None].repeat(nX, 1).ravel()   # (K,)
                Xa = np.array(EXIT, float)[None, :].repeat(nE, 0).ravel()
                res_b: dict[str, dict] = {}
                for arm in arms:
                    r_ = R[arm]
                    f_ = fin[arm]
                    tgt = np.zeros((nb, NS, K), dtype=np.float32)
                    reb = np.zeros((nb, K), dtype=bool)
                    pos = np.zeros((NS, K), dtype=bool)
                    hold_n = np.zeros((NS, K), dtype=np.int32)
                    prev_cnt = np.zeros(K, dtype=np.int32)
                    for i in range(nb):
                        rv = r_[i][:, None]
                        fv = f_[i][:, None]
                        enter = (~pos) & fv & (rv < Ea[None, :])
                        leave = pos & fv & (hold_n >= H) & (rv > Xa[None, :])
                        newpos = (pos & ~leave) | enter
                        hold_n = np.where(enter, 0, hold_n + 1)
                        cnt = newpos.sum(axis=0)
                        changed = (newpos != pos).any(axis=0)
                        pos = newpos
                        prev_cnt = cnt
                        with np.errstate(invalid="ignore", divide="ignore"):
                            w = np.where(cnt[None, :] > 0,
                                         newpos / np.maximum(cnt[None, :], 1), 0.0)
                        tgt[i] = w
                        reb[i] = changed
                    net, turn, held = engine(tgt.astype(float), reb, sec_rets)
                    res_b[arm] = dict(net=net, turn=turn, held=held, tgt=tgt, reb=reb)

                for ki in range(K):
                    lab = f"E={int(Ea[ki])},X={int(Xa[ki])},H={H}"
                    rec = {}
                    for arm in arms:
                        rec[arm] = emit(rows, arm, size, kind, "乙", lab,
                                        res_b[arm], ki, nb, years, base, base_stat,
                                        dates, ep,
                                        extra=dict(E=int(Ea[ki]), X=int(Xa[ki]), H=H))
                    for a1, a2 in pairs_for(size):
                        contrast_rows.append(
                            contrast(size, kind, "乙", lab, res_b, ki, rec,
                                     dict(E=int(Ea[ki]), X=int(Xa[ki]), H=H), a1, a2))
                del res_a, res_b

    pan = pd.DataFrame(rows)
    pan.to_csv(HERE / "panorama.csv", index=False, encoding="utf-8-sig")
    con = pd.DataFrame(contrast_rows)
    con.to_csv(HERE / "contrast.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(corr_rows).to_csv(HERE / "rsi_corr.csv", index=False, encoding="utf-8-sig")
    vc = pd.DataFrame(vbt_rows)
    vc.to_csv(HERE / "vbt_check.csv", index=False, encoding="utf-8-sig")
    print(f"panorama {pan.shape} contrast {con.shape} vbt對照 {vc.shape} "
          f"最大年化差 {vc['abs_diff'].max():.4f} 百分點")

    h1 = hashlib.sha256(PROD_DB.read_bytes()).hexdigest()
    meta = dict(
        ticket="KARST-135", generated=time.strftime("%Y-%m-%d %H:%M:%S"),
        prices=str(PRICES.relative_to(REPO)), multiples=str(MULT_CSV.relative_to(REPO)),
        sectors=SECTORS, cost_bp=COST_BP, rsi_window=RSI_WIN, burn_bars=BURN,
        bar_sizes=BAR_SIZES, holds=HOLDS, n_top=N_TOP, entry=ENTRY, exit=EXIT,
        rsi_kinds=RSI_KINDS, common_start=str(START.date()),
        daily_multiple_coverage=round(float(cov), 4),
        prod_db_sha256_head16_before=h0[:16], prod_db_sha256_head16_after=h1[:16],
        prod_db_unchanged=(h0 == h1),
        arms="mult(票面砌法) / price(對照臂) / mult_raw(月底 pe_lag 正本,只 1M+3M)",
        panorama_rows=int(len(pan)), contrast_rows=int(len(con)),
        vbt_max_abs_cagr_diff_pp=round(float(vc["abs_diff"].max()), 5),
        runtime_sec=round(time.time() - t0, 1),
    )
    (HERE / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                    encoding="utf-8")
    print(f"生產庫收工雜湊 {h1[:16]} 不變={h0 == h1}  用時 {meta['runtime_sec']}s")


def emit(rows, arm, size, kind, style, params, res, ki, nb, years, base, base_stat,
         dates, ep, extra):
    net = res["net"][:, ki]
    st = stats(net[:, None], years)
    d_spy = net - base["spy"]
    d_ew = net - base["ew9"]
    turn = res["turn"][:, ki]
    held = res["held"][:, :, ki]
    # 分段穩定性:前半 / 後半(文獻講 2011 後衰減,要見得到)
    half = nb // 2
    yr_h = years / 2.0
    exc_h1 = (stats(net[:half, None], yr_h)["cagr"][0]
              - stats(base["spy"][:half, None], yr_h)["cagr"][0])
    exc_h2 = (stats(net[half:, None], yr_h)["cagr"][0]
              - stats(base["spy"][half:, None], yr_h)["cagr"][0])
    rec = dict(arm=arm, bar=size, rsi_kind=kind, style=style, params=params,
               n_periods=nb, start=str(dates[ep[0]].date()), end=str(dates[ep[-1]].date()),
               years=round(years, 2),
               cagr_pct=round(float(st["cagr"][0]), 4),
               maxdd_pct=round(float(st["maxdd"][0]), 3),
               exc_spy=round(float(st["cagr"][0] - base_stat["spy"]["cagr"][0]), 4),
               t_spy=round(float(tstat(d_spy[:, None])[0]), 3),
               exc_ew9=round(float(st["cagr"][0] - base_stat["ew9"]["cagr"][0]), 4),
               t_ew9=round(float(tstat(d_ew[:, None])[0]), 3),
               exc_spy_h1=round(float(exc_h1), 4), exc_spy_h2=round(float(exc_h2), 4),
               ann_turnover=round(float(turn.sum() / years), 2),
               pct_in_mkt=round(float(held.any(axis=1).mean()) * 100, 2),
               n_rebal=int((turn > 1e-9).sum()), **extra)
    rows.append(rec)
    return rec


def vbt_check(size, arm, H, tgt, reb, ep, dates, open_a, sec_i, years, hand_net):
    """用 vectorBT 重跑同一批甲式權重,對照手寫引擎(D-095 指定工具)。"""
    nbp, ns, K = tgt.shape
    idx = pd.DatetimeIndex(dates[ep[:nbp + 1]])
    px = open_a[ep[:nbp + 1]][:, sec_i]
    labels = [f"c{k}" for k in range(K)]
    mi = pd.MultiIndex.from_tuples([(l, s) for l in labels for s in SECTORS],
                                   names=["combo", "ticker"])
    big = np.full((nbp + 1, K * ns), np.nan)
    for k in range(K):
        big[:nbp, k * ns:(k + 1) * ns] = np.where(reb[:, k][:, None], tgt[:, :, k], np.nan)
    size_df = pd.DataFrame(big, index=idx, columns=mi)
    price_df = pd.DataFrame(np.tile(px, (1, K)), index=idx, columns=mi)
    pf = vbt.Portfolio.from_orders(
        close=price_df, size=size_df, size_type="targetpercent",
        group_by="combo", cash_sharing=True, call_seq="auto",
        fees=COST / 2.0, init_cash=100.0, freq="1D")
    vr = pf.returns()
    out = []
    for k, N in enumerate(N_TOP):
        v = vr[labels[k]].to_numpy()
        v_cagr = (np.prod(1.0 + v[1:]) ** (1.0 / years) - 1.0) * 100
        h_cagr = (np.prod(1.0 + hand_net[:, k]) ** (1.0 / years) - 1.0) * 100
        out.append(dict(bar=size, arm=arm, style="甲", params=f"N={N},H={H}",
                        hand_cagr=round(float(h_cagr), 4),
                        vbt_cagr=round(float(v_cagr), 4),
                        abs_diff=round(abs(float(h_cagr - v_cagr)), 4)))
    return out


def contrast(size, kind, style, params, res, ki, rec, extra, a1="mult", a2="price"):
    hm = res[a1]["held"][:, :, ki]
    hp = res[a2]["held"][:, :, ki]
    agree = float((hm == hp).mean())
    inter = float((hm & hp).sum())
    union = float((hm | hp).sum())
    jac = inter / union if union > 0 else np.nan
    return dict(bar=size, rsi_kind=kind, style=style, params=params,
                pair=f"{a1}|{a2}", arm_a=a1, arm_b=a2,
                agreement=round(agree, 4), jaccard=round(jac, 4) if union > 0 else np.nan,
                a_cagr=rec[a1]["cagr_pct"], b_cagr=rec[a2]["cagr_pct"],
                a_exc_spy=rec[a1]["exc_spy"], b_exc_spy=rec[a2]["exc_spy"],
                diff_exc_spy=round(rec[a1]["exc_spy"] - rec[a2]["exc_spy"], 4),
                a_exc_ew9=rec[a1]["exc_ew9"], b_exc_ew9=rec[a2]["exc_ew9"],
                diff_exc_ew9=round(rec[a1]["exc_ew9"] - rec[a2]["exc_ew9"], 4),
                a_t_spy=rec[a1]["t_spy"], b_t_spy=rec[a2]["t_spy"],
                **extra)


if __name__ == "__main__":
    main()
