"""期初存貨(opening inventory):檢視視窗一開波,手上已經有的那批貨。

檢視視窗是**重看不重跑**(詞彙表「檢視視窗」),所以它必然會由中間切一刀:
切之前買入、切之後才賣出的倉,在視窗之內只見得到賣出那一邊。單邊配不出來回,
先入先出於是報「賣出但手上沒有貨」——KARST-032 撞到的正是這一道。

補法是把那批倉當**期初存貨**:視窗未開波之前最後一個交易日收工時手上有什麼,
就按**那一日的收市價**入帳做成本,再與視窗之內的成交配對。

**為什麼取前一日收價,不取視窗第一日收價**:``window_stats`` 把淨值由視窗
第一日的收市值重設為 100(``karst.runs.window``),即是話這一段量度的是
「由第一日收工起計」的變化。用前一日收價,換來兩件事:視窗第一日本身那些成交
仍然算在這一段之內(它本來就是那一日發生的事);以及**全期視窗一個字不變**
——全期的第一日之前沒有前一日,期初存貨必然是空,八項數字與未有本層之前
逐位相同。代價是承接回來那一注的成本與淨值基準之間,差住第一日那一日的走勢,
數目細但不是零。

成本只取價,**不帶入場費用**:那筆費用在上一段已經付過,算落這一段等於同一筆
費用收兩次。同理,承接回來的倉不計入這一段的成交金額(換手只數這一段真正落過
的單),而視窗完結時仍未平的倉不入來回類指標——它未有結果;它的未實現賺蝕
由逐日淨值那一邊自然帶出,累計回報、最大回撤、Sortino 全部已經含住。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ..data.snapshots import read_price_panel
from ..errors import NotFound
from ..runs import RunStore
from ..store import RunRecord


@dataclass(frozen=True, slots=True)
class OpeningLot:
    """期初存貨的一注:視窗開波之前已經在手上的一個實體。

    ``as_of`` 是估值日(視窗之前最後一個交易日),``price`` 是該日收市價,
    亦即這一注在本段的入帳成本。費用一律 0——見本檔開頭。
    """

    entity_id: int
    as_of: str
    shares: float
    price: float


def valuation_day(equity: pd.Series, window_start: str) -> pd.Timestamp | None:
    """估值日:視窗第一個交易日**之前**的最後一個交易日。

    視窗由運行第一日起計就沒有前一日,回 ``None``——那一段沒有東西要承接。
    """
    index = pd.DatetimeIndex(equity.index)
    earlier = index[index < pd.Timestamp(window_start)]
    if len(earlier) == 0:
        return None
    return earlier[-1]


def opening_inventory(
    runs: RunStore,
    record: RunRecord,
    equity: pd.Series,
    window_start: str,
    *,
    root: str | Path | None = None,
) -> tuple[OpeningLot, ...]:
    """視窗開波那一刻手上有什麼,連同按估值日收市價定的成本。

    全期(或者由運行第一日起計)的視窗回空——沒有承接,亦即與未有本層之前
    行同一條路。收市價取的是**這次運行自己那個快照**(規格 8.4、D-026 第 4 條):
    快照只存已調整價,換一個快照整條歷史會變,兩邊的數字就不可比。
    """
    day = valuation_day(equity, window_start)
    if day is None:
        return ()

    held = {
        int(entity_id): float(shares)
        for entity_id, shares in runs.holdings_on(record.run_id, day.date()).items()
        if float(shares) > 0.0
    }
    if not held:
        return ()

    entity_ids = sorted(held)
    closes = _closes_upto(runs.store, record.snapshot_id, entity_ids, day, root=root)
    as_of = str(day.date())
    return tuple(
        OpeningLot(
            entity_id=entity_id,
            as_of=as_of,
            shares=held[entity_id],
            price=closes[entity_id],
        )
        for entity_id in entity_ids
    )


def _closes_upto(
    store,
    snapshot_id: str,
    entity_ids: list[int],
    day: pd.Timestamp,
    *,
    root: str | Path | None = None,
) -> dict[int, float]:
    """估值日的收市價;那日停牌就取停牌之前最後一口價。

    一隻都查不到價就當場拋錯,**不當它是零**:成本填 0 會令那一注的來回
    賺足全副身家,比算不出更壞。
    """
    panel = read_price_panel(
        store, snapshot_id, field="close", root=root, entity_ids=entity_ids
    )
    upto = panel.loc[panel.index <= day]
    if upto.empty:
        raise NotFound(
            f"快照 {snapshot_id} 在 {day.date()} 或之前一日收市價都沒有,"
            "估不到期初存貨的成本"
        )

    latest = upto.ffill().iloc[-1]
    closes: dict[int, float] = {}
    for entity_id in entity_ids:
        value = latest.get(entity_id)
        if value is None or not pd.notna(value) or float(value) <= 0.0:
            raise NotFound(
                f"快照 {snapshot_id} 沒有實體 {entity_id} 截至 {day.date()} 的收市價,"
                "估不到期初存貨的成本"
            )
        closes[entity_id] = float(value)
    return closes
