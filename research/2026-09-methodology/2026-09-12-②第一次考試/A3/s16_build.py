# -*- coding: utf-8 -*-
"""KARST-232 第二至九步:重建 84 個取證包(對 `cache/picks_final.json`)。

一支做完全部 84 包,內容:
  1 事件識別(照 s9 體例,加 slot_id / 來源 event_id / 換入資訊)
  2 觸發資料(EX-99.1 全文、同日 8-K 項目、逐字稿注入、**上一份業績稿指引句**、
    **preliminary_release 標籤**)
  3 截止前文件(最近 10-K/20-F、最近兩份 10-Q/6-K,申報日 ≤ T1)
  4 財務數列(原有八季 + **加十項八季**,訊號季一行只認 EX-99.1 稿內有的數字)
  5 同業與行業(**同 SIC4;不足 5 家退 SIC3;仍不足標「同業資料不足」**;兩大同業年報
    資本開支摘錄非空)
  6 價格狀態  7 共識
  masking_check(全文 ISO 日期掃描: T1 之後只准 T2 與凍結日)

只讀既有資料;不抓網絡(抓取由 s15_fetch.py 先做完)。輸出 `packets/<slot>.json`。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

import finlib as F
import s15_lib as L
from s6_improve_text import parse_guidance
from buckets import bucket_of

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "packets"
TRANS = HERE / "transcripts"
ROOT = Path(r"C:\projects\Karst")
ISO_RX = re.compile(r"\b(19|20)\d\d-\d\d-\d\d\b")

HIST_KW = {
    "inventory": re.compile(r"(?i)inventor"),
    "accounts_receivable": re.compile(r"(?i)receivable"),
    "deferred_revenue": re.compile(r"(?i)(deferred revenue|contract liabilit)"),
    "cash_and_equivalents": re.compile(r"(?i)cash"),
    "total_debt": re.compile(r"(?i)(debt|borrow|notes payable|term loan)"),
    "capex": re.compile(r"(?i)(capital expenditure|property, plant|purchases of property)"),
    "depreciation_amortization": re.compile(r"(?i)(depreciation|amortization)"),
    "net_income": re.compile(r"(?i)(net (income|loss|earnings))"),
    "diluted_eps": re.compile(r"(?i)(per share|\beps\b)"),
    "diluted_shares": re.compile(r"(?i)(diluted|weighted average)"),
}


def fmt_variants(x: float) -> list[str]:
    out = []
    for s in ("%.2f" % x, "%.1f" % x, "%.0f" % x):
        s = s.rstrip("0").rstrip(".") if "." in s else s
        if not s:
            continue
        if s not in out:
            out.append(s)
        with_comma = re.sub(r"\B(?=(\d{3})+(?!\d))", ",", s.split(".")[0])
        with_comma = with_comma + ("." + s.split(".")[1] if "." in s else "")
        if with_comma not in out:
            out.append(with_comma)
    return out


def find_usd(text: str, v: float, kw: re.Pattern) -> bool:
    """USD 項在稿內找同一個數(可寫成千/百萬/十億)。"""
    if not text or v is None:
        return False
    for sc in (1.0, 1e3, 1e6, 1e9):
        x = abs(v) / sc
        if x <= 0:
            continue
        for s in fmt_variants(x):
            pat = re.compile(r"(?<![\d.,])\(?\$?\s*" + re.escape(s) + r"(?![\d])")
            for m in pat.finditer(text):
                if sc != 1.0 and not re.match(
                        r"\s*(thousand|million|billion|mn|bn|[MBK])\b",
                        text[m.end():m.end() + 12], re.I):
                    continue        # 縮放過的數一定要緊跟單位字,否則當巧合
                ctx = text[max(0, m.start() - 200):m.end() + 200]
                if kw.search(ctx):
                    return True
    return False


def find_plain(text: str, v: float, kw: re.Pattern) -> bool:
    """非 USD 項(EPS、股數):數字本身 + 附近要有關鍵字。"""
    if not text or v is None:
        return False
    for s in fmt_variants(abs(v)):
        pat = re.compile(r"(?<![\d.,])\$?\s*" + re.escape(s) + r"(?![\d])")
        for m in pat.finditer(text):
            ctx = text[max(0, m.start() - 200):m.end() + 200]
            if kw.search(ctx):
                return True
    return False


def transcript_for(src_eid: str, t1: str) -> tuple[object, str]:
    """回傳 (注入內容 或 '查不到', transcript_date 或 '')。"""
    p = TRANS / ("%s.json" % src_eid)
    if not p.exists():
        return "查不到", ""
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "查不到", ""
    rd = d.get("report_date") or ""
    if not rd or rd > t1:
        return "查不到", ""
    segs = d.get("segments") or []
    head = dict(report_date=rd, source=d.get("source", ""), dataset=d.get("dataset", ""),
                n_segments=d.get("n_segments", len(segs)),
                has_qna=d.get("has_qna"), n_chars=d.get("n_chars"),
                note="照 A3/transcripts/<來源 event_id>.json 注入;只取 segments 與日期,"
                     "不含抓取時間等 T1 之後的欄位")
    payload = json.dumps(segs, ensure_ascii=False)
    if len(payload.encode("utf-8")) > 300 * 1024:
        head["segments_note"] = "全文超過 300 KB,只留頭 50 段,全文另存"
        head["transcript_path"] = "A3/transcripts/%s.json" % src_eid
        head["segments_head_50"] = segs[:50]
        return head, rd
    head["segments"] = segs
    return head, rd


def main() -> None:
    picks = json.loads((CACHE / "picks_final.json").read_text(encoding="utf-8"))
    final = picks["final"]
    plan = json.loads((CACHE / "enrich_plan.json").read_text(encoding="utf-8"))
    cp = CACHE / "capex_extra.json"
    CAPEX_EXTRA = json.loads(cp.read_text(encoding="utf-8")) if cp.exists() else {}
    pop = pd.read_parquet(CACHE / "population_improvement.parquet")
    meta = pop.set_index("accessionNumber")
    meta["accessionNumber"] = meta.index
    ent = pd.read_parquet(ROOT / "data" / "universe" / "entities.parquet",
                          columns=["entity_id", "name", "primary_ticker", "sic", "exchange"])
    ent["sic4"] = ent["sic"].astype(str).str.zfill(4)
    ent["sic3"] = ent["sic4"].str[:3]
    ent["sic2"] = ent["sic4"].str[:2]
    px_state = pd.read_parquet(CACHE / "px_state_enrich.parquet")
    key = px_state.set_index(["entity_id", "date"])[["ret6", "ret12", "rank6", "rank12",
                                                     "dist52"]]
    dv_by_date = px_state.set_index(["date", "entity_id"])["dv60"].dropna()
    first_px = {k: pd.Timestamp(v) for k, v in
                json.loads((CACHE / "first_px_enrich.json").read_text()).items()}
    FROZEN = "2026-09-13"

    stat = {k: 0 for k in
            ["peer_sic4", "peer_sic3", "peer_insufficient", "peer_capex_empty",
             "peer_no_annual", "prior_ok", "prior_missing", "prior_fallback",
             "prelim_true",
             "transcript_injected", "transcript_missing", "packets", "mask_bad"]}
    extra_cov = {k: 0 for k in L.EXTRA_ITEMS}
    extra_signal = {k: 0 for k in L.EXTRA_ITEMS}
    log = []

    for f in final:
        slot, acc = f["slot"], f["acc"]
        m = meta.loc[acc]
        t1 = m["reaction_date"]
        t1d = pd.Timestamp(t1)
        src_eid = f["event_id"]
        pack = {"event_id": src_eid, "slot_id": slot,
                "schema": "②第一次考試取證包 v1(補強版)",
                "ticker": m["ticker"], "cik": m["cik"], "name": m["name"],
                "sic": m["sic"], "sic2": m["sic2"], "bucket": f["bucket"],
                "evidence_cutoff": "T1 = %s(反應日收市)" % t1,
                "provenance": {
                    "rule": "執行口徑——②第一次考試-v1.2(修訂頁)第 1–10 項 + 補充四;"
                            "提示詞——改善驅動可持續性判斷-v1.1 第二節輸入表;"
                            "KARST-232 補強(同業規則、加十項財務數列、歷史稿指引句、"
                            "preliminary 標籤、逐字稿注入、遮罩重掃)",
                    "frozen": FROZEN}}
        pack["1_事件識別"] = {
            "slot_id": slot, "event_id": src_eid, "ticker": m["ticker"], "cik": m["cik"],
            "T0_公布時間_美東": m["t0_et"], "T0_UTC": m["acceptanceDateTime"],
            "t0_source": m["t0_source"], "EX-99.1_稿頭日期": m["dateline"],
            "公開時段": m["release_timing"],
            "signal_date_反應日": t1, "T1_分析截止": "%s 收市" % t1,
            "T2_可成交": "%s 開市" % m["t2_date"],
            "fiscal_quarter": m["fiscal_quarter"],
            "improvement_type_機械": m["improvement_type"],
            "8-K_items": m["items"], "accessionNumber": acc,
            "edgar_8k_url": L.doc_url(m["cik"], acc, m["primaryDocument"]),
            "swapped_in": ({"replaced_slot": slot, "replaced_event_id": slot,
                            "replaced_accessionNumber": f["replaced_acc"],
                            "reason": f["reason"]} if f.get("swapped") else None)}

        # ---- 2 觸發資料
        ex_fn = "%s__EX991.txt.gz" % acc.replace("-", "")
        ex_txt = L.read_doc(ex_fn)
        ex_ok = bool(ex_txt)
        k8 = "%s__8k.txt.gz" % acc.replace("-", "")
        if not (L.DOCS / k8).exists():
            k8 = ""
        pri = plan["prior"].get(slot, {})
        prior_out = "查不到"
        if pri.get("found"):
            pfn = "%s__EX991.txt.gz" % pri["accn"].replace("-", "")
            ptxt = L.read_doc(pfn)
            if ptxt:
                recs = parse_guidance(ptxt)
                sents, seen = [], set()
                for r in recs:
                    s = (r.get("sentence") or "").strip()
                    if s and s not in seen:
                        seen.add(s)
                        sents.append(s)
                method = "s6_improve_text.parse_guidance"
                if not sents:
                    # 解析器交白卷而上游已證其漏率過半(52.5%):補一道保守標記掃描,
                    # 照樣只給原句、不給解析結果,並在 method 欄講明來源不同。
                    sents = L.guidance_fallback(ptxt)
                    if sents:
                        method = "後備標記掃描(解析器零收穫時啟用)"
                prior_out = {
                    "source": "訊號季前一季的 8-K(Item 2.02)所附 EX-99.1",
                    "accessionNumber": pri["accn"], "filingDate": pri["filingDate"],
                    "reportDate": pri.get("reportDate", ""), "form": "8-K",
                    "local_gz": pfn if (L.DOCS / pfn).exists() else "",
                    "method": method,
                    "n_guidance_records": len(recs), "n_sentences": len(sents[:20]),
                    "guidance_sentences": sents[:20],
                    "note": "指引句,**原文照抄,只給句子,不給解析結果**(不寫指標、期間、新舊值);"
                            "單句長度上限 600 字元;最多列 20 句。method 欄講明句子由哪一支找出"}
                if not sents:
                    prior_out["status"] = "查不到(該份 EX-99.1 內找不到指引句,該期可能本來就沒給指引)"
                stat["prior_ok"] += 1
                stat["prior_fallback"] += int(method != "s6_improve_text.parse_guidance")
            else:
                stat["prior_missing"] += 1
                prior_out = {"status": "查不到",
                             "note": "找到上一份 8-K,但其 EX-99.1 抓不到(該申報無 EX-99 附件)"}
        else:
            stat["prior_missing"] += 1
        pos = plan["prelim"].get(slot, {}).get("first_prelim_pos", -1)
        prelim = bool(0 <= pos < 600)
        stat["prelim_true"] += int(prelim)
        tr, trd = transcript_for(src_eid, t1)
        stat["transcript_injected"] += int(tr != "查不到")
        stat["transcript_missing"] += int(tr == "查不到")
        gc_i = ex_txt.lower().find("going concern")
        pack["2_觸發資料"] = {
            "ex991_full_text": ex_txt if ex_ok else "查不到",
            "ex991_chars": len(ex_txt),
            "same_day_8k_items": m["items"],
            "same_day_8k_other_items_note":
                "同日 8-K 其他項目見上欄 items;本體全文見 local_8k",
            "local_8k": k8,
            "preliminary_release": prelim,
            "preliminary_release_rule":
                "只認「稿頭即初步業績」(EX-99.1 首 600 字元內出現 preliminary);"
                "免責句、表頭、非 GAAP 說明一律為假",
            "prior_release_guidance": prior_out,
            "earnings_call_transcript": tr,
            "going_concern_hit": int(gc_i >= 0),
            "going_concern_snippet": re.sub(r"\s+", " ", ex_txt[gc_i:gc_i + 200]) if gc_i >= 0 else ""}

        # ---- 3 截止前文件
        rows = L.filing_rows(m["cik"])
        pf = L.pick_filings(rows, t1)
        docs = {}
        for k, lab in (("annual", "最近 10-K/20-F"), ("q0", "最近 10-Q/6-K(1)"),
                       ("q1", "最近 10-Q/6-K(2)")):
            x = pf.get(k)
            if not x:
                docs[lab] = "查不到"
                continue
            fn = "%s__%s.txt.gz" % (x["accn"].replace("-", ""), k)
            if not (L.DOCS / fn).exists():
                docs[lab] = "查不到"
                continue
            docs[lab] = {"form": x["form"], "filingDate": x["filingDate"],
                         "reportDate": x["reportDate"], "accession": x["accn"],
                         "url": L.doc_url(m["cik"], x["accn"], x["doc"]),
                         "local_gz": fn,
                         "n_lines": L.read_doc(fn).count("\n") + 1}
        pack["3_截止前文件"] = docs

        # ---- 4 財務數列
        facts = L.load_facts(m["cik"])
        b = F.bundle(m["cik"])
        q_end = m["signal_q_end"]
        series = []
        if b.get("ok") and q_end:
            ends = sorted(b["rev_q"])
            if q_end in ends:
                i = ends.index(q_end)
                filed_map = b.get("rev_q_filed", {})
                for e in ends[max(0, i - 7): i + 1]:
                    rf = filed_map.get(e, (None, ""))[1]
                    series.append({
                        "period_end": e, "revenue": b["rev_q"].get(e),
                        "gross_profit": b["gp_q"].get(e),
                        "operating_income": b["oi_q"].get(e),
                        "ocf": b["ocf_q"].get(e),
                        "revenue_xbrl_first_filed_after_T1": bool(rf and rf > t1),
                        "revenue_year_end_derived": bool(
                            e not in b.get("rev_q_direct", ()))})
        extras = L.extra_series(facts) if facts else {n: {} for n in L.EXTRA_ITEMS}
        for r_ in series:
            is_sig = r_["period_end"] == q_end
            ex = {}
            for name, cfg in L.EXTRA_ITEMS.items():
                hit = extras.get(name, {}).get(r_["period_end"])
                if hit is None:
                    ex[name] = "查不到"
                    continue
                val, filed = hit
                if is_sig:
                    ok = (find_usd(ex_txt, val, HIST_KW[name]) if cfg["unit"] == "USD"
                          else find_plain(ex_txt, val, HIST_KW[name]))
                    if ok:
                        ex[name] = {"value": val, "source": "EX-99.1 稿內文字"}
                        extra_signal[name] += 1
                    else:
                        ex[name] = "查不到"
                        continue
                else:
                    if not filed or filed > t1:
                        ex[name] = "查不到"
                        continue
                    ex[name] = {"value": val, "filed": filed,
                                "source": "XBRL 首報值", "tag": cfg["tags"][0]
                                if cfg["tags"] else "derived"}
                extra_cov[name] += 1
            r_["extra"] = ex
        for r_ in series:
            if r_["period_end"] == q_end:
                r_["revenue_source"] = "EX-99.1 稿內文字"
                if not pd.isna(m["rev_signal_text"]):
                    r_["revenue_ex991"] = float(m["rev_signal_text"])
                r_["revenue_xbrl_for_reference"] = (
                    None if pd.isna(m["rev_signal_xbrl"]) else float(m["rev_signal_xbrl"]))
            else:
                r_["revenue_source"] = "XBRL 首報值(稿內未逐季列出)"
        pack["4_財務數列"] = {
            "source": "訊號季收入 = EX-99.1 稿內文字(v1.2 第 4 項);"
                      "其餘各季 = data/sec/companyfacts XBRL 首報值",
            "extra_items_rule":
                "加十項(XBRL 首報值,每一格的來源申報日 ≤ T1,晚於 T1 者一律「查不到」)。"
                "**訊號季那一行只認 EX-99.1 稿內有的數字**(數字匹配 + 附近要有該項的關鍵字),"
                "稿內沒有者標「查不到」。非訊號季者附 `filed` = 該值最早申報日(必 ≤ T1)。",
            "extra_items_legend": {
                k: {"label": v["label"], "unit": v["unit"], "kind": v["kind"],
                    "tags": v["tags"] or ["LongTermDebtCurrent+LongTermDebtNoncurrent"
                                          "(不足者退 LongTermDebt)"]}
                for k, v in L.EXTRA_ITEMS.items()},
            "hist_quarters_public_by_T1": bool(m["hist_quarters_public_by_t1"]),
            "hist_src_latest_filed": m["hist_src_latest_filed"],
            "n_rows": len(series),
            "n_rows_first_filed_after_T1": sum(
                1 for r_ in series if r_["revenue_xbrl_first_filed_after_T1"]),
            "year_end_derived_note":
                "標 `revenue_year_end_derived=true` 的季是**推算**而來:該季無 80–100 日的"
                "單季 duration,由年報(340–380 日)減同期 9 個月累計(255–285 日)得出"
                "(票 A″ 第 3 步同一條)。",
            "quarters": series, "signal_q_end": q_end,
            "g0_signal_q_yoy": None if pd.isna(m["rev_g0_text"]) else round(float(m["rev_g0_text"]), 6),
            "g0_xbrl_for_reference": None if pd.isna(m["rev_g0"]) else round(float(m["rev_g0"]), 6),
            "prev_q_yoy": None if pd.isna(m["rev_prev_q_yoy"]) else round(float(m["rev_prev_q_yoy"]), 6),
            "accel_pp": None if pd.isna(m["accel_pp_text"]) else round(float(m["accel_pp_text"]), 4),
            "accel_rule": "稿內訊號季收入 ÷ XBRL 去年同季 − 1 = 稿內 g0;"
                          "稿內 g0 − XBRL 上一季按年增速 ≥ 2pp 即加速(v1.2 第 7 項)"}

        # ---- 5 同業與行業
        pr = plan["peers"].get(slot, {})
        rule = pr.get("rule", "insufficient")
        peers_out = []
        if rule == "insufficient":
            stat["peer_insufficient"] += 1
        else:
            stat["peer_" + rule] += 1
            for it in pr.get("peers", []):
                o = dict(it)
                o.pop("bucket", None)
                if it.get("accn"):
                    fn, st = L.cached(it["entity_id"], it["accn"], "", "peer10k",
                                      fetch=False)
                    o["local_gz"] = fn
                    txt = L.read_doc(fn)
                    exc = L.capex_excerpt(txt) if txt else []
                    if exc:
                        o["capex_excerpt"] = exc
                        o["capex_status"] = "ok"
                    else:
                        # 年報本文無資本開支(40-F 封面式、或以引註併入):改看同一申報的附件
                        alt = CAPEX_EXTRA.get(it["accn"], {})
                        if alt.get("status") == "ok":
                            o["capex_excerpt"] = alt["capex_excerpt"]
                            o["capex_status"] = "ok(附件 %s)" % alt["doc"]
                            o["capex_local_gz"] = alt["local_gz"]
                        else:
                            # 一律用字串「查不到」,不留空陣列
                            o["capex_excerpt"] = "查不到"
                            o["capex_status"] = "查不到"
                            o["note"] = "年報本文與同申報附件皆無可摘錄的資本開支句"
                            stat["peer_capex_empty"] += 1
                else:
                    o["capex_excerpt"] = "查不到"
                    o["capex_status"] = "查不到"
                    o["note"] = "該同業在 T1 前無年報(10-K/20-F/40-F)"
                    stat["peer_no_annual"] += 1
                peers_out.append(o)
        pack["5_同業與行業"] = {
            "sic4": str(m["sic"]).zfill(4), "sic2": m["sic2"],
            "bucket": bucket_of(m["sic2"]),
            "peer_rule": "同 SIC 四位數**且**同行業桶,且反應日之前已有日線(已上市);"
                         "同 SIC4 上市同業不足 5 家退三位數;仍不足 5 家標「同業資料不足」。"
                         "「兩個最大」按**反應日當日**的 60 日中位成交額排序,不用今日值。"
                         "兩大同業的最近年報(申報日 ≤ T1)資本開支摘錄不得為空陣列。",
            "peer_rule_applied": rule,
            "n_listed_peers": int(pr.get("n_pool", 0)),
            "peer_list_all_tickers": ([] if rule == "insufficient" else
                                      sorted(x["ticker"] for x in pr.get("peers", [])
                                             if x.get("ticker"))[:120]),
            "peer_annual_reports_2_largest":
                ("同業資料不足" if rule == "insufficient" else peers_out)}

        # ---- 6 價格狀態
        try:
            k = key.loc[(m["cik"], t1d)]
            ps = {"ret_6m_skip1m": float(k["ret6"]), "ret_12m_skip1m": float(k["ret12"]),
                  "rank_6m_pct_in_universe": float(k["rank6"]),
                  "rank_12m_pct_in_universe": float(k["rank12"]),
                  "dist_from_52w_high": float(k["dist52"])}
        except KeyError:
            ps = {"note": "該日無價格狀態"}
        ps.update({"reaction_day_return": None if pd.isna(m["ret"]) else float(m["ret"]),
                   "reaction_day_rel_spy": None if pd.isna(m["rel_spy"]) else float(m["rel_spy"]),
                   "reaction_day_rel_sic2_median": None if pd.isna(m["rel_sic2"]) else float(m["rel_sic2"])})
        pack["6_價格狀態"] = ps
        pack["7_共識"] = {"analyst_consensus": "查不到",
                          "note": "倉內無歷史共識資料;不得憑記憶補"}

        # ---- masking_check
        dates_in = [t1, m["filingDate"]]
        for d in pack["3_截止前文件"].values():
            if isinstance(d, dict):
                dates_in.append(d["filingDate"])
        for it in peers_out:
            if it.get("filingDate"):
                dates_in.append(it["filingDate"])
        if series:
            dates_in.append(series[-1]["period_end"])
        if isinstance(prior_out, dict) and prior_out.get("filingDate"):
            dates_in.append(prior_out["filingDate"])
        for r_ in series:
            for v in r_.get("extra", {}).values():
                if isinstance(v, dict) and v.get("filed"):
                    dates_in.append(v["filed"])
        if trd:
            dates_in.append(trd)
        body = json.dumps(pack, ensure_ascii=False)
        allowed = {str(m["t2_date"]), FROZEN}
        viol = sorted({x.group(0) for x in ISO_RX.finditer(body)
                       if x.group(0) > t1 and x.group(0) not in allowed})
        latest = max(d for d in dates_in if d)
        pack["masking_check"] = {
            "latest_data_date": latest,
            "cutoff": t1,
            "excluded": "T1 之後的價格、財報、公告整欄不入包",
            "known_leak_note":
                "財務數列的**收入**一律以稿內文字為準,不越界;其餘項目(毛利率、經營利潤、"
                "經營現金流)取 XBRL 首報值。逐列附布林 `revenue_xbrl_first_filed_after_T1`"
                "(不寫日期,免在包內留下 T1 之後的日子),凡為真者計入 "
                "`4_財務數列.n_rows_first_filed_after_T1`。加十項一律只收來源申報日 ≤ T1 的值,"
                "晚於 T1 者標「查不到」,不在包內放越界的日子。",
            "transcript_date": trd or None,
            "iso_date_scan": {"n_after_T1": len(viol), "after_T1_dates": viol[:20],
                              "allowed_after_T1": sorted(allowed)},
            "verified": bool(len(viol) == 0 and latest <= t1)}
        if not pack["masking_check"]["verified"]:
            stat["mask_bad"] += 1
        (OUT / ("%s.json" % slot)).write_text(
            json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
        stat["packets"] += 1
        log.append(dict(slot=slot, event_id=src_eid, acc=acc, rule=rule,
                        n_peers=len(peers_out), prior=("查不到" if isinstance(prior_out, str)
                                                       else "ok"),
                        prelim=prelim, transcript=(tr != "查不到"),
                        latest=latest, ok=pack["masking_check"]["verified"],
                        n_viol=len(viol)))
        del facts
        print("  %s(%s) rule=%s peers=%d prior=%s prelim=%d tr=%d latest=%s 越界=%d"
              % (slot, src_eid, rule, len(peers_out),
                 "查不到" if isinstance(prior_out, str) else "ok",
                 prelim, tr != "查不到", latest, len(viol)), flush=True)

    pd.DataFrame(log).to_csv(CACHE / "enrich_packets_log.csv", index=False,
                             encoding="utf-8-sig")
    stats = dict(packets=stat, extra_coverage=extra_cov, extra_signal_quarter=extra_signal)
    (CACHE / "enrich_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
