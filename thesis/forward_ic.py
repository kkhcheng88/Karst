"""Forward IC evaluator -- the NHITL judge of Phase 3.

Measures whether thesis CONFIDENCE rank-orders forward returns (Information Coefficient), the
success criterion from DESIGN section 8 (thesis-ranked forward IC >= ~0.05 beats SPY; 0.10 doubles it).

Honest constraint: IC CANNOT be backfilled -- the theses did not exist historically, so applying
today's confidence to past prices would be look-ahead. It ACCUMULATES FORWARD:
  log (daily) -> predictions pile up point-in-time -> as each horizon matures -> cross-sectional
  Spearman IC per date -> mean IC / IR over dates. First 21d read ~1 month out; a significant mean
  IC needs ~3-6 months of daily logs. No verdict today by design -- this is the machine + the clock.

Data: prices via yfinance (adjusted total return, backtest/data.py); predictions from themes.yaml.
No new data needed -- only TIME and a daily `log` cadence.

    python thesis/forward_ic.py log       # append today's thesis cross-section (point-in-time, dedup)
    python thesis/forward_ic.py ic        # compute IC from MATURED predictions (+ coverage)
    python thesis/forward_ic.py report     # write thesis/ic_report.md snapshot
"""
import datetime as dt
import json
import os
import sys

import pandas as pd
import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "..", "backtest"))
TRACK = os.path.join(ROOT, "track_record.jsonl")
THEMES = os.path.join(ROOT, "themes.yaml")
HORIZONS = [21, 63, 126]        # trading days ~ 1 / 3 / 6 months
MIN_NAMES = 5                   # min matured tickers on a date to compute a cross-sectional IC
BENCH = "SPY"


def _themes():
    return (yaml.safe_load(open(THEMES, encoding="utf-8")) or {}).get("themes", {}) or {}


def _load_track():
    rows = []
    if os.path.exists(TRACK):
        for line in open(TRACK, encoding="utf-8"):
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _price(sym):
    """Adjusted total-return close series indexed by date (yfinance-first). None on failure."""
    try:
        from data import load
        df = load(sym, adjusted=True, min_rows=20)   # date = index, cols o/h/l/close/volume
        s = df["close"].copy()
        s.index = pd.to_datetime(df.index)
        return s.sort_index()
    except Exception:
        return None


def log_predictions():
    """Append today's full thesis cross-section (every thesis ticker x its confidence)."""
    themes = _themes()
    spy = _price(BENCH)
    asof = (spy.index[-1] if spy is not None else pd.Timestamp(dt.date.today())).strftime("%Y-%m-%d")
    existing = {(r["ts"], r["ticker"], r["thesis_id"]) for r in _load_track()}
    new = 0
    with open(TRACK, "a", encoding="utf-8") as f:
        for slug, t in themes.items():
            conf = t.get("confidence")
            cyc = t.get("cycle_stage")
            for tk in (t.get("tickers") or []):
                key = (asof, tk, slug)
                if key in existing:
                    continue
                f.write(json.dumps({"ts": asof, "ticker": tk, "thesis_id": slug,
                                    "confidence": conf, "cycle_stage": cyc}, ensure_ascii=False) + "\n")
                existing.add(key)
                new += 1
    print(f"[forward_ic] logged {new} new predictions (as-of {asof}) -> {TRACK}")


def _fwd_return(s, ts, n):
    """Return (fwd_ret, target_date) for n trading days after ts using series s; None if not matured."""
    idx = s.index
    pos = idx.searchsorted(pd.Timestamp(ts))
    if pos >= len(idx):
        return None
    if pos + n >= len(idx):
        return None                      # horizon not matured yet
    p0, p1 = s.iloc[pos], s.iloc[pos + n]
    if not (p0 > 0):
        return None
    return (p1 / p0 - 1.0, idx[pos + n])


def _bench_return(bench, ts, target_date):
    if bench is None:
        return None
    i0 = bench.index.searchsorted(pd.Timestamp(ts))
    i1 = bench.index.searchsorted(pd.Timestamp(target_date))
    if i0 >= len(bench) or i1 >= len(bench):
        return None
    p0, p1 = bench.iloc[i0], bench.iloc[i1]
    return (p1 / p0 - 1.0) if p0 > 0 else None


def compute_ic(verbose=True):
    preds = _load_track()
    if not preds:
        print("[forward_ic] no predictions logged yet -- run `log` first."); return {}
    tickers = sorted({r["ticker"] for r in preds})
    prices = {t: _price(t) for t in tickers}
    bench = _price(BENCH)
    missing = [t for t in tickers if prices[t] is None]
    out = {}
    if verbose:
        n_dates = len({r["ts"] for r in preds})
        print(f"[forward_ic] {len(preds)} predictions | {len(tickers)} tickers | {n_dates} date(s)"
              f" | price-load failed: {len(missing)} {missing[:8]}")
    for n in HORIZONS:
        # per-prediction forward + excess
        recs = []
        pending = 0
        for r in preds:
            s = prices.get(r["ticker"])
            if s is None or r.get("confidence") is None:
                continue
            fr = _fwd_return(s, r["ts"], n)
            if fr is None:
                pending += 1
                continue
            fwd, tdate = fr
            br = _bench_return(bench, r["ts"], tdate)
            recs.append({"ts": r["ts"], "conf": r["confidence"], "fwd": fwd,
                         "excess": (fwd - br) if br is not None else None})
        df = pd.DataFrame(recs)
        # cross-sectional Spearman per date, then average
        ic_raw, ic_exc = [], []
        if not df.empty:
            for ts, g in df.groupby("ts"):
                if g["conf"].nunique() >= 2 and len(g) >= MIN_NAMES:
                    ic_raw.append(g["conf"].corr(g["fwd"], method="spearman"))
                    ge = g.dropna(subset=["excess"])
                    if ge["conf"].nunique() >= 2 and len(ge) >= MIN_NAMES:
                        ic_exc.append(ge["conf"].corr(ge["excess"], method="spearman"))
        def agg(xs):
            xs = [x for x in xs if x == x]
            if not xs:
                return None
            s = pd.Series(xs)
            return {"mean": round(s.mean(), 3), "ir": round(s.mean() / s.std(), 2) if len(xs) > 1 and s.std() else None,
                    "hit": round((s > 0).mean(), 2), "n_dates": len(xs)}
        out[n] = {"matured": len(df), "pending": pending, "raw": agg(ic_raw), "excess": agg(ic_exc)}
        if verbose:
            print(f"\n  horizon {n}d: matured={len(df)} pending={pending}")
            print(f"    raw   IC: {out[n]['raw']}")
            print(f"    excess IC: {out[n]['excess']}")
    total_dates = len({r['ts'] for r in preds})
    if verbose:
        if total_dates < 20:
            print(f"\n  [honest] {total_dates} prediction date(s) -> PRELIMINARY / not significant."
                  f" Need ~20-50+ daily logs before the mean IC / IR means anything.")
    return out


def report():
    res = compute_ic(verbose=False)
    preds = _load_track()
    dates = sorted({r["ts"] for r in preds})
    lines = ["# Phase-3 forward IC report", "",
             f"predictions: {len(preds)} | tickers: {len({r['ticker'] for r in preds})} | "
             f"dates: {len(dates)} ({dates[0] if dates else '-'} .. {dates[-1] if dates else '-'})", "",
             "IC = cross-sectional Spearman(confidence, forward return), averaged over dates. "
             "Target >= 0.05 (excess-vs-SPY). Accumulates forward; NOT backfillable.", "",
             "| horizon | matured | pending | raw IC (mean/IR/hit/n) | excess IC (mean/IR/hit/n) |",
             "|---|---|---|---|---|"]
    for n in HORIZONS:
        r = res.get(n, {})
        def fmt(a):
            return f"{a['mean']}/{a['ir']}/{a['hit']}/{a['n_dates']}" if a else "-- (unmatured)"
        lines.append(f"| {n}d | {r.get('matured','-')} | {r.get('pending','-')} | "
                     f"{fmt(r.get('raw'))} | {fmt(r.get('excess'))} |")
    lines += ["", f"_status: {'PRELIMINARY -- accumulating' if len(dates) < 20 else 'active'};"
              f" {len(dates)} date(s) logged._"]
    open(os.path.join(ROOT, "ic_report.md"), "w", encoding="utf-8").write("\n".join(lines))
    print(f"[forward_ic] wrote {os.path.join(ROOT, 'ic_report.md')}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ic"
    if cmd == "log":
        log_predictions()
    elif cmd == "ic":
        compute_ic()
    elif cmd == "report":
        report()
    else:
        print(__doc__)
