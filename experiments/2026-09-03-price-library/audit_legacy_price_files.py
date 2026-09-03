"""KARST-171 步驟四:盤點 154 家新增收市價與 6 個未登記價格檔(D-153 第 2 條)。

只讀。對每個舊檔:列出它有哪些代號、有多少個在 ticker_periods 登記過、
有多少個已經被本票的單一價格庫覆蓋(而且是全 OHLCV);未登記者逐個列出交主 agent。
不刪任何舊檔、不改任何舊檔。
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
OUTDIR = Path(__file__).parent / "out"

LEGACY = {
    "narrative_layers_v2_new_close": "experiments/2026-09-02-narrative-layers-v2/data/new_close.parquet",
    "timing_sweep_daily_close": "experiments/2026-09-02-timing-sweep/data/daily_close.parquet",
    "sector_safety_prices_daily": "experiments/2026-08-31-sector-safety/prices_daily.parquet",
    "fear_greed_prices_daily": "experiments/2026-08-31-fear-greed/prices_daily.parquet",
    "tenbagger_scan_counterexample": "experiments/2026-09-02-tenbagger-scan/data/counterexample_close.parquet",
    "tenbagger_casecontrol_monthly": "experiments/2026-09-02-tenbagger-casecontrol/data/prices_monthly.parquet",
}


def tickers_of(df: pd.DataFrame) -> list[str]:
    if "ticker" in df.columns:
        return sorted(set(df["ticker"].astype(str)))
    return sorted({str(c) for c in df.columns})


def main() -> None:
    tp = pd.read_parquet(ROOT / "data" / "universe" / "ticker_periods.parquet")
    registered = set(tp["ticker"])
    man = pd.read_csv(ROOT / "data" / "prices" / "daily" / "manifest.csv", dtype=str)
    covered = set(man.loc[man["status"].isin(["ok", "partial"]), "ticker"])

    report, unregistered_all = {}, {}
    for name, rel in LEGACY.items():
        p = ROOT / rel
        if not p.exists():
            report[name] = {"path": rel, "exists": False}
            continue
        df = pd.read_parquet(p)
        tk = tickers_of(df)
        reg = [t for t in tk if t in registered]
        cov = [t for t in tk if t in covered]
        unreg = [t for t in tk if t not in registered]
        unregistered_all[name] = unreg
        report[name] = {
            "path": rel,
            "exists": True,
            "bytes": p.stat().st_size,
            "shape": list(df.shape),
            "tickers": len(tk),
            "registered_in_ticker_periods": len(reg),
            "covered_by_new_library": len(cov),
            "unregistered": len(unreg),
            "superseded": len(unreg) == 0 and len(cov) == len(tk),
        }

    rows = []
    for name, unreg in unregistered_all.items():
        for t in unreg:
            rows.append({"file": name, "ticker": t})
    pd.DataFrame(rows).to_csv(OUTDIR / "legacy_unregistered_tickers.csv", index=False,
                              encoding="utf-8")
    (OUTDIR / "legacy_price_files_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("未登記代號合計:", len(rows), "個(逐個列在 out/legacy_unregistered_tickers.csv)")


if __name__ == "__main__":
    main()
