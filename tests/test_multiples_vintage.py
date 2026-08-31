"""KARST-124 驗收:板塊倍數每日存檔件(依 D-084)。

每個測試對住票上一條驗收條件:

  · 一句命令抓齊十隻 ETF 的前瞻市盈率落追加式存檔,連時間戳與來源網址;
    同日重跑冪等 → ``test_capture_*`` 四條
  · 欄位斷纜響亮失敗(模擬來源缺欄位);不寫空值 → ``test_parse_*`` 四條
  · CLI 讀得返存檔列成表 → ``test_cli_*`` 三條
  · 生產庫雜湊不變(存檔屬新檔,不動既有庫) → ``test_cli_multiples_never_opens_the_definition_store``

樣本 ``tests/frozen/karst-124-ssga-xlk-2026-08-31.html`` 是 2026-08-31 由發行商頁面
實抓、逐字不改抽出來的那幾截,不是手砌的假形狀。真實抓取那一條要連網,離線即 skip。

跑法:``PYTHONUTF8=1 python -m pytest tests/test_multiples_vintage.py -q``
"""

from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from karst.data.errors import DataFetchFailed
from karst.data.multiples import (
    CAPTURED,
    FAILED,
    MULTIPLES_UNIVERSE,
    READING_COLUMNS,
    UNCHANGED,
    StaticMultiplesSource,
    capture_multiples,
    parse_ssga_fund_page,
    read_readings,
)
from karst.gateway.cli import main

FIXTURE = Path(__file__).parent / "frozen" / "karst-124-ssga-xlk-2026-08-31.html"
MOMENT = datetime(2026, 8, 31, 4, 15, 30, tzinfo=timezone.utc)


@pytest.fixture()
def page() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def _parse(page: str, symbol: str = "XLK"):
    return parse_ssga_fund_page(
        page,
        symbol=symbol,
        source_url="https://example.invalid/fund",
        capture_id="20260831T041530Z",
        captured_at_utc="2026-08-31T04:15:30Z",
        raw_sha256="0" * 64,
        raw_file="raw/20260831T041530Z/XLK.html.gz",
    )


# ----------------------------------------------------------------------
# 解析:斷纜要響亮,不寫空值
# ----------------------------------------------------------------------


def test_parse_reads_every_valuation_field_off_the_real_page(page: str) -> None:
    """實抓頁面的八格估值欄全部讀得出,而且是來源原文的數字。"""
    reading = _parse(page)
    assert reading.forward_pe_fy1 == "26.03"
    assert reading.trailing_pe == "34.25"
    assert reading.price_cash_flow == "29.00"
    assert reading.price_book == "11.66"
    assert reading.est_eps_growth_3_5y_pct == "35.82"
    assert reading.index_holdings == "73"
    assert reading.weighted_avg_market_cap_musd == "2004984.80"
    assert reading.index_as_of == reading.fund_as_of == "2026-08-28"


def test_parse_shouts_which_field_broke_when_the_source_renames_a_column(page: str) -> None:
    """來源改欄名,錯誤訊息要指得出是哪一格斷了,不是靜靜留空。"""
    changed = page.replace("Price/Cash Flow", "Price/Cashflow")
    with pytest.raises(DataFetchFailed, match="Price/Cash Flow") as caught:
        _parse(changed)
    assert "price_cash_flow" in str(caught.value)


def test_parse_shouts_when_a_whole_section_disappears(page: str) -> None:
    """整節不見(來源改版),整隻不收,並講明見到的是哪幾節。"""
    changed = page.replace("Index Characteristics", "Index Snapshot")
    with pytest.raises(DataFetchFailed, match="Index Characteristics"):
        _parse(changed)


def test_parse_refuses_a_page_that_says_it_is_another_fund(page: str) -> None:
    """頁面自報的代號對不上要抓的那一隻,寧可整隻不收——網址對照表可能有錯。"""
    with pytest.raises(DataFetchFailed, match="不是這一隻"):
        _parse(page, symbol="XLF")


def test_parse_refuses_a_market_cap_whose_unit_changed(page: str) -> None:
    """單位由百萬變十億就不是同一個數;不強行換算,響亮失敗。"""
    changed = page.replace("$2,004,984.80 M", "$2,004.98 B")
    with pytest.raises(DataFetchFailed, match="百萬美元"):
        _parse(changed)


# ----------------------------------------------------------------------
# 存檔:追加式與同日冪等
# ----------------------------------------------------------------------


def test_capture_writes_one_row_per_symbol_with_timestamp_and_source_url(
    tmp_path: Path, page: str
) -> None:
    """一句命令抓齊名單,每隻一列,連抓取時間戳與來源網址。"""
    source = StaticMultiplesSource({"XLK": page, "SPY": page.replace('value="XLK"', 'value="SPY"')})
    report = capture_multiples(
        source=source, symbols=("XLK", "SPY"), root=tmp_path, now=MOMENT
    )
    assert [item.status for item in report.outcomes] == [CAPTURED, CAPTURED]

    rows = read_readings(tmp_path)
    assert len(rows) == 2
    assert tuple(rows[0]) == READING_COLUMNS
    assert rows[0]["captured_at_utc"] == "2026-08-31T04:15:30Z"
    assert rows[0]["source_url"].startswith("https://www.ssga.com/")
    assert rows[0]["forward_pe_fy1"] == "26.03"
    # 原始頁面先落檔、後解析:即使日後解析失敗,那一日的頁面仍在。
    assert (tmp_path / rows[0]["raw_file"]).exists()
    assert (tmp_path / "說明.md").exists()


def test_capture_twice_on_the_same_day_with_the_same_numbers_adds_no_row(
    tmp_path: Path, page: str
) -> None:
    """同日重跑冪等:數字一格都沒變,就不再寫一列。"""
    source = StaticMultiplesSource({"XLK": page})
    capture_multiples(source=source, symbols=("XLK",), root=tmp_path, now=MOMENT)
    again = capture_multiples(
        source=source, symbols=("XLK",), root=tmp_path, now=MOMENT + timedelta(hours=3)
    )
    assert [item.status for item in again.outcomes] == [UNCHANGED]
    assert len(read_readings(tmp_path)) == 1


def test_capture_twice_on_the_same_day_with_different_numbers_keeps_both_rows(
    tmp_path: Path, page: str
) -> None:
    """同日第二次抓到不同數字,兩條都留,以抓取時間戳分辨,永不覆蓋。"""
    first = StaticMultiplesSource({"XLK": page})
    capture_multiples(source=first, symbols=("XLK",), root=tmp_path, now=MOMENT)

    revised = StaticMultiplesSource({"XLK": page.replace(">26.03<", ">27.11<")})
    later = MOMENT + timedelta(hours=6)
    again = capture_multiples(source=revised, symbols=("XLK",), root=tmp_path, now=later)
    assert [item.status for item in again.outcomes] == [CAPTURED]

    rows = read_readings(tmp_path)
    assert [row["forward_pe_fy1"] for row in rows] == ["26.03", "27.11"]
    assert rows[0]["captured_at_utc"] != rows[1]["captured_at_utc"]


def test_capture_on_a_new_day_adds_a_row_even_when_nothing_moved(
    tmp_path: Path, page: str
) -> None:
    """隔日再抓,數字沒變一樣要寫一列——沒有那一列就分不出「當日不變」與「當日沒抓」。"""
    source = StaticMultiplesSource({"XLK": page})
    capture_multiples(source=source, symbols=("XLK",), root=tmp_path, now=MOMENT)
    capture_multiples(
        source=source, symbols=("XLK",), root=tmp_path, now=MOMENT + timedelta(days=1)
    )
    assert len(read_readings(tmp_path)) == 2


def test_capture_writes_nothing_for_a_symbol_whose_field_broke(tmp_path: Path, page: str) -> None:
    """一隻斷纜不拖累其餘;斷了那隻一列都不寫,而且逐隻講明斷了哪一格。"""
    broken = page.replace("Price/Book Ratio", "Price/Book")
    source = StaticMultiplesSource(
        {"XLK": page, "SPY": broken.replace('value="XLK"', 'value="SPY"')}
    )
    report = capture_multiples(
        source=source, symbols=("XLK", "SPY"), root=tmp_path, now=MOMENT
    )
    assert [item.status for item in report.outcomes] == [CAPTURED, FAILED]
    assert "Price/Book Ratio" in report.failed[0].trouble

    rows = read_readings(tmp_path)
    assert [row["symbol"] for row in rows] == ["XLK"]
    # 斷纜那隻的原始頁面照樣留住,修好解析之後補得回。
    assert (tmp_path / "raw" / report.capture_id / "SPY.html.gz").exists()


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------


@pytest.fixture()
def karst(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """回傳一個「跑一句 karst 命令」的函數:(回傳碼, 螢幕輸出)。"""
    monkeypatch.setenv("KARST_WRITER", "KARST-124-測試")
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
    import karst.data.multiples as multiples

    pages = {symbol: page.replace('value="XLK"', f'value="{symbol}"')
             for symbol in MULTIPLES_UNIVERSE}

    def build(*args, **kwargs):
        return StaticMultiplesSource(pages)

    monkeypatch.setattr(multiples, "SsgaMultiplesSource", build)
    return pages


def test_cli_capture_then_list_prints_a_table(karst, offline_source, tmp_path: Path) -> None:
    """一句命令抓齊全份名單,再一句讀得返出來列成表。"""
    root = tmp_path / "vintage"
    code, output = karst("multiples", "capture", "--root", str(root))
    assert code == 0
    assert "板塊倍數存檔" in output
    for symbol in MULTIPLES_UNIVERSE:
        assert symbol in output
    # 票點名的十隻(九隻板塊 + SPY)全部在內。
    for symbol in ("XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY", "SPY"):
        assert symbol in output

    code, listed = karst("multiples", "list", "--root", str(root))
    assert code == 0
    assert "每隻最新一列" in listed
    assert "26.03" in listed
    assert f"{len(MULTIPLES_UNIVERSE)} 隻" in listed


def test_cli_list_of_one_symbol_shows_its_history(karst, offline_source, tmp_path: Path) -> None:
    """給 --symbol 即列該隻的逐次讀數,存檔查得回。"""
    root = tmp_path / "vintage"
    karst("multiples", "capture", "--root", str(root), "--symbol", "XLK")
    code, output = karst("multiples", "list", "--root", str(root), "--symbol", "XLK")
    assert code == 0
    assert "XLK 逐次讀數" in output
    assert "26.03" in output


def test_cli_capture_returns_non_zero_when_a_field_broke(
    karst, monkeypatch: pytest.MonkeyPatch, page: str, tmp_path: Path
) -> None:
    """來源改版,命令要響亮失敗(回傳碼非零)並講明斷了哪一格。"""
    import karst.data.multiples as multiples

    broken = page.replace("Price/Earnings Ratio FY1", "Fwd P/E")
    monkeypatch.setattr(multiples, "SsgaMultiplesSource", lambda *a, **k: StaticMultiplesSource({"XLK": broken}))
    code, output = karst(
        "multiples", "capture", "--root", str(tmp_path / "vintage"), "--symbol", "XLK"
    )
    assert code == 1
    assert "Price/Earnings Ratio FY1" in output
    assert "不寫空值" in output


def test_cli_multiples_never_opens_the_definition_store(karst, offline_source, tmp_path: Path) -> None:
    """存檔屬新檔:跑這兩句命令,單一定義庫連開都不開,庫檔一個位元都不會動。"""
    root = tmp_path / "vintage"
    karst("multiples", "capture", "--root", str(root))
    karst("multiples", "list", "--root", str(root))
    assert not karst.store.exists()


# ----------------------------------------------------------------------
# 真實抓取(要連網;離線即 skip,不以樣本冒充實抓)
# ----------------------------------------------------------------------


def test_real_fetch_of_one_fund_page(tmp_path: Path) -> None:
    """真的向發行商抓一隻,證明網址與解析對得住今日的頁面。"""
    from karst.data.multiples import SsgaMultiplesSource

    try:
        report = capture_multiples(
            source=SsgaMultiplesSource(),
            symbols=("XLK",),
            root=tmp_path,
            now=datetime.now(timezone.utc),
        )
    except DataFetchFailed as exc:  # pragma: no cover - 視乎當時有沒有網
        pytest.skip(f"離線或來源不通,跳過真實抓取:{exc}")
    if report.failed:  # pragma: no cover - 來源改版時才會走到
        pytest.fail(f"實抓解析失敗:{report.failed[0].trouble}")
    reading = report.outcomes[0].reading
    assert reading is not None
    assert float(reading.forward_pe_fy1) > 0
    assert reading.index_as_of <= datetime.now(timezone.utc).date().isoformat()
