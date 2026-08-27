"""把一批數據凍結成 parquet 並登記成快照。

D-026 第 1 條:大批數據(行情、基本面、逐字稿)存 parquet,單一定義庫只登記
它的編號、來源、路徑與當時的宇宙名單。這裡只做「凍結+登記」這一小段接縫,
抓取管線本身是另一張票。
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from .store import DefinitionStore


def content_hash(frame: pd.DataFrame) -> str:
    """一批數據的內容雜湊:同樣的內容永遠同一個雜湊,與寫檔時的雜項無關。"""
    digest = hashlib.sha256()
    for column in frame.columns:
        digest.update(str(column).encode("utf-8"))
        digest.update(b"\x00")
    digest.update(pd.util.hash_pandas_object(frame, index=True).to_numpy().tobytes())
    return digest.hexdigest()


def freeze_batch(
    store: DefinitionStore,
    frame: pd.DataFrame,
    *,
    root: str | Path,
    source: str,
    taken_on: date | datetime | str,
    universe: Iterable[str] = (),
) -> str:
    """寫出 parquet 並登記快照,回傳快照編號。

    同一批內容重跑會落回同一個編號、同一個檔;內容變了就是另一個快照,
    舊的一律不動。
    """
    digest = content_hash(frame)
    snapshot_id = store.snapshot_id_for(taken_on, digest)
    directory = Path(root) / source
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{snapshot_id}.parquet"
    if not path.exists():
        frame.to_parquet(path, engine="pyarrow", index=True)
    return store.register_snapshot(
        source=source,
        taken_on=taken_on,
        content_hash=digest,
        path=str(path),
        universe=universe,
    )


def read_batch(store: DefinitionStore, snapshot_id: str) -> pd.DataFrame:
    """按快照編號讀回那一批數據。"""
    snapshot = store.get_snapshot(snapshot_id)
    if not snapshot.path:
        raise FileNotFoundError(f"快照 {snapshot_id} 沒有記錄檔案路徑")
    return pd.read_parquet(snapshot.path, engine="pyarrow")
