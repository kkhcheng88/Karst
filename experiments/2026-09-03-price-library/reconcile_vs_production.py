"""KARST-171 步驟五:與生產快照抽 20 個重疊代號對帳收市價。

生產快照的收市價口徑是 yfinance auto_adjust=True(D-026 adjusted-close-only),
對應本庫的 adj_close 欄。生產庫全程 mode=ro 唯讀開啟。
"""

import json
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
OUTDIR = Path(__file__).parent / "out"
SNAP = "2026-08-28-493fd1df1cb9"
NSAMPLE = 20


def main() -> None:
    con = sqlite3.connect(f"file:{ROOT / 'karst.sqlite'}?mode=ro", uri=True)
    ent = pd.read_sql("select entity_id, entity_kind, cik from entity", con)
    et = pd.read_sql("select entity_id, ticker from entity_ticker", con)
    con.close()
    prod = ent.merge(et, on="entity_id")
    prod = prod[prod["cik"].notna()].copy()
    prod["cik10"] = prod["cik"].astype(str).str.zfill(10)

    px = pd.read_parquet(ROOT / "data" / "snapshots" / SNAP / "prices.parquet")
    px = px[["date", "entity_id", "close"]].copy()
    px["date"] = pd.to_datetime(px["date"]).dt.date

    man = pd.read_csv(ROOT / "data" / "prices" / "daily" / "manifest.csv", dtype=str)
    man = man[man["series_role"] == "primary"]
    ours_keys = set(zip(man["entity_id"], man["ticker"]))

    cand = prod[prod["entity_id"].isin(px["entity_id"].unique())]
    cand = cand[[(r.cik10, r.ticker) in ours_keys for r in cand.itertuples()]]
    cand = cand.sort_values("ticker").reset_index(drop=True)
    step = max(1, len(cand) // NSAMPLE)
    sample = cand.iloc[::step].head(NSAMPLE)

    lib = []
    for f in sorted((ROOT / "data" / "prices" / "daily").glob("part_*.parquet")):
        d = pd.read_parquet(f, columns=["entity_id", "ticker", "date", "adj_close"])
        d = d[d["entity_id"].isin(set(sample["cik10"]))]
        if len(d):
            lib.append(d)
    lib = pd.concat(lib, ignore_index=True)

    rows = []
    for r in sample.itertuples():
        a = px[px["entity_id"] == r.entity_id][["date", "close"]].rename(columns={"close": "prod"})
        b = lib[(lib["entity_id"] == r.cik10) & (lib["ticker"] == r.ticker)][
            ["date", "adj_close"]
        ].rename(columns={"adj_close": "new"})
        j = a.merge(b, on="date", how="inner")
        if j.empty:
            rows.append({"ticker": r.ticker, "cik": r.cik10, "overlap_days": 0})
            continue
        diff = (j["new"] - j["prod"]) / j["prod"] * 100
        j2 = j[j["date"] < pd.Timestamp("2026-08-28").date()]
        d2 = (j2["new"] - j2["prod"]) / j2["prod"] * 100 if len(j2) else diff
        rows.append(
            {
                "ticker": r.ticker,
                "cik": r.cik10,
                "overlap_days": int(len(j)),
                "median_diff_pct": round(float(diff.median()), 6),
                "mean_abs_diff_pct": round(float(diff.abs().mean()), 6),
                "p95_abs_diff_pct": round(float(diff.abs().quantile(0.95)), 6),
                "max_abs_diff_pct": round(float(diff.abs().max()), 6),
                "max_abs_diff_pct_excl_snapshot_day": round(float(d2.abs().max()), 6),
            }
        )
    out = pd.DataFrame(rows)
    out.to_csv(OUTDIR / "reconcile_20.csv", index=False, encoding="utf-8")
    print(out.to_string())
    summary = {
        "snapshot": SNAP,
        "n": int(len(out)),
        "median_of_max_abs_diff_pct": float(out["max_abs_diff_pct"].median()),
        "worst_max_abs_diff_pct": float(out["max_abs_diff_pct"].max()),
        "worst_excl_snapshot_day": float(out["max_abs_diff_pct_excl_snapshot_day"].max()),
    }
    (OUTDIR / "reconcile_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
