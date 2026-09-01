# -*- coding: utf-8 -*-
"""KARST-146 step 7: actually test the free price sources on delisted names.

The report must not merely assert "free sources have no delisted prices" - it
has to have tried. This probes a sample of the delisted companies that DO have
accounts in the panel against every free price source available here, and
records what each one returned.

Run:  PYTHONUTF8=1 python probe_free_price_sources.py
"""
from __future__ import annotations

import io
import json
import pathlib

import pandas as pd

from sec_client import get

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"

SAMPLE_N = 12


def try_yfinance(t: str) -> tuple[bool, str]:
    try:
        import yfinance as yf
    except ImportError:
        return False, "yfinance 未安裝"
    try:
        df = yf.Ticker(t).history(period="max", auto_adjust=False)
        if df is None or df.empty:
            return False, "回傳空表"
        return True, f"{len(df)} 個交易日,{df.index.min():%Y-%m-%d}~{df.index.max():%Y-%m-%d}"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {str(exc)[:80]}"


def try_stooq(t: str) -> tuple[bool, str]:
    raw, err = get(f"https://stooq.com/q/d/l/?s={t.lower()}.us&i=d")
    if raw is None:
        return False, err
    txt = raw.decode("utf-8", "replace")
    if "No data" in txt or len(txt.strip().splitlines()) < 3:
        return False, "回傳 No data / 空檔"
    try:
        df = pd.read_csv(io.StringIO(txt))
    except Exception as exc:  # noqa: BLE001
        return False, f"無法解析回應({type(exc).__name__})"
    if "Date" not in df.columns or df.empty:
        return False, f"回應不是行情表:{txt.strip()[:60]}"
    return True, f"{len(df)} 行,{df.Date.min()}~{df.Date.max()}"


def main() -> None:
    gap = pd.read_csv(OUT / "accounts_but_no_price.csv", dtype=str).fillna("")
    delisted = gap[gap.left_on != ""].sort_values("left_on", ascending=False)
    sample = delisted.head(SAMPLE_N)
    print(f"{len(delisted)} delisted names have accounts but no local price; "
          f"probing {len(sample)}\n")

    rows = []
    for _, r in sample.iterrows():
        y_ok, y_msg = try_yfinance(r.ticker)
        s_ok, s_msg = try_stooq(r.ticker)
        rows.append(dict(ticker=r.ticker, left_on=r.left_on,
                         yfinance_ok=y_ok, yfinance=y_msg,
                         stooq_ok=s_ok, stooq=s_msg))
        print(f"{r.ticker:6s} left {r.left_on}  yf={y_ok!s:5s} {y_msg[:44]:44s} "
              f"stooq={s_ok!s:5s} {s_msg[:40]}")

    # Control: a still-listed name. If a source cannot even serve AAPL from
    # this machine, then "no data for the delisted name" proves nothing about
    # that source - it only proves the source refused us.
    ctl = {}
    for name, fn in (("yfinance", try_yfinance), ("stooq", try_stooq)):
        ok, msg = fn("AAPL")
        ctl[name] = dict(live_ticker_works=ok, detail=msg)
        print(f"\n對照組 AAPL / {name}: {ok} {msg[:70]}")

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "free_price_source_probe.csv", index=False, encoding="utf-8")
    summary = dict(
        probed=len(df),
        yfinance_returned_data=int(df.yfinance_ok.sum()),
        stooq_returned_data=int(df.stooq_ok.sum()),
        control_live_ticker=ctl,
        note="回傳有數不等於「是當年那家公司的價格」——代號被後人接用時,"
             "拿到的是接用者的走勢(KARST-083 的 ADT 案例)。逐個核對留給價格線的票。"
             "對照組不通過的來源,只證明它不肯服務這部機,不證明它沒有除牌資料。",
    )
    (OUT / "free_price_source_probe.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n", summary)


if __name__ == "__main__":
    main()
