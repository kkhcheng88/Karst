"""CIO Phase-0 validation for the INSIDER family -- does insider open-market BUYING actually predict?

The one Phase-3 signal that is BACKFILLABLE (so it can be walk-forward / deflated-Sharpe tested, unlike
the thesis confidences). Data = SEC bulk Form 345 quarterly data sets (pre-parsed, whole market):
  SUBMISSION (ticker, 10b5-1 flag) + NONDERIV_TRANS (code/shares/price/date) + REPORTINGOWNER (role).

Look-ahead-safe: entry = the Form 4 FILING_DATE (when the trade becomes public), NOT the trade date.
Signal = open-market PURCHASES (code P), 10b5-1 excluded, cluster = >=2 distinct insiders in a window.
Measures forward EXCESS return vs SPY (the cross-sectional edge, market beta removed) + a portfolio
Sharpe / deflated Sharpe (honest re: how many variants were tried).

    python backtest/exp_insider_validate.py            # 2022q1..2025q2 default
"""
import io
import os
import sys
import urllib.request
import zipfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data import load  # noqa: E402

_UA = {"User-Agent": "Karst-research/1.0 (contact research@karst.local)"}
_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".insider_data")
_HOR = [21, 63, 126]
_CLUSTER_WIN = 21        # trading-ish days: >=2 distinct owners filing P within this -> cluster
_MIN_VALUE = 500_000     # cluster $ must be >= this (meaningful conviction + more tradeable names)
_REENTRY = 63            # no re-fire for a ticker within this many days of an event


def _quarters(start="2022q1", end="2025q2"):
    ys, qs = int(start[:4]), int(start[5]); ye, qe = int(end[:4]), int(end[5])
    out = []
    y, q = ys, qs
    while (y, q) <= (ye, qe):
        out.append(f"{y}q{q}"); q += 1
        if q > 4:
            q = 1; y += 1
    return out


def _load_quarter(qtr):
    os.makedirs(_DATA, exist_ok=True)
    zp = os.path.join(_DATA, f"{qtr}_form345.zip")
    if not os.path.exists(zp):
        url = f"https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{qtr}_form345.zip"
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=120) as r, open(zp, "wb") as f:
            f.write(r.read())
    z = zipfile.ZipFile(zp)

    def tsv(name, cols):
        with z.open(name) as fh:
            txt = io.TextIOWrapper(fh, encoding="utf-8", errors="replace")
            have = pd.read_csv(io.StringIO(txt.readline()), sep="\t", nrows=0).columns
        with z.open(name) as fh:
            use = [c for c in cols if c in have]           # AFF10B5ONE absent in pre-2023 quarters
            return pd.read_csv(io.TextIOWrapper(fh, encoding="utf-8", errors="replace"),
                               sep="\t", usecols=use, dtype=str, low_memory=False)
    sub = tsv("SUBMISSION.tsv", ["ACCESSION_NUMBER", "FILING_DATE", "DOCUMENT_TYPE",
                                 "ISSUERTRADINGSYMBOL", "AFF10B5ONE"])
    if "AFF10B5ONE" not in sub.columns:
        sub["AFF10B5ONE"] = "0"                             # unknown pre-2023 -> keep (can't filter)
    tr = tsv("NONDERIV_TRANS.tsv", ["ACCESSION_NUMBER", "TRANS_CODE", "TRANS_SHARES",
                                    "TRANS_PRICEPERSHARE", "TRANS_ACQUIRED_DISP_CD"])
    own = tsv("REPORTINGOWNER.tsv", ["ACCESSION_NUMBER", "RPTOWNERCIK", "RPTOWNER_RELATIONSHIP"])
    tr = tr[(tr["TRANS_CODE"] == "P") & (tr["TRANS_ACQUIRED_DISP_CD"] == "A")].copy()   # open-market BUY
    tr["shares"] = pd.to_numeric(tr["TRANS_SHARES"], errors="coerce")
    tr["price"] = pd.to_numeric(tr["TRANS_PRICEPERSHARE"], errors="coerce")
    tr["value"] = tr["shares"] * tr["price"]
    tr = tr[tr["value"] > 0]
    df = tr.merge(sub, on="ACCESSION_NUMBER").merge(own, on="ACCESSION_NUMBER")
    df = df[(df["DOCUMENT_TYPE"] == "4") & (df["AFF10B5ONE"] != "1")]                   # exclude 10b5-1
    df["ticker"] = df["ISSUERTRADINGSYMBOL"].str.upper().str.strip()
    df["filed"] = pd.to_datetime(df["FILING_DATE"], format="%d-%b-%Y", errors="coerce")
    df = df.dropna(subset=["ticker", "filed"])
    df = df[df["ticker"].str.match(r"^[A-Z]{1,5}$")]                                    # drop odd symbols
    return df[["ticker", "filed", "value", "RPTOWNERCIK", "RPTOWNER_RELATIONSHIP"]]


def build_events(qtrs):
    raw = pd.concat([_load_quarter(q) for q in qtrs], ignore_index=True)
    # aggregate P-buys to (ticker, filed-day): sum value, distinct owners
    day = (raw.groupby(["ticker", "filed"])
              .agg(val=("value", "sum"), owners=("RPTOWNERCIK", "nunique"))
              .reset_index().sort_values(["ticker", "filed"]))
    events = []
    for tk, g in day.groupby("ticker"):
        g = g.reset_index(drop=True)
        last = None
        for i in range(len(g)):
            win = g[(g["filed"] > g.loc[i, "filed"] - pd.Timedelta(days=_CLUSTER_WIN * 1.6)) &
                    (g["filed"] <= g.loc[i, "filed"])]
            owners = int(win["owners"].sum()); val = float(win["val"].sum())
            if owners >= 2 and val >= _MIN_VALUE:                                       # CLUSTER buy
                d = g.loc[i, "filed"]
                if last is None or (d - last).days > _REENTRY:
                    events.append({"ticker": tk, "date": d, "owners": owners, "value": val})
                    last = d
    return pd.DataFrame(events)


_PX = {}
def _px_series(tk):
    """Prices from defeatbeta (DuckDB-cached, NO rate limit, and it RETAINS delisted names' history ->
    less survivorship bias than yfinance, which failed on delisted event names)."""
    try:
        from defeatbeta_api.data.ticker import Ticker
        d = Ticker(tk).price()
        d = d.data if hasattr(d, "data") else d
        s = pd.Series(pd.to_numeric(d["close"], errors="coerce").values,
                      index=pd.to_datetime(d["report_date"], errors="coerce")).dropna().sort_index()
        return s if len(s) > 60 else None
    except Exception:
        return None


def _batch_prices(tickers, start=None):
    """Price all event tickers + SPY via defeatbeta; disk-cache so re-runs are instant. (start ignored;
    defeatbeta returns full history.)"""
    import pickle
    pxc = os.path.join(_DATA, "px_defeatbeta.pkl")
    cache = {}
    if os.path.exists(pxc):
        try:
            cache = pickle.load(open(pxc, "rb"))
        except Exception:
            cache = {}
    syms = sorted(set(tickers) | {"SPY"})
    need = [t for t in syms if t not in cache]
    for i, t in enumerate(need):
        cache[t] = _px_series(t)
        if i % 250 == 249:
            pickle.dump(cache, open(pxc, "wb"))
    pickle.dump(cache, open(pxc, "wb"))
    for t in syms:
        _PX[t] = cache.get(t)
    print(f"[insider-validate] priced {sum(_PX.get(t) is not None for t in syms)}/{len(syms)} via "
          f"defeatbeta (SPY {'ok' if _PX.get('SPY') is not None else 'MISSING'})")


def _px(tk):
    return _PX.get(tk)


def _fwd(s, d, n):
    if s is None:
        return None
    pos = s.index.searchsorted(pd.Timestamp(d))
    if pos >= len(s) or pos + n >= len(s):
        return None
    p0 = s.iloc[pos]
    return (s.iloc[pos + n] / p0 - 1.0) if p0 > 0 else None


def run(start="2022q1", end="2025q2"):
    qtrs = _quarters(start, end)
    print(f"[insider-validate] quarters {qtrs[0]}..{qtrs[-1]} ({len(qtrs)})")
    ev = build_events(qtrs)
    print(f"[insider-validate] cluster-buy events: {len(ev)} across {ev['ticker'].nunique()} tickers")
    if ev.empty:
        return ev
    _batch_prices(ev["ticker"].tolist(), start=(ev["date"].min() - pd.Timedelta(days=10)).date().isoformat())
    spy = _px("SPY")
    rows = []
    for _, e in ev.iterrows():
        s = _px(e["ticker"])
        rec = {"date": e["date"], "ticker": e["ticker"]}
        ok = False
        for n in _HOR:
            r = _fwd(s, e["date"], n); b = _fwd(spy, e["date"], n)
            rec[f"x{n}"] = (r - b) if (r is not None and b is not None) else np.nan
            ok = ok or (r is not None)
        if ok:
            rows.append(rec)
    df = pd.DataFrame(rows)
    print(f"[insider-validate] matured events with prices: {len(df)}\n")
    print("=== EVENT STUDY: forward EXCESS return vs SPY after an insider cluster-buy ===")
    print(f"{'horizon':>8} {'n':>6} {'mean%':>8} {'median%':>8} {'hit>0':>7} {'t-stat':>7}")
    for n in _HOR:
        x = df[f"x{n}"].dropna()
        if len(x) < 20:
            print(f"{n:>7}d {len(x):>6}  (insufficient)"); continue
        t = x.mean() / (x.std() / np.sqrt(len(x)))
        print(f"{n:>7}d {len(x):>6} {x.mean() * 100:>8.2f} {x.median() * 100:>8.2f} "
              f"{(x > 0).mean():>7.0%} {t:>7.2f}")
    # portfolio: monthly-rebalanced equal-weight basket of names with a cluster-buy in the last 63d,
    # held 63d -> return series -> Sharpe + deflated Sharpe
    try:
        from metrics import deflated_sharpe_ratio as dsr
    except Exception:
        dsr = None
    _portfolio(df, ev, dsr)
    return df


def _portfolio(df, ev, dsr):
    print("\n=== PORTFOLIO: monthly cohort of cluster-buy names, hold H days, mean EXCESS vs SPY ===")
    hold_per_yr = {21: 12, 63: 4, 126: 2}          # ~non-overlapping windows per year per horizon
    series, sharpes = {}, []
    for n in _HOR:
        d = df.dropna(subset=[f"x{n}"]).copy()
        if len(d) < 30:
            continue
        d["m"] = d["date"].values.astype("datetime64[M]")
        m = d.groupby("m")[f"x{n}"].mean().dropna()    # each month's cohort mean H-day excess
        if len(m) < 12 or not m.std():
            continue
        s_ann = (m.mean() / m.std()) * np.sqrt(hold_per_yr[n])
        series[n] = m; sharpes.append(s_ann)
        print(f"  {n:>3}d hold: {len(m):>3} monthly cohorts | mean excess {m.mean() * 100:>6.2f}% | "
              f"hit {(m > 0).mean():>3.0%} | Sharpe(ann) {s_ann:>5.2f}")
    if 63 in series and dsr and len(sharpes) >= 2:
        m = series[63]
        try:
            ds = dsr(m.values, sharpes, periods_per_year=hold_per_yr[63])
            print(f"\n  deflated Sharpe (63d hold, vs the {len(sharpes)} horizon variants tried): {ds:.3f}")
            print("  (DSR is a PROBABILITY the true Sharpe>0 after multiple-testing; >0.95 = strong.)")
        except Exception as e:
            print(f"  deflated Sharpe: n/a ({str(e)[:50]})")
    print("  NOTE: overlapping windows + a small trial universe -> a SCREEN, not live PnL; equal-weight,"
          " costless, survivorship in yfinance prices. Honest read = the event-study t-stats above.")


if __name__ == "__main__":
    a = sys.argv[1:]
    run(a[0] if a else "2022q1", a[1] if len(a) > 1 else "2025q2")
