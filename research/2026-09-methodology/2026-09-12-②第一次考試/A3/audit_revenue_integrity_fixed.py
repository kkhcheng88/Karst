# -*- coding: utf-8 -*-
"""KARST-236 第 4 步:以 `finlib_fixed` 為真值,重跑 84 包收入欄完整性核查。

與 KARST-235 的 `audit_revenue_integrity.py` 同一套判準(同一批 helper、同一容差),
**真值來源改成 `finlib_fixed`**——即「同一期末跨 tag 取最早申報 + 累計差分補缺格 +
財年末季推算」。另外加三項:

  1. 換庫等值檢查:`finlib` 與 `finlib_fixed` 算出的真值逐格比對(證明「真值沒變、
     變的只是包內值」)。
  2. 逐包 g0 / prev_q_yoy / accel 的「存值 vs 真值重算」(只記錄,不改任何包)。
  3. 訊號季那行的標籤—值一致性:四欄逐欄看 `signal_row_sources`,標「EX-99.1 稿內文字」
     者該值必須在稿內(2% 容差)、標「查不到」者必須為 null;無該欄的舊包只核
     `revenue` 與 `revenue_ex991` 是否同一數(KARST-235 那一條)。

只讀;輸出一律在 `audit_out_fixed/` 與 `收入欄完整性核查——修正後.md`,不碰 KARST-235
的報告與 csv。不列公司名或代號。
用法:`PYTHONUTF8=1 python audit_revenue_integrity_fixed.py`
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_revenue_integrity as A  # noqa: E402
import finlib as OLD  # noqa: E402
import finlib_fixed as FIX  # noqa: E402
import s22_fix235_rebuild as R  # noqa: E402

OUT_DIR = HERE / "audit_out_fixed"
OUT_DIR.mkdir(exist_ok=True)
FIELDS = A.FIELDS
PKT = HERE / "packets"


def bare_in_text(text: str, v, tol: float = 0.005) -> bool:
    """稿內任何位置有沒有一個等於 v 的數(千/百萬/十億縮放;**不要求**關鍵字)。

    `A.text_hits` 只認 `$` 開頭或帶單位字的數,財報表格那種裸數(`22,812`)認不到,
    本函式補這一格。為免「`3` × 1e6」這類細整數誤中,裸數要至少四位數字(或帶單位字)。
    """
    if v in (None, 0) or not text:
        return False
    for m in R.NUM_RX.finditer(text):
        tok = m.group(1)
        raw = R._num(tok)
        if raw is None or raw == 0:
            continue
        unit = (m.group(2) or "").lower()
        if unit not in R.MULT and sum(c.isdigit() for c in tok) < 4:
            continue
        cands = ([raw * R.MULT[unit]] if unit in R.MULT else []) + \
                [raw * s for s in (1.0, 1e3, 1e6, 1e9)]
        if any(c and abs(abs(c) / abs(v) - 1.0) <= tol for c in cands):
            return True
    return False


def rec_pair(facts):
    """同一份 facts,分別用兩套庫算真值,回 (舊庫, 新庫)。"""
    A.F = OLD
    a = A.rec_all(facts, True)
    A.F = FIX
    b = A.rec_all(facts, True)
    return a, b


def yoy_recalc(fin, qs, rec, sig):
    """照 KARST-236 口徑重算 g0 / prev_q_yoy / accel(訊號季收入用包內值)。"""
    rev_v = rec["revenue"]
    ends = sorted(rev_v)
    if sig not in rev_v:
        return {}
    yago = FIX.yoy_end(rev_v, sig)
    prev_q = ends[ends.index(sig) - 1] if ends.index(sig) >= 1 else None
    prev_yago = FIX.yoy_end(rev_v, prev_q) if prev_q else None
    out = {}
    sigrow = next((q for q in qs if q["period_end"] == sig), None)
    sv = sigrow.get("revenue") if sigrow else None
    if sv is not None and yago and rev_v.get(yago):
        out["g0_signal_q_yoy"] = round(sv / rev_v[yago] - 1.0, 6)
    if prev_q and prev_yago and rev_v.get(prev_yago):
        out["prev_q_yoy"] = round(rev_v[prev_q] / rev_v[prev_yago] - 1.0, 6)
    if out.get("g0_signal_q_yoy") is not None and out.get("prev_q_yoy") is not None:
        out["accel_pp"] = round(
            (out["g0_signal_q_yoy"] - out["prev_q_yoy"]) * 100.0, 4)
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    rows, detail, yoy_rows = [], [], []
    lib_diff = []
    for pf in sorted(PKT.glob("*.json")):
        p = json.load(open(pf, encoding="utf-8"))
        eid = p["event_id"]
        idn = p["1_事件識別"]
        t1 = str(idn.get("T1_分析截止", ""))[:10]
        fin = p["4_財務數列"]
        qs = fin["quarters"]
        sig = fin.get("signal_q_end")
        text = (p["2_觸發資料"] or {}).get("ex991_full_text") or ""
        facts = FIX.load_facts(str(idn["cik"]).zfill(10))
        old_rec, rec = rec_pair(facts)
        for name in FIELDS:
            if old_rec[name] != rec[name]:
                lib_diff.append("%s:%s" % (eid, name))
        tprec = A.rec_all(facts, False)
        detail_local = []

        r = {"event_id": eid, "t1": t1, "n_rows": len(qs),
             "signal_q_end": sig, "has_sig_sources": int(
                 "signal_row_sources" in (next(
                     (q for q in qs if q["period_end"] == sig), {}) or {}))}
        for name in FIELDS:
            ok = bad = leak = no = post = sigtext = coinc = 0
            types, leaks, postc = [], [], []
            tags = {"revenue": FIX.REV_TAGS, "gross_profit": FIX.GP_TAGS,
                    "operating_income": FIX.OI_TAGS, "ocf": FIX.OCF_TAGS}[name]
            for q in qs:
                e, pv = q["period_end"], q.get(name)
                tv = rec[name].get(e)
                ff = (A.filed_first(facts, tags, e, pv, 0, 100000)
                      if name == "ocf" else
                      A.filed_first(facts, tags, e, pv, 60, 130)) if facts else None
                if ff and ff > t1 and e != sig:
                    post += 1
                    postc.append("%s(值首見於 %s)" % (e, ff))
                if pv is None:
                    no += 1
                    if tv is None:
                        ok += 1
                    continue
                if tv is None:
                    continue
                # 訊號季那行:若該欄已明標「EX-99.1 稿內文字」,值只要在稿內就當合格
                # (與收入的豁免對稱;舊包沒有 `signal_row_sources` 者不受影響)
                lab = (q.get("signal_row_sources") or {}).get(name) \
                    if e == sig else None
                if lab == "EX-99.1 稿內文字":
                    if bare_in_text(text, pv):
                        sigtext += 1
                        continue
                is_sig = (name == "revenue"
                          and q.get("revenue_source") == "EX-99.1 稿內文字")
                if is_sig:
                    good = (A.close(pv, tv, A.TOL_OK)
                            or A.close(pv, q.get("revenue_ex991"), A.TOL_SAME))
                else:
                    good = A.close(pv, tv, A.TOL_OK)
                if good:
                    ok += 1
                else:
                    bad += 1
                    t, why = A.classify(
                        pv, e, rec[name], sorted(rec["revenue"]),
                        bool(q.get("revenue_year_end_derived"))
                        if name == "revenue" else False)
                    types.append(t)
                    detail_local.append(
                        {"event_id": eid, "field": name, "period_end": e,
                         "packet": pv, "truth_earliest_filed": tv,
                         "tag_priority_value": tprec[name].get(e),
                         "type": t, "why": why, "filed_first": ff,
                         "filed_after_T1": int(bool(ff) and ff > t1)})
                if name == "revenue":
                    pv_after = [x for x in sorted(rec["revenue"]) if x > t1][:4]
                    hit = [x for x in pv_after
                           if A.close(pv, rec["revenue"][x], A.TOL_SAME)]
                    near = [x for x in pv_after
                            if A.close(pv, rec["revenue"][x], 1e-3)]
                    if hit and not A.close(pv, tv, A.TOL_OK):
                        leak += 1
                        leaks.append("%s=%s(未來季 %s 真值)" % (e, pv, hit[0]))
                    elif near and not A.close(pv, tv, A.TOL_OK):
                        leak += 1
                        leaks.append("%s=%s(近似未來季 %s 真值)" % (e, pv, near[0]))
                    elif near:
                        coinc += 1
            r.update({name + "_ok": ok, name + "_bad": bad, name + "_leak": leak,
                      name + "_coinc": coinc, name + "_nopack": no,
                      name + "_post": post, name + "_sigtext": sigtext,
                      name + "_types": "|".join(sorted(set(types))),
                      name + "_postcells": "; ".join(postc),
                      name + "_leakcells": "; ".join(leaks)})

        # 訊號季行的標籤—值
        sigrow = next((q for q in qs if q["period_end"] == sig), {}) or {}
        sv, ex = sigrow.get("revenue"), sigrow.get("revenue_ex991")
        r["sig_rev_eq_ex991"] = int(A.close(sv, ex, A.TOL_OK))
        r["sig_rev_vs_ex991_pp"] = (None if (sv is None or ex in (None, 0))
                                    else round((sv / ex - 1.0) * 100, 2))
        r["sig_rev_in_text"] = int(A.text_hits(text, sv))
        r["sig_rev_in_text_loose"] = int(A.text_hits(text, sv)
                                         or bare_in_text(text, sv))
        srcs = sigrow.get("signal_row_sources") or {}
        labbad, labloose = [], []
        for name in FIELDS:
            if name not in srcs:
                continue
            lab, v = srcs[name], sigrow.get(name)
            if lab == "EX-99.1 稿內文字":
                if v is None or not (A.text_hits(text, v) or bare_in_text(text, v)):
                    labbad.append("%s:標稿內但稿內無" % name)
                elif not A.text_hits(text, v):
                    labloose.append("%s:只在裸數(表格)中命中" % name)
            elif v is not None:
                labbad.append("%s:標查不到但有值" % name)
        r["label_violations"] = len(labbad)
        r["label_violations_detail"] = "; ".join(labbad)
        r["label_bare_only"] = len(labloose)
        r["label_bare_only_detail"] = "; ".join(labloose)
        r["n_sig_sources_fields"] = len(srcs)

        yy = yoy_recalc(fin, qs, rec, sig)
        stale = [k for k, v in yy.items() if fin.get(k) != v]
        yoy_rows.append({"event_id": eid, "stale": "; ".join(stale),
                         "g0_stored": fin.get("g0_signal_q_yoy"),
                         "g0_truth": yy.get("g0_signal_q_yoy"),
                         "prev_stored": fin.get("prev_q_yoy"),
                         "prev_truth": yy.get("prev_q_yoy"),
                         "accel_stored": fin.get("accel_pp"),
                         "accel_truth": yy.get("accel_pp"),
                         "accel_truth_lt2": int(
                             (yy.get("accel_pp") is not None
                              and yy["accel_pp"] < 2.0))})
        rows.append(r)
        detail += detail_local

    cols = ["event_id", "t1", "signal_q_end", "n_rows",
            "revenue_ok", "revenue_bad", "revenue_leak", "revenue_coinc",
            "revenue_sigtext", "revenue_post", "revenue_postcells",
            "gross_profit_ok", "gross_profit_bad", "gross_profit_leak",
            "gross_profit_sigtext", "gross_profit_post", "gross_profit_postcells",
            "operating_income_ok", "operating_income_bad", "operating_income_leak",
            "operating_income_sigtext", "operating_income_post",
            "operating_income_postcells",
            "ocf_ok", "ocf_bad", "ocf_leak", "ocf_sigtext", "ocf_post",
            "ocf_postcells",
            "revenue_nopack", "gross_profit_nopack", "operating_income_nopack",
            "ocf_nopack", "revenue_types", "revenue_leakcells",
            "sig_rev_eq_ex991", "sig_rev_vs_ex991_pp",
            "sig_rev_in_text", "sig_rev_in_text_loose", "has_sig_sources", "n_sig_sources_fields",
            "label_violations", "label_violations_detail",
            "label_bare_only", "label_bare_only_detail"]
    with open(OUT_DIR / "revenue_integrity_fixed.csv", "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with open(OUT_DIR / "yoy_stale.csv", "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(yoy_rows[0].keys()))
        w.writeheader()
        for r in yoy_rows:
            w.writerow(r)
    json.dump(detail, open(OUT_DIR / "revenue_integrity_fixed_detail.json", "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)

    def ids(pred):
        return sorted(r["event_id"] for r in rows if pred(r))

    anybad = ids(lambda r: any(r["%s_bad" % n] for n in FIELDS))
    revbad = ids(lambda r: r["revenue_bad"])
    leakany = ids(lambda r: any(r["%s_leak" % n] for n in FIELDS))
    postany = ids(lambda r: any(r["%s_post" % n] for n in FIELDS))
    sigdiff = ids(lambda r: r["sig_rev_eq_ex991"] == 0)
    signot = ids(lambda r: not r["sig_rev_in_text"])
    sigbare = ids(lambda r: not r["sig_rev_in_text_loose"])
    labbad = ids(lambda r: r["label_violations"])
    labbare = ids(lambda r: r["label_bare_only"])
    stale = [r["event_id"] for r in yoy_rows if r["stale"]]
    lowaccel = [r["event_id"] for r in yoy_rows if r["accel_truth_lt2"]]
    summ = {"n": len(rows), "any_bad": anybad, "rev_bad": revbad,
            "leak_any_field": leakany, "post_T1_filed_any": postany,
            "sig_rev_ne_ex991": sigdiff, "signal_rev_not_in_text": signot,
            "signal_rev_not_in_text_loose": sigbare,
            "label_violations": labbad, "label_bare_only": labbare,
            "yoy_stale": stale,
            "accel_lt2_after_fix": lowaccel, "lib_truth_diff": lib_diff,
            "sigtext_cells": {n: sum(r["%s_sigtext" % n] for r in rows)
                              for n in FIELDS},
            "type_counts": {t: len([d for d in detail if d["type"] == t])
                            for t in ("shift", "copy_prev_year", "derived_err",
                                      "other", "signal_text_vs_xbrl_differs")},
            "n_rows_ok": sum(r["revenue_ok"] for r in rows),
            "n_rows_bad": sum(r["revenue_bad"] for r in rows)}
    json.dump(summ, open(OUT_DIR / "revenue_integrity_fixed_summary.json", "w",
                         encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: (v if not isinstance(v, list) else v)
                      for k, v in summ.items()}, ensure_ascii=False)[:3000])


if __name__ == "__main__":
    main()
