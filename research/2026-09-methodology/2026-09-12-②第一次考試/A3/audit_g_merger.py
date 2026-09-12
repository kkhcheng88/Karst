# -*- coding: utf-8 -*-
"""KARST-230 第一部 (e) 之二:併購排除獨立核 —— 對 20 宗自找同日 8-K 本地檔,
掃 Item 2.01 / Item 1.01 與併購字眼,驗「應排未排」與「不應排而排」。
輸出 audit_out/merger.json + merger.txt。不列公司名或代號。
"""
import glob, gzip, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_common as C

ITEM201 = re.compile(r"Item\s*2\.01", re.I)
ITEM101 = re.compile(r"Item\s*1\.01", re.I)
MERGE = re.compile(r"agreement and plan of merger|plan of merger|merger agreement|"
                   r"to be acquired|acquired by|acquisition of .{0,40}by|business combination", re.I)


def find8k(acc):
    nd = acc.replace("-", "")
    cands = [nd + "__8k.txt.gz", nd + "__8k1.txt.gz", nd + "__8k2.txt.gz"]
    for c in cands:
        p = os.path.join(C.EDGAR, c)
        if os.path.exists(p):
            with gzip.open(p, "rt", encoding="utf-8", errors="replace") as f:
                return c, f.read()
    return None, None


def main():
    s = C.load_sample()
    rows = [(g, r) for g, rs in s["groups"].items() for r in rs]
    pop = C.load_population({r["accessionNumber"] for _, r in rows})
    out = []
    for g, r in rows:
        a = r["accessionNumber"]
        p = pop[a]
        ex9, _ = C.edgar_text(a.replace("-", "") + "__EX991.txt.gz")
        f8, t8 = find8k(a)
        m9 = MERGE.findall(ex9)
        rec = {"group": g, "acc": a, "eightk_file": f8,
               "eightk_items": None, "eightk_201": None, "eightk_101": None,
               "eightk_msame": None, "ex991_merger_words": len(m9),
               "ex991_merger_samples": [C.mask_text(x[:60]) for x in m9[:3]],
               "csv_excl_2_01": p.get("excl_merger_2_01"), "csv_excl_1_01": p.get("excl_merger_1_01"),
               "csv_excl_1_01_old": p.get("excl_merger_1_01_old"),
               "csv_merger_text_pending": p.get("merger_text_pending"),
               "csv_items_same_day": None, "entry_pool": p.get("entry_pool"),
               "improvement_type": p.get("improvement_type")}
        if t8 is not None:
            head = t8[:20000]
            rec["eightk_201"] = bool(ITEM201.search(head))
            rec["eightk_101"] = bool(ITEM101.search(head))
            rec["eightk_msame"] = len(MERGE.findall(t8))
            ms = re.findall(r"Item\s*(\d\.\d\d)", head, re.I)
            rec["eightk_items"] = sorted(set(ms))
        out.append(rec)
    with open(os.path.join(C.OUT, "merger.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    L = []
    for r in out:
        L.append("%s %s 8K=%s items=%s 2.01=%s 1.01=%s 8KmergerWords=%s EX991mergerWords=%s "
                 "csv(2.01=%s 1.01=%s old=%s pending=%s) pool=%s type=%s"
                 % (r["group"], r["acc"], r["eightk_file"], r["eightk_items"], r["eightk_201"],
                    r["eightk_101"], r["eightk_msame"], r["ex991_merger_words"],
                    r["csv_excl_2_01"], r["csv_excl_1_01"], r["csv_excl_1_01_old"],
                    r["csv_merger_text_pending"], r["entry_pool"], r["improvement_type"]))
        for x in r["ex991_merger_samples"]:
            L.append("     稿內併購字眼: %s" % x)
    with open(os.path.join(C.OUT, "merger.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
