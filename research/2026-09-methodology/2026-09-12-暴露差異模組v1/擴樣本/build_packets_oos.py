# -*- coding: utf-8 -*-
"""KARST-220 擴樣本(E21–E27):遮蔽版取證包。

照 KARST-218 `build_packets_new.py` 同一口徑(同一遮蔽清單、同一逐家欄位、同一申報索引),
三處不同:
  1. 輸入 `out/basket_members_oos.csv`、輸出 `packets_oos/`;
  2. **市值欄用 `mcap_oos`**(未還原收市價 × 最近申報流通股數),**不用 `PanelFeatures.mcap_usd`**
     ——後者為已知缺陷(KARST-218 舉手第 1 件、KARST-219 修復中)。本地缺口由
     `out/shares_oos.csv`(SEC XBRL `dei:EntityCommonStockSharesOutstanding`,已過時點閘)補;
     兩邊都取不到即留空並在 `mcap_note` 寫明,不猜、不用財經網站。
  3. 加入提示詞 §二 第 6 項輸入:**折現率 = FRED DGS10 衝擊起日值 + 5 個百分點**
     (`out/dgs10_oos.csv`,抓不到即留空)。

**機械遮蔽(由本腳本保證,不靠判斷者自律)**:`T_/N_ 3m/6m/12m_excess` 連狀態欄、
`anchor_T_date`、`anchor_N_date` 及任何衝擊後價格一律不入包。落檔時逐包驗一次,驗到即拋錯。
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
PKT = HERE / "packets_oos"
SUB = ROOT / "data" / "sec" / "submissions"
TXT = ROOT / "data" / "sec" / "10k_text"
UA = {"User-Agent": "Karst research kaho@example.com"}
DGS10_CACHE = OUT / "dgs10_raw.csv"

EVENTS = ["E21", "E22", "E23", "E24", "E25", "E26", "E27"]
PICKS = {
    "E21": ["BCS", "LYG", "HSBC", "JPM"],
    "E22": ["BABA", "TAL", "NIO", "YUMC"],
    "E23": ["COIN", "MSTR", "RIOT", "HOOD"],
    "E24": ["AMAT", "ASML", "NVDA", "MU"],
    "E25": ["F", "GM", "APTV", "MGA"],
    "E26": ["VNO", "SPG", "O", "PLD"],
    "E27": ["UNH", "CVS", "MCK", "CNC"],
}

REDACT = {"T_3m_excess", "T_3m_status", "T_6m_excess", "T_6m_status",
          "T_12m_excess", "T_12m_status", "N_3m_excess", "N_3m_status",
          "N_6m_excess", "N_6m_status", "N_12m_excess", "N_12m_status",
          "anchor_T_date", "anchor_N_date"}

KEEP = ["ticker", "name", "entity_id", "sic", "sic_description", "named_confidence",
        "f_shock_rel_drop", "panel_period_end", "panel_filed", "currency",
        "ttm_revenue", "ttm_ocf", "ttm_net_income", "cash", "total_debt",
        "assets", "equity", "mcap_oos", "f_ps_oos", "f_pb_oos", "f_ocf_margin",
        "f_ni_margin", "f_rev_growth_yoy", "f_rev_cv8", "dollar_vol_60d",
        "close_raw_i0", "adj_close_i0"]

STALE_DAYS = 400          # 股數申報日距衝擊起日上限,與 basket_core.PANEL_STALE_DAYS 一致

# ADR 換算:XBRL 的 `EntityCommonStockSharesOutstanding` 是**普通股**股數,而價格庫是**每 ADS** 價,
# 兩者相差一個 ADS 比率,直接相乘會系統性放大(阿里巴巴 1 ADS = 8 普通股 → 市值放大 8 倍)。
# 逐家寫死比率並附出處;不在表內者不套用,亦不猜。
ADR_RATIO = {
    # (event, ticker): (每 ADS 折普通股數, 出處)
    ("E22", "BABA"): (8, "阿里巴巴 2021 年 20-F 封面:每份 ADS 代表 8 股普通股"),
}


def dgs10_series() -> pd.DataFrame:
    if not DGS10_CACHE.exists():
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            DGS10_CACHE.write_bytes(r.read())
    d = pd.read_csv(DGS10_CACHE)
    d.columns = ["date", "dgs10"]
    d["date"] = pd.to_datetime(d["date"])
    d["dgs10"] = pd.to_numeric(d["dgs10"], errors="coerce")
    return d.dropna().sort_values("date")


def _idx_rows() -> dict:
    """由 fetch_docs_oos.py 出的完整申報索引(docs_index_oos.json)取逐家申報清單。

    本地 submissions 快取的 `recent` 只覆蓋近年(2016/2018 兩宗的年報住在分片檔),
    故以抓全文時建立的索引為正本,避免包內索引空掉。
    """
    p = OUT / "docs_index_oos.json"
    if not p.exists():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    out: dict = {}
    for r in d:
        if r.get("status") != "已落 docs/":
            continue
        out.setdefault((r["event"], r["ticker"]), []).append(r)
    return out


def prefilings(cik: str, cutoff: str, ev: str = "", ticker: str = "", idx: dict | None = None) -> dict:
    """衝擊起日之前最後一份年度報告與最近兩份季度報告。"""
    hit = (idx or {}).get((ev, ticker))
    if hit:
        out = {}
        for r in hit:
            acc = r["accn"].replace("-", "")
            out[r["tag"]] = {"form": r["form"], "filingDate": r["filingDate"],
                             "reportDate": r.get("reportDate", ""), "accession": r["accn"],
                             "url": (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                                     f"{acc}/{r['file']}")}
        return out
    p = SUB / f"CIK{cik}.json"
    if not p.exists():
        return {"note": "本地無 submissions 快取,且全文索引無此家"}
    with open(p, encoding="utf-8") as f:
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
    annual = ("10-K", "20-F", "40-F")
    quar = ("10-Q", "6-K")
    a = [x for x in rows if x["form"] in annual][:1]
    q = [x for x in rows if x["form"] in quar][:2]
    sel = [("年報", x) for x in a] + [(f"季報{j}", x) for j, x in enumerate(q)]
    for key, s in sel:
        acc = s["accessionNumber"].replace("-", "")
        out[key] = {"form": s["form"], "filingDate": s["filingDate"],
                    "reportDate": s["reportDate"], "accession": s["accessionNumber"],
                    "url": (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                            f"{acc}/{s['primaryDocument']}")}
    return out


def local_fulltext(ticker: str, acc: str):
    if not acc:
        return None
    p = TXT / f"{ticker}_{acc.replace('-', '')}.txt.gz"
    return str(p) if p.exists() else None


def main() -> None:
    PKT.mkdir(parents=True, exist_ok=True)
    spec = json.loads((HERE / "new_events_spec_oos.json").read_text(encoding="utf-8"))
    events = {e["event_id"]: e for e in spec["events"]}

    mem = pd.read_csv(OUT / "basket_members_oos.csv", encoding="utf-8-sig",
                      dtype={"entity_id": str, "ticker": str})
    mem = mem[mem["basket_kind"] == "新聞點名"].copy()
    leaked = REDACT & set(mem.columns)
    print("遮蔽欄仍在來源檔(預期為真,落包時會剔):", sorted(leaked))

    sh = pd.read_csv(OUT / "shares_oos.csv", encoding="utf-8-sig", dtype={"entity_id": str, "ticker": str})
    sh_idx = {(r.event_id, r.ticker): r for r in sh.itertuples()}

    dg = dgs10_series()
    docidx = _idx_rows()
    print(f"全文索引覆蓋 {len(docidx)} 家(由 docs_index_oos.json)")
    dg_rows = []
    for eid, ev in events.items():
        t = pd.Timestamp(ev["shock_start"])
        s = dg[dg["date"] <= t]
        base = float(s["dgs10"].iloc[-1]) if len(s) else float("nan")
        dg_rows.append(dict(event_id=eid, shock_start=ev["shock_start"],
                            dgs10_date=str(s["date"].iloc[-1].date()) if len(s) else "",
                            dgs10=base, dgs10_plus_500bp=base + 5.0))
    dgdf = pd.DataFrame(dg_rows)
    dgdf.to_csv(OUT / "dgs10_oos.csv", index=False, encoding="utf-8-sig")
    print(dgdf.to_string(index=False))

    for eid in EVENTS:
        ev = events[eid]
        cutoff = ev["shock_start"]
        picks = PICKS[eid]
        pack = {"event_id": eid, "name": ev["name"], "event_type": ev.get("event_type", ""),
                "narrative": ev["narrative"],
                "shock_start": cutoff, "news_shock_end": ev.get("news_shock_end"),
                "basket_definition": ev["basket_definition"],
                "basket_source": ev["basket_source"],
                "sources": ev["sources"],
                "picked": picks,
                "picked_note": "按暴露形態挑,理由見 picks_before_results.md(判斷之前寫死)",
                "evidence_cutoff": f"申報日 < {cutoff}",
                "discount_rate_note": ("提示詞 §二.6:FRED DGS10 衝擊起日值 + 5 個百分點;"
                                       "DGS10 本身非投資建議,只作折現率輸入"),
                "discount_rate": float(dgdf[dgdf.event_id == eid]["dgs10_plus_500bp"].iloc[0]),
                "discount_rate_base": float(dgdf[dgdf.event_id == eid]["dgs10"].iloc[0]),
                "redacted": sorted(REDACT), "companies": []}
        n_local = n_mcap = 0
        for _, m in mem[mem.event_id == eid].iterrows():
            cik = str(m["entity_id"]).zfill(10)
            c = {k: (None if pd.isna(m.get(k)) else m.get(k)) for k in KEEP}
            c["entity_id"] = cik
            # --- 市值:面板推得的 mcap_oos 為先;缺即用 SEC XBRL 股數 × 未還原收市價
            mc = c.get("mcap_oos")
            note = "" if (mc is not None and mc == mc) else ""
            if mc is None or mc != mc:
                r = sh_idx.get((eid, str(m["ticker"])))
                raw = m.get("close_raw_i0")
                ok = (r is not None and r.shares == r.shares and r.shares > 0 and r.shares_filed
                      and (pd.Timestamp(cutoff) - pd.Timestamp(str(r.shares_filed))).days <= STALE_DAYS
                      and raw == raw and raw > 0)
                if ok:
                    adr, adr_src = ADR_RATIO.get((eid, str(m["ticker"])), (1, ""))
                    mc = float(r.shares) / adr * float(raw)
                    c["mcap_oos"] = mc
                    rev = c.get("ttm_revenue")
                    eq = c.get("equity")
                    if rev and rev == rev and rev > 0:
                        c["f_ps_oos"] = mc / float(rev)
                    if eq and eq == eq and eq > 0:
                        c["f_pb_oos"] = mc / float(eq)
                    note = (f"面板無股數,改用 SEC XBRL 流通股數 {float(r.shares):,.0f} 股"
                            f"(申報日 {r.shares_filed})× 衝擊起日前一交易日未還原收市價 {float(raw):.2f}")
                    if adr != 1:
                        note += f";此為普通股股數,已按 1 ADS = {adr} 普通股 折算({adr_src})"
                else:
                    why = "面板與 SEC XBRL 兩邊都取不到衝擊起日之前 400 日內的流通股數"
                    if r is not None and r.shares == r.shares and r.shares_filed:
                        why += f"(SEC XBRL 最近一筆為 {r.shares_filed},已超過 400 日)"
                    note = "查不到:" + why + ";市值留空,估值一問改以每股數值答"
            c["mcap_note"] = note
            if c.get("mcap_oos") is not None:
                n_mcap += 1
            acc = ""
            pf = prefilings(cik, cutoff, eid, str(m["ticker"]), docidx)
            for k, v in pf.items():
                if isinstance(v, dict) and k == "年報":
                    acc = v["accession"]
            lp = local_fulltext(str(m["ticker"]), acc)
            if lp:
                n_local += 1
            c["prefilings"] = pf
            c["local_fulltext_gz"] = lp
            c["picked"] = str(m["ticker"]) in picks
            pack["companies"].append(c)
        for c in pack["companies"]:
            bad = REDACT & set(c.keys())
            if bad:
                raise SystemExit(f"{eid} {c['ticker']} 遮蔽欄外洩:{sorted(bad)}")
        with open(PKT / f"{eid}.json", "w", encoding="utf-8") as f:
            json.dump(pack, f, ensure_ascii=False, indent=1)
        print(f"{eid} {ev['name']}: {len(pack['companies'])} 家(挑 {len(picks)}),"
              f"有市值 {n_mcap},本地全文 {n_local},折現率 {pack['discount_rate']:.2f}%")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
