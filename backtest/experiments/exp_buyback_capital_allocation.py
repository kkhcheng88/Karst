"""Buyback yield / net share issuance — does management's capital-allocation behaviour predict
forward cross-sectional returns in Karst's OWN universe/data? (Mauboussin *Expectations Investing*
+ Chancellor *Capital Returns*: buybacks = mgmt thinks stock cheap; issuance/stock-M&A = mgmt thinks
it dear. Academic backbone already logged: Cooper-Gulen-Schill 2008 asset-growth, Lyandres-Sun-Zhang
2008 new-issues puzzle, F-F 2015 CMA — see docs/2026-07-09_magnifier_literature.md §2.)

This is a REPRODUCTION test of an already-well-supported factor in-sample, NOT a discovery run. Goal:
decide whether buyback_yield / net_issuance is worth adding to the Phase-3 admission-lint / kill_condition
vocabulary (docs/2026-07-08_phase3_ws3_lifecycle.md §2).

Question:  Pooled + per-sector, does trailing-4Q buyback_yield (high = good) and net_issuance
           (high = dilution = bad) have forward SPY-excess-return predictive power at 63/126/252d?

Method (mirror / increment / horizon — memory validation-mirror-and-increment):
  - mirror  = cross-sectional rank IC + quintile long-short (this is a CROSS-SECTIONAL factor, so the
              mirror is the cross-section of names on each report-period, NOT a single-name timer).
  - increment = the signal itself (buyback_yield, net_issuance) vs SPY-excess forward return; there is
              no A/B "increment over an existing signal" here — this is a first look at whether the
              factor exists at all in this data.
  - horizon = 63 / 126 / 252 trading days (~3m/6m/12m), matching a slow fundamental capital-cycle signal.
  - Point-in-time: signal uses cash-flow with period-end <= (known_date - LAG); returns use prices
    STRICTLY AFTER known_date. LAG = 75 calendar days (uniform reporting-lag ASSUMPTION: covers the
    10-K 60-day large-accelerated-filer deadline + buffer; 10-Q is 40d so 75 is conservative for all).
  - Denominator = point-in-time market cap AS-OF known_date (defeatbeta market_capitalization(), daily).
  - Prices = defeatbeta price().close for both name and SPY (same vendor/timestamp convention as
    exp_valuation_broad / exp_family_validate). Forward excess = name_fwd - SPY_fwd.

Cost assumptions: NONE modelled — this is a cross-sectional IC / quintile-spread SCREEN (is there edge
in the ranking?), not a live PnL. Equal-weight, costless, overlapping windows (autocorr caveat noted).

Universe: top-10 US holdings of all 11 SPDR sector ETFs (~90-110 names, sector-labelled) — reuses
exp_valuation_broad.build_universe() verbatim. CAVEAT: this is mega/large-cap tilted (SPDR top-10), it
does NOT cover small-caps unlike the repo's usual 4-asset-class standard; the user explicitly asked to
mirror exp_valuation_broad's universe method for THIS task, so the cap-size tilt is disclosed, not fixed.

Data caveat (load-bearing): defeatbeta quarterly_cash_flow only spans ~16 quarters (~2022Q2..2026Q1).
The whole test therefore lives in ONE macro regime (post-COVID / rate-hike / AI-capex). A null/weak
result here does NOT disprove the multi-decade academic factor; a positive result is one-regime-fragile.

Run: python backtest/experiments/exp_buyback_capital_allocation.py
"""
from __future__ import annotations

import contextlib
import io
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with contextlib.redirect_stdout(io.StringIO()):
    from defeatbeta_api.data.ticker import Ticker
import yfinance as yf

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".insider_data")
_CACHE = os.path.join(_DATA, "buyback_cap_alloc.pkl")

HORIZONS = [63, 126, 252]
LAG_DAYS = 75                 # uniform reporting-lag assumption (see docstring)
MIN_NAMES = 25                # per-date cross-section must have >= this many names to compute an IC
MIN_DATES = 6                 # report a Fama-MacBeth IC once >= this many cross-section dates (relaxed
                              # from exp_family_validate's 12 because the cash-flow history is only ~16Q;
                              # n_dates is printed so the reader sees the thin ones)
SECTORS = {"XLK": "Tech", "XLC": "Comm", "XLY": "Discr", "XLI": "Indus", "XLF": "Fin",
           "XLB": "Materl", "XLE": "Energy", "XLV": "Health", "XLP": "Staples",
           "XLU": "Util", "XLRE": "RealEst"}


def build_universe():
    """sym -> sector, from top-10 US holdings of each SPDR sector ETF (verbatim exp_valuation_broad)."""
    uni = {}
    for etf, name in SECTORS.items():
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                th = yf.Ticker(etf).funds_data.top_holdings
            for sym in th.index:
                s = str(sym)
                if "." not in s and s not in uni:   # US-listed, first sector wins
                    uni[s] = name
        except Exception:
            continue
    return uni


def _num(v):
    try:
        s = str(v).strip()
        if s in ("*", "", "None", "nan", "NaN"):
            return np.nan
        return float(v)
    except Exception:
        return np.nan


def _cf_rows(cf):
    """Extract {period_end -> value} for the buyback (magnitude-negative) and net-issuance rows."""
    cf = cf.data if hasattr(cf, "data") else cf
    bd = cf["Breakdown"].astype(str)
    datecols = [c for c in cf.columns if c not in ("Breakdown", "TTM")]

    def getrow(*names):
        for name in names:
            m = bd == name
            if m.any():
                row = cf[m].iloc[0]
                return {pd.Timestamp(c): _num(row[c]) for c in datecols}
        return None

    rep = getrow("Repurchase of Capital Stock", "Common Stock Payments")
    nci = getrow("Net Common Stock Issuance")
    # reconciliation helpers (only used for the printed sanity check)
    gross_iss = getrow("Common Stock Issuance", "Issuance of Capital Stock")
    csp = getrow("Common Stock Payments")
    return rep, nci, gross_iss, csp


def _series(df, val_col):
    df = df.data if hasattr(df, "data") else df
    s = pd.Series(pd.to_numeric(df[val_col], errors="coerce").values,
                  index=pd.to_datetime(df["report_date"], errors="coerce")).dropna().sort_index()
    return s[~s.index.duplicated()]


def _pull_one(tk):
    """Pull cash-flow rows + point-in-time market-cap + close price for one ticker (no cache)."""
    out = {"rep": None, "nci": None, "gross_iss": None, "csp": None, "mcap": None, "px": None}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            cf = Ticker(tk).quarterly_cash_flow()
        out["rep"], out["nci"], out["gross_iss"], out["csp"] = _cf_rows(cf)
    except Exception:
        pass
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            mc = Ticker(tk).market_capitalization()
        out["mcap"] = _series(mc, "market_capitalization")
    except Exception:
        pass
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            px = Ticker(tk).price()
        out["px"] = _series(px, "close")
    except Exception:
        pass
    return out


def _load_universe_data(tickers):
    """Disk-cached (pickle) pull of cash-flow/mcap/price for the universe + SPY. Self-heals None keys."""
    cache = {}
    if os.path.exists(_CACHE):
        try:
            cache = pickle.load(open(_CACHE, "rb"))
        except Exception:
            cache = {}
    syms = sorted(set(tickers) | {"SPY"})
    need = [t for t in syms if not cache.get(t) or cache[t].get("px") is None]
    for i, t in enumerate(need):
        cache[t] = _pull_one(t)
        if i % 25 == 24:
            pickle.dump(cache, open(_CACHE, "wb"))
    pickle.dump(cache, open(_CACHE, "wb"))
    return cache


def _fwd_excess(px, spy, known_date, h):
    if px is None or spy is None or len(px) < 30 or len(spy) < 30:
        return np.nan
    pos = px.index.searchsorted(known_date)
    sp = spy.index.searchsorted(known_date)
    if pos >= len(px) or sp >= len(spy) or pos + h >= len(px) or sp + h >= len(spy):
        return np.nan
    p0, s0 = px.iloc[pos], spy.iloc[sp]
    if p0 <= 0 or s0 <= 0:
        return np.nan
    return (px.iloc[pos + h] / p0 - 1) - (spy.iloc[sp + h] / s0 - 1)


def build_panel(uni, cache):
    """Long DataFrame of point-in-time name-quarter observations."""
    spy = cache.get("SPY", {}).get("px")
    rows = []
    for sym, sec in uni.items():
        d = cache.get(sym)
        if not d or d.get("rep") is None or d.get("nci") is None:
            continue
        rep, nci, mcap, px = d["rep"], d["nci"], d.get("mcap"), d.get("px")
        if mcap is None or px is None:
            continue
        quarters = sorted(q for q in rep if q in nci)   # quarter-ends present in both rows
        for i in range(3, len(quarters)):               # need 4 trailing quarters
            win = quarters[i - 3:i + 1]
            rep4 = [abs(rep[q]) for q in win]
            nci4 = [nci[q] for q in win]
            if any(pd.isna(x) for x in rep4) or any(pd.isna(x) for x in nci4):
                continue
            q_end = quarters[i]
            known = q_end + pd.Timedelta(days=LAG_DAYS)
            mc = mcap.asof(known)                        # point-in-time cap at known-date
            if pd.isna(mc) or mc <= 0:
                continue
            row = {"sym": sym, "sec": sec, "q_end": q_end, "known": known,
                   "buyback_yield": sum(rep4) / mc, "net_issuance": sum(nci4) / mc}
            for h in HORIZONS:
                row[f"f{h}"] = _fwd_excess(px, spy, known, h)
            rows.append(row)
    return pd.DataFrame(rows)


def _pooled_ic(df, sig, h):
    """Single Spearman across ALL name-quarter obs (the 'pool everything' lens)."""
    g = df[[sig, f"f{h}"]].dropna()
    if len(g) < 30:
        return None
    r = g[sig].corr(g[f"f{h}"], method="spearman")
    n = len(g)
    t = r * np.sqrt((n - 2) / (1 - r * r)) if abs(r) < 1 else np.nan
    return {"r": r, "t": t, "n": n}


def _fm_ic(df, sig, h):
    """Fama-MacBeth per-cross-section (group by q_end) Spearman IC — mirrors exp_family_validate._ic."""
    ics = []
    for _, g in df.groupby("q_end"):
        g = g[[sig, f"f{h}"]].dropna()
        if len(g) >= MIN_NAMES and g[sig].nunique() > 5:
            ics.append(g[sig].corr(g[f"f{h}"], method="spearman"))
    ics = [x for x in ics if x == x]
    if len(ics) < MIN_DATES:
        return None
    a = np.array(ics)
    return {"mean": a.mean(), "t": a.mean() / (a.std() / np.sqrt(len(a))) if a.std() else np.nan,
            "hit": (a > 0).mean(), "n_dates": len(a)}


def _quintile_spread(df, sig, h):
    """Pooled quintile Q5-Q1 mean forward excess + Welch t + n/quintile + cutoffs."""
    g = df[[sig, f"f{h}"]].dropna()
    if len(g) < 50:
        return None
    q = g[sig].quantile([0.2, 0.4, 0.6, 0.8]).values
    top = g[g[sig] >= q[3]][f"f{h}"]
    bot = g[g[sig] <= q[0]][f"f{h}"]
    means = [g[g[sig] <= q[0]][f"f{h}"].mean(),
             g[(g[sig] > q[0]) & (g[sig] <= q[1])][f"f{h}"].mean(),
             g[(g[sig] > q[1]) & (g[sig] <= q[2])][f"f{h}"].mean(),
             g[(g[sig] > q[2]) & (g[sig] <= q[3])][f"f{h}"].mean(),
             g[g[sig] > q[3]][f"f{h}"].mean()]
    sp = top.mean() - bot.mean()
    se = np.sqrt(top.var(ddof=1) / len(top) + bot.var(ddof=1) / len(bot))
    t = sp / se if se else np.nan
    return {"spread": sp, "t": t, "means": means, "cut": q, "n_top": len(top), "n_bot": len(bot)}


def _print_reco_cutoffs(df):
    print("\n=== signal distribution (pooled name-quarter obs) — for grounding any recommendation ===")
    for sig in ("buyback_yield", "net_issuance"):
        s = df[sig].dropna()
        qs = s.quantile([0.1, 0.2, 0.5, 0.8, 0.9])
        print(f"  {sig:14}: n={len(s)}  p10={qs.iloc[0]*100:+.2f}%  p20={qs.iloc[1]*100:+.2f}%  "
              f"median={qs.iloc[2]*100:+.2f}%  p80={qs.iloc[3]*100:+.2f}%  p90={qs.iloc[4]*100:+.2f}%  "
              f"(as % of market cap, trailing-4Q)")


def run():
    uni = build_universe()
    from collections import Counter
    print(f"universe = {len(uni)} US names across {len(SECTORS)} SPDR sectors  {dict(Counter(uni.values()))}")
    print(f"pulling cash-flow / market-cap / price via defeatbeta (disk-cached {os.path.basename(_CACHE)}) ...")
    cache = _load_universe_data(list(uni))

    # --- reconciliation sanity check: does Net Common Stock Issuance net gross issuance vs buybacks? ---
    print("\n=== reconciliation: Net Common Stock Issuance  ?=  CommonStockIssuance + CommonStockPayments ===")
    for tk in ["AAPL", "MSFT", "XOM", "NVDA"]:
        d = cache.get(tk, {})
        rep, nci, gi, csp = d.get("rep"), d.get("nci"), d.get("gross_iss"), d.get("csp")
        if not (rep and nci):
            continue
        q = max(nci)
        gi_v = gi.get(q, np.nan) if gi else np.nan
        csp_v = csp.get(q, np.nan) if csp else np.nan
        recon = (gi_v if gi_v == gi_v else 0.0) + (csp_v if csp_v == csp_v else 0.0)
        print(f"  {tk} {q.date()}: NCI={nci[q]/1e9:+.2f}B  gross_iss={gi_v/1e9 if gi_v==gi_v else float('nan'):+.2f}B"
              f"  CS_pay={csp_v/1e9 if csp_v==csp_v else float('nan'):+.2f}B  -> iss+pay={recon/1e9:+.2f}B"
              f"  repurchase={rep[q]/1e9:+.2f}B")

    df = build_panel(uni, cache)
    if df.empty:
        print("\nEMPTY PANEL — abort"); return
    n_names = df["sym"].nunique()
    print(f"\npanel: {len(df)} name-quarter obs, {n_names} names, "
          f"{df['q_end'].nunique()} report-periods ({df['q_end'].min().date()}..{df['q_end'].max().date()})")

    _print_reco_cutoffs(df)

    # ============================ POOLED (whole universe) ============================
    print("\n" + "=" * 78)
    print("POOLED — whole universe.  buyback_yield: HIGH=more buybacks (expect +).  "
          "net_issuance: HIGH=more dilution (expect -).")
    print("=" * 78)
    for sig in ("buyback_yield", "net_issuance"):
        print(f"\n--- {sig} ---")
        print(f"  {'hor':>4} | {'FM-IC':>7} {'FM-t':>6} {'hit':>5} {'nDt':>4} | "
              f"{'poolIC':>7} {'pool-t':>6} {'nObs':>5} | {'Q5-Q1':>7} {'sprd-t':>6}  quintile means (Q1..Q5) %")
        for h in HORIZONS:
            fm = _fm_ic(df, sig, h)
            pl = _pooled_ic(df, sig, h)
            qs = _quintile_spread(df, sig, h)
            fm_s = f"{fm['mean']:+.3f} {fm['t']:>6.2f} {fm['hit']:>4.0%} {fm['n_dates']:>4}" if fm else "   (insufficient) "
            pl_s = f"{pl['r']:+.3f} {pl['t']:>6.2f} {pl['n']:>5}" if pl else "  (insuff)   "
            if qs:
                qm = " ".join(f"{m*100:>6.1f}" for m in qs["means"])
                qs_s = f"{qs['spread']*100:>+6.1f}% {qs['t']:>6.2f}  {qm}"
            else:
                qs_s = "  (insufficient)"
            print(f"  {h:>3}d | {fm_s} | {pl_s} | {qs_s}")

    # ============================ SECTOR BREAKDOWN ============================
    print("\n" + "=" * 78)
    print("BY SECTOR — pooled Spearman IC + Q5-Q1 spread within each sector (per-date IC impossible: "
          "~10 names/sector < 25).  n honestly reported; thin n = do not over-read.")
    print("=" * 78)
    for sig in ("buyback_yield", "net_issuance"):
        print(f"\n--- {sig}  (pooled within sector) ---")
        print(f"  {'sector':8} {'nNm':>4} {'nObs':>5} | " +
              " | ".join(f"{'IC'+str(h):>7} {'t':>5}" for h in HORIZONS) + f" | {'Q5-Q1@126d':>10} {'t':>5}")
        for sec in SECTORS.values():
            sub = df[df["sec"] == sec]
            if sub.empty:
                continue
            nnm = sub["sym"].nunique()
            nobs = len(sub[["buyback_yield"] + [f"f{h}" for h in HORIZONS]].dropna())
            cells = []
            for h in HORIZONS:
                pl = _pooled_ic(sub, sig, h)
                cells.append(f"{pl['r']:>+7.3f} {pl['t']:>5.2f}" if pl else f"{'--':>7} {'--':>5}")
            qs = _quintile_spread(sub, sig, 126)
            qcell = f"{qs['spread']*100:>+9.1f}% {qs['t']:>5.2f}" if qs else f"{'--':>10} {'--':>5}"
            print(f"  {sec:8} {nnm:>4} {nobs:>5} | " + " | ".join(cells) + f" | {qcell}")

    print("\nNOTE: cross-sectional SCREEN (equal-weight, costless, overlapping fwd windows -> autocorr, "
          "single ~2022-2026 regime). FM-t>~2 or a monotone Q1->Q5 = real ranking edge; anything weaker "
          "in this short window is inconclusive, NOT a disproof of the multi-decade academic factor.")


if __name__ == "__main__":
    run()
