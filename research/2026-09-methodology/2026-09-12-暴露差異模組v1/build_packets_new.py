# -*- coding: utf-8 -*-
"""KARST-218 樣本外新事件:遮蔽版取證包。

照 KARST-212 批 1 `build_packets.py` 同一口徑。包內只有衝擊日之前拿得到的東西:
事件敘事、衝擊起訖日、籃子定義、籃子成員(代號/名/CIK/SIC)、衝擊窗相對跌幅、
衝擊前最後一份 10-K 與最近兩份 10-Q 的申報日與 accession、本地全文路徑或 EDGAR 網址、
衝擊前最後一期財務面板。

**明文遮蔽(由本腳本機械保證)**:T/N 兩錨 3/6/12 個月超額六欄、狀態欄、兩個錨日
一律不入包。判斷落檔之前不准讀 `out/basket_members_new.csv` 的結果欄。
"""
import csv
import json
import os

ROOT = "C:/projects/Karst"
HERE = f"{ROOT}/research/2026-09-methodology/2026-09-12-暴露差異模組v1"
OUT = f"{HERE}/packets"
SUB = ROOT + "/data/sec/submissions/CIK{cik}.json"
TXT = ROOT + "/data/sec/10k_text"

EVENTS = ["E17", "E18", "E19", "E20"]

REDACT = {"T_3m_excess", "T_3m_status", "T_6m_excess", "T_6m_status",
          "T_12m_excess", "T_12m_status", "N_3m_excess", "N_3m_status",
          "N_6m_excess", "N_6m_status", "N_12m_excess", "N_12m_status",
          "anchor_T_date", "anchor_N_date"}

KEEP = ["ticker", "name", "entity_id", "sic", "sic_description", "named_confidence",
        "f_shock_rel_drop", "panel_period_end", "panel_filed", "currency",
        "ttm_revenue", "ttm_ocf", "ttm_net_income", "cash", "total_debt",
        "assets", "equity", "mcap_usd", "f_ps", "f_ocf_margin", "f_ni_margin",
        "f_rev_growth_yoy", "f_rev_cv8", "dollar_vol_60d"]


def load_events():
    with open(f"{HERE}/new_events_spec.json", encoding="utf-8") as f:
        return {e["event_id"]: e for e in json.load(f)["events"]}


def prefilings(cik, cutoff):
    """衝擊起日之前最後一份 10-K 與最近兩份 10-Q。"""
    path = SUB.format(cik=cik)
    if not os.path.exists(path):
        return {"note": "本地無 submissions 快取,取證請打 EDGAR"}
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    r = d.get("filings", {}).get("recent", {})
    rows = []
    for i in range(len(r.get("form", []))):
        if r["filingDate"][i] < cutoff:
            rows.append({"form": r["form"][i], "filingDate": r["filingDate"][i],
                         "reportDate": r["reportDate"][i],
                         "accessionNumber": r["accessionNumber"][i],
                         "primaryDocument": r["primaryDocument"][i]})
    out = {}
    for form, n in (("10-K", 1), ("10-Q", 2), ("8-K", 0)):
        sel = [x for x in rows if x["form"] == form][:n]
        for j, s in enumerate(sel):
            acc = s["accessionNumber"].replace("-", "")
            key = form if n == 1 else f"{form}[{j}]"
            out[key] = {
                "filingDate": s["filingDate"], "reportDate": s["reportDate"],
                "accession": s["accessionNumber"],
                "url": (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                        f"{acc}/{s['primaryDocument']}"),
            }
    return out


def local_10k(ticker, acc):
    if not acc:
        return None
    p = f"{TXT}/{ticker}_{acc.replace('-', '')}.txt.gz"
    return p if os.path.exists(p) else None


def main():
    os.makedirs(OUT, exist_ok=True)
    events = load_events()
    with open(f"{HERE}/out/basket_members_new.csv", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["basket_kind"] == "新聞點名"]
    by_ev = {}
    for r in rows:
        by_ev.setdefault(r["event_id"], []).append(r)

    for eid in EVENTS:
        members = by_ev.get(eid, [])
        ev = events[eid]
        cutoff = ev["shock_start"]
        pack = {"event_id": eid, "name": ev["name"], "narrative": ev["narrative"],
                "shock_start": ev["shock_start"], "news_shock_end": ev.get("news_shock_end"),
                "basket_definition": ev["basket_definition"],
                "basket_source": ev["basket_source"],
                "sources": ev["sources"],
                "evidence_cutoff": f"申報日 < {cutoff}",
                "redacted": sorted(REDACT), "companies": []}
        n_local = 0
        for m in members:
            cik = m["entity_id"]
            pf = prefilings(cik, cutoff) if cik else {"note": "無 CIK"}
            acc = pf.get("10-K", {}).get("accession") if isinstance(pf, dict) else None
            lp = local_10k(m["ticker"], acc)
            if lp:
                n_local += 1
            c = {k: m.get(k) for k in KEEP}
            c["prefilings"] = pf
            c["local_10k_gz"] = lp
            pack["companies"].append(c)
        with open(f"{OUT}/{eid}.json", "w", encoding="utf-8") as f:
            json.dump(pack, f, ensure_ascii=False, indent=1)
        print(eid, len(members), "家, 本地 10-K 全文", n_local, "份 —", ev["name"])


if __name__ == "__main__":
    main()
