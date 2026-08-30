"""凍結模組(snapshot freezer):全倉唯一一條「把一批數凍成有編號的快照」的路。

# 一、這個模組解決的是什麼

從前「凍結」有三份實作:價格線一份(``pipeline``)、宏觀線自己一份(``macro``)、
重凍腳本再一份。三份各自做同一件事——算內容雜湊、查有沒有凍過、取編號、砌 manifest、
填說明檔、原子寫檔、經唯一入口登記簽章——於是同一條規矩要改三個地方,而**改漏一處
沒有人會發現**:三份都跑得通,只是凍出來的東西不一樣。

本模組把那六步收成一份正本,**一個入口**:``freeze_snapshot``。別名閘、三數等式、
簽章登記、說明檔格式全部住在裡面,不再散落。價格線、宏觀線、重凍腳本是它的三個
呼叫者,各自只剩「把外面那批數搬進來」那一段——那一段才是它們真正不同的地方。

# 二、六步,次序寫死

  1. **別名閘**(KARST-084)—— 同一個實體收到多過一條代號序列即按明文規則剔。
     規則正本住 ``ticker_history``,這裡只備料、落判詞、剔走輸家。
  2. **對齊實體編號**(D-026 第 2 條)—— 登記實體與代號生效期,再把每一列的代號
     **按它那一日**解析成實體編號,然後丟掉代號欄:落地之後就再沒有一條路可以用
     代號當主鍵。宏觀序列不是實體,這一步在它身上不跑(理由見 ``macro`` 開頭)。
  3. **對齊主日曆** —— 停牌照明文處置(最多前值填補 3 日,超過留空)。
  4. **三數等式**(KARST-084)—— 宇宙表代號數 = 實體數 + 剔除數。對得上就證明沒有
     一條代號序列被靜靜蓋走;``karst verify`` 核的就是這一條。宏觀那邊對應的是齊全度
     核對(KARST-061):逐條序列對主日曆核尾段與留空比例。
  5. **寫檔** —— 算內容雜湊、先問一句「這批數是不是已經凍過了」(等價重用,
     KARST-033)、取編號、砌 manifest、填說明檔、原子寫入快取根。
  6. **登記簽章**(KARST-087)—— 經單一定義庫登記,那道門的簽章手才寫得入;
     登記表回的編號與這裡算的對不上即當場拋錯(兩邊同一條算法,對不上即是庫壞了)。

# 三、兩種快照,同一個形狀

價格快照與宏觀快照的**內容**差很遠,**形狀**卻是同一個:一張主表、一張名冊表、
一條主日曆、一格決定內容長什麼樣的設定(``core``)。所以雜湊、等價比對、原子寫檔
三件在這裡各只有一份實作,靠 ``_Shape`` 講出「這一種快照的主表叫什麼、名冊叫什麼、
等價要比哪幾欄」。

    | | 價格快照 | 宏觀快照 |
    |---|---|---|
    | 主表 | ``prices.parquet`` | ``series.parquet`` |
    | 名冊 | ``universe.parquet``(宇宙名單) | ``registry.parquet``(序列名冊) |
    | 主鍵 | 實體編號 | 序列代號 |
    | 逐位要同的欄 | date、entity_id、bar_status | date、series、value_status |
    | 容差內要同的欄 | 開高低收量 | value |

# 四、抓取時間不入雜湊

``fetched_at`` 是牆上的鐘,刻意不入內容雜湊(D-026 第 3 條):同一批內容重抓要落回
同一個編號,否則每次重抓都變成新快照。它落在 manifest 與說明檔,查得回。
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd

from ..batches import content_hash
from ..errors import ContractViolation, TickerNotResolved
from ..store import DefinitionStore
from .calendar import (
    BAR_ACTUAL,
    BAR_FILLED,
    BAR_MISSING,
    FFILL_LIMIT,
    PANEL_COLUMNS,
    align_to_calendar,
)
from .cik import is_placeholder, placeholder_cik
from .errors import DataFetchFailed, TickerRecycled
from .normalise import (
    EQUIVALENCE_POLICY_ID,
    EQUIVALENCE_RTOL,
    NORMALISATION_POLICY_ID,
    PRICE_SIGNIFICANT_DIGITS,
    values_equivalent,
)
from .sources import PRICE_FIELDS
from .ticker_history import (
    ALIAS_RULE,
    AliasCandidate,
    AliasVerdict,
    dropped_by_alias,
    resolve_alias_collisions,
)
from .universe import UniverseMember

# ----------------------------------------------------------------------
# 一、快取根、檔名、規範形態
# ----------------------------------------------------------------------

# 單一快取根(D-026 第 5 條):全倉的快照只住這兩處,價格與宏觀分家
DEFAULT_SNAPSHOT_ROOT = Path("data") / "snapshots"
DEFAULT_MACRO_ROOT = Path("data") / "macro_snapshots"

PRICES_FILE = "prices.parquet"
SERIES_FILE = "series.parquet"
CALENDAR_FILE = "calendar.parquet"
UNIVERSE_FILE = "universe.parquet"
REGISTRY_FILE = "registry.parquet"
MANIFEST_FILE = "manifest.json"
README_FILE = "說明.md"

SNAPSHOT_KIND_PRICE = "price"
SNAPSHOT_KIND_MACRO = "macro"

UNIVERSE_COLUMNS: tuple[str, ...] = (
    "ticker",
    "entity_id",
    "entity_kind",
    "anchor",
    "anchor_source",
    "display_name",
)

# 統一輸出:一列一條序列一日。``value_status`` 與價格的 ``bar_status`` 同義同值。
SERIES_COLUMNS: tuple[str, ...] = ("date", "series", "value", "value_status")


def canonical_json(payload: Any) -> str:
    """雜湊用的規範化 JSON:排序鍵、不留空白,同樣的內容永遠同一串字。"""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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


def canonical_macro(frame: pd.DataFrame) -> pd.DataFrame:
    """宏觀長表的規範形態:欄序、型別、排序都寫死。

    與 ``canonical_prices`` 同一個用途——寫檔前與讀回後都過這一關,
    內容雜湊才會與寫檔的雜項無關。
    """
    out = frame.loc[:, list(SERIES_COLUMNS)].copy()
    out["date"] = out["date"].astype(str).astype("object")
    out["series"] = out["series"].astype(str).astype("object")
    out["value"] = out["value"].astype("float64")
    out["value_status"] = out["value_status"].astype(str).astype("object")
    return out.sort_values(["date", "series"]).reset_index(drop=True)


def _as_is(frame: pd.DataFrame) -> pd.DataFrame:
    """名冊表由呼叫方交來時已是規範形態(序列名冊排序寫死在它自己那一格)。"""
    return frame


@dataclass(frozen=True, slots=True)
class _Shape:
    """一種快照的形狀:主表與名冊表叫什麼、怎樣規範化、等價要比哪幾欄。

    有了這一格,雜湊、等價比對、原子寫檔三件在本模組各只有**一份**實作。
    兩種快照的分別由這裡的資料講出來,不是由三段各自抄一次的程式講出來。
    """

    kind: str
    data_file: str
    roster_file: str
    canonical_data: Callable[[pd.DataFrame], pd.DataFrame]
    canonical_roster: Callable[[pd.DataFrame], pd.DataFrame]
    #: 逐位要相同的欄(形狀那半,不留餘地)
    exact_columns: tuple[str, ...]
    #: 容差內要相同的欄(數值那半)
    numeric_columns: tuple[str, ...]


PRICE_SHAPE = _Shape(
    kind=SNAPSHOT_KIND_PRICE,
    data_file=PRICES_FILE,
    roster_file=UNIVERSE_FILE,
    canonical_data=canonical_prices,
    canonical_roster=canonical_universe,
    exact_columns=("date", "entity_id", "bar_status"),
    numeric_columns=PRICE_FIELDS,
)

MACRO_SHAPE = _Shape(
    kind=SNAPSHOT_KIND_MACRO,
    data_file=SERIES_FILE,
    roster_file=REGISTRY_FILE,
    canonical_data=canonical_macro,
    canonical_roster=_as_is,
    exact_columns=("date", "series", "value_status"),
    numeric_columns=("value",),
)


# ----------------------------------------------------------------------
# 二、明文處置(規格 10.4:每個快照要自己講得清)
# ----------------------------------------------------------------------

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

MACRO_INFORMED_POLICY = (
    "知情時間:本快照全部序列一律**當日收市後可得**(D-021 第 3 條),與價格同一級。"
    "驅動器在決策日看得見的最後一行就是決策日當日的收市讀數,成交在之後那一根 K 線"
    "的開價。指數與息率序列沒有盤後修訂的問題;期貨結算價亦於收市後公布。"
)

NON_INVESTABLE_POLICY = (
    "非可投資序列處置:本快照的序列**一律不是可投資對象**。它們不入 entity 表、"
    "不佔實體編號、不入代號生效期映射表,亦不入價格快照的 prices.parquet——"
    "所以永遠不會出現在價格面板裡,引擎的目標比重表以實體編號為欄,"
    "**結構性地落不到注在它們身上**(不是靠自律)。本快照的主鍵是序列代號,不是實體編號。"
    "HY_ETF(HYG)與 IG_ETF(LQD)背後雖是可投資 ETF,在此亦只作訊號來源,同樣不入實體表;"
    "要真的持有它們,須另行寫入宇宙名單、走價格那一條管線。"
)

MACRO_HALT_POLICY = (
    f"缺日處置:與價格同一條規矩(karst.data.calendar)。對齊主日曆時最多以前值填補 "
    f"{FFILL_LIMIT} 個交易日,超過即留空(NaN),不外推、不內插、不當零。"
    f"每一格自報身分(value_status:{BAR_ACTUAL} 真有讀數 / {BAR_FILLED} 前值填補 / "
    f"{BAR_MISSING} 留空),所以「哪一格是填出來的」在數據上驗得到。"
    "驅動器讀到留空即當回望期不夠,退回熱身期權重並記成「數據不足」。"
)

MACRO_NORMALISATION_POLICY = (
    f"歸一化:凍結前每個讀數四捨五入到 {PRICE_SIGNIFICANT_DIGITS} 位有效數字,"
    "與價格快照同一條規矩、同一個函式(D-028 第 1 條)。同樣配一層等價重用:"
    f"同窗口、同序列、同規矩而讀數相對差不過 {EQUIVALENCE_RTOL:.0e} 的已凍結宏觀快照,"
    "沿用原編號原檔案,不另存一份副本。"
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


def macro_core(
    *,
    source: str,
    window_start: str,
    window_end: str,
    calendar_ticker: str,
    series_codes: Sequence[str],
) -> dict[str, Any]:
    """進內容雜湊的那一格:決定這批宏觀數據長什麼樣的每一項。抓取時間不在此列。"""
    return {
        "source": source,
        "window_start": window_start,
        "window_end": window_end,
        "calendar_ticker": calendar_ticker,
        "series": sorted(str(code) for code in series_codes),
        "ffill_limit": FFILL_LIMIT,
        "informed_at": "close",
        "non_investable": True,
        "price_significant_digits": PRICE_SIGNIFICANT_DIGITS,
        "normalisation_policy_id": NORMALISATION_POLICY_ID,
        "equivalence_policy_id": EQUIVALENCE_POLICY_ID,
        "equivalence_rtol": EQUIVALENCE_RTOL,
    }


def _digest(
    data: pd.DataFrame,
    roster: pd.DataFrame,
    calendar: Sequence[str],
    core: dict[str, Any],
) -> str:
    """一個快照的內容雜湊:同樣的內容永遠同一串字。

    四件都算進去——主表、名冊表、主日曆、決定數據長什麼樣的設定。抓取時間刻意不算,
    否則同一批數據每次重抓都變成新快照。兩種快照同一條算法,故此只有這一份。

    交進來的兩張表**必須已經是規範形態**(見 ``_Shape.canonical_*``):雜湊要與寫檔
    的雜項無關,規範化就是把那些雜項抹平的那一關。
    """
    digest = hashlib.sha256()
    digest.update(content_hash(data).encode("utf-8"))
    digest.update(b"|")
    digest.update(content_hash(roster).encode("utf-8"))
    digest.update(b"|")
    digest.update("\n".join(str(day) for day in calendar).encode("utf-8"))
    digest.update(b"|")
    digest.update(canonical_json(core).encode("utf-8"))
    return digest.hexdigest()


def snapshot_digest(
    prices: pd.DataFrame,
    calendar: Sequence[str],
    universe: pd.DataFrame,
    core: dict[str, Any],
) -> str:
    """一個價格快照的內容雜湊。"""
    return _digest(canonical_prices(prices), canonical_universe(universe), calendar, core)


def macro_digest(
    values: pd.DataFrame,
    calendar: Sequence[str],
    registry: pd.DataFrame,
    core: dict[str, Any],
) -> str:
    """一個宏觀快照的內容雜湊。"""
    return _digest(canonical_macro(values), registry, calendar, core)


# ----------------------------------------------------------------------
# 三、三數等式(KARST-084)
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UniverseBalance:
    """一個快照的三數等式:宇宙表代號數 = 實體數 + 剔除數。

    * ``universe_tickers``——**入口收到**的代號數,即登記那一列的宇宙名單長度。
    * ``entities``——凍下來的宇宙表裡不同的實體編號數。
    * ``alias_dropped``——同實體別名閘剔走的代號數。

    對不上就代表有一條代號序列在登記實體那一層被靜靜蓋走(KARST-083 的 BBT/TFC、
    EQR/VMRK 正是這樣),那個快照的宇宙名單與它實際載住的價格對不上,不可用。

    ``declared`` 是 ``False`` 即**說明檔沒有剔除數那一格**(凍結於這道閘之前)。
    那時剔除數以 0 核——不是猜:那一刻根本沒有這道閘,一條都沒有剔過。

    等式只有這一份:凍結那一刻寫入 manifest 與說明檔的那一句,與 ``karst verify``
    事後重核的那一句,都由這裡算出來。
    """

    snapshot_id: str
    universe_tickers: int
    entities: int
    rows: int
    alias_dropped: int
    declared: bool

    @property
    def balances(self) -> bool:
        """三數對得上,而且宇宙表裡沒有兩個代號共用一個實體編號。"""
        return (
            self.universe_tickers == self.entities + self.alias_dropped
            and self.rows == self.entities
        )

    def describe(self) -> str:
        head = (
            f"{self.snapshot_id}:宇宙表代號數 {self.universe_tickers} = 實體數 "
            f"{self.entities} + 剔除數 {self.alias_dropped}"
        )
        if not self.declared:
            head += "(說明檔沒有剔除數那一格,凍結於同實體別名閘之前,以 0 核)"
        if self.balances:
            return head + ";對得上"
        return (
            head
            + f";**對不上**——凍下來的宇宙表有 {self.rows} 個代號、只有 {self.entities} "
            "個實體,即有代號序列被靜靜蓋走"
        )


def balance_line(*, universe_tickers: int, entities: int, alias_dropped: int) -> str:
    """說明檔身分表裡那一句三數等式。凍結那一刻算,不必等到事後重核。"""
    balances = int(universe_tickers) == int(entities) + int(alias_dropped)
    return (
        f"{universe_tickers} 代號 = {entities} 實體 + {alias_dropped} 剔除;"
        + ("對得上" if balances else "**對不上——有代號序列被靜靜蓋走,這個快照不可用**")
    )


# ----------------------------------------------------------------------
# 四、別名閘(KARST-084)
# ----------------------------------------------------------------------


def alias_candidates(
    entries: Sequence[tuple[str, str, str]], *, bars: pd.DataFrame
) -> tuple[AliasCandidate, ...]:
    """把「代號、錨、生效訖」三件加上日線根數,砌成別名閘的候選。

    根數要由**手上這批日線**數,不可以由對照表推:同一個代號在不同窗口有幾多日
    有成交本來就不同,而規則第二關比的正是根數(長的那條留)。價格線與重凍腳本
    兩處都要備這一格,所以備料連同規則一樣只留一份。
    """
    counts = bars.groupby("ticker").size() if len(bars) else {}
    return tuple(
        AliasCandidate(
            ticker=ticker,
            cik=str(cik),
            valid_to=str(valid_to),
            bar_count=int(counts.get(ticker, 0)),
        )
        for ticker, cik, valid_to in entries
    )


def apply_alias_gate(
    members: Sequence[UniverseMember],
    *,
    bars: pd.DataFrame,
    cik_map: dict[str, str],
    anchor_valid_to: dict[str, str],
    notes: list[str],
) -> tuple[tuple[UniverseMember, ...], tuple[str, ...], tuple[AliasVerdict, ...]]:
    """凍結前那一道閘:同一個實體收到多過一條代號序列即按明文規則剔。

    規則本身**不住在這裡**——它住在 ``ticker_history.resolve_alias_collisions``,
    全倉只有那一份;這道閘只負責備料(誰錨到哪個實體、生效期完了沒有、有幾多根日線)、
    把裁決結果逐條寫入註記(於是它一定入 manifest 與說明檔),再把輸家由名單上剔走。

    ``anchor_valid_to`` 空即「沒有帶生效期的對照表」(SEC 今日對照那條路):那份對照
    列出的每一個代號都是今日仍然在用的,故此當作全部生效期未結束,規則自然落到第二關。
    """
    entries: list[tuple[str, str, str]] = []
    for member in members:
        if member.kind != "company":
            continue
        ticker = member.ticker.strip().upper()
        entries.append(
            (ticker, str(cik_map.get(ticker, "")), str(anchor_valid_to.get(ticker, "")))
        )
    verdicts = resolve_alias_collisions(alias_candidates(entries, bars=bars))
    if not verdicts:
        return tuple(members), (), ()

    dropped = dropped_by_alias(verdicts)
    notes.append(f"同實體別名閘(KARST-084)明文規則:{ALIAS_RULE}")
    for verdict in verdicts:
        notes.append(f"同實體別名·{verdict.cik}:{verdict.reason}")
    kept = tuple(member for member in members if member.ticker.strip().upper() not in dropped)
    return kept, dropped, verdicts


# ----------------------------------------------------------------------
# 五、對齊實體編號(D-026 第 2 條)
# ----------------------------------------------------------------------


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


def align_macro_to_calendar(
    values: pd.DataFrame,
    calendar: Sequence[str],
    *,
    ffill_limit: int = FFILL_LIMIT,
) -> pd.DataFrame:
    """把宏觀讀數對齊**價格快照那條主日曆**,並標明每一格的身分。

    對齊到價格的主日曆(而不是各自為政)是刻意的:驅動器在同一個決策日既要看
    四格 ETF 的收價,又要看宏觀讀數,兩邊的日子必須是同一批,否則「決策日」這
    三個字在兩個表裡各指一日。宏觀序列自己的假期與美股不同(例如期貨多幾日),
    對齊之後多出來的日子一律丟掉、缺的日子照停牌處置最多前值填補 ``ffill_limit``
    個交易日。
    """
    days = pd.Index(sorted({str(day) for day in calendar}), name="date")
    if days.empty:
        raise ContractViolation("主日曆是空的,無法對齊")

    blocks: list[pd.DataFrame] = []
    for code, block in values.groupby("series", sort=True):
        aligned_block = (
            block.drop_duplicates(subset="date", keep="last")
            .set_index("date")
            .sort_index()
            .reindex(days)
        )
        actual = aligned_block["value"].notna().to_numpy()
        carried = aligned_block["value"].ffill(limit=ffill_limit)
        filled = carried.notna().to_numpy() & ~actual
        carried_values = carried.to_numpy(dtype="float64")
        original = aligned_block["value"].to_numpy(dtype="float64")

        out = pd.DataFrame(index=days)
        out["series"] = str(code)
        out["value"] = np.where(actual, original, np.where(filled, carried_values, np.nan))
        out["value_status"] = np.where(
            actual, BAR_ACTUAL, np.where(filled, BAR_FILLED, BAR_MISSING)
        )
        blocks.append(out.reset_index())

    if not blocks:
        return pd.DataFrame({column: pd.Series(dtype="object") for column in SERIES_COLUMNS})

    frame = pd.concat(blocks, ignore_index=True)
    return canonical_macro(frame)


# ----------------------------------------------------------------------
# 六、齊全度核對(KARST-061;源自假設 A-008)
# ----------------------------------------------------------------------
#
# A-008 已經真的塌過一次:yfinance 的 ^VIX3M 自 2026-07-17 起靜靜地不再供新讀數,
# 抓取**一個錯都沒有報**——適配器的失手處置只認「回空批次」與「一條讀數都沒有」
# 兩種,而「由某一日起不再有新的」兩種都不是。對齊主日曆時尾段照停牌處置留空,
# 驅動器讀到留空即當「數據不足」退回熱身期權重:掃描照跑、報告照出、成績表照畫,
# 只是那個驅動器由某一日起實際上已經停止講話,而 28 個交易日無人察覺。
#
# 本節做的就是把「有沒有停止講話」由**要人去翻說明檔第七節**,改成**凍結那一刻
# 就講出來**。核對兩件事,逐條序列各自算:
#
#   1. **尾段落後** —— 最後一個真讀數之後,主日曆上還剩幾多個交易日。
#   2. **留空比例** —— 整段窗口留空的日數佔主日曆幾多。
#
# 兩個門檻**都是參數、都沒有預設值**(D-008 第 3 條)。理由不是懶得揀:「幾多日
# 算停更」不是數據的性質,是用戶對這條訊號的容忍度——程式代它揀一個數,等於把一個
# 沒有人裁決過的判斷寫進了每一次凍結,而且下一個人不會知道那個數是誰揀的。

ALERT_STALE_TAIL = "尾段落後"
ALERT_MISSING_RATIO = "留空過多"

COMPLETENESS_COLUMNS: tuple[str, ...] = (
    "series",
    "actual",
    "filled",
    "missing",
    "missing_ratio",
    "first_actual",
    "last_actual",
    "stale_days",
)


@dataclass(frozen=True, slots=True)
class CompletenessThresholds:
    """齊全度門檻:兩格,兩格都要明給,**一個預設值都沒有**。

    ``max_stale_days``
        尾段容許落後主日曆幾多個**交易日**。0 = 必須供到主日曆尾日。
    ``max_missing_ratio``
        整段窗口留空日數佔主日曆的比例上限,``0.01`` = 1%。0.0 = 一日都不准留空。
    """

    max_stale_days: int
    max_missing_ratio: float

    def __post_init__(self) -> None:
        try:
            days = int(self.max_stale_days)
        except (TypeError, ValueError):
            raise ContractViolation(
                f"尾段落後門檻要是整數個交易日,收到 {self.max_stale_days!r}"
            ) from None
        if days < 0:
            raise ContractViolation(f"尾段落後門檻不可為負,收到 {self.max_stale_days!r}")
        try:
            ratio = float(self.max_missing_ratio)
        except (TypeError, ValueError):
            raise ContractViolation(
                f"留空比例門檻要是一個比例,收到 {self.max_missing_ratio!r}"
            ) from None
        if not 0.0 <= ratio <= 1.0:
            raise ContractViolation(
                f"留空比例門檻要在 0 與 1 之間(0.01 = 1%),收到 {self.max_missing_ratio!r}"
            )
        object.__setattr__(self, "max_stale_days", days)
        object.__setattr__(self, "max_missing_ratio", ratio)

    def describe(self) -> str:
        """一句講得出這次用的是哪一套門檻——報告與警告都要印得出來。"""
        return (
            f"門檻:尾段落後不過 {self.max_stale_days} 個交易日、"
            f"留空不過 {self.max_missing_ratio:.2%}"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "max_stale_days": int(self.max_stale_days),
            "max_missing_ratio": float(self.max_missing_ratio),
        }


@dataclass(frozen=True, slots=True)
class CompletenessAlert:
    """一條序列超出齊全度門檻的一筆警報。一條序列最多一筆,兩項都超就兩項都寫在裡面。"""

    series: str
    kind: str
    stale_days: int
    last_actual: str
    missing: int
    missing_ratio: float
    calendar_end: str
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "series": self.series,
            "kind": self.kind,
            "stale_days": int(self.stale_days),
            "last_actual": self.last_actual,
            "missing": int(self.missing),
            "missing_ratio": float(self.missing_ratio),
            "calendar_end": self.calendar_end,
            "message": self.message,
        }


def macro_coverage(values: pd.DataFrame) -> pd.DataFrame:
    """逐條序列數清楚:真有讀數 / 前值填補 / 留空各幾多日,首尾在哪一日。"""
    rows: list[dict[str, Any]] = []
    for code, block in values.groupby("series", sort=True):
        status = block["value_status"]
        actual_days = block.loc[status == BAR_ACTUAL, "date"]
        rows.append(
            {
                "series": str(code),
                "actual": int((status == BAR_ACTUAL).sum()),
                "filled": int((status == BAR_FILLED).sum()),
                "missing": int((status == BAR_MISSING).sum()),
                "first_actual": str(actual_days.min()) if not actual_days.empty else "",
                "last_actual": str(actual_days.max()) if not actual_days.empty else "",
            }
        )
    return pd.DataFrame(
        rows, columns=["series", "actual", "filled", "missing", "first_actual", "last_actual"]
    )


def macro_completeness(coverage: pd.DataFrame, calendar: Sequence[str]) -> pd.DataFrame:
    """逐條序列對主日曆核對:尾段落後幾多個交易日、留空佔幾多。

    ``macro_coverage`` 只數清楚三種格各有幾多日;本表多的那兩格
    (``stale_days``、``missing_ratio``)才是「這條序列有沒有靜靜停更」答得出來的
    地方。本函式**不判合格與否**——判斷要門檻,而門檻是參數,見
    ``audit_macro_completeness``。
    """
    days = tuple(sorted({str(day) for day in calendar}))
    if not days:
        raise ContractViolation("主日曆是空的,齊全度無從核對")
    total = len(days)

    rows: list[dict[str, Any]] = []
    for row in coverage.to_dict("records"):
        last_actual = str(row.get("last_actual") or "")
        # 一個真讀數都沒有 = 由主日曆第一日起就在落後,不是「落後零日」
        stale = sum(1 for day in days if day > last_actual) if last_actual else total
        missing = int(row["missing"])
        rows.append(
            {
                "series": str(row["series"]),
                "actual": int(row["actual"]),
                "filled": int(row["filled"]),
                "missing": missing,
                "missing_ratio": missing / total,
                "first_actual": str(row.get("first_actual") or ""),
                "last_actual": last_actual,
                "stale_days": int(stale),
            }
        )
    frame = pd.DataFrame(rows, columns=list(COMPLETENESS_COLUMNS))
    return frame.sort_values("series").reset_index(drop=True)


def audit_macro_completeness(
    completeness: pd.DataFrame,
    calendar: Sequence[str],
    *,
    thresholds: CompletenessThresholds,
) -> tuple[CompletenessAlert, ...]:
    """逐條核對門檻,超出的**一條一筆**講出來;齊全的一條都不報。

    「不誤報」是本函式的合約之一:一條供到主日曆尾日、一日都沒有留空的序列,
    在任何一套門檻下都不會出現在回傳的名單裡。報一堆狼來了,下一個人就會學會
    不看警告——那樣這件事等於沒有做。
    """
    days = tuple(sorted({str(day) for day in calendar}))
    if not days:
        raise ContractViolation("主日曆是空的,齊全度無從核對")
    calendar_end = days[-1]

    alerts: list[CompletenessAlert] = []
    for row in completeness.to_dict("records"):
        code = str(row["series"])
        stale = int(row["stale_days"])
        missing = int(row["missing"])
        ratio = float(row["missing_ratio"])
        last_actual = str(row.get("last_actual") or "")

        kinds: list[str] = []
        reasons: list[str] = []
        if stale > thresholds.max_stale_days:
            kinds.append(ALERT_STALE_TAIL)
            reasons.append(
                f"最後一個真讀數在 {last_actual or '沒有'},"
                f"比主日曆尾日 {calendar_end} 短 {stale} 個交易日"
                f"(門檻 {thresholds.max_stale_days} 日)"
            )
        if ratio > thresholds.max_missing_ratio:
            kinds.append(ALERT_MISSING_RATIO)
            reasons.append(
                f"留空 {missing} 日,佔主日曆 {ratio:.2%}"
                f"(門檻 {thresholds.max_missing_ratio:.2%})"
            )
        if not kinds:
            continue
        alerts.append(
            CompletenessAlert(
                series=code,
                kind="、".join(kinds),
                stale_days=stale,
                last_actual=last_actual,
                missing=missing,
                missing_ratio=ratio,
                calendar_end=calendar_end,
                message=f"{code}:" + ";".join(reasons),
            )
        )
    return tuple(alerts)


# ----------------------------------------------------------------------
# 七、說明檔(兩份範本,全倉唯一)
# ----------------------------------------------------------------------
#
# 每個快照目錄裡那份 ``說明.md`` 是照範本填出來的實例,住在 ``data/``(不入 git)。
# 範本住這裡,不散落——凍結一份快照與看懂一份快照是同一件事的兩面。

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
    """照唯一那份範本填出一個價格快照的說明檔。

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
        balance_line=balance_line(
            universe_tickers=universe_tickers,
            entities=entities,
            alias_dropped=dropped_count,
        ),
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


MACRO_README_TEMPLATE = """# 宏觀數據快照 {snapshot_id}

> 本檔由 `karst.data.macro` 產生,是宏觀快照的說明檔;快照一經凍結即不可改,
> 要改就出新編號。**本快照的序列全部不是可投資對象**,詳見第三節。

## 一、身分

| 項目 | 內容 |
|---|---|
| 快照編號 | `{snapshot_id}` |
| 快照種類 | 宏觀訊號序列(非可投資) |
| 來源 | {source} |
| 抓取時間(UTC) | {fetched_at} |
| 快照日期 | {taken_on} |
| 數據期間 | {window_start} ~ {window_end} |
| 對齊的主日曆 | {calendar_ticker}(交易日 {trading_days} 日) |
| 內容雜湊 | `{content_hash}` |
| 讀數列數 | {rows} |
| 序列數 | {series_count} |
| 讀數精度 | {price_significant_digits} 位有效數字 |

## 二、知情時間

{informed_policy}

## 三、非可投資序列處置

{non_investable_policy}

## 四、缺日處置

{halt_policy}

## 五、歸一化處置

{normalisation_policy}

## 六、序列名冊(連同快照一併凍結)

{registry_table}

## 七、逐條序列的齊全度

下表逐條數清楚:真有讀數幾多日、前值填補幾多日、留空幾多日。**留空不是零**,
驅動器讀到留空即當回望期不夠。

{coverage_table}

## 七之一、齊全度核對(對主日曆;KARST-061)

{completeness_section}

{notes_section}## 八、檔案

| 檔案 | 內容 |
|---|---|
| `series.parquet` | 讀數長表:date、series、value、value_status |
| `calendar.parquet` | 對齊用的主日曆交易日 |
| `registry.parquet` | 序列名冊:代號、來源代號、來源、分層、族、名稱、單位、註記 |
| `manifest.json` | 上表全部欄位的機讀版 |
| `說明.md` | 本檔 |

## 九、與價格快照的關係

本快照**不取代亦不改動**任何價格快照。一次回測引用兩個編號:價格快照決定買賣
什麼、宏觀快照決定怎樣分。兩者對齊同一條主日曆,所以「決策日」在兩邊指同一日。
"""


def render_macro_readme(
    *,
    snapshot_id: str,
    source: str,
    fetched_at: str,
    taken_on: str,
    window_start: str,
    window_end: str,
    calendar_ticker: str,
    trading_days: int,
    content_hash_value: str,
    rows: int,
    registry: pd.DataFrame,
    coverage: pd.DataFrame,
    completeness: pd.DataFrame,
    alerts: Sequence[CompletenessAlert],
    thresholds: CompletenessThresholds,
    calendar_end: str,
    notes: Sequence[str],
) -> str:
    """照唯一那份範本填出一個宏觀快照的說明檔。"""
    registry_header = (
        "| 序列代號 | 來源代號 | 來源 | 分層 | 族 | 名稱 | 單位 | 註記 |\n"
        "|---|---|---|---|---|---|---|---|"
    )
    registry_lines = [
        f"| `{row['series']}` | `{row['symbol']}` | `{row.get('source', '')}` |"
        f" {row['tier']} | {row['family']} |"
        f" {row['label']} | {row['unit']} | {row['note'] or '—'} |"
        for row in registry.to_dict("records")
    ]
    coverage_header = "| 序列代號 | 真有讀數 | 前值填補 | 留空 | 首個讀數 | 最後讀數 |\n|---|---|---|---|---|---|"
    coverage_lines = [
        f"| `{row['series']}` | {row['actual']} | {row['filled']} | {row['missing']} |"
        f" {row['first_actual'] or '—'} | {row['last_actual'] or '—'} |"
        for row in coverage.to_dict("records")
    ]
    notes_section = ""
    if notes:
        notes_section = "## 七之二、註記\n\n" + "\n".join(f"- {note}" for note in notes) + "\n\n"
    return MACRO_README_TEMPLATE.format(
        snapshot_id=snapshot_id,
        source=source,
        fetched_at=fetched_at,
        taken_on=taken_on,
        window_start=window_start,
        window_end=window_end,
        calendar_ticker=calendar_ticker,
        trading_days=trading_days,
        content_hash=content_hash_value,
        rows=rows,
        series_count=len(registry),
        price_significant_digits=PRICE_SIGNIFICANT_DIGITS,
        informed_policy=MACRO_INFORMED_POLICY,
        non_investable_policy=NON_INVESTABLE_POLICY,
        halt_policy=MACRO_HALT_POLICY,
        normalisation_policy=MACRO_NORMALISATION_POLICY,
        registry_table="\n".join([registry_header, *registry_lines]),
        coverage_table="\n".join([coverage_header, *coverage_lines]),
        completeness_section=render_macro_completeness(
            completeness, alerts, thresholds, calendar_end
        ),
        notes_section=notes_section,
    )


def render_macro_completeness(
    completeness: pd.DataFrame,
    alerts: Sequence[CompletenessAlert],
    thresholds: CompletenessThresholds,
    calendar_end: str,
) -> str:
    """說明檔第七之一節:逐條序列對主日曆的核對結果,連這次用的是哪一套門檻。

    第七節那張表數的是「有幾多日」,這一節答的是「夠不夠新」——**尾段短過主日曆
    即等於那條訊號已經停止講話**,而那件事在第七節的三個數字裡看不出來
    (停更之後每一日都算「留空」,與中段有洞的序列長得一模一樣)。
    """
    header = (
        "| 序列代號 | 尾段落後(交易日) | 最後真讀數 | 留空 | 留空比例 | 核對結果 |\n"
        "|---|---|---|---|---|---|"
    )
    flagged = {alert.series: alert for alert in alerts}
    lines = []
    for row in completeness.to_dict("records"):
        code = str(row["series"])
        alert = flagged.get(code)
        verdict = f"**超出門檻({alert.kind})**" if alert is not None else "合格"
        lines.append(
            f"| `{code}` | {int(row['stale_days'])} | {row['last_actual'] or '—'} |"
            f" {int(row['missing'])} | {float(row['missing_ratio']):.2%} | {verdict} |"
        )

    if alerts:
        verdict_lines = [
            f"**{len(alerts)} 條序列超出門檻**({thresholds.describe()};"
            f"主日曆尾日 {calendar_end}):",
            "",
            *(f"- {alert.message}" for alert in alerts),
            "",
            "尾段短過主日曆,即等於那條訊號由某一日起**已經停止講話**:對齊時尾段照停牌"
            "處置留空,驅動器讀到留空即當「數據不足」退回熱身期權重——掃描照跑、報告照出、"
            "成績表照畫,一個錯都不會報(假設 A-008 已於 2026-08-29 推翻)。",
        ]
    else:
        verdict_lines = [
            f"**{len(completeness)} 條序列全部合格**({thresholds.describe()};"
            f"主日曆尾日 {calendar_end})。",
        ]
    return "\n".join([*verdict_lines, "", header, *lines])


# ----------------------------------------------------------------------
# 八、落地與等價重用
# ----------------------------------------------------------------------


def _write_dir(
    root: str | Path,
    snapshot_id: str,
    *,
    tables: dict[str, pd.DataFrame],
    manifest: dict[str, Any],
    readme: str,
) -> Path:
    """原子寫入一個快照目錄,回傳它的路徑。兩種快照同一份實作。

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
        for name, frame in tables.items():
            frame.to_parquet(staging / name, engine="pyarrow", index=False)
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


def _calendar_frame(calendar: Sequence[str]) -> pd.DataFrame:
    return pd.DataFrame({"date": [str(day) for day in calendar]})


def _readme_of(directory: Path) -> str:
    """沿用一份已凍結的快照時,說明檔照它原本那份讀回來——**不重新填一次**。

    重填會用今日的範本蓋掉當日那份,而快照一經凍結即不可改(D-026 第 3 條)。
    舊快照缺說明檔即回空串:那是它當日的事實,不在這裡補一份出來。
    """
    path = directory / README_FILE
    return path.read_text(encoding="utf-8") if path.exists() else ""


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
    """原子寫入一個價格快照目錄,回傳它的路徑。"""
    return _write_dir(
        root,
        snapshot_id,
        tables={
            PRICES_FILE: canonical_prices(prices),
            CALENDAR_FILE: _calendar_frame(calendar),
            UNIVERSE_FILE: canonical_universe(universe),
        },
        manifest=manifest,
        readme=readme,
    )


def _frames_equivalent(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    shape: _Shape,
    rtol: float,
) -> bool:
    """兩張主表是不是「同一批數據」——形狀逐格相同,數值在相對容差內相同。

    形狀那半要求**逐位相同**,不留餘地:同一組日期、同一組主鍵、同一個排序,
    每一格的身分(actual / filled / missing)也要一樣。少一日、多一隻股、
    停牌填補的位置不同,都是真的不一樣,不是抓取雜訊。
    """
    if len(left) != len(right):
        return False
    for column in shape.exact_columns:
        if not left[column].equals(right[column]):
            return False
    return all(
        values_equivalent(
            left[column].to_numpy("float64"), right[column].to_numpy("float64"), rtol=rtol
        )
        for column in shape.numeric_columns
    )


def price_frames_equivalent(
    left: pd.DataFrame, right: pd.DataFrame, *, rtol: float = EQUIVALENCE_RTOL
) -> bool:
    """兩張日線長表是不是「同一批數據」。"""
    return _frames_equivalent(left, right, shape=PRICE_SHAPE, rtol=rtol)


def _find_equivalent(
    root: str | Path,
    *,
    shape: _Shape,
    core: dict[str, Any],
    data: pd.DataFrame,
    calendar: Sequence[str],
    roster: pd.DataFrame,
    rtol: float,
) -> tuple[Path, dict[str, Any]] | None:
    """在快取根裡找一份與這批新數據等價的已凍結快照;找不到回 ``None``。

    這是「重抓不多一份副本」(KARST-033)真正靠的那一關。同一個窗口抓兩次,
    已調整價會在 float32 的最後幾個 bit 上飄(見 ``normalise``),四捨五入壓得住
    雜訊的量級、壓不住「剛好跨過格線」,所以凍結之前要親自問一句:這批數,
    是不是已經凍過了?

    四關全過才算等價,次序由平到貴:

      1. ``core`` 逐項相同——同一個來源、同一個窗口、同一條主日曆、同一套處置與
         同一個歸一化精度。這一關只讀 manifest.json,把絕大多數候選擋在門外,
         也保證舊規矩凍下來的快照永遠不會被誤認作等價。
      2. 列數相同。
      3. 主日曆與名冊表逐位相同(名冊用內容雜湊比,不逐格比)。
      4. 主表形狀逐格相同、數值在 ``rtol`` 內相同。

    找到就沿用它——**原編號、原檔案、原抓取時間一概不動**(D-026 第 3 條
    「舊快照永不改動」)。
    """
    root = Path(root)
    if not root.is_dir():
        return None

    wanted_data = shape.canonical_data(data)
    wanted_calendar = tuple(str(day) for day in calendar)
    wanted_roster = content_hash(shape.canonical_roster(roster))

    for directory in sorted(
        entry for entry in root.iterdir() if entry.is_dir() and not entry.name.startswith(".")
    ):
        manifest_path = directory / MANIFEST_FILE
        if not manifest_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue  # 半截或壞掉的快照不當候選,靜靜略過
        if manifest.get("core") != core:
            continue
        if int(manifest.get("rows", -1)) != len(wanted_data):
            continue
        try:
            frozen_calendar = tuple(
                pd.read_parquet(directory / CALENDAR_FILE, engine="pyarrow")["date"].astype(str)
            )
            frozen_roster = shape.canonical_roster(
                pd.read_parquet(directory / shape.roster_file, engine="pyarrow")
            )
            frozen_data = shape.canonical_data(
                pd.read_parquet(directory / shape.data_file, engine="pyarrow")
            )
        except (OSError, ValueError, KeyError):
            continue
        if frozen_calendar != wanted_calendar:
            continue
        if content_hash(frozen_roster) != wanted_roster:
            continue
        if not _frames_equivalent(frozen_data, wanted_data, shape=shape, rtol=rtol):
            continue
        return directory, manifest
    return None


def find_equivalent_snapshot(
    root: str | Path,
    *,
    core: dict[str, Any],
    prices: pd.DataFrame,
    calendar: Sequence[str],
    universe: pd.DataFrame,
    rtol: float = EQUIVALENCE_RTOL,
) -> tuple[Path, dict[str, Any]] | None:
    """在快取根裡找一份與這批新日線等價的已凍結價格快照。"""
    return _find_equivalent(
        root,
        shape=PRICE_SHAPE,
        core=core,
        data=prices,
        calendar=calendar,
        roster=universe,
        rtol=rtol,
    )


# ----------------------------------------------------------------------
# 九、唯一入口
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PriceFreezeDetail:
    """價格快照凍結時那幾步各自留下的痕跡,交回呼叫者砌成果單。"""

    universe_rows: tuple[dict[str, Any], ...]
    entity_ids: tuple[int, ...]
    alias_dropped: tuple[str, ...]
    alias_verdicts: tuple[AliasVerdict, ...]


@dataclass(frozen=True, slots=True)
class MacroFreezeDetail:
    """宏觀快照凍結時齊全度核對的結果,交回呼叫者砌成果單。"""

    thresholds: CompletenessThresholds
    alerts: tuple[CompletenessAlert, ...]


@dataclass(frozen=True, slots=True)
class FrozenSnapshot:
    """凍結一次的成果單:編號、內容雜湊、落點、說明檔,以及那一種快照自己的痕跡。"""

    kind: str
    snapshot_id: str
    content_hash: str
    source: str
    fetched_at: str
    taken_on: str
    window_start: str
    window_end: str
    calendar_ticker: str
    trading_days: int
    rows: int
    path: str
    manifest: dict[str, Any]
    readme: str
    notes: tuple[str, ...]
    reused: bool
    detail: PriceFreezeDetail | MacroFreezeDetail


@dataclass(frozen=True, slots=True, eq=False)
class PriceFreezePlan:
    """凍一個價格快照要的全部備料。

    交進來的東西只有一種身分:**來源適配器搬進來那批數**,加上「這批數是誰、哪一段
    窗口、對哪一條主日曆」。之後六步全部由凍結模組做——別名閘、登記實體、解析實體
    編號、對齊、三數等式、說明檔、寫檔、簽章登記,呼叫者一步都不重覆。
    """

    #: 來源名(記入快照,亦入內容雜湊)
    source: str
    #: 來源是不是交已調整價(入內容雜湊)
    auto_adjust: bool
    fetched_at: str
    taken_on: str
    window_start: str
    window_end: str
    calendar_ticker: str
    #: 主日曆:由來源那批數定出來,凍結模組不再自己算一次
    calendar: tuple[str, ...]
    #: 已歸一化、未解析實體的日線長表(date / ticker / 開高低收量)
    bars: pd.DataFrame
    #: 入口收到的宇宙名單(別名閘之前那一份)
    members: tuple[UniverseMember, ...]
    #: 入口收到的代號(三數等式的第一個數,亦即登記那一列的宇宙名單)
    universe_tickers: tuple[str, ...]
    cik_map: dict[str, str]
    #: 代號→生效訖(留空即未結束),只餵別名閘規則第一關
    anchor_valid_to: dict[str, str]
    #: 呼叫者交來的註記;凍結模組會在後面接上自己見到的事
    notes: tuple[str, ...]
    root: str | Path


@dataclass(frozen=True, slots=True, eq=False)
class MacroFreezePlan:
    """凍一個宏觀快照要的全部備料。

    與價格那份的分別只在**沒有實體那一段**:宏觀序列不是可投資對象,不入 entity 表、
    不佔實體編號,故此別名閘與解析實體編號兩步在它身上根本不存在(理由見 ``macro``
    開頭第一節)。它那一步對應的是齊全度核對(KARST-061)。
    """

    source: str
    fetched_at: str
    taken_on: str
    window_start: str
    window_end: str
    calendar_ticker: str
    #: 對齊用的主日曆:價格快照那一條,由呼叫者交來
    calendar: tuple[str, ...]
    #: 已歸一化、未對齊的讀數長表(date / series / value)
    values: pd.DataFrame
    #: 連同快照一併凍結的序列名冊(已是規範形態)
    registry: pd.DataFrame
    #: 名冊上那幾條的內部代號,次序即名冊次序
    series_codes: tuple[str, ...]
    #: 齊全度門檻:必給,沒有預設值
    thresholds: CompletenessThresholds
    notes: tuple[str, ...]
    root: str | Path


def freeze_snapshot(
    store: DefinitionStore, plan: PriceFreezePlan | MacroFreezePlan
) -> FrozenSnapshot:
    """把一批數凍成一個有編號的快照——全倉唯一那條路。

    六步的次序寫死(見本檔開頭第二節),兩種快照共用後半段:算內容雜湊、問一句
    「這批數是不是已經凍過了」、取編號、砌 manifest、填說明檔、原子寫檔、經唯一
    入口登記簽章。**登記表回的編號與這裡算的對不上即當場拋錯**——兩邊同一條算法,
    對不上即是庫壞了。
    """
    if isinstance(plan, PriceFreezePlan):
        return _freeze_price(store, plan)
    if isinstance(plan, MacroFreezePlan):
        return _freeze_macro(store, plan)
    raise ContractViolation(  # pragma: no cover - 型別註明已經講死只有兩種
        f"凍結模組不認得這種備料:{type(plan).__name__}"
    )


def _register(
    store: DefinitionStore,
    *,
    source: str,
    taken_on: str,
    digest: str,
    path: Path,
    roster_keys: Sequence[str],
    snapshot_id: str,
    kind_label: str,
) -> None:
    """第六步:經唯一入口登記,蓋簽章(KARST-087),再對一次編號。"""
    registered = store.register_snapshot(
        source=source,
        taken_on=taken_on,
        content_hash=digest,
        path=path.as_posix(),
        universe=roster_keys,
    )
    if registered != snapshot_id:  # pragma: no cover - 兩邊同一條算法,對不上即是庫壞了
        raise ContractViolation(
            f"{kind_label}編號對不上:凍結模組算出 {snapshot_id},登記表回 {registered}"
        )


def _freeze_price(store: DefinitionStore, plan: PriceFreezePlan) -> FrozenSnapshot:
    notes = list(plan.notes)
    root = plan.root
    calendar = plan.calendar
    bars = plan.bars

    # 第一步:同實體別名那道閘(KARST-084)。行在登記實體**之前**——兩個代號錨到同
    # 一個實體,登記那一層只會回同一個實體編號,兩條價格序列撞在一起而無人出聲
    # (KARST-083 的 BBT/TFC、EQR/VMRK 就是這樣靜靜決定的)。
    members, alias_dropped, alias_verdicts = apply_alias_gate(
        plan.members,
        bars=bars,
        cik_map=plan.cik_map,
        anchor_valid_to=plan.anchor_valid_to,
        notes=notes,
    )
    if alias_dropped:
        bars = bars.loc[~bars["ticker"].isin(set(alias_dropped))].reset_index(drop=True)
        if bars.empty:
            raise ContractViolation(
                f"同實體別名閘剔走 {len(alias_dropped)} 個代號之後,這批數據一列都不剩"
            )

    # 第二、三步:登記實體與代號生效期,把代號按日解析成實體編號,再對齊主日曆
    universe_frame = ensure_entities(
        store, members, bars=bars, cik_map=plan.cik_map, notes=notes
    )
    aligned = align_to_calendar(resolve_entity_ids(store, bars), calendar)

    core = snapshot_core(
        source=plan.source,
        window_start=plan.window_start,
        window_end=plan.window_end,
        calendar_ticker=plan.calendar_ticker,
        auto_adjust=plan.auto_adjust,
    )
    digest = snapshot_digest(aligned, calendar, universe_frame, core)
    day = plan.taken_on

    # numpy 的整數不入 JSON,一律先換回 Python 的 int
    universe_rows = [
        {key: (int(value) if key == "entity_id" else str(value)) for key, value in row.items()}
        for row in universe_frame.to_dict("records")
    ]
    entity_ids = tuple(sorted(int(row["entity_id"]) for row in universe_rows))

    # 第五步之前:等價重用(KARST-033)。凍結之前先問一句「這批數是不是已經凍過了」。
    existing = find_equivalent_snapshot(
        root, core=core, prices=aligned, calendar=calendar, universe=universe_frame
    )
    if existing is not None:
        path, manifest = existing
        snapshot_id = str(manifest["snapshot_id"])
        digest = str(manifest["content_hash"])
        day = str(manifest["taken_on"])
        reused = True
        readme = _readme_of(path)
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
            "source": plan.source,
            "fetched_at": plan.fetched_at,
            "taken_on": day,
            "window_start": plan.window_start,
            "window_end": plan.window_end,
            "calendar_ticker": plan.calendar_ticker,
            "trading_days": len(calendar),
            "rows": int(len(aligned)),
            "entities": len(entity_ids),
            # 第四步:三數等式(KARST-084)。宇宙表代號數 = 實體數 + 剔除數。
            # 對得上就證明沒有一條代號序列被靜靜蓋走;`karst verify` 核的就是這一條。
            "universe_tickers": len(plan.universe_tickers),
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
            source=plan.source,
            fetched_at=plan.fetched_at,
            taken_on=day,
            window_start=plan.window_start,
            window_end=plan.window_end,
            calendar_ticker=plan.calendar_ticker,
            trading_days=len(calendar),
            content_hash=digest,
            rows=int(len(aligned)),
            entities=len(entity_ids),
            universe_tickers=len(plan.universe_tickers),
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

    _register(
        store,
        source=plan.source,
        taken_on=day,
        digest=digest,
        path=path,
        roster_keys=plan.universe_tickers,
        snapshot_id=snapshot_id,
        kind_label="快照",
    )

    return FrozenSnapshot(
        kind=SNAPSHOT_KIND_PRICE,
        snapshot_id=snapshot_id,
        content_hash=digest,
        source=plan.source,
        fetched_at=str(manifest["fetched_at"]),
        taken_on=day,
        window_start=plan.window_start,
        window_end=plan.window_end,
        calendar_ticker=plan.calendar_ticker,
        trading_days=len(calendar),
        rows=int(len(aligned)),
        path=path.as_posix(),
        manifest=manifest,
        readme=readme,
        notes=tuple(notes),
        reused=reused,
        detail=PriceFreezeDetail(
            universe_rows=tuple(universe_rows),
            entity_ids=entity_ids,
            alias_dropped=alias_dropped,
            alias_verdicts=alias_verdicts,
        ),
    )


def _freeze_macro(store: DefinitionStore, plan: MacroFreezePlan) -> FrozenSnapshot:
    notes = list(plan.notes)
    root = plan.root
    days = plan.calendar

    # 第三步:對齊主日曆(宏觀序列不是實體,沒有解析實體編號那一步)
    aligned = align_macro_to_calendar(plan.values, days)

    # 第四步:齊全度核對(KARST-061)——價格那邊的三數等式在宏觀這邊的對應物
    coverage = macro_coverage(aligned)
    completeness = macro_completeness(coverage, days)
    alerts = audit_macro_completeness(completeness, days, thresholds=plan.thresholds)

    if alerts:
        notes.append(
            f"齊全度核對:{len(alerts)} 條序列超出門檻({plan.thresholds.describe()})。"
            "尾段短過主日曆即等於那條訊號已經停止講話,而掃描與報告一個錯都不會報"
            "(假設 A-008)"
        )
        notes.extend(f"齊全度警報 {alert.message}" for alert in alerts)
    else:
        notes.append(
            f"齊全度核對:{len(completeness)} 條序列全部合格({plan.thresholds.describe()})"
        )

    for row in coverage.to_dict("records"):
        if int(row["missing"]) > 0:
            notes.append(
                f"{row['series']} 在主日曆上有 {row['missing']} 日留空"
                f"(真有讀數 {row['actual']} 日、前值填補 {row['filled']} 日;"
                f"最後一個讀數在 {row['last_actual'] or '沒有'});"
                "留空的日子驅動器會當「數據不足」退回熱身期權重,不當零"
            )

    registry = plan.registry
    core = macro_core(
        source=plan.source,
        window_start=plan.window_start,
        window_end=plan.window_end,
        calendar_ticker=plan.calendar_ticker,
        series_codes=plan.series_codes,
    )
    digest = macro_digest(aligned, days, registry, core)
    day = plan.taken_on

    existing = _find_equivalent(
        root,
        shape=MACRO_SHAPE,
        core=core,
        data=aligned,
        calendar=days,
        roster=registry,
        rtol=EQUIVALENCE_RTOL,
    )
    if existing is not None:
        path, manifest = existing
        snapshot_id = str(manifest["snapshot_id"])
        digest = str(manifest["content_hash"])
        day = str(manifest["taken_on"])
        reused = True
        readme = _readme_of(path)
        notes.append(
            f"這次抓取與已凍結的宏觀快照 {snapshot_id} 等價(全部讀數相對差不過 "
            f"{EQUIVALENCE_RTOL:.0e}),沿用原編號與原檔案,不另存一份副本(D-028 第 2 條)"
        )
    else:
        reused = False
        snapshot_id = store.snapshot_id_for(day, digest)
        manifest = {
            "snapshot_id": snapshot_id,
            "snapshot_kind": SNAPSHOT_KIND_MACRO,
            "source": plan.source,
            "fetched_at": plan.fetched_at,
            "taken_on": day,
            "window_start": plan.window_start,
            "window_end": plan.window_end,
            "calendar_ticker": plan.calendar_ticker,
            "trading_days": len(days),
            "rows": int(len(aligned)),
            "series": list(plan.series_codes),
            "content_hash": digest,
            "core": core,
            "informed_policy": MACRO_INFORMED_POLICY,
            "non_investable_policy": NON_INVESTABLE_POLICY,
            "halt_policy": MACRO_HALT_POLICY,
            "normalisation_policy": MACRO_NORMALISATION_POLICY,
            "registry": registry.to_dict("records"),
            "coverage": [
                {key: (int(value) if key in {"actual", "filled", "missing"} else str(value))
                 for key, value in row.items()}
                for row in coverage.to_dict("records")
            ],
            # 齊全度核對(KARST-061):逐條的數、這次用的門檻、超出門檻的那幾條。
            # 三樣一齊落在已凍結的快照裡,所以「當日核對過沒有、用的是哪一套門檻」
            # 事後查得回,不必靠人記得。
            "completeness_thresholds": plan.thresholds.as_dict(),
            "completeness": [
                {
                    key: (
                        int(value)
                        if key in {"actual", "filled", "missing", "stale_days"}
                        else float(value)
                        if key == "missing_ratio"
                        else str(value)
                    )
                    for key, value in row.items()
                }
                for row in completeness.to_dict("records")
            ],
            "completeness_alerts": [alert.as_dict() for alert in alerts],
            "notes": notes,
        }
        readme = render_macro_readme(
            snapshot_id=snapshot_id,
            source=plan.source,
            fetched_at=plan.fetched_at,
            taken_on=day,
            window_start=plan.window_start,
            window_end=plan.window_end,
            calendar_ticker=plan.calendar_ticker,
            trading_days=len(days),
            content_hash_value=digest,
            rows=int(len(aligned)),
            registry=registry,
            coverage=coverage,
            completeness=completeness,
            alerts=alerts,
            thresholds=plan.thresholds,
            calendar_end=days[-1],
            notes=notes,
        )
        path = _write_dir(
            root,
            snapshot_id,
            tables={
                SERIES_FILE: canonical_macro(aligned),
                CALENDAR_FILE: _calendar_frame(days),
                REGISTRY_FILE: registry,
            },
            manifest=manifest,
            readme=readme,
        )

    _register(
        store,
        source=plan.source,
        taken_on=day,
        digest=digest,
        path=path,
        roster_keys=list(plan.series_codes),
        snapshot_id=snapshot_id,
        kind_label="宏觀快照",
    )

    return FrozenSnapshot(
        kind=SNAPSHOT_KIND_MACRO,
        snapshot_id=snapshot_id,
        content_hash=digest,
        source=plan.source,
        fetched_at=str(manifest["fetched_at"]),
        taken_on=day,
        window_start=plan.window_start,
        window_end=plan.window_end,
        calendar_ticker=plan.calendar_ticker,
        trading_days=len(days),
        rows=int(len(aligned)),
        path=path.as_posix(),
        manifest=manifest,
        readme=readme,
        notes=tuple(notes),
        reused=reused,
        detail=MacroFreezeDetail(thresholds=plan.thresholds, alerts=alerts),
    )
