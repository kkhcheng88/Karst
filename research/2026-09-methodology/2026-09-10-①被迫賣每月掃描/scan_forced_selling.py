# -*- coding: utf-8 -*-
"""
KARST-201:①被迫賣(forced-selling)每月候選來源 —— 參數化掃描腳本。

沿用 research/2026-09-methodology/scan_forced_selling_2026-08.py 的七類申報
分類規則(不改動),把「年月」變成參數,並在原本只掃申報的基礎上再接三件事:

  1. 實體:CIK(即申報快取檔名去掉 "CIK" 與 ".json")直接就是本倉的
     entity_id(data/universe/entities.parquet 已驗證同一口徑),查代號用
     data/universe/ticker_periods.parquet(生效期含申報日那一條,查不到就退
     entities.parquet 的 primary_ticker)。
  2. 價格:data/prices/daily/part_*.parquet(entity_id, date, adj_close,
     volume 等)。算兩件事——
       - 衝擊期跌幅:申報日前後 20 個交易日,相對 SPY 的變化
         (方法照 research/2026-09-methodology/2026-09-09-①基準率表/build_events.py
         的 rel60 做法:用 adj_close/SPY adj_close 的比值,取視窗尾/視窗頭 − 1)。
       - 近 60 個交易日中位成交額(申報日之前,含申報日當日)。
  3. 現金流與負債:呼叫 strategy/tools/implied_expectations.py 的取數層
     (load_facts / duration_series / quarterize / ttm / interest_bearing_debt)
     ——只讀不改,不呼叫它的估值/市價/WACC 那一截(那些要連網抓 yfinance 與
     十年期美債,逐家掃太慢,亦與本票無關)。算滾動四季經營現金流(OCF TTM)
     是否為正,以及負債 / OCF 的比率。

①兩道閘(與 build_events.py 的「負債閘 B」「現金流閘」同一口徑,KARST-187/191
已用同一組定義):
  閘一(現金流閘)—— OCF_TTM > 0
  閘二(負債閘 B)—— 總負債 / OCF_TTM <= 3
候選 = 兩閘皆過 且 衝擊期相對 SPY 跌幅 <= -15%。

SC 13D / SC 13D/A 只計數,不逐宗接實體與價格(票面要求)。

輸出:
  <OUT>/candidates_<YYYY-MM>.csv   —— 逐宗申報,含接好的四項與閘結果
  <OUT>/summary_<YYYY-MM>.txt      —— 一頁摘要:各類宗數、候選家數、前十家

用法:
  python scan_forced_selling.py 2026-07
  python scan_forced_selling.py 2026-08
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(r"C:\projects\Karst")
SUBMISSIONS_DIR = REPO / "data" / "sec" / "submissions"
ENTITIES_PATH = REPO / "data" / "universe" / "entities.parquet"
TICKER_PERIODS_PATH = REPO / "data" / "universe" / "ticker_periods.parquet"
PRICES_DIR = REPO / "data" / "prices" / "daily"
SPY_CSV = REPO / "data" / "prices" / "spy_daily.csv"
OUT_DIR = Path(__file__).resolve().parent

TOOLS_DIR = REPO / "strategy" / "tools"
sys.path.insert(0, str(TOOLS_DIR))
import implied_expectations as ie  # noqa: E402  只讀不改,只用取數層函數

# ---------------------------------------------------------------- 七類申報分類(原封搬自原型)
FORM10_FORMS = {"10-12B", "10-12B/A", "10-12G", "10-12G/A"}
S4_425_FORMS = {"S-4", "S-4/A", "425"}
FORM_8A_FORMS = {"8-A12B"}
SC13D_FORMS = {"SC 13D", "SC 13D/A", "SCHEDULE 13D", "SCHEDULE 13D/A"}

CAT_NAMES = {
    1: "Form 10(分拆登記 10-12B/10-12G)",
    2: "8-K Item 1.03(破產)",
    3: "8-K Item 3.01(退市 / 不合規通知)",
    4: "8-K Item 2.01(完成收購或處置)",
    5: "S-4/425(換股合併文件)",
    6: "8-A12B(新上市登記)",
    7: "SC 13D / SC 13D/A(大股東異動,只計數)",
}

# ①兩道閘(與 build_events.py 同口徑)
DEBT_TO_OCF_MAX = 3.0
IMPACT_WINDOW = 20     # 申報日前後各 20 個交易日
VOLUME_WINDOW = 60     # 近 60 個交易日中位成交額
CANDIDATE_DROP = -0.15  # 衝擊期相對 SPY 跌幅門檻

OCF_TAGS = [
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
]


def month_window(yyyymm: str) -> tuple[str, str]:
    y, m = int(yyyymm[:4]), int(yyyymm[5:7])
    start = dt.date(y, m, 1)
    if m == 12:
        end = dt.date(y, 12, 31)
    else:
        end = dt.date(y, m + 1, 1) - dt.timedelta(days=1)
    return start.isoformat(), end.isoformat()


def classify(form: str, items: str) -> list[int]:
    cats = []
    item_list = [i.strip() for i in items.split(",")] if items else []
    if form in FORM10_FORMS:
        cats.append(1)
    if form == "8-K" and "1.03" in item_list:
        cats.append(2)
    if form == "8-K" and "3.01" in item_list:
        cats.append(3)
    if form == "8-K" and "2.01" in item_list:
        cats.append(4)
    if form in S4_425_FORMS:
        cats.append(5)
    if form in FORM_8A_FORMS:
        cats.append(6)
    if form in SC13D_FORMS:
        cats.append(7)
    return cats


def scan_filings(window_start: str, window_end: str) -> tuple[list[dict], int, str, int]:
    """回傳 (逐宗申報列表[不含 SC13D], SC13D 宗數, 快取內最新申報日, 掃描公司數)。"""
    rows: list[dict] = []
    sc13d_count = 0
    company_count = 0
    latest_seen = ""

    for fp in sorted(SUBMISSIONS_DIR.glob("*.json")):
        company_count += 1
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            continue

        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        items_list = recent.get("items", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        name = data.get("name", "")
        cik = data.get("cik", "")  # 已是 10 位補零字串,即 entity_id
        tickers_field = ";".join(data.get("tickers", []) or [])

        for i in range(len(forms)):
            filing_date = dates[i] if i < len(dates) else ""
            if filing_date > latest_seen:
                latest_seen = filing_date
            if not (window_start <= filing_date <= window_end):
                continue

            form = forms[i] if i < len(forms) else ""
            items = items_list[i] if i < len(items_list) else ""
            accession = accessions[i] if i < len(accessions) else ""
            primary_doc = primary_docs[i] if i < len(primary_docs) else ""

            cats = classify(form, items)
            if not cats:
                continue

            for cat in cats:
                if cat == 7:
                    sc13d_count += 1
                    continue
                rows.append({
                    "category": cat,
                    "form": form,
                    "items": items,
                    "filingDate": filing_date,
                    "cik": cik,
                    "name": name,
                    "tickers_field": tickers_field,
                    "accessionNumber": accession,
                    "primaryDocument": primary_doc,
                })

    return rows, sc13d_count, latest_seen, company_count


# ---------------------------------------------------------------- 實體與代號
def load_entity_lookup() -> pd.DataFrame:
    return pd.read_parquet(ENTITIES_PATH, columns=["entity_id", "name", "primary_ticker", "approx_mcap_usd"])


def load_ticker_periods() -> pd.DataFrame:
    df = pd.read_parquet(TICKER_PERIODS_PATH)
    df["valid_from_ts"] = pd.to_datetime(df["valid_from"], errors="coerce")
    df["valid_to_ts"] = pd.to_datetime(df["valid_to"], errors="coerce")
    return df


def resolve_ticker(entity_id: str, filing_date: str, ent_df: pd.DataFrame, tp_df: pd.DataFrame) -> str:
    fd = pd.Timestamp(filing_date)
    hits = tp_df[(tp_df["entity_id"] == entity_id)
                 & (tp_df["valid_from_ts"] <= fd)
                 & ((tp_df["valid_to_ts"].isna()) | (tp_df["valid_to_ts"] >= fd))]
    if len(hits):
        return str(hits.iloc[0]["ticker"])
    row = ent_df[ent_df["entity_id"] == entity_id]
    if len(row) and pd.notna(row.iloc[0]["primary_ticker"]):
        return str(row.iloc[0]["primary_ticker"])
    return ""


# ---------------------------------------------------------------- 價格庫(只讀已凍結的日線)
def load_price_panel() -> pd.DataFrame:
    parts = sorted(PRICES_DIR.glob("part_*.parquet"))
    cols = ["entity_id", "date", "adj_close", "volume", "series_role"]
    frames = []
    for p in parts:
        d = pd.read_parquet(p, columns=cols)
        d = d[d["series_role"] == "primary"].drop(columns=["series_role"])
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["adj_close"])
    df = df.sort_values(["entity_id", "date"], kind="stable").reset_index(drop=True)
    return df


def load_spy() -> pd.DataFrame:
    spy = pd.read_csv(SPY_CSV, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    return spy[["date", "adj_close"]].rename(columns={"adj_close": "spy_adj"})


def price_metrics(entity_id: str, filing_date: str, px: pd.DataFrame) -> dict:
    """算衝擊期相對 SPY 跌幅與近 60 日中位成交額。px 已含 spy_adj 欄、已按 entity_id+date 排序。"""
    sub = px[px["entity_id"] == entity_id]
    if sub.empty:
        return {"has_price": False, "impact_rel_pct": None, "median_vol_60d": None, "price_note": "實體不在日線價格庫"}

    sub = sub.reset_index(drop=True)
    fd = pd.Timestamp(filing_date)
    # 申報日或之後最近一個交易日的位置
    pos_arr = sub.index[sub["date"] >= fd]
    if len(pos_arr) == 0:
        return {"has_price": False, "impact_rel_pct": None, "median_vol_60d": None, "price_note": "申報日之後無日線(資料未覆蓋到)"}
    idx0 = pos_arr[0]

    idx_before = idx0 - IMPACT_WINDOW
    idx_after = idx0 + IMPACT_WINDOW
    if idx_before < 0 or idx_after >= len(sub):
        impact = None
        note = "衝擊期視窗不足 ±%d 個交易日" % IMPACT_WINDOW
    else:
        rel = sub["adj_close"] / sub["spy_adj"]
        impact = float(rel.iloc[idx_after] / rel.iloc[idx_before] - 1.0)
        note = ""

    vol_start = max(0, idx0 - VOLUME_WINDOW + 1)
    vol_window = sub["volume"].iloc[vol_start: idx0 + 1]
    median_vol = float(vol_window.median()) if len(vol_window) else None
    if len(vol_window) < VOLUME_WINDOW:
        note = (note + "；" if note else "") + "成交額視窗不足 %d 個交易日,樣本 %d 日" % (VOLUME_WINDOW, len(vol_window))

    return {"has_price": True, "impact_rel_pct": impact, "median_vol_60d": median_vol, "price_note": note}


# ---------------------------------------------------------------- 現金流與負債(implied_expectations 取數層)
_facts_cache: dict[str, dict] = {}


def cfo_and_debt(cik: str) -> dict:
    """呼叫 implied_expectations.py 的低層函數:load_facts / duration_series /
    quarterize / ttm / interest_bearing_debt。不呼叫 build_financials()/analyse()
    (那兩個會連網抓 yfinance 現價與十年期美債,逐宗掃太慢且與本票無關)。"""
    out = {"ocf_ttm": None, "ocf_positive": None, "debt": None,
           "debt_to_ocf": None, "gate_cashflow": None, "gate_debt": None,
           "fin_note": ""}
    try:
        if cik in _facts_cache:
            facts = _facts_cache[cik]
        else:
            facts = ie.load_facts(cik)
            _facts_cache[cik] = facts
    except (FileNotFoundError, OSError):
        out["fin_note"] = "無 companyfacts 快取"
        return out

    try:
        ocf_q = ie.quarterize(ie.duration_series(facts, OCF_TAGS))
        if not ocf_q:
            out["fin_note"] = "無經營現金流標籤"
            return out
        asof = max(ocf_q)
        ocf_ttm, _ = ie.ttm(ocf_q, asof)
        if ocf_ttm is None:
            out["fin_note"] = "經營現金流不足四季,算不出 TTM"
            return out
        out["ocf_ttm"] = ocf_ttm
        out["ocf_positive"] = ocf_ttm > 0

        notes: list[str] = []
        debt, _detail = ie.interest_bearing_debt(facts, asof, notes)
        out["debt"] = debt
        out["fin_note"] = "；".join(notes)

        if ocf_ttm > 0:
            out["debt_to_ocf"] = debt / ocf_ttm
        out["gate_cashflow"] = bool(out["ocf_positive"])
        out["gate_debt"] = bool(out["debt_to_ocf"] is not None and out["debt_to_ocf"] <= DEBT_TO_OCF_MAX)
    except Exception as e:  # noqa: BLE001  逐宗掃描,單宗出錯不可整個腳本死
        out["fin_note"] = "取數失敗:%s" % e
    return out


def main():
    if len(sys.argv) != 2:
        print("用法:python scan_forced_selling.py 2026-07")
        sys.exit(1)
    yyyymm = sys.argv[1]
    window_start, window_end = month_window(yyyymm)

    print("[1/5] 掃 EDGAR 申報快取 %s ~ %s" % (window_start, window_end))
    rows, sc13d_count, latest_seen, company_count = scan_filings(window_start, window_end)
    print("      七類申報(不含 SC13D)行數:%d,SC13D 宗數:%d" % (len(rows), sc13d_count))

    print("[2/5] 讀實體表與代號歷史對照")
    ent_df = load_entity_lookup()
    tp_df = load_ticker_periods()
    entity_ids = set(ent_df["entity_id"])

    print("[3/5] 讀日線價格庫並接 SPY")
    px = load_price_panel()
    spy = load_spy()
    px = px.merge(spy, on="date", how="inner")
    px = px.sort_values(["entity_id", "date"], kind="stable").reset_index(drop=True)

    print("[4/5] 逐宗接實體/價格/現金流/負債(%d 宗)" % len(rows))
    out_rows = []
    for i, r in enumerate(rows):
        cik = r["cik"]
        in_entities = cik in entity_ids
        ticker = resolve_ticker(cik, r["filingDate"], ent_df, tp_df) if in_entities else ""

        pm = price_metrics(cik, r["filingDate"], px) if in_entities else \
            {"has_price": False, "impact_rel_pct": None, "median_vol_60d": None, "price_note": "CIK 不在實體表"}

        fd_metrics = cfo_and_debt(cik)

        gate1 = fd_metrics["gate_cashflow"]
        gate2 = fd_metrics["gate_debt"]
        both_gates = bool(gate1) and bool(gate2)
        impact = pm["impact_rel_pct"]
        drop_enough = impact is not None and impact <= CANDIDATE_DROP
        candidate = bool(both_gates and drop_enough)

        out_rows.append({
            "category": r["category"],
            "category_name": CAT_NAMES[r["category"]],
            "form": r["form"],
            "items": r["items"],
            "filingDate": r["filingDate"],
            "cik": cik,
            "name": r["name"],
            "ticker": ticker,
            "in_entity_table": in_entities,
            "has_price": pm["has_price"],
            "impact_rel_pct_20d": impact,
            "median_vol_60d": pm["median_vol_60d"],
            "price_note": pm["price_note"],
            "ocf_ttm": fd_metrics["ocf_ttm"],
            "ocf_positive": fd_metrics["ocf_positive"],
            "debt": fd_metrics["debt"],
            "debt_to_ocf": fd_metrics["debt_to_ocf"],
            "gate_cashflow_pass": gate1,
            "gate_debt_pass": gate2,
            "candidate": candidate,
            "fin_note": fd_metrics["fin_note"],
            "accessionNumber": r["accessionNumber"],
            "primaryDocument": r["primaryDocument"],
        })
        if (i + 1) % 100 == 0:
            print("      ...已處理 %d/%d" % (i + 1, len(rows)))

    out_rows.sort(key=lambda x: (x["category"], x["filingDate"]))

    csv_path = OUT_DIR / ("candidates_%s.csv" % yyyymm)
    fieldnames = list(out_rows[0].keys()) if out_rows else [
        "category", "category_name", "form", "items", "filingDate", "cik", "name",
        "ticker", "in_entity_table", "has_price", "impact_rel_pct_20d", "median_vol_60d",
        "price_note", "ocf_ttm", "ocf_positive", "debt", "debt_to_ocf",
        "gate_cashflow_pass", "gate_debt_pass", "candidate", "fin_note",
        "accessionNumber", "primaryDocument",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)

    print("[5/5] 寫摘要")
    counts_by_cat = {c: 0 for c in range(1, 7)}
    for r in out_rows:
        counts_by_cat[r["category"]] += 1

    candidates = [r for r in out_rows if r["candidate"]]
    candidates_sorted = sorted(
        candidates,
        key=lambda x: (x["impact_rel_pct_20d"] if x["impact_rel_pct_20d"] is not None else 0.0),
    )
    top10 = candidates_sorted[:10]

    lines = []
    lines.append("①被迫賣個案每月候選來源掃描 —— %s" % yyyymm)
    lines.append("申報窗口:%s ~ %s" % (window_start, window_end))
    lines.append("本地申報快取公司數:%d;快取內任何表格最新申報日:%s" % (company_count, latest_seen))
    lines.append("")
    lines.append("各類宗數:")
    for c in range(1, 7):
        lines.append("  %d. %s:%d" % (c, CAT_NAMES[c], counts_by_cat[c]))
    lines.append("  7. %s:%d" % (CAT_NAMES[7], sc13d_count))
    lines.append("")
    n_in_entity = sum(1 for r in out_rows if r["in_entity_table"])
    n_has_price = sum(1 for r in out_rows if r["has_price"])
    n_gate_both = sum(1 for r in out_rows if r["gate_cashflow_pass"] and r["gate_debt_pass"])
    lines.append("接得上實體表:%d / %d 宗;接得上日線價格庫:%d 宗" % (n_in_entity, len(out_rows), n_has_price))
    lines.append("兩道閘皆過(現金流>0 且 負債/經營現金流<=%.1f):%d 宗" % (DEBT_TO_OCF_MAX, n_gate_both))
    lines.append("候選(兩閘皆過 且 衝擊期相對 SPY 跌幅 <= %.0f%%):%d 宗" % (CANDIDATE_DROP * 100, len(candidates)))
    lines.append("")
    lines.append("候選前十家(按衝擊期相對 SPY 跌幅由大至小排):")
    if top10:
        for r in top10:
            lines.append("  %s(%s)%s  申報日 %s  衝擊期跌幅 %.1f%%  負債/OCF %.2f" % (
                r["name"], r["ticker"] or "無代號", CAT_NAMES[r["category"]],
                r["filingDate"], (r["impact_rel_pct_20d"] or 0) * 100, r["debt_to_ocf"] or 0.0,
            ))
    else:
        lines.append("  (本月無候選)")
    lines.append("")
    lines.append("CSV:%s" % csv_path.name)

    summary_path = OUT_DIR / ("summary_%s.txt" % yyyymm)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
