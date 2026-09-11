# -*- coding: utf-8 -*-
"""出處核對第六輪(最後一輪):E23 找加密礦企/交易所申報;E26 長窗覆核;E27 換 HCA 正本。"""
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

FTS = [
 ("E23 bitcoin miner 8-K", '"bitcoin" AND "liquidity"', "2022-06-01", "2022-07-31", "8-K"),
 ("E23 coinbase", '"Coinbase"', "2022-06-01", "2022-07-31", "8-K"),
 ("E27 健保合資", '"Amazon" AND "Berkshire"', "2018-01-29", "2018-02-15", "8-K"),
]

URLS = [
 ("E27_HCA_8K", "https://www.sec.gov/Archives/edgar/data/860730/000119312518024575/d521507dex991.htm",
  ["Amazon", "Berkshire", "JPMorgan", "health"]),
]


def fts(q, d1, d2, forms):
    url = ("https://efts.sec.gov/LATEST/search-index?q=" + urllib.parse.quote(q)
           + "&dateRange=custom&startdt=" + d1 + "&enddt=" + d2 + "&forms=" + forms)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())
    return [(h["_source"].get("display_names", [""])[0][:44], h["_source"].get("file_date"),
             h["_id"][:60]) for h in d.get("hits", {}).get("hits", [])[:8]]


def fetch(u: str) -> str:
    req = urllib.request.Request(u, headers=UA)
    with urllib.request.urlopen(req, timeout=40, context=CTX) as r:
        raw = r.read().decode("utf-8", "ignore")
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = re.sub(r"&nbsp;?", " ", t)
    return re.sub(r"\s+", " ", t)


def main() -> None:
    for label, q, d1, d2, forms in FTS:
        print("###", label, flush=True)
        try:
            for row in fts(q, d1, d2, forms):
                print("   ", row, flush=True)
        except Exception as e:  # noqa: BLE001
            print("   ERR", type(e).__name__, str(e)[:60], flush=True)
    for k, u, kws in URLS:
        try:
            t = fetch(u)
            print(k, len(t), {w: (w.lower() in t.lower()) for w in kws}, flush=True)
            for w in kws:
                i = t.lower().find(w.lower())
                if i >= 0:
                    print("   ...", t[max(0, i - 120):i + 180], flush=True)
        except Exception as e:  # noqa: BLE001
            print(k, "ERR", type(e).__name__, str(e)[:60], flush=True)

    sys.path.insert(0, str(ROOT / "research" / "2026-09-methodology" / "2026-09-10-①行業殺錯事件籃子"))
    from basket_core import build_wide, load_prices, load_spy, resolve_tickers  # noqa: E402
    spy_df = load_spy()
    px = load_prices()
    cal, wide, spy = build_wide(px, spy_df)
    cal = pd.DatetimeIndex(cal)
    tick = ["SPG", "O", "VNO", "BXP", "ARE", "PLD", "SLG", "KIM", "REG", "AVB",
            "EQR", "ESS", "MAA", "NNN", "WPC"]
    for shock, end in (("2023-09-19", "2023-10-19"), ("2023-09-19", "2023-12-29"),
                       ("2023-07-31", "2023-10-19")):
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


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
