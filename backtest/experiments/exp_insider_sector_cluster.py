"""Insider SECTOR/THEME cluster probe — Phase-3 WS4 early-detection question (2026-07-08).

NOT a trading-signal backtest. Question: does insider open-market cluster-buying, when it fires
ACROSS >=2 different companies in the SAME theme/value-chain within a short window, work as an
early THEME-DISCOVERY flag (where to point qualitative research), ahead of when the narrative
becomes visible in this repo's own thesis corpus? Uses thesis/themes.yaml groupings (value-chain,
not GICS) + the SEC bulk Form 345 archive already cached 2006q1-2025q2 (backtest/.insider_data,
78 quarters, offline, no re-pull).

Definition grid (pre-registered): per company, a "company-cluster" = >=3 distinct insiders,
open-market P-buys only (10b5-1 excluded where flagged), summed value > $250k, within a window W.
A "theme-cluster fire" = >=2 different companies in the same theme.yaml bucket each have a
company-cluster with dates within W of each other. W in {21, 42} trading days (~1.4x calendar
days, matching exp_insider_validate's convention).

    python backtest/experiments/exp_insider_sector_cluster.py
"""
import os
import sys
import json

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp_insider_validate as IV  # noqa: E402

_MIN_INSIDERS = 3
_MIN_VALUE = 250_000
_MIN_COMPANIES = 2
_WINDOWS = [21, 42]
_GRID_MIN_INSIDERS = [2, 3]  # relaxation sweep — the pre-registered >=3 bar turned out near-empty (see results)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_THESIS_DIR = os.path.join(os.path.dirname(_THIS_DIR), "..", "thesis")
_THESIS_DIR = os.path.normpath(_THESIS_DIR)


def load_themes():
    p = os.path.join(_THESIS_DIR, "themes.yaml")
    y = yaml.safe_load(open(p, encoding="utf-8")) or {}
    themes = y.get("themes", {}) or {}
    out = {}
    for name, t in themes.items():
        tks = [x.upper() for x in (t.get("tickers") or [])]
        if len(tks) >= _MIN_COMPANIES:
            out[name] = tks
    return out


def build_company_clusters(day, min_insiders=_MIN_INSIDERS):
    """Per-ticker events where >=min_insiders distinct insiders filed open-market P-buys summing
    > _MIN_VALUE within each candidate day's trailing window (`day` = the day-level ticker/filed
    aggregate built once by main() and reused across grid combos)."""
    out = {}  # window -> list of dict(ticker, date, owners, value)
    for w in _WINDOWS:
        events = []
        for tk, g in day.groupby("ticker"):
            g = g.reset_index(drop=True)
            last = None
            for i in range(len(g)):
                win = g[(g["filed"] > g.loc[i, "filed"] - pd.Timedelta(days=w * 1.4)) &
                        (g["filed"] <= g.loc[i, "filed"])]
                owners = int(win["owners"].sum()); val = float(win["val"].sum())
                if owners >= min_insiders and val >= _MIN_VALUE:
                    d = g.loc[i, "filed"]
                    if last is None or (d - last).days > w:
                        events.append({"ticker": tk, "date": d, "owners": owners, "value": val})
                        last = d
        out[w] = pd.DataFrame(events)
        print(f"[sector-cluster] min_insiders={min_insiders} window={w}d: {len(out[w])} company-cluster "
              f"events ({out[w]['ticker'].nunique() if len(out[w]) else 0} tickers)")
    return out


def theme_fires(company_ev: pd.DataFrame, themes: dict, window: int):
    """A theme-cluster fire = >=2 distinct tickers in the same theme with a company-cluster event
    date within `window` (calendar-approx, same 1.4x convention) of each other. Report the EARLIEST
    date of each firing group (dedup overlapping fires within 2x window of a prior fire)."""
    tk2themes = {}
    for name, tks in themes.items():
        for tk in tks:
            tk2themes.setdefault(tk, []).append(name)
    fires = []
    for name, tks in themes.items():
        sub = company_ev[company_ev["ticker"].isin(tks)].sort_values("date")
        if sub.empty:
            continue
        sub = sub.reset_index(drop=True)
        last_fire = None
        for i in range(len(sub)):
            d0 = sub.loc[i, "date"]
            win = sub[(sub["date"] >= d0 - pd.Timedelta(days=window * 1.4)) & (sub["date"] <= d0)]
            n_co = win["ticker"].nunique()
            if n_co >= _MIN_COMPANIES:
                if last_fire is None or (d0 - last_fire).days > window * 2:
                    fires.append({"theme": name, "date": d0, "n_companies": n_co,
                                  "tickers": sorted(win["ticker"].unique().tolist())})
                    last_fire = d0
    return pd.DataFrame(fires)


def per_year_counts(fires: pd.DataFrame):
    if fires.empty:
        return pd.Series(dtype=int)
    yr = fires["date"].dt.year
    return yr.value_counts().sort_index()


def data_inventory():
    print("=== 1. DATA INVENTORY ===")
    cache_p = os.path.join(_THESIS_DIR, "insider_cache.json")
    cache = json.load(open(cache_p, encoding="utf-8"))
    print(f"thesis/insider_cache.json (EDGAR, current snapshot): {len(cache)} tickers, "
          f"asof={next(iter(cache.values()))['asof']}, 180d rolling window each (thesis/insider_edgar.py).")
    print("SEC bulk Form 345 archive (backtest/.insider_data): 78 quarterly zips, 2006q1-2025q2, "
          "already cached offline (verified by exp_insider_extended.py: 18,751 cluster events / "
          "6,766 tickers / 9,997 priced, 2006-2025). This probe reuses that archive with a STRICTER "
          "bar (>=3 insiders, >$250k, vs the validated >=2/$500k) and adds theme cross-company grouping.")
    print("No re-pull performed (per instructions); 2025q3+ not available (SEC bulk lags ~1-2 quarters).")


def main():
    data_inventory()
    themes = load_themes()
    print(f"\n=== 2. THEME UNIVERSE (thesis/themes.yaml, {len(themes)} themes with >=2 tickers) ===")
    for name, tks in themes.items():
        print(f"  {name}: {tks}")

    qtrs = IV._quarters("2016q1", "2025q2")  # 2016+: enough regime span, all bulk cached
    print(f"\n=== 3. LOAD raw Form-4 P-buys, {qtrs[0]}..{qtrs[-1]} ({len(qtrs)} quarters, cached) ===")
    raw = pd.concat([IV._load_quarter(q) for q in qtrs], ignore_index=True)
    day = (raw.groupby(["ticker", "filed"])
              .agg(val=("value", "sum"), owners=("RPTOWNERCIK", "nunique"))
              .reset_index().sort_values(["ticker", "filed"]))
    print(f"[sector-cluster] {len(day)} ticker-days with >=1 open-market P-buy filed, "
          f"{day['ticker'].nunique()} distinct tickers")

    print("\n=== 4. GRID: THEME-CLUSTER FIRES per (min_insiders x window), annual fire counts ===")
    all_fires = {}
    for mi in _GRID_MIN_INSIDERS:
        company_ev = build_company_clusters(day, min_insiders=mi)
        for w in _WINDOWS:
            fires = theme_fires(company_ev[w], themes, w)
            all_fires[(mi, w)] = fires
            print(f"\n--- min_insiders={mi}, window={w}d: {len(fires)} theme-cluster fires, "
                  f"{qtrs[0][:4]}-{qtrs[-1][:4]} ---")
            if fires.empty:
                print("  (none)")
                continue
            counts = per_year_counts(fires)
            full = counts.reindex(range(2016, 2026), fill_value=0)
            print("  fires/year:", dict(counts))
            print(f"  mean/yr = {full.mean():.2f}  (years with 0: {(full == 0).sum()}/10, "
                  f"years >6: {(full > 6).sum()}/10)")
            print("  detail:")
            for _, r in fires.sort_values("date").iterrows():
                print(f"    {r['date'].date()}  [{r['theme']}] {r['n_companies']} cos: {r['tickers']}")

    # save the most-relaxed grid point (min_insiders=2, window=42) for the case-study step
    best = all_fires.get((2, 42))
    out = {}
    for (mi, w), fires in all_fires.items():
        out[f"mi{mi}_w{w}"] = (fires.assign(date=fires["date"].astype(str)).to_dict("records")
                                if not fires.empty else [])
    json.dump(out, open(os.path.join(_THIS_DIR, "_sector_cluster_fires.json"), "w"), indent=1, default=str)
    print(f"\nSaved fire list (all grid points) -> {os.path.join(_THIS_DIR, '_sector_cluster_fires.json')}")


if __name__ == "__main__":
    main()
