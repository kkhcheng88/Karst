"""板塊倍數每日存檔件:由今日起自己儲的前瞻市盈率版本存檔(KARST-124,依 D-084)。

**為什麼有這個檔。** 前瞻市盈率(分析員對未來一年盈利的共識除出來的倍數)沒有
任何免費來源肯給歷史:發行商官網每日原地覆寫,今日拿到的只有今日一個數
(KARST-121 勘察,``research/2026-08-31-倍數數據勘察.md``)。所以唯一一條不用畀錢
就會隨時間變成資產的路,是**由今日起每日抄低一次**——一年之後就有一條自家造的、
無可爭議的 point-in-time 序列(詞彙表「數據版本存檔 / vintage」)。遲一日開始,
就永遠少一日,補不回。

**形態:追加式(append-only)。** 一次抓取寫一列,舊列一個字都不動。同日重跑而數字
一樣就不再寫(冪等);同日重跑而數字變了,兩列都留,以抓取時間戳分辨——因為
「同一日之內數字改過」本身就是關於這個來源的事實,覆蓋掉就查不回。

**響亮失敗,不寫空值。** 來源改版導致哪一格抓不到,即拋 :class:`DataFetchFailed`
並講明是哪一隻、哪一格、原文長成怎樣;絕不以空白冒充成功(``karst/data/errors.py``
同一條理)。**原始頁面在解析之前就先落檔**:即使解析當場失敗,那一日的頁面仍在,
日後修好解析器可以由存檔重跑,不會白白蝕一日。

用法(一句命令,見 ``karst.gateway.cli``)::

    python -m karst.gateway multiples capture
    python -m karst.gateway multiples list

只用標準庫 ``urllib``,不加任何套件(與 ``macro.py`` / ``cik.py`` 同一慣例)。
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import re
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from .errors import DataFetchFailed

# ----------------------------------------------------------------------
# 來源與宇宙
# ----------------------------------------------------------------------

SOURCE_NAME = "ssga-spdr"
SSGA_FUND_URL = "https://www.ssga.com/us/en/intermediary/etfs/{slug}"
USER_AGENT = "karst-multiples/1.0"

# 抓取重試(KARST-124 派工鐵律):斷纜重試兩三次,仍然不通就照實記錄,不無限重試。
# 這不是「用戶要裁決的判斷」,是網絡本身的性質,故寫死在這裡而不做參數。
FETCH_ATTEMPTS = 3
FETCH_BACKOFF_SECONDS = (1.0, 3.0)

# 發行商頁面的落點。代號→網址那一格是**來源的事實**,估不出,故逐隻寫死;
# 日後 State Street 改版式,錯的會是抓取那一步,響亮失敗,不會靜靜抓錯一隻。
#
# 名單比 D-084 講的「九隻 + SPY」多兩隻:XLRE(房地產)與 XLC(通訊服務)。
# 理由:倉內板塊名單 ``SECTOR_ETF_UNIVERSE`` 本來就是十一隻,而這個檔的全部價值
# 在於「今日不抄,以後補不回」——漏了這兩隻,日後板塊計分要用全套倍數時,
# 這兩格會永遠是空白。多抓兩隻成本是零,漏抓兩隻是不可逆。票上點名那十隻全部在內。
SSGA_SLUGS: dict[str, str] = {
    "XLB": "the-materials-select-sector-spdr-fund-xlb",
    "XLC": "the-communication-services-select-sector-spdr-fund-xlc",
    "XLE": "the-energy-select-sector-spdr-fund-xle",
    "XLF": "the-financial-select-sector-spdr-fund-xlf",
    "XLI": "the-industrial-select-sector-spdr-fund-xli",
    "XLK": "the-technology-select-sector-spdr-fund-xlk",
    "XLP": "the-consumer-staples-select-sector-spdr-fund-xlp",
    "XLRE": "the-real-estate-select-sector-spdr-fund-xlre",
    "XLU": "the-utilities-select-sector-spdr-fund-xlu",
    "XLV": "the-health-care-select-sector-spdr-fund-xlv",
    "XLY": "the-consumer-discretionary-select-sector-spdr-fund-xly",
    "SPY": "spdr-sp-500-etf-trust-spy",
}

MULTIPLES_UNIVERSE: tuple[str, ...] = tuple(SSGA_SLUGS)

DEFAULT_MULTIPLES_ROOT = Path("vintage") / "sector-multiples"
READINGS_FILE = "readings.csv"
README_FILE = "說明.md"
RAW_DIR = "raw"


def url_for(symbol: str) -> str:
    """代號 → 發行商頁面網址;不認得的代號當場拒收,不猜一條網址出來。"""
    try:
        slug = SSGA_SLUGS[symbol]
    except KeyError:
        raise DataFetchFailed(
            f"{symbol} 不在板塊倍數存檔的名單內;認得的是 {', '.join(MULTIPLES_UNIVERSE)}"
        ) from None
    return SSGA_FUND_URL.format(slug=slug)


# ----------------------------------------------------------------------
# 一列讀數
# ----------------------------------------------------------------------

# 存檔的欄。次序即 CSV 的欄次序,只可在尾加,不可插中間、不可改名——
# 舊列是別人日後要讀的正本,改欄名等於改寫歷史。
READING_COLUMNS: tuple[str, ...] = (
    "capture_id",
    "captured_at_utc",
    "symbol",
    "source_url",
    "index_as_of",
    "fund_as_of",
    "forward_pe_fy1",
    "trailing_pe",
    "price_cash_flow",
    "price_book",
    "est_eps_growth_3_5y_pct",
    "index_holdings",
    "fund_holdings",
    "weighted_avg_market_cap_musd",
    "fund_forward_pe_fy1",
    "raw_sha256",
    "raw_file",
)

# 判「同日重跑抓到的是不是同一個數」時比對的欄:抓取本身的痕跡(編號、時間戳、
# 頁面雜湊、存檔檔名)每次都不同,不算數字有變。
VALUE_COLUMNS: tuple[str, ...] = (
    "symbol",
    "source_url",
    "index_as_of",
    "fund_as_of",
    "forward_pe_fy1",
    "trailing_pe",
    "price_cash_flow",
    "price_book",
    "est_eps_growth_3_5y_pct",
    "index_holdings",
    "fund_holdings",
    "weighted_avg_market_cap_musd",
    "fund_forward_pe_fy1",
)


@dataclass(frozen=True, slots=True)
class MultiplesReading:
    """某一隻 ETF 在某一次抓取當時的一份估值讀數。

    數值一律以**來源原文的數字**存成字串(去掉 ``$``、``%``、``,``、``M``),
    不轉成 float 再印返出來——轉一次就有可能改變位數,而存檔要對得住原文。
    """

    capture_id: str
    captured_at_utc: str
    symbol: str
    source_url: str
    index_as_of: str
    fund_as_of: str
    forward_pe_fy1: str
    trailing_pe: str
    price_cash_flow: str
    price_book: str
    est_eps_growth_3_5y_pct: str
    index_holdings: str
    fund_holdings: str
    weighted_avg_market_cap_musd: str
    fund_forward_pe_fy1: str
    raw_sha256: str
    raw_file: str

    def as_row(self) -> dict[str, str]:
        return {name: getattr(self, name) for name in READING_COLUMNS}


# ----------------------------------------------------------------------
# 解析(純函式:不連網,測試直接餵真實頁面樣本)
# ----------------------------------------------------------------------

_SECTION_RE = re.compile(r'<section data-fundComponent="true">(.*?)</section>', re.S)
_TITLE_RE = re.compile(r'<h2 class="comp-title">(.*?)</h2>', re.S)
_DATE_RE = re.compile(r'<span class="date">\s*as of\s*([^<]+?)\s*</span>', re.S)
_ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.S)
_TH_RE = re.compile(r"<th[^>]*>(.*?)</th>", re.S)
_TD_RE = re.compile(r'<td class="data">(.*?)</td>', re.S)
_TICKER_RE = re.compile(r'id="fund-info-ticker"[^>]*value="([^"]*)"')
_TAG_RE = re.compile(r"<[^>]+>")

INDEX_SECTION = "Index Characteristics"
FUND_SECTION = "Fund Characteristics"

# 來源欄名 → 存檔欄名。來源改名即抓不到,響亮失敗——這正是要它斷得出聲的地方。
INDEX_FIELDS: dict[str, str] = {
    "Price/Earnings Ratio FY1": "forward_pe_fy1",
    "Price/Earnings": "trailing_pe",
    "Price/Cash Flow": "price_cash_flow",
    "Est. 3-5 Year EPS Growth": "est_eps_growth_3_5y_pct",
    "Number of Holdings": "index_holdings",
}
FUND_FIELDS: dict[str, str] = {
    "Price/Book Ratio": "price_book",
    "Price/Earnings Ratio FY1": "fund_forward_pe_fy1",
    "Weighted Average Market Cap": "weighted_avg_market_cap_musd",
    "Number of Holdings": "fund_holdings",
}

# 每一格用哪把尺讀。讀不出即拋錯,不當它是零、不當它是空白。
_RATIO_FIELDS = frozenset(
    {"forward_pe_fy1", "trailing_pe", "price_cash_flow", "price_book", "fund_forward_pe_fy1"}
)
_PERCENT_FIELDS = frozenset({"est_eps_growth_3_5y_pct"})
_COUNT_FIELDS = frozenset({"index_holdings", "fund_holdings"})
_MILLIONS_FIELDS = frozenset({"weighted_avg_market_cap_musd"})


def _plain_text(fragment: str) -> str:
    text = _TAG_RE.sub(" ", fragment)
    for entity, char in (("&amp;", "&"), ("&#39;", "'"), ("&quot;", '"'), ("&nbsp;", " ")):
        text = text.replace(entity, char)
    return " ".join(text.replace("﻿", "").split())


def _label_of(cell_html: str) -> str:
    """欄名住在 ``<th>`` 開頭的裸文字裡,後面那個 ``<span class="info">`` 是說明浮框。

    取第一個 ``<span`` 之前那一截,浮框裡重複一次的欄名與整段解釋就不會混進來。
    """
    return _plain_text(cell_html.split("<span", 1)[0])


def _sections(page: str) -> dict[str, tuple[str, dict[str, str]]]:
    found: dict[str, tuple[str, dict[str, str]]] = {}
    for body in _SECTION_RE.findall(page):
        title_match = _TITLE_RE.search(body)
        if not title_match:
            continue
        heading = title_match.group(1)
        title = _label_of(heading)
        date_match = _DATE_RE.search(heading)
        fields: dict[str, str] = {}
        for row in _ROW_RE.findall(body):
            th_match, td_match = _TH_RE.search(row), _TD_RE.search(row)
            if not th_match or not td_match:
                continue
            value = _plain_text(td_match.group(1))
            if value:
                fields.setdefault(_label_of(th_match.group(1)), value)
        if fields and title not in found:
            found[title] = (date_match.group(1) if date_match else "", fields)
    return found


def _as_of(raw: str, *, symbol: str, section: str) -> str:
    """``Aug 28 2026`` → ``2026-08-28``。讀不出格式即拋錯,不退而求其次用今日。"""
    try:
        return datetime.strptime(raw.strip(), "%b %d %Y").date().isoformat()
    except ValueError:
        raise DataFetchFailed(
            f"{symbol}:{section} 的截數日期形狀變了,讀不出「{raw}」;"
            "來源改版,請先修好解析再抓——存檔不收猜出來的日期"
        ) from None


def _numeric(raw: str, *, field: str, symbol: str) -> str:
    text = raw.strip()
    if field in _PERCENT_FIELDS:
        if not text.endswith("%"):
            raise DataFetchFailed(f"{symbol}:{field} 本應是百分數,來源給的是「{raw}」")
        text = text[:-1]
    elif field in _MILLIONS_FIELDS:
        match = re.fullmatch(r"\$([\d,]+(?:\.\d+)?)\s*M", text)
        if not match:
            raise DataFetchFailed(
                f"{symbol}:{field} 本應是「$1,234.56 M」形狀(單位:百萬美元),"
                f"來源給的是「{raw}」——單位變了就不是同一個數,不強行換算"
            )
        text = match.group(1)
    text = text.replace(",", "")
    try:
        if field in _COUNT_FIELDS:
            int(text)
        elif field in _RATIO_FIELDS or field in _PERCENT_FIELDS or field in _MILLIONS_FIELDS:
            float(text)
        else:  # pragma: no cover - 上面四個集合已窮盡存檔的數值欄
            raise AssertionError(f"未指定尺的欄 {field}")
    except ValueError:
        raise DataFetchFailed(f"{symbol}:{field} 讀不成數字,來源給的是「{raw}」") from None
    return text


def parse_ssga_fund_page(
    page: str, *, symbol: str, source_url: str, capture_id: str, captured_at_utc: str,
    raw_sha256: str, raw_file: str,
) -> MultiplesReading:
    """由發行商基金頁面抽出一份讀數;缺任何一格都響亮失敗,不寫空值。"""
    ticker_match = _TICKER_RE.search(page)
    if not ticker_match:
        raise DataFetchFailed(
            f"{symbol}:頁面找不到自報代號那一格(fund-info-ticker),"
            "來源改版,無法確認抓回來的是不是這一隻"
        )
    if ticker_match.group(1).strip().upper() != symbol:
        raise DataFetchFailed(
            f"{symbol}:抓回來的頁面自報是 {ticker_match.group(1)!r},不是這一隻——"
            "網址對照表或來源版式有變,寧可整隻不收"
        )

    sections = _sections(page)
    values: dict[str, str] = {}
    as_of: dict[str, str] = {}
    for section_name, field_map, as_of_key in (
        (INDEX_SECTION, INDEX_FIELDS, "index_as_of"),
        (FUND_SECTION, FUND_FIELDS, "fund_as_of"),
    ):
        if section_name not in sections:
            raise DataFetchFailed(
                f"{symbol}:頁面找不到「{section_name}」一節({source_url});"
                f"見到的是 {sorted(sections)}——來源改版,請先修好解析"
            )
        raw_date, fields = sections[section_name]
        if not raw_date:
            raise DataFetchFailed(
                f"{symbol}:「{section_name}」一節沒有截數日期;"
                "沒有截數日期的數字對不上知情時點,不收"
            )
        as_of[as_of_key] = _as_of(raw_date, symbol=symbol, section=section_name)
        for label, field in field_map.items():
            if label not in fields:
                raise DataFetchFailed(
                    f"{symbol}:「{section_name}」一節缺了「{label}」一欄"
                    f"(存檔欄 {field});見到的欄是 {sorted(fields)}——"
                    "來源改版,斷了哪一格已講明,存檔不寫空值"
                )
            values[field] = _numeric(fields[label], field=field, symbol=symbol)

    return MultiplesReading(
        capture_id=capture_id,
        captured_at_utc=captured_at_utc,
        symbol=symbol,
        source_url=source_url,
        index_as_of=as_of["index_as_of"],
        fund_as_of=as_of["fund_as_of"],
        raw_sha256=raw_sha256,
        raw_file=raw_file,
        **values,
    )


# ----------------------------------------------------------------------
# 來源適配器(真抓一個,離線孖生一個;與 sources.py 同一形態)
# ----------------------------------------------------------------------


class MultiplesSource(Protocol):
    """把一隻代號變成「網址 + 頁面正文」;解析與落檔一律不歸它管。"""

    name: str

    def fetch_page(self, symbol: str) -> tuple[str, str]:
        """回傳 ``(網址, 頁面正文)``;抓不到即拋 :class:`DataFetchFailed`。"""


class SsgaMultiplesSource:
    """State Street 官網基金頁面。免費、不用鑰匙、伺服器直出,不用瀏覽器。"""

    name = SOURCE_NAME

    def __init__(self, *, timeout: float = 60.0, attempts: int = FETCH_ATTEMPTS) -> None:
        self.timeout = timeout
        self.attempts = attempts

    def fetch_page(self, symbol: str) -> tuple[str, str]:
        import urllib.request  # noqa: PLC0415 - 只在真正抓數時才需要

        url = url_for(symbol)
        troubles: list[str] = []
        for attempt in range(1, self.attempts + 1):
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = response.read()
                return url, payload.decode("utf-8", errors="replace")
            except Exception as exc:  # noqa: BLE001 - 對外抓取的錯一律歸一
                troubles.append(f"第 {attempt} 次:{type(exc).__name__}: {exc}")
                if attempt < self.attempts:
                    pause = FETCH_BACKOFF_SECONDS[min(attempt, len(FETCH_BACKOFF_SECONDS)) - 1]
                    time.sleep(pause)
        raise DataFetchFailed(
            f"{symbol} 抓 {url} 連續 {self.attempts} 次都失敗;" + ";".join(troubles)
        )


class StaticMultiplesSource:
    """離線孖生:由手上的頁面正文重放,一次網都不出(測試與由存檔重跑解析用)。"""

    name = f"{SOURCE_NAME}-static"

    def __init__(self, pages: Mapping[str, str]) -> None:
        self._pages = dict(pages)

    def fetch_page(self, symbol: str) -> tuple[str, str]:
        try:
            page = self._pages[symbol]
        except KeyError:
            raise DataFetchFailed(f"離線來源手上沒有 {symbol} 的頁面") from None
        return url_for(symbol), page


# ----------------------------------------------------------------------
# 存檔(追加式)
# ----------------------------------------------------------------------


def readings_path(root: Path | str) -> Path:
    return Path(root) / READINGS_FILE


def read_readings(root: Path | str) -> list[dict[str, str]]:
    """讀回整份存檔;還未抓過就是空清單(不是錯)。"""
    path = readings_path(root)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if rows and tuple(rows[0]) != READING_COLUMNS:
        raise DataFetchFailed(
            f"存檔 {path} 的欄與現行版式對不上;現行是 {READING_COLUMNS},"
            f"檔內是 {tuple(rows[0])}——舊列不改寫,請先對清楚才續寫"
        )
    return rows


def append_reading(root: Path | str, reading: MultiplesReading) -> None:
    """追加一列。舊列一個字都不動;檔不存在就連表頭一齊開。"""
    path = readings_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(READING_COLUMNS))
        if fresh:
            writer.writeheader()
        writer.writerow(reading.as_row())


def latest_row_on(rows: Sequence[Mapping[str, str]], symbol: str, day: str) -> dict[str, str] | None:
    """某隻代號在某一日(UTC)最後寫入的那一列;那一日沒抓過就回 ``None``。"""
    hits = [
        dict(row) for row in rows
        if row["symbol"] == symbol and row["captured_at_utc"][:10] == day
    ]
    return hits[-1] if hits else None


def values_unchanged(previous: Mapping[str, str], reading: MultiplesReading) -> bool:
    row = reading.as_row()
    return all(previous.get(name) == row[name] for name in VALUE_COLUMNS)


# ----------------------------------------------------------------------
# 抓一次
# ----------------------------------------------------------------------

CAPTURED = "已寫入"
UNCHANGED = "同日不變"
FAILED = "失敗"


@dataclass(frozen=True, slots=True)
class CaptureOutcome:
    symbol: str
    status: str
    reading: MultiplesReading | None
    trouble: str | None


@dataclass(frozen=True, slots=True)
class CaptureReport:
    capture_id: str
    captured_at_utc: str
    root: Path
    source_name: str
    outcomes: tuple[CaptureOutcome, ...]

    @property
    def written(self) -> tuple[CaptureOutcome, ...]:
        return tuple(item for item in self.outcomes if item.status == CAPTURED)

    @property
    def unchanged(self) -> tuple[CaptureOutcome, ...]:
        return tuple(item for item in self.outcomes if item.status == UNCHANGED)

    @property
    def failed(self) -> tuple[CaptureOutcome, ...]:
        return tuple(item for item in self.outcomes if item.status == FAILED)


def capture_id_for(now: datetime) -> str:
    return now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _raw_relative_path(capture_id: str, symbol: str) -> str:
    return f"{RAW_DIR}/{capture_id}/{symbol}.html.gz"


def _store_raw(root: Path, capture_id: str, symbol: str, page: str) -> tuple[str, str]:
    """原始頁面先落檔、後解析:解析當場失敗,那一日的頁面仍然留得住,補得回。"""
    relative = _raw_relative_path(capture_id, symbol)
    path = root / Path(relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = page.encode("utf-8")
    with gzip.open(path, "wb") as handle:
        handle.write(body)
    return hashlib.sha256(body).hexdigest(), relative


def capture_multiples(
    *,
    source: MultiplesSource,
    symbols: Sequence[str],
    root: Path | str,
    now: datetime,
) -> CaptureReport:
    """抓一次、逐隻落存檔;一隻斷纜不影響其餘,失敗逐隻記錄在報告裡。

    四個參數一個預設值都沒有(D-009):抓哪幾隻、落哪裡、當作幾點,
    全部是呼叫者才知道的事,程式代揀一個就等於把一個沒有人裁決過的判斷寫死。
    """
    if not symbols:
        raise DataFetchFailed("名單是空的,無數可抓")
    root_path = Path(root)
    moment = now.astimezone(timezone.utc)
    capture_id = capture_id_for(moment)
    captured_at = moment.strftime("%Y-%m-%dT%H:%M:%SZ")
    day = captured_at[:10]

    existing = read_readings(root_path)
    outcomes: list[CaptureOutcome] = []
    for symbol in symbols:
        try:
            url, page = source.fetch_page(symbol)
            digest, relative = _store_raw(root_path, capture_id, symbol, page)
            reading = parse_ssga_fund_page(
                page,
                symbol=symbol,
                source_url=url,
                capture_id=capture_id,
                captured_at_utc=captured_at,
                raw_sha256=digest,
                raw_file=relative,
            )
        except DataFetchFailed as exc:
            outcomes.append(CaptureOutcome(symbol, FAILED, None, str(exc)))
            continue
        previous = latest_row_on(existing, symbol, day)
        if previous is not None and values_unchanged(previous, reading):
            outcomes.append(CaptureOutcome(symbol, UNCHANGED, reading, None))
            continue
        append_reading(root_path, reading)
        existing.append(reading.as_row())
        outcomes.append(CaptureOutcome(symbol, CAPTURED, reading, None))

    _ensure_readme(root_path)
    return CaptureReport(
        capture_id=capture_id,
        captured_at_utc=captured_at,
        root=root_path,
        source_name=source.name,
        outcomes=tuple(outcomes),
    )


README_TEXT = """# 板塊倍數版本存檔(vintage)

由 `python -m karst.gateway multiples capture` 逐日追加,KARST-124 依 D-084 開檔。

## 這是什麼

發行商(State Street)官網每日更新一次十一隻 SPDR 板塊 ETF 連 SPY 的估值欄位,
**原地覆寫、無官方存檔**——今日拿到的只有今日一個數,歷史任何人都買不到免費版
(KARST-121 勘察)。所以這一份是**自己儲出來的** point-in-time 序列:每日抄一次,
一年之後就有一條無可爭議的自家前瞻市盈率歷史。**遲一日開始就永遠少一日。**

## 規矩

- **追加式**:一次抓取寫一列,舊列一個字都不動。
- **同日冪等**:同日重跑而每一格數字都一樣,不再寫一列;
  **同日重跑而數字變了,兩列都留**,以 `captured_at_utc` 分辨——
  「同一日之內來源改過數」本身就是關於這個來源的事實,覆蓋掉就查不回。
- **不寫空值**:任何一格抓不到即整隻不收,並講明是哪一格斷了。
- **原始頁面先落檔、後解析**:解析當場失敗,`raw/` 內那一日的頁面仍在,
  日後修好解析器由存檔重跑補得回。

## 檔案

| 落點 | 是什麼 | 入不入 git |
|---|---|---|
| `readings.csv` | 存檔正本,一列一次(抓取 × 代號) | **入**(這一份不可再生,必須跟住倉走) |
| `raw/<抓取編號>/<代號>.html.gz` | 當次原始頁面,做證據與補抓用 | 不入(體積大;`.gitignore` 已擋) |
| `說明.md` | 本檔 | 入 |

## 欄

`forward_pe_fy1` 是本存檔的主角:發行商所講的**前瞻市盈率 FY1**,取自頁面
「Index Characteristics」一節,口徑是加權調和平均。`index_as_of` / `fund_as_of`
是發行商自報的截數日,通常是抓取日的前一個交易日(知情滯後 T+1)——
**回測對齊要用截數日,不是抓取日**。`price_book`、`fund_holdings`、
`weighted_avg_market_cap_musd`、`fund_forward_pe_fy1` 取自「Fund Characteristics」
一節(基金層),其餘取自指數層;兩節的 FY1 各存一格,分歧本身也是事實。

`est_eps_growth_3_5y_pct` 以百分數的數字存(`35.82` 即 35.82%);
`weighted_avg_market_cap_musd` 單位是百萬美元。
"""


def _ensure_readme(root: Path) -> None:
    path = root / README_FILE
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(README_TEXT, encoding="utf-8")


# ----------------------------------------------------------------------
# 讀回
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ArchiveSummary:
    rows: int
    captures: int
    symbols: tuple[str, ...]
    first_day: str
    last_day: str


def summarise(rows: Sequence[Mapping[str, str]]) -> ArchiveSummary:
    days = sorted({row["captured_at_utc"][:10] for row in rows})
    return ArchiveSummary(
        rows=len(rows),
        captures=len({row["capture_id"] for row in rows}),
        symbols=tuple(sorted({row["symbol"] for row in rows})),
        first_day=days[0] if days else "",
        last_day=days[-1] if days else "",
    )


def latest_per_symbol(rows: Iterable[Mapping[str, str]]) -> list[dict[str, str]]:
    """每隻代號最新的一列,按代號排序;存檔空即空清單。"""
    newest: dict[str, dict[str, str]] = {}
    for row in rows:
        newest[row["symbol"]] = dict(row)
    return [newest[symbol] for symbol in sorted(newest)]


def history_of(
    rows: Iterable[Mapping[str, str]], symbol: str, *, since: str | None
) -> list[dict[str, str]]:
    """某隻代號的逐次讀數;``since`` 留空即全部(留空是「不篩」,不是預設值)。"""
    picked = [dict(row) for row in rows if row["symbol"] == symbol]
    if since is not None:
        picked = [row for row in picked if row["captured_at_utc"][:10] >= since]
    return picked
