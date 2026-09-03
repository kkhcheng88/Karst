# -*- coding: utf-8 -*-
"""KARST-172 步驟二:以實體主鍵重建季度面板 v3。

鍵:`entity_id`(CIK)+ `period_end`。一列 = 一個實體的一個財政期末。

與面板 v2(KARST-146/158)的分別:
  v2 鍵是 ticker + 月末,每個月末抄一次最新已知值(即同一份申報會重覆出現在多個月);
  v3 鍵是 entity_id + 期末,一份申報一列,不重覆。要「某月最新已知值」的用法,
  由讀取方按 `filed_date <= 該月末` 自己取,取法住在因子取值口那一層,不預先攤平。

前視防線:
  1. `filed_date` 是**申報日**,不是期末日。任何用法一律以 filed_date 為可得日。
  2. 每格取**首次申報值**(同一 tag 同一期最早申報那一版),不是最新重述值。
     最新重述值另存 `<欄>_restated` 與 `<欄>_restated_filed`;用它即帶修訂前視,
     報告已寫明。

缺值原因(`<欄>_missing_reason`):
  none          有值
  tag_absent    這家公司這一期沒有貼這個標籤
  fpi_no_facts  整份 companyfacts 沒有 us-gaap / ifrs-full 區塊(外國申報人多數如此)
  fail          companyfacts 抓不到
"""
from __future__ import annotations

import gzip
import json
import pathlib
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

REPO = pathlib.Path(r"C:\projects\Karst")
CACHE = REPO / "data" / "sec" / "companyfacts"
OUTDIR = REPO / "data" / "panel"
HERE = pathlib.Path(__file__).resolve().parent

FORMS_PRIMARY = {"10-K", "10-Q", "20-F", "40-F"}
FORMS_AMEND = {"10-K/A", "10-Q/A", "20-F/A", "40-F/A"}
OK_SHARES = {"shares"}
MONEY_RE = __import__("re").compile(r"^[A-Z]{3}$")
# 貨幣單位:收全部三個大寫字母的 ISO 代碼,不是只收 USD。
# 理由:241 家外國申報人(IFRS)的帳目全部以本國貨幣申報,只收 USD 等於把它們整批當成
# 「取不到」,而它們其實有齊 Assets / Liabilities / CashAndCashEquivalents / Equity。
# 代價寫死在這裡:**本面板不做貨幣換算**,逐格記低 `<欄>_unit`,列上記 `currency`。
# 任何跨公司比大細的用法必須自己先換算;只看正負號的用法(例如淨現金為正)不受影響。

# 標籤表:欄名 -> [(分類體系, 標籤), ...],次序即優先次序
INSTANT_FIELDS: dict[str, list[tuple[str, str]]] = {
    "cash_and_equivalents": [
        ("us-gaap", "CashAndCashEquivalentsAtCarryingValue"),
        ("us-gaap", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"),
        ("us-gaap", "CashAndCashEquivalentsAtCarryingValueIncludingDiscontinuedOperations"),
        ("ifrs-full", "CashAndCashEquivalents"),
    ],
    "short_term_investments": [
        ("us-gaap", "ShortTermInvestments"),
        ("us-gaap", "MarketableSecuritiesCurrent"),
        ("us-gaap", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"),
        ("us-gaap", "OtherShortTermInvestments"),
        ("ifrs-full", "OtherCurrentFinancialAssets"),
    ],
    "lt_debt": [
        ("us-gaap", "LongTermDebtNoncurrent"),
        ("us-gaap", "LongTermDebt"),
        ("us-gaap", "LongTermDebtAndCapitalLeaseObligationsNoncurrent"),
        ("ifrs-full", "NoncurrentPortionOfNoncurrentBorrowings"),
    ],
    "liabilities": [
        ("us-gaap", "Liabilities"),
        ("ifrs-full", "Liabilities"),
    ],
    "assets": [
        ("us-gaap", "Assets"),
        ("ifrs-full", "Assets"),
    ],
    "equity": [
        ("us-gaap", "StockholdersEquity"),
        ("us-gaap", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
        ("ifrs-full", "Equity"),
    ],
}

# 短期債務照 KARST-166 CRITERIA 第二節:短期借款與「一年內到期的長期債務」是兩件事,
# 分兩條序列各自取值再**相加**,不是取優先次序第一個有數的。
ST_DEBT_A = [("us-gaap", "ShortTermBorrowings"), ("us-gaap", "OtherShortTermBorrowings"),
             ("ifrs-full", "ShorttermBorrowings")]
ST_DEBT_B = [("us-gaap", "LongTermDebtCurrent"),
             ("ifrs-full", "CurrentPortionOfLongtermBorrowings")]

FLOW_FIELDS: dict[str, list[tuple[str, str]]] = {
    "revenue": [
        ("us-gaap", "Revenues"),
        ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
        ("us-gaap", "RevenueFromContractWithCustomerIncludingAssessedTax"),
        ("us-gaap", "SalesRevenueNet"),
        ("us-gaap", "SalesRevenueGoodsNet"),
        ("ifrs-full", "Revenue"),
        ("ifrs-full", "RevenueFromContractsWithCustomers"),
    ],
    "operating_cash_flow": [
        ("us-gaap", "NetCashProvidedByUsedInOperatingActivities"),
        ("us-gaap", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"),
        ("ifrs-full", "CashFlowsFromUsedInOperatingActivities"),
    ],
    "net_income": [
        ("us-gaap", "NetIncomeLoss"),
        ("us-gaap", "ProfitLoss"),
        ("ifrs-full", "ProfitLoss"),
        ("ifrs-full", "ProfitLossAttributableToOwnersOfParent"),
    ],
}

VALUE_FIELDS = (list(INSTANT_FIELDS) + ["st_debt", "total_debt"]
                + list(FLOW_FIELDS) + ["shares_outstanding"])


def period_type(start, end) -> str | None:
    """把一個事實的跨期分類。

    現金流量表與部分損益表在 10-Q 裡是**年初至今累計**,不是單季,所以除了 Q 與 FY,
    半年(H)與九個月(9M)兩種累計期同樣收,並在 `<欄>_period` 逐格寫明它蓋住幾長。
    只收這四種,其餘(例如兩年累計)一律丟。
    """
    if not start:
        return "instant"
    days = (pd.Timestamp(end) - pd.Timestamp(start)).days
    if 80 <= days <= 100:
        return "Q"
    if 170 <= days <= 190:
        return "H"
    if 260 <= days <= 290:
        return "9M"
    if 330 <= days <= 400:
        return "FY"
    return None


def harvest(doc: dict, spec: list[tuple[str, str]], want_shares: bool = False):
    """由一份 companyfacts 抽出一張 (期末 -> 候選點) 表,已按優先次序帶 prio。"""
    facts = doc.get("facts") or {}
    out: dict[str, list[dict]] = defaultdict(list)
    for prio, (scope, tag) in enumerate(spec):
        units = ((facts.get(scope) or {}).get(tag) or {}).get("units") or {}
        for unit, points in units.items():
            if want_shares:
                if unit not in OK_SHARES:
                    continue
            elif not MONEY_RE.match(unit):
                continue
            for pt in points:
                form = pt.get("form")
                if form not in FORMS_PRIMARY and form not in FORMS_AMEND:
                    continue
                if pt.get("val") is None or not pt.get("filed"):
                    continue
                ptype = period_type(pt.get("start"), pt.get("end"))
                if ptype is None:
                    continue
                out[pt["end"]].append(dict(
                    scope=scope, tag=tag, prio=prio, val=float(pt["val"]),
                    filed=pt["filed"], accn=pt.get("accn", ""), ptype=ptype,
                    unit=unit, amended=form in FORMS_AMEND))
    return out


def choose(cands: list[dict], allowed: tuple[str, ...]) -> dict | None:
    """由同一期末的候選點揀一格值。

    先按標籤優先次序(prio 細者先),同一標籤取**最早申報**那一版作為值,
    最遲申報那一版作為重述值。期別以 allowed 限死(存量只收 instant,流量先 Q 後 FY)。
    """
    pool = [c for c in cands if c["ptype"] in allowed]
    if not pool:
        return None
    for ptype in allowed:
        sub = [c for c in pool if c["ptype"] == ptype]
        if not sub:
            continue
        # 同一格有多過一種貨幣時,USD 優先(有些外國申報人兩種都貼)
        if any(c.get("unit") == "USD" for c in sub):
            sub = [c for c in sub if c.get("unit") == "USD"]
        best_prio = min(c["prio"] for c in sub)
        same = [c for c in sub if c["prio"] == best_prio]
        originals = [c for c in same if not c["amended"]] or same
        first = min(originals, key=lambda c: c["filed"])
        latest = max(same, key=lambda c: c["filed"])
        return dict(first, restated=latest["val"], restated_filed=latest["filed"],
                    was_restated=bool(latest["filed"] != first["filed"]
                                      and latest["val"] != first["val"]))
    return None


def blank_row(cik: str, status: str, reason: str) -> list[dict]:
    row = {"entity_id": cik, "period_end": None, "filed_date": None, "n_fields": 0,
           "facts_status": status, "currency": ""}
    for f in VALUE_FIELDS:
        row[f] = None
        row[f"{f}_tag"] = ""
        row[f"{f}_scope"] = ""
        row[f"{f}_unit"] = ""
        row[f"{f}_filed"] = None
        row[f"{f}_missing_reason"] = reason
    return [row]


def build_one(args) -> list[dict]:
    cik, status = args
    base = {"entity_id": cik}
    if status == "fail":
        return blank_row(cik, "fail", "fail")
    if status != "ok":
        return blank_row(cik, "empty", "fpi_no_facts")

    p = CACHE / f"CIK{cik}.json.gz"
    if not p.exists():
        return blank_row(cik, "fail", "fail")
    with gzip.open(p, "rb") as f:
        doc = json.load(f)

    inst = {name: harvest(doc, spec) for name, spec in INSTANT_FIELDS.items()}
    sta = harvest(doc, ST_DEBT_A)
    stb = harvest(doc, ST_DEBT_B)
    flow = {name: harvest(doc, spec) for name, spec in FLOW_FIELDS.items()}
    cover = harvest(doc, [("dei", "EntityCommonStockSharesOutstanding")], want_shares=True)

    ends: set[str] = set()
    for tbl in inst.values():
        ends |= set(tbl)
    for tbl in flow.values():
        ends |= {e for e, v in tbl.items()
                 if any(c["ptype"] in ("Q", "H", "9M", "FY") for c in v)}
    ends |= set(sta) | set(stb)
    if not ends:
        # 分開兩件事:整份文件沒有帳目區塊 vs 有帳目但沒有一條落在本表的標籤與表格類型之內
        facts = doc.get("facts") or {}
        has_acc = bool(facts.get("us-gaap")) or bool(facts.get("ifrs-full"))
        if has_acc:
            return blank_row(cik, "no_usable_period", "tag_absent")
        return blank_row(cik, "empty", "fpi_no_facts")

    cover_by_accn: dict[str, dict] = {}
    cover_flat: list[tuple[str, dict]] = []
    for e, cands in cover.items():
        best = min(cands, key=lambda c: c["filed"])
        cover_flat.append((e, best))
        for c in cands:
            cover_by_accn.setdefault(c["accn"], c)
    cover_flat.sort()

    rows = []
    for end in sorted(ends):
        row = dict(base, period_end=end, facts_status="ok")
        filed_dates, accns, nfields = [], set(), 0

        def put(field: str, pick: dict | None, derived_tag: str = "") -> None:
            nonlocal nfields
            if pick is None:
                row[field] = None
                row[f"{field}_tag"] = ""
                row[f"{field}_scope"] = ""
                row[f"{field}_unit"] = ""
                row[f"{field}_filed"] = None
                row[f"{field}_missing_reason"] = "tag_absent"
                return
            row[field] = pick["val"]
            row[f"{field}_tag"] = derived_tag or pick["tag"]
            row[f"{field}_scope"] = pick.get("scope", "")
            row[f"{field}_unit"] = pick.get("unit", "")
            row[f"{field}_filed"] = pick["filed"]
            row[f"{field}_missing_reason"] = "none"
            if "restated" in pick:
                row[f"{field}_restated"] = pick["restated"]
                row[f"{field}_was_restated"] = pick["was_restated"]
            filed_dates.append(pick["filed"])
            if pick.get("accn"):
                accns.add(pick["accn"])
            nfields += 1

        for name, tbl in inst.items():
            put(name, choose(tbl.get(end, []), ("instant",)))

        a = choose(sta.get(end, []), ("instant",))
        b = choose(stb.get(end, []), ("instant",))
        if a is None and b is None:
            put("st_debt", None)
        else:
            val = (a["val"] if a else 0.0) + (b["val"] if b else 0.0)
            src = a or b
            tags = "+".join(x["tag"] for x in (a, b) if x)
            put("st_debt", dict(src, val=val, restated=val,
                                restated_filed=src["filed"], was_restated=False), tags)

        if row.get("lt_debt") is not None:
            st = row.get("st_debt") or 0.0
            row["total_debt"] = row["lt_debt"] + st
            row["total_debt_tag"] = ("lt_debt+st_debt" if row.get("st_debt") is not None
                                     else "lt_debt+st_debt(st 缺當 0)")
            row["total_debt_scope"] = row.get("lt_debt_scope", "")
            row["total_debt_unit"] = row.get("lt_debt_unit", "")
            row["total_debt_filed"] = row.get("lt_debt_filed")
            row["total_debt_missing_reason"] = "none"
        else:
            row["total_debt"] = None
            row["total_debt_tag"] = ""
            row["total_debt_scope"] = ""
            row["total_debt_unit"] = ""
            row["total_debt_filed"] = None
            row["total_debt_missing_reason"] = "tag_absent"

        for name, tbl in flow.items():
            pick = choose(tbl.get(end, []), ("Q", "H", "9M", "FY"))
            put(name, pick)
            row[f"{name}_period"] = pick["ptype"] if pick else ""

        sh = None
        for accn in accns:
            if accn in cover_by_accn:
                sh = cover_by_accn[accn]
                break
        if sh is None and cover_flat:
            lim = (pd.Timestamp(end) + pd.Timedelta(days=150)).strftime("%Y-%m-%d")
            after = [(e, c) for e, c in cover_flat if end <= e <= lim]
            if after:
                sh = after[0][1]
        put("shares_outstanding", sh)

        row["filed_date"] = max(filed_dates) if filed_dates else None
        row["n_fields"] = nfields
        units = [row.get(f"{f}_unit") for f in
                 (list(INSTANT_FIELDS) + ["st_debt"] + list(FLOW_FIELDS))]
        units = [u for u in units if u]
        row["currency"] = max(set(units), key=units.count) if units else ""
        rows.append(row)
    return rows


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    man = pd.read_csv(CACHE / "manifest.csv", dtype=str)
    jobs = list(zip(man["cik"], man["status"]))
    print(f"{len(jobs)} 個實體要建面板", flush=True)
    frames = []
    with ProcessPoolExecutor(max_workers=6) as ex:
        for i, rows in enumerate(ex.map(build_one, jobs, chunksize=20), 1):
            if rows:
                frames.append(pd.DataFrame(rows))
            if i % 500 == 0:
                print(f"  {i}/{len(jobs)}", flush=True)
    panel = pd.concat(frames, ignore_index=True)
    for c in panel.columns:
        if c.endswith("_filed") or c in ("period_end", "filed_date"):
            panel[c] = pd.to_datetime(panel[c], errors="coerce")
    panel = panel.sort_values(["entity_id", "period_end"]).reset_index(drop=True)

    # 股數刻度旗(RULES.md 第六節的鄰期一千倍規則):只標旗,不自動修
    panel["shares_scale_suspect"] = False
    s = panel.loc[panel["shares_outstanding"].notna(),
                  ["entity_id", "shares_outstanding"]].copy()
    s["shares_outstanding"] = s["shares_outstanding"].replace(0.0, pd.NA).astype("Float64")
    r = s.groupby("entity_id")["shares_outstanding"].transform(
        lambda x: (x / x.shift()).abs())
    flag = r[(r > 1000) | (r < 1 / 1000)].index
    panel.loc[flag, "shares_scale_suspect"] = True

    panel.to_parquet(OUTDIR / "quarterly_v3.parquet", index=False, compression="zstd")
    print(f"面板 {len(panel):,} 列,實體 {panel.entity_id.nunique()}", flush=True)
    print("刻度旗:", int(panel["shares_scale_suspect"].sum()), flush=True)


if __name__ == "__main__":
    main()
