# -*- coding: utf-8 -*-
"""KARST-155 step 2: rebuild the silent-revision event table from the raw
SEC companyfacts layer.

Why not the monthly panel: `panel_monthly.parquet` keeps only the value of the
latest version of each period (`<field>_restated`); it does NOT keep the date on
which that version was filed. That date is the whole point of this test, so the
event table is rebuilt from KARST-146's preserved raw JSON.

Everything here follows CRITERIA.md sections 2-5 literally. No return number is
touched in this file.

Output:
  out/events.parquet    one row per revision event
  out/events_meta.json  counts, exclusions, flags
"""
from __future__ import annotations

import json
import pathlib
import time
from collections import defaultdict

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
PANEL_DIR = REPO / "experiments" / "2026-09-02-fundamentals-panel"
FACTS = PANEL_DIR / "data" / "secfacts"
OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)

DAILY = REPO / "experiments" / "2026-09-02-timing-sweep" / "data" / "daily_close.parquet"
MONTHLY = REPO / "experiments" / "2026-09-01-stock-oracle-curve" / "data" / "stock_monthly.parquet"
SPLITS = REPO / "experiments" / "2026-09-02-fourpiece-test" / "data" / "splits.parquet"

FORMS_PRIMARY = {"10-K", "10-Q", "20-F", "40-F"}
FORMS_AMEND = {"10-K/A", "10-Q/A", "20-F/A", "40-F/A"}

# CRITERIA sec.2 - four fields only, tag fallback verbatim from KARST-146 RULES.md sec.4
TAGS: dict[str, list[str]] = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                "RevenueFromContractWithCustomerIncludingAssessedTax",
                "SalesRevenueNet", "SalesRevenueGoodsNet",
                "Revenue", "RevenueFromContractsWithCustomers",
                "RealEstateRevenueNet"],
    "net_income": ["NetIncomeLoss", "ProfitLoss",
                   "ProfitLossAttributableToOwnersOfParent"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
            "CashFlowsFromUsedInOperatingActivities"],
    "assets": ["Assets"],
}
FLOW_FIELDS = {"revenue", "net_income", "cfo"}
STOCK_FIELDS = {"assets"}

REL_TIERS = (0.02, 0.05)          # CRITERIA sec.3
ABS_FLOOR = 1_000_000.0           # CRITERIA sec.3 / E3
SPLIT_TOL = 0.01                  # CRITERIA E2
TRANSITION_YEARS = {2018, 2019}   # CRITERIA F3


def period_type(start, end):
    if not start:
        return "instant"
    days = (pd.Timestamp(end) - pd.Timestamp(start)).days
    if 80 <= days <= 100:
        return "Q"
    if 170 <= days <= 190:
        return "H"
    if 330 <= days <= 400:
        return "FY"
    return None


def extract(facts: dict) -> dict[tuple, list[dict]]:
    """group key -> list of (filed, val, amended) observations."""
    groups: dict[tuple, list[dict]] = defaultdict(list)
    blocks = facts.get("facts", {})
    for scope in ("us-gaap", "ifrs-full"):
        blk = blocks.get(scope, {})
        for field, taglist in TAGS.items():
            for tag in taglist:
                units = blk.get(tag, {}).get("units", {})
                for unit, points in units.items():
                    if unit != "USD":
                        continue
                    for pt in points:
                        form = pt.get("form")
                        if form not in FORMS_PRIMARY and form not in FORMS_AMEND:
                            continue
                        pt_type = period_type(pt.get("start"), pt.get("end"))
                        if pt_type is None:
                            continue
                        if field in FLOW_FIELDS and pt_type == "instant":
                            continue
                        if field in STOCK_FIELDS and pt_type != "instant":
                            continue
                        filed, val = pt.get("filed"), pt.get("val")
                        if not filed or val is None:
                            continue
                        groups[(field, tag, pt.get("start"), pt["end"], pt_type)].append(
                            dict(filed=filed, val=float(val),
                                 amended=form in FORMS_AMEND, form=form))
    return groups


def split_ratio_between(arr, f0: str, f1: str) -> float:
    """cumulative split ratio for splits with report_date in (f0, f1]."""
    if arr is None:
        return 1.0
    r = 1.0
    for d, ratio in arr:
        if f0 < d <= f1:
            r *= float(ratio)
    return r


def company_events(ticker: str, cik: str, path: pathlib.Path,
                   split_arr) -> tuple[list[dict], dict]:
    facts = json.loads(path.read_text(encoding="utf-8"))
    groups = extract(facts)
    ev, stat = [], defaultdict(int)

    for (field, tag, start, end, ptype), obs in groups.items():
        # dedupe (filed, val); same filing can restate the same fact twice
        seen, uniq = set(), []
        for o in sorted(obs, key=lambda x: (x["filed"], x["val"])):
            k = (o["filed"], o["val"])
            if k in seen:
                continue
            seen.add(k)
            uniq.append(o)
        uniq.sort(key=lambda x: x["filed"])
        stat["groups"] += 1

        originals = [o for o in uniq if not o["amended"]] or uniq
        base = min(originals, key=lambda o: o["filed"])
        v0, f0 = base["val"], base["filed"]
        if abs(v0) < ABS_FLOOR:
            stat["excl_E3_tiny_base"] += 1
            continue

        # first crossing per tier
        for tier in REL_TIERS:
            hit = None
            for o in uniq:
                if o["filed"] <= f0:
                    continue
                d = o["val"] - v0
                if abs(d) >= ABS_FLOOR and abs(d) / abs(v0) > tier:
                    hit = o
                    break
            if hit is None:
                continue
            f1, v1 = hit["filed"], hit["val"]
            # E2 split-mechanical guard
            r = split_ratio_between(split_arr, f0, f1)
            excl_split = False
            if r != 1.0 and v0 != 0:
                ratio = v1 / v0
                if abs(ratio - r) <= SPLIT_TOL * r or abs(ratio - 1 / r) <= SPLIT_TOL / r:
                    excl_split = True
            if excl_split:
                stat[f"excl_E2_split_t{tier}"] += 1
                continue
            ev.append(dict(
                ticker=ticker, cik=cik, field=field, tag=tag, period_type=ptype,
                period_start=start, period_end=end, tier=tier,
                first_val=v0, first_filed=f0, rev_val=v1, rev_filed=f1,
                rel_change=(v1 - v0) / abs(v0),
                direction="down" if v1 < v0 else "up",
                via_amendment=bool(hit["amended"]), rev_form=hit["form"],
                standard_transition=pd.Timestamp(end).year in TRANSITION_YEARS,
            ))
            stat[f"events_t{tier}"] += 1
    return ev, stat


def main() -> None:
    uni = pd.read_csv(PANEL_DIR / "out" / "universe_cik.csv", dtype=str).fillna("")
    uni = uni[uni.cik != ""].drop_duplicates(subset=["ticker"])

    daily = pd.read_parquet(DAILY)
    priced = set(daily.columns)
    monthly = pd.read_parquet(MONTHLY, columns=["symbol", "etf"])
    sector = monthly.dropna(subset=["etf"]).groupby("symbol")["etf"].last()

    splits = pd.read_parquet(SPLITS)
    splits["report_date"] = pd.to_datetime(splits["report_date"]).dt.strftime("%Y-%m-%d")
    sp = {s: g[["report_date", "ratio"]].to_numpy()
          for s, g in splits.groupby("symbol")}

    all_ev, agg = [], defaultdict(int)
    t0 = time.time()
    done = 0
    for _, r in uni.iterrows():
        p = FACTS / f"CIK{r.cik}.json"
        if not p.exists() or p.stat().st_size == 0:
            agg["no_facts_file"] += 1
            continue
        try:
            ev, stat = company_events(r.ticker, r.cik, p, sp.get(r.ticker))
        except Exception as exc:  # noqa: BLE001
            agg["parse_error"] += 1
            print(f"  parse error {r.ticker}: {exc}", flush=True)
            continue
        all_ev += ev
        for k, v in stat.items():
            agg[k] += v
        done += 1
        if done % 100 == 0:
            print(f"  {done} companies  {len(all_ev)} events  "
                  f"{time.time()-t0:.0f}s", flush=True)

    df = pd.DataFrame(all_ev)
    df["has_price"] = df["ticker"].isin(priced)
    df["sector"] = df["ticker"].map(sector)

    # 8-K Item 4.02 within +-90 days of the revision filing (CRITERIA F2)
    f402 = pd.read_csv(OUT / "eightk_402.csv", dtype=str)
    by_cik = defaultdict(list)
    for _, r in f402.iterrows():
        by_cik[str(r.cik)].append(pd.Timestamp(r.filing_date))
    rev_dt = pd.to_datetime(df["rev_filed"])
    near = []
    for cik, d in zip(df["cik"], rev_dt):
        hits = by_cik.get(str(cik), [])
        near.append(any(abs((h - d).days) <= 90 for h in hits))
    df["near_8k_402"] = near

    df["silent"] = (~df["via_amendment"]) & (~df["near_8k_402"])
    df["rev_filed_dt"] = rev_dt
    # entry = first calendar month end strictly after the revision filing date
    df["entry_month_end"] = (rev_dt + pd.Timedelta(days=1)) + pd.offsets.MonthEnd(0)

    df.to_parquet(OUT / "events.parquet", index=False)

    def cnt(mask) -> int:
        return int(mask.sum())

    t2 = df["tier"] == 0.02
    meta = dict(
        criteria="CRITERIA.md sections 2-5, frozen before any return number",
        source="experiments/2026-09-02-fundamentals-panel/data/secfacts/*.json "
               "(KARST-146 preserved raw companyfacts); the monthly panel keeps "
               "no revision filing date, so events are rebuilt from raw",
        companies_scanned=done,
        companies_no_facts_file=agg["no_facts_file"],
        period_groups=agg["groups"],
        excluded_E3_tiny_base=agg["excl_E3_tiny_base"],
        excluded_E2_split_tier002=agg["excl_E2_split_t0.02"],
        excluded_E2_split_tier005=agg["excl_E2_split_t0.05"],
        events_tier002=cnt(t2), events_tier005=cnt(df["tier"] == 0.05),
        tier002=dict(
            total=cnt(t2),
            down=cnt(t2 & (df.direction == "down")),
            up=cnt(t2 & (df.direction == "up")),
            via_amendment=cnt(t2 & df.via_amendment),
            near_8k_402=cnt(t2 & df.near_8k_402),
            silent=cnt(t2 & df.silent),
            silent_down=cnt(t2 & df.silent & (df.direction == "down")),
            silent_up=cnt(t2 & df.silent & (df.direction == "up")),
            silent_down_priced=cnt(t2 & df.silent & (df.direction == "down")
                                   & df.has_price),
            silent_down_priced_sector=cnt(t2 & df.silent & (df.direction == "down")
                                          & df.has_price & df.sector.notna()),
            standard_transition=cnt(t2 & df.standard_transition),
        ),
        excluded_E4_no_price_tier002=cnt(t2 & ~df.has_price),
        excluded_E5_no_sector_tier002=cnt(t2 & df.has_price & df.sector.isna()),
        by_field_tier002=df[t2].groupby(["field", "direction"]).size()
                              .unstack(fill_value=0).to_dict(),
        seconds=round(time.time() - t0, 1),
    )
    (OUT / "events_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")
    print(json.dumps(meta, indent=2, ensure_ascii=False, default=str), flush=True)


if __name__ == "__main__":
    main()
