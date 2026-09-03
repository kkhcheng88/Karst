"""KARST-171 追查:對帳中 LMT 與 TAP 全期出現同一個百分比的偏差,查是不是派息重算。

假設:adj_close 每次派息都會把整條歷史按同一個比率重新縮放,所以同一個代號在兩個
不同日期抓回來的已調整價,差幅是一個常數比率,不是隨機噪音。唯讀。
"""

import json
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
SNAP = "2026-08-28-493fd1df1cb9"


def main() -> None:
    con = sqlite3.connect(f"file:{ROOT / 'karst.sqlite'}?mode=ro", uri=True)
    ent = pd.read_sql("select entity_id, cik from entity where cik is not null", con)
    et = pd.read_sql("select entity_id, ticker from entity_ticker", con)
    con.close()
    prod = ent.merge(et, on="entity_id")
    prod["cik10"] = prod["cik"].astype(str).str.zfill(10)

    px = pd.read_parquet(ROOT / "data" / "snapshots" / SNAP / "prices.parquet")
    px["date"] = pd.to_datetime(px["date"]).dt.date

    out = {}
    for tk in ["LMT", "TAP"]:
        row = prod[prod["ticker"] == tk].iloc[0]
        a = px[px["entity_id"] == row.entity_id][["date", "close"]].rename(columns={"close": "prod"})
        lib = []
        for f in sorted((ROOT / "data" / "prices" / "daily").glob("part_*.parquet")):
            d = pd.read_parquet(f, columns=["entity_id", "ticker", "date", "adj_close", "close"])
            d = d[(d["entity_id"] == row.cik10) & (d["ticker"] == tk)]
            if len(d):
                lib.append(d)
        b = pd.concat(lib, ignore_index=True)
        j = a.merge(b[["date", "adj_close", "close"]], on="date", how="inner")
        ratio = j["adj_close"] / j["prod"]
        out[tk] = {
            "days": int(len(j)),
            "ratio_min": float(ratio.min()),
            "ratio_max": float(ratio.max()),
            "ratio_median": float(ratio.median()),
            "ratio_std": float(ratio.std()),
            "raw_close_equal_days": int((abs(j["close"] - j["prod"]) < 1e-9).sum()),
        }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    (Path(__file__).parent / "out" / "adj_drift.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
