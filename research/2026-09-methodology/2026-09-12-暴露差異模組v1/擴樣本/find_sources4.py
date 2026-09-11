# -*- coding: utf-8 -*-
"""出處核對第五輪:抓候選出處正文,核『有沒有提到本宗的敘事與籃子』;並重篩 E26 窗口。"""
from __future__ import annotations

import json
import re
import ssl
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

UA = {"User-Agent": "Karst research kaho@example.com"}
CTX = ssl._create_unverified_context()  # noqa: SLF001
ROOT = Path(r"C:\projects\Karst")

DOCS = [
 ("E21_AVIVA_6K", "https://www.sec.gov/Archives/edgar/data/1140022/000119163816002226/av201606246k.htm",
  ["referendum", "Barclays", "Lloyds", "RBS", "banks"]),
 ("E23_GDLC_8K", "https://www.sec.gov/Archives/edgar/data/1729997/000095017022012299/gdlc-20220629.htm",
  ["Celsius", "bitcoin", "digital asset", "liquidity"]),
 ("E23_MIGI_8K", "https://www.sec.gov/Archives/edgar/data/1813603/000121390022035365/ea162182ex99-1_mawson.htm",
  ["Celsius", "bitcoin", "hash", "mining"]),
 ("E24_AMAT_8K", "https://www.sec.gov/Archives/edgar/data/6951/000119312522261327/d370937d8k.htm",
  ["export", "China", "controls", "revenue"]),
 ("E25_DANA_8K", "https://www.sec.gov/Archives/edgar/data/26780/000119312523264461/d528555dex991.htm",
  ["strike", "UAW", "production"]),
 ("E25_WOR_8K", "https://www.sec.gov/Archives/edgar/data/108516/000095017023051497/wor-ex99_1.htm",
  ["strike", "UAW", "customer"]),
 ("E26_CIO_8K", "https://www.sec.gov/Archives/edgar/data/1572894/000119312523273691/d930402dex991.htm",
  ["interest rate", "10-year", "Treasury", "cap rate"]),
 ("E27_AETNA_8K", "https://www.sec.gov/Archives/edgar/data/1122304/000112230418000011/exhibit99_1.htm",
  ["Amazon", "Berkshire", "JPMorgan", "health care"]),
]


def fetch(u: str) -> str:
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=40, context=CTX) as r:
        raw = r.read().decode("utf-8", "ignore")
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = re.sub(r"&nbsp;?", " ", t)
    return re.sub(r"\s+", " ", t)


def screen_e26() -> None:
    sys.path.insert(0, str(ROOT / "research" / "2026-09-methodology" / "2026-09-10-①行業殺錯事件籃子"))
    from basket_core import build_wide, load_prices, load_spy, resolve_tickers  # noqa: E402
    spy_df = load_spy()
    px = load_prices()
    cal, wide, spy = build_wide(px, spy_df)
    cal = pd.DatetimeIndex(cal)
    tick = ["SPG", "O", "VNO", "BXP", "ARE", "PLD", "SLG", "KIM", "REG", "AVB",
            "EQR", "ESS", "MAA", "NNN", "WPC", "CIO", "CUZ", "HIW", "DEI", "PGRE"]
    for shock, end in (("2023-09-19", "2023-10-19"), ("2023-09-19", "2023-10-27"),
                       ("2023-08-01", "2023-10-19")):
        i0 = int(cal.searchsorted(pd.Timestamp(shock), side="left"))
        t0 = cal[i0]
        i_end = int(min(cal.searchsorted(pd.Timestamp(end), side="right") - 1, len(cal) - 1))
        hi = int(min(i_end + 21, len(cal) - 1))
        res = resolve_tickers(tick, t0)
        good = res[res["resolve_status"] == "已解析"]["entity_id"].tolist()
        mem = [e for e in good if e in wide.columns and np.isfinite(wide[e].iloc[i0])]
        seg = wide.loc[:, mem].iloc[i0:hi + 1]
        rel = seg.div(seg.iloc[0], axis=1).div(spy.iloc[i0:hi + 1] / spy.iloc[i0], axis=0)
        br = rel.mean(axis=1, skipna=True)
        i_tr = i0 + int(np.nanargmin(br.to_numpy()))
        print(f"E26 {shock}→{end}: 可用 {len(mem)}/{len(tick)} 相對跌 {br.min()-1:.2%} "
              f"低點 {cal[i_tr].date()} 窗末 {cal[hi].date()}", flush=True)


def main() -> None:
    for k, u, kws in DOCS:
        try:
            t = fetch(u)
            hit = {w: (w.lower() in t.lower()) for w in kws}
            print(f"{k} len={len(t)} {hit}", flush=True)
            for w in kws:
                i = t.lower().find(w.lower())
                if i >= 0:
                    print("    ...", t[max(0, i - 110):i + 160].replace("\n", " "), flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"{k} ERR {type(e).__name__} {str(e)[:60]}", flush=True)
    print("--- E26 重篩 ---", flush=True)
    screen_e26()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
