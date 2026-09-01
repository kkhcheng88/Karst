# -*- coding: utf-8 -*-
"""KARST-146 step 5: build the monthly point-in-time fundamentals panel.

Implements experiments/2026-09-02-fundamentals-panel/RULES.md verbatim. Read
that file first - it is the spec, this is only the machinery.

Outputs (all under out/):
  panel_monthly.parquet   one row per (ticker, month end)
  coverage_by_year.csv    per field per year: value / no value / custom-tag-only
  meta.json               period, counts, per-field coverage, download stats

Run:  PYTHONUTF8=1 python build_panel.py
"""
from __future__ import annotations

import json
import pathlib
import time
from collections import defaultdict

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"
CACHE = HERE / "data" / "secfacts"
OUT.mkdir(parents=True, exist_ok=True)

PANEL_START = "2009-01-31"
PANEL_END = "2026-08-31"

FORMS_PRIMARY = {"10-K", "10-Q", "20-F", "40-F"}
FORMS_AMEND = {"10-K/A", "10-Q/A", "20-F/A", "40-F/A"}

TAGS: dict[str, list[str]] = {
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
    "lt_debt": ["LongTermDebtNoncurrent", "LongTermDebt",
                "NoncurrentPortionOfBorrowings"],
}

FLOW_FIELDS = ["revenue", "gross_profit", "net_income", "diluted_shares",
               "cfo", "capex"]
STOCK_FIELDS = ["assets", "liabilities", "equity", "cash", "lt_debt"]
TTM_FIELDS = ["revenue", "gross_profit", "net_income", "cfo", "capex"]

SPAN_ORDER = {"instant": 0, "Q": 0, "H": 1, "FY": 2}

SHARE_FIELDS = {"diluted_shares"}
OK_UNITS_MONEY = {"USD"}
OK_UNITS_SHARES = {"shares"}

# Keywords used ONLY to classify the "custom tag only" coverage bucket. They
# never feed a panel value - see RULES.md section 3.
#
# MEASURED RESULT (all 698 downloaded documents): the companyfacts endpoint
# publishes ONLY standard taxonomies - dei, us-gaap, srt, ffd, invest, ecd,
# rxp, ifrs-full. Not one company-specific extension namespace appears in any
# document. So this bucket is structurally always zero here: it is not that no
# filer uses custom tags, it is that THIS endpoint does not expose them. They
# live in each filing's own XBRL instance. The bucket is kept, and reported as
# not-measurable rather than as zero, so nobody later reads a 0 as "no filer
# uses custom tags".
CUSTOM_HINTS = {
    "revenue": ("revenue", "sales"),
    "gross_profit": ("grossprofit", "grossmargin"),
    "net_income": ("netincome", "profitloss", "netloss"),
    "diluted_shares": ("diluted", "weightedaverage"),
    "cfo": ("operatingactivities",),
    "capex": ("paymentstoacquire", "capitalexpenditure", "purchaseofproperty"),
    "assets": ("assets",),
    "liabilities": ("liabilities",),
    "equity": ("equity",),
    "cash": ("cash",),
    "lt_debt": ("debt", "borrowing"),
}


def month_ends(a: str, b: str) -> list[pd.Timestamp]:
    return list(pd.date_range(a, b, freq="ME"))


def period_type(start: str | None, end: str | None) -> str | None:
    """Classify a fact's span. Anything that is not a clean quarter, half or
    year is dropped - see RULES.md section 6."""
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


def extract(facts: dict) -> tuple[dict[str, list[dict]], dict[str, bool]]:
    """Pull every usable observation for our eleven fields out of one
    companyfacts document. Returns (observations, has_custom_tag_hint)."""
    obs: dict[str, list[dict]] = {f: [] for f in TAGS}
    blocks = facts.get("facts", {})
    for scope in ("us-gaap", "ifrs-full"):
        blk = blocks.get(scope, {})
        if not blk:
            continue
        for field, taglist in TAGS.items():
            want_shares = field in SHARE_FIELDS
            for prio, tag in enumerate(taglist):
                units = blk.get(tag, {}).get("units", {})
                for unit, points in units.items():
                    if want_shares:
                        if unit not in OK_UNITS_SHARES:
                            continue
                    elif unit not in OK_UNITS_MONEY:
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
                        filed = pt.get("filed")
                        if not filed or pt.get("val") is None:
                            continue
                        obs[field].append(dict(
                            tag=tag, prio=prio, start=pt.get("start"),
                            end=pt["end"], filed=filed, val=float(pt["val"]),
                            ptype=pt_type, amended=form in FORMS_AMEND))

    # custom-namespace hint: any taxonomy that is not us-gaap / ifrs-full / dei
    custom: dict[str, bool] = {f: False for f in TAGS}
    for scope, blk in blocks.items():
        if scope in ("us-gaap", "ifrs-full", "dei", "srt"):
            continue
        low = [k.lower() for k in blk]
        for field, hints in CUSTOM_HINTS.items():
            if any(any(h in k for h in hints) for k in low):
                custom[field] = True
    return obs, custom


def first_versions(rows: list[dict]) -> list[dict]:
    """Collapse each (tag, start, end) to its earliest-filed version, carrying
    the latest-filed version alongside as the restatement. RULES.md section 2."""
    by_period: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        by_period[(r["tag"], r["start"], r["end"])].append(r)
    out = []
    for _, group in by_period.items():
        originals = [g for g in group if not g["amended"]] or group
        originals.sort(key=lambda g: g["filed"])
        first = dict(originals[0])
        latest = max(group, key=lambda g: g["filed"])
        first["restated_val"] = latest["val"]
        first["restated_filed"] = latest["filed"]
        first["was_restated"] = (latest["filed"] != first["filed"]
                                 and latest["val"] != first["val"])
        out.append(first)
    out.sort(key=lambda g: (g["filed"], g["end"]))
    return out


def pick_tag(cands: list[dict]) -> str | None:
    """Latest-reaching tag wins; ties go to the higher-priority tag.
    RULES.md section 4."""
    if not cands:
        return None
    best: dict[str, tuple[str, int]] = {}
    for c in cands:
        cur = best.get(c["tag"])
        if cur is None or c["end"] > cur[0]:
            best[c["tag"]] = (c["end"], c["prio"])
    return max(best.items(), key=lambda kv: (kv[1][0], -kv[1][1]))[0]


def build_ttm(cands: list[dict]) -> tuple[float | None, str]:
    """Trailing four quarters. RULES.md section 6."""
    qs = sorted([c for c in cands if c["ptype"] == "Q"],
                key=lambda c: c["end"], reverse=True)
    fys = sorted([c for c in cands if c["ptype"] == "FY"], key=lambda c: c["end"])

    def chain(quarters: list[dict]) -> tuple[float | None, str]:
        if not quarters:
            return None, ""
        picked = [quarters[0]]
        for q in quarters[1:]:
            if len(picked) == 4:
                break
            prev = picked[-1]
            # the next quarter must end where the previous one starts (+-10d)
            gap = abs((pd.Timestamp(prev["start"]) - pd.Timestamp(q["end"])).days)
            if gap <= 10:
                picked.append(q)
        if len(picked) != 4:
            return None, ""
        span = (pd.Timestamp(picked[0]["end"])
                - pd.Timestamp(picked[-1]["start"])).days
        if not 350 <= span <= 380:
            return None, ""
        return sum(p["val"] for p in picked), "four_quarters"

    val, basis = chain(qs)
    if val is not None:
        return val, basis

    # fy_minus_three: derive the missing Q4 from the annual figure
    if fys:
        fy = fys[-1]
        inner = [q for q in qs
                 if q["start"] >= fy["start"] and q["end"] <= fy["end"]]
        if len(inner) >= 3:
            inner_sorted = sorted(inner, key=lambda c: c["end"])[:3]
            covered = sum(q["val"] for q in inner_sorted)
            q4 = dict(start=inner_sorted[-1]["end"], end=fy["end"],
                      val=fy["val"] - covered, ptype="Q",
                      filed=fy["filed"], tag=fy["tag"])
            merged = sorted(qs + [q4], key=lambda c: c["end"], reverse=True)
            val, _ = chain(merged)
            if val is not None:
                return val, "fy_minus_three"
        return fy["val"], "annual_only"
    return None, "insufficient"


def build_company(ticker: str, cik: str, path: pathlib.Path,
                  months: list[pd.Timestamp], memb: tuple[str, str]):
    facts = json.loads(path.read_text(encoding="utf-8"))
    obs, custom = extract(facts)
    series = {f: first_versions(v) for f, v in obs.items()}

    all_filed = [r["filed"] for v in series.values() for r in v]
    if not all_filed:
        return [], custom
    lo, hi = min(all_filed), max(all_filed)

    rows = []
    for m in months:
        ms = m.strftime("%Y-%m-%d")
        if ms < lo:
            continue
        if ms > (pd.Timestamp(hi) + pd.DateOffset(months=6)).strftime("%Y-%m-%d"):
            continue
        row = {"ticker": ticker, "cik": cik, "month_end": m,
               "in_index": (memb[0] <= ms and (not memb[1] or ms <= memb[1]))}
        for field in TAGS:
            cands = [r for r in series[field] if r["filed"] <= ms]
            tag = pick_tag(cands)
            if tag is None:
                continue
            same = [c for c in cands if c["tag"] == tag]
            latest_end = max(c["end"] for c in same)
            # Same period end => shortest span wins (Q over H over FY), so a
            # 10-Q's year-to-date column never masquerades as the quarter.
            # RULES.md section 6.
            best = min([c for c in same if c["end"] == latest_end],
                       key=lambda c: (SPAN_ORDER[c["ptype"]], c["filed"]))
            row[field] = best["val"]
            row[f"{field}_tag"] = tag
            row[f"{field}_end"] = best["end"]
            row[f"{field}_filed"] = best["filed"]
            row[f"{field}_age_days"] = (m - pd.Timestamp(best["filed"])).days
            row[f"{field}_restated"] = best["restated_val"]
            row[f"{field}_was_restated"] = bool(best["was_restated"])
            if field in FLOW_FIELDS:
                row[f"{field}_period"] = best["ptype"]
            if field in TTM_FIELDS:
                ttm, basis = build_ttm(same)
                row[f"{field}_ttm"] = ttm
                row[f"{field}_ttm_basis"] = basis
        rows.append(row)
    return rows, custom


def main() -> None:
    uni = pd.read_csv(OUT / "universe_cik.csv", dtype=str).fillna("")
    have = uni[uni.cik != ""].copy()
    months = month_ends(PANEL_START, PANEL_END)
    print(f"{len(have)} tickers with a CIK, {len(months)} month ends", flush=True)

    frames, custom_map, no_facts, empty = [], {}, [], []
    t0 = time.time()
    for i, (_, r) in enumerate(have.iterrows(), 1):
        p = CACHE / f"CIK{r.cik}.json"
        if not p.exists() or p.stat().st_size == 0:
            no_facts.append(r.ticker)
            continue
        try:
            rows, custom = build_company(r.ticker, r.cik, p, months,
                                         (r.joined_on, r.left_on))
        except Exception as exc:  # noqa: BLE001
            no_facts.append(f"{r.ticker} (parse error: {exc})")
            continue
        custom_map[r.ticker] = custom
        if not rows:
            empty.append(r.ticker)
            continue
        frames.append(pd.DataFrame(rows))
        if i % 100 == 0:
            print(f"  {i}/{len(have)}  {time.time() - t0:.0f}s", flush=True)

    panel = pd.concat(frames, ignore_index=True)
    panel = panel.sort_values(["ticker", "month_end"]).reset_index(drop=True)
    panel.to_parquet(OUT / "panel_monthly.parquet", index=False)
    print(f"panel rows {len(panel):,}  tickers {panel.ticker.nunique()}",
          flush=True)

    # ---- coverage by year -------------------------------------------------
    panel["year"] = panel.month_end.dt.year
    cov_rows = []
    for year, grp in panel.groupby("year"):
        alive = set(grp.ticker.unique())
        for field in TAGS:
            if field in grp.columns:
                withval = set(grp.loc[grp[field].notna(), "ticker"].unique())
            else:
                withval = set()
            without = alive - withval
            custom_only = {t for t in without
                           if custom_map.get(t, {}).get(field)}
            cov_rows.append(dict(
                year=int(year), field=field, companies_in_panel=len(alive),
                has_value=len(withval),
                custom_tag_only=len(custom_only),
                custom_tag_measurable=False,
                no_value=len(without) - len(custom_only),
                pct_has_value=round(len(withval) / len(alive), 4) if alive else None,
                note="custom_tag_only 恆為 0:companyfacts 端點只出標準分類體系,"
                     "公司自訂標籤根本不在這份文件裡,不是「沒有公司用自訂標籤」"))
    cov = pd.DataFrame(cov_rows).sort_values(["year", "field"])
    cov.to_csv(OUT / "coverage_by_year.csv", index=False, encoding="utf-8")

    # ---- ttm basis mix ----------------------------------------------------
    basis_rows = []
    for field in TTM_FIELDS:
        col = f"{field}_ttm_basis"
        if col in panel.columns:
            vc = panel[col].fillna("missing").value_counts(normalize=True)
            for k, v in vc.items():
                basis_rows.append(dict(field=field, basis=k, share=round(v, 4)))
    pd.DataFrame(basis_rows).to_csv(OUT / "ttm_basis_mix.csv", index=False,
                                    encoding="utf-8")

    dl = {}
    if (OUT / "download_summary.json").exists():
        dl = json.loads((OUT / "download_summary.json").read_text(encoding="utf-8"))
    meta = dict(
        rules_commit_note="規則見 RULES.md,已於面板數字產生前獨立 commit",
        panel_start=PANEL_START, panel_end=PANEL_END,
        month_ends=len(months),
        universe_tickers=int(len(uni)),
        tickers_with_cik=int(len(have)),
        tickers_without_cik=int((uni.cik == "").sum()),
        tickers_in_panel=int(panel.ticker.nunique()),
        tickers_cik_but_no_facts_file=no_facts,
        tickers_facts_but_no_usable_row=empty,
        panel_rows=int(len(panel)),
        custom_tag_bucket=(
            "無法量度。已掃全部 698 份 companyfacts,出現過的分類體系只有 dei / "
            "us-gaap / srt / ffd / invest / ecd / rxp / ifrs-full,一個公司自訂命名"
            "空間都沒有。自訂標籤住在每份申報自己的 XBRL 實例檔,不在這個端點。"
            "所以覆蓋率報告的第三格恆為 0,那是端點的限制,不是事實陳述。"
            "要真正量度自訂標籤,要另外下載申報實例檔——本票範圍以外。"),
        field_coverage_overall={
            f: round(float(panel[f].notna().mean()), 4)
            for f in TAGS if f in panel.columns},
        download=dl,
    )
    (OUT / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print("meta written", flush=True)


if __name__ == "__main__":
    main()
