"""用現役兩個快照的原輸入重凍一次,把成果落檔(KARST-096 的對照腳本)。

本檔**不判對錯**,只負責「照原輸入再凍一次,把凍出來的東西完整寫下來」。判對錯是
``compare.py`` 的事。分家是刻意的:同一支腳本要在改動**之前**跑一次、改動**之後**
再跑一次,兩次的成果放在兩個目錄裡逐位比,腳本本身一個字都不准改——否則「改動前後
一樣」這句話就沒有意思了。

跑法(倉根)::

    python experiments/2026-08-30-freeze-module/replay.py --label before --out <目錄>
    python experiments/2026-08-30-freeze-module/replay.py --label after  --out <目錄>

**動的是複本,不是生產庫。** 每次跑都把 ``karst.sqlite`` 複製一份去輸出目錄,快照亦
寫進輸出目錄自己的快取根;生產庫與 ``data/`` 一個位元都不碰。

# 原輸入從哪裡來

價格線那份(現役 S&P500 快照)的原輸入是 KARST-083 的重凍:同一批日線重放、一份帶
生效期的代號對照、一批呼叫方註記。三樣全部由**已凍結的快照本身**加那次重凍留下的
副產檔還原得回:

  * 日線 —— 取已凍結的 ``prices.parquet`` 裡 ``bar_status = actual`` 那批(填補與留白
    是對齊那一步生出來的,由管線重新生成),經實體編號還原成代號,寫成 csv 餵回 csv
    來源適配器。這正是當日那條路。
  * 代號對照 —— ``experiments/2026-08-29-ticker-history/snapshot-anchors-083.csv``,
    當日那份原檔。
  * 呼叫方註記 —— 由已凍結的 manifest 的 ``notes`` 切出來。切在哪一刀不是猜的:
    管線自己會在尾巴補一批「取不到 SEC CIK,以佔位錨…」的註記,那一批由代號對照
    算得出來,算出來之後與 manifest 尾巴逐條核對,核得上才切(核不上即當場拋錯)。

宏觀線那份同一個做法:取已凍結的 ``series.parquet`` 裡 ``value_status = actual`` 那批
餵回靜態來源適配器,主日曆取已凍結的那條。

# 兩格不入內容雜湊的東西

``fetched_at``(抓取時間)是牆上的鐘,**刻意不入內容雜湊**(D-026 第 3 條:同一批
內容重抓要落回同一個編號)。所以重凍出來的說明檔那一行必然與原檔不同,本腳本照樣
原樣寫下來,由 ``compare.py`` 明文列為「唯一容許不同的一行」。

齊全度門檻同理:它決定「這樣算不算過關」,不決定數據長什麼樣,故不入雜湊
(KARST-061)。已凍結那份宏觀快照凍於門檻這件事出現之前,manifest 裡沒有這一格,
所以本腳本明給一套,兩次重凍用同一套——改動前後比得住。
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from karst.data.cik import placeholder_cik  # noqa: E402
from karst.gateway import Gateway  # noqa: E402
from karst.gateway.service import build_source, resolve_universe  # noqa: E402

# ---- 對照的兩個現役快照 ----
PRICE_SNAPSHOT = "2026-08-28-3bf7ab0a522a"
MACRO_SNAPSHOT = "2026-08-28-dc2d9f1a1778"
# 宏觀那份對齊的是這條主日曆(兩者的 calendar.parquet 逐日相同,已核)
MACRO_CALENDAR_FROM = "2026-08-28-a508d635a5fa"

ANCHOR_TABLE = (
    REPO_ROOT / "experiments" / "2026-08-29-ticker-history" / "snapshot-anchors-083.csv"
)
LIVE_STORE = REPO_ROOT / "karst.sqlite"
PRICE_ROOT = REPO_ROOT / "data" / "snapshots"
MACRO_ROOT = REPO_ROOT / "data" / "macro_snapshots"

# 齊全度門檻:不入內容雜湊,兩次重凍用同一套即可(理由見本檔開頭)
MAX_STALE_DAYS = 3
MAX_MISSING_RATIO = 0.05


def _read_manifest(directory: Path) -> dict[str, Any]:
    return json.loads((directory / "manifest.json").read_text(encoding="utf-8"))


def _split_caller_notes(
    frozen_notes: list[str], members: tuple[Any, ...], cik_map: dict[str, str]
) -> list[str]:
    """把已凍結的註記切成「呼叫方交來那批」與「管線自己補那批」,回傳前者。

    管線補的那批是 ``ensure_entities`` 為取不到 SEC CIK 的上市公司逐個補的佔位錨註記,
    次序就是名單的次序。這裡照同一條規則算一次,再與 manifest 的尾巴逐條核對:
    **核不上即當場拋錯**,不將就——切錯一刀,重凍出來的說明檔就會多或少幾行註記,
    那時「改動前後一樣」這句話已經證不到任何事。
    """
    generated = [
        f"{member.ticker.strip().upper()} 取不到 SEC CIK,"
        f"以佔位錨 {placeholder_cik(member.ticker.strip().upper())} 登記;"
        "日後補回真 CIK 前,這個實體不可與 SEC 申報對接"
        for member in members
        if member.kind == "company" and not cik_map.get(member.ticker.strip().upper())
    ]
    if not generated:
        return list(frozen_notes)
    tail = frozen_notes[-len(generated) :]
    if tail != generated:
        raise SystemExit(
            "切不出呼叫方註記:算出來的管線註記與已凍結 manifest 的尾巴對不上。\n"
            f"  算出 {len(generated)} 條,首條:{generated[0]}\n"
            f"  尾巴 {len(tail)} 條,首條:{tail[0] if tail else '(沒有)'}"
        )
    return list(frozen_notes[: len(frozen_notes) - len(generated)])


def replay_price(gateway: Gateway, out: Path, scratch: Path) -> dict[str, Any]:
    """照原輸入重凍一次現役 S&P500 快照。"""
    from karst.data.ticker_history import (
        anchor_map_for_window,
        read_anchor_table,
        valid_to_for_window,
    )

    frozen_dir = PRICE_ROOT / PRICE_SNAPSHOT
    manifest = _read_manifest(frozen_dir)
    prices = pd.read_parquet(frozen_dir / "prices.parquet", engine="pyarrow")
    universe = pd.read_parquet(frozen_dir / "universe.parquet", engine="pyarrow")

    by_entity = dict(zip(universe["entity_id"], universe["ticker"], strict=True))
    actual = prices.loc[prices["bar_status"] == "actual"].copy()
    actual["ticker"] = [by_entity[int(eid)] for eid in actual["entity_id"]]
    bars = actual.loc[:, ["date", "ticker", "open", "high", "low", "close", "volume"]]
    bars_file = scratch / "sp500_bars_replay_096.csv"
    bars.to_csv(bars_file, index=False, encoding="utf-8")

    tickers = sorted(str(t) for t in universe["ticker"])
    members = resolve_universe(tickers)

    table = read_anchor_table(ANCHOR_TABLE)
    start, end = str(manifest["window_start"]), str(manifest["window_end"])
    cik_map = anchor_map_for_window(table, start=start, end=end)
    anchor_valid_to = valid_to_for_window(table, start=start, end=end)

    caller_notes = _split_caller_notes(list(manifest["notes"]), members, cik_map)

    snapshot, _fetch = gateway.take_snapshot(
        start=start,
        end=end,
        universe=members,
        source=build_source("csv", bars=str(bars_file)),
        root=str(out / "snapshots"),
        taken_on=str(manifest["taken_on"]),
        extra_notes=caller_notes,
        cik_map=cik_map,
        anchor_valid_to=anchor_valid_to,
    )
    return _harvest(
        kind="price",
        snapshot=snapshot,
        directory=Path(snapshot.path),
        frozen_dir=frozen_dir,
        out=out,
        extra={"caller_notes": len(caller_notes), "bars_rows": int(len(bars))},
    )


def replay_macro(gateway: Gateway, out: Path) -> dict[str, Any]:
    """照原輸入重凍一次現役宏觀快照。"""
    from karst.data import CompletenessThresholds, StaticMacroSource

    frozen_dir = MACRO_ROOT / MACRO_SNAPSHOT
    manifest = _read_manifest(frozen_dir)
    series = pd.read_parquet(frozen_dir / "series.parquet", engine="pyarrow")
    actual = series.loc[series["value_status"] == "actual", ["date", "series", "value"]]

    source = StaticMacroSource(actual.copy(), name=str(manifest["source"]))
    snapshot, _fetch = gateway.take_macro_snapshot(
        price_snapshot_id=MACRO_CALENDAR_FROM,
        thresholds=CompletenessThresholds(
            max_stale_days=MAX_STALE_DAYS, max_missing_ratio=MAX_MISSING_RATIO
        ),
        source=source,
        root=str(out / "macro_snapshots"),
        price_root=str(PRICE_ROOT),
        codes=tuple(manifest["series"]),
        taken_on=str(manifest["taken_on"]),
    )
    return _harvest(
        kind="macro",
        snapshot=snapshot,
        directory=Path(snapshot.path),
        frozen_dir=frozen_dir,
        out=out,
        extra={"actual_rows": int(len(actual))},
    )


def _harvest(
    *,
    kind: str,
    snapshot: Any,
    directory: Path,
    frozen_dir: Path,
    out: Path,
    extra: dict[str, Any],
) -> dict[str, Any]:
    """把重凍出來的說明檔與 manifest 原樣抄一份落輸出目錄,並記下身分。"""
    readme = (directory / "說明.md").read_text(encoding="utf-8")
    manifest_text = (directory / "manifest.json").read_text(encoding="utf-8")
    (out / f"{kind}-說明.md").write_text(readme, encoding="utf-8")
    (out / f"{kind}-manifest.json").write_text(manifest_text, encoding="utf-8")

    frozen_readme = (frozen_dir / "說明.md").read_text(encoding="utf-8")
    return {
        "kind": kind,
        "frozen_snapshot_id": frozen_dir.name,
        "replayed_snapshot_id": snapshot.snapshot_id,
        "frozen_content_hash": json.loads(
            (frozen_dir / "manifest.json").read_text(encoding="utf-8")
        )["content_hash"],
        "replayed_content_hash": snapshot.content_hash,
        "reused": bool(getattr(snapshot, "reused", False)),
        "replayed_readme_lines": len(readme.splitlines()),
        "frozen_readme_lines": len(frozen_readme.splitlines()),
        **extra,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="用現役快照的原輸入重凍一次並落檔")
    parser.add_argument("--label", required=True, help="這一次的名(before / after)")
    parser.add_argument("--out", required=True, help="輸出根目錄(會建 <根>/<label>/)")
    args = parser.parse_args()

    out = Path(args.out) / args.label
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    scratch = out / "scratch"
    scratch.mkdir()

    # 動的是複本:生產庫一個位元都不碰
    store_copy = scratch / "karst-replay.sqlite"
    shutil.copy2(LIVE_STORE, store_copy)

    gateway = Gateway.open(str(store_copy))
    try:
        price = replay_price(gateway, out, scratch)
        print(f"價格線重凍 {price['replayed_snapshot_id']}")
        macro = replay_macro(gateway, out)
        print(f"宏觀線重凍 {macro['replayed_snapshot_id']}")
    finally:
        gateway.close()

    summary = {"label": args.label, "price": price, "macro": macro}
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"成果已落 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
