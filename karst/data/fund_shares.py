"""每日在外股數存檔件:SPY 連十一隻 SPDR 板塊 ETF 的基金單位數(KARST-130)。

**為什麼有這個檔。** 申贖流(創設與贖回,即基金單位數的每日增減)是判「錢在流入
還是流出一個板塊」最乾淨的一條線。現時倉內唯一一條申贖流數據是由富途的前復權
成交量除以換手率**反推**出來的分母;KARST-128 考出那條反推線在 2020-01 之前
係一條**凍結的分母**——數值不動,即那一段根本不是真流,只是一個常數。真流歷史
因此只剩六年半,次數不夠過考試的關,申贖流一路判「量不出」(D-094)。

發行商(State Street)自己每日在基金頁公布 `Shares Outstanding`,附自報截數日;
但同樣**原地覆寫、無官方歷史**——今日不抄,以後補不回。所以這一份與板塊倍數存檔
(``multiples.py``,D-086)同一形態:由今日起每日抄一次,一年之後就有一條不靠
反推、無可爭議的自家 point-in-time 單位數序列。**遲一日開始就永遠少一日。**

**同一張頁面,兩份存檔。** 在外股數與前瞻倍數住在發行商同一張基金頁的不同一節
(前者「Fund Net Asset Value」,後者「Index / Fund Characteristics」),所以這個檔
重用 ``multiples.py`` 的抓取與解析零件,只換一節、換一份存檔。兩份存檔各自獨立:
一邊的解析斷了,另一邊照樣儲得到——這正是不把新欄硬塞落舊 CSV 的理由(舊列是
別人日後要讀的正本,加欄等於改寫已經寫好的歷史)。

**回填。** 板塊倍數存檔由 2026-08-31 起就已經把整張原始頁面落了檔,而那些頁面裡
本來就有 `Shares Outstanding` 一節。所以這個檔開檔第一日就補得回 8 月 31 日那幾次
——見 ``backfill_from_raw``。

用法(見 ``karst.gateway.cli``)::

    python -m karst.gateway shares capture
    python -m karst.gateway shares backfill
    python -m karst.gateway shares list

只用標準庫,不加任何套件(與 ``multiples.py`` 同一慣例)。
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

from .errors import DataFetchFailed
from .multiples import (
    DEFAULT_MULTIPLES_ROOT,
    MULTIPLES_UNIVERSE,
    RAW_DIR,
    MultiplesSource,
    SsgaMultiplesSource,
    StaticMultiplesSource,
    _TICKER_RE,
    _as_of,
    _sections,
    url_for,
)

# 抓哪幾隻:與板塊倍數存檔同一個宇宙。兩份存檔講同一批基金,名單分岔就會出現
# 「一邊有、一邊冇」的日子,日後對不上。故此直接沿用,不另立一份名單。
SHARES_UNIVERSE: tuple[str, ...] = MULTIPLES_UNIVERSE

DEFAULT_SHARES_ROOT = Path("vintage") / "fund-shares"
SHARES_READINGS_FILE = "readings.csv"
SHARES_README_FILE = "說明.md"

# 禮貌節奏:逐隻之間停一停。發行商官網是免費公開頁,一日十二個請求本來就輕,
# 但連珠炮發是觸發封鎖的典型形狀;停一秒的代價是十二秒,被封的代價是整條數據線。
POLITE_PAUSE_SECONDS = 1.0

SOURCE_SECTION = "Fund Net Asset Value"

# 來源欄名 → 存檔欄名。來源改名即抓不到,響亮失敗——這正是要它斷得出聲的地方。
SHARES_FIELDS: dict[str, str] = {
    "Shares Outstanding": "shares_outstanding_m",
    "NAV": "nav_usd",
    "Assets Under Management": "aum_musd",
}

# 每一格用哪把尺讀。三格一齊存,是因為 單位數 × NAV ≈ 資產淨值 本身就是一條
# 免費的自檢:三個數對不上,即那一日的頁面有古怪,查得出。
_SHARES_MILLIONS_FIELDS = frozenset({"shares_outstanding_m"})
_DOLLAR_MILLIONS_FIELDS = frozenset({"aum_musd"})
_DOLLAR_FIELDS = frozenset({"nav_usd"})

# 存檔的欄。次序即 CSV 的欄次序,只可在尾加,不可插中間、不可改名——
# 舊列是別人日後要讀的正本,改欄名等於改寫歷史。
SHARES_COLUMNS: tuple[str, ...] = (
    "capture_id",
    "captured_at_utc",
    "symbol",
    "source_url",
    "nav_as_of",
    "shares_outstanding_m",
    "nav_usd",
    "aum_musd",
    "raw_sha256",
    "raw_file",
)

# 判「同日重跑抓到的是不是同一個數」時比對的欄:抓取本身的痕跡(編號、時間戳、
# 頁面雜湊、存檔檔名)每次都不同,不算數字有變。
SHARES_VALUE_COLUMNS: tuple[str, ...] = (
    "symbol",
    "source_url",
    "nav_as_of",
    "shares_outstanding_m",
    "nav_usd",
    "aum_musd",
)


@dataclass(frozen=True, slots=True)
class SharesReading:
    """某一隻 ETF 在某一次抓取當時的在外股數讀數。

    數值一律以**來源原文的數字**存成字串(去掉 ``$``、``,``、``M``),不轉成 float
    再印返出來——轉一次就有可能改變位數,而存檔要對得住原文。
    """

    capture_id: str
    captured_at_utc: str
    symbol: str
    source_url: str
    nav_as_of: str
    shares_outstanding_m: str
    nav_usd: str
    aum_musd: str
    raw_sha256: str
    raw_file: str

    def as_row(self) -> dict[str, str]:
        return {name: getattr(self, name) for name in SHARES_COLUMNS}


# ----------------------------------------------------------------------
# 解析(純函式:不連網,測試直接餵真實頁面樣本)
# ----------------------------------------------------------------------


def _shares_numeric(raw: str, *, field: str, symbol: str) -> str:
    text = raw.strip()
    if field in _SHARES_MILLIONS_FIELDS:
        match = re.fullmatch(r"([\d,]+(?:\.\d+)?)\s*M", text)
        if not match:
            raise DataFetchFailed(
                f"{symbol}:{field} 本應是「1,058.53 M」形狀(單位:百萬股),"
                f"來源給的是「{raw}」——單位變了就不是同一個數,不強行換算"
            )
        text = match.group(1)
    elif field in _DOLLAR_MILLIONS_FIELDS:
        match = re.fullmatch(r"\$([\d,]+(?:\.\d+)?)\s*M", text)
        if not match:
            raise DataFetchFailed(
                f"{symbol}:{field} 本應是「$814,409.65 M」形狀(單位:百萬美元),"
                f"來源給的是「{raw}」——單位變了就不是同一個數,不強行換算"
            )
        text = match.group(1)
    elif field in _DOLLAR_FIELDS:
        match = re.fullmatch(r"\$([\d,]+(?:\.\d+)?)", text)
        if not match:
            raise DataFetchFailed(
                f"{symbol}:{field} 本應是「$769.38」形狀(每單位美元),"
                f"來源給的是「{raw}」"
            )
        text = match.group(1)
    else:  # pragma: no cover - 上面三個集合已窮盡存檔的數值欄
        raise AssertionError(f"未指定尺的欄 {field}")
    text = text.replace(",", "")
    try:
        float(text)
    except ValueError:
        raise DataFetchFailed(f"{symbol}:{field} 讀不成數字,來源給的是「{raw}」") from None
    return text


def parse_ssga_shares(
    page: str, *, symbol: str, source_url: str, capture_id: str, captured_at_utc: str,
    raw_sha256: str, raw_file: str,
) -> SharesReading:
    """由發行商基金頁面抽出在外股數;缺任何一格都響亮失敗,不寫空值。"""
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
    if SOURCE_SECTION not in sections:
        raise DataFetchFailed(
            f"{symbol}:頁面找不到「{SOURCE_SECTION}」一節({source_url});"
            f"見到的是 {sorted(sections)}——來源改版,請先修好解析"
        )
    raw_date, fields = sections[SOURCE_SECTION]
    if not raw_date:
        raise DataFetchFailed(
            f"{symbol}:「{SOURCE_SECTION}」一節沒有截數日期;"
            "沒有截數日期的數字對不上知情時點,不收"
        )
    nav_as_of = _as_of(raw_date, symbol=symbol, section=SOURCE_SECTION)

    values: dict[str, str] = {}
    for label, field in SHARES_FIELDS.items():
        if label not in fields:
            raise DataFetchFailed(
                f"{symbol}:「{SOURCE_SECTION}」一節缺了「{label}」一欄"
                f"(存檔欄 {field});見到的欄是 {sorted(fields)}——"
                "來源改版,斷了哪一格已講明,存檔不寫空值"
            )
        values[field] = _shares_numeric(fields[label], field=field, symbol=symbol)

    return SharesReading(
        capture_id=capture_id,
        captured_at_utc=captured_at_utc,
        symbol=symbol,
        source_url=source_url,
        nav_as_of=nav_as_of,
        raw_sha256=raw_sha256,
        raw_file=raw_file,
        **values,
    )


# ----------------------------------------------------------------------
# 存檔(追加式)
# ----------------------------------------------------------------------


def shares_readings_path(root: Path | str) -> Path:
    return Path(root) / SHARES_READINGS_FILE


def read_shares_readings(root: Path | str) -> list[dict[str, str]]:
    """讀回整份存檔;還未抓過就是空清單(不是錯)。"""
    path = shares_readings_path(root)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if rows and tuple(rows[0]) != SHARES_COLUMNS:
        raise DataFetchFailed(
            f"存檔 {path} 的欄與現行版式對不上;現行是 {SHARES_COLUMNS},"
            f"檔內是 {tuple(rows[0])}——舊列不改寫,請先對清楚才續寫"
        )
    return rows


def append_shares_reading(root: Path | str, reading: SharesReading) -> None:
    """追加一列。舊列一個字都不動;檔不存在就連表頭一齊開。"""
    path = shares_readings_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SHARES_COLUMNS))
        if fresh:
            writer.writeheader()
        writer.writerow(reading.as_row())


def _rows_on(rows: Sequence[Mapping[str, str]], symbol: str, day: str) -> list[Mapping[str, str]]:
    return [row for row in rows if row["symbol"] == symbol and row["captured_at_utc"][:10] == day]


def shares_unchanged(previous: Mapping[str, str], reading: SharesReading) -> bool:
    row = reading.as_row()
    return all(previous.get(name) == row[name] for name in SHARES_VALUE_COLUMNS)


def _already_have(rows: Sequence[Mapping[str, str]], reading: SharesReading) -> bool:
    """那一日已經有一列數字一模一樣就不再寫。

    比對那一日**全部**列而不只是最後一列:回填是照抓取編號逐次補的,可以在
    已有的列中間插入,只看最後一列就會重複寫。同日重跑一樣受惠——冪等的定義
    是「這一日已經記住了這個數」,不是「上一列剛好是這個數」。
    """
    return any(shares_unchanged(row, reading) for row in _rows_on(rows, reading.symbol, reading.captured_at_utc[:10]))


# ----------------------------------------------------------------------
# 抓一次
# ----------------------------------------------------------------------

CAPTURED = "已寫入"
UNCHANGED = "同日不變"
FAILED = "失敗"


@dataclass(frozen=True, slots=True)
class SharesOutcome:
    symbol: str
    status: str
    reading: SharesReading | None
    trouble: str | None


@dataclass(frozen=True, slots=True)
class SharesReport:
    capture_id: str
    captured_at_utc: str
    root: Path
    source_name: str
    outcomes: tuple[SharesOutcome, ...]

    @property
    def written(self) -> tuple[SharesOutcome, ...]:
        return tuple(item for item in self.outcomes if item.status == CAPTURED)

    @property
    def unchanged(self) -> tuple[SharesOutcome, ...]:
        return tuple(item for item in self.outcomes if item.status == UNCHANGED)

    @property
    def failed(self) -> tuple[SharesOutcome, ...]:
        return tuple(item for item in self.outcomes if item.status == FAILED)


def shares_capture_id_for(now: datetime) -> str:
    return now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _store_raw(root: Path, capture_id: str, symbol: str, page: str) -> tuple[str, str]:
    """原始頁面先落檔、後解析:解析當場失敗,那一日的頁面仍然留得住,補得回。"""
    relative = f"{RAW_DIR}/{capture_id}/{symbol}.html.gz"
    path = root / Path(relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = page.encode("utf-8")
    with gzip.open(path, "wb") as handle:
        handle.write(body)
    return hashlib.sha256(body).hexdigest(), relative


def _record(
    rows: list[dict[str, str]], root: Path, reading: SharesReading
) -> SharesOutcome:
    if _already_have(rows, reading):
        return SharesOutcome(reading.symbol, UNCHANGED, reading, None)
    append_shares_reading(root, reading)
    rows.append(reading.as_row())
    return SharesOutcome(reading.symbol, CAPTURED, reading, None)


def capture_shares(
    *,
    source: MultiplesSource,
    symbols: Sequence[str],
    root: Path | str,
    now: datetime,
    pause_seconds: float,
) -> SharesReport:
    """抓一次、逐隻落存檔;一隻斷纜不影響其餘,失敗逐隻記錄在報告裡。

    五個參數一個預設值都沒有(D-009):抓哪幾隻、落哪裡、當作幾點、停幾耐,
    全部是呼叫者才知道的事,程式代揀一個就等於把一個沒有人裁決過的判斷寫死。
    """
    if not symbols:
        raise DataFetchFailed("名單是空的,無數可抓")
    root_path = Path(root)
    moment = now.astimezone(timezone.utc)
    capture_id = shares_capture_id_for(moment)
    captured_at = moment.strftime("%Y-%m-%dT%H:%M:%SZ")

    existing = read_shares_readings(root_path)
    outcomes: list[SharesOutcome] = []
    for position, symbol in enumerate(symbols):
        if position and pause_seconds > 0:
            time.sleep(pause_seconds)  # 禮貌節奏:逐隻之間停一停,唔好連珠炮發
        try:
            url, page = source.fetch_page(symbol)
            digest, relative = _store_raw(root_path, capture_id, symbol, page)
            reading = parse_ssga_shares(
                page,
                symbol=symbol,
                source_url=url,
                capture_id=capture_id,
                captured_at_utc=captured_at,
                raw_sha256=digest,
                raw_file=relative,
            )
        except DataFetchFailed as exc:
            outcomes.append(SharesOutcome(symbol, FAILED, None, str(exc)))
            continue
        outcomes.append(_record(existing, root_path, reading))

    _ensure_readme(root_path)
    return SharesReport(
        capture_id=capture_id,
        captured_at_utc=captured_at,
        root=root_path,
        source_name=source.name,
        outcomes=tuple(outcomes),
    )


# ----------------------------------------------------------------------
# 回填(由板塊倍數存檔已落檔的原始頁面補)
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BackfillReport:
    source_root: Path
    root: Path
    captures: tuple[str, ...]
    outcomes: tuple[SharesOutcome, ...]

    @property
    def written(self) -> tuple[SharesOutcome, ...]:
        return tuple(item for item in self.outcomes if item.status == CAPTURED)

    @property
    def unchanged(self) -> tuple[SharesOutcome, ...]:
        return tuple(item for item in self.outcomes if item.status == UNCHANGED)

    @property
    def failed(self) -> tuple[SharesOutcome, ...]:
        return tuple(item for item in self.outcomes if item.status == FAILED)


def _captured_at_of(multiples_root: Path, capture_id: str, symbol: str) -> str:
    """回填那一列的抓取時間,以**當日真正抓那張頁面**那一刻為準,不是回填這一刻。

    優先由板塊倍數存檔的正本讀回原句;讀不到就由抓取編號還原(編號本身就是
    UTC 時間戳)。回填出來的列必須對得住它所根據的那張頁面,否則時點就假了。
    """
    from .multiples import read_readings  # noqa: PLC0415 - 只在回填時才需要

    try:
        for row in read_readings(multiples_root):
            if row["capture_id"] == capture_id and row["symbol"] == symbol:
                return row["captured_at_utc"]
    except DataFetchFailed:
        pass
    moment = datetime.strptime(capture_id, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def backfill_from_raw(
    *,
    multiples_root: Path | str,
    root: Path | str,
    symbols: Sequence[str],
) -> BackfillReport:
    """由板塊倍數存檔已落檔的原始頁面,補回開檔之前那幾次的在外股數。

    一個網都不出:讀的是 ``vintage/sector-multiples/raw/`` 裡已經在手的頁面。
    ``raw_file`` 記的是那張原頁的位置(相對本存檔根),指得返去證據本身,
    不再複製一份——同一張頁面存兩次只會令兩份存檔的雜湊各講各話。
    """
    source_root = Path(multiples_root)
    root_path = Path(root)
    raw_root = source_root / RAW_DIR
    if not raw_root.is_dir():
        raise DataFetchFailed(
            f"回填不到:{raw_root} 不存在——板塊倍數存檔還未落過任何原始頁面"
        )

    wanted = set(symbols)
    existing = read_shares_readings(root_path)
    outcomes: list[SharesOutcome] = []
    captures = sorted(item.name for item in raw_root.iterdir() if item.is_dir())
    for capture_id in captures:
        for page_path in sorted((raw_root / capture_id).glob("*.html.gz")):
            symbol = page_path.name.split(".", 1)[0]
            if symbol not in wanted:
                continue
            body = page_path.read_bytes()
            page = gzip.decompress(body).decode("utf-8", errors="replace")
            relative = Path("..") / source_root.name / RAW_DIR / capture_id / page_path.name
            try:
                reading = parse_ssga_shares(
                    page,
                    symbol=symbol,
                    source_url=url_for(symbol),
                    capture_id=capture_id,
                    captured_at_utc=_captured_at_of(source_root, capture_id, symbol),
                    raw_sha256=hashlib.sha256(body).hexdigest(),
                    raw_file=relative.as_posix(),
                )
            except DataFetchFailed as exc:
                outcomes.append(SharesOutcome(symbol, FAILED, None, str(exc)))
                continue
            outcomes.append(_record(existing, root_path, reading))

    _ensure_readme(root_path)
    return BackfillReport(
        source_root=source_root,
        root=root_path,
        captures=tuple(captures),
        outcomes=tuple(outcomes),
    )


# ----------------------------------------------------------------------
# 說明檔
# ----------------------------------------------------------------------

SHARES_README_TEXT = """# 每日在外股數版本存檔(vintage)

由 `python -m karst.gateway shares capture` 逐日追加,KARST-130 開檔。

## 這是什麼

發行商(State Street)官網每日更新一次十一隻 SPDR 板塊 ETF 連 SPY 的
**在外股數(Shares Outstanding,即基金單位數)**,**原地覆寫、無官方存檔**——
今日拿到的只有今日一個數。單位數的每日增減就是**申贖流**(創設與贖回),
是判「錢在流入還是流出一個板塊」最乾淨的一條線。

現時倉內唯一一條申贖流是由富途的前復權成交量除以換手率**反推**出來的;
KARST-128 考出那條反推線在 2020-01 之前係一條**凍結的分母**——數值不動,
那一段根本不是真流。真流歷史因此只剩六年半,次數不夠過關,申贖流判「量不出」
(D-094)。這一份就是那條乾淨線的起點:**遲一日開始就永遠少一日。**

## 規矩

- **追加式**:一次抓取寫一列,舊列一個字都不動。
- **同日冪等**:同日已經記住了一模一樣的數就不再寫;
  **同日重跑而數字變了,兩列都留**,以 `captured_at_utc` 分辨——
  「同一日之內來源改過數」本身就是關於這個來源的事實,覆蓋掉就查不回。
- **不寫空值**:任何一格抓不到即整隻不收,並講明是哪一格斷了。
- **原始頁面先落檔、後解析**:解析當場失敗,`raw/` 內那一日的頁面仍在,
  日後修好解析器由存檔重跑補得回。
- **禮貌節奏**:逐隻之間停一秒,不連珠炮發。

## 檔案

| 落點 | 是什麼 | 入不入 git |
|---|---|---|
| `readings.csv` | 存檔正本,一列一次(抓取 × 代號) | **入**(這一份不可再生,必須跟住倉走) |
| `raw/<抓取編號>/<代號>.html.gz` | 當次原始頁面,做證據與補抓用 | 不入(體積大;`.gitignore` 已擋) |
| `說明.md` | 本檔 | 入 |

## 欄

`shares_outstanding_m` 是本存檔的主角:發行商自報的在外股數,**單位是百萬股**
(`1058.53` 即 1,058,530,000 股)。`nav_usd` 是每單位資產淨值(美元),
`aum_musd` 是資產淨值總額(百萬美元)——三格一齊存,是因為
「單位數 × NAV ≈ 總額」本身就是一條免費的自檢。

`nav_as_of` 是發行商自報的截數日,通常是抓取日的前一個交易日(知情滯後 T+1)——
**回測對齊要用截數日,不是抓取日**。

`raw_file` 以 `../sector-multiples/raw/...` 開頭的那些列,是由板塊倍數存檔已落檔
的原始頁面**回填**出來的(本存檔開檔之前那幾次);它們的 `captured_at_utc` 是
當日真正抓那張頁面那一刻,不是回填那一刻。
"""


def _ensure_readme(root: Path) -> None:
    path = root / SHARES_README_FILE
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SHARES_README_TEXT, encoding="utf-8")


# ----------------------------------------------------------------------
# 讀回
# ----------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SharesSummary:
    rows: int
    captures: int
    symbols: tuple[str, ...]
    first_day: str
    last_day: str


def summarise_shares(rows: Sequence[Mapping[str, str]]) -> SharesSummary:
    days = sorted({row["captured_at_utc"][:10] for row in rows})
    return SharesSummary(
        rows=len(rows),
        captures=len({row["capture_id"] for row in rows}),
        symbols=tuple(sorted({row["symbol"] for row in rows})),
        first_day=days[0] if days else "",
        last_day=days[-1] if days else "",
    )


def latest_shares_per_symbol(rows: Iterable[Mapping[str, str]]) -> list[dict[str, str]]:
    """每隻代號最新的一列,按代號排序;存檔空即空清單。"""
    newest: dict[str, dict[str, str]] = {}
    for row in rows:
        newest[row["symbol"]] = dict(row)
    return [newest[symbol] for symbol in sorted(newest)]


def shares_history_of(
    rows: Iterable[Mapping[str, str]], symbol: str, *, since: str | None
) -> list[dict[str, str]]:
    """某隻代號的逐次讀數,按抓取時間排;``since`` 留空即全部(留空是「不篩」)。"""
    picked = [dict(row) for row in rows if row["symbol"] == symbol]
    if since is not None:
        picked = [row for row in picked if row["captured_at_utc"][:10] >= since]
    return sorted(picked, key=lambda row: row["captured_at_utc"])


__all__ = [
    "DEFAULT_MULTIPLES_ROOT",
    "DEFAULT_SHARES_ROOT",
    "POLITE_PAUSE_SECONDS",
    "SHARES_COLUMNS",
    "SHARES_UNIVERSE",
    "SHARES_VALUE_COLUMNS",
    "BackfillReport",
    "SharesReading",
    "SharesReport",
    "SharesSummary",
    "SsgaMultiplesSource",
    "StaticMultiplesSource",
    "append_shares_reading",
    "backfill_from_raw",
    "capture_shares",
    "latest_shares_per_symbol",
    "parse_ssga_shares",
    "read_shares_readings",
    "shares_history_of",
    "shares_readings_path",
    "summarise_shares",
]
