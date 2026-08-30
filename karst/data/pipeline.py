"""價格線:由抓取到凍結的那一條管線(D-026 第 5 條:全倉只有一條)。

本檔**只做「把外面那批數搬進來」那一段**——抓、歸一化、定日曆、取代號→CIK 對照。
之後的六步(別名閘 → 對齊實體編號 → 對齊主日曆 → 三數等式 → 寫檔 → 登記簽章)
一步都不在這裡:它們住在 ``karst.data.freeze``,價格線、宏觀線、重凍腳本三處共用
那一份正本(KARST-096)。

於是這條管線讀起來仍然是五步,只是後面那一步整個交了出去:

  1. **抓** —— 適配器向來源要一批日線(已調整價)。抓不到即拋錯,不靜靜跳過。
  2. **歸一化** —— 價格取 7 位有效數字,行在對齊與填補之前:填出來的那一根抄的是
     已歸一化的收市價,不會再飄第二次(KARST-033)。
  3. **定日曆** —— 以主日曆代號(預設 SPY)真有成交的日子做主日曆。
  4. **取錨** —— 上市公司以 SEC CIK 為錨;呼叫方給了帶生效期的對照表就用那一份。
  5. **凍結** —— 交給凍結模組:``freeze_snapshot``。

出來的編號就是回測運行要引用的那一個:同一個編號重算,結果一字不差。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from ..errors import ContractViolation
from ..models import as_date
from ..store import DefinitionStore
from .calendar import trading_calendar
from .cik import fetch_cik_map
from .errors import DataFetchFailed
from .freeze import (
    DEFAULT_SNAPSHOT_ROOT,
    PriceFreezePlan,
    canonical_json,
    freeze_snapshot,
)
from .normalise import normalise_bars
from .sources import PriceSource, YFinanceSource
from .universe import CALENDAR_TICKER, STARTER_UNIVERSE, UniverseMember, tickers_of


@dataclass(frozen=True, slots=True)
class PriceSnapshot:
    """一次拉數的成果單。``snapshot_id`` 就是回測運行要引用的那個編號。"""

    snapshot_id: str
    source: str
    fetched_at: str
    taken_on: str
    window_start: str
    window_end: str
    path: str
    content_hash: str
    universe: tuple[str, ...]
    entity_ids: tuple[int, ...]
    trading_days: int
    rows: int
    notes: tuple[str, ...]
    reused: bool = False
    """這次抓取是否沿用了一份早已凍結的等價快照(KARST-033)。

    ``True`` 即快取根裡沒有多一份副本,``snapshot_id`` 是原本那一個。
    """


def build_price_snapshot(
    store: DefinitionStore,
    *,
    start: date | datetime | str,
    end: date | datetime | str,
    universe: Sequence[UniverseMember] = STARTER_UNIVERSE,
    source: PriceSource | None = None,
    root: str | Path | None = None,
    calendar_ticker: str = CALENDAR_TICKER,
    taken_on: date | datetime | str | None = None,
    sec_user_agent: str | None = None,
    cik_map: dict[str, str] | None = None,
    anchor_valid_to: dict[str, str] | None = None,
    extra_notes: Sequence[str] = (),
) -> PriceSnapshot:
    """跑完整條管線,回傳快照成果單。

    ``extra_notes`` 是**呼叫方交來的註記**,排在管線自己那批之前一併寫入 manifest
    與說明檔。管線只講得出自己見到的事(佔位錨、未收市、等價重用);「這批數據
    少了哪些代號、為什麼少」只有呼叫方知道——標普 500 歷史成分那批抓不到的退市
    代號(KARST-065)正是這樣逐條講出來的。註記不入內容雜湊,所以它改變不了
    快照編號,亦不會令同一批數據凍出第二個編號。

    ``anchor_valid_to`` 是「代號→生效訖」(留空即未結束),由帶生效期的對照表交來
    (``ticker_history.valid_to_for_window``)。它只餵同實體別名那道閘的規則第一關;
    ``None`` 即沒有帶生效期的對照表,見 ``freeze.apply_alias_gate``。
    """
    source = source or YFinanceSource()
    root = Path(root) if root is not None else DEFAULT_SNAPSHOT_ROOT
    members = tuple(universe)
    if not members:
        raise ContractViolation("宇宙名單是空的,無數可抓")
    tickers = tickers_of(members)
    calendar_symbol = str(calendar_ticker).strip().upper()
    if calendar_symbol not in tickers:
        raise ContractViolation(
            f"主日曆代號 {calendar_symbol} 不在宇宙名單內,日曆無從取得"
        )

    window_start, window_end = as_date(start, "start"), as_date(end, "end")
    fetched_at = datetime.now(timezone.utc)
    notes: list[str] = [str(note) for note in extra_notes if str(note).strip()]

    if window_end >= fetched_at.date().isoformat():
        notes.append(
            f"窗口收在 {window_end},那一日可能仍未收市:未收市的日線之後還會變,"
            "同一個窗口重抓會得出另一個快照編號。要可重現,請把窗口收在上一個已收市的交易日"
        )

    bars = source.fetch_daily_bars(tickers, window_start, window_end)
    if bars.empty:
        raise DataFetchFailed(
            f"{source.name} 在 {window_start}~{window_end} 回了空批次,當抓取失敗處理"
        )

    # 歸一化(KARST-033)緊接抓取,行在對齊與填補之前:填出來的那一根抄的是
    # 已歸一化的收市價,不會再飄第二次。
    bars = normalise_bars(bars)

    calendar = trading_calendar(bars, calendar_symbol)

    if cik_map is None:
        if any(member.kind == "company" for member in members):
            try:
                cik_map = fetch_cik_map(user_agent=sec_user_agent)
            except DataFetchFailed as exc:
                cik_map = {}
                notes.append(f"SEC 代號→CIK 對照抓不到,全部上市公司改用佔位錨({exc})")
        else:
            cik_map = {}

    frozen = freeze_snapshot(
        store,
        PriceFreezePlan(
            source=source.name,
            auto_adjust=bool(getattr(source, "auto_adjust", True)),
            fetched_at=fetched_at.isoformat(timespec="seconds"),
            taken_on=(
                as_date(taken_on, "taken_on")
                if taken_on is not None
                else fetched_at.date().isoformat()
            ),
            window_start=window_start,
            window_end=window_end,
            calendar_ticker=calendar_symbol,
            calendar=tuple(str(day) for day in calendar),
            bars=bars,
            members=members,
            universe_tickers=tickers,
            cik_map=cik_map,
            anchor_valid_to=anchor_valid_to or {},
            notes=tuple(notes),
            root=root,
        ),
    )

    return PriceSnapshot(
        snapshot_id=frozen.snapshot_id,
        source=frozen.source,
        fetched_at=frozen.fetched_at,
        taken_on=frozen.taken_on,
        window_start=frozen.window_start,
        window_end=frozen.window_end,
        path=frozen.path,
        content_hash=frozen.content_hash,
        universe=tickers,
        entity_ids=frozen.detail.entity_ids,
        trading_days=frozen.trading_days,
        rows=frozen.rows,
        notes=frozen.notes,
        reused=frozen.reused,
    )


def snapshot_summary(snapshot: PriceSnapshot) -> str:
    """一行講完一個快照的身分,給命令列與交接用。"""
    return canonical_json(
        {
            "snapshot_id": snapshot.snapshot_id,
            "source": snapshot.source,
            "fetched_at": snapshot.fetched_at,
            "window": f"{snapshot.window_start}~{snapshot.window_end}",
            "entities": len(snapshot.entity_ids),
            "rows": snapshot.rows,
        }
    )
