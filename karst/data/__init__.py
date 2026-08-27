"""行情數據接入與數據快照(KARST-027,依 D-026 / D-027)。

一條管線,五步:抓 → 定日曆 → 按日期把代號解析成實體編號 → 對齊主日曆 → 凍成快照。

    from karst import DefinitionStore
    from karst.data import build_price_snapshot, read_price_panel

    with DefinitionStore.open("karst.sqlite") as store:
        snapshot = build_price_snapshot(store, start="2020-01-01", end="2026-08-26")
        panel = read_price_panel(store, snapshot.snapshot_id)   # 欄=實體編號

兩條明文處置(規格 10.4,寫在每個快照的說明檔,並在 ``bar_status`` 欄驗得到):

  · 除權除息——只存來源的已調整價,不自建除權除息事件表;不同快照之間價格不可直接比較。
  · 停牌——缺日不填補、留空;對齊主日曆時最多前值填補 3 個交易日,超過留 NaN。

護欄(D-027 第 4 條):本套件不開任何 sqlite 連線,登記與查詢一律經 ``karst.store``。
"""

from .calendar import (
    BAR_ACTUAL,
    BAR_FILLED,
    BAR_MISSING,
    FFILL_LIMIT,
    PANEL_COLUMNS,
    align_to_calendar,
    trading_calendar,
)
from .cik import PLACEHOLDER_PREFIX, fetch_cik_map, is_placeholder, placeholder_cik
from .errors import DataFetchFailed, SnapshotBroken, TickerRecycled
from .manifest import (
    DIVIDEND_POLICY,
    DIVIDEND_POLICY_ID,
    HALT_POLICY,
    HALT_POLICY_ID,
    SNAPSHOT_README_TEMPLATE,
)
from .pipeline import (
    PriceSnapshot,
    build_price_snapshot,
    ensure_entities,
    resolve_entity_ids,
    snapshot_summary,
)
from .snapshots import (
    DEFAULT_SNAPSHOT_ROOT,
    read_calendar,
    read_manifest,
    read_price_frame,
    read_price_panel,
    read_universe,
    snapshot_dir,
    verify_snapshot,
)
from .sources import PRICE_FIELDS, PriceSource, StaticSource, YFinanceSource
from .universe import CALENDAR_TICKER, STARTER_UNIVERSE, UniverseMember, tickers_of

__all__ = [
    "BAR_ACTUAL",
    "BAR_FILLED",
    "BAR_MISSING",
    "CALENDAR_TICKER",
    "DEFAULT_SNAPSHOT_ROOT",
    "DIVIDEND_POLICY",
    "DIVIDEND_POLICY_ID",
    "DataFetchFailed",
    "FFILL_LIMIT",
    "HALT_POLICY",
    "HALT_POLICY_ID",
    "PANEL_COLUMNS",
    "PLACEHOLDER_PREFIX",
    "PRICE_FIELDS",
    "PriceSnapshot",
    "PriceSource",
    "SNAPSHOT_README_TEMPLATE",
    "STARTER_UNIVERSE",
    "SnapshotBroken",
    "StaticSource",
    "TickerRecycled",
    "UniverseMember",
    "YFinanceSource",
    "align_to_calendar",
    "build_price_snapshot",
    "ensure_entities",
    "fetch_cik_map",
    "is_placeholder",
    "placeholder_cik",
    "read_calendar",
    "read_manifest",
    "read_price_frame",
    "read_price_panel",
    "read_universe",
    "resolve_entity_ids",
    "snapshot_dir",
    "snapshot_summary",
    "tickers_of",
    "trading_calendar",
    "verify_snapshot",
]
