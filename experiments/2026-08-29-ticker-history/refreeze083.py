"""32 個代號辨明之後再重凍一次(KARST-083 第三步)。

做法與 KARST-082 的 ``refreeze.py`` 一模一樣,分別只在三處:讀 083 的錨改變清單、
落 083 的兩份副產、註記寫明這是第三代。**基準快照仍然是最原始那個
``2026-08-28-493fd1df1cb9``**——每一代都由同一批日線重放,兩代之間的分別才只有一樣:
那份對照表。由第二代再重放會令「對照表改了什麼」與「上一代剔走了什麼」混在一起。

**不重抓行情**(理由見 082 的 refreeze.py:重抓會因免費源的除權除息調整令整條歷史
再飄一次)。只取 ``bar_status = actual`` 那批真實成交的日線,經 csv 來源適配器行同一
條管線;填補與留白由管線重新生成。

跑法(倉根)::

    python experiments/2026-08-29-ticker-history/refreeze083.py <scratchpad 路徑>

三代快照全部保留,編號並列於本目錄的 README.md。
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from karst.data.freeze import alias_candidates  # noqa: E402
from karst.data.snapshots import read_price_frame, read_universe  # noqa: E402
from karst.data.ticker_history import (  # noqa: E402
    anchors_for_range,
    distinct_ciks,
    read_anchor_table,
    resolve_alias_collisions,
    write_anchor_table,
)
from karst.errors import NotFound  # noqa: E402
from karst.gateway import Gateway  # noqa: E402
from karst.gateway.cli import main as gateway_main  # noqa: E402

BASE_SNAPSHOT = "2026-08-28-493fd1df1cb9"
PRIOR_SNAPSHOT = "2026-08-28-c442236133d4"
WINDOW_START = "2015-01-02"
WINDOW_END = "2026-08-28"
TAKEN_ON = "2026-08-28"

STORE_PATH = REPO_ROOT / "karst.sqlite"
ANCHOR_TABLE = REPO_ROOT / "karst" / "data" / "universes" / "sp500_ticker_anchors.csv"
OUT_DIR = Path(__file__).resolve().parent
CHANGED_FILE = OUT_DIR / "anchor-changes-083.csv"
DROPPED_FILE = OUT_DIR / "dropped-tickers-083.csv"
SNAPSHOT_ANCHORS = OUT_DIR / "snapshot-anchors-083.csv"


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
    print(f"基準快照 {BASE_SNAPSHOT}:{len(prices)} 列,其中真實成交 {len(actual)} 列")

    frame = actual.copy()
    frame["ticker"] = [by_entity[int(eid)] for eid in frame["entity_id"]]
    ranges = frame.groupby("ticker")["date"].agg(["min", "max"])

    # ---- 逐個代號按**行情實際落在哪一段**挑錨,挑不到的剔走(規則與 082 相同) ----
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
        spans = "、".join(
            f"{a.valid_from}~{a.valid_to or '仍在名單上'}"
            for a in anchors_for_range(anchors, ticker=ticker, start="0000-00-00", end="9999-99-99")
        )
        old_anchor = str(universe.loc[universe["ticker"] == ticker, "anchor"].iloc[0])
        if not hit:
            dropped.append(
                {
                    "ticker": ticker,
                    "bars": f"{first}~{last}",
                    "membership": spans,
                    "old_anchor": old_anchor,
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
                    "old_anchor": old_anchor,
                    "reason": (
                        f"日線期間內代號易主(錨到 {'、'.join(ciks)});"
                        "一個快照的價格表以代號為鍵,容不下兩家公司的價格,故此剔走"
                    ),
                }
            )
            continue
        unknown = [a for a in hit if not a.cik]
        picked = unknown[0] if unknown else next(a for a in hit if a.cik)
        if unknown and len(hit) > 1:
            print(
                f"  {ticker}:日線 {first}~{last} 跨越 {len(hit)} 段成分期,"
                f"其中 {len(unknown)} 段認不出持有人,改用佔位錨"
            )
        keep.append(picked)
        kept_tickers.append(ticker)

    # ---- 兩個代號錨到同一個實體:同一家公司的新舊代號各記一次,只可以留一個 ----
    #
    # 規則**不住在這裡**(KARST-084),備料亦**不住在這裡**(KARST-096)。規則住
    # `karst.data.ticker_history.resolve_alias_collisions`,備料住凍結模組的
    # `karst.data.freeze.alias_candidates`;凍結管線與這個腳本同呼叫那兩份,不留第二份。
    # 本腳本在這一格剩下的只有一件:把裁決結果落成 083 那兩份副產檔。
    verdicts = resolve_alias_collisions(
        alias_candidates(
            [(anchor.ticker, anchor.cik, anchor.valid_to) for anchor in keep], bars=frame
        )
    )
    by_ticker = {anchor.ticker: anchor for anchor in keep}
    aliased = []
    for verdict in verdicts:
        for ticker in verdict.dropped:
            anchor = by_ticker[ticker]
            aliased.append(
                {
                    "ticker": ticker,
                    "bars": f"{ranges.loc[ticker, 'min']}~{ranges.loc[ticker, 'max']}",
                    "membership": f"{anchor.valid_from}~{anchor.valid_to or '仍在名單上'}",
                    "old_anchor": str(
                        universe.loc[universe["ticker"] == ticker, "anchor"].iloc[0]
                    ),
                    "reason": verdict.reason,
                }
            )
    losers = {row["ticker"] for row in aliased}
    if losers:
        keep = [a for a in keep if a.ticker not in losers]
        kept_tickers = [t for t in kept_tickers if t not in losers]
        dropped.extend(aliased)
        print(f"同實體別名剔走 {len(losers)} 個代號:{sorted(losers)}")

    with DROPPED_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["ticker", "bars", "membership", "old_anchor", "reason"]
        )
        writer.writeheader()
        writer.writerows(dropped)
    print(f"入新快照 {len(kept_tickers)} 個代號;剔走 {len(dropped)} 個")

    write_anchor_table(SNAPSHOT_ANCHORS, keep)

    frame = frame.loc[frame["ticker"].isin(set(kept_tickers))]
    bars_file = scratch / "sp500_bars_replay_083.csv"
    frame = frame.loc[:, ["date", "ticker", "open", "high", "low", "close", "volume"]]
    frame.to_csv(bars_file, index=False, encoding="utf-8")
    print(f"重放日線 {len(frame)} 列 → {bars_file}")

    # 撤回錨改變了的代號映射,好讓管線按新對照重新登記。舊實體不刪,舊快照照樣讀得到。
    changed = changed_tickers()
    for ticker in sorted({row["ticker"] for row in changed}):
        for period in store.ticker_history(ticker):
            try:
                store.retract_ticker(
                    ticker, entity_id=period.entity_id, valid_from=period.valid_from
                )
            except NotFound as error:
                print(f"  {ticker} 撤回略過:{error}")
        print(f"  已撤回 {ticker} 的舊映射")

    manifest = json.loads(
        (REPO_ROOT / "data" / "snapshots" / PRIOR_SNAPSHOT / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    tickers = sorted(kept_tickers)
    notes = [
        f"本快照是第三代(KARST-083):由 {BASE_SNAPSHOT} 重放同一批日線、同一段窗口,"
        f"唯一分別是代號→實體的對照表比第二代 {PRIOR_SNAPSHOT} 多辨明了 32 個代號。"
        "三代編號並列於 experiments/2026-08-29-ticker-history/README.md,舊快照一個不刪",
        "第二代留低 32 段成分期判詞為人手待辨或佔位錨(SEC 兩份公開檔都沒有代號一欄,"
        "單憑代號認不出當時屬誰)。本代逐段以三源交叉核對辨明:SEC 申報名稱窗口、"
        "SEC 名稱→CIK 表、維基百科標普 500 成分變動表(唯一把代號連到公司名的來源);"
        "每一段的證據逐條寫在 karst/data/universes/sp500_ticker_anchors.csv 的 evidence 欄,"
        "以及 experiments/2026-08-29-ticker-history/manual-review-resolved.csv",
        "自動裁決規則一字不改;人手裁決過的列另落判詞「人手辨明」。"
        "本次 32 段全部辨明,無一落「未能辨明」",
        f"錨改變 {len(changed)} 列;逐列由誰改到誰見 "
        "experiments/2026-08-29-ticker-history/anchor-changes-083.csv",
        "日線來自重放而非重抓:重抓會因免費源的除權除息調整令整條歷史再飄一次,"
        "那樣就分不清快照變了是因為改錨還是因為數據飄了。重放只取基準快照 "
        "bar_status = actual 那批,填補與留白由管線重新生成",
        f"本快照比基準快照 {BASE_SNAPSHOT} 少了 {len(dropped)} 個代號:它們抓回來的日線整段落在"
        "成分期之外(免費行情源給的是代號**今日持有人**的歷史),或者日線期間內代號易主。"
        "逐條見 experiments/2026-08-29-ticker-history/dropped-tickers-083.csv",
    ]
    for row in changed:
        notes.append(
            f"改錨·{row['ticker']}(生效期 {row['membership']}):"
            f"{row['from_anchor']} → {row['to_anchor']};{row['evidence']}"
        )
    for row in dropped:
        notes.append(
            f"剔走·{row['ticker']}(成分期 {row['membership']};日線 {row['bars']};"
            f"原錨 {row['old_anchor']}):{row['reason']}"
        )
    # 上一代那批註記(退市代號缺口、同錨拆走等)原文帶過來,免得重凍之後缺口說明失傳。
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
        str(SNAPSHOT_ANCHORS),
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
