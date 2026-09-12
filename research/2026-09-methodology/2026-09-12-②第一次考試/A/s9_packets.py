# -*- coding: utf-8 -*-
"""KARST-222 票 A 第九步:逐事件建 T1 遮蔽取證包 `packets/<event_id>.json`。

**必須在 `picks_before_results.md` 落檔之後才跑。** 包內七項照
`strategy/specs/提示詞——改善驅動可持續性判斷-v1.md` 第二節:
  1 事件識別(T0/T1/T2) 2 觸發資料(EX-99.1 全文、同日 8-K 其他項目、逐字稿查不到)
  3 截止前文件(最近 10-K、最近兩份 10-Q,申報日 ≤ T1) 4 財務數列(截止前八季 + g0 + 上一季增速)
  5 同業與行業(同 SIC2 上市同業名單;對手最近年報資本開支節摘錄) 6 價格狀態
  7 共識一律「查不到」

**機械遮蔽**:本檔只寫 T1(反應日收市)或之前的資料;`masking_check` 記包內最晚一份資料日期。
10-K/10-Q 全文不入包,只留本地路徑與 EDGAR 網址(build_packets_new.py 體例)。
本檔不讀 `controls_operating.csv`(對照預測另檔,不入包)。
"""
from __future__ import annotations

import gzip
import html
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

import finlib as F
import pxlib
from buckets import bucket_of

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DOCS = HERE / "edgar_cache"
OUT = HERE / "packets"
SUB = ROOT / "data" / "sec" / "submissions"
UA = {"User-Agent": "Karst research kaho@example.com"}
WORKERS = 1                  # 票面硬規矩:抓取單線程、不平行(亦省記憶體)
_BUNDLES: dict[str, dict] = {}
# 分段抓取:命令列 `fetch <N>` = 只抓文件、本次最多新抓 N 份(長工序拆支跑,不做背景等待)
STAGE = sys.argv[1] if len(sys.argv) > 1 else "all"
FETCH_LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 400
_n_new = [0]


def bundle(cik: str) -> dict:
    """companyfacts 逐家讀,讀過即留(128 家,避免重讀同一個大 JSON)。"""
    if cik not in _BUNDLES:
        _BUNDLES[cik] = F.bundle(cik)
    return _BUNDLES[cik]
RATE_PER_SEC = 3.0          # 與 s5 同一個克制水平,避免再被 SEC 429
_lock = threading.Lock()
_last = [0.0]


def _throttle() -> None:
    with _lock:
        now = time.time()
        wait = _last[0] + 1.0 / RATE_PER_SEC - now
        if wait > 0:
            time.sleep(wait)
            now = _last[0] + 1.0 / RATE_PER_SEC
        _last[0] = now


def strip_html(raw: bytes) -> str:
    t = raw.decode("utf-8", "ignore")
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    t = re.sub(r"(?is)<br\s*/?>", "\n", t)
    t = re.sub(r"(?is)</(p|div|tr|h[1-6]|li)>", "\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\xa0]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t


def get(url: str, timeout: int = 90) -> bytes:
    for a in range(4):
        _throttle()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 503):
                time.sleep((30.0, 90.0, 180.0, 240.0)[a])
                continue
            raise
        except Exception:  # noqa: BLE001
            time.sleep(1.5 * (a + 1))
    raise RuntimeError("retries exhausted %s" % url)


def filing_rows(cik: str) -> list[dict]:
    p = SUB / ("CIK%s.json" % cik)
    if not p.exists():
        return []
    d = json.loads(p.read_text(encoding="utf-8"))
    r = d.get("filings", {}).get("recent", {})
    out = []
    for i in range(len(r.get("form", []))):
        out.append(dict(form=r["form"][i], filingDate=r["filingDate"][i],
                        reportDate=r["reportDate"][i], accn=r["accessionNumber"][i],
                        doc=r["primaryDocument"][i], items=r.get("items", [""])[i]
                        if i < len(r.get("items", [])) else ""))
    out.sort(key=lambda x: x["filingDate"], reverse=True)   # 新到舊,與 EDGAR recent 同序
    return out


def doc_url(cik: str, accn: str, doc: str) -> str:
    return "https://www.sec.gov/Archives/edgar/data/%s/%s/%s" % (
        int(cik), accn.replace("-", ""), doc)


def cached_doc(cik: str, accn: str, doc: str, tag: str) -> tuple[str, str]:
    """抓一份文件並落 edgar_cache;回傳 (本地檔名, 狀態)。"""
    p = DOCS / ("%s__%s.txt.gz" % (accn.replace("-", ""), tag))
    if p.exists():
        return p.name, "已快取"
    with _lock:
        if _n_new[0] >= FETCH_LIMIT:
            return "", "本段額滿"
        _n_new[0] += 1
    try:
        txt = strip_html(get(doc_url(cik, accn, doc)))
    except Exception as e:  # noqa: BLE001
        return "", "抓取失敗:%s" % type(e).__name__
    with gzip.open(p, "wt", encoding="utf-8") as f:
        f.write(txt)
    return p.name, "ok"


def pick_filings(rows: list[dict], cutoff: str) -> dict:
    rows = [x for x in rows if x["filingDate"] <= cutoff]
    out = {}
    k = [x for x in rows if x["form"] in ("10-K", "20-F", "40-F")]
    if k:
        out["annual"] = k[0]
    for j, x in enumerate([x for x in rows if x["form"] in ("10-Q", "6-K")][:2]):
        out["q%d" % j] = x
    return out


def capex_excerpt(txt: str, n: int = 3) -> list[str]:
    hits = []
    for m in re.finditer(r"(?i)capital expenditure", txt):
        a, b = max(0, m.start() - 500), min(len(txt), m.end() + 500)
        w = re.sub(r"\s+", " ", txt[a:b]).strip()
        if re.search(r"\d", w):
            hits.append(w[:700])
        if len(hits) >= n:
            break
    return hits


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    picks = json.loads((CACHE / "picks.json").read_text(encoding="utf-8"))
    pop = pd.read_parquet(CACHE / "population_improvement.parquet")
    meta = pop.set_index("accessionNumber")
    meta["accessionNumber"] = meta.index          # set_index 會拿走該欄,補回供逐列取用
    ent = pd.read_parquet(ROOT / "data" / "universe" / "entities.parquet",
                          columns=["entity_id", "name", "primary_ticker", "sic", "exchange"])

    # ---- 價格狀態(逐檔掃描,見 pxlib.py:2,065 萬列一次過讀入會爆記憶體)
    # 反應日集合由**鎖定清單**(主+後備)取,不依賴後面的補位結果
    ev_dates = {meta.loc[q["acc"], "reaction_date"]
                for kind in ("main", "backup") for q in picks[kind]}
    px_state, first_px = pxlib.state_at(ev_dates)
    key = px_state.set_index(["entity_id", "date"])[["ret6", "ret12", "rank6", "rank12",
                                                     "dist52"]]
    # 60 日中位成交額走勢,供「同業」在**反應日當日**排序用 —— 不可用今日的成交額
    dv_by_date = px_state.set_index(["date", "entity_id"])["dv60"].dropna()
    print("價格狀態:反應日 %d 個、狀態列 %d;有日線的 entity %d"
          % (len(ev_dates), len(px_state), len(first_px)), flush=True)

    # ---- 後備補位:主清單事件若「建不成包」才按後備次序補上(次序 = B01…B44)
    def buildable(m) -> tuple[bool, str]:
        ex = DOCS / ("%s__EX991.txt.gz" % m["accessionNumber"].replace("-", ""))
        if not ex.exists():
            return False, "無觸發 EX-99.1 全文"
        if not m["reaction_date"] or pd.isna(m["ret"]):
            return False, "反應日無成交價"
        b = bundle(m["cik"])
        if not b.get("ok") or not m["signal_q_end"]:
            return False, "無 XBRL 財務數列"
        return True, ""

    # 後備逐個試建(結果與次序無關),不可建者另記原因 —— 不再靜默消耗
    bk_state: dict[str, tuple[bool, str]] = {}
    for b in picks["backup"]:
        bk_state[b["event_id"]] = buildable(meta.loc[b["acc"]])
    bk_bad = [dict(event_id=b["event_id"], acc=b["acc"], year=b["year"], bucket=b["bucket"],
                   reason=bk_state[b["event_id"]][1])
              for b in picks["backup"] if not bk_state[b["event_id"]][0]]
    print("後備不可建 %d 個:%s" % (
        len(bk_bad), [(x["event_id"], x["reason"]) for x in bk_bad]), flush=True)

    final_picks, subs, unbuildable = [], [], []
    used_bk: set[str] = set()
    for p in picks["main"]:
        m = meta.loc[p["acc"]]
        okr, why = buildable(m)
        if okr:
            final_picks.append(p)
            continue
        # 鎖定檔規矩:後備按清單次序補,**同年同桶優先**,之後才按全表次序
        same = [b for b in picks["backup"]
                if b["year"] == p["year"] and b["bucket"] == p["bucket"]
                and b["event_id"] not in used_bk]
        same_ids = {b["event_id"] for b in same}
        cand = same + [b for b in picks["backup"]
                       if b["event_id"] not in used_bk
                       and b["event_id"] not in same_ids]
        placed = False
        for b in cand:
            ok2, why2 = bk_state[b["event_id"]]
            if ok2:
                used_bk.add(b["event_id"])
                nb = dict(b)
                nb["replaces"], nb["replaces_acc"], nb["replace_reason"] = (
                    p["event_id"], p["acc"], why)
                nb["same_year_bucket"] = bool(b["year"] == p["year"]
                                              and b["bucket"] == p["bucket"])
                final_picks.append(nb)
                subs.append(dict(main_event=p["event_id"], main_acc=p["acc"],
                                 main_year=p["year"], main_bucket=p["bucket"],
                                 backup_event=b["event_id"], backup_acc=b["acc"],
                                 backup_year=b["year"], backup_bucket=b["bucket"],
                                 same_year_bucket=nb["same_year_bucket"], reason=why))
                print("補位:%s(%s,%s)→ %s(%s,%s)同年同桶=%s(原因 %s)"
                      % (p["event_id"], p["year"], p["bucket"], b["event_id"],
                         b["year"], b["bucket"], nb["same_year_bucket"], why), flush=True)
                placed = True
                break
        if not placed:
            unbuildable.append(dict(event=p["event_id"], acc=p["acc"], reason=why))
            print("建不成又無後備:%s(%s)" % (p["event_id"], why), flush=True)
    print("主清單 %d;補位 %d(同年同桶 %d);建不成 %d;用剩後備 %d"
          % (len(picks["main"]), len(subs),
             sum(1 for s in subs if s["same_year_bucket"]), len(unbuildable),
             len(picks["backup"]) - len(used_bk)), flush=True)

    # ---- 前置:一次過抓齊最終清單的事件文件(8-K 本體、年報、兩份季報)
    jobs = []
    for p in final_picks:
        m = meta.loc[p["acc"]]
        rows = filing_rows(m["cik"])
        pf = pick_filings(rows, m["reaction_date"])
        jobs.append((p, m, pf))
    uniq: dict[tuple, tuple] = {}
    for _p, m, pf in jobs:
        for k, f in pf.items():
            uniq[(m["cik"], f["accn"], f["doc"], k)] = (m["cik"], f["accn"], f["doc"], k)
        self8k = [r for r in filing_rows(m["cik"]) if r["accn"] == m["accessionNumber"]]
        if self8k:
            uniq[(m["cik"], m["accessionNumber"], self8k[0]["doc"], "8k")] = (
                m["cik"], m["accessionNumber"], self8k[0]["doc"], "8k")
    print("前置文件數(去重):%d" % len(uniq), flush=True)

    def _fetch(t):
        return (t, cached_doc(*t))

    doc_index: dict[tuple, str] = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for t, (fn, st) in ex.map(_fetch, list(uniq)):
            doc_index[(t[0], t[1], t[3])] = fn if fn else ("FAIL:" + st)
    print("前置文件完成 %d" % len(doc_index), flush=True)

    # ---- 對手年報(每事件兩個最大成交同業)
    peer_jobs: dict[tuple, tuple] = {}
    peer_pick: dict[str, list] = {}
    peer_universe_by_eid: dict[str, pd.DataFrame] = {}
    sic2_ent = ent.copy()
    sic2_ent["sic2"] = sic2_ent["sic"].astype(str).str.zfill(4).str[:2]
    for p, m, _pf in jobs:
        t1d = pd.Timestamp(m["reaction_date"])
        peer_universe = sic2_ent[(sic2_ent["sic2"] == m["sic2"])
                                 & (sic2_ent["entity_id"] != m["cik"])
                                 & (sic2_ent["entity_id"].map(first_px) <= t1d)].copy()
        try:
            dv_t1 = dv_by_date.loc[t1d]
        except KeyError:
            dv_t1 = pd.Series(dtype="float64")
        peer_universe_by_eid[p["event_id"]] = peer_universe
        peers = peer_universe.assign(
            dv=peer_universe["entity_id"].map(dv_t1).astype("float64")
        ).dropna(subset=["dv"]).sort_values("dv", ascending=False).head(2)
        lst = []
        for pr in peers.itertuples(index=False):
            rows = filing_rows(pr.entity_id)
            ann = [x for x in rows if x["form"] in ("10-K", "20-F", "40-F")
                   and x["filingDate"] <= m["reaction_date"]]
            item = dict(entity_id=pr.entity_id, name=pr.name, ticker=pr.primary_ticker,
                        sic2=pr.sic2)
            if ann:
                a = ann[0]
                item.update(form=a["form"], filingDate=a["filingDate"], accn=a["accn"])
                peer_jobs[(pr.entity_id, a["accn"], a["doc"], "peer10k")] = (
                    pr.entity_id, a["accn"], a["doc"], "peer10k")
            lst.append(item)
        peer_pick[p["event_id"]] = lst
    print("對手年報數(去重):%d" % len(peer_jobs), flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for t, (fn, st) in ex.map(_fetch, list(peer_jobs)):
            doc_index[(t[0], t[1], t[3])] = fn if fn else ("FAIL:" + st)

    if STAGE == "fetch":
        left = sum(1 for v in doc_index.values() if v.startswith("FAIL:本段額滿"))
        print("本段新抓 %d 份(快取在 edgar_cache);本段未抓 %d 份" % (_n_new[0], left),
              flush=True)
        return

    n_missing = sum(1 for v in doc_index.values() if v.startswith("FAIL:"))
    print("文件就緒:成功 %d / 缺 %d(缺者包內標「查不到」)" % (len(doc_index) - n_missing,
                                                       n_missing), flush=True)

    # ---- 逐事件落包
    n_ok = 0
    rows_log = []
    for p, m, pf in jobs:
        eid = p["event_id"]
        t1 = m["reaction_date"]
        pack = {"event_id": eid, "schema": "②第一次考試取證包 v1", "ticker": m["ticker"],
                "cik": m["cik"], "name": meta.loc[p["acc"], "name"] if "name" in meta.columns else "",
                "sic": m["sic"], "sic2": m["sic2"], "bucket": bucket_of(m["sic2"]),
                "evidence_cutoff": "T1 = %s(反應日收市)" % t1,
                "provenance": {"rule": "執行口徑——②第一次考試-v1.md 第二節;"
                                       "提示詞——改善驅動可持續性判斷-v1.md 第二節",
                               "frozen": "2026-09-12"}}
        # 1 事件識別
        pack["1_事件識別"] = {
            "event_id": eid, "ticker": m["ticker"], "cik": m["cik"],
            "T0_公布時間_美東": m["t0_et"], "T0_UTC": m["acceptanceDateTime"],
            "signal_date_反應日": t1, "T1_分析截止": "%s 收市" % t1,
            "T2_可成交": "%s 開市" % m["t2_date"],
            "fiscal_quarter": m["fiscal_quarter"], "cluster_id": m["cluster_id"],
            "improvement_type_機械": m["improvement_type"],
            "8-K_items": m["items"],
            "accessionNumber": m["accessionNumber"],
            "edgar_8k_url": doc_url(m["cik"], m["accessionNumber"], m["primaryDocument"])}
        # 2 觸發資料
        ex_fn = DOCS / ("%s__EX991.txt.gz" % p["acc"].replace("-", ""))
        ex_txt = gzip.open(ex_fn, "rt", encoding="utf-8").read() if ex_fn.exists() else ""
        k8 = doc_index.get((m["cik"], m["accessionNumber"], "8k"), "")
        pack["2_觸發資料"] = {
            "ex991_full_text": ex_txt if ex_txt else "查不到",
            "ex991_chars": len(ex_txt),
            "same_day_8k_items": m["items"],
            "same_day_8k_other_items_note":
                "同日 8-K 其他項目見上欄 items;本體全文見 local_8k",
            "local_8k": k8,
            "earnings_call_transcript": "查不到"}
        # 3 截止前文件
        docs = {}
        for k, lab in (("annual", "最近 10-K/20-F"), ("q0", "最近 10-Q/6-K(1)"),
                       ("q1", "最近 10-Q/6-K(2)")):
            f = pf.get(k)
            if not f:
                docs[lab] = "查不到"
                continue
            fn = doc_index.get((m["cik"], f["accn"], k), "")
            docs[lab] = {"form": f["form"], "filingDate": f["filingDate"],
                         "reportDate": f["reportDate"], "accession": f["accn"],
                         "url": doc_url(m["cik"], f["accn"], f["doc"]),
                         "local_gz": fn}
        pack["3_截止前文件"] = docs
        # 4 財務數列
        b = bundle(m["cik"])
        q_end = m["signal_q_end"]
        series = []
        if b.get("ok") and q_end:
            ends = sorted(b["rev_q"])
            i = ends.index(q_end) if q_end in ends else None
            if i is not None:
                for e in ends[max(0, i - 7): i + 1]:
                    series.append({
                        "period_end": e,
                        "revenue": b["rev_q"].get(e),
                        "gross_profit": b["gp_q"].get(e),
                        "operating_income": b["oi_q"].get(e),
                        "ocf": b["ocf_q"].get(e)})
        pack["4_財務數列"] = {
            "source": "data/sec/companyfacts(XBRL 首報值)",
            "quarters": series,
            "signal_q_end": q_end,
            "g0_signal_q_yoy": None if pd.isna(m["rev_g0"]) else round(float(m["rev_g0"]), 6),
            "prev_q_yoy": None if pd.isna(m["rev_prev_q_yoy"]) else round(float(m["rev_prev_q_yoy"]), 6),
            "accel_pp": None if pd.isna(m["accel_pp"]) else round(float(m["accel_pp"]), 4)}
        # 5 同業與行業
        peers_out = []
        for it in peer_pick[eid]:
            o = dict(it)
            if it.get("accn"):
                fn = doc_index.get((it["entity_id"], it["accn"], "peer10k"), "")
                o["local_gz"] = fn
                txt = ""
                if fn and not fn.startswith("FAIL"):
                    try:
                        txt = gzip.open(DOCS / fn, "rt", encoding="utf-8").read()
                    except OSError:
                        txt = ""
                o["capex_excerpt"] = capex_excerpt(txt) if txt else []
            peers_out.append(o)
        pu = peer_universe_by_eid.get(eid, sic2_ent.iloc[0:0])
        pack["5_同業與行業"] = {
            "sic2": m["sic2"],
            "peer_rule": "同一 SIC2 且反應日之前已有日線(已上市)的全部同業;"
                         "「兩個最大」按**反應日當日**的 60 日中位成交額排序,不用今日值",
            "n_listed_peers_same_sic2": int(len(pu)),
            "peer_list_all_same_sic2_tickers": sorted(
                pu["primary_ticker"].dropna().astype(str).tolist())[:120],
            "peer_annual_reports_2_largest": peers_out}
        # 6 價格狀態
        try:
            k = key.loc[(m["cik"], pd.Timestamp(t1))]
            pstate = {"ret_6m_skip1m": float(k["ret6"]), "ret_12m_skip1m": float(k["ret12"]),
                      "rank_6m_pct_in_universe": float(k["rank6"]),
                      "rank_12m_pct_in_universe": float(k["rank12"]),
                      "dist_from_52w_high": float(k["dist52"])}
        except KeyError:
            pstate = {"note": "該日無價格狀態"}
        pstate.update({"reaction_day_return": None if pd.isna(m["ret"]) else float(m["ret"]),
                       "reaction_day_rel_spy": None if pd.isna(m["rel_spy"]) else float(m["rel_spy"]),
                       "reaction_day_rel_sic2_median": None if pd.isna(m["rel_sic2"]) else float(m["rel_sic2"])})
        pack["6_價格狀態"] = pstate
        pack["7_共識"] = {"analyst_consensus": "查不到",
                          "note": "倉內無歷史共識資料;不得憑記憶補"}

        # masking_check:包內最晚資料日期
        dates_in = [t1, m["filingDate"]]
        for lab, d in pack["3_截止前文件"].items():
            if isinstance(d, dict):
                dates_in.append(d["filingDate"])
        for it in peers_out:
            if it.get("filingDate"):
                dates_in.append(it["filingDate"])
        if series:
            dates_in.append(series[-1]["period_end"])
        pack["masking_check"] = {
            "latest_data_date": max(d for d in dates_in if d),
            "cutoff": t1,
            "excluded": "T1 之後的價格、財報、公告整欄不入包",
            "known_leak_note":
                "財務數列取 XBRL 首報值;訊號季那組數的最早申報來源是該季 10-Q(在 T1 之後"
                "才申報),但同一批數在同日 EX-99.1 已公布;毛利率、經營現金流等項目有時"
                "季報才見,屬已知的輕微越界。",
            "verified": bool(max(d for d in dates_in if d) <= t1)}
        (OUT / ("%s.json" % eid)).write_text(
            json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
        n_ok += 1
        rows_log.append(dict(event_id=eid, acc=p["acc"], ticker=m["ticker"],
                             replaces=p.get("replaces", ""),
                             replace_reason=p.get("replace_reason", ""),
                             ex991_chars=len(ex_txt),
                             n_quarters=len(series),
                             latest_data_date=pack["masking_check"]["latest_data_date"],
                             cutoff=t1, ok=pack["masking_check"]["verified"]))
        print("  %s %s ex991=%d字 季數=%d 最晚資料=%s" % (
            eid, m["ticker"], len(ex_txt), len(series),
            pack["masking_check"]["latest_data_date"]), flush=True)
    pd.DataFrame(rows_log).to_csv(CACHE / "packets_log.csv", index=False, encoding="utf-8-sig")
    (CACHE / "packets_substitutions.json").write_text(json.dumps(
        {"n_main": len(picks["main"]), "n_subs": len(subs), "subs": subs,
         "unbuildable": unbuildable, "backups_used": sorted(used_bk),
         "backups_unbuildable": bk_bad},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("落包 %d 個;遮罩不合者 %d 個" % (
        n_ok, sum(1 for r in rows_log if not r["ok"])))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
