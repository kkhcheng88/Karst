# -*- coding: utf-8 -*-
"""KARST-220 擴樣本:補流通股數(本地面板缺口)。

**為什麼要這一步**:本票明文禁用 `basket_core.mcap_usd`(已知缺陷,KARST-219 修復中),
改用「未還原收市價 × 最近申報流通股數」。但本地 `data/panel/quarterly_v3.parquet` 的
`shares_outstanding` 對海外發行人與部分美國公司在衝擊日之前根本沒有值
(例:F 只到 2011-05-10、SPG 只到 2010-03-31 且值為 0、BCS/HSBC/BABA 只有 2022 之後、
COIN/MSTR/HOOD/NIO/TAL 完全沒有),`data/sec/companyfacts` 本地快取同樣缺。

故直接打 SEC XBRL 公司概念 API 取 `dei:EntityCommonStockSharesOutstanding` 全歷史,
**只取 `filed <= 衝擊起日`** 的最新一筆(時點紀律與面板一致),落 `out/shares_oos.csv`。
取不到即留空——不猜、不用財經網站。

輸出:out/shares_oos.csv(event_id, ticker, entity_id, shares, shares_filed, shares_form, note)
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
UA = {"User-Agent": "Karst research kaho@example.com"}

PICKS_TICKERS = {
    "E21": ["BCS", "LYG", "HSBC", "JPM"],
    "E22": ["BABA", "TAL", "NIO", "YUMC"],
    "E23": ["COIN", "MSTR", "RIOT", "HOOD"],
    "E24": ["AMAT", "ASML", "NVDA", "MU"],
    "E25": ["F", "GM", "APTV", "MGA"],
    "E26": ["VNO", "SPG", "O", "PLD"],
    "E27": ["UNH", "CVS", "MCK", "CNC"],
}

CONCEPT = ("https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/"
           "dei/EntityCommonStockSharesOutstanding.json")


def main() -> None:
    spec = json.loads((HERE / "new_events_spec_oos.json").read_text(encoding="utf-8"))
    cutoff = {e["event_id"]: e["shock_start"] for e in spec["events"]}
    # entity_id 一律由籃子檔取(零填充 CIK),避免手抄出錯
    mem = pd.read_csv(OUT / "basket_members_oos.csv", encoding="utf-8-sig",
                      dtype={"entity_id": str, "ticker": str})
    mem = mem[mem["basket_kind"] == "新聞點名"]
    eid_of = {(r.event_id, r.ticker): str(r.entity_id).zfill(10) for r in mem.itertuples()}

    rows = []
    for ev, tks in PICKS_TICKERS.items():
        for ticker in tks:
            cik = eid_of[(ev, ticker)]
            rec = dict(event_id=ev, ticker=ticker, entity_id=cik,
                       shares=float("nan"), shares_filed="", shares_form="", note="")
            try:
                req = urllib.request.Request(CONCEPT.format(cik=cik), headers=UA)
                with urllib.request.urlopen(req, timeout=40) as r:
                    d = json.loads(r.read())
                pts = [u for u in d.get("units", {}).get("shares", [])
                       if u.get("filed", "9999") < cutoff[ev]]
                pts.sort(key=lambda u: (u["filed"], u["end"]))
                if pts:
                    k = pts[-1]
                    rec.update(shares=float(k["val"]), shares_filed=k["filed"],
                               shares_form=k.get("form", ""), note=f"SEC XBRL,取 < {cutoff[ev]} 最新一筆(共 {len(pts)} 筆)")
                else:
                    rec["note"] = "SEC XBRL 在衝擊起日之前無流通股數"
                if ticker == "MGA" and rec["shares"] == rec["shares"]:
                    rec["note"] += ";MGA 為加拿大發行人,面額以美元計,未另換算"
            except Exception as e:  # noqa: BLE001
                rec["note"] = "抓取失敗:" + type(e).__name__
            rows.append(rec)
            print(f"{ev} {ticker:5s} shares={rec['shares']!r:>18} filed={rec['shares_filed']} {rec['note'][:44]}",
                  flush=True)
            time.sleep(0.25)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "shares_oos.csv", index=False, encoding="utf-8-sig")
    ok = int(df["shares"].notna().sum())
    print(f"完成:{ok}/{len(df)} 家有股數")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
