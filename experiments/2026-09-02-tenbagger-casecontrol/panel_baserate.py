# -*- coding: utf-8 -*-
"""Base rate of 10x outcomes inside the in-repo 657-member monthly panel.

Purpose: put a prior under the thesis line. If you pick a name at random from
this universe at the end of year Y and hold, how often does it 10x within the
next N years?

Two things make this an UPPER BOUND, not a fair estimate:
  1. The panel holds today's sector-ETF constituents. Companies that were
     delisted, went bankrupt or were acquired at a loss between Y and today are
     simply not in it. That is exactly the survivorship the ticket warns about.
  2. Prices are ETF-membership-conditioned - a name only appears because it made
     it into an XL* sector ETF.

So the true base rate for a name pickable at time Y is LOWER than what prints
here. Read the number as "even under favourable accounting, this rare".

Run:  PYTHONUTF8=1 python panel_baserate.py
"""
import json
import pathlib

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
PANEL = pathlib.Path(
    r"C:\projects\Karst\experiments\2026-09-01-stock-oracle-curve\data\stock_monthly.parquet")

HORIZONS = [3, 5, 10]
THRESHOLDS = [2, 3, 5, 10]


def main():
    d = pd.read_parquet(PANEL)
    d["month_end"] = pd.to_datetime(d["month_end"])
    px = d.pivot_table(index="month_end", columns="symbol", values="close")
    sector = d.groupby("symbol")["etf"].last()

    rows = []
    for year in range(2011, 2024):
        anchor = pd.Timestamp(f"{year}-12-31")
        hist = px[px.index <= anchor]
        if hist.empty:
            continue
        base = hist.iloc[-1].dropna()
        for h in HORIZONS:
            end = anchor + pd.DateOffset(years=h)
            if end > px.index.max():
                continue
            fwd = px[(px.index > anchor) & (px.index <= end)]
            peak = fwd[base.index].max()
            mult = (peak / base).dropna()
            if mult.empty:
                continue
            rec = dict(base_year=year, horizon_years=h, n_names=int(len(mult)),
                       median_peak_multiple=round(float(mult.median()), 2))
            for th in THRESHOLDS:
                rec[f"share_ge_{th}x"] = round(float((mult >= th).mean()), 4)
                rec[f"n_ge_{th}x"] = int((mult >= th).sum())
            rows.append(rec)
    br = pd.DataFrame(rows)
    br.to_csv(OUT / "panel_baserate.csv", index=False, encoding="utf-8")

    # which sectors produced the 10x names, 10y horizon
    sect_rows = []
    for year in range(2011, 2017):
        anchor = pd.Timestamp(f"{year}-12-31")
        hist = px[px.index <= anchor]
        base = hist.iloc[-1].dropna()
        end = anchor + pd.DateOffset(years=10)
        if end > px.index.max():
            continue
        fwd = px[(px.index > anchor) & (px.index <= end)]
        mult = (fwd[base.index].max() / base).dropna()
        hits = mult[mult >= 10]
        for sym, m in hits.items():
            sect_rows.append(dict(base_year=year, symbol=sym,
                                  sector=sector.get(sym), peak_multiple_10y=round(float(m), 2)))
    sd = pd.DataFrame(sect_rows)
    sd.to_csv(OUT / "panel_10x_names.csv", index=False, encoding="utf-8")

    print("=== base rate of reaching a peak multiple, in-panel (survivor-biased UPPER bound) ===")
    print(br[["base_year", "horizon_years", "n_names", "median_peak_multiple",
              "share_ge_2x", "share_ge_5x", "share_ge_10x", "n_ge_10x"]].to_string(index=False))
    if not sd.empty:
        print("\n=== 10y 10x names by sector (base years 2011-2015) ===")
        print(sd.groupby(["base_year", "sector"]).size().to_string())
        print("\ntotal 10x hits listed:", len(sd), "unique names:", sd.symbol.nunique())
    summary = dict(
        panel_names=int(px.shape[1]),
        panel_first=str(px.index.min().date()), panel_last=str(px.index.max().date()),
        share_ge_10x_10y_2011=float(br[(br.base_year == 2011) & (br.horizon_years == 10)]["share_ge_10x"].iloc[0])
        if not br[(br.base_year == 2011) & (br.horizon_years == 10)].empty else None,
    )
    (OUT / "panel_baserate_summary.json").write_text(json.dumps(summary, indent=1))
    print("\n", json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
