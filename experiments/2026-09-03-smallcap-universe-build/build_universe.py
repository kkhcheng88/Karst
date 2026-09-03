"""KARST-167 步驟四:由申報索引建實體表、代號時段表與小型股宇宙 v0 名單。

規則正本住 data/universe/RULES.md(跑數之前已獨立 commit),本腳本只是照它執行。
主鍵 entity_id = CIK(D-153);代號只是帶時段的別名。

產物:
  data/universe/entities.parquet
  data/universe/ticker_periods.parquet
  data/universe/universe_smallcap_v0.csv
  data/universe/manifest.json
  experiments/2026-09-03-smallcap-universe-build/out/*.csv|json(盤點表與底稿)
"""

from __future__ import annotations

import glob
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta

import pandas as pd
import requests

REPO = r"C:\projects\Karst"
CACHE = os.path.join(REPO, "data", "sec", "submissions")
MANIFEST = os.path.join(CACHE, "manifest.jsonl")
UNIVERSE = os.path.join(REPO, "data", "universe")
OUT = os.path.join(REPO, "experiments", "2026-09-03-smallcap-universe-build", "out")
UA = "Casy Limited kaho.career@gmail.com"

MAIN_EXCHANGES = {"NYSE", "NASDAQ", "NYSEAMER", "NYSE AMERICAN", "AMEX", "CBOE", "BATS", "NYSEARCA"}
LISTED_EXCHANGES = {"NYSE", "NASDAQ", "NYSEAMER", "NYSE AMERICAN", "AMEX", "CBOE"}
ANNUAL_FORMS = {"10-K", "10-K405", "10-KSB", "10-KSB405", "20-F", "40-F", "10-K/A", "20-F/A", "40-F/A"}
FOREIGN_FORMS = {"20-F", "40-F", "20-F/A", "40-F/A", "6-K"}
EXCLUDED_SIC = {"6722", "6726", "6189"}
BLANK_CHECK_SIC = "6770"
ALIAS_DROP = re.compile(r"-(P[A-Z]?|W[SI]?|R|U)$")
SMALLCAP_THRESHOLD = 5_000_000_000.0
ACTIVE_DAYS = 400

# KARST-165 人手核:代號重用(前手 -> 後手)。規則正本 RULES.md 第五節。
MANUAL_REUSE = [
    {"ticker": "CPWR", "prior_cik": "0000859014", "current_cik": "0000827099",
     "prior_name": "Compuware Corp", "current_name": "Ocean Thermal Energy Corp",
     "cut": None,  # 前手已停止申報,用它的最後申報日
     "cut_basis": "Compuware(CIK 0000859014)最後申報日,取自 EDGAR 申報索引",
     "note": "KARST-165 確證:Compuware 2014 年私有化後停止申報,代號其後由 Ocean Thermal Energy 使用"},
    {"ticker": "EP", "prior_cik": "0001066107", "current_cik": "0000887396",
     "prior_name": "El Paso Corp/DE", "current_name": "Empire Petroleum Corp",
     "cut": "2012-05-25",
     "cut_basis": "KARST-165 記的 El Paso 成分期離場日(被 Kinder Morgan 收購);"
                  "CIK 0001066107 至今仍以債券發行人身分申報,所以不可用最後申報日",
     "note": "KARST-165 確證:El Paso 2012 年被 Kinder Morgan 收購,代號其後由 Empire Petroleum 使用"},
    {"ticker": "PARA", "prior_cik": "0000813828", "current_cik": "0001826011",
     "prior_name": "Paramount Global", "current_name": "Banzai International",
     "cut": "2025-08-08",
     "cut_basis": "KARST-165 記的 Paramount 成分期離場日(與 Skydance 合併改代號 PSKY);"
                  "CIK 0000813828 至今仍在申報,所以不可用最後申報日",
     "note": "KARST-165 確證:Paramount 與 Skydance 合併後改代號 PSKY(新 CIK 0002041610),PARA 由另一實體使用"},
    {"ticker": "SUN", "prior_cik": "0000095304", "current_cik": "0001552275",
     "prior_name": "Sunoco Inc", "current_name": "Sunoco LP",
     "cut": None,
     "cut_basis": "Sunoco Inc(CIK 0000095304)最後申報日,取自 EDGAR 申報索引",
     "note": "KARST-165 嫌疑六宗之一,人手核為兩個不同法律實體:Sunoco Inc 與 Sunoco LP"},
]
# KARST-165 嫌疑六宗之中今日已無持有人的五個,只記錄不建段
SUSPECT_NO_HOLDER = ["COV", "MEE", "RAI", "RTN", "WRK"]


def cache_path(cik: str) -> str:
    return os.path.join(CACHE, f"CIK{cik}.json")


def ensure_submission(cik: str, session: requests.Session) -> dict | None:
    """人手核用的舊 CIK 未必在今日代號表內;缺就補抓一份入單一快取連 manifest。"""
    path = cache_path(cik)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    time.sleep(0.15)
    resp = session.get(f"https://data.sec.gov/submissions/CIK{cik}.json", timeout=60)
    if resp.status_code != 200:
        print(f"  manual cik {cik} http{resp.status_code}", flush=True)
        return None
    with open(path, "wb") as fh:
        fh.write(resp.content)
    obj = json.loads(resp.content)
    import hashlib
    with open(MANIFEST, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "cik": cik, "file": f"CIK{cik}.json", "name": obj.get("name"),
            "entityType": obj.get("entityType"), "sic": obj.get("sic"),
            "tickers": obj.get("tickers"), "exchanges": obj.get("exchanges"),
            "url": f"https://data.sec.gov/submissions/CIK{cik}.json",
            "bytes": len(resp.content), "sha256": hashlib.sha256(resp.content).hexdigest(),
            "fetchedAt": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fetchedBy": "KARST-167 universe-167", "source": "edgar",
        }, ensure_ascii=False) + "\n")
    return obj


def summarise(obj: dict) -> dict:
    recent = obj.get("filings", {}).get("recent", {}) or {}
    dates = [d for d in (recent.get("filingDate") or []) if d]
    forms = [f for f in (recent.get("form") or []) if f]
    files = obj.get("filings", {}).get("files", []) or []
    first_candidates = [d for d in dates]
    last_candidates = [d for d in dates]
    for blk in files:
        if blk.get("filingFrom"):
            first_candidates.append(blk["filingFrom"])
        if blk.get("filingTo"):
            last_candidates.append(blk["filingTo"])
    addresses = obj.get("addresses") or {}
    business = addresses.get("business") or {}
    tickers = [t for t in (obj.get("tickers") or []) if t]
    exchanges = obj.get("exchanges") or []
    pairs = []
    for i, tkr in enumerate(obj.get("tickers") or []):
        exch = exchanges[i] if i < len(exchanges) else None
        if tkr:
            pairs.append((str(tkr).upper().strip(), (exch or "").upper().strip()))
    former = obj.get("formerNames") or []
    return {
        "entity_id": str(obj.get("cik")).zfill(10),
        "name": obj.get("name"),
        "entity_type": obj.get("entityType"),
        "sic": str(obj.get("sic") or "").strip(),
        "sic_description": obj.get("sicDescription"),
        "state_of_incorporation": obj.get("stateOfIncorporation"),
        "country": business.get("country") or business.get("stateOrCountry"),
        "fiscal_year_end": obj.get("fiscalYearEnd"),
        "category": obj.get("category"),
        "tickers": [p[0] for p in pairs],
        "exchanges": [p[1] for p in pairs],
        "ticker_pairs": pairs,
        "n_former_names": len(former),
        "first_filing_date": min(first_candidates) if first_candidates else None,
        "last_filing_date": max(last_candidates) if last_candidates else None,
        "has_annual_report": bool(ANNUAL_FORMS & set(forms)),
        "is_foreign_filer": bool(FOREIGN_FORMS & set(forms)),
        "n_filings_recent": len(dates),
    }


def main() -> int:
    os.makedirs(UNIVERSE, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    today = date.today()
    active_cutoff = (today - timedelta(days=ACTIVE_DAYS)).isoformat()

    with open(os.path.join(REPO, "data", "sec", "company_tickers.json"), "r", encoding="utf-8") as fh:
        tmap = json.load(fh)
    ciks = sorted(set(tmap.values()))
    print(f"unique_cik={len(ciks)}", flush=True)

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Encoding": "gzip, deflate"})

    records: list[dict] = []
    missing: list[str] = []
    for cik in ciks:
        path = cache_path(cik)
        if not os.path.exists(path):
            missing.append(cik)
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                obj = json.load(fh)
        except Exception:  # noqa: BLE001
            missing.append(cik)
            continue
        records.append(summarise(obj))
    print(f"loaded={len(records)} missing_submissions={len(missing)}", flush=True)

    frame = pd.DataFrame(records)

    # ---- 收錄與剔除(RULES.md 第二、三節)----
    def keep_aliases(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
        return [p for p in pairs if not ALIAS_DROP.search(p[0])]

    frame["kept_pairs"] = frame["ticker_pairs"].apply(keep_aliases)
    frame["listed_pairs"] = frame["kept_pairs"].apply(
        lambda ps: [p for p in ps if p[1] in LISTED_EXCHANGES])
    frame["i1_has_ticker"] = frame["ticker_pairs"].apply(len) > 0
    frame["i2_main_exchange"] = frame["listed_pairs"].apply(len) > 0
    frame["i3_annual_report"] = frame["has_annual_report"]
    # RULES.md v0.1 更正:外國申報人(ADR)的 entityType 是 "other" 不是 "operating",
    # 原 I4 會把全部 ADR 剔走,與票面「收美國交易所上市普通股與 ADR」直接衝突。
    frame["i4_operating"] = frame["entity_type"].fillna("").isin(["operating", "other"])
    frame["e1_fund_sic"] = frame["sic"].isin(EXCLUDED_SIC)
    frame["e2_blank_check"] = frame["sic"] == BLANK_CHECK_SIC
    frame["e3_no_listed_exchange"] = ~frame["i2_main_exchange"]
    frame["included"] = (
        frame["i1_has_ticker"] & frame["i2_main_exchange"]
        & frame["i3_annual_report"] & frame["i4_operating"]
        & ~frame["e1_fund_sic"] & ~frame["e2_blank_check"]
    )

    gate_counts = {
        "unique_cik_in_ticker_map": len(ciks),
        "submissions_loaded": int(len(frame)),
        "submissions_missing": len(missing),
        "I1_has_ticker": int(frame["i1_has_ticker"].sum()),
        "I2_main_exchange": int(frame["i2_main_exchange"].sum()),
        "I3_annual_report": int(frame["i3_annual_report"].sum()),
        "I4_operating_or_other": int(frame["i4_operating"].sum()),
        "I4_dropped_investment_type": int((frame["i2_main_exchange"] & ~frame["i4_operating"]).sum()),
        "E1_fund_sic_dropped": int((frame["e1_fund_sic"] & frame["i2_main_exchange"]).sum()),
        "E2_blank_check_dropped": int((frame["e2_blank_check"] & frame["i2_main_exchange"]).sum()),
        "E3_no_listed_exchange_dropped": int(frame["e3_no_listed_exchange"].sum()),
        "E4_alias_dropped": int(sum(len(a) - len(b) for a, b in
                                    zip(frame["ticker_pairs"], frame["kept_pairs"]))),
        "included": int(frame["included"].sum()),
    }
    print(json.dumps(gate_counts, ensure_ascii=False), flush=True)

    dropped_cols = ["entity_id", "name", "entity_type", "sic", "sic_description",
                    "first_filing_date", "last_filing_date"]
    frame.loc[frame["e2_blank_check"] & frame["i2_main_exchange"], dropped_cols].to_csv(
        os.path.join(OUT, "dropped_blank_check_sic6770.csv"), index=False)
    frame.loc[frame["e1_fund_sic"] & frame["i2_main_exchange"], dropped_cols].to_csv(
        os.path.join(OUT, "dropped_fund_sic.csv"), index=False)
    frame.loc[frame["i2_main_exchange"] & ~frame["i4_operating"], dropped_cols].to_csv(
        os.path.join(OUT, "dropped_not_operating.csv"), index=False)
    frame.loc[frame["i2_main_exchange"] & frame["i4_operating"]
              & ~frame["i3_annual_report"], dropped_cols].to_csv(
        os.path.join(OUT, "dropped_no_annual_report.csv"), index=False)

    kept = frame.loc[frame["included"]].copy()
    def pick_primary(pairs):
        # 普通股一般是最短那個代號:同一家公司的權證/單位代號是在它後面加字母
        return sorted(pairs, key=lambda p: (len(p[0]), p[0]))[0]

    kept["primary_ticker"] = kept["listed_pairs"].apply(lambda ps: pick_primary(ps)[0])
    kept["exchange"] = kept["listed_pairs"].apply(lambda ps: pick_primary(ps)[1])
    kept["all_tickers"] = kept["listed_pairs"].apply(lambda ps: "|".join(p[0] for p in ps))
    kept["multi_class"] = kept["listed_pairs"].apply(len) > 1
    kept["filing_status"] = kept["last_filing_date"].apply(
        lambda d: "active" if (d or "") >= active_cutoff else "ceased")
    kept["first_filing_year"] = kept["first_filing_date"].str.slice(0, 4)

    # ---- 封面頁股數(RULES.md 第六節)----
    shares_path = os.path.join(OUT, "cover_shares.json")
    shares_latest: dict[str, float] = {}
    shares_period: dict[str, str] = {}
    scale_suspect: set[str] = set()
    if os.path.exists(shares_path):
        with open(shares_path, "r", encoding="utf-8") as fh:
            blob = json.load(fh)
        order = [q for q in blob["quarters"] if q in blob["data"]]
        for q in order:  # 由最近一季往回
            for cik, val in blob["data"][q].items():
                if cik not in shares_latest and val and val > 0:
                    shares_latest[cik] = float(val)
                    shares_period[cik] = q
        # 一千倍刻度檢查:同一 CIK 相鄰兩季相差一千倍以上
        for cik, latest in shares_latest.items():
            for q in order:
                other = blob["data"][q].get(cik)
                if not other or other <= 0 or q == shares_period[cik]:
                    continue
                ratio = latest / other
                if ratio >= 1000 or ratio <= 1 / 1000:
                    scale_suspect.add(cik)
                break
    else:
        print("WARNING cover_shares.json missing", flush=True)

    kept["shares_outstanding"] = kept["entity_id"].map(shares_latest)
    kept["shares_period"] = kept["entity_id"].map(shares_period)
    kept["has_shares"] = kept["shares_outstanding"].notna()
    kept["shares_scale_suspect"] = kept["entity_id"].isin(scale_suspect)

    # ---- 現價快照 ----
    snaps = sorted(glob.glob(os.path.join(UNIVERSE, "price_snapshot_*.csv")))
    if snaps:
        prices = pd.read_csv(snaps[-1])
        price_map = dict(zip(prices["ticker"].astype(str), prices["close"].astype(float)))
        date_map = dict(zip(prices["ticker"].astype(str), prices["price_date"].astype(str)))
        snapshot_file = os.path.basename(snaps[-1])
    else:
        price_map, date_map, snapshot_file = {}, {}, None
        print("WARNING price snapshot missing", flush=True)
    kept["price"] = kept["primary_ticker"].map(price_map)
    kept["price_date"] = kept["primary_ticker"].map(date_map)
    kept["has_price"] = kept["price"].notna()
    kept["approx_mcap_usd"] = kept["shares_outstanding"] * kept["price"]
    kept["is_smallcap"] = kept["approx_mcap_usd"] < SMALLCAP_THRESHOLD
    # 荒謬細的近似市值多數是股數單位錯格或者價格對錯代號,標出來不自動修
    kept["mcap_implausible"] = kept["approx_mcap_usd"] < 1_000_000
    # v0 規則(RULES.md E1)只剔 6722/6726/6189,漏了商品與加密貨幣信託型 ETP(SIC 6221)。
    # 規則已凍結,所以這裡只標旗不剔走,並在報告列出家數,留給 v1 修。
    kept["etp_suspect"] = kept["sic"] == "6221"

    entity_cols = [
        "entity_id", "name", "primary_ticker", "all_tickers", "exchange", "sic",
        "sic_description", "state_of_incorporation", "country", "category",
        "first_filing_date", "last_filing_date", "first_filing_year", "filing_status",
        "is_foreign_filer", "multi_class", "n_former_names",
        "shares_outstanding", "shares_period", "has_shares", "shares_scale_suspect",
        "price", "price_date", "has_price", "approx_mcap_usd", "is_smallcap",
        "mcap_implausible", "etp_suspect",
    ]
    entities = kept.loc[:, entity_cols].sort_values("entity_id").reset_index(drop=True)
    entities.to_parquet(os.path.join(UNIVERSE, "entities.parquet"), index=False)

    # ---- 代號時段表(RULES.md 第五節)----
    periods: list[dict] = []
    for row in kept.itertuples(index=False):
        vto = row.last_filing_date if row.filing_status == "ceased" else None
        for tkr, exch in row.listed_pairs:
            periods.append({
                "ticker": tkr, "entity_id": row.entity_id, "exchange": exch,
                "valid_from": row.first_filing_date, "valid_to": vto,
                "in_universe": True,
                "source": "sec_snapshot", "confidence": "low",
                "note": "由今日代號快照與該實體申報期外推;不是查證的代號歷史",
            })

    manual_rows: list[dict] = []
    conflicts: list[dict] = []
    for case in MANUAL_REUSE:
        prior = ensure_submission(case["prior_cik"], session)
        if prior is None:
            conflicts.append({"ticker": case["ticker"], "issue": "prior submissions unavailable"})
            continue
        psum = summarise(prior)
        prior_from = psum["first_filing_date"]
        prior_to = case["cut"] or psum["last_filing_date"]
        cur = [p for p in periods if p["ticker"] == case["ticker"]
               and p["entity_id"] == case["current_cik"]]
        cut = (datetime.fromisoformat(prior_to) + timedelta(days=1)).date().isoformat()
        handover_note = (
            case["note"] + f";切斷點依據:{case['cut_basis']};"
            "後手的生效起是**下限**(前手釋出代號那日),真正接手日沒有免費正本"
        )
        for p in cur:
            if p["valid_from"] < cut:
                p["valid_from"] = cut
            p["source"] = "manual_karst165"
            p["confidence"] = "manual"
            p["note"] = handover_note
        if not cur:
            # 後手不在 v0 宇宙(例如已轉場外),照樣登記這一段,只是標明不在名單內
            cobj = ensure_submission(case["current_cik"], session)
            csum = summarise(cobj) if cobj else None
            conflicts.append({
                "ticker": case["ticker"],
                "issue": f"current holder {case['current_cik']} 不在 v0 宇宙名單內(未過收錄關),"
                         "代號時段照樣拆段登記",
            })
            manual_rows.append({
                "ticker": case["ticker"], "entity_id": case["current_cik"], "exchange": "",
                "valid_from": cut,
                "valid_to": (csum["last_filing_date"] if csum and
                             (csum["last_filing_date"] or "") < active_cutoff else None),
                "in_universe": False,
                "source": "manual_karst165", "confidence": "manual",
                "note": handover_note + f";後手 {case['current_name']},不在 v0 宇宙名單內",
            })
        manual_rows.append({
            "ticker": case["ticker"], "entity_id": case["prior_cik"], "exchange": "",
            "valid_from": prior_from, "valid_to": prior_to,
            "in_universe": False,
            "source": "manual_karst165", "confidence": "manual",
            "note": handover_note + f";前手 {case['prior_name']},不在 v0 宇宙名單內",
        })
    periods.extend(manual_rows)

    tp = pd.DataFrame(periods)
    tp = tp.sort_values(["ticker", "valid_from"]).reset_index(drop=True)
    # 無重疊檢查
    overlaps = []
    for tkr, blk in tp.groupby("ticker"):
        blk = blk.sort_values("valid_from")
        prev_to, prev_id = None, None
        for r in blk.itertuples(index=False):
            if prev_to is not None and r.valid_from <= prev_to:
                overlaps.append({"ticker": tkr, "entity_a": prev_id, "entity_b": r.entity_id,
                                 "prev_valid_to": prev_to, "next_valid_from": r.valid_from})
            prev_to = r.valid_to if r.valid_to else "9999-12-31"
            prev_id = r.entity_id
    print(f"ticker_periods={len(tp)} overlaps={len(overlaps)}", flush=True)
    tp.to_parquet(os.path.join(UNIVERSE, "ticker_periods.parquet"), index=False)
    pd.DataFrame(overlaps).to_csv(os.path.join(OUT, "ticker_period_overlaps.csv"), index=False)

    # ---- 小型股名單 ----
    small = entities.loc[entities["is_smallcap"].fillna(False)].copy()
    small_cols = ["entity_id", "primary_ticker", "all_tickers", "exchange", "sic",
                  "sic_description", "first_filing_date", "last_filing_date", "filing_status",
                  "approx_mcap_usd", "shares_outstanding", "shares_period", "price",
                  "price_date", "has_price", "has_shares", "shares_scale_suspect",
                  "is_foreign_filer", "multi_class", "mcap_implausible", "etp_suspect", "name"]
    small.loc[:, small_cols].to_csv(
        os.path.join(UNIVERSE, "universe_smallcap_v0.csv"), index=False)

    # ---- 規模盤點 ----
    by_year = entities.groupby("first_filing_year").size().rename("entities").reset_index()
    by_year.to_csv(os.path.join(OUT, "entities_by_first_filing_year.csv"), index=False)
    by_exch = entities.groupby("exchange").size().rename("entities").reset_index()
    by_exch.to_csv(os.path.join(OUT, "entities_by_exchange.csv"), index=False)
    entities["sic2"] = entities["sic"].str.slice(0, 2)
    by_sic = (entities.groupby("sic2").size().rename("entities")
              .reset_index().sort_values("entities", ascending=False))
    by_sic.to_csv(os.path.join(OUT, "entities_by_sic2.csv"), index=False)
    small_by_exch = small.groupby("exchange").size().rename("smallcap").reset_index()
    small_by_exch.to_csv(os.path.join(OUT, "smallcap_by_exchange.csv"), index=False)

    tally = {
        "as_of": today.isoformat(),
        "gates": gate_counts,
        "entities_total": int(len(entities)),
        "filing_status_active": int((entities["filing_status"] == "active").sum()),
        "filing_status_ceased": int((entities["filing_status"] == "ceased").sum()),
        "has_shares": int(entities["has_shares"].sum()),
        "has_price": int(entities["has_price"].sum()),
        "has_both": int((entities["has_shares"] & entities["has_price"]).sum()),
        "mcap_computable": int(entities["approx_mcap_usd"].notna().sum()),
        "smallcap_under_5b": int(len(small)),
        "smallcap_active": int((small["filing_status"] == "active").sum()),
        "foreign_filers": int(entities["is_foreign_filer"].sum()),
        "foreign_filers_with_shares": int(
            (entities["is_foreign_filer"] & entities["has_shares"]).sum()),
        "multi_class": int(entities["multi_class"].sum()),
        "shares_scale_suspect": int(entities["shares_scale_suspect"].sum()),
        "mcap_implausible": int(entities["mcap_implausible"].sum()),
        "etp_suspect": int(entities["etp_suspect"].sum()),
        "smallcap_excluding_etp_suspect": int((~small["etp_suspect"]).sum()),
        "smallcap_etp_suspect": int(small["etp_suspect"].sum()),
        "ticker_periods": int(len(tp)),
        "ticker_period_overlaps": len(overlaps),
        "manual_reuse_cases": len(MANUAL_REUSE),
        "suspects_without_holder": SUSPECT_NO_HOLDER,
        "conflicts": conflicts,
        "price_snapshot_file": snapshot_file,
        "smallcap_threshold_usd": SMALLCAP_THRESHOLD,
    }
    for q in [0.1, 0.25, 0.5, 0.75, 0.9]:
        tally[f"mcap_q{int(q * 100)}"] = float(entities["approx_mcap_usd"].quantile(q))
    buckets = pd.cut(entities["approx_mcap_usd"],
                     [0, 5e7, 3e8, 1e9, 2e9, 5e9, 1e10, 5e10, 1e13],
                     labels=["<0.5億", "0.5-3億", "3-10億", "10-20億", "20-50億",
                             "50-100億", "100-500億", ">500億"])
    tally["mcap_buckets"] = {str(k): int(v) for k, v in buckets.value_counts().sort_index().items()}

    with open(os.path.join(OUT, "tally.json"), "w", encoding="utf-8") as fh:
        json.dump(tally, fh, ensure_ascii=False, indent=2)
    print(json.dumps(tally, ensure_ascii=False, indent=2), flush=True)

    manifest = {
        "produced_by": "KARST-167 universe-167",
        "produced_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rules": "data/universe/RULES.md (v0, 跑數前 commit e8343bb)",
        "primary_key": "entity_id = SEC CIK (10 位補零)",
        "sources": {
            "ticker_map": "data/sec/company_tickers.json (SEC 2026-09-02 快照)",
            "submissions": "data/sec/submissions/ 單一快取連 manifest.jsonl",
            "cover_shares": "SEC XBRL frames dei:EntityCommonStockSharesOutstanding",
            "price": snapshot_file,
        },
        "files": {},
        "counts": {k: tally[k] for k in
                   ["entities_total", "smallcap_under_5b", "ticker_periods",
                    "filing_status_active", "filing_status_ceased"]},
        "known_biases": [
            "缺退市正本:最後申報日只是退市日的代理",
            "基本面回溯只到 2011(XBRL 分階段實施)",
            "市值是近似:封面頁股數 x 一次現價快照",
            "倖存者口徑:名單由今日快照建成,沒有已除牌公司",
        ],
    }
    import hashlib
    for fname in ["entities.parquet", "ticker_periods.parquet", "universe_smallcap_v0.csv",
                  "RULES.md"] + ([snapshot_file] if snapshot_file else []):
        p = os.path.join(UNIVERSE, fname)
        if os.path.exists(p):
            with open(p, "rb") as fh:
                manifest["files"][fname] = {
                    "bytes": os.path.getsize(p),
                    "sha256": hashlib.sha256(fh.read()).hexdigest(),
                }
    with open(os.path.join(UNIVERSE, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    print("manifest written", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
