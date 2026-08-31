"""KARST-130 驗收:每日在外股數存檔件(SSGA 十二隻 ETF)。

每個測試對住票上一條驗收條件:

  · 命令跑得、十二隻齊、同日重跑冪等;原始頁面先落檔後解析;
    抓取時間與截數日兩欄齊 → ``test_capture_*`` 五條、``test_cli_capture_*`` 兩條
  · 欄位斷纜響亮失敗,不寫空值 → ``test_parse_*`` 四條
  · 由已存 raw 頁回填,重跑不重複 → ``test_backfill_*`` 三條
  · 生產庫雜湊不變(存檔屬新檔,不動既有庫)→ ``test_cli_shares_never_opens_the_definition_store``

樣本 ``tests/frozen/karst-130-ssga-xlk-nav-2026-08-31.html`` 是由 2026-08-31 實抓、
已落檔的原始頁面逐字抽出來的那兩截(自報代號 + 「Fund Net Asset Value」一節),
不是手砌的假形狀。真實抓取那一條要連網,離線即 skip。

跑法:``PYTHONUTF8=1 python -m pytest tests/test_fund_shares_vintage.py -q``
"""

from __future__ import annotations

import gzip
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from karst.data.errors import DataFetchFailed
from karst.data.fund_shares import (
    CAPTURED,
    FAILED,
    SHARES_COLUMNS,
    SHARES_UNIVERSE,
    UNCHANGED,
    StaticMultiplesSource,
    backfill_from_raw,
    capture_shares,
    parse_ssga_shares,
    read_shares_readings,
)
from karst.gateway.cli import main

FIXTURE = Path(__file__).parent / "frozen" / "karst-130-ssga-xlk-nav-2026-08-31.html"
MOMENT = datetime(2026, 8, 31, 4, 15, 30, tzinfo=timezone.utc)


@pytest.fixture()
def page() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def _parse(page: str, symbol: str = "XLK"):
    return parse_ssga_shares(
        page,
        symbol=symbol,
        source_url="https://example.invalid/fund",
        capture_id="20260831T041530Z",
        captured_at_utc="2026-08-31T04:15:30Z",
        raw_sha256="0" * 64,
        raw_file="raw/20260831T041530Z/XLK.html.gz",
    )


def _capture(source, symbols, root, now):
    return capture_shares(
        source=source, symbols=symbols, root=root, now=now, pause_seconds=0.0
    )


# ----------------------------------------------------------------------
# 解析:斷纜要響亮,不寫空值
# ----------------------------------------------------------------------


def test_parse_reads_shares_outstanding_off_the_real_page(page: str) -> None:
    """實抓頁面的三格連截數日全部讀得出,而且是來源原文的數字。"""
    reading = _parse(page)
    assert reading.shares_outstanding_m == "651.66"   # 來源原文 "651.66 M"
    assert reading.nav_usd == "185.69"                # 來源原文 "$185.69"
    assert reading.aum_musd == "121007.28"            # 來源原文 "$121,007.28 M"
    assert reading.nav_as_of == "2026-08-28"          # 來源原文 "as of Aug 28 2026"
    assert reading.captured_at_utc == "2026-08-31T04:15:30Z"


def test_parse_keeps_shares_and_nav_and_aum_consistent(page: str) -> None:
    """單位數 × NAV ≈ 資產淨值:三格一齊存就有得自檢,對不上即那一日的頁面有古怪。"""
    reading = _parse(page)
    implied = float(reading.shares_outstanding_m) * float(reading.nav_usd)
    assert abs(implied - float(reading.aum_musd)) / float(reading.aum_musd) < 0.001


def test_parse_fails_loudly_when_the_shares_field_is_renamed(page: str) -> None:
    """來源把欄改名即整隻不收,並講明斷了哪一格——不以空白冒充成功。"""
    broken = page.replace("Shares Outstanding", "Units Outstanding")
    with pytest.raises(DataFetchFailed) as caught:
        _parse(broken)
    assert "Shares Outstanding" in str(caught.value)
    assert "shares_outstanding_m" in str(caught.value)


def test_parse_fails_loudly_when_the_shares_unit_changed(page: str) -> None:
    """單位由百萬股變成裸股數就不是同一個數,寧可不收也不強行換算。"""
    broken = page.replace("651.66 M", "651,660,000")
    with pytest.raises(DataFetchFailed) as caught:
        _parse(broken)
    assert "百萬股" in str(caught.value)


def test_parse_fails_loudly_when_the_page_is_a_different_fund(page: str) -> None:
    """抓回來的頁面自報不是這一隻,即網址對照表有變,整隻不收。"""
    with pytest.raises(DataFetchFailed) as caught:
        _parse(page, symbol="XLE")
    assert "'XLK'" in str(caught.value)


# ----------------------------------------------------------------------
# 抓一次:追加式、同日冪等、原始頁面先落檔
# ----------------------------------------------------------------------


def test_capture_writes_one_row_per_symbol_with_both_timestamps(
    tmp_path: Path, page: str
) -> None:
    """一次抓取每隻一列,抓取時間與發行商自報截數日兩欄齊,欄次序即存檔版式。"""
    pages = {symbol: page.replace('value="XLK"', f'value="{symbol}"')
             for symbol in SHARES_UNIVERSE}
    report = _capture(StaticMultiplesSource(pages), SHARES_UNIVERSE, tmp_path, MOMENT)
    assert len(report.written) == len(SHARES_UNIVERSE) == 12

    rows = read_shares_readings(tmp_path)
    assert tuple(rows[0]) == SHARES_COLUMNS
    assert {row["symbol"] for row in rows} == set(SHARES_UNIVERSE)
    for row in rows:
        assert row["captured_at_utc"] == "2026-08-31T04:15:30Z"
        assert row["nav_as_of"] == "2026-08-28"


def test_capture_stores_the_raw_page_before_parsing(tmp_path: Path, page: str) -> None:
    """原始頁面先落檔:即使解析當場失敗,那一日的頁面仍在,日後補得回。"""
    broken = page.replace("Shares Outstanding", "Unit Count")
    source = StaticMultiplesSource({"XLK": broken})
    report = _capture(source, ("XLK",), tmp_path, MOMENT)
    assert [item.status for item in report.outcomes] == [FAILED]
    assert not read_shares_readings(tmp_path)

    stored = tmp_path / "raw" / report.capture_id / "XLK.html.gz"
    assert stored.exists()
    assert gzip.decompress(stored.read_bytes()).decode("utf-8") == broken


def test_capture_twice_on_the_same_day_with_the_same_numbers_adds_no_row(
    tmp_path: Path, page: str
) -> None:
    """同日重跑冪等:數字一格都沒變,就不再寫一列。"""
    source = StaticMultiplesSource({"XLK": page})
    _capture(source, ("XLK",), tmp_path, MOMENT)
    again = _capture(source, ("XLK",), tmp_path, MOMENT + timedelta(hours=3))
    assert [item.status for item in again.outcomes] == [UNCHANGED]
    assert len(read_shares_readings(tmp_path)) == 1


def test_capture_twice_on_the_same_day_with_different_numbers_keeps_both_rows(
    tmp_path: Path, page: str
) -> None:
    """同日第二次抓到不同單位數,兩條都留——申贖流正正住在這個差額裡,覆蓋掉就查不回。"""
    _capture(StaticMultiplesSource({"XLK": page}), ("XLK",), tmp_path, MOMENT)
    revised = StaticMultiplesSource({"XLK": page.replace("651.66 M", "654.16 M")})
    again = _capture(revised, ("XLK",), tmp_path, MOMENT + timedelta(hours=6))
    assert [item.status for item in again.outcomes] == [CAPTURED]

    rows = read_shares_readings(tmp_path)
    assert [row["shares_outstanding_m"] for row in rows] == ["651.66", "654.16"]
    assert rows[0]["captured_at_utc"] != rows[1]["captured_at_utc"]


def test_capture_on_a_new_day_adds_a_row_even_when_nothing_moved(
    tmp_path: Path, page: str
) -> None:
    """隔日再抓,單位數沒變一樣要寫一列——沒有那一列就分不出「當日零申贖」與「當日沒抓」。"""
    source = StaticMultiplesSource({"XLK": page})
    _capture(source, ("XLK",), tmp_path, MOMENT)
    _capture(source, ("XLK",), tmp_path, MOMENT + timedelta(days=1))
    assert len(read_shares_readings(tmp_path)) == 2


# ----------------------------------------------------------------------
# 回填:由板塊倍數存檔已落檔的原始頁面補
# ----------------------------------------------------------------------


def _seed_multiples_raw(root: Path, capture_id: str, pages: dict[str, str]) -> None:
    folder = root / "raw" / capture_id
    folder.mkdir(parents=True, exist_ok=True)
    for symbol, body in pages.items():
        with gzip.open(folder / f"{symbol}.html.gz", "wb") as handle:
            handle.write(body.encode("utf-8"))


def test_backfill_reads_shares_out_of_the_already_stored_multiples_pages(
    tmp_path: Path, page: str
) -> None:
    """票的第一步:已存的板塊倍數原始頁面本來就有這一格,補得回,一個網都不出。"""
    source_root, root = tmp_path / "sector-multiples", tmp_path / "fund-shares"
    _seed_multiples_raw(source_root, "20260831T143807Z", {"XLK": page})

    report = backfill_from_raw(
        multiples_root=source_root, root=root, symbols=("XLK",)
    )
    assert len(report.written) == 1
    row = read_shares_readings(root)[0]
    assert row["shares_outstanding_m"] == "651.66"
    # 抓取時間是**當日真正抓那張頁面**那一刻(由抓取編號還原),不是回填這一刻。
    assert row["captured_at_utc"] == "2026-08-31T14:38:07Z"
    assert row["capture_id"] == "20260831T143807Z"
    # 指得返去證據本身,不再複製一份頁面。
    assert row["raw_file"] == "../sector-multiples/raw/20260831T143807Z/XLK.html.gz"


def test_backfill_twice_writes_nothing_the_second_time(tmp_path: Path, page: str) -> None:
    """回填重跑冪等:同一日已經記住了同一個數,就不再寫。"""
    source_root, root = tmp_path / "sector-multiples", tmp_path / "fund-shares"
    _seed_multiples_raw(source_root, "20260831T143807Z", {"XLK": page})
    backfill_from_raw(multiples_root=source_root, root=root, symbols=("XLK",))
    again = backfill_from_raw(multiples_root=source_root, root=root, symbols=("XLK",))
    assert len(again.written) == 0
    assert len(again.unchanged) == 1
    assert len(read_shares_readings(root)) == 1


def test_backfill_of_several_same_day_captures_keeps_only_the_distinct_numbers(
    tmp_path: Path, page: str
) -> None:
    """同一日抓過幾次,數字一樣的只留一列,改過的兩列都留——與抓取那條同一把尺。"""
    source_root, root = tmp_path / "sector-multiples", tmp_path / "fund-shares"
    _seed_multiples_raw(source_root, "20260831T143807Z", {"XLK": page})
    _seed_multiples_raw(source_root, "20260831T143824Z", {"XLK": page})
    _seed_multiples_raw(
        source_root, "20260831T173116Z", {"XLK": page.replace("651.66 M", "654.16 M")}
    )
    report = backfill_from_raw(multiples_root=source_root, root=root, symbols=("XLK",))
    assert len(report.written) == 2
    assert [row["shares_outstanding_m"] for row in read_shares_readings(root)] == [
        "651.66", "654.16"
    ]


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------


@pytest.fixture()
def karst(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """回傳一個「跑一句 karst 命令」的函數:(回傳碼, 螢幕輸出)。"""
    monkeypatch.setenv("KARST_WRITER", "KARST-130-測試")
    store = tmp_path / "karst.sqlite"

    def run(*argv: str) -> tuple[int, str]:
        buffer = io.StringIO()
        code = main(["--store", str(store), *argv], out=buffer)
        return code, buffer.getvalue()

    run.store = store  # type: ignore[attr-defined]
    return run


@pytest.fixture()
def offline_source(monkeypatch: pytest.MonkeyPatch, page: str):
    """把 CLI 用的真抓來源換成離線孖生:命令列驗得到,一次網都不出。"""
    import karst.data.fund_shares as fund_shares

    pages = {symbol: page.replace('value="XLK"', f'value="{symbol}"')
             for symbol in SHARES_UNIVERSE}
    monkeypatch.setattr(
        fund_shares, "SsgaMultiplesSource", lambda *a, **k: StaticMultiplesSource(pages)
    )
    return pages


def test_cli_capture_then_list_prints_a_table(karst, offline_source, tmp_path: Path) -> None:
    """一句命令抓齊十二隻,再一句讀得返出來列成表。"""
    root = tmp_path / "vintage"
    code, output = karst("shares", "capture", "--root", str(root), "--pause", "0")
    assert code == 0
    assert "在外股數存檔" in output
    for symbol in SHARES_UNIVERSE:
        assert symbol in output

    code, listed = karst("shares", "list", "--root", str(root))
    assert code == 0
    assert "每隻最新一列" in listed
    assert "651.66" in listed
    assert f"{len(SHARES_UNIVERSE)} 隻" in listed


def test_cli_capture_returns_non_zero_when_the_field_broke(
    karst, monkeypatch: pytest.MonkeyPatch, page: str, tmp_path: Path
) -> None:
    """來源改版,命令要響亮失敗(回傳碼非零)並講明斷了哪一格。"""
    import karst.data.fund_shares as fund_shares

    broken = page.replace("Shares Outstanding", "Units in Issue")
    monkeypatch.setattr(
        fund_shares, "SsgaMultiplesSource",
        lambda *a, **k: StaticMultiplesSource({"XLK": broken}),
    )
    code, output = karst(
        "shares", "capture", "--root", str(tmp_path / "vintage"),
        "--symbol", "XLK", "--pause", "0",
    )
    assert code == 1
    assert "Shares Outstanding" in output
    assert "不寫空值" in output


def test_cli_backfill_then_list_shows_the_backfilled_history(
    karst, tmp_path: Path, page: str
) -> None:
    """一句命令由已存原始頁面回填,再一句讀得返該隻的逐次讀數。"""
    source_root, root = tmp_path / "sector-multiples", tmp_path / "fund-shares"
    _seed_multiples_raw(source_root, "20260831T143807Z", {"XLK": page})
    code, output = karst(
        "shares", "backfill", "--root", str(root), "--from-root", str(source_root)
    )
    assert code == 0
    assert "新寫 1 列" in output

    code, listed = karst("shares", "list", "--root", str(root), "--symbol", "XLK")
    assert code == 0
    assert "XLK 逐次讀數" in listed
    assert "651.66" in listed


def test_cli_shares_never_opens_the_definition_store(
    karst, offline_source, tmp_path: Path
) -> None:
    """存檔屬新檔:跑這幾句命令,單一定義庫連開都不開,庫檔一個位元都不會動。"""
    root = tmp_path / "vintage"
    karst("shares", "capture", "--root", str(root), "--pause", "0")
    karst("shares", "list", "--root", str(root))
    assert not karst.store.exists()


# ----------------------------------------------------------------------
# 真實抓取(要連網;離線即 skip,不以樣本冒充實抓)
# ----------------------------------------------------------------------


def test_real_fetch_of_one_fund_page(tmp_path: Path) -> None:
    """真的向發行商抓一隻,證明網址與解析對得住今日的頁面。"""
    from karst.data.fund_shares import SsgaMultiplesSource

    try:
        report = capture_shares(
            source=SsgaMultiplesSource(),
            symbols=("XLK",),
            root=tmp_path,
            now=datetime.now(timezone.utc),
            pause_seconds=0.0,
        )
    except DataFetchFailed as exc:  # pragma: no cover - 視乎當時有沒有網
        pytest.skip(f"離線或來源不通,跳過真實抓取:{exc}")
    if report.failed:  # pragma: no cover - 來源改版時才會走到
        pytest.fail(f"實抓解析失敗:{report.failed[0].trouble}")
    reading = report.outcomes[0].reading
    assert reading is not None
    assert float(reading.shares_outstanding_m) > 0
    assert reading.nav_as_of <= datetime.now(timezone.utc).date().isoformat()
