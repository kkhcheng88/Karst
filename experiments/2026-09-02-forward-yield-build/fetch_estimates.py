"""KARST-136 第一步:逐隻公司抓 yfinance 季度 EPS 預估,落本地快取。

照 SPEC.md 第六節:一隻一個 parquet,已存在即跳過,指數退避重試,批間停頓。
快取目錄不入 git。

用法:
    python fetch_estimates.py            # 抓齊未抓過的
    python fetch_estimates.py --retry    # 連上次失敗的一齊再試
"""
from __future__ import annotations

import argparse
import pathlib
import random
import sys
import time

import pandas as pd
import yfinance as yf

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
CACHE = HERE / "cache" / "earnings_dates"
CACHE.mkdir(parents=True, exist_ok=True)
LOG = HERE / "cache" / "fetch_log.csv"

PANEL = REPO / "experiments" / "2026-09-02-multiples-oracle-scan" / "data" / "constituent_panel.parquet"

BATCH = 25
SLEEP_WITHIN = 0.9      # 每隻之間
SLEEP_BETWEEN = 6.0     # 每批之間
MAX_TRIES = 3


def symbols() -> list[str]:
    p = pd.read_parquet(PANEL, columns=["symbol"])
    return sorted(p["symbol"].dropna().unique().tolist())


def fetch_one(sym: str) -> tuple[str, int, str]:
    """回 (狀態, 列數, 訊息)。狀態 ∈ ok / empty / error。"""
    last = ""
    for attempt in range(MAX_TRIES):
        try:
            t = yf.Ticker(sym)
            df = t.get_earnings_dates(limit=100)
            if df is None or len(df) == 0:
                return "empty", 0, "no rows"
            out = df.reset_index()
            out.columns = [str(c) for c in out.columns]
            out["symbol"] = sym
            out.to_parquet(CACHE / f"{sym}.parquet", index=False)
            return "ok", len(out), ""
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"[:200]
            time.sleep((2 ** attempt) * 2.5 + random.random())
    return "error", 0, last


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--retry", action="store_true")
    args = ap.parse_args()

    syms = symbols()
    done = {p.stem for p in CACHE.glob("*.parquet")}

    prev = {}
    if LOG.exists():
        lg = pd.read_csv(LOG)
        prev = dict(zip(lg["symbol"], lg["status"]))

    todo = []
    for s in syms:
        if s in done:
            continue
        if not args.retry and prev.get(s) in ("empty", "error"):
            continue
        todo.append(s)

    print(f"成分 {len(syms)} 隻,已快取 {len(done)},今次要抓 {len(todo)}", flush=True)

    rows = [{"symbol": k, "status": v, "n_rows": 0, "msg": ""} for k, v in prev.items()]
    rows = [r for r in rows if r["symbol"] not in todo]

    for i, sym in enumerate(todo):
        st, n, msg = fetch_one(sym)
        rows.append({"symbol": sym, "status": st, "n_rows": n, "msg": msg})
        if (i + 1) % 10 == 0 or st != "ok":
            print(f"[{i+1}/{len(todo)}] {sym} -> {st} {n} {msg}", flush=True)
        time.sleep(SLEEP_WITHIN + random.random() * 0.4)
        if (i + 1) % BATCH == 0:
            pd.DataFrame(rows).to_csv(LOG, index=False, encoding="utf-8")
            time.sleep(SLEEP_BETWEEN)

    lg = pd.DataFrame(rows).drop_duplicates("symbol", keep="last")
    lg.to_csv(LOG, index=False, encoding="utf-8")
    print("\n狀態分佈:")
    print(lg["status"].value_counts().to_string())
    ok = lg[lg["status"] == "ok"]
    print(f"有貨 {len(ok)} 隻,列數中位 {ok['n_rows'].median() if len(ok) else 0}")


if __name__ == "__main__":
    sys.exit(main())
