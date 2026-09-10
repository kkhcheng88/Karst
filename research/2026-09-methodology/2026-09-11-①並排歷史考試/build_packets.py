# -*- coding: utf-8 -*-
"""KARST-210:替「判斷隊」砌兩宗事件的遮蔽版取證包。

照 199 `checklist_test/build_packets.py` 的做法,但本票只在兩宗事件、每家 5 家身上做,
故每包逐家附上「衝擊前一交易日收市價」與當時十年期美債(FRED DGS10),不另開一支腳本。

**明文遮蔽**:T_3m/6m/12m 與 N_3m/6m/12m 六欄連狀態欄與兩個錨日一律不入包。
遮蔽由本腳本機械保證,不靠判斷隊自律。**本腳本不讀 out/ 之下任何檔案**(籃子成員由
events_spec 的 basket 定義 + 199 的 basket_members.csv 取成員名單;該檔的十二個月欄
在本腳本讀入後立即丟棄)。

輸出:packets/<EVENT>.json + packets/_遮蔽清單.md
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

TICKERS = {"E06": ["MDLZ", "KO", "RMD", "DXCM", "DVA"],
           "E07": ["NVDA", "MU", "VRT", "ANET", "ORCL"]}

REDACT = {"T_3m_excess", "T_3m_status", "T_6m_excess", "T_6m_status",
          "T_12m_excess", "T_12m_status", "N_3m_excess", "N_3m_status",
          "N_6m_excess", "N_6m_status", "N_12m_excess", "N_12m_status",
          "anchor_T_date", "anchor_N_date"}

KEEP = ["ticker", "name", "entity_id", "sic", "sic_description", "named_confidence",
        "f_shock_rel_drop", "panel_period_end", "panel_filed", "currency",
        "ttm_revenue", "ttm_ocf", "ttm_net_income", "cash", "total_debt",
        "assets", "equity", "mcap_usd", "f_ps", "f_ocf_margin", "f_ni_margin",
        "f_rev_growth_yoy", "f_rev_cv8", "dollar_vol_60d"]


def pre_price(ticker, day):
    """衝擊前一交易日(＝衝擊起日)收市價,取自倉內日線庫。"""
    import pandas as pd
    fs = sorted(f for f in os.listdir(PRICES) if f.startswith("part_"))
    for f in fs:
        d = pd.read_parquet(f"{PRICES}/{f}", columns=["ticker", "date", "close"])
        m = d[(d["ticker"] == ticker) & (d["date"].astype(str) == day)]
        if len(m):
            return float(m["close"].iloc[0])
    return None


def dgs10(d1, d2):
    u = ("https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10&cosd=%s&coed=%s" % (d1, d2))
    t = urllib.request.urlopen(u, timeout=30).read().decode()
    return {ln.split(",")[0]: ln.split(",")[1] for ln in t.splitlines()[1:] if "," in ln}


def docs_index(eid):
    """204 已抽好的衝擊前 10-K 純文字,本票只讀不改。"""
    d = {}
    for fn in os.listdir(f"{DOCS}/{eid}"):
        if fn.endswith(".txt"):
            tk = fn.split("__")[0]
            d.setdefault(tk, []).append(f"{DOCS}/{eid}/{fn}")
    return d


def main():
    os.makedirs(OUT, exist_ok=True)
    with open(f"{BASE}/events_spec.json", encoding="utf-8") as f:
        events = {e["event_id"]: e for e in json.load(f)["events"]}
    rows = list(csv.DictReader(open(f"{BASE}/out/basket_members.csv", encoding="utf-8-sig")))
    rows = [r for r in rows if r["basket_kind"] == "新聞點名"]
    # 讀入後即刻丟棄答案欄,只留成員身分
    members = {}
    for r in rows:
        members.setdefault(r["event_id"], {})[r["ticker"]] = {k: r.get(k) for k in KEEP}

    idx = {}
    for eid, ev in events.items():
        if eid not in TICKERS:
            continue
        idx[eid] = dgs10(ev["shock_start"], ev["shock_start"])
        pack = {"event_id": eid, "name": ev["name"], "narrative": ev["narrative"],
                "shock_start": ev["shock_start"], "news_shock_end": ev.get("news_shock_end"),
                "basket_definition": ev["basket_definition"],
                "evidence_cutoff": "申報日 < %s" % ev["shock_start"],
                "treasury_10y_pct_on_shock_start": idx[eid].get(ev["shock_start"]),
                "redacted": sorted(REDACT), "companies": []}
        for tk in TICKERS[eid]:
            m = members[eid][tk]
            c = dict(m)
            c["price_shock_start_close"] = pre_price(tk, ev["shock_start"])
            c["prefiling_docs"] = docs_index(eid).get(tk, [])
            pack["companies"].append(c)
        with open(f"{OUT}/{eid}.json", "w", encoding="utf-8") as f:
            json.dump(pack, f, ensure_ascii=False, indent=1)
        print(eid, ev["name"], "| 美債", pack["treasury_10y_pct_on_shock_start"],
              "| 各家收市價", {c["ticker"]: c["price_shock_start_close"] for c in pack["companies"]})

    with open(f"{OUT}/_遮蔽清單.md", "w", encoding="utf-8") as f:
        f.write("# 取證包遮蔽清單(KARST-210)\n\n本清單由 `build_packets.py` 機械保證。\n\n"
                "## 整欄不入包的欄位(本票要考的答案)\n\n"
                + "\n".join("- `%s`" % k for k in sorted(REDACT)) +
                "\n\n## 入包的欄位\n\n"
                + "\n".join("- `%s`" % k for k in KEEP + ["price_shock_start_close",
                                                          "prefiling_docs"]) +
                "\n\n## 為什麼衝擊窗相對跌幅照給\n\n"
                  "規格 v2.1 步六要「用衝擊前後的價格對照」,沒有它步六整格做不成。"
                  "它是事件本身的一部分(衝擊期間跌了多少),不是本票要考的答案"
                  "(答案是衝擊之後十二個月的超額)。199 已量過跌深與事後回報的關係,"
                  "見 199 總覽;此處照 204 口徑沿用。\n")


if __name__ == "__main__":
    main()
