"""由抓取到快照的那一條管線(D-026 第 5 條:全倉只有一條)。

五步,次序寫死:

  1. **抓** —— 適配器向來源要一批日線(已調整價)。抓不到即拋錯,不靜靜跳過。
  2. **定日曆** —— 以主日曆代號(預設 SPY)真有成交的日子做主日曆。
  3. **解析實體** —— 每一列的代號**按它那一日**解析成實體編號(D-026 第 2 條);
     代號只是屬性,價格掛在實體編號上。解析不到即當場拒收,不猜。
  4. **對齊** —— 全部實體對齊主日曆,停牌照明文處置(最多前值填補 3 日,超過留空)。
  5. **凍結** —— 原子寫入 ``data/snapshots/<編號>/``,經單一定義庫登記快照編號,
     連同當時的宇宙名單一併凍結,記下來源名與抓取時間。

出來的編號就是回測運行要引用的那一個:同一個編號重算,結果一字不差。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from ..errors import ContractViolation, TickerNotResolved
from ..models import as_date
from ..store import DefinitionStore
from .calendar import align_to_calendar, trading_calendar
from .cik import fetch_cik_map, is_placeholder, placeholder_cik
from .errors import DataFetchFailed, TickerRecycled
from .manifest import (
    DIVIDEND_POLICY,
    HALT_POLICY,
    NORMALISATION_POLICY,
    canonical_json,
    render_readme,
    snapshot_core,
)
from .normalise import EQUIVALENCE_RTOL, normalise_bars
from .snapshots import (
    DEFAULT_SNAPSHOT_ROOT,
    canonical_universe,
    find_equivalent_snapshot,
    snapshot_digest,
    write_snapshot_dir,
)
from .sources import PRICE_FIELDS, PriceSource, YFinanceSource
from .ticker_history import (
    ALIAS_RULE,
    AliasCandidate,
    AliasVerdict,
    dropped_by_alias,
    resolve_alias_collisions,
)
from .universe import CALENDAR_TICKER, STARTER_UNIVERSE, UniverseMember, tickers_of

UNIVERSE_COLUMNS: tuple[str, ...] = (
    "ticker",
    "entity_id",
    "entity_kind",
    "anchor",
    "anchor_source",
    "display_name",
)


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


def ensure_entities(
    store: DefinitionStore,
    members: Sequence[UniverseMember],
    *,
    bars: pd.DataFrame,
    cik_map: dict[str, str],
    notes: list[str],
) -> pd.DataFrame:
    """登記名單上每一員的實體與代號生效期,回傳「代號→實體編號」的名單表。

    上市公司以 SEC CIK 為錨,抓不到就用佔位錨並記一筆註記;ETF 另編內部代碼。
    代號的生效起用它在這批數據裡**第一日有成交的日子**。
    """
    rows: list[dict[str, object]] = []
    for member in members:
        ticker = member.ticker.strip().upper()
        seen = bars.loc[bars["ticker"] == ticker, "date"]
        if seen.empty:
            raise DataFetchFailed(f"{ticker} 在這批數據裡一日都沒有,不可登記實體")
        first_seen, last_seen = str(seen.min()), str(seen.max())

        if member.kind == "company":
            anchor = cik_map.get(ticker) or placeholder_cik(ticker)
            anchor_source = "placeholder" if is_placeholder(anchor) else "sec"
            if anchor_source == "placeholder":
                notes.append(
                    f"{ticker} 取不到 SEC CIK,以佔位錨 {anchor} 登記;"
                    "日後補回真 CIK 前,這個實體不可與 SEC 申報對接"
                )
            entity_id = store.register_entity(
                kind="company", display_name=member.display_name, cik=anchor
            )
        else:
            anchor, anchor_source = ticker, "local"
            entity_id = store.register_entity(
                kind=member.kind, display_name=member.display_name, local_code=ticker
            )

        _ensure_ticker_period(store, entity_id, ticker, first_seen, last_seen)
        rows.append(
            {
                "ticker": ticker,
                "entity_id": int(entity_id),
                "entity_kind": member.kind,
                "anchor": anchor,
                "anchor_source": anchor_source,
                "display_name": member.display_name,
            }
        )
    return canonical_universe(pd.DataFrame(rows, columns=list(UNIVERSE_COLUMNS)))


def apply_alias_gate(
    members: Sequence[UniverseMember],
    *,
    bars: pd.DataFrame,
    cik_map: dict[str, str],
    anchor_valid_to: dict[str, str],
    notes: list[str],
) -> tuple[tuple[UniverseMember, ...], tuple[str, ...], tuple[AliasVerdict, ...]]:
    """凍結前那一道閘:同一個實體收到多過一條代號序列即按明文規則剔(KARST-084)。

    規則本身**不住在這裡**——它住在 ``ticker_history.resolve_alias_collisions``,
    全倉只有那一份;這道閘只負責備料(誰錨到哪個實體、生效期完了沒有、有幾多根日線)、
    把裁決結果逐條寫入註記(於是它一定入 manifest 與說明檔),再把輸家由名單上剔走。

    ``anchor_valid_to`` 空即「沒有帶生效期的對照表」(SEC 今日對照那條路):那份對照
    列出的每一個代號都是今日仍然在用的,故此當作全部生效期未結束,規則自然落到第二關。
    """
    counts = bars.groupby("ticker").size() if len(bars) else {}
    candidates = [
        AliasCandidate(
            ticker=member.ticker.strip().upper(),
            cik=str(cik_map.get(member.ticker.strip().upper(), "")),
            valid_to=str(anchor_valid_to.get(member.ticker.strip().upper(), "")),
            bar_count=int(counts.get(member.ticker.strip().upper(), 0)),
        )
        for member in members
        if member.kind == "company"
    ]
    verdicts = resolve_alias_collisions(candidates)
    if not verdicts:
        return tuple(members), (), ()

    dropped = dropped_by_alias(verdicts)
    notes.append(f"同實體別名閘(KARST-084)明文規則:{ALIAS_RULE}")
    for verdict in verdicts:
        notes.append(f"同實體別名·{verdict.cik}:{verdict.reason}")
    kept = tuple(member for member in members if member.ticker.strip().upper() not in dropped)
    return kept, dropped, verdicts


def _ensure_ticker_period(
    store: DefinitionStore, entity_id: int, ticker: str, first_seen: str, last_seen: str
) -> None:
    """確保這個代號在這批數據的頭尾兩日都解析得到同一個實體。"""
    try:
        resolved = store.resolve_ticker(ticker, first_seen)
    except TickerNotResolved:
        resolved = None

    if resolved is None:
        owned = [
            period for period in store.ticker_history(ticker) if period.entity_id == entity_id
        ]
        if owned and min(period.valid_from for period in owned) > first_seen:
            raise ContractViolation(
                f"代號 {ticker} 已登記由 {min(p.valid_from for p in owned)} 起生效,"
                f"但這批數據早至 {first_seen};代號生效起不可回頭改,"
                "請由更早的日子重建這個代號的映射"
            )
        store.register_ticker(entity_id, ticker, valid_from=first_seen)
        resolved = entity_id

    if int(resolved) != int(entity_id):
        raise TickerRecycled(
            f"{first_seen} 的代號 {ticker} 屬實體 {resolved},不是 {entity_id};"
            "代號會被回收再發給別人,價格不可掛錯實體"
        )
    if int(store.resolve_ticker(ticker, last_seen)) != int(entity_id):
        raise TickerRecycled(
            f"{last_seen} 的代號 {ticker} 已不屬實體 {entity_id};這批數據跨了代號易主"
        )


def resolve_entity_ids(store: DefinitionStore, bars: pd.DataFrame) -> pd.DataFrame:
    """把每一列的代號**按它那一日**解析成實體編號,然後丟掉代號欄。

    丟掉代號是刻意的:落地之後就再沒有一條路可以用代號當主鍵。
    """
    cache: dict[tuple[str, str], int] = {}
    resolved: list[int] = []
    for ticker, day in zip(bars["ticker"], bars["date"], strict=True):
        key = (str(ticker), str(day))
        if key not in cache:
            cache[key] = int(store.resolve_ticker(key[0], key[1]))
        resolved.append(cache[key])
    frame = bars.copy()
    frame["entity_id"] = pd.Series(resolved, index=frame.index, dtype="int64")
    return frame.loc[:, ["date", "entity_id", *PRICE_FIELDS]].reset_index(drop=True)


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
    ``None`` 即沒有帶生效期的對照表,見 ``apply_alias_gate``。
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

    # 同實體別名那道閘(KARST-084)。行在登記實體**之前**:兩個代號錨到同一個實體,
    # 登記那一層只會回同一個實體編號,兩條價格序列撞在一起而無人出聲(KARST-083 的
    # BBT/TFC、EQR/VMRK 就是這樣靜靜決定的)。規則正本住 ticker_history,不在這裡。
    members, alias_dropped, alias_verdicts = apply_alias_gate(
        members,
        bars=bars,
        cik_map=cik_map,
        anchor_valid_to=anchor_valid_to or {},
        notes=notes,
    )
    if alias_dropped:
        bars = bars.loc[~bars["ticker"].isin(set(alias_dropped))].reset_index(drop=True)
        if bars.empty:
            raise ContractViolation(
                f"同實體別名閘剔走 {len(alias_dropped)} 個代號之後,這批數據一列都不剩"
            )

    universe_frame = ensure_entities(
        store, members, bars=bars, cik_map=cik_map, notes=notes
    )
    aligned = align_to_calendar(resolve_entity_ids(store, bars), calendar)

    core = snapshot_core(
        source=source.name,
        window_start=window_start,
        window_end=window_end,
        calendar_ticker=calendar_symbol,
        auto_adjust=bool(getattr(source, "auto_adjust", True)),
    )
    digest = snapshot_digest(aligned, calendar, universe_frame, core)
    day = as_date(taken_on, "taken_on") if taken_on is not None else fetched_at.date().isoformat()

    # numpy 的整數不入 JSON,一律先換回 Python 的 int
    universe_rows = [
        {key: (int(value) if key == "entity_id" else str(value)) for key, value in row.items()}
        for row in universe_frame.to_dict("records")
    ]
    entity_ids = tuple(sorted(int(row["entity_id"]) for row in universe_rows))

    # 等價重用(KARST-033):凍結之前先問一句「這批數是不是已經凍過了」。
    # 歸一化壓得住飄移的量級,壓不住「剛好跨過捨入格線」,故單靠它不足以令重抓
    # 得同一個編號;這一關才是「重抓不多一份副本」真正靠的那件事。
    existing = find_equivalent_snapshot(
        root, core=core, prices=aligned, calendar=calendar, universe=universe_frame
    )
    if existing is not None:
        path, manifest = existing
        snapshot_id = str(manifest["snapshot_id"])
        digest = str(manifest["content_hash"])
        day = str(manifest["taken_on"])
        reused = True
        notes.append(
            f"這次抓取與已凍結的快照 {snapshot_id} 等價(全部價格相對差不過 "
            f"{EQUIVALENCE_RTOL:.0e}),沿用原編號與原檔案,不另存一份副本;"
            f"該快照的抓取時間仍是 {manifest.get('fetched_at')}(KARST-033)"
        )
    else:
        reused = False
        snapshot_id = store.snapshot_id_for(day, digest)
        manifest = {
            "snapshot_id": snapshot_id,
            "source": source.name,
            "fetched_at": fetched_at.isoformat(timespec="seconds"),
            "taken_on": day,
            "window_start": window_start,
            "window_end": window_end,
            "calendar_ticker": calendar_symbol,
            "trading_days": len(calendar),
            "rows": int(len(aligned)),
            "entities": len(entity_ids),
            # 三數等式(KARST-084):宇宙表代號數 = 實體數 + 剔除數。
            # 對得上就證明沒有一條代號序列被靜靜蓋走;`karst verify` 核的就是這一條。
            "universe_tickers": len(tickers),
            "alias_dropped": len(alias_dropped),
            "alias_rule": ALIAS_RULE,
            "alias_verdicts": [
                {
                    "cik": verdict.cik,
                    "tickers": list(verdict.tickers),
                    "kept": verdict.kept,
                    "dropped": list(verdict.dropped),
                    "reason": verdict.reason,
                }
                for verdict in alias_verdicts
            ],
            "content_hash": digest,
            "core": core,
            "dividend_policy": DIVIDEND_POLICY,
            "halt_policy": HALT_POLICY,
            "normalisation_policy": NORMALISATION_POLICY,
            "universe": universe_rows,
            "notes": notes,
            "survivorship": "免費來源不含退市股;本快照的宇宙名單是抓取當日仍在市的名單(D-026 第 6 條)",
        }
        readme = render_readme(
            snapshot_id=snapshot_id,
            source=source.name,
            fetched_at=manifest["fetched_at"],
            taken_on=day,
            window_start=window_start,
            window_end=window_end,
            calendar_ticker=calendar_symbol,
            trading_days=len(calendar),
            content_hash=digest,
            rows=int(len(aligned)),
            entities=len(entity_ids),
            universe_tickers=len(tickers),
            alias_dropped=alias_dropped,
            alias_verdicts=alias_verdicts,
            universe_rows=universe_rows,
            notes=notes,
        )
        path = write_snapshot_dir(
            root,
            snapshot_id,
            prices=aligned,
            calendar=calendar,
            universe=universe_frame,
            manifest=manifest,
            readme=readme,
        )

    registered = store.register_snapshot(
        source=source.name,
        taken_on=day,
        content_hash=digest,
        path=path.as_posix(),
        universe=tickers,
    )
    if registered != snapshot_id:  # pragma: no cover - 兩邊同一條算法,對不上即是庫壞了
        raise ContractViolation(
            f"快照編號對不上:管線算出 {snapshot_id},登記表回 {registered}"
        )

    return PriceSnapshot(
        snapshot_id=snapshot_id,
        source=source.name,
        fetched_at=str(manifest["fetched_at"]),
        taken_on=day,
        window_start=window_start,
        window_end=window_end,
        path=path.as_posix(),
        content_hash=digest,
        universe=tickers,
        entity_ids=entity_ids,
        trading_days=len(calendar),
        rows=int(len(aligned)),
        notes=tuple(notes),
        reused=reused,
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
