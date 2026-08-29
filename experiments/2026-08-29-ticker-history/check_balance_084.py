"""三代標普 500 快照的三數等式核對(KARST-084 第四步)。

**唯讀,不重凍**:只讀已凍結的 ``universe.parquet`` 與 ``manifest.json``,再對照登記
那一列的宇宙名單,核一條等式——

    宇宙表代號數(入口收到) = 實體數(凍下來) + 剔除數(同實體別名閘剔走)

對不上就代表有兩個代號錨到同一個實體、其中一條價格序列被登記那一層靜靜蓋走
(D-026 第 2 條:實體編號才是主鍵,代號只是帶生效期的屬性)。

跑法(倉根)::

    python experiments/2026-08-29-ticker-history/check_balance_084.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from karst.data.snapshots import read_universe, universe_balance  # noqa: E402
from karst.store import DefinitionStore  # noqa: E402

STORE_PATH = REPO_ROOT / "karst.sqlite"

GENERATIONS = (
    ("第一代(KARST-065 原凍)", "2026-08-28-493fd1df1cb9"),
    ("第二代(KARST-082 改錨重凍)", "2026-08-28-c442236133d4"),
    ("第三代(KARST-083 辨明 32 個代號)", "2026-08-28-3bf7ab0a522a"),
)


def main() -> int:
    store = DefinitionStore.open(str(STORE_PATH))
    failed = 0
    for label, snapshot_id in GENERATIONS:
        balance = universe_balance(store, snapshot_id)
        print(f"{label} {snapshot_id}")
        print(f"  {balance.describe()}")

        # 對不上就把撞在一起的實體逐個列出來,講得出是哪幾個代號共用了一個實體編號。
        if not balance.balances:
            failed += 1
            universe = read_universe(store, snapshot_id)
            clashes = universe.groupby("entity_id")["ticker"].apply(list)
            for entity_id, tickers in clashes.items():
                if len(tickers) > 1:
                    print(f"  實體 {entity_id} 收到 {len(tickers)} 個代號:{'、'.join(tickers)}")
    print(f"三代核對完:{len(GENERATIONS) - failed} 個對得上,{failed} 個對不上")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
