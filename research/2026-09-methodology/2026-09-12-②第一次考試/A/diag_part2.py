# -*- coding: utf-8 -*-
"""診斷二:entity 是否跨檔;population 的列數、cik 數、需要的日期數。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
PRICES = ROOT / "data" / "prices" / "daily"
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"


def main() -> None:
    seen: dict[str, str] = {}
    dup = 0
    for p in sorted(PRICES.glob("part_*.parquet")):
        d = pd.read_parquet(p, columns=["entity_id"])
        for e in d["entity_id"].unique():
            if e in seen:
                dup += 1
            seen[e] = p.name
        del d
    print("全宇宙 entity 數", len(seen), ";跨檔重複", dup)

    pop = pd.read_parquet(CACHE / "population_improvement.parquet")
    print("population 列數", len(pop), "欄數", pop.shape[1])
    print("distinct cik", pop["cik"].nunique())
    print("年份分佈", pop["year"].value_counts().sort_index().to_dict())
    need = set(pop["reaction_date"].dropna()) | set(pop["prev_date"].dropna()) | set(pop["t2_date"].dropna())
    print("s10 需要日期數", len(need))
    picks = json.loads((CACHE / "picks.json").read_text(encoding="utf-8"))
    print("pick 事件數", len(picks["main"]), len(picks["backup"]),
          "distinct cik", len({p["acc"] for p in picks["main"] + picks["backup"]}))
    meta = pop.set_index("accessionNumber")
    print("主清單 distinct cik", len({meta.loc[p["acc"], "cik"] for p in picks["main"]}))
    evd = sorted({meta.loc[p["acc"], "reaction_date"] for p in picks["main"] + picks["backup"]})
    print("事件反應日 distinct", len(evd), evd[0], evd[-1])
    print("每檔價格 entity 數 ~", len(seen) / 16)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
