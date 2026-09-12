# -*- coding: utf-8 -*-
"""KARST-232 第六步(補):同業年報本身不含資本開支時,改看同一申報的附件。

兩種情況:(一)40-F 類,年報本文只是封面,實質年報是 EX-99 附件;
(二)10-K 的財務報表以引註方式併入(本文無現金流量表)。
做法:抓該筆申報的 `index.json`,排除主文件後按名稱挑候選(年報/EX-13/EX-99/財務),
每個申報最多試 3 份,抽到即止。單線程 3 請求/秒,原文寫 `A/edgar_cache/`,
結果寫 `cache/capex_extra.json`。
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

SKIP = re.compile(r"(?i)\.(jpg|png|gif|zip|xml|xsd|css|js)$|^R\d+\.htm$|-index")


def main() -> None:
    sys.path.insert(0, str(HERE))
    import s15_lib as L

    plan = json.loads((CACHE / "enrich_plan.json").read_text(encoding="utf-8"))
    seen = set()
    targets = []
    for slot, pv in sorted(plan["peers"].items()):
        for it in pv["peers"]:
            if not it.get("accn"):
                continue
            k = (it["entity_id"], it["accn"])
            if k in seen:
                continue
            seen.add(k)
            fn, _ = L.cached(it["entity_id"], it["accn"], "", "peer10k", fetch=False)
            if not fn:
                continue
            if L.capex_excerpt(L.read_doc(fn)):
                continue
            targets.append(it)

    out = {}
    log = (CACHE / "capex_extra_log.jsonl").open("a", encoding="utf-8")
    for it in targets:
        cik, accn, primary = it["entity_id"], it["accn"], it.get("doc") or ""
        base = "https://www.sec.gov/Archives/edgar/data/%s/%s" % (
            int(cik), accn.replace("-", ""))
        try:
            idx = json.loads(L.http_get(base + "/index.json", timeout=60))
        except Exception as e:                                   # noqa: BLE001
            out[accn] = {"status": "index 抓取失敗:%s" % type(e).__name__}
            log.write(json.dumps(dict(accn=accn, status="index_fail"),
                                 ensure_ascii=False) + "\n")
            continue
        # 不靠檔名關鍵字(各家命名不一,RTX 的實質年報叫 exhibit13),改取最大的幾份:
        # 年報/財報附件必然是該筆申報裡最大的文件。
        cand = []
        for f in idx.get("directory", {}).get("item", []):
            nm = f.get("name", "")
            if not nm.lower().endswith((".htm", ".html")):
                continue
            if nm == primary or SKIP.search(nm):
                continue
            try:
                sz = int(f.get("size") or 0)
            except (TypeError, ValueError):
                sz = 0
            cand.append((sz, nm))
        cand.sort(reverse=True)
        cands = [nm for _, nm in cand[:3]]
        got = []
        for nm in cands:
            # 命名不能截斷(截斷會令同一申報的多份附件撞同一個快取名)
            tag = "peerX_%s" % hashlib.sha1(nm.encode("utf-8")).hexdigest()[:10]
            fn, st = L.cached(cik, accn, nm, tag)
            if not fn:
                continue
            ex = L.capex_excerpt(L.read_doc(fn))
            if ex:
                got = ex
                out[accn] = {"status": "ok", "doc": nm, "local_gz": fn,
                             "capex_excerpt": ex}
                break
        if not got:
            out[accn] = {"status": "查不到", "tried": cands}
        log.write(json.dumps(dict(accn=accn, ticker=it.get("ticker"),
                                  tried=cands, status=out[accn]["status"]),
                             ensure_ascii=False) + "\n")
        log.flush()
        print("  %s %s tried=%d -> %s" % (it.get("ticker"), accn, len(cands),
                                          out[accn]["status"]), flush=True)
    log.close()
    (CACHE / "capex_extra.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                            encoding="utf-8")
    ok = sum(1 for v in out.values() if v["status"] == "ok")
    print("年期報本文抽不到資本開支的同業 %d;附件救回 %d;仍查不到 %d"
          % (len(targets), ok, len(targets) - ok))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
