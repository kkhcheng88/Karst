"""KARST-034 驗收:唯一入口的數據快照子命令。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況。
一律經命令列那道門(``karst.gateway.cli.main``)——與人手用的是同一條路。

真實抓取那一條要連網,離線即 skip 並註明(沿用 tests/test_data_yfinance.py 做法);
命令列本身用 csv 來源適配器離線驗得到,不以合成數據冒充真實抓取。

跑法:``PYTHONUTF8=1 python -m pytest tests/test_gateway_data.py -q``
"""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pandas as pd
import pytest

from karst.gateway.cli import main
from karst.store import DefinitionStore

REPO_ROOT = Path(__file__).resolve().parents[1]

WINDOW = ("2024-01-02", "2024-01-31")
# 離線那幾條只用 ETF:起步名單上的 ETF 不掛 SEC CIK,故整條管線一次網都不用出。
OFFLINE_TICKERS = ("SPY", "QQQ")


@pytest.fixture()
def karst(tmp_path, monkeypatch):
    """回傳一個「跑一句 karst 命令」的函數:(回傳碼, 螢幕輸出)。"""
    monkeypatch.delenv("KARST_GATEWAY_KEY", raising=False)
    monkeypatch.setenv("KARST_WRITER", "KARST-034-gateway")
    path = str(tmp_path / "karst.sqlite")

    def run(*argv: str) -> tuple[int, str]:
        buffer = io.StringIO()
        code = main(["--store", path, *argv], out=buffer)
        return code, buffer.getvalue()

    run.path = path  # type: ignore[attr-defined]
    run.root = str(tmp_path / "snapshots")  # type: ignore[attr-defined]
    return run


@pytest.fixture()
def bars_file(tmp_path) -> str:
    """一份離線日線檔:兩隻 ETF、2024 年 1 月的營業日,價格照公式生成。"""
    days = pd.bdate_range(*WINDOW)
    rows = []
    for index, day in enumerate(days):
        for ticker, base in (("SPY", 470.0), ("QQQ", 400.0)):
            close = base + index * 0.5
            rows.append(
                {
                    "date": day.date().isoformat(),
                    "ticker": ticker,
                    "open": close - 0.4,
                    "high": close + 0.6,
                    "low": close - 0.8,
                    "close": close,
                    "volume": 1_000_000 + index,
                }
            )
    path = tmp_path / "bars.csv"
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8")
    return str(path)


@pytest.fixture(scope="module")
def online() -> None:
    pytest.importorskip("yfinance", reason="未安裝 yfinance,跳過真實抓取")
    from karst.data import DataFetchFailed, YFinanceSource

    try:
        YFinanceSource().fetch_daily_bars(["SPY"], "2024-01-02", "2024-01-05")
    except DataFetchFailed as exc:
        pytest.skip(f"離線或來源不通,跳過真實抓取:{exc}")


def snapshot_id_of(output: str) -> str:
    match = re.search(r"已凍結數據快照 (\S+)", output)
    assert match, output
    return match.group(1)


def take_offline_snapshot(karst, bars_file: str, *, end: str = WINDOW[1]) -> tuple[int, str]:
    return karst(
        "data", "snapshot",
        *[argument for ticker in OFFLINE_TICKERS for argument in ("--ticker", ticker)],
        "--start", WINDOW[0], "--end", end,
        "--source", "csv", "--bars", bars_file,
        "--root", karst.root,
    )


# 驗收條件 1:一句命令完成抓取、凍結、登記,並印出快照編號(真實抓取,離線自動略過)
def test_one_command_fetches_freezes_and_registers(karst, online):
    code, output = karst(
        "data", "snapshot", "--ticker", "SPY", "--ticker", "QQQ",
        "--start", WINDOW[0], "--end", WINDOW[1], "--root", karst.root,
    )
    assert code == 0
    snapshot_id = snapshot_id_of(output)
    assert "  來源      yfinance" in output

    # 抓:真數落了地;凍:快照目錄齊件;登:庫內查得回同一個編號
    from karst.data import read_price_panel, verify_snapshot

    with DefinitionStore.open(karst.path) as store:
        snapshot = store.get_snapshot(snapshot_id)
        assert snapshot.source == "yfinance"
        assert verify_snapshot(store, snapshot_id) == snapshot.content_hash
        panel = read_price_panel(store, snapshot_id)
        assert 19 <= len(panel.index) <= 21   # 2024 年 1 月的美股交易日
        assert panel.notna().all().all()


# 驗收條件 2:登記表直接查得到該快照的抓取時間與來源
def test_registry_answers_when_and_from_where(karst, bars_file):
    code, output = take_offline_snapshot(karst, bars_file)
    assert code == 0
    snapshot_id = snapshot_id_of(output)

    with DefinitionStore.open(karst.path) as store:
        fetch = store.snapshot_fetch(snapshot_id)
        assert fetch is not None
        assert pd.Timestamp(fetch.fetched_at).tz is not None       # 抓取時間帶時區
        assert (fetch.window_start, fetch.window_end) == WINDOW
        assert fetch.entity_count == 2
        assert store.get_snapshot(snapshot_id).source == "csv"     # 來源

        # 一次查詢即講齊「幾時抓、由哪裡抓」,不用翻快照目錄裡的清單檔
        listing = store.list_snapshots()[0]
        assert (listing.snapshot_id, listing.source) == (snapshot_id, "csv")
        assert listing.fetched_at == fetch.fetched_at

    assert "  抓取時間  " in output


# 驗收條件 3:karst data list 列得出庫內全部快照(編號、窗口、實體數、抓取時間)
def test_list_shows_every_snapshot_in_the_store(karst, bars_file):
    first = snapshot_id_of(take_offline_snapshot(karst, bars_file)[1])
    # 另一個窗口 = 另一批數據 = 另一個快照編號
    second = snapshot_id_of(take_offline_snapshot(karst, bars_file, end="2024-01-19")[1])
    assert first != second

    code, output = karst("data", "list")
    assert code == 0
    assert "共 2 個" in output
    for snapshot_id in (first, second):
        assert snapshot_id in output
    assert "2024-01-02~2024-01-31" in output      # 窗口
    assert "2024-01-02~2024-01-19" in output
    assert "2 個實體" in output                    # 實體數
    assert output.count("抓於 20") == 2            # 抓取時間


# KARST-065:宇宙名單登記可由唯一入口列出(含成分期與來源)
def test_universe_registry_lists_through_the_gateway(karst):
    code, output = karst("data", "universe")
    assert code == 0
    for key in ("starter", "factor-etf", "sector-etf", "sp500-historical"):
        assert key in output
    assert "fja05680/sp500" in output and "抓取日期 2026-08-29" in output

    code, sector_listing = karst("data", "universe", "--name", "sector-etf")
    assert code == 0
    assert "XLK" in sector_listing and "XLRE" in sector_listing and "XLC" in sector_listing
    assert "SPY" in sector_listing  # 主日曆錨連同十一隻行業 ETF 一併列出(KARST-073)

    code, listing = karst("data", "universe", "--name", "sp500-historical")
    assert code == 0
    assert "加入日期" in listing and "剔除日期" in listing
    assert "AABA  1999-12-08  2017-06-19" in listing      # 已剔除的代號帶兩個日期
    assert "AAPL" in listing

    # 查無此名即拒收,不猜
    code, refused = karst("data", "universe", "--name", "no-such-list")
    assert code == 1
    assert "沒有" in refused


# KARST-065:呼叫方交來的註記寫得入快照說明檔與清單(缺口逐條標示靠這一格)
def test_caller_notes_land_in_the_snapshot_readme(karst, bars_file):
    code, output = karst(
        "data", "snapshot",
        *[argument for ticker in OFFLINE_TICKERS for argument in ("--ticker", ticker)],
        "--start", WINDOW[0], "--end", WINDOW[1],
        "--source", "csv", "--bars", bars_file, "--root", karst.root,
        "--note", "缺口·抓不到 AABA(成分期 1999-12-08~2017-06-19)",
    )
    assert code == 0
    snapshot_id = snapshot_id_of(output)
    assert "缺口·抓不到 AABA" in output

    directory = Path(karst.root) / snapshot_id
    readme = (directory / "說明.md").read_text(encoding="utf-8")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert "缺口·抓不到 AABA" in readme
    assert "缺口·抓不到 AABA(成分期 1999-12-08~2017-06-19)" in manifest["notes"]
    # 註記不入內容雜湊:同一批數據不會因為多一句註記而凍出第二個編號
    assert "notes" not in manifest["core"]


# 驗收條件 4:不繞過 karst/store.py 開連線(D-027 第 4 條護欄二)
def test_gateway_opens_no_sqlite_connection_of_its_own():
    for path in sorted((REPO_ROOT / "karst" / "gateway").glob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "sqlite3.connect" not in source, path.name
        assert not re.search(r"^\s*import\s+sqlite3\b.*\n.*connect\(", source, re.M), path.name
