"""KARST-136:在本票這批成分上重測 yfinance 預估值的事後改寫率。

做法照 KARST-125 的 `verify_yahoo_estimate_vintage.py`(Wayback 舊版頁面 vs 今日值,
已含「欄位次序」與「拆股換算」兩個坑的修正),只換樣本:由本票 587 隻成分中
按市值分層隨機抽 14 隻(固定種子),與 KARST-125 那六隻不重疊,好讓兩次量度互相獨立。

輸出:out/vintage_results.json、out/vintage_report.txt(本目錄)
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import random

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
SRC = REPO / "experiments" / "2026-08-31-quarterly-consensus" / "verify_yahoo_estimate_vintage.py"
PANEL = REPO / "experiments" / "2026-09-02-multiples-oracle-scan" / "data" / "constituent_panel.parquet"

KARST125 = {"CROX", "AAPL", "NVDA", "MSFT", "INTC", "TSLA"}
N_LARGE, N_REST = 7, 7
SEED = 20260902


def pick() -> list[str]:
    p = pd.read_parquet(PANEL, columns=["symbol", "month_end", "mcap"])
    last = p["month_end"].max()
    snap = (p[p["month_end"] == last].dropna(subset=["mcap"])
            .sort_values("mcap", ascending=False))
    syms = [s for s in snap["symbol"].tolist() if s not in KARST125]
    cut = max(len(syms) // 4, N_LARGE)
    rnd = random.Random(SEED)
    large = rnd.sample(syms[:cut], N_LARGE)
    rest = rnd.sample(syms[cut:], N_REST)
    return sorted(large + rest)


def main() -> None:
    spec = importlib.util.spec_from_file_location("vintage", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    mod.TICKERS = pick()
    mod.OUT = str(HERE / "out")
    mod.RAW = str(HERE / "cache" / "wayback")
    os.makedirs(mod.OUT, exist_ok=True)
    os.makedirs(mod.RAW, exist_ok=True)
    print("樣本:", ", ".join(mod.TICKERS), flush=True)

    import traceback
    try:
        mod.main()
    except Exception:  # noqa: BLE001
        mod.log(traceback.format_exc())
    # 注意:vintage_results.json 由 mod.main() 自己寫,這裡**不可以**再開一次
    # 同名檔——以 "w" 開檔即使不寫任何嘢一樣會把它清空(踩過一次)。
    with open(os.path.join(mod.OUT, "vintage_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(mod.log_lines))
    print("log ->", os.path.join(mod.OUT, "vintage_report.txt"))


if __name__ == "__main__":
    main()
