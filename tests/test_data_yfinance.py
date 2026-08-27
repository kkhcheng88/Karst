"""KARST-027 驗收:真實抓取那半。

要連網。離線即 skip 並註明——不以合成數據冒充真實抓取,亦不讓離線變成假綠燈。
只抓小樣本(兩隻、一個月),真正那次全宇宙抓取由 ``tools`` 一次性跑,不入測試。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from karst import DefinitionStore
from karst.data import (
    PRICE_SIGNIFICANT_DIGITS,
    DataFetchFailed,
    UniverseMember,
    YFinanceSource,
    build_price_snapshot,
    is_placeholder,
    read_manifest,
    read_price_frame,
    read_price_panel,
    read_universe,
    round_significant,
    verify_snapshot,
)

pytest.importorskip("yfinance", reason="未安裝 yfinance,跳過真實抓取")

SAMPLE = (
    UniverseMember("SPY", "etf", "SPDR S&P 500 ETF Trust"),
    UniverseMember("AAPL", "company", "Apple Inc."),
)
WINDOW = ("2024-01-02", "2024-01-31")

# 重抓去重那條驗收要用派過息、歷史夠長的股:飄移只出現在已調整價上,
# 派息愈多、回溯愈遠,累計調整因子的尾數愈容易每次不同(KARST-033)。
DIVIDEND_SAMPLE = (
    UniverseMember("SPY", "etf", "SPDR S&P 500 ETF Trust"),
    UniverseMember("KO", "company", "The Coca-Cola Company"),
)
DIVIDEND_WINDOW = ("2015-01-02", "2018-12-31")


@pytest.fixture(scope="module")
def online() -> None:
    try:
        YFinanceSource().fetch_daily_bars(["SPY"], "2024-01-02", "2024-01-05")
    except DataFetchFailed as exc:
        pytest.skip(f"離線或來源不通,跳過真實抓取:{exc}")


def test_real_snapshot_is_daily_bars_from_yfinance(online, tmp_path):
    with DefinitionStore.open(":memory:") as store:
        snapshot = build_price_snapshot(
            store,
            start=WINDOW[0],
            end=WINDOW[1],
            universe=SAMPLE,
            source=YFinanceSource(),
            root=tmp_path,
        )
        manifest = read_manifest(store, snapshot.snapshot_id)
        panel = read_price_panel(store, snapshot.snapshot_id)
        universe = read_universe(store, snapshot.snapshot_id)

        # 來源與抓取時間查得出
        assert manifest["source"] == "yfinance"
        assert store.get_snapshot(snapshot.snapshot_id).source == "yfinance"
        assert pd.Timestamp(manifest["fetched_at"]).tz is not None

        # 真實美股日線:2024 年 1 月 2 日至 31 日有 20 個交易日
        assert 19 <= len(panel.index) <= 21
        assert list(panel.columns) == sorted(int(e) for e in universe["entity_id"])
        assert panel.notna().all().all()
        assert 400.0 < float(panel.iloc[0].max()) < 700.0  # SPY 當時的水位

        # 檔案重算的雜湊對得上登記
        assert verify_snapshot(store, snapshot.snapshot_id) == snapshot.content_hash


def test_company_anchored_on_sec_cik(online, tmp_path):
    with DefinitionStore.open(":memory:") as store:
        snapshot = build_price_snapshot(
            store,
            start=WINDOW[0],
            end=WINDOW[1],
            universe=SAMPLE,
            source=YFinanceSource(),
            root=tmp_path,
        )
        universe = read_universe(store, snapshot.snapshot_id).set_index("ticker")
        anchor = str(universe.loc["AAPL", "anchor"])

        if is_placeholder(anchor):
            # SEC 不通時照樣做得完,但一定要在註記裡講明
            assert any("AAPL" in note or "CIK" in note for note in snapshot.notes)
        else:
            assert anchor == "0000320193"  # Apple Inc. 的 SEC CIK
            assert universe.loc["AAPL", "anchor_source"] == "sec"
        assert str(universe.loc["SPY", "anchor_source"]) == "local"  # ETF 不掛 CIK


def test_prices_are_dividend_adjusted(online):
    """除權除息處置在數據上驗得到:已調整價低於當日真實成交價。

    派息股(JNJ)2024 年派了四次息,故 2024 年初那根日線的**已調整**收市價
    一定低於同一根的未調整收市價。這就是「不自建除權除息事件表、只存已調整價」
    這條處置的數據證據。
    """
    import yfinance

    common = {
        "start": "2024-01-02",
        "end": "2024-12-31",
        "interval": "1d",
        "actions": False,
        "threads": False,
        "progress": False,
    }
    adjusted = yfinance.download("JNJ", auto_adjust=True, **common)
    raw = yfinance.download("JNJ", auto_adjust=False, **common)
    if adjusted is None or adjusted.empty or raw is None or raw.empty:
        pytest.skip("JNJ 抓不到,跳過除息處置的數據驗證")

    first_adjusted = float(adjusted["Close"].iloc[0].item())
    first_raw = float(raw["Close"].iloc[0].item())
    assert first_adjusted < first_raw
    assert first_adjusted == pytest.approx(first_raw, rel=0.15)  # 只差在派息,不是另一隻股


def test_refetching_the_same_window_keeps_one_snapshot(online, tmp_path):
    """KARST-033 驗收 1:同一窗口同一宇宙真實抓兩次,得同一個編號、只得一份副本。

    KARST-027 收檔時量到的毛病就是這裡:同一個窗口相隔十幾秒抓兩次,已調整價在
    float32 的最後幾個 bit 上飄,內容雜湊逐次不同,快取每抓一次就多 1.6MB。
    現在凍結前先歸一化到 7 位有效數字,再問一句「這批數是不是已經凍過了」,
    等價就沿用原編號原檔案。
    """
    with DefinitionStore.open(":memory:") as store:
        common = {
            "start": DIVIDEND_WINDOW[0],
            "end": DIVIDEND_WINDOW[1],
            "universe": DIVIDEND_SAMPLE,
            "root": tmp_path,
        }
        first = build_price_snapshot(store, source=YFinanceSource(), **common)
        second = build_price_snapshot(store, source=YFinanceSource(), **common)

        assert second.snapshot_id == first.snapshot_id
        assert second.content_hash == first.content_hash
        assert second.reused  # 第二次是沿用,不是重新凍結

        # 快取根裡只得一個快照目錄——重抓不再多一份幾乎一樣的檔
        frozen = sorted(path.name for path in tmp_path.iterdir() if path.is_dir())
        assert frozen == [first.snapshot_id]

        # 沿用回來那份檔案照樣驗得過,抓取時間仍是第一次那個
        assert verify_snapshot(store, second.snapshot_id) == first.content_hash
        assert read_manifest(store, second.snapshot_id)["fetched_at"] == first.fetched_at


def test_real_prices_are_stored_at_the_declared_precision(online, tmp_path):
    """KARST-033:真實抓回來的價格,凍下來時已在宣告的精度上。"""
    with DefinitionStore.open(":memory:") as store:
        snapshot = build_price_snapshot(
            store,
            start=WINDOW[0],
            end=WINDOW[1],
            universe=SAMPLE,
            source=YFinanceSource(),
            root=tmp_path,
        )
        frame = read_price_frame(store, snapshot.snapshot_id)
        manifest = read_manifest(store, snapshot.snapshot_id)

        assert manifest["core"]["price_significant_digits"] == PRICE_SIGNIFICANT_DIGITS
        for field in ("open", "high", "low", "close"):
            values = frame[field].to_numpy("float64")
            present = np.isfinite(values)
            assert np.array_equal(values[present], round_significant(values[present]))


def test_unknown_ticker_raises_instead_of_skipping(online):
    with pytest.raises(DataFetchFailed):
        YFinanceSource().fetch_daily_bars(["ZZZZ-NOT-A-TICKER"], "2024-01-02", "2024-01-31")
