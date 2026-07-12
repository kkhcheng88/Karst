"""Insider MARKET-WIDE $ sell/buy ratio -- macro timing probe (Edward Chancellor, *Capital Returns*,
Marathon Asset Management anecdote: Vickers-style aggregate insider sell:buy ratio ~16:1 in Apr-2006
(near a market top) vs ~2:1 in Oct-2008 (near the GFC bottom)). NOT the per-ticker cluster-buy signal
(exp_insider_validate) -- this aggregates ALL open-market Form-4 purchases (code P) and sales (code S)
across the WHOLE market into a monthly $ sell/buy ratio and tests whether extreme readings predict
forward SPY returns. Data: SEC bulk Form 345 (backtest/.insider_data, 2006q1-2025q2, 78 quarters,
already cached offline -- no re-pull, per task instructions).

Look-ahead-safe: FILING_DATE (not trade date) is the event date -- a Form 4 is public within ~2
business days of the trade, so a live pipeline COULD compute this same-day; only the SEC BULK
research dataset used here for backtesting lags 1-2 quarters in publication (irrelevant for this
backtest's statistical read, relevant as a deployment note if this were wired into P0-c).

    python backtest/experiments/exp_insider_market_ratio.py
"""
import io
import os
import sys
import zipfile

import numpy as np
import pandas as pd
from scipy import stats as sps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp_insider_validate as IV       # noqa: E402

HORS = {"3m": 63, "6m": 126, "12m": 252}
_ANECDOTE = [("2006-04", "Marathon: ~16:1 sell:buy near 2006-07 market top"),
             ("2008-10", "Marathon: ~2:1 sell:buy near GFC bottom"),
             ("2009-03", "SPY cycle bottom (2026-context hindsight check)"),
             ("2020-03", "COVID crash bottom (hindsight check)")]


def _load_quarter_buysell(qtr):
    """Like exp_insider_validate._load_quarter but keeps BOTH open-market P (buy, disp A) and
    S (sell, disp D), market-wide (no ticker restriction). Offline-only: raises if the cached zip
    is missing (per task instructions -- do not re-pull)."""
    zp = os.path.join(IV._DATA, f"{qtr}_form345.zip")
    if not os.path.exists(zp):
        raise FileNotFoundError(f"{zp} not cached -- expected all 2006q1-2025q2 zips present offline")
    z = zipfile.ZipFile(zp)

    def tsv(name, cols):
        with z.open(name) as fh:
            txt = io.TextIOWrapper(fh, encoding="utf-8", errors="replace")
            have = pd.read_csv(io.StringIO(txt.readline()), sep="\t", nrows=0).columns
        with z.open(name) as fh:
            use = [c for c in cols if c in have]
            return pd.read_csv(io.TextIOWrapper(fh, encoding="utf-8", errors="replace"),
                               sep="\t", usecols=use, dtype=str, low_memory=False)

    sub = tsv("SUBMISSION.tsv", ["ACCESSION_NUMBER", "FILING_DATE", "DOCUMENT_TYPE", "AFF10B5ONE"])
    if "AFF10B5ONE" not in sub.columns:
        sub["AFF10B5ONE"] = "0"                             # unknown pre-2023 -> keep, can't filter
    tr = tsv("NONDERIV_TRANS.tsv", ["ACCESSION_NUMBER", "TRANS_CODE", "TRANS_SHARES",
                                    "TRANS_PRICEPERSHARE", "TRANS_ACQUIRED_DISP_CD"])
    own = tsv("REPORTINGOWNER.tsv", ["ACCESSION_NUMBER", "RPTOWNERCIK"])
    tr = tr[((tr["TRANS_CODE"] == "P") & (tr["TRANS_ACQUIRED_DISP_CD"] == "A")) |
            ((tr["TRANS_CODE"] == "S") & (tr["TRANS_ACQUIRED_DISP_CD"] == "D"))].copy()
    tr["shares"] = pd.to_numeric(tr["TRANS_SHARES"], errors="coerce")
    tr["price"] = pd.to_numeric(tr["TRANS_PRICEPERSHARE"], errors="coerce")
    tr["value"] = tr["shares"] * tr["price"]
    tr = tr[tr["value"] > 0]
    # DATA-QUALITY GUARD (added after diagnosing the 2026-07-11 run): SEC bulk Form345 has rare
    # fat-finger filings -- e.g. ACCESSION 0001125282-06-002179 (ticker LCC, filed 2006-04-11) has
    # TRANS_PRICEPERSHARE = $67,550,000/share, turning ONE row into a $118 TRILLION "purchase" that
    # alone swamps that entire month's market-wide $ sum (and inverted the sign of the Apr-2006
    # anecdote check vs the literature). A raw dollar SUM (unlike a median/log-scaled regression)
    # has zero robustness to this, so filter implausible per-share prices (ceiling well above
    # BRK.A, the highest-priced legitimately-traded common stock in this sample) and implausible
    # single-transaction dollar values (no genuine open-market Form-4 trade in 2006-2025 approaches
    # $10B; even Bezos/Musk's largest single tranches were low single-digit billions).
    _PRICE_CAP, _TXN_CAP = 2_000_000, 10_000_000_000
    before_n, before_val = len(tr), tr["value"].sum()
    tr = tr[(tr["price"] <= _PRICE_CAP) & (tr["value"] <= _TXN_CAP)]
    if before_n != len(tr):
        print(f"[market-ratio][{qtr}] data-quality filter dropped {before_n - len(tr)} row(s), "
              f"${(before_val - tr['value'].sum())/1e9:,.1f}B of the ${before_val/1e9:,.1f}B raw sum")
    df = tr.merge(sub, on="ACCESSION_NUMBER").merge(own, on="ACCESSION_NUMBER")
    df = df[df["DOCUMENT_TYPE"] == "4"]
    df["filed"] = pd.to_datetime(df["FILING_DATE"], format="%d-%b-%Y", errors="coerce")
    df = df.dropna(subset=["filed"])
    return df[["filed", "TRANS_CODE", "value", "AFF10B5ONE", "RPTOWNERCIK"]]


def build_market_series(start="2006q1", end="2025q2", freq="M", exclude_10b51=False):
    qtrs = IV._quarters(start, end)
    raw = pd.concat([_load_quarter_buysell(q) for q in qtrs], ignore_index=True)
    print(f"[market-ratio] raw open-market P/S transactions {start}..{end}: {len(raw)} rows "
          f"({(raw.TRANS_CODE == 'P').sum()} buys / {(raw.TRANS_CODE == 'S').sum()} sells)")
    if exclude_10b51:
        before = len(raw)
        raw = raw[raw["AFF10B5ONE"] != "1"]
        print(f"[market-ratio] excl 10b5-1: {before} -> {len(raw)} rows "
              f"(flag only populated 2023q1+; earlier quarters unaffected/kept)")
    raw["period"] = raw["filed"].dt.to_period(freq)
    val = raw.groupby(["period", "TRANS_CODE"])["value"].sum().unstack(fill_value=0.0)
    val = val.rename(columns={"P": "buy_val", "S": "sell_val"})
    cnt = raw.groupby(["period", "TRANS_CODE"]).size().unstack(fill_value=0)
    cnt = cnt.rename(columns={"P": "buy_n", "S": "sell_n"})
    ins = raw.groupby(["period", "TRANS_CODE"])["RPTOWNERCIK"].nunique().unstack(fill_value=0)
    ins = ins.rename(columns={"P": "buy_insiders", "S": "sell_insiders"})
    out = val.join(cnt).join(ins).sort_index()
    out["sb_ratio"] = out["sell_val"] / out["buy_val"].replace(0, np.nan)
    out["sb_ratio_n"] = out["sell_n"] / out["buy_n"].replace(0, np.nan)
    out["date"] = out.index.to_timestamp(how="end")
    return out.reset_index(drop=True)


def newey_west_ols(y, x, lag):
    """OLS y = a + b*x with Newey-West HAC standard errors (Bartlett kernel). Needed because forward
    windows longer than the sampling step (e.g. 12m fwd return sampled monthly) overlap heavily ->
    plain OLS SEs understate the true uncertainty."""
    m = np.isfinite(y) & np.isfinite(x)
    y, x = y[m], x[m]
    n = len(y)
    if n < 20:
        return None
    X = np.column_stack([np.ones(n), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    XtX_inv = np.linalg.inv(X.T @ X)
    u = X * resid[:, None]
    S = u.T @ u
    for lg in range(1, lag + 1):
        w = 1 - lg / (lag + 1)
        gamma = u[lg:].T @ u[:-lg]
        S += w * (gamma + gamma.T)
    cov = XtX_inv @ S @ XtX_inv
    se = np.sqrt(np.maximum(np.diag(cov), 0))
    t = beta / np.where(se > 0, se, np.nan)
    r2 = 1 - (resid @ resid) / ((y - y.mean()) ** 2).sum()
    return dict(n=n, beta=beta, se=se, t=t, r2=r2)


def decile_test(m, ratio_col, hcol, label):
    d = m.dropna(subset=[ratio_col, hcol]).copy()
    if len(d) < 30:
        print(f"  {label}: n too small ({len(d)})")
        return
    d["dec"] = pd.qcut(d[ratio_col], 10, labels=False, duplicates="drop")
    top = d[d.dec == d.dec.max()][hcol]     # highest sell:buy -> predicted BEARISH
    bot = d[d.dec == d.dec.min()][hcol]     # lowest sell:buy (most buying) -> predicted BULLISH
    mid = d[(d.dec != d.dec.max()) & (d.dec != d.dec.min())][hcol]
    tstat, pval = sps.ttest_ind(bot.values, top.values, equal_var=False)
    print(f"  {label}: n={len(d)} | top-decile(most SELLING) mean fwd={top.mean()*100:+.2f}% (n={len(top)}) | "
          f"bottom-decile(most BUYING) mean fwd={bot.mean()*100:+.2f}% (n={len(bot)}) | "
          f"middle80% mean={mid.mean()*100:+.2f}% | "
          f"diff(bottom-top) t={tstat:+.2f} p={pval:.3f}")


def main():
    IV._batch_prices([])           # SPY only, reuse cache
    spy = IV._px("SPY")
    if spy is None:
        print("SPY price series unavailable -- abort"); return

    for excl in [False, True]:
        tag = "excl-10b5-1 (2023q1+ only meaningful)" if excl else "baseline (all open-market P/S)"
        print(f"\n{'='*90}\n=== BUILD: monthly market-wide $ sell/buy ratio, 2006-01..2025-06  [{tag}] ===\n{'='*90}")
        m = build_market_series(exclude_10b51=excl)
        print(f"[market-ratio] {len(m)} months built")

        for hname, hdays in HORS.items():
            fwd = []
            for d in m["date"]:
                r = IV._fwd(spy, d, hdays)
                fwd.append(r)
            m[f"fwd_{hname}"] = fwd

        print(f"\nsb_ratio ($ sell/$ buy) summary: min={m.sb_ratio.min():.2f} p10={m.sb_ratio.quantile(.1):.2f} "
              f"median={m.sb_ratio.median():.2f} p90={m.sb_ratio.quantile(.9):.2f} max={m.sb_ratio.max():.2f}")

        print("\n--- 1. ANECDOTE SPOT-CHECK (known market top/bottom months) ---")
        m2 = m.set_index(m["date"].dt.to_period("M").astype(str))
        for ym, note in _ANECDOTE:
            if ym in m2.index:
                row = m2.loc[ym]
                print(f"  {ym}: sb_ratio(${{}})={row.sb_ratio:.2f}  sb_ratio(n)={row.sb_ratio_n:.2f}  "
                      f"buy${row.buy_val/1e6:.0f}M sell${row.sell_val/1e6:.0f}M  -- {note}")
            else:
                print(f"  {ym}: not in sample -- {note}")

        print("\n--- 2. REGRESSION: forward SPY return ~ log(sb_ratio), Newey-West HAC (lag=horizon months) ---")
        for hname, hdays in HORS.items():
            lag_months = {"3m": 3, "6m": 6, "12m": 12}[hname]
            y = m[f"fwd_{hname}"].values.astype(float)
            x = np.log(m["sb_ratio"].values.astype(float))
            res = newey_west_ols(y, x, lag_months)
            if res is None:
                print(f"  {hname}: n too small"); continue
            print(f"  fwd {hname:>3} SPY ~ log(sb_ratio):  n={res['n']}  R2={res['r2']:.4f}  "
                  f"slope={res['beta'][1]:+.4f}  NW-t={res['t'][1]:+.2f}")

        print("\n--- 3. DECILE TEST: forward SPY return in extreme sb_ratio months (dollar-weighted) ---")
        for hname in HORS:
            decile_test(m, "sb_ratio", f"fwd_{hname}", f"fwd {hname} SPY, $ ratio")

        print("\n--- 4. ROBUSTNESS: same decile test using TRANSACTION-COUNT ratio (not $) ---")
        print("      (checks whether the $ result is just a few mega-dollar insider sales dominating)")
        for hname in HORS:
            decile_test(m, "sb_ratio_n", f"fwd_{hname}", f"fwd {hname} SPY, count ratio")

        print("\n--- 5. YEARLY sb_ratio ($) averages (sanity: does our data show 2006-07 high / 2008-09 low?) ---")
        yr = m.copy()
        yr["yr"] = yr["date"].dt.year
        g = yr.groupby("yr")["sb_ratio"].mean()
        for y_, v in g.items():
            print(f"    {y_}: {v:6.2f}")

        m.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              f"_market_ratio_monthly{'_excl10b51' if excl else ''}.csv"), index=False)

    print("\nREAD: 若 NW-t 顯著(|t|>~2)且方向啱(sb_ratio 高 -> forward SPY 低,反之亦然),且 decile "
          "test top vs bottom 有意義差距、count-ratio 同 $-ratio 方向一致 -> 訊號站得住腳,可以加入大市層"
          "工具箱。若得 $-ratio 顯著但 count-ratio 唔顯著 -> 可能係少數巨額 insider 沽貨(如億萬富豪程式化"
          "減持)主導,唔係真正嘅 breadth 訊號。")


if __name__ == "__main__":
    main()
