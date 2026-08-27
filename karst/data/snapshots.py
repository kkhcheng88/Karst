"""快照的落地與讀回。

D-026:
  · 第 1 條——大批數據存 parquet,單一定義庫只登記編號、來源、路徑與宇宙名單。
  · 第 3 條——每次拉數一個快照編號(日期+內容雜湊),舊快照永不改動。
  · 第 5 條——**單一快取根**、寫入原子化:先寫暫存目錄,一次過改名到正式編號,
    杜絕舊倉「五套管線五個快取、先撞先贏」的第二影像。

一個快照就是一個目錄 ``data/snapshots/<快照編號>/``:

    prices.parquet    日線長表(date、entity_id、OHLCV、bar_status)
    calendar.parquet  主日曆
    universe.parquet  當時的宇宙名單
    manifest.json     機讀清單(來源、抓取時間、兩條處置、內容雜湊)
    說明.md           人讀說明檔
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from ..batches import content_hash
from ..store import DefinitionStore
from .calendar import PANEL_COLUMNS
from .errors import SnapshotBroken
from .manifest import canonical_json
from .sources import PRICE_FIELDS

# 單一快取根(D-026 第 5 條):全倉的快照只住這一處
DEFAULT_SNAPSHOT_ROOT = Path("data") / "snapshots"

PRICES_FILE = "prices.parquet"
CALENDAR_FILE = "calendar.parquet"
UNIVERSE_FILE = "universe.parquet"
MANIFEST_FILE = "manifest.json"
README_FILE = "說明.md"


def canonical_prices(frame: pd.DataFrame) -> pd.DataFrame:
    """日線長表的規範形態:欄序、型別、排序都寫死。

    寫檔前與讀回後都過這一關,內容雜湊才會**與寫檔的雜項無關**——
    這正是「同一個快照編號讀兩次一字不差」靠的那件事。
    """
    out = frame.loc[:, list(PANEL_COLUMNS)].copy()
    out["date"] = out["date"].astype(str).astype("object")
    out["entity_id"] = out["entity_id"].astype("int64")
    for field in PRICE_FIELDS:
        out[field] = out[field].astype("float64")
    out["bar_status"] = out["bar_status"].astype(str).astype("object")
    return out.sort_values(["date", "entity_id"]).reset_index(drop=True)


def canonical_universe(frame: pd.DataFrame) -> pd.DataFrame:
    """宇宙名單的規範形態:代號排序,文字欄一律 object。"""
    out = frame.copy()
    out["entity_id"] = out["entity_id"].astype("int64")
    for column in out.columns:
        if column != "entity_id":
            out[column] = out[column].astype(str).astype("object")
    return out.sort_values("ticker").reset_index(drop=True)


def snapshot_digest(
    prices: pd.DataFrame,
    calendar: Sequence[str],
    universe: pd.DataFrame,
    core: dict[str, Any],
) -> str:
    """一個快照的內容雜湊:同樣的內容永遠同一串字。

    四件都算進去——日線、主日曆、當時的宇宙名單、決定數據長什麼樣的設定
    (來源、期間、對齊上限、兩條處置)。抓取時間刻意不算,否則同一批數據
    每次重抓都變成新快照。
    """
    import hashlib

    digest = hashlib.sha256()
    digest.update(content_hash(canonical_prices(prices)).encode("utf-8"))
    digest.update(b"|")
    digest.update(content_hash(canonical_universe(universe)).encode("utf-8"))
    digest.update(b"|")
    digest.update("\n".join(str(day) for day in calendar).encode("utf-8"))
    digest.update(b"|")
    digest.update(canonical_json(core).encode("utf-8"))
    return digest.hexdigest()


def write_snapshot_dir(
    root: str | Path,
    snapshot_id: str,
    *,
    prices: pd.DataFrame,
    calendar: Sequence[str],
    universe: pd.DataFrame,
    manifest: dict[str, Any],
    readme: str,
) -> Path:
    """原子寫入一個快照目錄,回傳它的路徑。

    先寫 ``.tmp-…`` 暫存目錄,全部檔案落地之後才一次過改名成正式編號:
    讀的人永遠見不到半截快照。目錄已存在即代表同樣內容早已凍結,原封不動。
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    final = root / snapshot_id
    if final.exists():
        return final

    staging = root / f".tmp-{snapshot_id}-{uuid4().hex[:8]}"
    if staging.exists():  # pragma: no cover - uuid 撞名近乎不可能
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        canonical_prices(prices).to_parquet(
            staging / PRICES_FILE, engine="pyarrow", index=False
        )
        pd.DataFrame({"date": [str(day) for day in calendar]}).to_parquet(
            staging / CALENDAR_FILE, engine="pyarrow", index=False
        )
        canonical_universe(universe).to_parquet(
            staging / UNIVERSE_FILE, engine="pyarrow", index=False
        )
        (staging / MANIFEST_FILE).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (staging / README_FILE).write_text(readme, encoding="utf-8")
        try:
            staging.replace(final)
        except OSError:
            # 同一刻另一個寫入者已把同編號的快照改名落位:內容一樣,讓它贏
            if not final.exists():
                raise
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    return final


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
