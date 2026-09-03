"""KARST-171:逐個查未登記代號的原因,寫入 out/unregistered_reasons.csv。唯讀。"""

import json
import os

import pandas as pd

ROOT = r"C:\projects\Karst"
ANN = {"10-K", "10-K405", "10-KSB", "10-KSB405", "20-F", "40-F"}
MAJOR = {"NYSE", "Nasdaq", "NYSE American", "CBOE", "BZX", "NYSEArca", "NYSE Arca"}


def main() -> None:
    ct = json.load(open(rf"{ROOT}\data\sec\company_tickers.json"))
    ent = pd.read_parquet(rf"{ROOT}\data\universe\entities.parquet")
    ids = set(ent["entity_id"])
    tp = pd.read_parquet(rf"{ROOT}\data\universe\ticker_periods.parquet")
    known = set(tp["ticker"])
    d = pd.read_csv(rf"{ROOT}\experiments\2026-09-03-price-library\out\legacy_unregistered_tickers.csv")
    rows = []
    for t in sorted(set(d["ticker"])):
        if t in known:
            continue
        cik = ct.get(t)
        if cik is None:
            rows.append({"ticker": t, "cik": "", "reason": "不在證監會 2026-09-02 代號快照"})
            continue
        if cik in ids:
            rows.append({"ticker": t, "cik": cik, "reason": "實體在名單內,但這個代號不是它的登記代號"})
            continue
        p = rf"{ROOT}\data\sec\submissions\CIK{cik}.json"
        if not os.path.exists(p):
            rows.append({"ticker": t, "cik": cik, "reason": "無 submissions 快取"})
            continue
        s = json.load(open(p))
        ex = sorted({x for x in (s.get("exchanges") or []) if x})
        ann = bool(set(s["filings"]["recent"]["form"]) & ANN)
        et = s.get("entityType")
        bits = []
        if not ex:
            bits.append("交易所欄空白(E3)")
        elif not (set(ex) & MAJOR):
            bits.append(f"只有 {'/'.join(ex)}(E3)")
        if not ann:
            bits.append("無年報(I3)")
        if et not in ("operating", "other"):
            bits.append(f"entityType={et}(I4)")
        rows.append({"ticker": t, "cik": cik, "reason": ";".join(bits) or f"其他(exchanges={ex}, type={et})",
                     "name": s.get("name", "")})
    out = pd.DataFrame(rows)
    out.to_csv(rf"{ROOT}\experiments\2026-09-03-price-library\out\unregistered_reasons.csv",
               index=False, encoding="utf-8")
    print(out.to_string())


if __name__ == "__main__":
    main()
