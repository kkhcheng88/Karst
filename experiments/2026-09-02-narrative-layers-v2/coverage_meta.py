"""KARST-157 步驟 4:宇宙補齊家數、缺失名單、價格來源憑證入 meta。

驗收條件要求「價格快照編號入 meta」。本票沒有生成正式快照編號:登記那一步會寫
生產庫 karst.sqlite,而同一張票的驗收條件要求生產庫 SHA256 首 16 位維持不變
(見 CRITERIA.md 第 1.3 節的偏離聲明)。故此這裡記的是**價格來源憑證**:
既有 parquet 的路徑與 SHA256、本票新抓 parquet 的路徑與 SHA256、抓取窗口與口徑。

Run: PYTHONUTF8=1 python coverage_meta.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "out"
V1 = REPO / "experiments" / "2026-09-02-narrative-layers"
PARQUET_OLD = REPO / "experiments" / "2026-09-02-timing-sweep" / "data" / "daily_close.parquet"
PARQUET_NEW = HERE / "data" / "new_close.parquet"
CACHE = REPO / "data" / "sec" / "10k_text"

SLICES = ["2015-06-30", "2019-06-30", "2023-06-30"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def main() -> int:
    uni = json.loads((OUT / "universe_v2.json").read_text(encoding="utf-8"))
    price = json.loads((OUT / "new_price_meta.json").read_text(encoding="utf-8"))
    tm_new = json.loads((OUT / "text_manifest_new.json").read_text(encoding="utf-8")) \
        if (OUT / "text_manifest_new.json").exists() else {}
    tm_v1 = json.loads((V1 / "out" / "text_manifest.json").read_text(encoding="utf-8"))
    miss_new = json.loads((OUT / "text_missing_new.json").read_text(encoding="utf-8")) \
        if (OUT / "text_missing_new.json").exists() else {}

    px_new = pd.read_parquet(PARQUET_NEW) if PARQUET_NEW.exists() else pd.DataFrame()

    # 文本覆蓋(合併 v1 與本票)
    cov = {}
    for sl in SLICES:
        v1_ok = sum(1 for k, v in tm_v1.items() if k.endswith(sl) and v.get("ok"))
        v2_ok = sum(1 for k, v in tm_new.items() if k.endswith(sl) and v.get("ok"))
        why_v2: dict[str, int] = {}
        for k, v in tm_new.items():
            if k.endswith(sl) and not v.get("ok"):
                w = str(v.get("why", ""))
                bucket = ("切節失敗" if w.startswith("extract failed")
                          else "切片前未有 10-K" if "no 10-K filed before" in w
                          else "過期" if w.startswith("stale")
                          else "無 CIK / 無 10-K" if ("CIK" in w or "no filings" in w)
                          else "抓取或解析失敗")
                why_v2[bucket] = why_v2.get(bucket, 0) + 1
        cov[sl] = {"v1_574_texts": v1_ok, "v2_new_texts": v2_ok,
                   "total_texts": v1_ok + v2_ok, "v2_missing_reasons": why_v2}

    cache_files = sorted(p.name for p in CACHE.glob("*.txt.gz")) if CACHE.exists() else []
    manifest_lines = 0
    mine = 0
    mpath = CACHE / "manifest.jsonl"
    if mpath.exists():
        for ln in mpath.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            manifest_lines += 1
            try:
                if json.loads(ln).get("by") == "KARST-157":
                    mine += 1
            except Exception:  # noqa: BLE001
                pass

    meta = {
        "ticket": "KARST-157",
        "criteria_commit": "1c4a7b5",
        "universe": {
            "source_1_existing_stocks": uni["existing_stocks"],
            "source_2_manual_table_tickers": uni["manual_count"],
            "source_2_not_in_existing": len(uni["manual_not_in_existing"]),
            "source_3_theme_etfs": len(uni["theme_etfs"]),
            "source_3_us_names": len(uni["etf_names"]),
            "source_3_dropped_non_us": uni["dropped_non_us"],
            "universe_stock_count_before_filter": uni["universe_stock_count"],
            "new_tickers_requested": price["new_requested"],
            "dropped_non_equity": price["non_equity_dropped"],
            "new_tickers_priced": price["priced_ok"],
            "price_missing": price["price_missing"],
            "final_universe_stocks": uni["existing_stocks"] + price["priced_ok"],
        },
        "price_provenance": {
            "note": "本票沒有生成正式快照編號;見 CRITERIA.md 1.3 的偏離聲明",
            "existing_parquet": str(PARQUET_OLD),
            "existing_parquet_sha256": sha256_file(PARQUET_OLD),
            "new_parquet": str(PARQUET_NEW),
            "new_parquet_sha256": sha256_file(PARQUET_NEW) if PARQUET_NEW.exists() else None,
            "new_parquet_cols": int(px_new.shape[1]) if len(px_new) else 0,
            "new_parquet_rows": int(px_new.shape[0]) if len(px_new) else 0,
            "source": "yfinance", "auto_adjust": True,
            "window": price["window"],
        },
        "text_coverage": cov,
        "text_missing_new": miss_new,
        "shared_cache_d134": {
            "root": str(CACHE),
            "files": len(cache_files),
            "manifest_lines_total": manifest_lines,
            "manifest_lines_by_KARST_157": mine,
        },
    }
    (OUT / "coverage_meta_v2.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"universe": meta["universe"], "text_coverage": cov,
                      "cache": meta["shared_cache_d134"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
