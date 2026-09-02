# -*- coding: utf-8 -*-
"""KARST-154 非價格宏觀狀態開關存在性測試 —— 主運算。

判準見同目錄 CRITERIA.md(跑數前已凍結,commit 8a4f064)。本檔只實作,不改判準。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

RNG = np.random.default_rng(20260902)

WIN_START = pd.Timestamp("1990-01-01")
WIN_END = pd.Timestamp("2026-09-01")

COST_BPS = 5.0 / 10000.0
BORROW_SPREAD = 0.0100          # rf + 1.00%,見 CRITERIA §6

BASE = dict(L1=12, L2=52, ab=(3, 18), k=1.0, p=0.0, theta=0.5)

GRID = dict(
    L1=[6, 12, 24],
    L2=[26, 52],
    ab=[(0, 12), (3, 18), (6, 24)],
    k=[0.5, 1.0, 1.5],
    p=[0.0, -5.0],
    theta=[0.4, 0.5, 0.6],
)


# ---------------------------------------------------------------- 載入原料
def load() -> dict:
    def f(sid):
        s = pd.read_csv(OUT / f"fred_{sid}.csv", index_col=0, parse_dates=True)[sid]
        return s.dropna()

    px = pd.read_csv(OUT / "prices.csv", index_col=0, parse_dates=True)

    # 成交軌道甲:SPY 軌 = 1993-01-29 起 SPY,之前用 ^SP500TR 日回報接上
    spy_r = px["SPY"].dropna().pct_change()
    tr_r = px["SP500TR"].dropna().pct_change()
    splice = pd.Timestamp("1993-01-29")
    spy_track = pd.concat([tr_r[tr_r.index < splice], spy_r[spy_r.index >= splice]]).dropna()
    spy_track = spy_track[~spy_track.index.duplicated()].sort_index()

    xlk_track = px["XLK"].dropna().pct_change().dropna()

    rf = f("DTB3") / 100.0
    rf = rf.reindex(spy_track.index.union(xlk_track.index).union(rf.index)).ffill()

    return dict(
        UNRATE=f("UNRATE"),
        ICSA=f("ICSA"),
        T10Y3M=f("T10Y3M"),
        SPREAD=(f("DBAA") - f("DAAA")).dropna(),
        PHIL=f("GACDFSA066MSFRBPHI"),
        RRSFS=f("RRSFS"),
        rf=rf,
        spy=spy_track,
        xlk=xlk_track,
        gspc=px["GSPC"].dropna(),
    )


# ------------------------------------------------------- 月度訊號日與可用性
def signal_dates(track: pd.Series) -> pd.DatetimeIndex:
    """每個日曆月的最後一個交易日,窗內。"""
    idx = track.index
    per = idx.to_period("M")
    last = pd.Series(idx, index=per).groupby(level=0).last()
    last = last[(last.index >= WIN_START.to_period("M")) & (last.index <= WIN_END.to_period("M"))]
    return pd.DatetimeIndex(last.values), last.index


def monthly_map(s: pd.Series) -> pd.Series:
    """月度序列 -> 以 Period('M') 為索引。"""
    out = s.copy()
    out.index = out.index.to_period("M")
    return out[~out.index.duplicated(keep="last")]


def month_end_values(daily: pd.Series) -> pd.Series:
    """日序列 -> 每月最後一個觀測值,以 Period('M') 為索引。"""
    g = daily.groupby(daily.index.to_period("M")).last()
    return g


def month_mean_values(daily: pd.Series) -> pd.Series:
    return daily.groupby(daily.index.to_period("M")).mean()


# ------------------------------------------------------------------ 投票
def build_votes(d: dict, months: pd.PeriodIndex, params: dict) -> pd.DataFrame:
    """回傳 DataFrame:每個訊號月 × 六條變量,值 = 1(風險關)/0(風險開)/NaN(無數據)。

    可用性一律照 CRITERIA §2 的保守公布滯後。
    """
    L1, L2, (a, b), k, p = params["L1"], params["L2"], params["ab"], params["k"], params["p"]

    unrate = monthly_map(d["UNRATE"])
    phil = monthly_map(d["PHIL"])
    rrsfs = monthly_map(d["RRSFS"])
    curve_m = month_mean_values(d["T10Y3M"])
    spread_me = month_end_values(d["SPREAD"])

    icsa = d["ICSA"]

    votes = pd.DataFrame(index=months, columns=["U", "C", "Y", "S", "P", "R"], dtype=float)
    spread_narrow = pd.Series(index=months, dtype=float)

    for m in months:
        # --- U 失業率:可用到 m-1
        prev = m - 1
        win = unrate.loc[:prev].tail(L1)
        if len(win) == L1 and prev in unrate.index:
            votes.at[m, "U"] = 1.0 if unrate[prev] > win.mean() else 0.0

        # --- C 初請失業金:週結束日 <= 該月最後日曆日 - 10 日
        cutoff = m.to_timestamp(how="end").normalize() - pd.Timedelta(days=10)
        av = icsa[icsa.index <= cutoff]
        if len(av) >= L2:
            votes.at[m, "C"] = 1.0 if av.tail(4).mean() > av.tail(L2).mean() else 0.0

        # --- Y 收益率曲線:月均值於 [m-b, m-a] 曾為負
        lo, hi = m - b, m - a
        seg = curve_m[(curve_m.index >= lo) & (curve_m.index <= hi)]
        if len(seg) == (b - a + 1):
            votes.at[m, "Y"] = 1.0 if seg.min() < 0 else 0.0

        # --- S 信貸息差:m 月底值 > 過去 24 個月月底值均值 + k*標準差
        sw = spread_me[spread_me.index <= m].tail(24)
        if len(sw) == 24 and m in spread_me.index:
            cur = spread_me[m]
            votes.at[m, "S"] = 1.0 if cur > sw.mean() + k * sw.std(ddof=1) else 0.0
            ma12 = spread_me[spread_me.index <= m].tail(12).mean()
            spread_narrow[m] = 1.0 if cur < ma12 else 0.0

        # --- P 製造業景氣:可用到 m-1,三個月均值
        pw = phil[phil.index <= prev].tail(3)
        if len(pw) == 3 and prev in phil.index:
            votes.at[m, "P"] = 1.0 if pw.mean() < p else 0.0

        # --- R 實質零售銷售:可用到 m-1,十二個月對數變化
        if prev in rrsfs.index and (prev - 12) in rrsfs.index:
            votes.at[m, "R"] = 1.0 if np.log(rrsfs[prev] / rrsfs[prev - 12]) < 0 else 0.0

    return votes, spread_narrow


def composite_exposure(votes: pd.DataFrame, spread_narrow: pd.Series,
                       theta: float, strong_variant: str = "A") -> pd.Series:
    n = votes.notna().sum(axis=1)
    v = votes.sum(axis=1, skipna=True)
    frac = v / n.replace(0, np.nan)

    risk_off = (frac > theta) & (n >= 3)
    exposure = pd.Series(1.0, index=votes.index)
    exposure[risk_off] = 0.0

    bullish = (n - v)                       # 看好的變量數
    narrow = spread_narrow.reindex(votes.index).fillna(0.0) == 1.0
    if strong_variant == "A":               # 票面字面:>=2 條看好 + 息差收窄
        strong = (~risk_off) & (bullish >= 2) & narrow
    else:                                   # 較嚴:風險關票數 <=1 + 息差收窄
        strong = (~risk_off) & (v <= 1) & narrow
    exposure[strong] = 2.0
    exposure[n < 3] = 1.0
    return exposure


def single_var_exposure(votes: pd.DataFrame, col: str) -> pd.Series:
    e = pd.Series(1.0, index=votes.index)
    e[votes[col] == 1.0] = 0.0
    return e


# ------------------------------------------------------------ 月度注碼 -> 日
_FIRST_TD_CACHE: dict = {}


def _first_trading_days(track_index: pd.DatetimeIndex) -> pd.Series:
    key = (track_index[0], track_index[-1], len(track_index))
    if key not in _FIRST_TD_CACHE:
        per = track_index.to_period("M")
        _FIRST_TD_CACHE[key] = pd.Series(track_index, index=per).groupby(level=0).first()
    return _FIRST_TD_CACHE[key]


def daily_position(exposure_m: pd.Series, sig_dates: pd.DatetimeIndex,
                   months: pd.PeriodIndex, track_index: pd.DatetimeIndex) -> pd.Series:
    """訊號於 T 月最後交易日算出,倉位於 T+1 月首個交易日收市生效。"""
    first_td = _first_trading_days(track_index)

    eff = {}
    for m, e in exposure_m.items():
        nxt = m + 1
        if nxt in first_td.index:
            eff[first_td[nxt]] = e
    s = pd.Series(eff).sort_index()
    pos = s.reindex(track_index).ffill()
    pos = pos.shift(1)                    # 收市生效 -> 下一日的回報才用新注碼
    return pos


def levered_returns(track: pd.Series, rf: pd.Series, pos: pd.Series) -> pd.Series:
    """注碼 0/1/2 的日回報,含融資成本與交易成本。"""
    rfd = rf.reindex(track.index).ffill() / 252.0
    r1 = track
    r0 = rfd
    r2 = 2.0 * track - (rf.reindex(track.index).ffill() + BORROW_SPREAD) / 252.0

    p = pos.reindex(track.index)
    out = pd.Series(np.nan, index=track.index)
    out[p == 0.0] = r0[p == 0.0]
    out[p == 1.0] = r1[p == 1.0]
    out[p == 2.0] = r2[p == 2.0]

    chg = p.diff().abs().fillna(0.0)
    out = out - chg * COST_BPS
    return out.dropna()


def const_lev(track: pd.Series, rf: pd.Series, mult: float) -> pd.Series:
    if mult == 1.0:
        return track
    rfa = rf.reindex(track.index).ffill()
    return mult * track - (mult - 1.0) * (rfa + BORROW_SPREAD) / 252.0


# ------------------------------------------------------------------- 指標
def metrics(r: pd.Series, rf: pd.Series, pos: pd.Series | None = None) -> dict:
    r = r.dropna()
    n = len(r)
    if n == 0:
        return {}
    eq = (1 + r).cumprod()
    yrs = n / 252.0
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    vol = r.std(ddof=1) * np.sqrt(252)
    ex = r - rf.reindex(r.index).ffill() / 252.0
    sharpe = ex.mean() / ex.std(ddof=1) * np.sqrt(252) if ex.std(ddof=1) > 0 else np.nan
    dd = eq / eq.cummax() - 1
    out = dict(cagr=float(cagr), vol=float(vol), sharpe=float(sharpe),
               maxdd=float(dd.min()), n_days=int(n), years=float(yrs))
    if pos is not None:
        p = pos.reindex(r.index)
        out["time_in_market"] = float((p > 0).mean())
        out["turnover_yr"] = float(p.diff().abs().sum() / yrs)
        out["avg_exposure"] = float(p.mean())
    return out


# --------------------------------------------------------------- 熊市事件
def bear_events(track: pd.Series) -> list:
    eq = (1 + track).cumprod()
    peak = eq.cummax()
    dd = eq / peak - 1

    events = []
    i = 0
    idx = eq.index
    n = len(eq)
    while i < n:
        if dd.iloc[i] <= -0.20:
            # 回溯至該段的高位
            j = i
            while j > 0 and dd.iloc[j - 1] < 0:
                j -= 1
            peak_date = idx[j - 1] if j > 0 else idx[0]
            peak_val = peak.iloc[i]
            # 向前找回到高位的日子
            e = i
            while e < n and eq.iloc[e] < peak_val:
                e += 1
            seg = dd.iloc[j:e] if e > j else dd.iloc[j:]
            seg_idx = idx[j:e] if e > j else idx[j:]
            trough_pos = int(np.argmin(seg.values))
            d20 = next((seg_idx[t] for t in range(len(seg)) if seg.values[t] <= -0.20), None)
            d35 = next((seg_idx[t] for t in range(len(seg)) if seg.values[t] <= -0.35), None)
            events.append(dict(
                peak=peak_date, start20=d20, cross35=d35,
                trough=seg_idx[trough_pos], depth=float(seg.values[trough_pos]),
                recovered=idx[e] if e < n else None,
                end=idx[e - 1] if e < n else idx[-1],
            ))
            i = e
        else:
            i += 1
    return events


def death_line(events: list, pos: pd.Series, track: pd.Series) -> dict:
    rows = []
    passed = True
    for ev in events:
        row = dict(
            peak=str(ev["peak"].date()), start20=str(ev["start20"].date()),
            trough=str(ev["trough"].date()), depth=round(ev["depth"] * 100, 1),
            cross35=str(ev["cross35"].date()) if ev["cross35"] is not None else None,
        )
        p = pos.reindex(track.index).ffill()
        if ev["cross35"] is not None:
            before = p[(p.index >= ev["peak"]) & (p.index < ev["cross35"])]
            at_zero = before.iloc[-1] == 0.0 if len(before) else False
            row["zero_before_35"] = bool(at_zero)
            if at_zero:
                z = before[before == 0.0]
                run_start = z.index[-1]
                for t in range(len(before) - 1, -1, -1):
                    if before.iloc[t] != 0.0:
                        break
                    run_start = before.index[t]
                row["zero_since"] = str(run_start.date())
                row["months_early"] = round((ev["cross35"] - run_start).days / 30.44, 1)
            else:
                row["zero_since"] = None
                row["months_early"] = None
                passed = False
        else:
            row["zero_before_35"] = None
            row["zero_since"] = None
            row["months_early"] = None
        # 跌穿 -20% 之後仍在市內的日數
        after20 = p[(p.index >= ev["start20"]) & (p.index <= ev["trough"])]
        row["days_20_to_trough"] = int(len(after20))
        row["days_in_market_after20"] = int((after20 > 0).sum())
        seg_r = track[(track.index > ev["start20"]) & (track.index <= ev["trough"])]
        row["drop_20_to_trough_pct"] = round(float(((1 + seg_r).prod() - 1) * 100), 1)
        rows.append(row)
    return dict(passed=bool(passed), events=rows)


def false_alarms(exposure_m: pd.Series, events: list, track: pd.Series,
                 months: pd.PeriodIndex) -> dict:
    """非熊市期間轉 0× 的段落:次數、月數、期間錯過的市場升幅。"""
    bear_months = set()
    for ev in events:
        s, e = ev["peak"].to_period("M"), ev["trough"].to_period("M")
        m = s
        while m <= e:
            bear_months.add(m)
            m += 1

    mret = (1 + track).groupby(track.index.to_period("M")).prod() - 1
    runs = []
    cur = None
    for m in exposure_m.index:
        if exposure_m[m] == 0.0:
            if cur is None:
                cur = [m, m]
            else:
                cur[1] = m
        else:
            if cur is not None:
                runs.append(tuple(cur))
                cur = None
    if cur is not None:
        runs.append(tuple(cur))

    fa, real = [], []
    for s, e in runs:
        n_months = int((e.ordinal - s.ordinal) + 1)
        run_months = [s + i for i in range(n_months)]
        # 倉位於 s+1 月生效,至 e+1 月尾
        span = [m for m in mret.index if (s + 1) <= m <= (e + 1)]
        mkt = float(np.prod([1 + mret[m] for m in span]) - 1) if span else 0.0
        overlaps_bear = any(m in bear_months for m in run_months)
        rec = dict(start=str(s), end=str(e), months=n_months,
                   market_move_pct=round(mkt * 100, 1))
        (real if overlaps_bear else fa).append(rec)
    return dict(n_runs=len(runs), n_false=len(fa), n_real=len(real),
                false=fa, real=real,
                missed_upside_pct=round(float(sum(x["market_move_pct"] for x in fa)), 1))


# ----------------------------------------------------------------- 運氣帶
def luck_band(exposure_m: pd.Series, sig_months: pd.PeriodIndex, sig_dates,
              track: pd.Series, rf: pd.Series, n_draws: int = 1000) -> dict:
    mask = (exposure_m == 0.0).values
    n_zero = int(mask.sum())
    n_m = len(mask)

    runs = []
    c = 0
    for x in mask:
        if x:
            c += 1
        elif c:
            runs.append(c)
            c = 0
    if c:
        runs.append(c)

    def run_one(m_arr):
        e = pd.Series(np.where(m_arr, 0.0, 1.0), index=sig_months)
        pos = daily_position(e, sig_dates, sig_months, track.index)
        r = levered_returns(track, rf, pos)
        return metrics(r, rf, pos)

    iid, blk = [], []
    for _ in range(n_draws):
        a = np.zeros(n_m, dtype=bool)
        a[RNG.choice(n_m, n_zero, replace=False)] = True
        iid.append(run_one(a))

        b = np.zeros(n_m, dtype=bool)
        ok = False
        for _try in range(200):
            b[:] = False
            good = True
            for L in RNG.permutation(runs):
                cands = [s for s in range(n_m - L + 1) if not b[max(0, s - 1):s + L + 1].any()]
                if not cands:
                    good = False
                    break
                s = int(RNG.choice(cands))
                b[s:s + L] = True
            if good:
                ok = True
                break
        if not ok:
            b[:] = False
            b[RNG.choice(n_m, n_zero, replace=False)] = True
        blk.append(run_one(b))

    def summarise(lst):
        return {kk: {"p5": float(np.percentile([x[kk] for x in lst], 5)),
                     "p50": float(np.percentile([x[kk] for x in lst], 50)),
                     "p95": float(np.percentile([x[kk] for x in lst], 95)),
                     "raw": [x[kk] for x in lst]}
                for kk in ("cagr", "sharpe", "maxdd")}

    return dict(n_zero_months=n_zero, n_months=n_m, runs=runs,
                iid=summarise(iid), block=summarise(blk))


def percentile_of(value: float, sample: list) -> float:
    s = np.asarray(sample)
    return float((s < value).mean() * 100)


# ------------------------------------------------------------------- 主流程
def main() -> None:
    d = load()
    track = d["spy"]
    track = track[(track.index >= WIN_START) & (track.index <= WIN_END)]
    rf = d["rf"]

    sig_dates, months = signal_dates(track)
    print(f"訊號月數 {len(months)}:{months[0]} -> {months[-1]}")

    votes_base, narrow_base = build_votes(d, months, BASE)
    votes_base.to_csv(OUT / "votes_base.csv")
    print("可用變量數分佈:")
    print(votes_base.notna().sum(axis=1).value_counts().sort_index().to_string())

    events = bear_events(track)
    print(f"\n熊市事件({len(events)} 次 >20%):")
    for ev in events:
        print(f"  高位 {ev['peak'].date()}  跌穿20% {ev['start20'].date()}  "
              f"低位 {ev['trough'].date()} {ev['depth']*100:.1f}%  "
              f"跌穿35% {ev['cross35'].date() if ev['cross35'] is not None else '無'}")

    results = {}

    # ---- 基準
    bench = {}
    pos_bh = pd.Series(1.0, index=track.index)
    bench["SPY 買入持有"] = metrics(track, rf, pos_bh)
    r2 = const_lev(track, rf, 2.0)
    bench["2x SPY 恆常槓桿"] = metrics(r2, rf, pd.Series(2.0, index=track.index))
    xlk = d["xlk"]
    xlk = xlk[(xlk.index >= WIN_START) & (xlk.index <= WIN_END)]
    bench["XLK 買入持有"] = metrics(xlk, rf, pd.Series(1.0, index=xlk.index))
    bench["全現金"] = metrics(rf.reindex(track.index).ffill() / 252.0, rf, pd.Series(0.0, index=track.index))
    results["benchmarks"] = bench

    # ---- 主判:合成規則(變體甲/乙)
    rules = {}
    for variant in ("A", "B"):
        e = composite_exposure(votes_base, narrow_base, BASE["theta"], variant)
        pos = daily_position(e, sig_dates, months, track.index)
        r = levered_returns(track, rf, pos)
        dl = death_line(events, pos, track)
        fa = false_alarms(e, events, track, months)
        rules[f"合成規則_變體{variant}"] = dict(
            metrics=metrics(r, rf, pos), death_line=dl, false_alarms=fa,
            exposure_counts={str(k): int(v) for k, v in e.value_counts().items()},
        )
        e.to_csv(OUT / f"exposure_composite_{variant}.csv")

    # ---- 單變量規則(只做 0/1,不加 2x)
    for col in ["U", "C", "Y", "S", "P", "R"]:
        e = single_var_exposure(votes_base, col)
        pos = daily_position(e, sig_dates, months, track.index)
        r = levered_returns(track, rf, pos)
        rules[f"單變量_{col}"] = dict(
            metrics=metrics(r, rf, pos),
            death_line=death_line(events, pos, track),
            false_alarms=false_alarms(e, events, track, months),
        )

    # ---- 合成規則但只 0/1(拆走槓桿的貢獻)
    e01 = pd.Series(np.where(composite_exposure(votes_base, narrow_base, BASE["theta"], "A") == 0.0, 0.0, 1.0),
                    index=months)
    pos01 = daily_position(e01, sig_dates, months, track.index)
    r01 = levered_returns(track, rf, pos01)
    rules["合成規則_只0或1"] = dict(
        metrics=metrics(r01, rf, pos01),
        death_line=death_line(events, pos01, track),
        false_alarms=false_alarms(e01, events, track, months),
    )
    results["rules"] = rules

    # ---- XLK 臂(同一組宏觀訊號,換標的)
    xlk_sig_dates, xlk_months = signal_dates(xlk)
    v_x, n_x = build_votes(d, xlk_months, BASE)
    e_x = composite_exposure(v_x, n_x, BASE["theta"], "A")
    pos_x = daily_position(e_x, xlk_sig_dates, xlk_months, xlk.index)
    r_x = levered_returns(xlk, rf, pos_x)
    results["xlk_arm"] = dict(
        rule=metrics(r_x, rf, pos_x),
        buyhold=metrics(xlk, rf, pd.Series(1.0, index=xlk.index)),
        lev2=metrics(const_lev(xlk, rf, 2.0), rf, pd.Series(2.0, index=xlk.index)),
    )

    # ---- 小格掃描 324 格
    print("\n小格掃描 324 格 …")
    grid_rows = []
    for L1 in GRID["L1"]:
        for L2 in GRID["L2"]:
            for ab in GRID["ab"]:
                pr = dict(L1=L1, L2=L2, ab=ab, k=None, p=None)
                for k in GRID["k"]:
                    for p in GRID["p"]:
                        params = dict(L1=L1, L2=L2, ab=ab, k=k, p=p)
                        vv, nn = build_votes(d, months, params)
                        for theta in GRID["theta"]:
                            e = composite_exposure(vv, nn, theta, "A")
                            pos = daily_position(e, sig_dates, months, track.index)
                            r = levered_returns(track, rf, pos)
                            mm = metrics(r, rf, pos)
                            dl = death_line(events, pos, track)
                            grid_rows.append(dict(
                                L1=L1, L2=L2, a=ab[0], b=ab[1], k=k, p=p, theta=theta,
                                cagr=mm["cagr"], sharpe=mm["sharpe"], maxdd=mm["maxdd"],
                                time_in_market=mm["time_in_market"], turnover_yr=mm["turnover_yr"],
                                death_pass=dl["passed"],
                            ))
    grid = pd.DataFrame(grid_rows)
    grid.to_csv(OUT / "grid_324.csv", index=False)
    results["grid"] = dict(
        n=len(grid),
        death_pass_rate=float(grid["death_pass"].mean()),
        cagr=dict(min=float(grid.cagr.min()), q25=float(grid.cagr.quantile(.25)),
                  med=float(grid.cagr.median()), q75=float(grid.cagr.quantile(.75)),
                  max=float(grid.cagr.max())),
        sharpe=dict(min=float(grid.sharpe.min()), q25=float(grid.sharpe.quantile(.25)),
                    med=float(grid.sharpe.median()), q75=float(grid.sharpe.quantile(.75)),
                    max=float(grid.sharpe.max())),
        maxdd=dict(min=float(grid.maxdd.min()), q25=float(grid.maxdd.quantile(.25)),
                   med=float(grid.maxdd.median()), q75=float(grid.maxdd.quantile(.75)),
                   max=float(grid.maxdd.max())),
        n_beat_bh_cagr=int((grid.cagr > bench["SPY 買入持有"]["cagr"]).sum()),
    )

    # ---- 運氣帶(對基準格合成規則,只 0/1)
    print("運氣帶 1,000 × 2 …")
    lb = luck_band(e01, months, sig_dates, track, rf, n_draws=1000)
    m01 = rules["合成規則_只0或1"]["metrics"]
    results["luck_band"] = dict(
        n_zero_months=lb["n_zero_months"], n_months=lb["n_months"], runs=lb["runs"],
        iid={kk: {p: lb["iid"][kk][p] for p in ("p5", "p50", "p95")} for kk in ("cagr", "sharpe", "maxdd")},
        block={kk: {p: lb["block"][kk][p] for p in ("p5", "p50", "p95")} for kk in ("cagr", "sharpe", "maxdd")},
        rule_percentile_iid={kk: percentile_of(m01[kk], lb["iid"][kk]["raw"]) for kk in ("cagr", "sharpe", "maxdd")},
        rule_percentile_block={kk: percentile_of(m01[kk], lb["block"][kk]["raw"]) for kk in ("cagr", "sharpe", "maxdd")},
    )

    results["meta"] = dict(
        window=[str(track.index[0].date()), str(track.index[-1].date())],
        n_signal_months=len(months), base_params={k: str(v) for k, v in BASE.items()},
        cost_bps=5, borrow_spread=BORROW_SPREAD,
    )

    (OUT / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str),
                                      encoding="utf-8")
    print("\n寫入", OUT / "results.json")


if __name__ == "__main__":
    main()
