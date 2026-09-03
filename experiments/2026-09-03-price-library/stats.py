"""KARST-171 步驟六:單一價格庫落地後的體檢數字(報告用)。唯讀。"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
LIB = ROOT / "data" / "prices" / "daily"


def main() -> None:
    man = pd.read_csv(LIB / "manifest.csv", dtype={"entity_id": str})
    ok = man[man["rows"] > 0]

    dup_total = 0
    rows_total = 0
    bytes_total = 0
    yr_first, yr_last = [], []
    per_entity_rows = {}
    for f in sorted(LIB.glob("part_*.parquet")):
        bytes_total += f.stat().st_size
        d = pd.read_parquet(f, columns=["entity_id", "ticker", "date", "series_role"])
        rows_total += len(d)
        p = d[d["series_role"] == "primary"]
        dup_total += int(p.duplicated(subset=["entity_id", "date"]).sum())
        g = p.groupby("entity_id")["date"]
        for eid, n in g.size().items():
            per_entity_rows[eid] = per_entity_rows.get(eid, 0) + int(n)
        yr_first.append(g.min())
        yr_last.append(g.max())

    fd = pd.concat(yr_first)
    ld = pd.concat(yr_last)
    pe = pd.Series(per_entity_rows)
    out = {
        "periods": int(len(man)),
        "status": man["status"].value_counts().to_dict(),
        "completion_rate_ok_partial": round(
            float((man["status"] != "fail").sum() / len(man)) * 100, 2
        ),
        "series_role": man["series_role"].value_counts().to_dict(),
        "entities_in_ticker_periods": int(man["entity_id"].nunique()),
        "entities_with_prices": int(ok["entity_id"].nunique()),
        "total_rows": rows_total,
        "primary_rows": int(pe.sum()),
        "duplicate_entity_date_in_primary": dup_total,
        "library_bytes": bytes_total,
        "library_mb": round(bytes_total / 1e6, 1),
        "first_date_year_hist": pd.to_datetime(fd).dt.year.value_counts().sort_index().to_dict(),
        "last_date_year_hist": pd.to_datetime(ld).dt.year.value_counts().sort_index().to_dict(),
        "rows_per_entity": {
            "min": int(pe.min()), "p10": int(pe.quantile(0.10)), "median": int(pe.median()),
            "p90": int(pe.quantile(0.90)), "max": int(pe.max()),
        },
        "entities_under_250_rows": int((pe < 250).sum()),
        "head_gap_days_median": float(ok["head_gap_days"].median()),
        "head_gap_over_45_days": int((ok["head_gap_days"] > 45).sum()),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    (Path(__file__).parent / "out" / "library_stats.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
