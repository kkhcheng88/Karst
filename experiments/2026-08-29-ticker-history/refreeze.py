"""錨改變之後重凍標普 500 歷史成分快照(KARST-082 第四步)。

**不重抓行情。** 舊快照 ``2026-08-28-493fd1df1cb9`` 已經凍住同一段窗口的日線,重抓
只會因為免費源的除權除息調整而得出另一批數字,那樣就分不清「快照變了」是因為改錨
還是因為數據本身飄了。故此改由舊快照**重放**:只取 ``bar_status = actual`` 那批真實
成交的日線(``filled`` 與 ``missing`` 是對齊那一步生出來的,由管線重新生成),
經 csv 來源適配器行同一條管線,唯一的分別就是那份帶生效期的代號對照。

跑法(倉根)::

    python experiments/2026-08-29-ticker-history/refreeze.py <scratchpad 路徑>

舊快照不刪。新舊編號並列寫入 README。
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from karst.data.snapshots import read_price_frame, read_universe  # noqa: E402
from karst.data.ticker_history import (  # noqa: E402
    anchors_for_range,
    distinct_ciks,
    read_anchor_table,
    write_anchor_table,
)
from karst.errors import NotFound  # noqa: E402
from karst.gateway import Gateway  # noqa: E402
from karst.gateway.cli import main as gateway_main  # noqa: E402

BASE_SNAPSHOT = "2026-08-28-493fd1df1cb9"
WINDOW_START = "2015-01-02"
WINDOW_END = "2026-08-28"
TAKEN_ON = "2026-08-28"

STORE_PATH = REPO_ROOT / "karst.sqlite"
ANCHOR_TABLE = REPO_ROOT / "karst" / "data" / "universes" / "sp500_ticker_anchors.csv"
CHANGED_FILE = Path(__file__).resolve().parent / "anchor-changes.csv"


def changed_tickers() -> list[dict[str, str]]:
    with CHANGED_FILE.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("要給 scratchpad 路徑做第一個參數")
    scratch = Path(sys.argv[1])
    scratch.mkdir(parents=True, exist_ok=True)

    # 庫身一律由唯一入口開出來(KARST-087):快照登記要有那道門的簽章手才寫得入,
    # 而這支腳本本身亦要撤回代號映射,同一條連線做完再放手,不留第二條在同一個庫檔上。
    gateway = Gateway.open(str(STORE_PATH))
    store = gateway.store
    universe = read_universe(store, BASE_SNAPSHOT)
    prices = read_price_frame(store, BASE_SNAPSHOT)
    by_entity = dict(zip(universe["entity_id"], universe["ticker"], strict=True))

    actual = prices.loc[prices["bar_status"] == "actual"]
    print(f"舊快照 {BASE_SNAPSHOT}:{len(prices)} 列,其中真實成交 {len(actual)} 列")

    frame = actual.copy()
    frame["ticker"] = [by_entity[int(eid)] for eid in frame["entity_id"]]
    ranges = frame.groupby("ticker")["date"].agg(["min", "max"])

    # ---- 逐個代號按**行情實際落在哪一段**挑錨,挑不到的剔走 ----
    anchors = read_anchor_table(ANCHOR_TABLE)
    kinds = dict(zip(universe["ticker"], universe["entity_kind"], strict=True))
    keep: list = []
    kept_tickers: list[str] = []
    dropped: list[dict[str, str]] = []
    for ticker in sorted(universe["ticker"]):
        first, last = str(ranges.loc[ticker, "min"]), str(ranges.loc[ticker, "max"])
        if kinds[ticker] != "company":
            kept_tickers.append(ticker)  # ETF 另編內部代碼,不經 CIK 錨
            continue
        hit = anchors_for_range(anchors, ticker=ticker, start=first, end=last)
        spans = "、".join(f"{a.valid_from}~{a.valid_to or '仍在名單上'}" for a in anchors_for_range(
            anchors, ticker=ticker, start="0000-00-00", end="9999-99-99"
        ))
        if not hit:
            dropped.append(
                {
                    "ticker": ticker,
                    "bars": f"{first}~{last}",
                    "membership": spans,
                    "old_anchor": str(universe.loc[universe["ticker"] == ticker, "anchor"].iloc[0]),
                    "reason": (
                        "抓回來的日線整段落在成分期之外——免費行情源給的是**代號今日持有人**"
                        "的歷史,不是當年那隻成分股的價格。留住它等於把另一家公司的走勢"
                        "當成成分股回測,故此剔走(D-026 第 6 條:留白比造一個看似完整的名單安全)"
                    ),
                }
            )
            continue
        ciks = distinct_ciks(hit)
        if len(ciks) > 1:
            dropped.append(
                {
                    "ticker": ticker,
                    "bars": f"{first}~{last}",
                    "membership": spans,
                    "old_anchor": str(universe.loc[universe["ticker"] == ticker, "anchor"].iloc[0]),
                    "reason": (
                        f"日線期間內代號易主(錨到 {'、'.join(ciks)});"
                        "一個快照的價格表以代號為鍵,容不下兩家公司的價格,故此剔走"
                    ),
                }
            )
            continue
        # 挑哪一行:日線期間只碰到一個真 CIK,但若同時碰到一段**認不出持有人**的成分期
        # (判詞是人手待辨或佔位錨),那批價格就跨了一段來歷不明的日子。這種情況一律
        # 用佔位錨——「其中一段不知道是誰」是真話,把整條序列都算到那個查得出的 CIK
        # 頭上不是。DXC 就是這一格:2017 年前那截是前身公司的歷史。
        unknown = [a for a in hit if not a.cik]
        picked = unknown[0] if unknown else next(a for a in hit if a.cik)
        if unknown and len(hit) > 1:
            print(
                f"  {ticker}:日線 {first}~{last} 跨越 {len(hit)} 段成分期,"
                f"其中 {len(unknown)} 段認不出持有人,改用佔位錨"
            )
        keep.append(picked)
        kept_tickers.append(ticker)

    with (Path(__file__).resolve().parent / "dropped-tickers.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["ticker", "bars", "membership", "old_anchor", "reason"]
        )
        writer.writeheader()
        writer.writerows(dropped)
    print(f"入新快照 {len(kept_tickers)} 個代號;剔走 {len(dropped)} 個")

    snapshot_anchors = Path(__file__).resolve().parent / "snapshot-anchors.csv"
    write_anchor_table(snapshot_anchors, keep)

    frame = frame.loc[frame["ticker"].isin(set(kept_tickers))]
    bars_file = scratch / "sp500_bars_replay.csv"
    frame = frame.loc[:, ["date", "ticker", "open", "high", "low", "close", "volume"]]
    frame.to_csv(bars_file, index=False, encoding="utf-8")
    print(f"重放日線 {len(frame)} 列 → {bars_file}")

    # 撤回錨錯了的代號映射,好讓管線按新對照重新登記。舊實體不刪,舊快照照樣讀得到。
    changed = changed_tickers()
    for row in changed:
        ticker = row["ticker"]
        for period in store.ticker_history(ticker):
            try:
                store.retract_ticker(
                    ticker, entity_id=period.entity_id, valid_from=period.valid_from
                )
            except NotFound as error:
                print(f"  {ticker} 撤回略過:{error}")
        print(f"  已撤回 {ticker} 的舊映射({row['from_anchor']} → {row['to_anchor']})")

    manifest = json.loads(
        (REPO_ROOT / "data" / "snapshots" / BASE_SNAPSHOT / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    tickers = sorted(kept_tickers)
    notes = [
        f"本快照由 {BASE_SNAPSHOT} 重凍(KARST-082):同一批日線、同一段窗口,"
        "唯一分別是代號→實體的錨改用帶生效期的對照表 "
        "karst/data/universes/sp500_ticker_anchors.csv;舊快照不刪,兩個編號並列於 "
        "experiments/2026-08-29-ticker-history/README.md",
        "改錨的由來:假設 A-011 崩塌——SEC company_tickers.json 只講代號**今日**屬誰,"
        "用它錨歷史成分會把已回收的代號掛到今日的另一家公司。新對照以 SEC "
        "cik-lookup-data.txt(保留歷史名)加逐個 CIK 的申報名稱窗口裁決,判不到的列成"
        "人手待辨清單,不猜",
        f"錨改變 {len(changed)} 個代號;逐個由誰改到誰見 "
        "experiments/2026-08-29-ticker-history/anchor-changes.csv",
        "日線來自重放而非重抓:重抓會因免費源的除權除息調整令整條歷史再飄一次,"
        "那樣就分不清快照變了是因為改錨還是因為數據飄了。重放只取原快照 "
        "bar_status = actual 那批,填補與留白由管線重新生成",
    ]
    notes.append(
        f"本快照比 {BASE_SNAPSHOT} 少了 {len(dropped)} 個代號:它們抓回來的日線整段落在"
        "成分期之外(免費行情源給的是代號**今日持有人**的歷史),或者日線期間內代號易主。"
        "留住它們等於把另一家公司的走勢當成成分股回測——這正是假設 A-011 崩塌所指的那件事。"
        "逐條見 experiments/2026-08-29-ticker-history/dropped-tickers.csv"
    )
    for row in changed:
        notes.append(
            f"改錨·{row['ticker']}(成分期 {row['membership']}):"
            f"{row['from_anchor']} → {row['to_anchor']};{row['evidence']}"
        )
    for row in dropped:
        notes.append(
            f"剔走·{row['ticker']}(成分期 {row['membership']};日線 {row['bars']};"
            f"原錨 {row['old_anchor']}):{row['reason']}"
        )
    # 舊快照那批註記(退市代號缺口、同錨拆走等)原文帶過來,免得重凍之後缺口說明失傳。
    notes.extend(str(note) for note in manifest.get("notes", ()))

    argv = [
        "--store",
        str(STORE_PATH),
        "data",
        "snapshot",
        "--start",
        WINDOW_START,
        "--end",
        WINDOW_END,
        "--taken-on",
        TAKEN_ON,
        "--source",
        "csv",
        "--bars",
        str(bars_file),
        "--anchors",
        str(snapshot_anchors),
    ]
    for ticker in tickers:
        argv += ["--ticker", ticker]
    for note in notes:
        argv += ["--note", note]

    # 重凍那一句自己會開唯一入口,所以先放手:同一個庫檔上不留兩條連線。
    gateway.close()
    print("經唯一入口重凍中(karst data snapshot --source csv --anchors …)")
    return gateway_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
