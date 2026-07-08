"""thesis/beta_check.py — Phase-3 WS3 Sec3 beta-ification detection (lifecycle backlog #4,
docs/2026-07-08_phase3_ws3_lifecycle.md Sec3).

Pure DETECTION tool. For each ACTIVE theme in themes.yaml, builds an equal-weight daily-
rebalanced basket of its loadable tickers (backtest/data.py, adjusted=True total-return
closes), matches it against the closest sector-proxy ETF, and reports:
  - 126-trading-day rolling correlation (basket vs proxy ETF)
  - trailing-126d excess return (basket cum-return - proxy cum-return over the same window)
  - a BETA-ONLY warning flag when corr > 0.9 AND excess ~ 0 have both PERSISTED for the
    trailing ~6 months (not just the latest reading) -- spec Sec3 exit path #3.

This script does NOT delist anything. It only produces the report a session uses to decide.

Proxy ETF map (per the WS3/WS5 briefing):
  memory-supercycle, photonics-optical, advanced-packaging, tpu-custom-silicon,
  semicap-equipment -> SMH (semiconductor sector)
  ai-power-grid -> XLU (utilities; theme's own wiki note already uses XLU as the
      "defensive swap" comparison)
  oil-gas-energy -> XLE
  space-satellite -> SKIP (no clean sector proxy)
  rare-earth-materials -> SKIP (no clean sector proxy)

Run: python thesis/beta_check.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
THEMES_PATH = os.path.join(ROOT, "themes.yaml")
sys.path.insert(0, os.path.join(ROOT, ".."))
from backtest import data as data_mod  # noqa: E402

ROLL_WINDOW = 126          # ~6 trading months
CORR_FLAG_THRESHOLD = 0.90
EXCESS_FLAG_THRESHOLD = 0.05   # |excess| treated as "~0" below this, per tail window
MIN_ROWS = 60

PROXY_MAP = {
    "memory-supercycle": "SMH",
    "photonics-optical": "SMH",
    "advanced-packaging": "SMH",
    "tpu-custom-silicon": "SMH",
    "semicap-equipment": "SMH",
    "ai-power-grid": "XLU",
    "oil-gas-energy": "XLE",
    "space-satellite": None,        # no clean proxy -> skip
    "rare-earth-materials": None,   # no clean proxy -> skip
}


def load_themes():
    with open(THEMES_PATH, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data.get("themes", {}) or {}


def load_close(symbol, min_rows=MIN_ROWS):
    df = data_mod.load(symbol, adjusted=True, min_rows=min_rows)
    return df["close"]


def build_basket(tickers):
    """Equal-weight, daily-rebalanced basket return series from whichever tickers load.
    Returns (basket_returns: pd.Series, loaded: list[str], failed: list[str])."""
    closes = {}
    failed = []
    for tk in tickers:
        try:
            closes[tk] = load_close(tk)
        except Exception:
            failed.append(tk)
    if not closes:
        return None, [], failed
    prices = pd.concat(closes, axis=1, sort=True).sort_index()
    # require at least 2 names' worth of overlap where possible; forward-fill short gaps,
    # then drop any remaining fully-empty rows.
    prices = prices.ffill()
    prices = prices.dropna(how="all")
    returns = prices.pct_change()
    # equal-weight daily rebalance: average of whichever names have a return that day
    basket_ret = returns.mean(axis=1, skipna=True).dropna()
    return basket_ret, list(closes.keys()), failed


def rolling_corr_and_excess(basket_ret, proxy_ret, window=ROLL_WINDOW):
    joined = pd.concat({"basket": basket_ret, "proxy": proxy_ret}, axis=1).dropna()
    if len(joined) < window + 1:
        return None, None, joined
    corr = joined["basket"].rolling(window).corr(joined["proxy"]).dropna()
    basket_cum = (1 + joined["basket"]).rolling(window).apply(lambda s: s.prod() - 1, raw=True)
    proxy_cum = (1 + joined["proxy"]).rolling(window).apply(lambda s: s.prod() - 1, raw=True)
    excess = (basket_cum - proxy_cum).dropna()
    return corr, excess, joined


def evaluate_theme(slug, tickers, proxy):
    if proxy is None:
        return {"slug": slug, "skipped": True, "reason": "no clean sector proxy (per briefing)"}

    basket_ret, loaded, failed = build_basket(tickers)
    if basket_ret is None or len(basket_ret) < MIN_ROWS:
        return {"slug": slug, "skipped": True,
                "reason": f"no usable basket data (loaded={loaded}, failed={failed})"}

    try:
        proxy_ret = load_close(proxy).pct_change().dropna()
    except Exception as e:
        return {"slug": slug, "skipped": True, "reason": f"proxy {proxy} load failed: {e}"}

    corr, excess, joined = rolling_corr_and_excess(basket_ret, proxy_ret)
    if corr is None or len(corr) == 0:
        return {"slug": slug, "skipped": True,
                "reason": f"insufficient overlapping history for a {ROLL_WINDOW}d rolling window "
                          f"(overlap={len(joined)}d)"}

    latest_corr = corr.iloc[-1]
    latest_excess = excess.iloc[-1] if len(excess) else None

    # "persisted for the trailing 6 months": look at the tail of the rolling-corr /
    # rolling-excess series itself (each already a 126d-window statistic) over the last
    # ROLL_WINDOW available readings.
    corr_tail = corr.tail(ROLL_WINDOW)
    excess_tail = excess.tail(ROLL_WINDOW) if len(excess) else pd.Series(dtype=float)
    persistent_high_corr = len(corr_tail) >= max(20, ROLL_WINDOW // 3) and corr_tail.min() > CORR_FLAG_THRESHOLD
    persistent_zero_excess = (len(excess_tail) >= max(20, ROLL_WINDOW // 3)
                               and excess_tail.abs().max() < EXCESS_FLAG_THRESHOLD)
    flag = persistent_high_corr and persistent_zero_excess

    return {
        "slug": slug,
        "skipped": False,
        "proxy": proxy,
        "tickers_loaded": loaded,
        "tickers_failed": failed,
        "latest_corr": latest_corr,
        "latest_excess": latest_excess,
        "corr_tail_min": corr_tail.min() if len(corr_tail) else None,
        "excess_tail_absmax": excess_tail.abs().max() if len(excess_tail) else None,
        "n_days_overlap": len(joined),
        "flag": flag,
    }


def run():
    themes = load_themes()
    active = {slug: t for slug, t in themes.items() if t.get("status", "active") == "active"}

    print("\n=== thesis beta-ification check (WS3 Sec3) ===")
    print(f"rolling window: {ROLL_WINDOW}d (~6 trading months); "
          f"flag = corr > {CORR_FLAG_THRESHOLD:.2f} AND |excess| < {EXCESS_FLAG_THRESHOLD:.2f}, "
          f"BOTH persisted across the last {ROLL_WINDOW}d of rolling readings.\n")

    header = (f"{'theme':<24}{'proxy':>7}{'corr(latest)':>14}{'excess(latest)':>16}"
              f"{'corr_tail_min':>15}{'excess_tail_max':>17}   flag")
    print(header)
    print("-" * len(header))

    results = []
    for slug, t in sorted(active.items()):
        proxy = PROXY_MAP.get(slug, "UNMAPPED")
        r = evaluate_theme(slug, t.get("tickers") or [], proxy if proxy != "UNMAPPED" else None)
        results.append(r)
        if r.get("skipped"):
            print(f"{slug:<24}{'--':>7}{'--':>14}{'--':>16}{'--':>15}{'--':>17}   SKIP ({r['reason']})")
        else:
            flag_str = "*** BETA-ONLY WARNING ***" if r["flag"] else "ok"
            print(f"{slug:<24}{r['proxy']:>7}{r['latest_corr']:>14.3f}{r['latest_excess']:>16.3%}"
                  f"{r['corr_tail_min']:>15.3f}{r['excess_tail_absmax']:>17.3%}   {flag_str}")

    print()
    flagged = [r["slug"] for r in results if not r.get("skipped") and r["flag"]]
    skipped = [(r["slug"], r["reason"]) for r in results if r.get("skipped")]

    if flagged:
        print(f"BETA-ONLY warning on: {', '.join(flagged)} "
              "-> route to session review for delisting per WS3 Sec3 (this script does not delist).")
    else:
        print("no theme currently flags BETA-ONLY.")

    if skipped:
        print("\nskipped (no clean proxy or insufficient data):")
        for slug, reason in skipped:
            print(f"  {slug}: {reason}")

    print()


if __name__ == "__main__":
    run()
