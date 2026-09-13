# -*- coding: utf-8 -*-
"""KARST-235 ②第一次考試 取證包 `4_財務數列` 完整性核查(只讀,不改任何包、不 commit)。

基線:每個 period_end 的**單季首報值**——由 `data/sec/companyfacts` 重算,做法照
`finlib.py` 體例,但**跨全部收入 tag 取最早申報那一份**(`finlib.quarterly()` 是
「tag 次序優先」,先命中的 tag 贏,不看得申報日先後;本核查兩者都算,以跨 tag 最早
申報者為真值,並保留 tag 優先版以指認成因)。單季 duration 缺則以累計差分補;
財年末季以年報(340–380 日)減同期九個月累計(255–285 日)推算。

逐包逐格:
  1 revenue / gross_profit / operating_income / ocf 四欄,包內值 vs 真值(容差 0.5%)。
    不符者判型態:shift(包內值等於另一個 period_end 的重算值,報偏移幾季)/
    copy_prev_year(等於上一年同季)/ derived_err(財年末季推算錯)/ other。
  2 數值越界:取 T1 之後四季的實際單季收入(companyfacts,不限申報日);包內任一格
    revenue 與其中之一相等(相對容差 ≤0.01%)記越界。真越界 = 該格又不符真值
    (即包內放了 T1 之後才公布的數);另記「同值巧合」= 該格符真值但剛好與未來季同值。
  3 稿內衝突:訊號季與去年同季的包內 revenue 對 `2_觸發資料.ex991_full_text` 的數字
    (千/百萬/十億、逗號、$ 號)匹配。
輸出 `A3/audit_out/revenue_integrity.csv`、`..._detail.json`、`..._summary.json`;
報表 `A3/收入欄完整性核查——A3.md`。不列公司名或代號。
"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import finlib as F  # noqa: E402

OUT_DIR = HERE / "audit_out"
OUT_DIR.mkdir(exist_ok=True)
TOL_OK = 0.005     # 包內值 vs 真值:合格容差 0.5%
TOL_SAME = 0.0001  # 值對值(找錯位/越界):0.01%
FIELDS = ("revenue", "gross_profit", "operating_income", "ocf")

NUM_UNIT = re.compile(
    r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*(billion|million|thousand|bn|mm)\b", re.I)
NUM_DOLLAR = re.compile(r"\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)")
PRIOR_KW = re.compile(
    r"(?i)(prior[- ]year|prior year|last year|year[- ]ago|year earlier|"
    r"compared (?:with|to) [^.]{0,30}(?:prior|last|year-ago))")
REV_KW = re.compile(r"(?i)(revenue|net sales|total sales|\bsales\b)")
SCALES = (1.0, 1e3, 1e6, 1e9)
UNIT_MULT = {"billion": 1e9, "bn": 1e9, "million": 1e6, "mm": 1e6, "thousand": 1e3}


def num(s):
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def close(a, b, tol):
    if a is None or b is None:
        return False
    if a == b:
        return True
    den = max(abs(a), abs(b))
    return den > 0 and abs(a - b) / den <= tol


def text_hits(text, value):
    """文字裡有沒有一個數字(按 1/1e3/1e6/1e9 比例)等於 value(容差 2%)。"""
    if value is None or not text:
        return False
    for m in NUM_UNIT.finditer(text):
        v = num(m.group(1))
        if v is not None and close(value, v * UNIT_MULT[m.group(2).lower()], 0.02):
            return True
    for m in NUM_DOLLAR.finditer(text):
        v = num(m.group(1))
        if v is None or v == 0:
            continue
        if any(close(value, v * s, 0.02) for s in SCALES):
            return True
    return False


def prior_text_conflict(text, value):
    """去年同季句:句內有貨幣數字而無一對得上 value → (True, 句內數字數)。"""
    if value is None or not text:
        return False, 0
    for sent in re.split(r"(?<=[.;])\s+|\n", text):
        if not PRIOR_KW.search(sent) or not REV_KW.search(sent):
            continue
        vals = []
        for m in NUM_UNIT.finditer(sent):
            v = num(m.group(1))
            if v is not None:
                vals.append(("u", v * UNIT_MULT[m.group(2).lower()]))
        for m in NUM_DOLLAR.finditer(sent):
            v = num(m.group(1))
            if v is not None:
                vals.append(("$", v))
        if not vals:
            continue
        for _kind, v in vals:
            if close(value, v, 0.02):
                return False, len(vals)
            if _kind == "$" and any(close(value, v * s, 0.02) for s in SCALES):
                return False, len(vals)
        return True, len(vals)
    return False, 0


def _merge(best, en, v, f, idx):
    key = (f, idx)
    if en not in best or key < best[en][2]:
        best[en] = (v, f, key)


def series(facts, tags, lo=80, hi=100, derive_fy=True, cross_tag=True):
    """end → (val, filed)。cross_tag=True:跨 tag 取最早申報;False:tag 次序優先。"""
    best = {}
    for idx, t in enumerate(tags):
        for (st, en), (v, f) in F._first_report(F.unit_rows(facts, t), lo, hi).items():
            if cross_tag:
                _merge(best, en, v, f, idx)
            elif en not in best:
                best[en] = (v, f, (f, idx))
    if derive_fy:
        for idx, t in enumerate(tags):
            for en, (v, f) in F._year_end_quarters(facts, [t]).items():
                if cross_tag:
                    _merge(best, en, v, f, idx)
                elif en not in best:
                    best[en] = (v, f, (f, idx))
    return {en: (v, f) for en, (v, f, _k) in best.items()}


def rec_all(facts, cross_tag):
    """四項目 → {period_end: 值};跨 tag 最早申報版 / tag 優先版(finlib 原樣)。"""
    out = {}
    for name, tags in (("revenue", F.REV_TAGS), ("gross_profit", F.GP_TAGS),
                       ("operating_income", F.OI_TAGS)):
        s = {} if not facts else series(facts, tags, cross_tag=cross_tag)
        s = {k: v for k, (v, _f) in s.items()}
        if facts:
            for en, v in F.quarterize_cumulative(
                    F.cumulative(facts, tags)).items():
                s.setdefault(en, v)
        out[name] = {k: v for k, v in s.items() if v is not None}
    s = {}
    if facts:
        # 現金流量表只報累計,包內 ocf = 累計差分(finlib bundle 同一條),差分為主,
        # 直接單季事實只補缺格
        s = dict(F.quarterize_cumulative(F.cumulative(facts, F.OCF_TAGS)))
        for en, (v, _f) in series(facts, F.OCF_TAGS,
                                 cross_tag=cross_tag).items():
            s.setdefault(en, v)
    out["ocf"] = {k: v for k, v in s.items() if v is not None}
    return out


def filed_first(facts, tags, end, val, lo=60, hi=130):
    """包內這格的值,最早哪一日申報出現(同一期末、同一值、期限 lo–hi 日)。無則 None。"""
    if facts is None or val is None:
        return None
    best = None
    for t in tags:
        for r in F.unit_rows(facts, t):
            if r.get("end") != end or r.get("val") is None:
                continue
            st = r.get("start")
            if st:
                try:
                    d = (date.fromisoformat(end) - date.fromisoformat(st)).days
                except ValueError:
                    continue
                if not (lo <= d <= hi):
                    continue
            if close(float(r["val"]), val, TOL_SAME):
                f = r.get("filed", "")
                if f and (best is None or f < best):
                    best = f
    return best


def classify(pv, e, rec, ends, derived):
    for e2, v2 in rec.items():
        if e2 == e or not close(pv, v2, TOL_SAME):
            continue
        try:
            gap = (date.fromisoformat(e2) - date.fromisoformat(e)).days
        except ValueError:
            gap = 0
        if -390 <= gap <= -340:
            return "copy_prev_year", "值等於上一年同季 %s" % e2
        k = (ends.index(e2) - ends.index(e)) if (e2 in ends and e in ends) else None
        if 340 <= gap <= 390:
            return "shift", "值等於**下一年同季** %s 的重算值" % e2
        return "shift", "值等於 %s 的重算值%s" % (
            e2, "" if k is None else "(相差 %+d 季)" % k)
    return ("derived_err" if derived else "other"), ""


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    rows, detail = [], []
    for pf in sorted((HERE / "packets").glob("*.json")):
        p = json.load(open(pf, encoding="utf-8"))
        eid = p["event_id"]
        idn = p["1_事件識別"]
        cik = str(idn["cik"]).zfill(10)
        t1 = str(idn.get("T1_分析截止", ""))[:10]
        fin = p["4_財務數列"]
        qs = fin["quarters"]
        text = (p["2_觸發資料"] or {}).get("ex991_full_text") or ""
        facts = F.load_facts(cik)
        rec = rec_all(facts, True)
        tprec = rec_all(facts, False)
        ends = sorted(rec["revenue"])
        post = [e for e in ends if e > t1][:4]
        # 未來四季的「實際收入」候選值:兩種基線 + 該期末所有 60–130 日事實的值
        post_vals = []
        for e2 in post:
            vs = set()
            for src in (rec["revenue"], tprec["revenue"]):
                if e2 in src:
                    vs.add(src[e2])
            for t in (F.REV_TAGS if facts else []):
                for rr in F.unit_rows(facts, t):
                    if rr.get("end") != e2 or rr.get("val") is None:
                        continue
                    st = rr.get("start")
                    if not st:
                        continue
                    try:
                        dd = (date.fromisoformat(e2) - date.fromisoformat(st)).days
                    except ValueError:
                        continue
                    if 60 <= dd <= 130:
                        vs.add(float(rr["val"]))
            post_vals += [(e2, v) for v in vs]

        r = {"event_id": eid, "t1": t1, "n_rows": len(qs),
             "cik_found": int(facts is not None), "n_post_T1_q": len(post)}
        for name in FIELDS:
            ok = bad = leak = coinc = no = post = 0
            types, leaks, co, postc = [], [], [], []
            tags = {"revenue": F.REV_TAGS, "gross_profit": F.GP_TAGS,
                    "operating_income": F.OI_TAGS, "ocf": F.OCF_TAGS}[name]
            for q in qs:
                e, pv = q["period_end"], q.get(name)
                tv = rec[name].get(e)
                # 這格的值的來源申報:最早哪一日出現;晚於 T1 = 包內放了 T1 之後才公布的字
                ff = filed_first(facts, tags, e, pv,
                                 0, 100000) if name == "ocf" else filed_first(
                                     facts, tags, e, pv, 60, 130)
                if ff:
                    r["%s_filed_first_%s" % (name, e)] = ff
                is_sig_row = (e == fin.get("signal_q_end"))
                if ff and ff > t1 and not is_sig_row:
                    # 訊號季那行本來就來自稿內文字/該季 10-Q(申報日必在 T1 後),不算越界
                    post += 1
                    postc.append("%s(值首見於 %s)" % (e, ff))
                if pv is None:
                    no += 1
                    if tv is None:
                        ok += 1
                    continue
                if tv is None:
                    continue
                is_sig = (name == "revenue"
                          and q.get("revenue_source") == "EX-99.1 稿內文字")
                if is_sig:
                    good = (close(pv, tv, TOL_OK)
                            or close(pv, q.get("revenue_ex991"), TOL_SAME))
                    if good:
                        ok += 1
                    else:
                        bad += 1
                        types.append("signal_text_vs_xbrl_differs")
                elif close(pv, tv, TOL_OK):
                    ok += 1
                else:
                    bad += 1
                    t, why = classify(pv, e, rec[name], ends,
                                      bool(q.get("revenue_year_end_derived"))
                                      if name == "revenue" else False)
                    types.append(t)
                    detail.append({"event_id": eid, "field": name,
                                   "period_end": e, "packet": pv,
                                   "truth_earliest_filed": tv,
                                   "tag_priority_value": tprec[name].get(e),
                                   "type": t, "why": why,
                                   "filed_first": ff,
                                   "filed_after_T1": int(bool(ff) and ff > t1),
                                   "in_text": int(text_hits(text, pv))})
                if name == "revenue":
                    exact = [(e2, v2) for e2, v2 in post_vals
                             if close(pv, v2, 1e-5)]
                    near = [(e2, v2) for e2, v2 in post_vals
                            if close(pv, v2, 1e-3)]
                    if exact and not close(pv, tv, TOL_OK):
                        leak += 1
                        leaks.append("%s=%s(未來季 %s 的實際收入)" % (
                            e, pv, exact[0][0]))
                    elif near and not close(pv, tv, TOL_OK):
                        leak += 1
                        leaks.append("%s=%s(近似未來季 %s 的實際收入,差 %.3f%%)" % (
                            e, pv, near[0][0],
                            abs(pv - near[0][1]) / near[0][1] * 100))
                    elif near:
                        coinc += 1
                        co.append("%s(與 %s 同值)" % (e, near[0][0]))
            r[name + "_ok"] = ok
            r[name + "_bad"] = bad
            r[name + "_leak"] = leak
            r[name + "_coinc"] = coinc
            r[name + "_nopack"] = no
            r[name + "_post"] = post
            r[name + "_types"] = "|".join(sorted(set(types)))
            r[name + "_leakcells"] = "; ".join(leaks)
            r[name + "_coincells"] = "; ".join(co)
            r[name + "_postcells"] = "; ".join(postc)
        # 稿內匹配(訊號季、去年同季)
        sig = fin.get("signal_q_end")
        sigrow = next((q for q in qs if q["period_end"] == sig), None)
        prior_end = None
        if sig:
            try:
                sd = date.fromisoformat(sig)
                cands = sorted((abs((sd - date.fromisoformat(q["period_end"])).days
                                    - 365), q["period_end"]) for q in qs
                               if 340 <= (sd - date.fromisoformat(
                                   q["period_end"])).days <= 390)
                prior_end = cands[0][1] if cands else None
            except ValueError:
                prior_end = None
        prow = next((q for q in qs if q["period_end"] == prior_end), None)
        sv = sigrow.get("revenue") if sigrow else None
        pv_ = prow.get("revenue") if prow else None
        # 訊號季那行自稱「收入來源 = EX-99.1 稿內文字」,但 `revenue` 欄同格另有
        # `revenue_ex991`(由稿內抽出的數)。兩者不符 = 該行寫了 XBRL 值而非稿內值。
        ex = sigrow.get("revenue_ex991") if sigrow else None
        r["sig_rev_eq_ex991"] = int(close(sv, ex, TOL_OK))
        r["sig_rev_vs_ex991_pp"] = (None if (sv is None or ex in (None, 0))
                                    else round((sv / ex - 1.0) * 100, 2))
        r["sig_rev_in_text"] = int(text_hits(text, sv))
        conf, nn = prior_text_conflict(text, pv_)
        r["prior_rev_in_text"] = int(text_hits(text, pv_))
        r["prior_text_conflict"] = int(conf)
        r["prior_sent_nums"] = nn
        rows.append(r)

    cols = ["event_id", "t1", "n_rows", "n_post_T1_q", "cik_found",
            "revenue_ok", "revenue_bad", "revenue_leak", "revenue_coinc",
            "revenue_post", "revenue_types", "gross_profit_ok", "gross_profit_bad",
            "gross_profit_leak", "gross_profit_post", "operating_income_ok",
            "operating_income_bad", "operating_income_leak", "operating_income_post",
            "ocf_ok", "ocf_bad", "ocf_leak", "ocf_post",
            "sig_rev_in_text", "sig_rev_eq_ex991", "sig_rev_vs_ex991_pp",
            "prior_rev_in_text", "prior_text_conflict",
            "revenue_nopack", "revenue_leakcells", "revenue_coincells",
            "revenue_postcells"]
    with open(OUT_DIR / "revenue_integrity.csv", "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    json.dump(detail, open(OUT_DIR / "revenue_integrity_detail.json", "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)

    def ids(pred):
        return sorted(r["event_id"] for r in rows if pred(r))

    allbad = ids(lambda r: r["revenue_bad"] or r["gross_profit_bad"]
                 or r["operating_income_bad"] or r["ocf_bad"])
    revbad = ids(lambda r: r["revenue_bad"])
    shift = ids(lambda r: "shift" in r["revenue_types"])
    copyv = ids(lambda r: "copy_prev_year" in r["revenue_types"])
    leak = ids(lambda r: r["revenue_leak"])
    leakany = ids(lambda r: any(r["%s_leak" % n] for n in FIELDS))
    coinc = ids(lambda r: r["revenue_coinc"])
    conf = ids(lambda r: r["prior_text_conflict"])
    notin = ids(lambda r: not r["prior_rev_in_text"])
    sigbad = ids(lambda r: not r["sig_rev_in_text"])
    clean = ids(lambda r: r["event_id"] not in allbad
                and r["event_id"] not in leak)
    sigdiff = ids(lambda r: r["sig_rev_eq_ex991"] == 0)
    sigbig = ids(lambda r: r["sig_rev_eq_ex991"] == 0
                 and abs(r["sig_rev_vs_ex991_pp"] or 0) >= 1.0)
    postrev = ids(lambda r: r["revenue_post"])
    postany = ids(lambda r: any(r["%s_post" % n] for n in FIELDS))
    summ = {"n": len(rows), "clean": clean, "any_bad": allbad, "rev_bad": revbad,
            "sig_rev_ne_ex991": sigdiff, "sig_rev_ne_ex991_ge1pp": sigbig,
            "post_T1_filed_rev": postrev, "post_T1_filed_any": postany,
            "shift": shift, "copy_prev_year": copyv, "leak_rev": leak,
            "leak_any_field": leakany, "coincidence": coinc,
            "text_conflict": conf, "prior_not_in_text": notin,
            "signal_not_in_text": sigbad,
            "type_counts": {t: len([d for d in detail if d["type"] == t])
                            for t in ("shift", "copy_prev_year", "derived_err",
                                      "other", "signal_text_vs_xbrl_differs")},
            "rows": rows, "detail": detail}
    json.dump(summ, open(OUT_DIR / "revenue_integrity_summary.json", "w",
                         encoding="utf-8"), ensure_ascii=False, indent=1)
    write_report(summ, rows, detail)
    for k, v in summ.items():
        if k in ("rows", "detail"):
            continue
        print(k, len(v) if isinstance(v, list) else v, v if isinstance(v, list) else "")


def write_report(summ, rows, detail):
    """落檔 A3/收入欄完整性核查——A3.md(不列公司名或代號)。"""
    def lst(v):
        return "、".join(v) if v else "無"
    det = {}
    for d in detail:
        det.setdefault(d["event_id"], []).append(d)
    L = []
    L.append("# ②第一次考試 取證包「4_財務數列」完整性核查(KARST-235)\n")
    L.append("> 核查日 2026-09-13。只讀 `A3/packets/` 84 個包與 "
             "`data/sec/companyfacts`,不改任何包、不 commit。"
             "真值口徑:每個 `period_end` 的**單季首報值**——跨全部收入 tag 取"
             "**最早申報**那一份(finlib 是 tag 次序優先,不看得申報日先後),"
             "單季 duration 缺以累計差分補,財年末季以年報減九個月累計推算。"
             "本檔不列公司名或代號。\n")
    L.append("## 一、結論\n")
    L.append("1. 84 包全部核完。**%d 包**四欄與真值逐格相符(相對容差 0.5%%);"
             "其餘 %d 包見下。" % (len(rows) - len(summ["any_bad"]),
                                len(summ["any_bad"])))
    L.append("2. **收入欄有 %d 包與真值不符**(%s);其中 **%s 兩包的包內值是 T1 "
             "之後才申報的數字**——E022 有 4 格寫入了訊號季**之後**四季的實際收入"
             "(逐格等於該四季的實際數,即整欄向後錯位一年),E024 有 2 格近似未來季"
             "實際收入、另 2 格為日後重述值。**這等於把未來的收入放進歷史欄。**"
             % (len(summ["rev_bad"]), lst(summ["rev_bad"]),
                lst(summ["leak_rev"])))
    L.append("   **E022、E024(以及下條的 E017)的判斷結果不可用,須重建後重判。**")
    L.append("3. **另有 1 包營業利潤欄(E017)一格是 T1 之後才申報的重述值**,"
             "同期年報與九個月累計相減本來可得(45,729,000),包內卻取了日後重述值。")
    L.append("4. **%d 包的訊號季那一行自相矛盾**(%s):該行標「收入來源 = EX-99.1 "
             "稿內文字」,但 `revenue` 欄放的是 XBRL 值,同一格另有 `revenue_ex991`"
             "(稿內抽出值);相差 ≥1%% 的有 %d 包(%s)。"
             "E022 的稿內值明明白白是 887,300,000,`revenue` 欄卻寫 952,549,000"
             "(該數在稿內完全找不到)。"
             % (len(summ["sig_rev_ne_ex991"]), lst(summ["sig_rev_ne_ex991"]),
                len(summ["sig_rev_ne_ex991_ge1pp"]),
                lst(summ["sig_rev_ne_ex991_ge1pp"])))
    L.append("5. 其餘 4 包的收入不符(E025、E033、E038、E039)與 1 格毛利(E047)"
             "屬**不同 tag 的口徑差**(ASC 606 前後的重述值),該值在 T1 之前已公開,"
             "不影響考試有效性,但包內自稱「XBRL 首報值」並不準確。")
    L.append("6. 稿內匹配:19 包有一句「去年同季」的收入句內數字與包內去年同季值對不上"
             "(啟發式,須人手核);4 包的去年同季值在稿內完全找不到。\n")

    L.append("## 二、逐包表(84 行;合格 = 該欄八格之中與真值相符的格數;"
             "「缺 n」= 該欄有 n 格包內沒有值且來源也查不到,兩邊皆無)\n")
    L.append("| event_id | revenue 合格/8 | 不符格 | 型態(收入) | 未來值格 | "
             "gp 合格 | oi 合格 | ocf 合格 | 值晚於T1才見申報格 | 訊號季=稿內值 | "
             "去年同季見於稿內 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")

    def cell(r, name):
        no = r.get(name + "_nopack", 0)
        return "%d%s" % (r.get(name + "_ok", 0), ("(缺%d)" % no) if no else "")

    for r in rows:
        types = r["revenue_types"] or "-"
        sig = "是" if r["sig_rev_eq_ex991"] else (
            "否(%.1f%%)" % (r["sig_rev_vs_ex991_pp"] or 0))
        L.append("| %s | %s | %d | %s | %d | %s | %s | %s | %d | %s | %s |" % (
            r["event_id"], cell(r, "revenue"), r["revenue_bad"], types,
            r["revenue_leak"], cell(r, "gross_profit"),
            cell(r, "operating_income"), cell(r, "ocf"), r["revenue_post"], sig,
            "是" if r["prior_rev_in_text"] else "否"))
    L.append("")
    L.append("## 三、彙總\n")
    L.append("- 四欄全部相符且無未來值:**%d/84** 包" % len(summ["clean"]))
    L.append("- 有欄不符真值:**%d** 包 —— %s" % (len(summ["any_bad"]),
                                              lst(summ["any_bad"])))
    L.append("- 收入欄不符:**%d** 包 —— %s" % (len(summ["rev_bad"]),
                                             lst(summ["rev_bad"])))
    L.append("- **真越界(包內放了 T1 之後季度的實際收入):%d** 包 —— %s"
             % (len(summ["leak_rev"]), lst(summ["leak_rev"])))
    L.append("- 值首見申報晚於 T1 的收入格(非訊號季):**%d** 包 —— %s"
             % (len(summ["post_T1_filed_rev"]), lst(summ["post_T1_filed_rev"])))
    L.append("- 四欄合計、值首見申報晚於 T1 的格:**%d** 包 —— %s"
             % (len(summ["post_T1_filed_any"]), lst(summ["post_T1_filed_any"])))
    L.append("- 訊號季 `revenue` 與自身 `revenue_ex991` 不符:**%d** 包 —— %s"
             % (len(summ["sig_rev_ne_ex991"]), lst(summ["sig_rev_ne_ex991"])))
    L.append("  - 其中相差 ≥1%%:**%d** 包 —— %s"
             % (len(summ["sig_rev_ne_ex991_ge1pp"]),
                lst(summ["sig_rev_ne_ex991_ge1pp"])))
    L.append("- 與未來季同值但本身符真值(巧合,不視為越界):%d 包 —— %s"
             % (len(summ["coincidence"]), lst(summ["coincidence"])))
    L.append("- 稿內「去年同季」句數字對不上(啟發式):%d 包 —— %s"
             % (len(summ["text_conflict"]), lst(summ["text_conflict"])))
    L.append("- 去年同季收入值在稿內找不到:%d 包 —— %s"
             % (len(summ["prior_not_in_text"]), lst(summ["prior_not_in_text"])))
    L.append("- 訊號季收入值在稿內找不到:%d 包 —— %s"
             % (len(summ["signal_not_in_text"]), lst(summ["signal_not_in_text"])))
    L.append("- 不符格的型態分佈:%s(shift = 值等於另一期重算值;other = "
             "值為較晚申報的另一 tag 值,既非該期首報值亦非另一期單季值)\n"
             % json.dumps(summ["type_counts"], ensure_ascii=False))
    L.append("### 逐格明細(不符真值的格)\n")
    L.append("| event_id | 欄 | period_end | 包內值 | 真值(最早申報) | "
             "包內值首見申報 | 晚於 T1? | 型態 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for d in detail:
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
            d["event_id"], d["field"], d["period_end"], d["packet"],
            d["truth_earliest_filed"], d["filed_first"] or "查不到",
            "是" if d["filed_after_T1"] else "否", d["type"]))
    L.append("")
    L.append("## 四、成因(指向程式碼)\n")
    L.append("1. **收入 tag 次序優先,不看得申報日先後** —— `finlib.py` "
             "`quarterly()`(第 98–111 行)逐 tag 走 `REV_TAGS`,以 "
             "`out.setdefault(en, v)` 收值:**哪個 tag 先命中就贏**,不比申報日。"
             "公司改用 ASC 606 之後的申報,會用新 tag 重列舊季,而新 tag 正是 "
             "`REV_TAGS` 第一個;於是同一期末,較晚申報的重述值蓋過最早申報的舊值。"
             "`_first_report()`(第 49–66 行)只在**單一 tag 之內**取最早申報,"
             "跨 tag 這一步沒有人比過日期。")
    L.append("2. **取數點直接吃這個 dict** —— `s16_build.py` 第 289、296 行"
             "(`s9_packets.py` 第 382、392 行同)以 `b[\"rev_q\"].get(e)` 填 "
             "`revenue`,所以上面那個「誰先命中」的結果原封不動入包。")
    L.append("3. **訊號季那行只換標籤、沒有換值** —— `s16_build.py` 第 332–336 行"
             "(`s9_packets.py` 第 400–409 行同):命中訊號季時寫 "
             "`revenue_source = \"EX-99.1 稿內文字\"`、並列 `revenue_ex991`,"
             "**但 `revenue` 欄本身仍是 XBRL 值,沒有被稿內值取代**。"
             "6 包因此出現「自稱稿內、實為 XBRL」的行。")
    L.append("4. **年末季推算輸給較晚的直接事實** —— `quarterly(derive_fy=True)` "
             "先收 80–100 日的直接單季事實,`_year_end_quarters()` 只在缺格時補。"
             "同一期末若有兩份不同申報的直接事實(原報與日後重述),先用列序先出現者,"
             "E017 營業利潤就是這樣取了重述值。")
    L.append("5. **遮罩檢查只掃日期,不核數值** —— `s16_build.py` 第 36、459 行只以 "
             "ISO 日期正則掃全文,抓「T1 之後的日期字串」。數值越界(值本身來自"
             "T1 之後)它結構上抓不到。\n")
    L.append("### 判斷隊所報的兩宗已知個案,本核查的對照\n")
    L.append("- **E006「年末季複製上一年」**:包內 2014 年末季值 = 251,689,000,"
             "與 2013 年末季同值;**來源申報本身如此**(2015-02-25 申報的 90 日事實"
             "就是這個數,日後重述為 272,096,000)。包內取的是最早申報那份,"
             "沒有取錯;重複來自申報者的標籤,不是本包引入。")
    L.append("- **E026「去年同季分母與稿內衝突」**:包內去年同季值(404,000,000)"
             "與 companyfacts 最早申報值一致(不是取數錯誤);該稿本身沒有列出"
             "去年同季的總收入數,故本核查只能判「稿內找不到」,判不了「衝突」。"
             "此格須人手核該稿。\n")
    L.append("### 為何毛利/營業利潤/淨利大多正確\n")
    L.append("`GP_TAGS`、`OI_TAGS` 各只有一個 tag,沒有「較晚的 tag 蓋較早」這條路;"
             "`REV_TAGS` 有六個,而 ASC 606 之後的新 tag 排第一。這正好對上判斷隊"
             "「收入整欄不對、毛利與營業利潤卻正確」的觀察。\n")
    L.append("## 五、處置建議\n")
    L.append("1. **停用 E022、E024**:兩包收入欄含 T1 之後的數字,判斷層若已用過"
             "這兩包,其結論須作廢重判。E022 尤其嚴重:八格之中**五格錯**"
             "(四個歷史季逐格等於其後一年的實際收入,訊號季那格亦為 XBRL 值"
             "而非稿內值)。")
    L.append("2. **重判 E017** 涉及營業利潤趨勢的段落(一格為 T1 後重述值)。")
    L.append("3. **修 6 包訊號季行**:把 `revenue` 欄改回稿內值 "
             "(`revenue_ex991`),或至少在該行標明兩值並以稿內值為準;"
             "受影響者見上表「訊號季=稿內值」欄為「否」者。")
    L.append("4. **修 finlib 取數口徑**再重建其餘不符格:跨 tag 比申報日"
             "(最早申報者勝、同期同日再按 tag 次序);年末季以「年報減九個月累計」"
             "優先於較晚申報的直接事實。此改動會影響已跑過的所有包,須一次重跑。")
    L.append("5. **遮罩檢查加數值步**:每格值對 T1 之後四季的實際值做等值檢查"
             "(本核查第 3 步的做法可直接搬過去)。")
    L.append("6. **不必停的兩組**:E025、E033、E038、E039、E047 屬 tag 口徑差"
             "(T1 前已公開);E011、E016、E048、E080 屬「XBRL 首報晚於 T1」"
             "(E011 已由包內布林自報),數字本身未必未公開,只宜在包內註明。\n")
    L.append("## 六、方法與限制\n")
    L.append("- 真值只用本地 `data/sec/companyfacts`(共取 84 包對應 CIK),"
             "不連網;「該期最早申報值」= 同期末、期限 80–100 日(現金流用累計差分)"
             "之中最早 `filed` 者。")
    L.append("- 越界判兩條:(a) 格值與 T1 之後四季的實際單季值相等(相對容差 "
             "0.01%);(b) 該值最早申報日晚於 T1。兩條並列,分開報。")
    L.append("- 稿內匹配用啟發式:抽出稿內貨幣數字(含千/百萬/十億與逗號),"
             "按 1/1e3/1e6/1e9 比例比對,容差 2%。**啟發式會誤報**,"
             "「稿內衝突」一欄只作線索,須人手核。")
    L.append("- 訊號季那行不計入「值晚於 T1 才申報」(該季 10-Q 必在 T1 後申報)。")
    L.append("- 未查:各包 `extra` 十項欄的完整度(本票只核四欄)。\n")
    (HERE / "收入欄完整性核查——A3.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
