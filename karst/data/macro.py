"""宏觀訊號序列的接入(KARST-040)。

因子輪動的驅動器至今只看得見四隻因子 ETF 與大市自身的收價
(``karst.strategies.factor_rotation`` 的 ``EXTERNAL_DATA`` 是空的)。本檔開的是
另一道門:VIX 與其期限結構、美債息率與曲線斜度、信用利差、聯邦基金利率預期,
按同一套規矩(來源適配器 → 對齊主日曆 → 凍結成有編號的快照)入庫,好讓驅動器
用價格以外的訊號決定四格怎樣分。

# 一、非可投資序列的處置(本檔最要緊的一條)

宏觀序列**不是可投資對象**。單一定義庫的 ``entity`` 表只收得三種實體
(``company`` / ``etf`` / ``basket``,見 schema 的 CHECK),而且上市公司必須以
SEC CIK 為錨;``^VIX`` 一類指數代號既沒有 CIK,亦根本不是可以持有的東西——
它連「一股」都不存在,買不到、賣不到、更沒有除權除息。

所以本檔**刻意不把宏觀序列登記成實體**,處置寫死如下:

  1. 宏觀序列不入 ``entity`` 表、不佔實體編號、不入代號生效期映射表。
  2. 宏觀序列不入價格快照的 ``prices.parquet``,即**永遠不會出現在價格面板裡**。
     引擎的目標比重表以實體編號為欄,面板裡沒有它,就結構性地落不到注在它身上
     ——這不是靠自律,是表達不出來。
  3. 宏觀序列另存一套**宏觀快照**(``data/macro_snapshots/<編號>/``),主鍵是
     **序列代號**(``VIX``、``UST_10Y`` 一類的內部代號),不是實體編號。
  4. 宏觀快照經同一個單一定義庫登記(``store.register_snapshot``),所以它一樣
     **有編號、可引用、可查重**,編號算法與價格快照同一條(日期 + 內容雜湊前
     12 位,D-026 第 3 條)。兩者靠 ``source`` 分得開:價格是 ``yfinance``,
     宏觀是 ``yfinance-macro``。

有兩條序列(``HY_ETF`` = HYG、``IG_ETF`` = LQD)背後其實是可投資的 ETF。它們在
這裡**只作訊號來源**,一樣不入實體表、不入價格面板:要真的持有它們,就要另行
寫進宇宙名單、走價格那一條管線。同一個東西在兩條管線裡各存一份是刻意的分工,
不是重覆——一邊是「可以買的東西」,一邊是「用來判斷的數」。

# 二、知情時間(D-021 第 3 條)

本檔全部序列的知情時間一律是**當日收市後可得**,與價格同一級。收市價一經公布
即為已知,故決策日當日的收市讀數用得着;成交照舊在**決策日之後那一根 K 線的
開價**。驅動器看得見的那一段由 ``macro.loc[:決策日]`` 切出來,最後一行就是決策
日——偷看之後的日子在這裡連表達都表達不出,與價格驅動器同一個做法。

# 三、來源:全部免費,一個鑰匙都不要

FRED 的 API 要申請鑰匙(``fredapi`` / ``pandas-datareader`` 皆然),CME 的
FedWatch 本身亦不是免費數據。所以本檔**一條 FRED 序列都不用**,全部改用免費
來源,亦因此**不必加任何新套件**——``yfinance`` 早已是本倉的依賴,Cboe 那條
只用標準庫的 ``urllib``。逐項替代與代價寫在 ``MACRO_SERIES`` 每一條的 ``note`` 裡。

現時**兩個來源並存**,逐條序列各自寫明由哪一個來源取:

  * ``yfinance-macro`` —— 息率、期貨、外匯、ETF 那十二條。
  * ``cboe-macro`` —— VIX 與 VIX_3M 兩條,取 Cboe 官方免費歷史檔
    (``cdn.cboe.com/api/global/us_indices/daily_prices/<代號>_History.csv``,
    無鑰匙、無登記、無配額)。

**為什麼 VIX 那兩條要換來源(KARST-058)。** 2026-08-28 實測發現 yfinance 的
``^VIX3M`` 只去到 2026-07-17,而 ``^VIX`` 去到 2026-08-26——期限結構那一條在尾段
有約五個星期沒有數,期限結構驅動器因此每日都判「數據不足」。用戶 2026-08-28 追問
(原話「VIX should have index which everyday is moving? Why only update to Jul.
This is weird」):指數本身 Cboe 每個交易日照常發布,停更的是免費轉發那一層,不是
指數。2026-08-29 實測 Cboe 官方檔兩條都去到 2026-08-27(最近交易日),故 VIX 與
VIX_3M 改由 Cboe 直取;VIX 一併改是為了兩條同源——期限結構是相除出來的比率,分子
分母來自同一份官方檔才不會因為兩邊的修訂節奏不同而在比率上造出假訊號。
``^VXV``(VIX 三個月的舊代號)已經抓不到,故不用。

**序列代號不變,只換來源代號**(D-026 第 7 條適配器形態要換來的正是這件事):
``VIX`` 與 ``VIX_3M`` 這兩個內部代號一個字都沒有改,驅動器、快照結構、報告全部
不用動;改的只是名冊上的 ``symbol``(``^VIX`` → ``VIX``、``^VIX3M`` → ``VIX3M``)
與新增的 ``source`` 一欄。名冊連同快照一併凍結,所以「這條讀數當日由哪個來源取」
在已凍結的快照裡查得回。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

import numpy as np
import pandas as pd

from ..batches import content_hash
from ..errors import ContractViolation
from ..models import as_date
from ..store import DefinitionStore
from .calendar import BAR_ACTUAL, BAR_FILLED, BAR_MISSING, FFILL_LIMIT
from .errors import DataFetchFailed, SnapshotBroken
from .manifest import canonical_json
from .normalise import (
    EQUIVALENCE_POLICY_ID,
    EQUIVALENCE_RTOL,
    NORMALISATION_POLICY_ID,
    PRICE_SIGNIFICANT_DIGITS,
    round_significant,
)

# 單一快取根(D-026 第 5 條的同一個道理):宏觀快照只住這一處,與價格快照分家。
DEFAULT_MACRO_ROOT = Path("data") / "macro_snapshots"

SERIES_FILE = "series.parquet"
CALENDAR_FILE = "calendar.parquet"
REGISTRY_FILE = "registry.parquet"
MANIFEST_FILE = "manifest.json"
README_FILE = "說明.md"

# 統一輸出:一列一條序列一日。``value_status`` 與價格的 ``bar_status`` 同義同值。
SERIES_COLUMNS: tuple[str, ...] = ("date", "series", "value", "value_status")
RAW_COLUMNS: tuple[str, ...] = ("date", "series", "value")

MACRO_SOURCE_NAME = "yfinance-macro"
CBOE_SOURCE_NAME = "cboe-macro"
# 兩個來源並存時,快照登記的來源名。名字本身講得出「哪幾條由誰取」的分工。
COMPOSITE_SOURCE_NAME = "cboe+yfinance-macro"

# Cboe 官方免費歷史檔(KARST-058)。無鑰匙、無登記、無配額;欄位固定為
# DATE、OPEN、HIGH、LOW、CLOSE,日期是 MM/DD/YYYY。
CBOE_HISTORY_URL = (
    "https://cdn.cboe.com/api/global/us_indices/daily_prices/{symbol}_History.csv"
)

# 序列分層(用戶 2026-08-28 裁定):
#   第一層 —— 可以做驅動器參數格的四項。
#   第二層 —— **只作對照列於成績表,不作驅動器參數格**。
TIER_DRIVER = "第一層"
TIER_REFERENCE = "第二層"

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


# ----------------------------------------------------------------------
# 序列名冊
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MacroSeries:
    """名冊上的一條宏觀序列。

    ``code`` 是**內部序列代號**,亦即快照與驅動器談的那個名;``symbol`` 是它在
    來源那邊叫什麼,``source`` 是「哪一個適配器負責取它」。三者分開,日後同一條
    序列換來源(KARST-058 就是這樣把 VIX 那兩條由 yfinance 換去 Cboe 官方檔)
    只需改 ``symbol`` 與 ``source``,驅動器、快照結構、報告一個字都不用改——
    這正是 D-026 第 7 條適配器形態要換來的那件事。
    """

    code: str
    symbol: str
    tier: str
    family: str
    label: str
    unit: str
    note: str = ""
    source: str = MACRO_SOURCE_NAME


MACRO_SERIES: tuple[MacroSeries, ...] = (
    # ---- 第一層之(1):VIX 及期限結構 ----
    MacroSeries(
        code="VIX",
        symbol="VIX",
        source=CBOE_SOURCE_NAME,
        tier=TIER_DRIVER,
        family="波動率",
        label="CBOE 波動率指數(30 日)",
        unit="年化波動率點數",
        note=(
            "免費、無鑰匙。恐慌水平的業界標準讀數。"
            "KARST-058 起由 Cboe 官方歷史檔直取(舊來源代號 ^VIX / yfinance);"
            "與 VIX_3M 同源,免得比率的分子分母來自兩邊而造出假訊號。"
        ),
    ),
    MacroSeries(
        code="VIX_3M",
        symbol="VIX3M",
        source=CBOE_SOURCE_NAME,
        tier=TIER_DRIVER,
        family="波動率",
        label="CBOE 波動率指數(3 個月)",
        unit="年化波動率點數",
        note=(
            "與 VIX 相除即期限結構(VIX/VIX_3M > 1 = 倒掛 = 即市恐慌高於遠期)。"
            "KARST-058 起由 Cboe 官方歷史檔直取(舊來源代號 ^VIX3M / yfinance):"
            "免費轉發那一層自 2026-07-17 起停更,指數本身 Cboe 每個交易日照常發布。"
            "舊代號 ^VXV 已抓不到,不用。"
        ),
    ),
    # ---- 第一層之(2):信用利差 ----
    MacroSeries(
        code="HY_ETF",
        symbol="HYG",
        tier=TIER_DRIVER,
        family="信用",
        label="iShares 高收益公司債 ETF",
        unit="已調整收市價",
        note=(
            "FRED 的高收益 OAS(BAMLH0A0HYM2)要 API 鑰匙,故改用免費替代:"
            "HY_ETF ÷ IG_ETF 的比率作信用利差的反向代理——比率跌 = 高收益跑輸 = 利差擴闊。"
            "代價明記:這是價格比率不是利差本身,含存續期與流動性差異,只讀方向不讀水平。"
        ),
    ),
    MacroSeries(
        code="IG_ETF",
        symbol="LQD",
        tier=TIER_DRIVER,
        family="信用",
        label="iShares 投資級公司債 ETF",
        unit="已調整收市價",
        note="與 HY_ETF 相除作信用利差代理的分母。",
    ),
    # ---- 第一層之(3):美債息率與曲線斜度 ----
    MacroSeries(
        code="UST_3M",
        symbol="^IRX",
        tier=TIER_DRIVER,
        family="息率",
        label="13 週美國國庫券息率",
        unit="百分點",
        note=(
            "曲線斜度的短端。用戶裁定可用它替代 2 年期——FRED 的 DGS2 要鑰匙。"
            "代價明記:3 個月對 2 年在減息預期期間會有分別,斜度的**絕對水平**因此"
            "與市場慣講的 10 年減 2 年不同,只讀方向與相對變化。"
        ),
    ),
    MacroSeries(
        code="UST_5Y",
        symbol="^FVX",
        tier=TIER_DRIVER,
        family="息率",
        label="5 年期美國國債息率",
        unit="百分點",
    ),
    MacroSeries(
        code="UST_10Y",
        symbol="^TNX",
        tier=TIER_DRIVER,
        family="息率",
        label="10 年期美國國債息率",
        unit="百分點",
        note="曲線斜度的長端;亦是息率趨勢那一條。",
    ),
    MacroSeries(
        code="UST_30Y",
        symbol="^TYX",
        tier=TIER_DRIVER,
        family="息率",
        label="30 年期美國國債息率",
        unit="百分點",
    ),
    # ---- 第一層之(4):聯邦基金利率預期的免費替代 ----
    MacroSeries(
        code="FF_FUTURE",
        symbol="ZQ=F",
        tier=TIER_DRIVER,
        family="政策利率",
        label="30 日聯邦基金期貨(近月連續)",
        unit="報價(100 − 隱含利率)",
        note=(
            "**FedWatch 本身不免費**(CME 的 FedWatch 工具不提供免費程式介面),"
            "FRED 的有效聯邦基金利率 DFF 亦要 API 鑰匙。故取免費替代:聯邦基金期貨報價。"
            "隱含利率 = 100 − 報價,所以**報價升 = 預期減息**。"
            "代價明記:近月連續合約會在轉倉時跳一格,只讀方向不讀水平。"
        ),
    ),
    # ---- 第二層:只作對照列於成績表,不作驅動器參數格(用戶 2026-08-28 裁定) ----
    MacroSeries(
        code="USD_INDEX",
        symbol="DX-Y.NYB",
        tier=TIER_REFERENCE,
        family="匯率",
        label="美元指數",
        unit="指數點",
    ),
    MacroSeries(
        code="OIL_WTI",
        symbol="CL=F",
        tier=TIER_REFERENCE,
        family="商品",
        label="西德州中質原油期貨(近月連續)",
        unit="美元/桶",
    ),
    MacroSeries(
        code="GROWTH_ETF",
        symbol="IWF",
        tier=TIER_REFERENCE,
        family="風格",
        label="iShares 羅素 1000 成長 ETF",
        unit="已調整收市價",
        note="與 VALUE_ETF 相除即成長對價值的風格輪動對照。",
    ),
    MacroSeries(
        code="VALUE_ETF",
        symbol="IWD",
        tier=TIER_REFERENCE,
        family="風格",
        label="iShares 羅素 1000 價值 ETF",
        unit="已調整收市價",
    ),
    MacroSeries(
        code="SMALLCAP_ETF",
        symbol="IWM",
        tier=TIER_REFERENCE,
        family="規模",
        label="iShares 羅素 2000 ETF",
        unit="已調整收市價",
        note="與大市(SPY)相除即細價股對大價股的規模對照。",
    ),
)

SERIES_BY_CODE: dict[str, MacroSeries] = {series.code: series for series in MACRO_SERIES}

DRIVER_TIER_CODES: tuple[str, ...] = tuple(
    series.code for series in MACRO_SERIES if series.tier == TIER_DRIVER
)
REFERENCE_TIER_CODES: tuple[str, ...] = tuple(
    series.code for series in MACRO_SERIES if series.tier == TIER_REFERENCE
)
ALL_SERIES_CODES: tuple[str, ...] = tuple(series.code for series in MACRO_SERIES)


def series_of(codes: Sequence[str]) -> tuple[MacroSeries, ...]:
    """按代號取名冊上那幾條。名不在冊即當場拒收,不猜。"""
    out: list[MacroSeries] = []
    for code in codes:
        name = str(code).strip().upper()
        series = SERIES_BY_CODE.get(name)
        if series is None:
            raise ContractViolation(
                f"名冊上沒有「{name}」這條宏觀序列;有的是:{'、'.join(ALL_SERIES_CODES)}"
            )
        out.append(series)
    if not out:
        raise ContractViolation("宏觀序列名單是空的,無數可抓")
    duplicates = sorted({s.code for s in out if [x.code for x in out].count(s.code) > 1})
    if duplicates:
        raise ContractViolation(f"宏觀序列名單有重覆:{'、'.join(duplicates)}")
    return tuple(out)


# ----------------------------------------------------------------------
# 來源適配器(D-026 第 7 條)
# ----------------------------------------------------------------------


@runtime_checkable
class MacroSource(Protocol):
    """宏觀日線序列來源的合約。

    與 ``karst.data.sources.PriceSource`` 是同一個模子的兩件:適配器只負責「把外面
    的形狀搬成我們的形狀」,不做對齊、不做歸一化、不做凍結——那三件是下面那條
    管線的事。
    """

    name: str

    def fetch_daily_series(
        self,
        series: Sequence[MacroSeries],
        start: date | datetime | str,
        end: date | datetime | str,
    ) -> pd.DataFrame:
        """抓一批日線讀數,起訖含頭含尾。回 ``date`` / ``series`` / ``value`` 三欄。"""
        ...


def _empty_raw() -> pd.DataFrame:
    return pd.DataFrame({column: pd.Series(dtype="object") for column in RAW_COLUMNS})


class YFinanceMacroSource:
    """yfinance 的宏觀序列適配器。

    **逐個代號分開抓**,與價格那邊一批過抓不同。理由是實測出來的:指數
    (``^VIX``)、期貨(``ZQ=F``)、外匯(``DX-Y.NYB``)與 ETF 混在同一個批次時,
    yfinance 會為對不齊的日曆補一堆空行,而且**任何一個代號失手就整批回空**;
    宏觀這幾條序列的日曆本來就各不相同(``^VIX3M`` 尾段短五星期那件事就是這樣
    看出來的,後來 KARST-058 把它換去 Cboe 官方檔),所以分開抓、逐條核,一條
    抓不到就指名道姓講出是哪一條。

    只取收市價一欄:宏觀序列談的是水平與方向,開高低與成交量在這裡沒有意思
    (息率的「成交量」根本不存在)。
    """

    name = MACRO_SOURCE_NAME

    def __init__(self, *, timeout: float = 60.0) -> None:
        self.timeout = timeout

    def fetch_daily_series(
        self,
        series: Sequence[MacroSeries],
        start: date | datetime | str,
        end: date | datetime | str,
    ) -> pd.DataFrame:
        try:
            import yfinance  # noqa: PLC0415 - 只在真正抓數時才需要
        except ImportError as exc:  # pragma: no cover - 未裝套件的環境
            raise DataFetchFailed(f"未安裝 yfinance:{exc}") from exc

        wanted = tuple(series)
        if not wanted:
            raise DataFetchFailed("宏觀序列名單是空的,無數可抓")

        first = as_date(start, "start")
        last = as_date(end, "end")
        # yfinance 的 end 不含尾,加一日換成「含頭含尾」
        end_exclusive = (date.fromisoformat(last) + timedelta(days=1)).isoformat()

        blocks: list[pd.DataFrame] = []
        for item in wanted:
            try:
                raw = yfinance.download(
                    item.symbol,
                    start=first,
                    end=end_exclusive,
                    interval="1d",
                    auto_adjust=True,
                    actions=False,
                    threads=False,
                    progress=False,
                    group_by="column",
                )
            except Exception as exc:  # noqa: BLE001 - 對外抓取的錯一律歸一
                raise DataFetchFailed(
                    f"yfinance 抓 {item.code}({item.symbol})失敗"
                    f"({type(exc).__name__}: {exc})"
                ) from exc
            if raw is None or raw.empty:
                raise DataFetchFailed(
                    f"yfinance 在 {first}~{last} 對 {item.code}({item.symbol})回了空批次;"
                    "空批次一律當失敗,不當作「這段日子沒有讀數」"
                )
            closes = _close_column(raw, item)
            index = pd.DatetimeIndex(raw.index)
            block = pd.DataFrame(
                {
                    "date": pd.Series(index.strftime("%Y-%m-%d"), dtype="object"),
                    "series": item.code,
                    "value": pd.Series(closes, dtype="float64"),
                }
            )
            block = block.loc[block["value"].notna()]
            if block.empty:
                raise DataFetchFailed(
                    f"{item.code}({item.symbol})在 {first}~{last} 一個收市讀數都沒有"
                )
            blocks.append(block)

        if not blocks:  # pragma: no cover - 上面每一條都已經拋過錯
            return _empty_raw()
        frame = pd.concat(blocks, ignore_index=True)
        return frame.loc[:, list(RAW_COLUMNS)].sort_values(["date", "series"]).reset_index(drop=True)


def _close_column(raw: pd.DataFrame, item: MacroSeries) -> np.ndarray:
    """由 yfinance 的寬表取出收市價一欄(單層或雙層欄皆收)。"""
    if isinstance(raw.columns, pd.MultiIndex):
        for key in (("Close", item.symbol), ("Close", item.symbol.upper())):
            if key in raw.columns:
                return raw[key].to_numpy(dtype="float64")
        level = raw.columns.get_level_values(0)
        if "Close" in set(level):
            block = raw.loc[:, level == "Close"]
            return block.iloc[:, 0].to_numpy(dtype="float64")
    elif "Close" in raw.columns:
        return raw["Close"].to_numpy(dtype="float64")
    raise DataFetchFailed(
        f"{item.code}({item.symbol})的回應裡沒有收市價一欄;欄位是:{list(raw.columns)[:8]}"
    )


def parse_cboe_history(
    text: str, item: MacroSeries, start: str, end: str
) -> pd.DataFrame:
    """把一份 Cboe 官方歷史 CSV 的正文,切成本倉的長表形狀。

    抽出來是為了**離線驗得到**:網絡那一段與解析那一段分家,解析這一段用一小段
    示例正文就試得完,不必連網。

    Cboe 那份檔的形狀寫死如下(2026-08-29 實測):首行 ``DATE,OPEN,HIGH,LOW,CLOSE``,
    日期 ``MM/DD/YYYY``,收市價是最後一欄。形狀變了即當場拋錯,不猜、不靜靜跳過。
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise DataFetchFailed(f"Cboe 的 {item.code}({item.symbol})歷史檔是空的")
    header = [cell.strip().upper() for cell in lines[0].split(",")]
    if "DATE" not in header or "CLOSE" not in header:
        raise DataFetchFailed(
            f"Cboe 的 {item.code}({item.symbol})歷史檔欄位變了形:{header[:8]};"
            "本適配器只認 DATE 與 CLOSE 兩欄,形狀不對即當抓取失敗"
        )
    date_at, close_at = header.index("DATE"), header.index("CLOSE")

    days: list[str] = []
    values: list[float] = []
    for line in lines[1:]:
        cells = line.split(",")
        if len(cells) <= max(date_at, close_at):
            continue
        raw_day = cells[date_at].strip()
        raw_value = cells[close_at].strip()
        if not raw_day or not raw_value:
            continue
        try:
            month, day, year = (int(part) for part in raw_day.split("/"))
            iso = f"{year:04d}-{month:02d}-{day:02d}"
        except ValueError:
            continue
        if iso < start or iso > end:
            continue
        try:
            value = float(raw_value)
        except ValueError:
            continue
        days.append(iso)
        values.append(value)

    frame = pd.DataFrame(
        {
            "date": pd.Series(days, dtype="object"),
            "series": pd.Series([item.code] * len(days), dtype="object"),
            "value": pd.Series(values, dtype="float64"),
        }
    )
    if frame.empty:
        raise DataFetchFailed(
            f"Cboe 的 {item.code}({item.symbol})在 {start}~{end} 一個收市讀數都沒有;"
            "空批次一律當失敗,不當作「這段日子沒有讀數」"
        )
    return frame


class CboeMacroSource:
    """Cboe 官方免費歷史檔的宏觀序列適配器(KARST-058)。

    **不用鑰匙、不用登記、不用付費**,亦不加任何套件——只用標準庫的 ``urllib``。
    每個指數一份 CSV,由 1990(VIX)或 2009(VIX3M)起至最近一個交易日,每個
    交易日一行。與 yfinance 那一條同一個合約:只把外面的形狀搬成我們的形狀,
    對齊、歸一化、凍結三件仍然歸下面那條管線。

    取收市價一欄,理由與 yfinance 那條一樣:宏觀序列談的是水平與方向。
    """

    name = CBOE_SOURCE_NAME

    def __init__(self, *, timeout: float = 60.0, url_template: str = CBOE_HISTORY_URL) -> None:
        self.timeout = timeout
        self.url_template = url_template

    def url_for(self, item: MacroSeries) -> str:
        return self.url_template.format(symbol=item.symbol)

    def _download(self, item: MacroSeries) -> str:
        import urllib.error  # noqa: PLC0415 - 只在真正抓數時才需要
        import urllib.request  # noqa: PLC0415

        url = self.url_for(item)
        request = urllib.request.Request(url, headers={"User-Agent": "karst-macro/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = response.read()
        except Exception as exc:  # noqa: BLE001 - 對外抓取的錯一律歸一
            raise DataFetchFailed(
                f"Cboe 抓 {item.code}({item.symbol})失敗:{url}"
                f"({type(exc).__name__}: {exc})"
            ) from exc
        return payload.decode("utf-8", errors="replace")

    def fetch_daily_series(
        self,
        series: Sequence[MacroSeries],
        start: date | datetime | str,
        end: date | datetime | str,
    ) -> pd.DataFrame:
        wanted = tuple(series)
        if not wanted:
            raise DataFetchFailed("宏觀序列名單是空的,無數可抓")
        first, last = as_date(start, "start"), as_date(end, "end")

        blocks = [
            parse_cboe_history(self._download(item), item, first, last) for item in wanted
        ]
        frame = pd.concat(blocks, ignore_index=True)
        return frame.loc[:, list(RAW_COLUMNS)].sort_values(["date", "series"]).reset_index(drop=True)


class CompositeMacroSource:
    """按名冊上那一格 ``source``,把每條序列派去它自己的來源(KARST-058)。

    宏觀名冊自此**不是一個來源一張表**:VIX 那兩條由 Cboe 官方檔取,其餘十二條
    仍由 yfinance 取。派錯來源會靜靜地抓到另一條數(或者抓不到),所以這裡的做法
    是**照名冊指名派工**,名冊上寫的來源沒有人接,就當場拋錯講出是哪一條——
    不退回「隨便找一個來源試試」。
    """

    def __init__(self, sources: Sequence[MacroSource], *, name: str = COMPOSITE_SOURCE_NAME) -> None:
        by_name: dict[str, MacroSource] = {}
        for source in sources:
            key = str(getattr(source, "name", "")).strip()
            if not key:
                raise ContractViolation("宏觀來源沒有名字,派不到工")
            if key in by_name:
                raise ContractViolation(f"宏觀來源名重覆:{key}")
            by_name[key] = source
        if not by_name:
            raise ContractViolation("複合宏觀來源手上一個來源都沒有")
        self._by_name = by_name
        self.name = str(name)

    @property
    def sources(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_name))

    def fetch_daily_series(
        self,
        series: Sequence[MacroSeries],
        start: date | datetime | str,
        end: date | datetime | str,
    ) -> pd.DataFrame:
        wanted = tuple(series)
        if not wanted:
            raise DataFetchFailed("宏觀序列名單是空的,無數可抓")

        unknown = sorted(
            {item.source for item in wanted if item.source not in self._by_name}
        )
        if unknown:
            raise ContractViolation(
                f"名冊上這幾個來源沒有人接:{'、'.join(unknown)};"
                f"手上有的是:{'、'.join(self.sources)}"
            )

        blocks: list[pd.DataFrame] = []
        for key in sorted({item.source for item in wanted}):
            batch = tuple(item for item in wanted if item.source == key)
            blocks.append(self._by_name[key].fetch_daily_series(batch, start, end))
        frame = pd.concat(blocks, ignore_index=True)
        return frame.loc[:, list(RAW_COLUMNS)].sort_values(["date", "series"]).reset_index(drop=True)


def default_macro_source() -> CompositeMacroSource:
    """現役的宏觀來源:Cboe 官方檔取 VIX 那兩條,yfinance 取其餘十二條。"""
    return CompositeMacroSource((CboeMacroSource(), YFinanceMacroSource()))


class StaticMacroSource:
    """離線來源:照給定的長表回數。

    用途與 ``karst.data.sources.StaticSource`` 一樣——測試不必連網,日後要由別的
    來源重放同一批數亦是照這個形狀餵進同一條管線。
    """

    name = "static-macro"

    def __init__(self, values: pd.DataFrame, *, name: str | None = None) -> None:
        missing = [column for column in RAW_COLUMNS if column not in values.columns]
        if missing:
            raise ValueError(f"靜態宏觀來源缺欄位:{'、'.join(missing)}")
        if name:
            self.name = str(name)
        frame = values.loc[:, list(RAW_COLUMNS)].copy()
        frame["date"] = frame["date"].map(lambda value: as_date(value, "date"))
        frame["series"] = frame["series"].astype(str).str.strip().str.upper()
        frame["value"] = frame["value"].astype("float64")
        self._values = frame

    def fetch_daily_series(
        self,
        series: Sequence[MacroSeries],
        start: date | datetime | str,
        end: date | datetime | str,
    ) -> pd.DataFrame:
        codes = [item.code for item in series]
        first, last = as_date(start, "start"), as_date(end, "end")
        frame = self._values.loc[
            self._values["series"].isin(codes)
            & (self._values["date"] >= first)
            & (self._values["date"] <= last)
        ].copy()
        got = set(frame.loc[frame["value"].notna(), "series"].unique())
        absent = [code for code in codes if code not in got]
        if absent:
            raise DataFetchFailed(
                f"{self.name} 沒有回這幾條序列的讀數:{'、'.join(absent)};"
                "抓取失敗不當作「這條序列沒有數」"
            )
        return frame.sort_values(["date", "series"]).reset_index(drop=True)


# ----------------------------------------------------------------------
# 對齊主日曆與規範形態
# ----------------------------------------------------------------------


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


def canonical_macro(frame: pd.DataFrame) -> pd.DataFrame:
    """宏觀長表的規範形態:欄序、型別、排序都寫死。

    與 ``snapshots.canonical_prices`` 同一個用途——寫檔前與讀回後都過這一關,
    內容雜湊才會與寫檔的雜項無關。
    """
    out = frame.loc[:, list(SERIES_COLUMNS)].copy()
    out["date"] = out["date"].astype(str).astype("object")
    out["series"] = out["series"].astype(str).astype("object")
    out["value"] = out["value"].astype("float64")
    out["value_status"] = out["value_status"].astype(str).astype("object")
    return out.sort_values(["date", "series"]).reset_index(drop=True)


def normalise_macro(frame: pd.DataFrame, *, digits: int = PRICE_SIGNIFICANT_DIGITS) -> pd.DataFrame:
    """凍結前的歸一化:讀數取 ``digits`` 位有效數字(D-028 第 1 條同一條規矩)。"""
    out = frame.copy()
    out["value"] = round_significant(out["value"].to_numpy(dtype="float64"), digits)
    return out


def canonical_registry(series: Sequence[MacroSeries]) -> pd.DataFrame:
    """連同快照一併凍結的序列名冊。"""
    rows = [
        {
            "series": item.code,
            "symbol": item.symbol,
            "source": item.source,
            "tier": item.tier,
            "family": item.family,
            "label": item.label,
            "unit": item.unit,
            "note": item.note,
        }
        for item in series
    ]
    frame = pd.DataFrame(
        rows, columns=["series", "symbol", "source", "tier", "family", "label", "unit", "note"]
    )
    for column in frame.columns:
        frame[column] = frame[column].astype(str).astype("object")
    return frame.sort_values("series").reset_index(drop=True)


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


def macro_digest(
    values: pd.DataFrame,
    calendar: Sequence[str],
    registry: pd.DataFrame,
    core: dict[str, Any],
) -> str:
    """一個宏觀快照的內容雜湊:同樣的內容永遠同一串字。"""
    digest = hashlib.sha256()
    digest.update(content_hash(canonical_macro(values)).encode("utf-8"))
    digest.update(b"|")
    digest.update(content_hash(registry).encode("utf-8"))
    digest.update(b"|")
    digest.update("\n".join(str(day) for day in calendar).encode("utf-8"))
    digest.update(b"|")
    digest.update(canonical_json(core).encode("utf-8"))
    return digest.hexdigest()


# ----------------------------------------------------------------------
# 說明檔
# ----------------------------------------------------------------------


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
        notes_section=notes_section,
    )


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


# ----------------------------------------------------------------------
# 落地、等價重用與讀回
# ----------------------------------------------------------------------


def write_macro_dir(
    root: str | Path,
    snapshot_id: str,
    *,
    values: pd.DataFrame,
    calendar: Sequence[str],
    registry: pd.DataFrame,
    manifest: dict[str, Any],
    readme: str,
) -> Path:
    """原子寫入一個宏觀快照目錄(與價格快照同一個做法),回傳它的路徑。"""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    final = root / snapshot_id
    if final.exists():
        return final

    staging = root / f".tmp-{snapshot_id}-{uuid4().hex[:8]}"
    if staging.exists():  # pragma: no cover - uuid 撞名近乎不可能
        import shutil

        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    try:
        canonical_macro(values).to_parquet(staging / SERIES_FILE, engine="pyarrow", index=False)
        pd.DataFrame({"date": [str(day) for day in calendar]}).to_parquet(
            staging / CALENDAR_FILE, engine="pyarrow", index=False
        )
        registry.to_parquet(staging / REGISTRY_FILE, engine="pyarrow", index=False)
        (staging / MANIFEST_FILE).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (staging / README_FILE).write_text(readme, encoding="utf-8")
        try:
            staging.replace(final)
        except OSError:
            if not final.exists():
                raise
    finally:
        if staging.exists():
            import shutil

            shutil.rmtree(staging, ignore_errors=True)
    return final


def find_equivalent_macro_snapshot(
    root: str | Path,
    *,
    core: dict[str, Any],
    values: pd.DataFrame,
    calendar: Sequence[str],
    registry: pd.DataFrame,
    rtol: float = EQUIVALENCE_RTOL,
) -> tuple[Path, dict[str, Any]] | None:
    """在快取根裡找一份與這批新數據等價的已凍結宏觀快照(D-028 第 2 條同一條規矩)。"""
    root = Path(root)
    if not root.is_dir():
        return None

    wanted_values = canonical_macro(values)
    wanted_calendar = tuple(str(day) for day in calendar)
    wanted_registry = content_hash(registry)

    for directory in sorted(
        entry for entry in root.iterdir() if entry.is_dir() and not entry.name.startswith(".")
    ):
        manifest_path = directory / MANIFEST_FILE
        if not manifest_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if manifest.get("core") != core:
            continue
        if int(manifest.get("rows", -1)) != len(wanted_values):
            continue
        try:
            frozen_calendar = tuple(
                pd.read_parquet(directory / CALENDAR_FILE, engine="pyarrow")["date"].astype(str)
            )
            frozen_registry = pd.read_parquet(directory / REGISTRY_FILE, engine="pyarrow")
            frozen_values = canonical_macro(
                pd.read_parquet(directory / SERIES_FILE, engine="pyarrow")
            )
        except (OSError, ValueError, KeyError):
            continue
        if frozen_calendar != wanted_calendar:
            continue
        if content_hash(frozen_registry) != wanted_registry:
            continue
        if not _macro_values_equivalent(frozen_values, wanted_values, rtol=rtol):
            continue
        return directory, manifest
    return None


def _macro_values_equivalent(
    left: pd.DataFrame, right: pd.DataFrame, *, rtol: float = EQUIVALENCE_RTOL
) -> bool:
    """形狀逐格相同、數值在相對容差內相同,才算同一批宏觀數據。"""
    if len(left) != len(right):
        return False
    if not left["date"].equals(right["date"]):
        return False
    if not left["series"].equals(right["series"]):
        return False
    if not left["value_status"].equals(right["value_status"]):
        return False
    from .normalise import values_equivalent

    return values_equivalent(
        left["value"].to_numpy("float64"), right["value"].to_numpy("float64"), rtol=rtol
    )


@dataclass(frozen=True, slots=True)
class MacroSnapshot:
    """一次宏觀拉數的成果單。``snapshot_id`` 就是報告要引用的那個編號。"""

    snapshot_id: str
    source: str
    fetched_at: str
    taken_on: str
    window_start: str
    window_end: str
    calendar_ticker: str
    path: str
    content_hash: str
    series: tuple[str, ...]
    trading_days: int
    rows: int
    notes: tuple[str, ...]
    reused: bool = False


def build_macro_snapshot(
    store: DefinitionStore,
    *,
    start: date | datetime | str,
    end: date | datetime | str,
    calendar: Sequence[str],
    calendar_ticker: str,
    codes: Sequence[str] = ALL_SERIES_CODES,
    source: MacroSource | None = None,
    root: str | Path | None = None,
    taken_on: date | datetime | str | None = None,
) -> MacroSnapshot:
    """跑完整條宏觀管線,回傳快照成果單。

    四步,次序與價格那條管線一樣、少一步(**沒有解析實體那一步**——宏觀序列不是
    實體,見本檔開頭第一節):

      1. **抓** —— 適配器逐條向來源要日線讀數。抓不到即拋錯,不靜靜跳過。
      2. **歸一化** —— 取 7 位有效數字,行在對齊與填補之前(D-028 第 1 條)。
      3. **對齊** —— 全部序列對齊**傳進來的那條主日曆**(即價格快照那一條),
         缺日照停牌處置最多前值填補 3 個交易日。
      4. **凍結** —— 原子寫入 ``data/macro_snapshots/<編號>/``,經單一定義庫登記,
         與價格快照同一套編號算法、同一張登記表,靠來源名分得開。
    """
    source = source or default_macro_source()
    root = Path(root) if root is not None else DEFAULT_MACRO_ROOT
    wanted = series_of(codes)
    days = tuple(sorted({str(day) for day in calendar}))
    if not days:
        raise ContractViolation("主日曆是空的:宏觀序列要對齊價格快照那條日曆,不可留空")

    window_start, window_end = as_date(start, "start"), as_date(end, "end")
    fetched_at = datetime.now(timezone.utc)
    notes: list[str] = []

    raw = source.fetch_daily_series(wanted, window_start, window_end)
    if raw.empty:
        raise DataFetchFailed(
            f"{source.name} 在 {window_start}~{window_end} 回了空批次,當抓取失敗處理"
        )

    raw = normalise_macro(raw)
    aligned = align_macro_to_calendar(raw, days)
    coverage = macro_coverage(aligned)

    for row in coverage.to_dict("records"):
        if int(row["missing"]) > 0:
            notes.append(
                f"{row['series']} 在主日曆上有 {row['missing']} 日留空"
                f"(真有讀數 {row['actual']} 日、前值填補 {row['filled']} 日;"
                f"最後一個讀數在 {row['last_actual'] or '沒有'});"
                "留空的日子驅動器會當「數據不足」退回熱身期權重,不當零"
            )

    registry = canonical_registry(wanted)
    core = macro_core(
        source=source.name,
        window_start=window_start,
        window_end=window_end,
        calendar_ticker=str(calendar_ticker).strip().upper(),
        series_codes=[item.code for item in wanted],
    )
    digest = macro_digest(aligned, days, registry, core)
    day = as_date(taken_on, "taken_on") if taken_on is not None else fetched_at.date().isoformat()

    existing = find_equivalent_macro_snapshot(
        root, core=core, values=aligned, calendar=days, registry=registry
    )
    if existing is not None:
        path, manifest = existing
        snapshot_id = str(manifest["snapshot_id"])
        digest = str(manifest["content_hash"])
        day = str(manifest["taken_on"])
        reused = True
        notes.append(
            f"這次抓取與已凍結的宏觀快照 {snapshot_id} 等價(全部讀數相對差不過 "
            f"{EQUIVALENCE_RTOL:.0e}),沿用原編號與原檔案,不另存一份副本(D-028 第 2 條)"
        )
    else:
        reused = False
        snapshot_id = store.snapshot_id_for(day, digest)
        manifest = {
            "snapshot_id": snapshot_id,
            "snapshot_kind": "macro",
            "source": source.name,
            "fetched_at": fetched_at.isoformat(timespec="seconds"),
            "taken_on": day,
            "window_start": window_start,
            "window_end": window_end,
            "calendar_ticker": core["calendar_ticker"],
            "trading_days": len(days),
            "rows": int(len(aligned)),
            "series": [item.code for item in wanted],
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
            "notes": notes,
        }
        readme = render_macro_readme(
            snapshot_id=snapshot_id,
            source=source.name,
            fetched_at=manifest["fetched_at"],
            taken_on=day,
            window_start=window_start,
            window_end=window_end,
            calendar_ticker=core["calendar_ticker"],
            trading_days=len(days),
            content_hash_value=digest,
            rows=int(len(aligned)),
            registry=registry,
            coverage=coverage,
            notes=notes,
        )
        path = write_macro_dir(
            root,
            snapshot_id,
            values=aligned,
            calendar=days,
            registry=registry,
            manifest=manifest,
            readme=readme,
        )

    registered = store.register_snapshot(
        source=source.name,
        taken_on=day,
        content_hash=digest,
        path=path.as_posix(),
        universe=[item.code for item in wanted],
    )
    if registered != snapshot_id:  # pragma: no cover - 兩邊同一條算法
        raise ContractViolation(
            f"宏觀快照編號對不上:管線算出 {snapshot_id},登記表回 {registered}"
        )

    return MacroSnapshot(
        snapshot_id=snapshot_id,
        source=source.name,
        fetched_at=str(manifest["fetched_at"]),
        taken_on=day,
        window_start=window_start,
        window_end=window_end,
        calendar_ticker=core["calendar_ticker"],
        path=path.as_posix(),
        content_hash=digest,
        series=tuple(item.code for item in wanted),
        trading_days=len(days),
        rows=int(len(aligned)),
        notes=tuple(notes),
        reused=reused,
    )


def macro_snapshot_dir(
    store: DefinitionStore, snapshot_id: str, *, root: str | Path | None = None
) -> Path:
    """宏觀快照目錄在哪。以登記的路徑為準,搬過位就退回快取根找同名目錄。"""
    snapshot = store.get_snapshot(snapshot_id)
    candidates: list[Path] = []
    if snapshot.path:
        candidates.append(Path(snapshot.path))
    candidates.append(Path(root or DEFAULT_MACRO_ROOT) / snapshot_id)
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise SnapshotBroken(
        f"宏觀快照 {snapshot_id} 的目錄不在:{'、'.join(str(c) for c in candidates)}"
    )


def read_macro_manifest(
    store: DefinitionStore, snapshot_id: str, *, root: str | Path | None = None
) -> dict[str, Any]:
    path = macro_snapshot_dir(store, snapshot_id, root=root) / MANIFEST_FILE
    if not path.exists():
        raise SnapshotBroken(f"宏觀快照 {snapshot_id} 缺 {MANIFEST_FILE}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_macro_frame(
    store: DefinitionStore, snapshot_id: str, *, root: str | Path | None = None
) -> pd.DataFrame:
    """讀回宏觀長表(一列一序列一日),欄位見 ``SERIES_COLUMNS``。"""
    path = macro_snapshot_dir(store, snapshot_id, root=root) / SERIES_FILE
    if not path.exists():
        raise SnapshotBroken(f"宏觀快照 {snapshot_id} 缺 {SERIES_FILE}")
    return canonical_macro(pd.read_parquet(path, engine="pyarrow"))


def read_macro_panel(
    store: DefinitionStore,
    snapshot_id: str,
    *,
    root: str | Path | None = None,
    codes: Sequence[str] | None = None,
) -> pd.DataFrame:
    """按快照編號讀回宏觀面板:日期為列、**序列代號**為欄。

    留空的格就是留空(NaN)——那是那一日沒有讀數,不是零。這張表就是交給
    ``karst.strategies.factor_rotation.run_factor_rotation(macro=...)`` 的那一張。
    """
    frame = read_macro_frame(store, snapshot_id, root=root)
    if codes is not None:
        wanted = [str(code).strip().upper() for code in codes]
        absent = [code for code in wanted if code not in set(frame["series"])]
        if absent:
            raise SnapshotBroken(
                f"宏觀快照 {snapshot_id} 沒有這幾條序列:{'、'.join(absent)}"
            )
        frame = frame.loc[frame["series"].isin(wanted)]
    panel = frame.pivot(index="date", columns="series", values="value")
    panel.index = pd.DatetimeIndex(pd.to_datetime(panel.index), name="date")
    panel.columns = pd.Index([str(column) for column in panel.columns], name="series")
    return panel.sort_index().sort_index(axis=1)


def verify_macro_snapshot(
    store: DefinitionStore, snapshot_id: str, *, root: str | Path | None = None
) -> str:
    """由目錄裡的檔案重算內容雜湊,對得上登記才過關,回傳那個雜湊。"""
    snapshot = store.get_snapshot(snapshot_id)
    directory = macro_snapshot_dir(store, snapshot_id, root=root)
    manifest = read_macro_manifest(store, snapshot_id, root=root)
    calendar = tuple(
        pd.read_parquet(directory / CALENDAR_FILE, engine="pyarrow")["date"].astype(str)
    )
    registry = pd.read_parquet(directory / REGISTRY_FILE, engine="pyarrow")
    recomputed = macro_digest(
        read_macro_frame(store, snapshot_id, root=root), calendar, registry, manifest["core"]
    )
    if recomputed != snapshot.content_hash:
        raise SnapshotBroken(
            f"宏觀快照 {snapshot_id} 的內容與登記的雜湊對不上:"
            f"登記 {snapshot.content_hash},重算 {recomputed}"
        )
    return recomputed
