"""快照說明檔(snapshot readme)與清單(manifest)。

一個快照要自己講得清四件事,不必翻代碼:來源與抓取時間、當時的宇宙名單、
除權除息怎樣處置、停牌怎樣處置。前兩件是血統,後兩件是規格 10.4 要求的明文。

說明檔的**範本只有一份**,就是本檔的 ``SNAPSHOT_README_TEMPLATE``(單一定義,
無第二影像);每個快照目錄裡那份 ``說明.md`` 是照它填出來的實例,住在 ``data/``
(不入 git)。
"""

from __future__ import annotations

import json
from typing import Any

from .calendar import BAR_ACTUAL, BAR_FILLED, BAR_MISSING, FFILL_LIMIT

# 處置編號:寫在 manifest 裡,程式可據此認出用的是哪一條規矩
DIVIDEND_POLICY_ID = "adjusted-close-only"
HALT_POLICY_ID = f"no-backfill-ffill-{FFILL_LIMIT}"

DIVIDEND_POLICY = (
    "除權除息:只存來源的已調整價(auto_adjust),本倉不自建除權除息事件表(D-026 第 4 條)。"
    "後果明記——每次派息後整條歷史價會變,故**不同快照之間的價格不可直接比較**,"
    "一律以快照編號為準;蠟燭圖畫的是調整價,不是當日真實成交價。"
)

HALT_POLICY = (
    f"停牌:缺日不填補、留空。對齊主日曆時最多以前值填補 {FFILL_LIMIT} 個交易日,"
    "超過即留 NaN;填補出來的那一根寫成 O=H=L=C=前一根收市價、成交量 0。"
    f"每根日線在 bar_status 欄自報身分({BAR_ACTUAL} 真有成交 / {BAR_FILLED} 前值填補 /"
    f" {BAR_MISSING} 留空),所以這條規矩在數據上驗得到。"
)

SNAPSHOT_README_TEMPLATE = """# 數據快照 {snapshot_id}

> 本檔由 `karst.data` 產生,是快照的說明檔;快照一經凍結即不可改,要改就出新編號。

## 一、身分

| 項目 | 內容 |
|---|---|
| 快照編號 | `{snapshot_id}` |
| 來源 | {source} |
| 抓取時間(UTC) | {fetched_at} |
| 快照日期 | {taken_on} |
| 數據期間 | {window_start} ~ {window_end} |
| 主日曆 | {calendar_ticker}(交易日 {trading_days} 日) |
| 內容雜湊 | `{content_hash}` |
| 日線列數 | {rows} |
| 實體數 | {entities} |

## 二、除權除息處置

{dividend_policy}

## 三、停牌處置

{halt_policy}

## 四、當時的宇宙名單(連同快照一併凍結)

{universe_table}

{notes_section}
## 五、檔案

| 檔案 | 內容 |
|---|---|
| `prices.parquet` | 日線長表:date、entity_id、open/high/low/close/volume、bar_status |
| `calendar.parquet` | 主日曆的交易日 |
| `universe.parquet` | 當時的宇宙名單:代號、實體編號、錨 |
| `manifest.json` | 上表全部欄位的機讀版 |
| `說明.md` | 本檔 |

## 六、存活者偏差

免費來源不含退市股(D-026 第 6 條)。本快照的宇宙名單是**抓取當日仍在市**的名單,
以此為據的回測成績報告一律標明「未含退市股」。
"""


def render_readme(
    *,
    snapshot_id: str,
    source: str,
    fetched_at: str,
    taken_on: str,
    window_start: str,
    window_end: str,
    calendar_ticker: str,
    trading_days: int,
    content_hash: str,
    rows: int,
    entities: int,
    universe_rows: list[dict[str, Any]],
    notes: list[str],
) -> str:
    """照唯一那份範本填出一個快照的說明檔。"""
    header = "| 代號 | 實體編號 | 種類 | 錨 | 名稱 |\n|---|---|---|---|---|"
    lines = [
        f"| {row['ticker']} | {row['entity_id']} | {row['entity_kind']} |"
        f" {row['anchor']} | {row['display_name']} |"
        for row in universe_rows
    ]
    notes_section = ""
    if notes:
        notes_section = "## 四之二、註記\n\n" + "\n".join(f"- {note}" for note in notes) + "\n\n"
    return SNAPSHOT_README_TEMPLATE.format(
        snapshot_id=snapshot_id,
        source=source,
        fetched_at=fetched_at,
        taken_on=taken_on,
        window_start=window_start,
        window_end=window_end,
        calendar_ticker=calendar_ticker,
        trading_days=trading_days,
        content_hash=content_hash,
        rows=rows,
        entities=entities,
        dividend_policy=DIVIDEND_POLICY,
        halt_policy=HALT_POLICY,
        universe_table="\n".join([header, *lines]),
        notes_section=notes_section,
    )


def snapshot_core(
    *,
    source: str,
    window_start: str,
    window_end: str,
    calendar_ticker: str,
    auto_adjust: bool,
) -> dict[str, Any]:
    """進內容雜湊的那一格:決定數據長什麼樣的每一項,抓取時間**不在此列**。

    抓取時間不入雜湊,同一批內容重抓才會落回同一個快照編號(D-026 第 3 條)。
    """
    return {
        "source": source,
        "window_start": window_start,
        "window_end": window_end,
        "calendar_ticker": calendar_ticker,
        "auto_adjust": bool(auto_adjust),
        "ffill_limit": FFILL_LIMIT,
        "dividend_policy_id": DIVIDEND_POLICY_ID,
        "halt_policy_id": HALT_POLICY_ID,
    }


def canonical_json(payload: Any) -> str:
    """雜湊用的規範化 JSON:排序鍵、不留空白,同樣的內容永遠同一串字。"""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
