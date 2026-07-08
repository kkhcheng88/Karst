"""Forward IC evaluator -- the NHITL judge of Phase 3.

Measures whether thesis CONFIDENCE rank-orders forward returns (Information Coefficient), the
success criterion from DESIGN section 8 (thesis-ranked forward IC >= ~0.05 beats SPY; 0.10 doubles it).

Honest constraint: IC CANNOT be backfilled -- the theses did not exist historically, so applying
today's confidence to past prices would be look-ahead. It ACCUMULATES FORWARD:
  log (daily) -> predictions pile up point-in-time -> as each horizon matures -> cross-sectional
  Spearman IC per date -> mean IC / IR over dates. First 21d read ~1 month out; a significant mean
  IC needs ~3-6 months of daily logs. No verdict today by design -- this is the machine + the clock.

Data: prices via yfinance (adjusted total return, backtest/data.py); predictions logged into
thesis/track_record.jsonl by `thesis/log_predictions.py` (the ONE writer -- Phase-3 WS1 D1; this
module used to also write a thinner duplicate schema via its own `log_predictions()`, which caused
two schemas to co-exist in the same file. That function is retired; do not re-add it).
No new data needed -- only TIME and a daily logging cadence (see thesis/daily_ic.cmd for the chain:
log_predictions.py -> backfill_outcomes.py -> forward_ic.py report -> git commit).

    python thesis/forward_ic.py ic        # compute IC from MATURED predictions (+ coverage)
    python thesis/forward_ic.py report     # write thesis/ic_report.md snapshot (+ verdict, WS1 D3)
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
MIN_NAMES = 5                   # min matured tickers on a date to compute a daily cross-sectional IC
BENCH = "SPY"

# --- WS1 D3 judge state machine -------------------------------------------------------------
WEEKLY_MIN_NAMES = 8            # min distinct tickers in an ISO week for a valid weekly cross-section
THEME_MIN_NAMES = 4             # theme-level cross-section is thin (9 themes total) -- lighter floor
ROLLING_WEEKS = 26              # trailing window (weeks) the verdict is computed over
JUDGE_HORIZON = 63              # the horizon the PASS/FAIL verdict is based on (63d excess IC)
PRELIM_MATURED_MIN = 60         # below this many matured JUDGE_HORIZON rows -> PRELIMINARY, no verdict
PASS_MEAN_MIN = 0.05
PASS_IR_MIN = 0.5
FAIL_MEAN_MAX = 0.0
FAIL_MATURED_MIN = 150


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


def _matured_records(preds, prices, bench, n):
    """Row-level matured records for horizon n: ts, week, ticker, thesis_id, conf, fwd, excess.
    Also returns the pending count (predictions with a priceable ticker + confidence, not yet matured)."""
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
        recs.append({"ts": r["ts"], "week": _week_label(r["ts"]), "ticker": r["ticker"],
                     "thesis_id": r.get("thesis_id"), "conf": r["confidence"], "fwd": fwd,
                     "excess": (fwd - br) if br is not None else None})
    return recs, pending


def _week_label(ts):
    iso = pd.Timestamp(ts).isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _daily_cross_sectional_ic(df, min_names=MIN_NAMES):
    """Secondary/reference metric: per-calendar-date cross-sectional Spearman IC (raw + excess)."""
    ic_raw, ic_exc = [], []
    if not df.empty:
        for _ts, g in df.groupby("ts"):
            if g["conf"].nunique() >= 2 and len(g) >= min_names:
                ic_raw.append(g["conf"].corr(g["fwd"], method="spearman"))
                ge = g.dropna(subset=["excess"])
                if ge["conf"].nunique() >= 2 and len(ge) >= min_names:
                    ic_exc.append(ge["conf"].corr(ge["excess"], method="spearman"))
    return ic_raw, ic_exc


def _weekly_cross_sectional_ic(df, min_names, name_col):
    """Weekly, NON-overlapping cross-sectional Spearman IC(confidence, excess return) -- the judge's
    primary series (WS1 D3). One value per ISO week, built from matured rows whose ts falls in that
    week; a name seen on multiple days within the week is deduped (kept latest) so the same name
    doesn't get double-weighted. Returns [(week_label, ic), ...] sorted chronologically."""
    out = []
    if df.empty:
        return out
    for wk, g in df.groupby("week"):
        g = g.sort_values("ts").drop_duplicates(subset=[name_col], keep="last")
        if g["conf"].nunique() < 2 or len(g) < min_names:
            continue
        ge = g.dropna(subset=["excess"])
        if ge["conf"].nunique() >= 2 and len(ge) >= min_names:
            out.append((wk, ge["conf"].corr(ge["excess"], method="spearman")))
    out.sort(key=lambda x: x[0])
    return out


def _rolling_stats(weekly_ic, window=ROLLING_WEEKS):
    vals = [v for _, v in weekly_ic[-window:] if v == v]
    if not vals:
        return {"n_weeks": 0, "mean": None, "ir": None}
    s = pd.Series(vals)
    ir = round(s.mean() / s.std(), 2) if len(vals) > 1 and s.std() else None
    return {"n_weeks": len(vals), "mean": round(s.mean(), 4), "ir": ir}


def _agg_daily(xs):
    xs = [x for x in xs if x == x]
    if not xs:
        return None
    s = pd.Series(xs)
    return {"mean": round(s.mean(), 3), "ir": round(s.mean() / s.std(), 2) if len(xs) > 1 and s.std() else None,
            "hit": round((s > 0).mean(), 2), "n_dates": len(xs)}


def judge(weekly_ic_63, matured_63):
    """WS1 D3 state machine. weekly_ic_63 = _weekly_cross_sectional_ic(..., name_col='ticker') for
    the 63d horizon. Returns (status, circuit_breaker: bool, rolling: dict)."""
    rolling = _rolling_stats(weekly_ic_63)
    if matured_63 < PRELIM_MATURED_MIN or rolling["n_weeks"] == 0:
        return "PRELIMINARY", False, rolling
    if (rolling["mean"] is not None and rolling["mean"] <= FAIL_MEAN_MAX
            and matured_63 >= FAIL_MATURED_MIN):
        return "FAIL", True, rolling
    if (rolling["mean"] is not None and rolling["mean"] >= PASS_MEAN_MIN
            and rolling["ir"] is not None and rolling["ir"] >= PASS_IR_MIN):
        return "PASS", False, rolling
    return "MONITORING", False, rolling  # neither threshold met yet; no verdict, still accumulating


def compute_ic(verbose=True):
    """Quick CLI check (`python thesis/forward_ic.py ic`) -- per-horizon matured/pending + daily
    raw/excess IC. Unchanged output shape from pre-WS1 (kept for the daily eyeball check);
    the judged verdict lives in report()/judge() (weekly, rolling-26w -- WS1 D3)."""
    preds = _load_track()
    if not preds:
        print("[forward_ic] no predictions logged yet -- run `thesis/log_predictions.py` first."); return {}
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
        recs, pending = _matured_records(preds, prices, bench, n)
        df = pd.DataFrame(recs)
        ic_raw, ic_exc = _daily_cross_sectional_ic(df)
        out[n] = {"matured": len(df), "pending": pending, "raw": _agg_daily(ic_raw), "excess": _agg_daily(ic_exc)}
        if verbose:
            print(f"\n  horizon {n}d: matured={len(df)} pending={pending}")
            print(f"    raw   IC: {out[n]['raw']}")
            print(f"    excess IC: {out[n]['excess']}")
    total_dates = len({r['ts'] for r in preds})
    if verbose and total_dates < 20:
        print(f"\n  [honest] {total_dates} prediction date(s) -> PRELIMINARY / not significant."
              f" Need ~20-50+ daily logs before the mean IC / IR means anything.")
    return out


def report():
    """WS1 D3: judged report. Writes ic_report.json (machine-readable -- WS5 sizing reads
    circuit_breaker from here) and ic_report.md (human-readable) side by side."""
    preds = _load_track()
    tickers = sorted({r["ticker"] for r in preds}) if preds else []
    prices = {t: _price(t) for t in tickers}
    bench = _price(BENCH)
    missing = [t for t in tickers if prices.get(t) is None]

    horizons_out = {}
    judge_weekly, judge_matured = [], 0
    for n in HORIZONS:
        recs, pending = _matured_records(preds, prices, bench, n)
        df = pd.DataFrame(recs)
        ic_raw, ic_exc = _daily_cross_sectional_ic(df)
        weekly_ticker = _weekly_cross_sectional_ic(df, min_names=WEEKLY_MIN_NAMES, name_col="ticker")

        theme_df = pd.DataFrame()
        if not df.empty:
            theme_df = (df.groupby(["ts", "week", "thesis_id"], as_index=False)
                          .agg(conf=("conf", "first"), fwd=("fwd", "mean"), excess=("excess", "mean")))
        weekly_theme = _weekly_cross_sectional_ic(theme_df, min_names=THEME_MIN_NAMES, name_col="thesis_id")

        horizons_out[n] = {
            "matured": len(df), "pending": pending,
            "raw_ic_daily": _agg_daily(ic_raw), "excess_ic_daily": _agg_daily(ic_exc),
            "weekly_ticker_ic": [{"week": w, "ic": round(v, 4)} for w, v in weekly_ticker],
            "weekly_ticker_rolling26": _rolling_stats(weekly_ticker),
            "weekly_theme_ic": [{"week": w, "ic": round(v, 4)} for w, v in weekly_theme],
            "weekly_theme_rolling26": _rolling_stats(weekly_theme),
        }
        if n == JUDGE_HORIZON:
            judge_weekly, judge_matured = weekly_ticker, len(df)

    status, circuit_breaker, rolling26 = judge(judge_weekly, judge_matured)

    dates = sorted({r["ts"] for r in preds}) if preds else []
    out = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "circuit_breaker": circuit_breaker,
        "judge_horizon_days": JUDGE_HORIZON,
        "judge_rolling_26w": rolling26,
        "thresholds": {
            "preliminary_matured_min": PRELIM_MATURED_MIN, "weekly_min_names": WEEKLY_MIN_NAMES,
            "pass_mean_min": PASS_MEAN_MIN, "pass_ir_min": PASS_IR_MIN,
            "fail_mean_max": FAIL_MEAN_MAX, "fail_matured_min": FAIL_MATURED_MIN,
        },
        "coverage": {
            "predictions": len(preds), "tickers": len(tickers),
            "dates": len(dates), "date_range": [dates[0], dates[-1]] if dates else None,
            "price_load_failed": missing,
        },
        "horizons": horizons_out,
    }

    json_path = os.path.join(ROOT, "ic_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    def fmt_daily(a):
        return f"{a['mean']}/{a['ir']}/{a['hit']}/{a['n_dates']}" if a else "-- (unmatured)"

    def fmt_roll(rr):
        return f"{rr['mean']}/{rr['ir']} ({rr['n_weeks']}w)" if rr["n_weeks"] else "-- (no valid week yet)"

    lines = [
        "# Phase-3 forward IC report (judged, WS1 D3)", "",
        f"**status: {status}**" + (" -- circuit_breaker: TRUE (satellite sizing halved)" if circuit_breaker else ""),
        "",
        f"predictions: {len(preds)} | tickers: {len(tickers)} | dates: {len(dates)} "
        f"({dates[0] if dates else '-'} .. {dates[-1] if dates else '-'}) | price-load failed: {missing}",
        "",
        f"Judge (primary): {JUDGE_HORIZON}d **excess** IC, ticker-level weekly cross-section "
        f"(>= {WEEKLY_MIN_NAMES} names/week), rolling {ROLLING_WEEKS}w. "
        f"PASS: mean >= {PASS_MEAN_MIN} and IR >= {PASS_IR_MIN}. "
        f"FAIL: mean <= {FAIL_MEAN_MAX} and matured >= {FAIL_MATURED_MIN} (-> circuit_breaker). "
        f"Below {PRELIM_MATURED_MIN} matured or 0 valid weeks -> PRELIMINARY, no verdict.",
        "",
        f"rolling {ROLLING_WEEKS}w ({JUDGE_HORIZON}d, ticker, excess): {fmt_roll(rolling26)}", "",
        "Secondary metrics (reported, NOT judged -- thin cross-sections / different horizons):", "",
        "| horizon | matured | pending | raw IC daily (mean/IR/hit/n) | excess IC daily (mean/IR/hit/n) | "
        "weekly ticker rolling26 (mean/IR, nweeks) | weekly theme rolling26 (mean/IR, nweeks, n=9 themes) |",
        "|---|---|---|---|---|---|---|",
    ]
    for n in HORIZONS:
        r = horizons_out[n]
        lines.append(f"| {n}d | {r['matured']} | {r['pending']} | {fmt_daily(r['raw_ic_daily'])} | "
                     f"{fmt_daily(r['excess_ic_daily'])} | {fmt_roll(r['weekly_ticker_rolling26'])} | "
                     f"{fmt_roll(r['weekly_theme_rolling26'])} |")
    lines += ["", "IC = cross-sectional Spearman(confidence, forward return). Excess = vs SPY, same-basis "
              "adjusted total return. Accumulates forward only; NOT backfillable (theses did not exist "
              "historically)."]
    md_path = os.path.join(ROOT, "ic_report.md")
    open(md_path, "w", encoding="utf-8").write("\n".join(lines))
    print(f"[forward_ic] status={status} circuit_breaker={circuit_breaker} -> wrote {json_path} and {md_path}")
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ic"
    if cmd == "ic":
        compute_ic()
    elif cmd == "report":
        report()
    else:
        print(__doc__)
