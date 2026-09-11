# -*- coding: utf-8 -*-
"""KARST-212 批 1:替判斷隊砌「遮蔽版」取證包(E01/E02/E03/E04/E09)。

照 KARST-204 `checklist_test/build_packets.py` 同一口徑,只加兩個限制:
  1. 只出本批五宗事件;
  2. 落檔在 2026-09-11-①v3全量回測/批1/packets/。

包內只有衝擊日之前拿得到的東西:
  - 事件敘事、衝擊起訖日、籃子定義;
  - 籃子成員(代號、名、CIK、SIC)、衝擊窗相對跌幅(步六要用);
  - 衝擊日之前最後一份 10-K / 最近兩份 10-Q 的申報日、期末、accession、本地全文路徑或 EDGAR 網址;
  - 衝擊日之前最後一期財務面板(收入、現金流、負債等),連期末與申報日。

**明文遮蔽**:T_3m/6m/12m、N_3m/6m/12m 六欄連狀態欄及兩個錨日一律不入包——那是本票要考的答案。
遮蔽由這支腳本機械保證,不靠判斷隊自律。
"""
import csv
import json
import os

ROOT = "C:/projects/Karst"
BASE = f"{ROOT}/research/2026-09-methodology/2026-09-10-①行業殺錯事件籃子"
OUT = f"{ROOT}/research/2026-09-methodology/2026-09-11-①v3全量回測/批1/packets"
SUB = ROOT + "/data/sec/submissions/CIK{cik}.json"
TXT = ROOT + "/data/sec/10k_text"

EVENTS = ["E01", "E02", "E03", "E04", "E09"]

# 遮蔽欄:十二個月及其他前瞻結果,判斷隊一律看不到
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
    with open(f"{BASE}/events_spec.json", encoding="utf-8") as f:
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
    with open(f"{BASE}/out/basket_members.csv", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["basket_kind"] == "新聞點名"]
    by_ev = {}
    for r in rows:
        by_ev.setdefault(r["event_id"], []).append(r)

    summary = []
    for eid in EVENTS:
        members = by_ev.get(eid, [])
        ev = events[eid]
        cutoff = ev["shock_start"]
        pack = {"event_id": eid, "name": ev["name"], "narrative": ev["narrative"],
                "shock_start": ev["shock_start"], "news_shock_end": ev.get("news_shock_end"),
                "basket_definition": ev["basket_definition"],
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
        summary.append((eid, ev["name"], len(members), n_local))

    for s in summary:
        print(s[0], s[2], "家, 本地 10-K 全文", s[3], "份 —", s[1])


if __name__ == "__main__":
    main()
