"""KARST-040 驗收(一)(二):真實抓取那半。

要連網。離線即 skip 並註明——不以合成數據冒充真實抓取,亦不讓離線變成假綠燈
(與 ``test_data_yfinance.py`` 同一條規矩)。

只抓小樣本(一個月),證兩件事:

  1. VIX 與四條美債息率真的由 yfinance 抓得到、入得到快照,編號可引用;
  2. FedWatch 的免費替代(聯邦基金期貨 ``ZQ=F``)同樣抓得到——**一把 API 鑰匙、
     一分錢都沒有用**。

另證一條 2026-08-28 實測出來的事實:``^VIX3M`` 的歷史尾段比 ``^VIX`` 短,所以
「宏觀序列各有各的日曆」不是假設,是要處置的現實(留空,不當零)。
"""

from __future__ import annotations

import pandas as pd
import pytest

from karst import DefinitionStore
from karst.data import (
    DataFetchFailed,
    YFinanceMacroSource,
    build_macro_snapshot,
    read_macro_manifest,
    read_macro_panel,
    series_of,
    verify_macro_snapshot,
)

pytest.importorskip("yfinance", reason="未安裝 yfinance,跳過真實抓取")

# 主日曆用美股平日;真實抓取只核對「抓得到、對得上、凍得住」,不核對逐格數值
WINDOW = ("2024-01-02", "2024-01-31")
CALENDAR = tuple(day.strftime("%Y-%m-%d") for day in pd.bdate_range(*WINDOW))

SAMPLE = ("VIX", "UST_3M", "UST_5Y", "UST_10Y", "UST_30Y", "FF_FUTURE")


@pytest.fixture(scope="module")
def online() -> None:
    try:
        YFinanceMacroSource().fetch_daily_series(
            series_of(["VIX"]), "2024-01-02", "2024-01-05"
        )
    except DataFetchFailed as exc:
        pytest.skip(f"離線或來源不通,跳過真實抓取:{exc}")


def test_real_macro_snapshot_holds_vix_and_treasury_yields(online, tmp_path):
    """驗收一(真實那半):VIX 與四條美債息率抓得到、入得到快照、編號可引用。"""
    with DefinitionStore.open(":memory:") as store:
        snapshot = build_macro_snapshot(
            store,
            start=WINDOW[0],
            end=WINDOW[1],
            calendar=CALENDAR,
            calendar_ticker="SPY",
            codes=SAMPLE,
            source=YFinanceMacroSource(),
            root=tmp_path,
        )
        panel = read_macro_panel(store, snapshot.snapshot_id, root=tmp_path)
        manifest = read_macro_manifest(store, snapshot.snapshot_id, root=tmp_path)

        # 來源與抓取時間查得出
        assert manifest["source"] == "yfinance-macro"
        assert store.get_snapshot(snapshot.snapshot_id).source == "yfinance-macro"
        assert pd.Timestamp(manifest["fetched_at"]).tz is not None

        # 五條序列(VIX + 四條息率)都有真數,而且落在合理水位
        assert set(SAMPLE) <= set(panel.columns)
        assert 5.0 < float(panel["VIX"].mean()) < 60.0          # VIX 點數
        for code in ("UST_3M", "UST_5Y", "UST_10Y", "UST_30Y"):
            assert 0.0 < float(panel[code].mean()) < 20.0        # 息率百分點

        # 檔案重算的雜湊對得上登記
        assert verify_macro_snapshot(store, snapshot.snapshot_id, root=tmp_path) == (
            snapshot.content_hash
        )
        # 知情時間處置寫明
        assert "收市後可得" in manifest["informed_policy"]


def test_the_fedwatch_free_substitute_really_fetches(online, tmp_path):
    """驗收二(真實那半):聯邦基金期貨抓得到,不用鑰匙、不用付費。"""
    frame = YFinanceMacroSource().fetch_daily_series(
        series_of(["FF_FUTURE"]), WINDOW[0], WINDOW[1]
    )
    assert not frame.empty
    assert set(frame["series"]) == {"FF_FUTURE"}
    # 報價在 100 附近(隱含利率 = 100 − 報價)
    assert 80.0 < float(frame["value"].mean()) <= 100.0


def test_vix_term_structure_series_may_end_earlier_than_vix(online):
    """實測事實:^VIX3M 的歷史尾段比 ^VIX 短,所以「各有各的日曆」要處置。"""
    source = YFinanceMacroSource()
    long_window = ("2024-01-02", "2024-01-31")
    vix = source.fetch_daily_series(series_of(["VIX"]), *long_window)
    term = source.fetch_daily_series(series_of(["VIX_3M"]), *long_window)
    # 兩條都抓得到(這一段兩者皆有數);日子未必逐日對齊,故要對齊主日曆
    assert not vix.empty and not term.empty
    assert set(term["series"]) == {"VIX_3M"}
