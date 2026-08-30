"""價格快照的**讀回**。凍結那一半住 ``karst.data.freeze``。

D-026:
  · 第 1 條——大批數據存 parquet,單一定義庫只登記編號、來源、路徑與宇宙名單。
  · 第 3 條——每次拉數一個快照編號(日期+內容雜湊),舊快照永不改動。
  · 第 5 條——**單一快取根**、寫入原子化。

一個快照就是一個目錄 ``data/snapshots/<快照編號>/``:

    prices.parquet    日線長表(date、entity_id、OHLCV、bar_status)
    calendar.parquet  主日曆
    universe.parquet  當時的宇宙名單
    manifest.json     機讀清單(來源、抓取時間、兩條處置、內容雜湊)
    說明.md           人讀說明檔

本檔只做「按編號把上面那幾件讀回來」,以及由讀回來的東西**重新核對**兩件事:
內容雜湊對不對得上登記(``verify_snapshot``)、三數等式對不對得上(``universe_balance``)。
核對用的算法一條都不在這裡自己再寫一次——都由凍結模組那一份算,免得核對器與凍結器
各自為政,核得過卻其實不是同一條規矩(KARST-096)。
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from ..store import DefinitionStore
from .errors import SnapshotBroken
from .freeze import (
    CALENDAR_FILE,
    DEFAULT_SNAPSHOT_ROOT,
    MANIFEST_FILE,
    PRICES_FILE,
    README_FILE,
    UNIVERSE_FILE,
    UniverseBalance,
    canonical_prices,
    canonical_universe,
    snapshot_digest,
)

__all__ = [
    "CALENDAR_FILE",
    "DEFAULT_SNAPSHOT_ROOT",
    "MANIFEST_FILE",
    "PRICES_FILE",
    "README_FILE",
    "UNIVERSE_FILE",
    "UniverseBalance",
    "canonical_prices",
    "canonical_universe",
    "read_calendar",
    "read_manifest",
    "read_price_frame",
    "read_price_panel",
    "read_universe",
    "snapshot_dir",
    "universe_balance",
    "verify_snapshot",
]


def snapshot_dir(
    store: DefinitionStore, snapshot_id: str, *, root: str | Path | None = None
) -> Path:
    """快照目錄在哪。以登記的路徑為準,搬過位就退回快取根找同名目錄。"""
    snapshot = store.get_snapshot(snapshot_id)
    candidates: list[Path] = []
    if snapshot.path:
        candidates.append(Path(snapshot.path))
    candidates.append(Path(root or DEFAULT_SNAPSHOT_ROOT) / snapshot_id)
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise SnapshotBroken(
        f"快照 {snapshot_id} 的目錄不在:{'、'.join(str(c) for c in candidates)}"
    )


def read_manifest(
    store: DefinitionStore, snapshot_id: str, *, root: str | Path | None = None
) -> dict[str, Any]:
    """讀回快照清單:來源、抓取時間、兩條處置、內容雜湊都在這裡。"""
    import json

    path = snapshot_dir(store, snapshot_id, root=root) / MANIFEST_FILE
    if not path.exists():
        raise SnapshotBroken(f"快照 {snapshot_id} 缺 {MANIFEST_FILE}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_price_frame(
    store: DefinitionStore, snapshot_id: str, *, root: str | Path | None = None
) -> pd.DataFrame:
    """讀回日線長表(一列一實體一日),欄位見 ``PANEL_COLUMNS``。"""
    path = snapshot_dir(store, snapshot_id, root=root) / PRICES_FILE
    if not path.exists():
        raise SnapshotBroken(f"快照 {snapshot_id} 缺 {PRICES_FILE}")
    return canonical_prices(pd.read_parquet(path, engine="pyarrow"))


def read_calendar(
    store: DefinitionStore, snapshot_id: str, *, root: str | Path | None = None
) -> tuple[str, ...]:
    path = snapshot_dir(store, snapshot_id, root=root) / CALENDAR_FILE
    if not path.exists():
        raise SnapshotBroken(f"快照 {snapshot_id} 缺 {CALENDAR_FILE}")
    return tuple(pd.read_parquet(path, engine="pyarrow")["date"].astype(str))


def read_universe(
    store: DefinitionStore, snapshot_id: str, *, root: str | Path | None = None
) -> pd.DataFrame:
    """讀回連同快照一併凍結的宇宙名單(代號、實體編號、錨)。"""
    path = snapshot_dir(store, snapshot_id, root=root) / UNIVERSE_FILE
    if not path.exists():
        raise SnapshotBroken(f"快照 {snapshot_id} 缺 {UNIVERSE_FILE}")
    return canonical_universe(pd.read_parquet(path, engine="pyarrow"))


def read_price_panel(
    store: DefinitionStore,
    snapshot_id: str,
    *,
    field: str = "close",
    root: str | Path | None = None,
    entity_ids: Sequence[int] | None = None,
) -> pd.DataFrame:
    """按快照編號讀回價格面板:日期為列、**實體編號**為欄。

    留空的格就是留空(NaN)——那是停牌或未上市,不是零。
    """
    frame = read_price_frame(store, snapshot_id, root=root)
    if field not in frame.columns:
        raise SnapshotBroken(f"快照 {snapshot_id} 沒有 {field} 欄")
    if entity_ids is not None:
        wanted = [int(entity_id) for entity_id in entity_ids]
        frame = frame.loc[frame["entity_id"].isin(wanted)]
    panel = frame.pivot(index="date", columns="entity_id", values=field)
    panel.index = pd.DatetimeIndex(pd.to_datetime(panel.index), name="date")
    panel.columns = pd.Index([int(column) for column in panel.columns], name="entity_id")
    return panel.sort_index().sort_index(axis=1)


def universe_balance(
    store: DefinitionStore, snapshot_id: str, *, root: str | Path | None = None
) -> UniverseBalance:
    """由已凍結的檔案算出一個快照的三數等式;不改任何東西,純讀。

    等式本身住凍結模組(``freeze.UniverseBalance``):凍結那一刻寫入說明檔的那一句,
    與這裡事後重核的那一句,是同一條算法算出來的。
    """
    snapshot = store.get_snapshot(snapshot_id)
    manifest = read_manifest(store, snapshot_id, root=root)
    universe = read_universe(store, snapshot_id, root=root)
    declared = "alias_dropped" in manifest
    return UniverseBalance(
        snapshot_id=snapshot_id,
        universe_tickers=len(tuple(snapshot.universe)),
        entities=int(universe["entity_id"].nunique()),
        rows=int(len(universe)),
        alias_dropped=int(manifest.get("alias_dropped", 0)),
        declared=declared,
    )


def verify_snapshot(
    store: DefinitionStore, snapshot_id: str, *, root: str | Path | None = None
) -> str:
    """由目錄裡的檔案重算內容雜湊,對得上登記才過關,回傳那個雜湊。

    這是「同一個快照編號重算兩次一字不差」的檢驗器:檔案被改過一個位,
    重算出來的雜湊即與登記的對不上,當場拋錯。
    """
    snapshot = store.get_snapshot(snapshot_id)
    manifest = read_manifest(store, snapshot_id, root=root)
    recomputed = snapshot_digest(
        read_price_frame(store, snapshot_id, root=root),
        read_calendar(store, snapshot_id, root=root),
        read_universe(store, snapshot_id, root=root),
        manifest["core"],
    )
    if recomputed != snapshot.content_hash:
        raise SnapshotBroken(
            f"快照 {snapshot_id} 的內容與登記的雜湊對不上:"
            f"登記 {snapshot.content_hash},重算 {recomputed}"
        )
    return recomputed
