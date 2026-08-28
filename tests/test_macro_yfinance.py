"""KARST-040 驗收(一)(二):真實抓取那半。

要連網。離線即 skip 並註明——不以合成數據冒充真實抓取,亦不讓離線變成假綠燈
(與 ``test_data_yfinance.py`` 同一條規矩)。

只抓小樣本(一個月),證兩件事:

  1. VIX 與四條美債息率真的由**現役來源**抓得到、入得到快照,編號可引用;
  2. FedWatch 的免費替代(聯邦基金期貨 ``ZQ=F``)同樣抓得到——**一把 API 鑰匙、
     一分錢都沒有用**。

KARST-058 之後現役來源是兩個並存的複合來源(VIX 那兩條由 Cboe 官方檔取、其餘
十二條仍由 yfinance 取),所以第一條測試改用 ``default_macro_source()``:它證的
是「這批數今日真的抓得回」,那就要用今日真正在用的那條路。**探測有沒有網的
那一針要扎在 yfinance 上**(本檔測的是 yfinance 那一半),不然 yfinance 一斷,
本檔會靜靜地全部 skip 變成假綠燈。

另證一條 KARST-058 的因由:``^VIX3M``(yfinance)的歷史尾段短過 Cboe 官方檔,
所以「宏觀序列各有各的日曆、甚至各有各的停更時間」不是假設,是要處置的現實。
"""

from __future__ import annotations

import pandas as pd
import pytest

from karst import DefinitionStore
from karst.data import (
    COMPOSITE_SOURCE_NAME,
    CboeMacroSource,
    CompletenessThresholds,
    DataFetchFailed,
    MacroSeries,
    YFinanceMacroSource,
    build_macro_snapshot,
    default_macro_source,
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

# KARST-058 之前 VIX_3M 的來源代號。留在這裡是為了驗得到那條因由,不是為了再用它。
LEGACY_VIX_3M = MacroSeries(
    code="VIX_3M",
    symbol="^VIX3M",
    tier="第一層",
    family="波動率",
    label="CBOE 波動率指數(3 個月)",
    unit="年化波動率點數",
    note="KARST-058 之前的來源代號",
)


@pytest.fixture(scope="module")
def online() -> None:
    # 探針扎在 yfinance 那一條(UST_10Y = ^TNX):本檔測的是 yfinance 那一半,
    # 拿一條已經不歸 yfinance 的序列去探,會令 yfinance 斷線時全部靜靜 skip。
    try:
        YFinanceMacroSource().fetch_daily_series(
            series_of(["UST_10Y"]), "2024-01-02", "2024-01-05"
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
            # 真實抓取那半:門檻放寬,本檔測的是「抓不抓得到」,不是齊全度判斷
            thresholds=CompletenessThresholds(max_stale_days=60, max_missing_ratio=1.0),
            codes=SAMPLE,
            source=default_macro_source(),
            root=tmp_path,
        )
        panel = read_macro_panel(store, snapshot.snapshot_id, root=tmp_path)
        manifest = read_macro_manifest(store, snapshot.snapshot_id, root=tmp_path)

        # 來源與抓取時間查得出;來源名講得出兩個來源的分工(KARST-058)
        assert manifest["source"] == COMPOSITE_SOURCE_NAME
        assert store.get_snapshot(snapshot.snapshot_id).source == COMPOSITE_SOURCE_NAME
        assert pd.Timestamp(manifest["fetched_at"]).tz is not None

        # 名冊逐條記明由哪個來源取
        by_code = {row["series"]: row for row in manifest["registry"]}
        assert by_code["VIX"]["source"] == "cboe-macro"
        assert by_code["UST_10Y"]["source"] == "yfinance-macro"

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


def test_the_fedwatch_free_substitute_really_fetches(online):
    """驗收二(真實那半):聯邦基金期貨抓得到,不用鑰匙、不用付費。"""
    frame = YFinanceMacroSource().fetch_daily_series(
        series_of(["FF_FUTURE"]), WINDOW[0], WINDOW[1]
    )
    assert not frame.empty
    assert set(frame["series"]) == {"FF_FUTURE"}
    # 報價在 100 附近(隱含利率 = 100 − 報價)
    assert 80.0 < float(frame["value"].mean()) <= 100.0


def test_the_official_file_runs_at_least_as_far_as_the_free_relay(online):
    """KARST-058 的因由:官方檔的尾**不會短過**免費轉發那一層。

    只斷言「不短過」而不是「一定長 29 日」:轉發那一層日後修好了,這條測試照樣
    成立,而換來源的理由(官方檔才是那條數的出處)一樣站得住。
    """
    window = ("2026-06-01", "2026-08-26")
    official = CboeMacroSource().fetch_daily_series(series_of(["VIX_3M"]), *window)
    assert not official.empty

    try:
        relay = YFinanceMacroSource().fetch_daily_series([LEGACY_VIX_3M], *window)
    except DataFetchFailed:
        relay = None   # 轉發那一層連數都回不了,更加不用比

    assert str(official["date"].max()) >= "2026-08-20"
    if relay is not None and not relay.empty:
        assert str(official["date"].max()) >= str(relay["date"].max())
