# -*- coding: utf-8 -*-
"""第一部之二:只靠『收入指引上調』入池的主/後備清單事件逐宗人手核素材。
輸出 audit_out/guidance_only.json + guidance_only.txt(含原句與行號),不列公司名或代號。
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_common as C

TARGETS = [
    ("主", "E002", "0001237831-15-000057"),
    ("主", "E056", "0001628280-21-021035"),
    ("主", "E070", "0001108524-23-000046"),
    ("後備", "B031", "0001345016-22-000053"),
    ("後備", "B037", "0000950170-24-050568"),
]
UP = re.compile(r"(rais|increas|up from|above (our|its) previous|higher than (our|its) previous|"
                r"now expect|updated? (our|its)|compared to (our|its) previous|"
                r"versus (our|its) previous|from (our|its) previous)", re.I)
GUIDE = re.compile(r"(guidance|outlook|expect|forecast|anticipat|we (now )?(see|estimate))", re.I)
REV = re.compile(r"(revenue|net sales|sales|top line)", re.I)


def main():
    accs = {a for _, _, a in TARGETS}
    pop = C.load_population(accs)
    gparsed = {}
    with open(os.path.join(C.HERE, "cache", "guidance_parsed.jsonl"), encoding="utf-8") as f:
        for ln in f:
            r = json.loads(ln)
            if r["accessionNumber"] in accs:
                gparsed.setdefault(r["accessionNumber"], []).append(r)
    main_l, back_l = C.load_picks_md()
    picks = {r["accessionNumber"]: r for r in main_l + back_l}
    out = []
    lines_dump = []
    for side, eid, a in TARGETS:
        p = pop.get(a, {})
        pr = picks.get(a, {})
        rec = {"side": side, "event_id": eid, "acc": a, "year": pr.get("year"),
               "bucket": pr.get("bucket"), "filingDate": p.get("filingDate"),
               "reaction_date": p.get("reaction_date"), "sic": p.get("sic"),
               "release_timing": p.get("release_timing"),
               "csv": {k: p.get(k) for k in [
                   "improvement_type", "accel_text_hit", "accel_pp_text", "rev_g0_text",
                   "rev_prev_q_yoy", "guide_rev_raise", "guidance_metric", "guidance_period",
                   "guidance_old_lo", "guidance_old_hi", "guidance_new_lo", "guidance_new_hi",
                   "guidance_mid_change", "guidance_raise_flag", "guidance_old_missing",
                   "guidance_eps_only", "guidance_raise_eps_only", "guidance_n_records",
                   "hist_quarters_public_by_t1", "signal_rev_in_text"]},
               "parsed": [{
                   "metric": x["metric"], "period": x["period"], "old_lo": x["old_lo"],
                   "old_hi": x["old_hi"], "old_mid": x["old_mid"], "new_lo": x["new_lo"],
                   "new_hi": x["new_hi"], "new_mid": x["new_mid"],
                   "mid_change": x["mid_change"], "raise_flag": x["raise_flag"],
                   "old_missing": x["old_missing"], "old_src": x["old_src"],
                   "unit": x.get("unit"), "sentence": C.mask_text(x["sentence"])}
                   for x in gparsed.get(a, [])]}
        # 由申報原文找出含指引字眼的行(逐行,附行號)
        txt, lines = C.edgar_text(a.replace("-", "") + "__EX991.txt.gz")
        hits = [(i, C.mask_text(ln.strip()[:400])) for i, ln in enumerate(lines, 1)
                if GUIDE.search(ln) and REV.search(ln)]
        rec["text_lines_n"] = len(lines)
        rec["text_char_n"] = len(txt)
        rec["candidate_lines"] = [{"line": i, "text": t} for i, t in hits[:40]]
        rec["upgrade_lines"] = [{"line": i, "text": t} for i, t in hits if UP.search(t)][:20]
        out.append(rec)
        lines_dump.append("=" * 78)
        lines_dump.append("[%s] %s %s  filing=%s react=%s sic=%s rt=%s" %
                          (side, eid, a, p.get("filingDate"), p.get("reaction_date"),
                           p.get("sic"), p.get("release_timing")))
        lines_dump.append("  csv: " + json.dumps(rec["csv"], ensure_ascii=False))
        for x in rec["parsed"]:
            lines_dump.append("  parsed[%s/%s] old=%s-%s new=%s-%s raise=%s old_missing=%s | %s"
                              % (x["metric"], x["period"], x["old_lo"], x["old_hi"],
                                 x["new_lo"], x["new_hi"], x["raise_flag"],
                                 x["old_missing"], x["sentence"][:300]))
        for h in rec["upgrade_lines"]:
            lines_dump.append("  L%d: %s" % (h["line"], h["text"]))
    with open(os.path.join(C.OUT, "guidance_only.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    with open(os.path.join(C.OUT, "guidance_only.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines_dump) + "\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
    print(open(os.path.join(C.OUT, "guidance_only.txt"), encoding="utf-8").read())
