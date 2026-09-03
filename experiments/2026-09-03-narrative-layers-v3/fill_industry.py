# -*- coding: utf-8 -*-
"""KARST-175 步驟一:只對缺 industry 的公司抓 yfinance info。

照 CRITERIA_rerun.md 第 4 節:
- 只抓現有 meta 缺 industry 的公司(上限 85 家)
- 逐家抓,每家之間退讓 1.2-2.0 秒;失敗者重試一次(退讓 1.5-2.5 秒)
- 取 industry 與 sector 兩欄,存 out/industry_fill.csv 附抓取日

跑法: set PYTHONUTF8=1 && python fill_industry.py
"""
from __future__ import annotations

import csv
import io
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)

V1 = REPO / "experiments" / "2026-09-02-narrative-layers"
V2 = REPO / "experiments" / "2026-09-02-narrative-layers-v2"
CHAIN = REPO / "experiments" / "2026-09-02-chain-layers" / "chain_membership_v2_2.csv"
MAX_FETCH = 85


def load_meta() -> dict:
    meta = json.loads((V1 / "out" / "ticker_meta.json").read_text(encoding="utf-8"))
    p = V2 / "out" / "ticker_meta_new.json"
    if p.exists():
        for t, v in json.loads(p.read_text(encoding="utf-8")).items():
            meta.setdefault(t, v)
    return meta


def main() -> int:
    import yfinance as yf

    with io.open(CHAIN, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    tickers = sorted({r["ticker"] for r in rows})
    meta = load_meta()
    need = [t for t in tickers if not ((meta.get(t) or {}).get("industry"))]
    print(f"chain tickers={len(tickers)}  need industry={len(need)}")
    if len(need) > MAX_FETCH:
        raise SystemExit(f"需要抓 {len(need)} 家,超過票面上限 {MAX_FETCH};停手")

    got: dict[str, dict] = {}
    failed: list[str] = []
    for i, t in enumerate(need, 1):
        try:
            info = yf.Ticker(t).info or {}
            got[t] = {
                "industry": info.get("industry") or "",
                "sector": info.get("sector") or "",
                "longName": info.get("longName") or "",
                "shortName": info.get("shortName") or "",
            }
            print(f"[{i}/{len(need)}] {t} -> {got[t]['industry'] or '(空)'} / {got[t]['sector'] or '(空)'}")
        except Exception as e:  # noqa: BLE001
            failed.append(t)
            print(f"[{i}/{len(need)}] {t} -> FAIL {type(e).__name__}")
        time.sleep(random.uniform(1.2, 2.0))

    if failed:
        print(f"重試 {len(failed)} 家")
        retry, failed2 = list(failed), []
        for t in retry:
            try:
                info = yf.Ticker(t).info or {}
                got[t] = {
                    "industry": info.get("industry") or "",
                    "sector": info.get("sector") or "",
                    "longName": info.get("longName") or "",
                    "shortName": info.get("shortName") or "",
                }
                print(f"  retry {t} -> {got[t]['industry'] or '(空)'}")
            except Exception as e:  # noqa: BLE001
                failed2.append(t)
                print(f"  retry {t} -> FAIL {type(e).__name__}")
            time.sleep(random.uniform(1.5, 2.5))
        failed = failed2

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    with io.open(OUT / "industry_fill.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["ticker", "industry", "sector", "longName",
                                           "shortName", "status", "fetchedAt"])
        w.writeheader()
        for t in need:
            v = got.get(t)
            if v is None:
                w.writerow({"ticker": t, "industry": "", "sector": "", "longName": "",
                            "shortName": "", "status": "fail", "fetchedAt": stamp})
            else:
                w.writerow({"ticker": t, **v,
                            "status": "ok" if v["industry"] else "no_industry",
                            "fetchedAt": stamp})
    n_ok = sum(1 for t in need if (got.get(t) or {}).get("industry"))
    print(f"written -> out/industry_fill.csv  有 industry {n_ok}/{len(need)}  失敗 {len(failed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
