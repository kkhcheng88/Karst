"""逐個代號抓日線,可中斷續抓(KARST-065 第三步的前半)。

抓的是「標普 500 歷史成分」名單上、成分期與窗口有重疊的全部代號,連主日曆錨
SPY 一隻。**一個代號一次抓取**,不合批:合批的話一個退市代號會拖冧整批,
而分辨「哪一個抓不到」正是本票要交的東西(D-026 第 6 條的缺口標示)。

抓取一律經現有的來源適配器 ``YFinanceSource``(D-026 第 7 條),本檔不另寫一套
抓取邏輯;它對空批次照樣拋 ``DataFetchFailed``,那一句就是「這個代號抓不到」。

落點全部在 scratchpad(暫存,不入倉):

    <scratchpad>/bars/<代號>.csv     一個代號一個檔(date、ticker、開高低收量)
    <scratchpad>/fetch_progress.json  進度:每個代號的狀態、列數、頭尾日、試了幾次

跑法(倉根)::

    python experiments/2026-08-29-sp500-universe/fetch_bars.py <scratchpad 路徑>

中斷了再跑同一句即可:已經有結果的代號直接跳過,只補未抓的那批。
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from karst.data.errors import DataFetchFailed  # noqa: E402
from karst.data.sources import BAR_COLUMNS, YFinanceSource  # noqa: E402
from karst.data.universe import members_in_window, universe_listing  # noqa: E402

WINDOW_START = "2015-01-02"
WINDOW_END = "2026-08-28"
CALENDAR_TICKER = "SPY"

# 禮貌限速:每抓一個代號歇一歇,失敗重試之間再歇長一點。
PAUSE_SECONDS = 0.4
RETRY_PAUSE_SECONDS = 2.0
RETRY_ROUNDS = 2


def scratch_dir() -> Path:
    if len(sys.argv) < 2:
        raise SystemExit("要給 scratchpad 路徑做第一個參數")
    path = Path(sys.argv[1])
    path.mkdir(parents=True, exist_ok=True)
    return path


def wanted_tickers() -> list[str]:
    listing = universe_listing("sp500-historical")
    members = members_in_window(listing, start=WINDOW_START, end=WINDOW_END)
    tickers = sorted({member.ticker for member in members} | {CALENDAR_TICKER})
    return tickers


def load_progress(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_progress(path: Path, progress: dict[str, dict]) -> None:
    staging = path.with_suffix(".tmp")
    staging.write_text(
        json.dumps(progress, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"
    )
    staging.replace(path)


def fetch_one(source: YFinanceSource, ticker: str, bars_dir: Path) -> dict:
    """抓一個代號。抓得到就落檔並回成績單,抓不到回 ``status="empty"`` 連來源那句話。"""
    try:
        frame = source.fetch_daily_bars([ticker], WINDOW_START, WINDOW_END)
    except DataFetchFailed as error:
        return {"status": "empty", "rows": 0, "reason": str(error)[:200]}
    frame = frame.loc[:, list(BAR_COLUMNS)]
    out = bars_dir / f"{ticker}.csv"
    frame.to_csv(out, index=False, encoding="utf-8")
    return {
        "status": "ok",
        "rows": int(len(frame)),
        "first": str(frame["date"].min()),
        "last": str(frame["date"].max()),
    }


def main() -> int:
    scratch = scratch_dir()
    bars_dir = scratch / "bars"
    bars_dir.mkdir(parents=True, exist_ok=True)
    progress_path = scratch / "fetch_progress.json"
    progress = load_progress(progress_path)

    tickers = wanted_tickers()
    source = YFinanceSource()
    todo = [ticker for ticker in tickers if ticker not in progress]
    print(f"名單 {len(tickers)} 個代號;已有結果 {len(progress)} 個,今次要抓 {len(todo)} 個")

    for index, ticker in enumerate(todo, start=1):
        record = fetch_one(source, ticker, bars_dir)
        record["attempts"] = 1
        progress[ticker] = record
        save_progress(progress_path, progress)
        if index % 25 == 0 or record["status"] == "empty":
            print(f"  [{index}/{len(todo)}] {ticker} {record['status']} {record.get('rows', 0)}")
        time.sleep(PAUSE_SECONDS)

    # 重試:抓不到的再試幾轉。退市代號永遠試不出來,但**網絡一下子不通**與
    # 「這個代號真的沒有數」分得開,靠的就是這幾轉。
    for round_no in range(1, RETRY_ROUNDS + 1):
        failed = [ticker for ticker, record in progress.items() if record["status"] != "ok"]
        if not failed:
            break
        print(f"第 {round_no} 轉重試:{len(failed)} 個代號")
        for ticker in failed:
            record = fetch_one(source, ticker, bars_dir)
            record["attempts"] = progress[ticker].get("attempts", 1) + 1
            progress[ticker] = record
            save_progress(progress_path, progress)
            time.sleep(RETRY_PAUSE_SECONDS if record["status"] != "ok" else PAUSE_SECONDS)

    ok = [t for t, r in progress.items() if r["status"] == "ok"]
    empty = [t for t, r in progress.items() if r["status"] != "ok"]
    print(f"完成:抓到 {len(ok)} 個、抓不到 {len(empty)} 個(共 {len(progress)} 個)")
    summary = scratch / "fetch_summary.csv"
    with summary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ticker", "status", "rows", "first", "last", "attempts", "reason"])
        for ticker in sorted(progress):
            record = progress[ticker]
            writer.writerow(
                [
                    ticker,
                    record["status"],
                    record.get("rows", 0),
                    record.get("first", ""),
                    record.get("last", ""),
                    record.get("attempts", 1),
                    record.get("reason", ""),
                ]
            )
    print(f"逐個代號的結果落 {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
