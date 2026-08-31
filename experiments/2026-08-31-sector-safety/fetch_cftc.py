"""KARST-119 取數(二):CFTC 金融版(TFF)週報,E-mini 標普 500 資產管理人持倉。

照 KARST-112:一律用合約代碼 13874A 認合約(合約名會改,代碼不會);
只取 FutOnly(期貨本身,不併期權)一套,避免兩套口徑混用。
屬探索性數據,只落 experiments/,不入生產庫。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import requests

OUT = Path(__file__).resolve().parent
URL = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
CODE = "13874A"
FIELDS = [
    "report_date_as_yyyy_mm_dd",
    "futonly_or_combined",
    "open_interest_all",
    "asset_mgr_positions_long",
    "asset_mgr_positions_short",
    "lev_money_positions_long",
    "lev_money_positions_short",
]


def main() -> int:
    rows: list[dict] = []
    offset = 0
    while True:
        resp = requests.get(
            URL,
            params={
                "$limit": 5000,
                "$offset": offset,
                "$select": ",".join(FIELDS),
                "$where": f"cftc_contract_market_code='{CODE}'",
                "$order": "report_date_as_yyyy_mm_dd",
            },
            timeout=120,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        rows.extend(batch)
        offset += len(batch)
        if len(batch) < 5000:
            break

    frame = pd.DataFrame(rows)
    frame["report_date"] = pd.to_datetime(
        frame["report_date_as_yyyy_mm_dd"]
    ).dt.tz_localize(None)
    for col in FIELDS[2:]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")

    print("全部列數:", len(frame))
    print(frame["futonly_or_combined"].value_counts().to_string())

    fut = frame[frame["futonly_or_combined"] == "FutOnly"].copy()
    fut = fut.sort_values("report_date").reset_index(drop=True)
    fut = fut.drop_duplicates(subset=["report_date"], keep="last")
    fut.to_parquet(OUT / "cftc_tff_es.parquet", index=False)

    print("FutOnly 週報數:", len(fut))
    print("由", fut["report_date"].min().date(), "至", fut["report_date"].max().date())
    weekday = fut["report_date"].dt.day_name().value_counts()
    print("截數日星期分佈:")
    print(weekday.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
