"""把抓回來的日線凍成快照,缺口逐條寫入快照說明檔(KARST-065 第三步的後半)。

四件事,次序寫死:

  1. **點算缺口** —— 讀 ``fetch_bars.py`` 的進度檔,分開「抓到」與「抓不到」兩批,
     抓不到那批逐個配回它的成分期(加入/剔除日期)。
  2. **拆走同錨代號** —— 上市公司以 SEC CIK 為錨(D-026 第 2 條),同一家公司的
     A/C 兩類股(GOOG 與 GOOGL 一類)共用一個 CIK,一齊入表會解析成同一個實體編號,
     對齊那一步會**靜靜**丟掉其中一條。故此凍結之前先按 CIK 分組,一個 CIK 只留一個
     代號,被拆走的一樣當缺口逐條講明。
  3. **合成一份日線檔** —— 全部留低的代號合成一個 CSV,由 ``csv`` 來源適配器重放,
     經唯一入口凍結(D-026 第 7 條:別的來源交得出同一套欄位就走同一條管線)。
  4. **凍結** —— 呼叫唯一入口的 ``data snapshot``,每一條缺口用一句 ``--note`` 帶進
     快照說明檔;快照編號、缺口數與比例印出來。

跑法(倉根)::

    python experiments/2026-08-29-sp500-universe/freeze.py <scratchpad 路徑>

不補假數據:抓不到就是抓不到,說明檔上見得到,價格表上不會多出一格。
"""

from __future__ import annotations

import csv
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from karst.data.cik import fetch_cik_map, placeholder_cik  # noqa: E402
from karst.data.errors import DataFetchFailed  # noqa: E402
from karst.data.universe import (  # noqa: E402
    SP500_MEMBERSHIP,
    members_in_window,
    universe_listing,
)
from karst.gateway.cli import main as gateway_main  # noqa: E402

WINDOW_START = "2015-01-02"
WINDOW_END = "2026-08-28"
CALENDAR_TICKER = "SPY"
STORE_PATH = REPO_ROOT / "karst.sqlite"

GAP_FILE = Path(__file__).resolve().parent / "缺口.csv"


def periods_of(ticker: str) -> str:
    """一個代號的成分期,寫成一句(可能不止一段)。"""
    spans = [
        f"{period.joined_on}~{period.left_on or '仍在名單上'}"
        for period in SP500_MEMBERSHIP
        if period.ticker == ticker
    ]
    return "、".join(spans) if spans else "(名單上查無成分期)"


def registered_tickers() -> set[str]:
    """單一定義庫內已登記的代號。同錨相撞時,已登記那個優先留低——
    它已經有實體編號與生效期,換成另一個代號等於把舊快照的血統打亂。"""
    if not STORE_PATH.exists():
        return set()
    connection = sqlite3.connect(STORE_PATH)
    try:
        return {row[0] for row in connection.execute("SELECT ticker FROM entity_ticker")}
    finally:
        connection.close()


def load_progress(scratch: Path) -> dict[str, dict]:
    path = scratch / "fetch_progress.json"
    if not path.exists():
        raise SystemExit(f"未見進度檔 {path};請先跑 fetch_bars.py")
    return json.loads(path.read_text(encoding="utf-8"))


def membership_days(ticker: str) -> int:
    """一個代號在名單上待過多少日(幾段成分期加埋);仍在名單上的算到窗口尾。"""
    total = 0
    for period in SP500_MEMBERSHIP:
        if period.ticker != ticker:
            continue
        joined = date.fromisoformat(period.joined_on)
        left = date.fromisoformat(period.left_on or WINDOW_END)
        total += max((left - joined).days, 0)
    return total


def choose_by_cik(
    tickers: list[str], rows: dict[str, int], cik_map: dict[str, str]
) -> tuple[list[str], list[tuple[str, str, str]]]:
    """按 SEC CIK 分組,一個錨只留一個代號。

    回傳(留低的代號, 拆走的[(代號, 留低那個, 那個 CIK)])。抓不到真 CIK 的用佔位錨,
    佔位錨逐個代號各不相同,故不會被誤拆。

    誰留低,三級排序:(1) 單一定義庫**已經登記**那個優先——它已有實體編號與生效期,
    換走等於把舊快照的血統打亂;(2) 抓到的日線多那個;(3) 在名單上待得耐那個。
    三級都相同才輪到代號字母,免得結果靠運氣。
    """
    already = registered_tickers()
    by_anchor: dict[str, list[str]] = defaultdict(list)
    for ticker in tickers:
        by_anchor[cik_map.get(ticker) or placeholder_cik(ticker)].append(ticker)

    kept: list[str] = []
    dropped: list[tuple[str, str, str]] = []
    for anchor, group in by_anchor.items():
        if len(group) == 1:
            kept.append(group[0])
            continue
        winner = sorted(
            group,
            key=lambda t: (t not in already, -rows.get(t, 0), -membership_days(t), t),
        )[0]
        kept.append(winner)
        dropped.extend((ticker, winner, anchor) for ticker in group if ticker != winner)
    return sorted(kept), sorted(dropped)


def assemble_bars(tickers: list[str], scratch: Path) -> Path:
    """把逐個代號的日線檔合成一份,交給 csv 來源適配器重放。"""
    out = scratch / "sp500_bars.csv"
    bars_dir = scratch / "bars"
    written = 0
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "ticker", "open", "high", "low", "close", "volume"])
        for ticker in tickers:
            path = bars_dir / f"{ticker}.csv"
            with path.open(encoding="utf-8", newline="") as source:
                reader = csv.reader(source)
                next(reader)
                for row in reader:
                    writer.writerow(row)
                    written += 1
    print(f"合成日線 {written} 列 → {out}")
    return out


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("要給 scratchpad 路徑做第一個參數")
    scratch = Path(sys.argv[1])
    progress = load_progress(scratch)

    listing = universe_listing("sp500-historical")
    wanted = sorted(
        {member.ticker for member in members_in_window(listing, start=WINDOW_START, end=WINDOW_END)}
        | {CALENDAR_TICKER}
    )
    missing_run = [ticker for ticker in wanted if ticker not in progress]
    if missing_run:
        raise SystemExit(f"還有 {len(missing_run)} 個代號未抓過(例:{missing_run[:5]}),請先跑完 fetch_bars.py")

    fetched = [t for t in wanted if progress[t]["status"] == "ok"]
    unfetched = [t for t in wanted if progress[t]["status"] != "ok"]
    rows = {t: int(progress[t].get("rows", 0)) for t in fetched}

    try:
        cik_map = fetch_cik_map()
    except DataFetchFailed as error:
        raise SystemExit(f"抓不到 SEC 代號→CIK 對照,無法先行拆同錨代號:{error}") from error

    kept, dropped = choose_by_cik(fetched, rows, cik_map)
    if CALENDAR_TICKER not in kept:
        raise SystemExit(f"主日曆錨 {CALENDAR_TICKER} 不在留低的名單內,凍結會拒收")

    total = len(wanted)
    gap_count = len(unfetched) + len(dropped)
    print(f"名單內代號 {total} 個:抓到 {len(fetched)}、抓不到 {len(unfetched)}、同錨拆走 {len(dropped)}")
    print(f"入快照 {len(kept)} 個;缺口 {gap_count} 個,佔 {gap_count / total:.1%}")

    with GAP_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ticker", "kind", "membership", "detail"])
        for ticker in unfetched:
            writer.writerow(
                [ticker, "抓不到", periods_of(ticker), progress[ticker].get("reason", "")]
            )
        for ticker, winner, anchor in dropped:
            writer.writerow([ticker, "同錨拆走", periods_of(ticker), f"與 {winner} 同錨 {anchor}"])
    print(f"逐條缺口落 {GAP_FILE}")

    bars = assemble_bars(kept, scratch)

    notes: list[str] = [
        f"宇宙名單是「標普 500 歷史成分」(宇宙名單登記 sp500-historical),含已退市與已剔除代號;"
        f"窗口 {WINDOW_START}~{WINDOW_END} 內曾入選的代號共 {total} 個",
        f"缺口總計 {gap_count} 個代號,佔曾入選 {total} 個的 {gap_count / total:.1%}"
        f"(抓不到 {len(unfetched)} 個、同一個 SEC 錨拆走 {len(dropped)} 個);"
        "一律留白,不補假數據(D-026 第 6 條)",
        "本快照與說明檔第七節那句通用話不同:它的宇宙名單**不是**抓取當日仍在市的名單,"
        "而是歷史成分名單;缺的是那批抓不到日線的退市代號,逐條列於下",
        "血統:日線由 yfinance 逐個代號抓(來源適配器 YFinanceSource,2026-08-29),"
        "合成一份 CSV 之後經 csv 適配器重放入同一條管線;manifest 的 source 欄記的是重放"
        "那一步(csv),原始行情來源是 yfinance",
        f"窗口為什麼由 {WINDOW_START} 起,不由 2014 年起:SPY 這個主日曆錨的代號生效起已經"
        "釘死在 2015-01-02(管線合約「代號生效起不可回頭改」),要往前推就要先重建代號映射,"
        "不在本快照範圍",
    ]
    for ticker in unfetched:
        notes.append(f"缺口·抓不到 {ticker}(成分期 {periods_of(ticker)}):免費行情源回空批次,多數是已退市代號")
    for ticker, winner, anchor in dropped:
        notes.append(
            f"缺口·同錨拆走 {ticker}(成分期 {periods_of(ticker)}):與 {winner} 同一個 SEC 錨 {anchor}"
            "(同一家公司的另一類股),一齊入表會撞同一個實體編號,本快照只收前者"
        )

    argv = [
        "--store",
        str(STORE_PATH),
        "data",
        "snapshot",
        "--start",
        WINDOW_START,
        "--end",
        WINDOW_END,
        "--source",
        "csv",
        "--bars",
        str(bars),
    ]
    for ticker in kept:
        argv += ["--ticker", ticker]
    for note in notes:
        argv += ["--note", note]

    print("經唯一入口凍結中(karst data snapshot --source csv …)")
    return gateway_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
