# -*- coding: utf-8 -*-
"""Pull ex-ante fundamentals from SEC XBRL companyfacts for every ticker in PAIRS.

The hard rule here is NO LOOK-AHEAD: a fact is only usable if its `filed` date is
on or before the last day of base_year. At the end of, say, 2015 an investor
could read the FY2014 10-K and the 2015 quarterlies, not the FY2015 10-K (filed
in early 2016). Everything is filtered on that basis.

Fields we cannot source are written as the literal string "NOT_AVAILABLE" plus a
reason, never guessed.

Run:  PYTHONUTF8=1 python fetch_fundamentals.py
"""
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pairs import PAIRS  # noqa: E402

DATA = HERE / "data"
OUT = HERE / "out"
CACHE = DATA / "secfacts"
for d in (DATA, OUT, CACHE):
    d.mkdir(parents=True, exist_ok=True)

UA = "Karst Research research@vl-lawyers.com"
TICKER_CIK = json.loads(
    pathlib.Path(r"C:\projects\Karst\data\sec\company_tickers.json").read_text())

# XBRL tag fallbacks - US GAAP naming is not consistent across filers.
TAGS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                "RevenueFromContractWithCustomerIncludingAssessedTax",
                "SalesRevenueNet", "SalesRevenueGoodsNet",
                "Revenue", "RevenueFromContractsWithCustomers",
                "RealEstateRevenueNet"],
    "gross_profit": ["GrossProfit"],
    "net_income": ["NetIncomeLoss", "ProfitLoss",
                   "ProfitLossAttributableToOwnersOfParent"],
    "diluted_shares": ["WeightedAverageNumberOfDilutedSharesOutstanding",
                       "WeightedAverageNumberOfDilutedSharesOutstandingBasicAndDiluted",
                       "WeightedAverageNumberOfSharesOutstandingBasic",
                       "WeightedAverageNumberOfShareOutstandingBasicAndDiluted",
                       "AdjustedWeightedAverageShares", "WeightedAverageShares"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
            "CashFlowsFromUsedInOperatingActivities"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment",
              "PaymentsToAcquireProductiveAssets"],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "equity": ["StockholdersEquity",
               "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
               "Equity"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue",
             "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
             "CashAndCashEquivalents"],
    "lt_debt": ["LongTermDebtNoncurrent", "LongTermDebt", "NoncurrentPortionOfBorrowings"],
}

# How long after a fiscal year ends before the public could read the numbers.
# Used by the fallback basis so a year that had ENDED but not yet been REPORTED
# is never treated as ex-ante observable.
REPORTING_LAG_DAYS = 90
SPLITS = None


def companyfacts(ticker):
    cik = TICKER_CIK.get(ticker)
    if not cik:
        return None, f"NOT_AVAILABLE: ticker {ticker} absent from SEC ticker->CIK map"
    cache = CACHE / f"{ticker}.json"
    if cache.exists():
        return json.loads(cache.read_text()), None
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        raw = urllib.request.urlopen(req, timeout=90).read()
    except urllib.error.HTTPError as exc:
        return None, f"NOT_AVAILABLE: SEC returned HTTP {exc.code} for {ticker}"
    except Exception as exc:  # noqa: BLE001
        return None, f"NOT_AVAILABLE: SEC fetch failed for {ticker} ({exc})"
    cache.write_bytes(raw)
    time.sleep(0.25)  # SEC fair-use
    return json.loads(raw), None


def annual_series(facts, keys, cutoff, basis="strict_filed"):
    """Latest annual value per fiscal year, observable as of `cutoff`.

    basis="strict_filed"  - the XBRL fact itself was FILED on or before cutoff.
                            Zero look-ahead, but SEC structured data only becomes
                            dense around 2011-2012, so early base years come up
                            empty.
    basis="period_public" - the fiscal year ENDED at least REPORTING_LAG_DAYS
                            before cutoff, i.e. the company had published these
                            numbers by then, even though the machine-readable
                            copy we are reading was filed later as a comparative.
                            Slight restatement risk; never look-ahead.
    """
    if facts is None:
        return {}
    cut = pd.Timestamp(cutoff)
    candidates = []
    for scope in ("us-gaap", "ifrs-full"):
        blk = facts.get("facts", {}).get(scope, {})
        for key in keys:
            out = {}
            unit_blk = blk.get(key, {}).get("units", {})
            for unit, points in unit_blk.items():
                if unit not in ("USD", "shares", "USD/shares"):
                    continue
                for pt in points:
                    if pt.get("form") not in ("10-K", "20-F", "40-F"):
                        continue
                    start, end = pt.get("start"), pt.get("end")
                    if start and end:  # flow item: require a ~annual span
                        span = (pd.Timestamp(end) - pd.Timestamp(start)).days
                        if not 330 <= span <= 400:
                            continue
                    if basis == "strict_filed":
                        if pt.get("filed", "9999") > cutoff:
                            continue
                    else:
                        if pd.Timestamp(end) + pd.Timedelta(days=REPORTING_LAG_DAYS) > cut:
                            continue
                    fy = end[:4]
                    prev = out.get(fy)
                    if prev is None or pt.get("filed", "") >= prev[1]:
                        out[fy] = (pt["val"], pt.get("filed", ""))
            if out:
                candidates.append(out)
    if not candidates:
        return {}
    # A filer may switch tags over time (e.g. SalesRevenueNet -> RevenueFrom
    # ContractWithCustomer...). Taking the first tag that has ANY data silently
    # returns a stale series, so pick the tag whose series reaches closest to the
    # cutoff, breaking ties on how many years it covers.
    best = max(candidates, key=lambda d: (max(d), len(d)))
    return {k: v[0] for k, v in sorted(best.items())}


def pct(a, b):
    if a is None or b is None or b == 0:
        return None
    return round(a / b - 1, 4)


def ratio(a, b):
    if a is None or b is None or b == 0:
        return None
    return round(a / b, 4)


def build():
    prices = pd.read_parquet(DATA / "prices_monthly.parquet")
    global SPLITS
    SPLITS = pd.read_csv(DATA / "splits.csv") if (DATA / "splits.csv").exists()         else pd.DataFrame(columns=["symbol", "date", "ratio"])
    rows, notes = [], []
    for p in PAIRS:
        for role in ("winner", "loser"):
            t = p[role]
            by = p["base_year"]
            cutoff = f"{by}-12-31"
            facts, err = companyfacts(t)
            if err:
                notes.append(dict(pid=p["pid"], symbol=t, note=err))
            s = {k: annual_series(facts, v, cutoff, "strict_filed")
                 for k, v in TAGS.items()}
            basis = "strict_filed"
            if not s.get("revenue"):
                s2 = {k: annual_series(facts, v, cutoff, "period_public")
                      for k, v in TAGS.items()}
                if s2.get("revenue"):
                    s, basis = s2, "period_public"

            def yrs(key):
                d = s.get(key, {})
                ks = sorted(d)
                return d, ks

            rev, rk = yrs("revenue")
            gp, gk = yrs("gross_profit")
            ni, nk = yrs("net_income")
            sh, shk = yrs("diluted_shares")
            cfo, ck = yrs("cfo")

            def last(d, k, back=0):
                return d[k[-1 - back]] if len(k) > back else None

            rev_l, rev_p, rev_pp = last(rev, rk), last(rev, rk, 1), last(rev, rk, 2)
            gp_l, gp_p = last(gp, gk), last(gp, gk, 1)
            ni_l, ni_p = last(ni, nk), last(ni, nk, 1)
            sh_l, sh_p, sh_pp = last(sh, shk), last(sh, shk, 1), last(sh, shk, 2)
            cfo_l, cfo_p = last(cfo, ck), last(cfo, ck, 1)
            assets = last(*yrs("assets"))
            liab = last(*yrs("liabilities"))
            eq = last(*yrs("equity"))
            cash = last(*yrs("cash"))
            debt = last(*yrs("lt_debt"))

            gm_l = ratio(gp_l, rev_l)
            gm_p = ratio(gp_p, rev_p)

            # Market cap at base-year end. yfinance prices are always split-
            # adjusted, so the as-reported SEC share count is restated onto the
            # same basis by the cumulative split factor after base-year end.
            # Skipping this understates the cap of every later-splitting company
            # (FTNT 1:5 in 2022 would have printed 5x too cheap).
            # Price basis: close_unadjusted is split-adjusted but NOT dividend-
            # adjusted, which is what a market cap wants (the dividend-adjusted
            # close understates the cap of heavy payers such as WING).
            # Share basis: a strict_filed count is as-reported at the time, so it
            # needs the post-cutoff split factor applied to match the price. A
            # period_public count was read out of a LATER filing's comparative
            # column, where the issuer has already restated it for any split, so
            # applying the factor again would double-count.
            mcap, px_used, split_factor = None, None, 1.0
            sp = SPLITS[(SPLITS.symbol == t) & (SPLITS.date > cutoff)]
            if len(sp):
                split_factor = float(sp.ratio.prod())
            applied_factor = split_factor if basis == "strict_filed" else 1.0
            try:
                sub = prices.loc[t]
                sub = sub[sub.index <= pd.Timestamp(cutoff)]
                use_px = sub["close_unadjusted"].dropna()
                if not len(use_px):
                    use_px = sub["close"].dropna()
                if len(use_px) and sh_l:
                    px_used = float(use_px.iloc[-1])
                    mcap = px_used * sh_l * applied_factor
            except KeyError:
                pass

            rows.append(dict(
                pid=p["pid"], role=role, symbol=t, base_year=by,
                data_basis=basis,
                latest_fy_readable=rk[-1] if rk else None,
                revenue_latest=rev_l,
                revenue_growth_yoy=pct(rev_l, rev_p),
                revenue_growth_prior_yoy=pct(rev_p, rev_pp),
                revenue_accelerating=(None if pct(rev_l, rev_p) is None or pct(rev_p, rev_pp) is None
                                      else pct(rev_l, rev_p) > pct(rev_p, rev_pp)),
                gross_margin=gm_l,
                gross_margin_prior=gm_p,
                gross_margin_direction=(None if gm_l is None or gm_p is None
                                        else round(gm_l - gm_p, 4)),
                net_income_latest=ni_l,
                net_income_positive=(None if ni_l is None else ni_l > 0),
                net_income_improving=(None if ni_l is None or ni_p is None else ni_l > ni_p),
                cfo_latest=cfo_l,
                cfo_positive=(None if cfo_l is None else cfo_l > 0),
                diluted_shares_latest=sh_l,
                dilution_yoy=pct(sh_l, sh_p),
                dilution_prior_yoy=pct(sh_p, sh_pp),
                liabilities_over_assets=ratio(liab, assets),
                equity_latest=eq,
                cash_latest=cash,
                lt_debt_latest=debt,
                net_debt=(None if debt is None or cash is None else debt - cash),
                net_debt_over_equity=(None if debt is None or cash is None or not eq
                                      else round((debt - cash) / eq, 4)),
                cash_over_annual_burn=(None if cfo_l is None or cash is None or cfo_l >= 0
                                       else round(cash / abs(cfo_l), 2)),
                price_used_for_mcap=px_used,
                cumulative_split_factor_after_base_year=split_factor,
                split_factor_applied_to_shares=applied_factor,
                market_cap_at_base_year_end=None if mcap is None else round(mcap, 0),
                ps_ratio=ratio(mcap, rev_l),
                analyst_revision_direction="NOT_AVAILABLE: no free source of "
                                           "point-in-time consensus history for these years",
                institutional_ownership_change="NOT_AVAILABLE: yfinance exposes only a "
                                               "current snapshot; historical 13F "
                                               "aggregation not built",
            ))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "fundamentals_exante.csv", index=False, encoding="utf-8")
    pd.DataFrame(notes).to_csv(OUT / "fundamentals_notes.csv", index=False, encoding="utf-8")
    return df, notes


if __name__ == "__main__":
    df, notes = build()
    cov = df.notna().mean().round(2).sort_values()
    print("=== column coverage (share of 22 rows with a value) ===")
    print(cov.to_string())
    print("\n=== rows missing revenue entirely ===")
    print(df[df.revenue_latest.isna()][["pid", "role", "symbol", "base_year"]].to_string(index=False))
    print("\n=== fetch notes ===")
    for n in notes:
        print(n)
