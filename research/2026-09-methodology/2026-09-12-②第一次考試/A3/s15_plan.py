# -*- coding: utf-8 -*-
"""KARST-232 第二步(前置):算出補強要用的東西,並列出「還差哪些原文要抓」。

寫 `cache/enrich_plan.json`(換入三宗的 meta、同業規則與同業名單、兩大同業年報待抓清單、
上一份業績稿待抓清單、preliminary 字眼首次出現位置)+ `cache/px_state_enrich.parquet`。
只讀既有資料,不抓網絡。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

import pxlib
import s15_lib as L

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
ROOT = Path(r"C:\projects\Karst")


def main() -> None:
    picks = json.loads((CACHE / "picks_final.json").read_text(encoding="utf-8"))
    final = picks["final"]
    pop = pd.read_parquet(CACHE / "population_improvement.parquet")
    meta = pop.set_index("accessionNumber")
    meta["accessionNumber"] = meta.index

    ent = pd.read_parquet(ROOT / "data" / "universe" / "entities.parquet",
                          columns=["entity_id", "name", "primary_ticker", "sic", "exchange"])
    ent["sic4"] = ent["sic"].astype(str).str.zfill(4)
    ent["sic3"] = ent["sic4"].str[:3]
    ent["sic2"] = ent["sic4"].str[:2]

    ev_dates = {meta.loc[f["acc"], "reaction_date"] for f in final}
    px_state, first_px = pxlib.state_at(ev_dates)
    px_state.to_parquet(CACHE / "px_state_enrich.parquet", index=False)
    (CACHE / "first_px_enrich.json").write_text(
        json.dumps({k: str(v)[:10] for k, v in first_px.items()}), encoding="utf-8")
    dv_by_date = px_state.set_index(["date", "entity_id"])["dv60"].dropna()

    plan = {"peers": {}, "prior": {}, "prelim": {}, "peer_docs_missing": [],
            "prior_docs_missing": [], "fetch_docs": []}
    seen_doc = set()
    for f in final:
        slot, acc = f["slot"], f["acc"]
        m = meta.loc[acc]
        t1d = pd.Timestamp(m["reaction_date"])
        rule, pu = L.choose_peers(ent, m, first_px, dv_by_date, t1d)
        peers = L.top2_peers(pu, dv_by_date, t1d) if rule != "insufficient" \
            else pu
        plist = []
        for pr in peers.itertuples(index=False):
            rows = L.filing_rows(pr.entity_id)
            ann = [x for x in rows if x["form"] in ("10-K", "20-F", "40-F")
                   and x["filingDate"] <= m["reaction_date"]]
            item = dict(entity_id=pr.entity_id, name=pr.name, ticker=pr.primary_ticker,
                        sic4=pr.sic4, sic3=pr.sic3, bucket=f["bucket"], has_annual=bool(ann))
            if ann:
                a = ann[0]
                item.update(form=a["form"], filingDate=a["filingDate"], accn=a["accn"])
                key = (pr.entity_id, a["accn"], "peer10k")
                if key not in seen_doc:
                    seen_doc.add(key)
                    fn, st = L.cached(pr.entity_id, a["accn"], a["doc"], "peer10k", fetch=False)
                    if not fn:
                        plan["peer_docs_missing"].append(
                            dict(entity_id=pr.entity_id, accn=a["accn"], slot=slot))
                        plan["fetch_docs"].append(dict(cik=pr.entity_id, accn=a["accn"],
                                                       doc=a["doc"], tag="peer10k"))
            plist.append(item)
        plan["peers"][slot] = dict(rule=rule, n_pool=int(len(pu)),
                                   n_all_tickers=int(len(pu)), peers=plist)

        # 上一份業績稿
        rows = L.filing_rows(m["cik"])
        pr8 = L.prior_release(rows, m["reaction_date"], m["filingDate"])
        rec = {"found": bool(pr8)}
        if pr8:
            rec.update(accn=pr8["accn"], filingDate=pr8["filingDate"],
                       reportDate=pr8["reportDate"])
            p = L.DOCS / ("%s__EX991.txt.gz" % pr8["accn"].replace("-", ""))
            rec["cached"] = p.exists()
            if not p.exists():
                plan["prior_docs_missing"].append(dict(slot=slot, accn=pr8["accn"]))
                plan["fetch_docs"].append(dict(cik=m["cik"], accn=pr8["accn"],
                                               doc="", tag="EX991"))
        plan["prior"][slot] = rec

        # preliminary 首次出現位置(判「稿頭即初步業績」用)
        ex = L.DOCS / ("%s__EX991.txt.gz" % acc.replace("-", ""))
        txt = L.read_doc(ex.name) if ex.exists() else ""
        low = txt.lower()
        i = low.find("preliminar")
        plan["prelim"][slot] = dict(chars=len(txt), first_prelim_pos=i)

    # 建包前置文件(全部 84 槽:補抓更舊分片後,原本看不到的年報/季報可能新露出來)
    extra_docs = []
    for f in final:
        m = meta.loc[f["acc"]]
        rows = L.filing_rows(m["cik"])
        pf = L.pick_filings(rows, m["reaction_date"])
        for k, x in pf.items():
            p = L.DOCS / ("%s__%s.txt.gz" % (x["accn"].replace("-", ""), k))
            if not p.exists():
                extra_docs.append(dict(cik=m["cik"], accn=x["accn"], doc=x["doc"],
                                       tag=k, slot=f["slot"]))
        p = L.DOCS / ("%s__8k.txt.gz" % f["acc"].replace("-", ""))
        if not p.exists():
            s8 = [r for r in rows if r["accn"] == f["acc"]]
            if s8:
                extra_docs.append(dict(cik=m["cik"], accn=f["acc"], doc=s8[0]["doc"],
                                       tag="8k", slot=f["slot"]))
    plan["build_docs_missing"] = extra_docs
    (CACHE / "enrich_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")

    from collections import Counter
    print("picks_final 84;price state rows %d;first_px %d" % (len(px_state), len(first_px)))
    print("同業規則分佈:", Counter(v["rule"] for v in plan["peers"].values()))
    print("同業池大小分位:",
          pd.Series([v["n_pool"] for v in plan["peers"].values()]).describe().to_dict())
    print("peer docs missing %d(unique);prior EX991 missing %d;build docs missing %d"
          % (len(plan["peer_docs_missing"]), len(plan["prior_docs_missing"]),
             len(extra_docs)))
    print("fetch_docs total %d" % len(plan["fetch_docs"]))
    print("prior found %d/84" % sum(1 for v in plan["prior"].values() if v["found"]))
    head = [k for k, v in plan["prelim"].items() if 0 <= v["first_prelim_pos"] < 600]
    print("preliminary 首現 <600 字元(稿頭式)的槽位數:", len(head), sorted(head))


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
