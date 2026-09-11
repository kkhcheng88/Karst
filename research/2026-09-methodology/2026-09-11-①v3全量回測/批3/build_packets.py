# -*- coding: utf-8 -*-
"""KARST-214(批 3):替判斷隊砌 E08、E12、E13、E14 四宗的遮蔽版取證包。

照 199 `checklist_test/build_packets.py` 與 210 `build_packets.py` 的做法。本包逐家附:
  - 事件敘事、衝擊起訖日、籃子定義、證據硬界線;
  - 成員身分(代號、名、entity_id、SIC)與衝擊前最後一期財務面板;
  - 衝擊起日收市價(包內唯一價格)、當時十年期美債(FRED DGS10);
  - 衝擊起日之前已抽好的 10-K 純文字全文路徑(204 `checklist_test/docs/<EID>/`);
  - 衝擊窗相對跌幅 `f_shock_rel_drop`(步六背景用,見下)。

**明文遮蔽**:T_3m/6m/12m 與 N_3m/6m/12m 六欄連狀態欄與兩個錨日一律不入包。
遮蔽由本腳本機械保證,不靠判斷隊自律。**本腳本砌包時不讀結果欄,讀入後即刻丟棄。**

輸出:packets/<EID>.json、packets/_遮蔽清單.md
用法:PYTHONUTF8=1 python build_packets.py
"""
import csv
import json
import os
import urllib.request

ROOT = "C:/projects/Karst"
BASE = f"{ROOT}/research/2026-09-methodology/2026-09-10-①行業殺錯事件籃子"
DOCS = f"{BASE}/checklist_test/docs"
OUT = os.path.dirname(os.path.abspath(__file__)) + "/packets"
PRICES = f"{ROOT}/data/prices/daily"

EVENTS = ["E08", "E12", "E13", "E14"]

REDACT = {"T_3m_excess", "T_3m_status", "T_6m_excess", "T_6m_status",
          "T_12m_excess", "T_12m_status", "N_3m_excess", "N_3m_status",
          "N_6m_excess", "N_6m_status", "N_12m_excess", "N_12m_status",
          "anchor_T_date", "anchor_N_date"}

KEEP = ["ticker", "name", "entity_id", "sic", "sic_description", "named_confidence",
        "f_shock_rel_drop", "panel_period_end", "panel_filed", "panel_age_days",
        "currency", "ttm_revenue", "ttm_ocf", "ttm_net_income", "cash", "total_debt",
        "assets", "equity", "mcap_usd", "f_net_cash_n2", "f_net_cash_over_mcap",
        "f_debt_to_assets", "f_liab_to_assets", "f_ocf_positive", "f_ocf_margin",
        "f_ni_margin", "f_ps", "f_pb", "f_pe", "f_log_mcap", "f_rev_growth_yoy",
        "f_rev_cv8", "dollar_vol_60d", "feat_status"]


def pre_price_map(pairs):
    """一次掃完日線庫,取各 (代號, 衝擊起日) 的收市價。

    pairs = [(ticker, day), ...]。日線庫 15 個 part、合共約 450MB,
    逐個 (代號,日) 重掃會慢幾個數量級,故只掃一遍。
    """
    import pandas as pd
    want = {}
    for tk, day in pairs:
        want.setdefault(str(day), set()).add(tk)
    out = {}
    fs = sorted(f for f in os.listdir(PRICES) if f.startswith("part_"))
    for f in fs:
        d = pd.read_parquet(f"{PRICES}/{f}", columns=["ticker", "date", "close"])
        ds = d["date"].astype(str)
        for day, tks in want.items():
            m = d[(ds == day) & (d["ticker"].isin(tks))]
            for _, r in m.iterrows():
                out[(r["ticker"], day)] = float(r["close"])
    return out


def dgs10(day):
    u = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10&cosd=%s&coed=%s" % (day, day)
    t = urllib.request.urlopen(u, timeout=30).read().decode()
    for ln in t.splitlines()[1:]:
        if "," in ln:
            k, v = ln.split(",")[0], ln.split(",")[1]
            if k == day:
                return float(v)
    return None


def docs_index(eid):
    """204 已抽好的衝擊前 10-K 純文字,本票只讀不改。"""
    d = {}
    p = f"{DOCS}/{eid}"
    if not os.path.isdir(p):
        return d
    for fn in os.listdir(p):
        if fn.endswith(".txt"):
            tk = fn.split("__")[0]
            d.setdefault(tk, []).append(f"{p}/{fn}")
    return d


def main():
    os.makedirs(OUT, exist_ok=True)
    with open(f"{BASE}/events_spec.json", encoding="utf-8") as f:
        events = {e["event_id"]: e for e in json.load(f)["events"]}
    rows = list(csv.DictReader(open(f"{BASE}/out/basket_members.csv", encoding="utf-8-sig")))
    rows = [r for r in rows if r["basket_kind"] == "新聞點名"]
    # 讀入後即刻只留身分與衝擊前財務,答案欄(REDACT)一個字都不落包
    members = {}
    for r in rows:
        members.setdefault(r["event_id"], {})[r["ticker"]] = {k: r.get(k) for k in KEEP}

    pairs = []
    for eid in EVENTS:
        for tk in members.get(eid, {}):
            pairs.append((tk, events[eid]["shock_start"]))
    px = pre_price_map(pairs)

    summary = []
    for eid in EVENTS:
        ev = events[eid]
        packs = members.get(eid, {})
        pack = {"event_id": eid, "name": ev["name"], "narrative": ev["narrative"],
                "shock_start": ev["shock_start"], "news_shock_end": ev.get("news_shock_end"),
                "basket_definition": ev["basket_definition"],
                "basket_source": ev.get("basket_source"),
                "spec_tickers": ev.get("tickers"),
                "spec_notes": ev.get("notes"),
                "evidence_cutoff": "文件申報日 < %s(硬界線);界線後文件一律不得引" % ev["shock_start"],
                "treasury_10y_pct_on_shock_start": dgs10(ev["shock_start"]),
                "redacted": sorted(REDACT), "companies": []}
        di = docs_index(eid)
        for tk, m in sorted(packs.items()):
            c = dict(m)
            c["price_shock_start_close"] = px.get((tk, ev["shock_start"]))
            c["prefiling_docs"] = di.get(tk, [])
            pack["companies"].append(c)
        with open(f"{OUT}/{eid}.json", "w", encoding="utf-8") as f:
            json.dump(pack, f, ensure_ascii=False, indent=1)
        summary.append((eid, len(pack["companies"]),
                        sum(1 for c in pack["companies"] if c["prefiling_docs"]),
                        pack["treasury_10y_pct_on_shock_start"]))

    for s in summary:
        print(s[0], "成員", s[1], "家|有衝擊前 10-K 全文", s[2], "家|美債10年", s[3])


if __name__ == "__main__":
    main()
