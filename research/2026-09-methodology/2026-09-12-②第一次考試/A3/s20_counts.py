# -*- coding: utf-8 -*-
"""KARST-232 第十一步前置:把補強紀錄要用的數量全部由成品重算,寫 cache/enrich_counts.json。"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "packets"


def main() -> None:
    picks = json.loads((CACHE / "picks_final.json").read_text(encoding="utf-8"))
    stats = json.loads((CACHE / "enrich_stats.json").read_text(encoding="utf-8"))
    c = {}
    c["packets"] = len(picks["final"])
    c["swaps"] = len(picks["swaps"])
    c["swap_same_year_bucket"] = sum(1 for s in picks["swaps"] if s["same_year_bucket"])
    c["backup_used"] = picks["n_backup_used"]
    c["backup_left"] = len(picks["backups_left"])
    c["hashes"] = picks["hashes"]
    c["peer_rule"] = {k: stats["packets"][k] for k in
                      ("peer_sic4", "peer_sic3", "peer_insufficient")}
    method = Counter()
    n_sent = 0
    n_prior_found = 0
    n_prior_none = 0
    tr = Counter()
    n_tr_dump = 0
    n_prelim = 0
    for f in picks["final"]:
        d = json.loads((OUT / ("%s.json" % f["slot"])).read_text(encoding="utf-8"))
        t = d["2_觸發資料"]
        pr = t["prior_release_guidance"]
        if isinstance(pr, dict) and pr.get("accessionNumber"):
            n_prior_found += 1
            m = pr.get("method", "")
            if pr.get("guidance_sentences"):
                n_sent += 1
                method["s6 解析器" if m.startswith("s6") else "後備標記掃描"] += 1
            else:
                method["有稿無句"] += 1
        else:
            n_prior_none += 1
        n_prelim += int(t["preliminary_release"] is True)
        x = t["earnings_call_transcript"]
        if isinstance(x, str):
            tr["查不到"] += 1
        else:
            tr["注入"] += 1
            n_tr_dump += int(isinstance(x, dict) and "head_50" in json.dumps(x))
        for lab, dv in d["3_截止前文件"].items():
            c.setdefault("doc_slots_total", 0)
            c["doc_slots_total"] += int(isinstance(dv, dict))
    c["prior"] = {"有稿": n_prior_found, "有句": n_sent, "無稿": n_prior_none,
                  "method": dict(method)}
    c["prelim_true"] = n_prelim
    c["transcript"] = dict(tr)
    c["transcript_dump_path_only"] = n_tr_dump
    c["extra_coverage"] = stats["extra_coverage"]
    c["extra_signal_quarter"] = stats["extra_signal_quarter"]
    c["mask_bad"] = stats["packets"]["mask_bad"]
    c["peer_capex_empty"] = stats["packets"]["peer_capex_empty"]
    c["peer_no_annual"] = stats["packets"]["peer_no_annual"]
    print(json.dumps(c, ensure_ascii=False, indent=1))
    (CACHE / "enrich_counts.json").write_text(
        json.dumps(c, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
