# -*- coding: utf-8 -*-
"""KARST-232 自查:對 84 包逐包機械核(獨立於建包碼,由檔案本體重算)。

核七項:
  A 84 包對 picks_final(檔名、accessionNumber、事件數)
  B 同業節(規則、同業資料不足標籤、摘錄非空陣列)
  C 加十項(八列 × 十項、來源申報日 ≤ T1)
  D prior_release_guidance 存在
  E preliminary_release 為布林
  F masking:全文 ISO 日期掃描(T1 之後只准 T2 與凍結日)+ latest_data_date ≤ T1
  G 3_截止前文件三槽(有檔者行數 ≥ 500 且含 MD&A / Item 7 / Item 2)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "packets"
DOCS = HERE.parent / "A" / "edgar_cache"
ISO_RX = re.compile(r"\b(19|20)\d\d-\d\d-\d\d\b")
FROZEN = "2026-09-13"
DOC_NEED = [re.compile(r"(?i)item\s*7"), re.compile(r"(?i)item\s*2\b"),
            re.compile(r"(?i)management.{0,3}s discussion|MD&A")]


def main() -> None:
    picks = json.loads((CACHE / "picks_final.json").read_text(encoding="utf-8"))
    final = picks["final"]
    bad = {k: [] for k in "ABCDEFG"}
    n = {"peer_sic4": 0, "peer_sic3": 0, "insufficient": 0, "capex_ok": 0,
         "capex_missing": 0, "no_annual": 0, "extra_cells": 0, "extra_total": 0,
         "extra_signal": 0, "prior_ok": 0, "prior_missing": 0, "prelim": 0,
         "doc_slots": 0, "doc_missing": 0, "doc_short": 0, "transcript": 0,
         "iso_hits": 0}
    for f in final:
        slot, acc = f["slot"], f["acc"]
        p = OUT / ("%s.json" % slot)
        if not p.exists():
            bad["A"].append(slot)
            continue
        text = p.read_text(encoding="utf-8")
        d = json.loads(text)
        if d["1_事件識別"]["accessionNumber"] != acc or d["event_id"] != f["event_id"]:
            bad["A"].append(slot)
        # B
        peer = d["5_同業與行業"]
        rule = peer["peer_rule_applied"]
        if rule == "insufficient":
            n["insufficient"] += 1
            if peer["peer_annual_reports_2_largest"] != "同業資料不足":
                bad["B"].append(slot)
        else:
            n["peer_" + rule] += 1
            lst = peer["peer_annual_reports_2_largest"]
            if not isinstance(lst, list) or not lst or len(lst) != 2:
                bad["B"].append(slot)
            for it in lst:
                ex = it.get("capex_excerpt")
                if isinstance(ex, list) and ex:
                    n["capex_ok"] += 1
                elif isinstance(ex, list):
                    bad["B"].append(slot + ":empty-array")     # 票面明文禁止
                    n["capex_missing"] += 1
                else:
                    n["capex_missing"] += 1
                    if not it.get("accn"):
                        n["no_annual"] += 1
        # C
        qs = d["4_財務數列"]["quarters"]
        if len(qs) != 8:
            bad["C"].append(slot + ":rows")
        for q in qs:
            ex = q.get("extra") or {}
            if len(ex) != 10:
                bad["C"].append(slot + ":items")
                break
            sig = q["period_end"] == d["4_財務數列"]["signal_q_end"]
            for k, v in ex.items():
                n["extra_total"] += 1
                if isinstance(v, dict):
                    n["extra_cells"] += 1
                    n["extra_signal"] += int(sig)
                    if sig:
                        if v.get("source") != "EX-99.1 稿內文字":
                            bad["C"].append(slot + ":" + k + ":sig")
                    else:
                        fd = v.get("filed") or ""
                        if not fd or fd > d["masking_check"]["cutoff"]:
                            bad["C"].append(slot + ":" + k + ":filed")
        # D
        pr = d["2_觸發資料"].get("prior_release_guidance")
        if pr is None:
            bad["D"].append(slot)
        elif isinstance(pr, dict) and pr.get("guidance_sentences"):
            n["prior_ok"] += 1
            for s in pr["guidance_sentences"]:
                if not isinstance(s, str) or not s.strip():
                    bad["D"].append(slot + ":sent")
        else:
            n["prior_missing"] += 1
        # E
        pv = d["2_觸發資料"].get("preliminary_release")
        if not isinstance(pv, bool):
            bad["E"].append(slot)
        n["prelim"] += int(pv is True)
        # F
        t1 = d["masking_check"]["cutoff"]
        t2 = str(d["1_事件識別"]["T2_可成交"]).split()[0]
        viol = sorted({m.group(0) for m in ISO_RX.finditer(text)
                       if m.group(0) > t1 and m.group(0) not in {t2, FROZEN}})
        if viol or not d["masking_check"]["verified"] \
                or d["masking_check"]["latest_data_date"] > t1:
            bad["F"].append(slot + ":" + ",".join(viol[:3]))
        n["iso_hits"] += len(viol)
        # G
        for lab, dv in d["3_截止前文件"].items():
            if not isinstance(dv, dict):
                n["doc_missing"] += 1
                continue
            fn = DOCS / dv["local_gz"]
            if not fn.exists():
                bad["G"].append(slot + ":nofile")
                continue
            t = fn.read_text(encoding="utf-8") if False else ""
            import gzip
            with gzip.open(fn, "rt", encoding="utf-8") as fh:
                t = fh.read()
            lines = t.count("\n") + 1
            n["doc_slots"] += 1
            if lines < 500:
                n["doc_short"] += 1
                bad["G"].append(slot + ":short")
            if not any(rx.search(t) for rx in DOC_NEED):
                bad["G"].append(slot + ":nosec")
        if d["2_觸發資料"]["earnings_call_transcript"] != "查不到":
            n["transcript"] += 1

    print("counts:", json.dumps(n, ensure_ascii=False))
    for k in "ABCDEFG":
        print("bad %s: %d %s" % (k, len(bad[k]), bad[k][:15]))
    (CACHE / "enrich_verify.json").write_text(
        json.dumps({"counts": n, "bad": bad}, ensure_ascii=False, indent=1),
        encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
