"""thesis/theme_signal.py — daily theme ENTRY signal (NHITL decision support, satellite sleeve).

Complements thesis/sizing.py ("how much") with "WHEN": for every active theme, is now a
buy-zone or should we wait for valuation to deflate? Design principle (docs/2026-07-08_
phase3_ws5_expression.md Sec0 entry discipline): NOT TA timing -- fundamental cycle_stage
(from themes.yaml, human/agent-assessed via the thinking loop) + a quantified valuation gate
(ttm_pe percentile vs the ticker's OWN history) + a plain trend/froth read (200SMA, 52w range)
as context. Pure DISPLAY: reads themes.yaml + prices/fundamentals, writes nothing.

Per-ticker metrics (skip a ticker gracefully -- NO price / NO ttm_pe -- rather than crash):
  - pe_pctile   : percentile rank of the ticker's LATEST POSITIVE ttm_pe within its own trailing
                  history (window = min(252, available) valid ttm_pe observations). High =
                  froth/priced-in vs itself; low = deflated. None if no fundamentals ever
                  (defeatbeta miss). ALWAYS printed for transparency, but if the latest positive
                  read is stale (> PE_STALE_DAYS old -- i.e. the name has since gone loss-making,
                  e.g. AXTI/AEHR) it is a peak-earnings ARTIFACT, flagged "[STALE ...]" and
                  EXCLUDED from verdict logic (pe_pctile_verdict = None instead) so an old
                  artifact-cheap or artifact-expensive read cannot drive a false BUY/ACCUMULATE
                  or KILL-WATCH.
  - vs_200sma   : adjusted close vs 200d SMA, %. None if <200 rows.
  - w52_pos     : position in the trailing 252d adjusted-close range, 0=52w low, 100=52w high.

Theme-level = the same three reads on an equal-weight basket of the theme's tickers that loaded
(price basket: rebase each name to 100 at the earliest common date, average) + pe_pctile = median
of per-ticker pe_pctile_verdict (stale reads excluded; only names with a current value), so the
printed theme-level pe_pctile and the VERDICT next to it are always mutually consistent.

VERDICT (rule-based, in priority order):
  1. NO-DATA          -- no ticker in the theme produced BOTH a price series and *any* signal.
  2. KILL-WATCH        -- basket trend broke below its 200SMA (down-cross) OR pe_pctile >= 90
                          (valuation extreme). "(見 note, kill_condition 人工判斷最終)".
  3. BUY-ZONE           -- cycle_stage == early AND (pe_pctile is None OR pe_pctile < 50) AND
                          trend up (vs_200sma > 0).
  4. WAIT               -- cycle_stage in {mid, late, event-driven} AND pe_pctile is not None AND
                          pe_pctile > 70.  ("don't chase; wait for valuation to deflate")
  5. ACCUMULATE         -- cycle_stage in {mid, late, event-driven} AND pe_pctile is not None AND
                          pe_pctile < 50 AND trend up.  (can size in, staged, per sizing.py caps)
  6. WAIT (fallback)     -- anything else with data (e.g. pe_pctile 50-70 "no man's land", or
                          pe_pctile unknown but not early-cycle) -- default to caution, matches the
                          thesis discipline "don't chase" when the signal isn't clearly a buy.

TARGET (added on top of the verdict -- "when" does WAIT flip, honestly split into two kinds so
neither pretends to be more precise than it is):
  - HARD (technical, closed-form $ or index level): the theme's basket 200SMA. If the theme has
    exactly ONE ticker with usable price data, this is that ticker's REAL $ price and $ 200SMA
    (exact). If the theme has MULTIPLE tickers, the "basket" is a rebase-to-100 equal-weight NAV
    (no single $ price exists for a multi-name basket) -- printed as an index level, explicitly
    labeled NAV so it is never mistaken for a tradeable quote. Either way the actionable number is
    the same: % distance to the 200SMA (pullback-to-accumulate target) / whether it has already
    closed below (kill-watch trend condition already live).
  - SOFT (fundamental, EPS-flat estimate, NOT a price target): current median ttm_pe percentile
    vs the ACCUMULATE gate (<50th). Where possible also prints an estimated avg "derate %" --
    the price decline that would bring each covered name's ttm_pe down to its OWN trailing-window
    MEDIAN pe (i.e. cross the 50th pctile), assuming trailing EPS stays flat. This is a rough
    estimate (real re-rating involves EPS changes too), always labeled SOFT.
  - Themes with no usable price/valuation data at all get "target=qualitative, monitor via
    news/constraint-language" instead of fabricating a number.

Run: python thesis/theme_signal.py   (PYTHONUTF8=1 recommended; prints ASCII+CJK, safe for
     redirection into playbook_log.txt via daily_playbook.cmd).
"""
from __future__ import annotations

import contextlib
import io
import os
import sys

import numpy as np
import pandas as pd
import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "..", "backtest"))
THEMES_PATH = os.path.join(ROOT, "themes.yaml")

PE_WINDOW = 252          # trailing valid ttm_pe observations for the own-history percentile
SMA_WINDOW = 200
W52_WINDOW = 252
KILL_PE_PCTILE = 90.0
WAIT_PE_PCTILE = 70.0
ACCUM_PE_PCTILE = 50.0
EARLY_CYCLE = {"early"}
LATE_CYCLE = {"mid", "late", "event-driven"}
PE_STALE_DAYS = 200      # last POSITIVE ttm_pe older than this = earnings likely negative NOW
                         # (loss-making) -> pctile is a peak-earnings artifact, not a current
                         # valuation read. Excluded from verdict logic (still shown, flagged).


def load_themes():
    with open(THEMES_PATH, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data.get("themes", {}) or {}


# ---------- per-ticker data ----------

def _price_adj(sym):
    """Adjusted total-return close series (yfinance-first, backtest/data.py). None on failure."""
    try:
        from data import load
        df = load(sym, adjusted=True, min_rows=20)
        s = df["close"].astype("float64").copy()
        s.index = pd.to_datetime(df.index)
        return s.sort_index()
    except Exception:
        return None


def _ttm_pe_series(sym):
    """Own-history ttm_pe series (defeatbeta), positive values only. None on failure/no coverage."""
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            from defeatbeta_api.data.ticker import Ticker
            df = Ticker(sym).ttm_pe()
        if df is None or len(df) == 0:
            return None
        df = df[["report_date", "ttm_pe"]].copy()
        df["date"] = pd.to_datetime(df["report_date"])
        df = df.set_index("date").sort_index()
        pe = df["ttm_pe"].astype("float64")
        pe = pe.where(pe > 0)   # negative/zero PE = no earnings, not "cheap"
        pe = pe.dropna()
        return pe if len(pe) else None
    except Exception:
        return None


def ticker_metrics(sym):
    """Return dict of per-ticker signal reads; fields are None where unavailable. Never raises.

    pe_pctile        : display value (own-history percentile of the latest POSITIVE ttm_pe read,
                        however old that read is).
    pe_pctile_verdict: same value but None if the read is stale (pe_stale_days > PE_STALE_DAYS)
                        -- what verdict logic consumes, so a loss-making name's old artifact PE
                        cannot masquerade as "currently cheap" (BUY/ACCUMULATE) or "currently
                        extreme" (KILL-WATCH).
    """
    out = {"symbol": sym, "price": None, "pe_pctile": None, "pe_pctile_verdict": None,
           "vs_200sma": None, "w52_pos": None, "last_pe": None, "last_close": None,
           "pe_stale_days": None, "sma200_price": None, "pe_window_median": None,
           "pe_derate_pct": None}
    try:
        px = _price_adj(sym)
        if px is not None and len(px) > 0:
            out["price"] = px
            out["last_close"] = float(px.iloc[-1])
            if len(px) >= SMA_WINDOW:
                sma200 = px.rolling(SMA_WINDOW).mean().iloc[-1]
                if sma200 and not np.isnan(sma200) and sma200 > 0:
                    out["sma200_price"] = float(sma200)
                    out["vs_200sma"] = float((px.iloc[-1] / sma200 - 1.0) * 100.0)
            w52 = px.tail(W52_WINDOW)
            if len(w52) >= 20:
                lo, hi = float(w52.min()), float(w52.max())
                if hi > lo:
                    out["w52_pos"] = float((px.iloc[-1] - lo) / (hi - lo) * 100.0)
    except Exception:
        pass
    try:
        pe = _ttm_pe_series(sym)
        if pe is not None and len(pe) > 0:
            window = pe.tail(PE_WINDOW)
            last = float(window.iloc[-1])
            out["last_pe"] = last
            out["pe_pctile"] = float((window <= last).mean() * 100.0)
            # Flag stale reads (e.g. AXTI/AEHR: last POSITIVE ttm_pe predates the name going
            # loss-making -- a peak-earnings artifact, not a current "cheap" signal).
            last_pe_date = pe.index[-1]
            ref_date = out["price"].index[-1] if out["price"] is not None and len(out["price"]) else pd.Timestamp.today()
            out["pe_stale_days"] = int((pd.Timestamp(ref_date) - pd.Timestamp(last_pe_date)).days)
            if out["pe_stale_days"] <= PE_STALE_DAYS:
                out["pe_pctile_verdict"] = out["pe_pctile"]
                # SOFT target: est. price derate to bring ttm_pe down to this name's OWN
                # trailing-window MEDIAN (i.e. cross the 50th pctile), holding EPS flat.
                med_pe = float(window.median())
                out["pe_window_median"] = med_pe
                if last > med_pe > 0:
                    out["pe_derate_pct"] = float((1.0 - med_pe / last) * 100.0)
                else:
                    out["pe_derate_pct"] = 0.0   # already at/below own median PE
    except Exception:
        pass
    return out


# ---------- theme-level aggregation ----------

def basket_reads(ticker_rows):
    """Equal-weight basket trend/froth from per-ticker price series.

    If exactly ONE ticker has price data, the "basket" IS that ticker -- real $ price/SMA,
    exact (is_single=True). If MULTIPLE tickers, rebase each to 100 at their common start date
    and average -- a synthetic NAV index (is_single=False, no real per-share $ exists for a
    multi-name basket) -- vs_200sma/w52_pos are still exact %, just not a $ quote.

    Returns a dict: vs_200sma, w52_pos, is_single, symbol (if single), level (current, $ if
    single else NAV idx), sma200_level (same units), or all-None fields if no basket at all.
    """
    empty = {"vs_200sma": None, "w52_pos": None, "is_single": False, "symbol": None,
             "level": None, "sma200_level": None}
    series = {r["symbol"]: r["price"] for r in ticker_rows if r["price"] is not None and len(r["price"]) > 0}
    if not series:
        return dict(empty)
    if len(series) == 1:
        sym, s = next(iter(series.items()))
        out = dict(empty)
        out["is_single"], out["symbol"] = True, sym
        out["level"] = float(s.iloc[-1])
        if len(s) >= SMA_WINDOW:
            sma200 = s.rolling(SMA_WINDOW).mean().iloc[-1]
            if sma200 and sma200 > 0:
                out["sma200_level"] = float(sma200)
                out["vs_200sma"] = float((s.iloc[-1] / sma200 - 1.0) * 100.0)
        tail = s.tail(W52_WINDOW)
        if len(tail) >= 20:
            lo, hi = float(tail.min()), float(tail.max())
            if hi > lo:
                out["w52_pos"] = float((s.iloc[-1] - lo) / (hi - lo) * 100.0)
        return out

    common_start = max(s.index.min() for s in series.values())
    rebased = []
    for s in series.values():
        s2 = s[s.index >= common_start]
        if len(s2) == 0 or s2.iloc[0] <= 0:
            continue
        rebased.append(s2 / s2.iloc[0] * 100.0)
    if not rebased:
        return dict(empty)
    basket = pd.concat(rebased, axis=1).ffill().mean(axis=1).dropna()
    out = dict(empty)
    out["is_single"] = False
    out["level"] = float(basket.iloc[-1])
    if len(basket) >= SMA_WINDOW:
        sma200 = basket.rolling(SMA_WINDOW).mean().iloc[-1]
        if sma200 and sma200 > 0:
            out["sma200_level"] = float(sma200)
            out["vs_200sma"] = float((basket.iloc[-1] / sma200 - 1.0) * 100.0)
    tail = basket.tail(W52_WINDOW)
    if len(tail) >= 20:
        lo, hi = float(tail.min()), float(tail.max())
        if hi > lo:
            out["w52_pos"] = float((basket.iloc[-1] - lo) / (hi - lo) * 100.0)
    return out


def theme_pe_pctile(ticker_rows):
    """Median pe_pctile driving BOTH the summary-table display and the VERDICT (excludes
    stale/artifact reads, see PE_STALE_DAYS, so the printed number and verdict never disagree)."""
    vals = [r["pe_pctile_verdict"] for r in ticker_rows if r["pe_pctile_verdict"] is not None]
    if not vals:
        return None
    return float(np.median(vals))


def verdict(cycle_stage, pe_pctile, vs_200sma, has_any_data):
    if not has_any_data:
        return "NO-DATA"
    trend_down = vs_200sma is not None and vs_200sma < 0
    pe_extreme = pe_pctile is not None and pe_pctile >= KILL_PE_PCTILE
    if trend_down or pe_extreme:
        return "KILL-WATCH"
    trend_up = vs_200sma is not None and vs_200sma > 0
    if cycle_stage in EARLY_CYCLE and (pe_pctile is None or pe_pctile < ACCUM_PE_PCTILE) and trend_up:
        return "BUY-ZONE"
    if cycle_stage in LATE_CYCLE and pe_pctile is not None and pe_pctile > WAIT_PE_PCTILE:
        return "WAIT"
    if cycle_stage in LATE_CYCLE and pe_pctile is not None and pe_pctile < ACCUM_PE_PCTILE and trend_up:
        return "ACCUMULATE"
    return "WAIT"


def ticker_verdict(cycle_stage, row):
    has_data = row["price"] is not None or row["pe_pctile"] is not None
    return verdict(cycle_stage, row["pe_pctile_verdict"], row["vs_200sma"], has_data)


# ---------- TARGET (hard price/index level + soft valuation threshold) ----------

def hard_target(basket):
    """HARD (technical, closed-form): 200SMA level + % distance. Real $ if is_single, else a
    labeled NAV index. None fields -> not enough price history to compute."""
    if basket["vs_200sma"] is None or basket["sma200_level"] is None:
        return "HARD: n/a (insufficient basket price history for a 200SMA read)"
    unit = f"${basket['symbol']}" if basket["is_single"] else "NAV-idx(base100)"
    cur, sma = basket["level"], basket["sma200_level"]
    dist = basket["vs_200sma"]
    cur_s = f"${cur:.2f}" if basket["is_single"] else f"{cur:.1f}"
    sma_s = f"${sma:.2f}" if basket["is_single"] else f"{sma:.1f}"
    if dist < 0:
        return (f"HARD [{unit}]: 200SMA={sma_s}, now={cur_s} ({dist:+.1f}%) -- "
                f"ALREADY BELOW 200SMA, kill-watch trend condition live")
    return (f"HARD [{unit}]: 200SMA={sma_s}, now={cur_s} ({dist:+.1f}% above) -- "
            f"needs ~{dist:.1f}% pullback to reach 200SMA (accumulate-on-pullback level); "
            f"kill-watch triggers if it closes below {sma_s}")


def soft_target(pe_med, ticker_rows):
    """SOFT (fundamental, EPS-flat estimate, NOT a price target): pctile vs the ACCUMULATE
    gate (<50th) + an approx avg derate% across covered names (assumes trailing EPS unchanged)."""
    if pe_med is None:
        return "SOFT: n/a (no current ttm_pe signal -- loss-making/no-fundamentals/stale)"
    if pe_med < ACCUM_PE_PCTILE:
        return (f"SOFT (valuation, EPS-flat est.): median ttm_pe pctile {pe_med:.0f}th -- "
                f"already < {ACCUM_PE_PCTILE:.0f}th, valuation gate OPEN (verdict then hinges on trend/cycle)")
    derates = [r["pe_derate_pct"] for r in ticker_rows
               if r["pe_pctile_verdict"] is not None and r["pe_derate_pct"] is not None]
    if derates:
        avg_derate = float(np.mean(derates))
        return (f"SOFT (valuation, EPS-flat est. -- NOT a price target): median ttm_pe pctile "
                f"{pe_med:.0f}th, needs < {ACCUM_PE_PCTILE:.0f}th for ACCUMULATE; est. avg derate "
                f"needed across covered names ~{avg_derate:.0f}% (crude: assumes EPS flat)")
    return (f"SOFT (valuation): median ttm_pe pctile {pe_med:.0f}th, needs < "
            f"{ACCUM_PE_PCTILE:.0f}th for ACCUMULATE (derate% not estimable)")


def theme_target_line(pe_med, basket, ticker_rows):
    if basket["vs_200sma"] is None and pe_med is None:
        return "TARGET: qualitative only (no tradeable price/valuation data) -- monitor via news/constraint-language"
    return f"TARGET: {hard_target(basket)} | {soft_target(pe_med, ticker_rows)}"


# ---------- run ----------

def run():
    themes = load_themes()
    active = {slug: t for slug, t in themes.items() if t.get("status", "active") == "active"}

    print("\n=== thesis theme_signal (daily entry read, satellite sleeve) ===")
    print("NOT TA timing: cycle_stage (thesis) + ttm_pe percentile vs OWN history (priced-in gate) "
          "+ 200SMA/52w context. Don't chase late-cycle froth; wait for deflate or accumulate small.\n")

    theme_summ = []
    theme_ticker_rows = {}

    for slug, t in sorted(active.items()):
        cycle = t.get("cycle_stage", "mid")
        tickers = t.get("tickers") or []
        rows = []
        for sym in tickers:
            try:
                rows.append(ticker_metrics(sym))
            except Exception as e:
                rows.append({"symbol": sym, "price": None, "pe_pctile": None,
                             "pe_pctile_verdict": None, "vs_200sma": None, "w52_pos": None,
                             "last_pe": None, "last_close": None, "pe_stale_days": None,
                             "sma200_price": None, "pe_window_median": None,
                             "pe_derate_pct": None, "error": str(e)[:80]})
        theme_ticker_rows[slug] = rows

        pe_med = theme_pe_pctile(rows)
        basket = basket_reads(rows)
        has_any = any(r["price"] is not None or r["pe_pctile"] is not None for r in rows)
        v = verdict(cycle, pe_med, basket["vs_200sma"], has_any)
        theme_summ.append({
            "slug": slug, "cycle": cycle, "pe_med": pe_med,
            "vs_200sma": basket["vs_200sma"], "w52_pos": basket["w52_pos"], "verdict": v,
            "target": theme_target_line(pe_med, basket, rows),
        })

    header = f"{'theme':<22}{'cycle':<14}{'pe_pctile':>10}{'vs200sma':>10}{'52w_pos':>9}  {'verdict'}"
    print(header)
    print("-" * len(header))
    for r in theme_summ:
        pe_s = f"{r['pe_med']:.0f}" if r["pe_med"] is not None else "n/a"
        sma_s = f"{r['vs_200sma']:+.1f}%" if r["vs_200sma"] is not None else "n/a"
        w52_s = f"{r['w52_pos']:.0f}" if r["w52_pos"] is not None else "n/a"
        print(f"{r['slug']:<22}{r['cycle']:<14}{pe_s:>10}{sma_s:>10}{w52_s:>9}  {r['verdict']}")

    buy_zone = [r["slug"] for r in theme_summ if r["verdict"] == "BUY-ZONE"]
    accumulate = [r["slug"] for r in theme_summ if r["verdict"] == "ACCUMULATE"]
    kill_watch = [r["slug"] for r in theme_summ if r["verdict"] == "KILL-WATCH"]
    print(f"\nBUY-ZONE: {', '.join(buy_zone) if buy_zone else '(none)'}")
    print(f"ACCUMULATE: {', '.join(accumulate) if accumulate else '(none)'}")
    print(f"KILL-WATCH: {', '.join(kill_watch) if kill_watch else '(none)'}")

    print("\n=== targets (when WAIT flips -- HARD=technical closed-form, SOFT=fundamental estimate) ===")
    for r in theme_summ:
        print(f"\n{r['slug']} ({r['verdict']}):")
        print(f"  {r['target']}")

    print("\n=== per-ticker detail ===")
    for slug, t in sorted(active.items()):
        cycle = t.get("cycle_stage", "mid")
        kill_txt = (t.get("kill_condition") or "").strip().replace("\n", " ")
        if len(kill_txt) > 160:
            kill_txt = kill_txt[:157] + "..."
        print(f"\n-- {slug} (cycle={cycle}) --")
        print(f"   kill_condition (人工判): {kill_txt}")
        rows = theme_ticker_rows.get(slug, [])
        thead = (f"   {'ticker':<8}{'pe_pctile':>10}{'last_pe':>9}{'vs200sma':>10}{'52w_pos':>9}"
                 f"{'200sma$':>10}{'derate%':>9}  {'verdict'}")
        print(thead)
        for row in rows:
            if row.get("error") and row["price"] is None and row["pe_pctile"] is None:
                print(f"   {row['symbol']:<8}  SKIP (no data: {row['error']})")
                continue
            if row["price"] is None and row["pe_pctile"] is None:
                print(f"   {row['symbol']:<8}  SKIP (no price/no ttm_pe)")
                continue
            pe_s = f"{row['pe_pctile']:.0f}" if row["pe_pctile"] is not None else "n/a"
            lpe_s = f"{row['last_pe']:.1f}" if row["last_pe"] is not None else "n/a"
            sma_s = f"{row['vs_200sma']:+.1f}%" if row["vs_200sma"] is not None else "n/a"
            w52_s = f"{row['w52_pos']:.0f}" if row["w52_pos"] is not None else "n/a"
            sma200_s = f"${row['sma200_price']:.2f}" if row["sma200_price"] is not None else "n/a"
            derate_s = ("n/a" if row["pe_derate_pct"] is None or row["pe_pctile_verdict"] is None
                        else f"{row['pe_derate_pct']:.0f}")
            tv = ticker_verdict(cycle, row)
            stale = ""
            if row.get("pe_stale_days") is not None and row["pe_stale_days"] > PE_STALE_DAYS:
                stale = f"  [STALE ttm_pe: no positive-earnings read in {row['pe_stale_days']}d " \
                        f"-- likely loss-making now, pctile is a peak-earnings artifact, not current]"
            print(f"   {row['symbol']:<8}{pe_s:>10}{lpe_s:>9}{sma_s:>10}{w52_s:>9}"
                  f"{sma200_s:>10}{derate_s:>9}  {tv}{stale}")
    print()


if __name__ == "__main__":
    run()
