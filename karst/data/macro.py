"""宏觀訊號序列的接入(KARST-040)。

因子輪動的驅動器至今只看得見四隻因子 ETF 與大市自身的收價
(``karst.strategies.factor_rotation`` 的 ``EXTERNAL_DATA`` 是空的)。本檔開的是
另一道門:VIX 與其期限結構、美債息率與曲線斜度、信用利差、聯邦基金利率預期,
按同一套規矩(來源適配器 → 對齊主日曆 → 凍結成有編號的快照)入庫,好讓驅動器
用價格以外的訊號決定四格怎樣分。

**凍結不在本檔**(KARST-096)。本檔只做名冊、來源適配器、歸一化與讀回四件;
對齊主日曆、齊全度核對、內容雜湊、等價重用、寫檔、簽章登記那一整條,住凍結模組
``karst.data.freeze``,與價格線共用同一份正本。從前宏觀線自己有一套私家凍結,
於是同一條規矩要改兩處而改漏一處沒有人會發現——兩邊都跑得通,只是凍出來的東西
不一樣。

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

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import numpy as np
import pandas as pd

from ..errors import ContractViolation
from ..models import as_date
from ..store import DefinitionStore
from .errors import DataFetchFailed, SnapshotBroken
from .freeze import (
    CALENDAR_FILE,
    DEFAULT_MACRO_ROOT,
    MANIFEST_FILE,
    README_FILE,
    REGISTRY_FILE,
    SERIES_COLUMNS,
    SERIES_FILE,
    CompletenessAlert,
    CompletenessThresholds,
    MacroFreezePlan,
    canonical_macro,
    freeze_snapshot,
    macro_completeness,
    macro_coverage,
    macro_digest,
)
from .normalise import PRICE_SIGNIFICANT_DIGITS, round_significant

# 適配器交回來的形狀:一列一條序列一日,未對齊、未標身分。
# 對齊之後那一張(多一欄 ``value_status``)是 ``freeze.SERIES_COLUMNS``。
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
# 凍結前的歸一化與序列名冊
# ----------------------------------------------------------------------
#
# 對齊主日曆、規範形態、內容雜湊、等價重用、寫檔、登記那六步都不在本檔——
# 它們住凍結模組 ``karst.data.freeze``,價格線與宏觀線共用那一份正本(KARST-096)。


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


# ----------------------------------------------------------------------
# 凍結(交給凍結模組)與讀回
# ----------------------------------------------------------------------


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
    # 齊全度核對的結果(KARST-061)。``alerts`` 空 = 每一條都合格,不是「沒有核對過」
    # ——沒有核對過這件事表達不出來:門檻是必給的參數,凍結一次就核對一次。
    thresholds: CompletenessThresholds | None = None
    alerts: tuple[CompletenessAlert, ...] = ()


def build_macro_snapshot(
    store: DefinitionStore,
    *,
    start: date | datetime | str,
    end: date | datetime | str,
    calendar: Sequence[str],
    calendar_ticker: str,
    thresholds: CompletenessThresholds,
    codes: Sequence[str] = ALL_SERIES_CODES,
    source: MacroSource | None = None,
    root: str | Path | None = None,
    taken_on: date | datetime | str | None = None,
) -> MacroSnapshot:
    """跑完整條宏觀管線,回傳快照成果單。

    本檔只做頭兩步——**把外面那批數搬進來**;之後的全部交給凍結模組
    (``karst.data.freeze``),與價格線用同一份正本(KARST-096):

      1. **抓** —— 適配器逐條向來源要日線讀數。抓不到即拋錯,不靜靜跳過。
      2. **歸一化** —— 取 7 位有效數字,行在對齊與填補之前(D-028 第 1 條)。
      3. **對齊、核齊全度、凍結、登記** —— 全部住凍結模組。

    比價格那條少一步(**沒有解析實體那一步**——宏觀序列不是實體,見本檔開頭第一節);
    多的那一步是齊全度核對(KARST-061):逐條對主日曆核尾段與留空比例,超出門檻即
    逐條列出。``thresholds`` 是**必給的參數**,沒有它就凍結不到快照,所以「凍了一份
    沒有人核對過的宏觀快照」這件事在這裡表達不出來。

    **門檻不入內容雜湊。** 齊全度是由讀數與主日曆算出來的,門檻只決定「這樣算不算
    過關」;同一批讀數換一套門檻仍然是同一批讀數,所以換門檻**不會**換出一個新的
    快照編號(``freeze.macro_core`` 一個字都沒有改)。核對結果落在說明檔與 manifest,
    不落在編號裡。
    """
    source = source or default_macro_source()
    root = Path(root) if root is not None else DEFAULT_MACRO_ROOT
    wanted = series_of(codes)
    days = tuple(sorted({str(day) for day in calendar}))
    if not days:
        raise ContractViolation("主日曆是空的:宏觀序列要對齊價格快照那條日曆,不可留空")

    window_start, window_end = as_date(start, "start"), as_date(end, "end")
    fetched_at = datetime.now(timezone.utc)

    raw = source.fetch_daily_series(wanted, window_start, window_end)
    if raw.empty:
        raise DataFetchFailed(
            f"{source.name} 在 {window_start}~{window_end} 回了空批次,當抓取失敗處理"
        )

    frozen = freeze_snapshot(
        store,
        MacroFreezePlan(
            source=source.name,
            fetched_at=fetched_at.isoformat(timespec="seconds"),
            taken_on=(
                as_date(taken_on, "taken_on")
                if taken_on is not None
                else fetched_at.date().isoformat()
            ),
            window_start=window_start,
            window_end=window_end,
            calendar_ticker=str(calendar_ticker).strip().upper(),
            calendar=days,
            values=normalise_macro(raw),
            registry=canonical_registry(wanted),
            series_codes=tuple(item.code for item in wanted),
            thresholds=thresholds,
            notes=(),
            root=root,
        ),
    )

    return MacroSnapshot(
        snapshot_id=frozen.snapshot_id,
        source=frozen.source,
        fetched_at=frozen.fetched_at,
        taken_on=frozen.taken_on,
        window_start=frozen.window_start,
        window_end=frozen.window_end,
        calendar_ticker=frozen.calendar_ticker,
        path=frozen.path,
        content_hash=frozen.content_hash,
        series=tuple(item.code for item in wanted),
        trading_days=frozen.trading_days,
        rows=frozen.rows,
        notes=frozen.notes,
        reused=frozen.reused,
        thresholds=frozen.detail.thresholds,
        alerts=frozen.detail.alerts,
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


def read_macro_calendar(
    store: DefinitionStore, snapshot_id: str, *, root: str | Path | None = None
) -> tuple[str, ...]:
    """讀回這個宏觀快照當日對齊的那條主日曆(連同快照一併凍結)。"""
    path = macro_snapshot_dir(store, snapshot_id, root=root) / CALENDAR_FILE
    if not path.exists():
        raise SnapshotBroken(f"宏觀快照 {snapshot_id} 缺 {CALENDAR_FILE}")
    frame = pd.read_parquet(path, engine="pyarrow")
    return tuple(str(day) for day in frame["date"])


def read_macro_completeness(
    store: DefinitionStore, snapshot_id: str, *, root: str | Path | None = None
) -> pd.DataFrame:
    """由**已凍結**的快照重算齊全度表,不必重抓。

    重算而不是讀回 manifest 那一份,是刻意的:manifest 那份是凍結當日算出來的,
    重算這一份用的是磁碟上的讀數本身——兩者對不上,即那份快照被人改過。要核對的
    是數據,不是別人寫下的結論。回傳的表與 ``macro_completeness`` 同一個形狀。
    """
    frame = read_macro_frame(store, snapshot_id, root=root)
    calendar = read_macro_calendar(store, snapshot_id, root=root)
    return macro_completeness(macro_coverage(frame), calendar)


def read_macro_panel(
    store: DefinitionStore,
    snapshot_id: str,
    *,
    root: str | Path | None = None,
    codes: Sequence[str] | None = None,
) -> pd.DataFrame:
    """按快照編號讀回宏觀面板:日期為列、**序列代號**為欄。

    留空的格就是留空(NaN)——那是那一日沒有讀數,不是零。這張表就是經執行台的
    ``extras``(鍵 ``karst.strategies.factor_rotation.MACRO_INPUT``)交給因子輪動
    合約的那一張。
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
