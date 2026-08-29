"""快照說明檔(snapshot readme)與清單(manifest)。

一個快照要自己講得清四件事,不必翻代碼:來源與抓取時間、當時的宇宙名單、
除權除息怎樣處置、停牌怎樣處置。前兩件是血統,後兩件是規格 10.4 要求的明文。

說明檔的**範本只有一份**,就是本檔的 ``SNAPSHOT_README_TEMPLATE``(單一定義,
無第二影像);每個快照目錄裡那份 ``說明.md`` 是照它填出來的實例,住在 ``data/``
(不入 git)。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from .calendar import BAR_ACTUAL, BAR_FILLED, BAR_MISSING, FFILL_LIMIT
from .normalise import (
    EQUIVALENCE_POLICY_ID,
    EQUIVALENCE_RTOL,
    NORMALISATION_POLICY_ID,
    PRICE_SIGNIFICANT_DIGITS,
)
from .ticker_history import ALIAS_RULE

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

NORMALISATION_POLICY = (
    f"價格歸一化:凍結之前,每個價格四捨五入到 {PRICE_SIGNIFICANT_DIGITS} 位"
    "**有效數字**(不是固定小數位——2015 年的已調整舊價低見 0.45 元,固定小數位會把"
    f"它們削平),成交量取整股。取 {PRICE_SIGNIFICANT_DIGITS} 位的理由:來源的已調整價"
    "實測只有 float32 那一級精度(約 7.2 位十進位有效數字,飄移量度出來是 2 至 14 個"
    "float32 ULP),第 8 位起是雜訊,不入庫。精度損失上限為半格,即相對 5e-8;"
    "一支 0.45 元的已調整舊價最多差 0.000011%,一支 285 元的股最多差 0.000005%。"
    "\n\n"
    "同一個窗口重抓,兩次的價格歸一化後仍可能落在相鄰兩格(實測仍有三成如此),"
    "單靠四捨五入不足以令兩次抓取拿到同一個編號,故另有一條**等價重用**規矩:凍結前"
    f"先看快取根內有沒有同窗口、同宇宙、同一套規矩、而且價格相對差不過 {EQUIVALENCE_RTOL:.0e} "
    "的已凍結快照;有就認定是同一批數據,沿用原編號與原檔案,不再多一份副本。"
    "差過容差即當真的更動(除權除息、數據更正一類,那一級至少 1e-3),照 D-026 第 3 條"
    "另開一個編號,舊快照一樣不動。"
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
| 宇宙表代號數 | {universe_tickers} |
| 實體數 | {entities} |
| 同實體別名剔除數 | {alias_dropped_count} |
| 三數等式 | {balance_line} |
| 價格精度 | {price_significant_digits} 位有效數字 |

## 二、除權除息處置

{dividend_policy}

## 三、停牌處置

{halt_policy}

## 四、價格歸一化處置

{normalisation_policy}

## 五、當時的宇宙名單(連同快照一併凍結)

{universe_table}

{notes_section}{alias_section}
## 六、檔案

| 檔案 | 內容 |
|---|---|
| `prices.parquet` | 日線長表:date、entity_id、open/high/low/close/volume、bar_status |
| `calendar.parquet` | 主日曆的交易日 |
| `universe.parquet` | 當時的宇宙名單:代號、實體編號、錨 |
| `manifest.json` | 上表全部欄位的機讀版 |
| `說明.md` | 本檔 |

## 七、存活者偏差

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
    universe_tickers: int,
    alias_dropped: Sequence[str],
    alias_verdicts: Sequence[Any],
    universe_rows: list[dict[str, Any]],
    notes: list[str],
) -> str:
    """照唯一那份範本填出一個快照的說明檔。

    ``universe_tickers`` / ``entities`` / ``alias_dropped`` 是三數等式那一格
    (KARST-084):宇宙表代號數 = 實體數 + 剔除數。對不上就代表有一條代號序列被
    靜靜蓋走,``karst verify`` 核的正是這一條。``alias_verdicts`` 是每次觸發的判詞
    (``ticker_history.AliasVerdict``),逐條落檔——哪個實體、哪幾個代號、留了誰、為什麼。
    """
    header = "| 代號 | 實體編號 | 種類 | 錨 | 名稱 |\n|---|---|---|---|---|"
    lines = [
        f"| {row['ticker']} | {row['entity_id']} | {row['entity_kind']} |"
        f" {row['anchor']} | {row['display_name']} |"
        for row in universe_rows
    ]
    notes_section = ""
    if notes:
        notes_section = "## 五之二、註記\n\n" + "\n".join(f"- {note}" for note in notes) + "\n\n"

    dropped_count = len(tuple(alias_dropped))
    balances = int(universe_tickers) == int(entities) + dropped_count
    balance_line = (
        f"{universe_tickers} 代號 = {entities} 實體 + {dropped_count} 剔除;"
        + ("對得上" if balances else "**對不上——有代號序列被靜靜蓋走,這個快照不可用**")
    )

    alias_section = (
        "## 五之三、同實體別名裁決(KARST-084)\n\n"
        f"{ALIAS_RULE}\n\n"
    )
    if alias_verdicts:
        alias_section += (
            "| 實體 | 收到的代號 | 留低 | 剔走 | 理由 |\n|---|---|---|---|---|\n"
            + "\n".join(
                f"| {verdict.cik} | {'、'.join(verdict.tickers)} |"
                f" {verdict.kept or '(分不出,兩條都剔)'} | {'、'.join(verdict.dropped)} |"
                f" {verdict.reason} |"
                for verdict in alias_verdicts
            )
            + "\n\n"
        )
    else:
        alias_section += "本快照一次都沒有觸發:每個實體都只收到一條代號序列。\n\n"

    return SNAPSHOT_README_TEMPLATE.format(
        universe_tickers=universe_tickers,
        alias_dropped_count=dropped_count,
        balance_line=balance_line,
        alias_section=alias_section,
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
        normalisation_policy=NORMALISATION_POLICY,
        price_significant_digits=PRICE_SIGNIFICANT_DIGITS,
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

    歸一化精度與等價容差也在此列(KARST-033):它們決定了凍下來的數字長什麼樣,
    改了就是另一套數據定義,理應落成另一個編號。這一格同時是**等價重用的配方鎖**
    ——只有 core 逐項相同的快照才拿來比對,舊規矩凍下來的快照永遠不會被誤認作等價。
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
        "price_significant_digits": PRICE_SIGNIFICANT_DIGITS,
        "normalisation_policy_id": NORMALISATION_POLICY_ID,
        "equivalence_policy_id": EQUIVALENCE_POLICY_ID,
        "equivalence_rtol": EQUIVALENCE_RTOL,
    }


def canonical_json(payload: Any) -> str:
    """雜湊用的規範化 JSON:排序鍵、不留空白,同樣的內容永遠同一串字。"""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
