"""KARST-058 驗收:VIX 與 VIX_3M 換來源(yfinance → Cboe 官方免費歷史檔)。

分兩半,與 ``test_macro_snapshot.py`` / ``test_macro_yfinance.py`` 同一條規矩:

  * **離線那半**(本檔大部分)—— 解析與派工是純邏輯,用一小段示例正文就試得完,
    一次都不連網。
  * **真實那半**(最後兩條)—— 要連網,離線即 skip 並註明;不以合成數據冒充
    真實抓取,亦不讓離線變成假綠燈。

本檔守住的那件事:**序列代號不變,只換來源代號**。``VIX`` 與 ``VIX_3M`` 這兩個
內部代號一個字都沒有改,所以驅動器、快照結構、報告全部照舊;改的只是名冊上的
``symbol`` 與 ``source``,而且兩者連同快照一併凍結——「這條讀數當日由哪個來源取」
在已凍結的快照裡查得回。
"""

from __future__ import annotations

import pandas as pd
import pytest

from karst.data import (
    CBOE_SOURCE_NAME,
    COMPOSITE_SOURCE_NAME,
    MACRO_SOURCE_NAME,
    CboeMacroSource,
    CompletenessThresholds,
    CompositeMacroSource,
    DataFetchFailed,
    MacroSeries,
    default_macro_source,
)
from karst.data.macro import (
    SERIES_BY_CODE,
    canonical_registry,
    parse_cboe_history,
    render_macro_readme,
    series_of,
)
from karst.errors import ContractViolation

# Cboe 官方檔的真實形狀(2026-08-29 實測):首行 DATE,OPEN,HIGH,LOW,CLOSE,
# 日期 MM/DD/YYYY,收市價最後一欄。
SAMPLE = """DATE,OPEN,HIGH,LOW,CLOSE
09/18/2009,25.910000,26.660000,25.910000,26.540000
07/17/2026,20.100000,20.900000,20.010000,20.540000
07/20/2026,20.500000,20.700000,20.100000,20.400000
08/26/2026,18.320000,18.320000,17.960000,17.990000
08/27/2026,17.900000,17.960000,17.480000,17.560000
"""


# ----------------------------------------------------------------------
# 一、解析:把 Cboe 那份檔搬成本倉的形狀
# ----------------------------------------------------------------------


def test_cboe_history_parses_into_the_house_shape():
    """MM/DD/YYYY 轉 ISO、只取收市價、窗口含頭含尾、序列代號用內部那個。"""
    item = SERIES_BY_CODE["VIX_3M"]
    frame = parse_cboe_history(SAMPLE, item, "2026-07-17", "2026-08-27")

    assert list(frame.columns) == ["date", "series", "value"]
    assert list(frame["date"]) == ["2026-07-17", "2026-07-20", "2026-08-26", "2026-08-27"]
    # 序列代號是內部那個(VIX_3M),不是來源代號(VIX3M)
    assert set(frame["series"]) == {"VIX_3M"}
    # 取的是 CLOSE 一欄,不是 OPEN
    assert float(frame["value"].iloc[0]) == pytest.approx(20.54)
    assert float(frame["value"].iloc[-1]) == pytest.approx(17.56)
    # 窗口外那一行(2009)沒有混進來
    assert "2009-09-18" not in set(frame["date"])


def test_cboe_history_rejects_a_changed_shape_instead_of_guessing():
    """欄位變了形即當場拋錯:靜靜猜一欄出來,比抓不到更難發現。"""
    item = SERIES_BY_CODE["VIX"]
    with pytest.raises(DataFetchFailed, match="欄位變了形"):
        parse_cboe_history("DATE,OPEN,HIGH,LOW\n07/17/2026,1,2,3\n", item, "2015-01-01", "2026-12-31")
    with pytest.raises(DataFetchFailed, match="是空的"):
        parse_cboe_history("   \n", item, "2015-01-01", "2026-12-31")


def test_an_empty_window_counts_as_a_failed_fetch_not_as_no_readings():
    """窗口內一個讀數都沒有 = 抓取失敗,不當作「這段日子沒有數」。"""
    item = SERIES_BY_CODE["VIX"]
    with pytest.raises(DataFetchFailed, match="一個收市讀數都沒有"):
        parse_cboe_history(SAMPLE, item, "2020-01-01", "2020-12-31")


def test_the_cboe_url_is_the_official_free_history_file():
    """URL 由來源代號砌出;無鑰匙、無查詢參數。"""
    url = CboeMacroSource().url_for(SERIES_BY_CODE["VIX_3M"])
    assert url == "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX3M_History.csv"
    assert "?" not in url and "key" not in url.lower()


# ----------------------------------------------------------------------
# 二、派工:名冊上寫哪個來源,就派去哪個來源
# ----------------------------------------------------------------------


class _Stub:
    """一個只會回自己那批數的假來源,用來看清楚派工派了什麼給誰。"""

    def __init__(self, name: str, level: float) -> None:
        self.name = name
        self.level = level
        self.seen: list[str] = []

    def fetch_daily_series(self, series, start, end):  # noqa: ANN001, ARG002
        items = list(series)
        self.seen = [item.code for item in items]
        return pd.DataFrame(
            {
                "date": ["2026-08-26"] * len(items),
                "series": [item.code for item in items],
                "value": [self.level] * len(items),
            }
        )


def test_each_series_goes_to_the_source_its_registry_row_names():
    """VIX 那兩條派去 Cboe,其餘派去 yfinance——照名冊,不靠猜。"""
    cboe, yf = _Stub(CBOE_SOURCE_NAME, 17.0), _Stub(MACRO_SOURCE_NAME, 4.0)
    composite = CompositeMacroSource((cboe, yf))
    frame = composite.fetch_daily_series(
        series_of(["VIX", "VIX_3M", "UST_10Y", "FF_FUTURE"]), "2026-08-26", "2026-08-26"
    )

    assert sorted(cboe.seen) == ["VIX", "VIX_3M"]
    assert sorted(yf.seen) == ["FF_FUTURE", "UST_10Y"]
    assert set(frame["series"]) == {"VIX", "VIX_3M", "UST_10Y", "FF_FUTURE"}
    assert list(frame.columns) == ["date", "series", "value"]


def test_a_series_whose_source_nobody_answers_is_refused_on_the_spot():
    """名冊寫的來源沒有人接,就指名道姓拋錯,不退回「隨便找一個試試」。"""
    composite = CompositeMacroSource((_Stub(MACRO_SOURCE_NAME, 4.0),))
    orphan = MacroSeries(
        code="VIX",
        symbol="VIX",
        source="沒有人接的來源",
        tier="第一層",
        family="波動率",
        label="測試用",
        unit="點",
    )
    with pytest.raises(ContractViolation, match="沒有人接"):
        composite.fetch_daily_series([orphan], "2026-08-26", "2026-08-26")


def test_the_live_source_pairs_cboe_with_yfinance():
    """現役來源就是這兩個;快照登記的來源名講得出分工。"""
    live = default_macro_source()
    assert live.name == COMPOSITE_SOURCE_NAME == "cboe+yfinance-macro"
    assert live.sources == (CBOE_SOURCE_NAME, MACRO_SOURCE_NAME)


# ----------------------------------------------------------------------
# 三、名冊:序列代號不變,來源代號與來源都凍結得住
# ----------------------------------------------------------------------


def test_the_series_codes_did_not_change_only_the_source_symbols_did():
    """驅動器談的那個名(序列代號)一個字都沒有改。"""
    vix, term = SERIES_BY_CODE["VIX"], SERIES_BY_CODE["VIX_3M"]
    assert (vix.code, term.code) == ("VIX", "VIX_3M")
    assert (vix.symbol, term.symbol) == ("VIX", "VIX3M")     # 舊:^VIX、^VIX3M
    assert vix.source == term.source == CBOE_SOURCE_NAME
    # 其餘十二條照舊由 yfinance 取
    assert SERIES_BY_CODE["UST_10Y"].source == MACRO_SOURCE_NAME


def test_the_frozen_registry_records_which_source_each_reading_came_from():
    """名冊連同快照一併凍結,所以「當日由哪個來源取」在快照裡查得回。"""
    registry = canonical_registry(series_of(["VIX", "VIX_3M", "UST_10Y"]))
    assert "source" in registry.columns
    by_code = registry.set_index("series")
    assert by_code.loc["VIX", "source"] == CBOE_SOURCE_NAME
    assert by_code.loc["VIX_3M", "symbol"] == "VIX3M"
    assert by_code.loc["UST_10Y", "source"] == MACRO_SOURCE_NAME

    readme = render_macro_readme(
        snapshot_id="2026-08-28-testtesttest",
        source=COMPOSITE_SOURCE_NAME,
        fetched_at="2026-08-28T00:00:00+00:00",
        taken_on="2026-08-28",
        window_start="2015-01-02",
        window_end="2026-08-26",
        calendar_ticker="SPY",
        trading_days=2929,
        content_hash_value="0" * 64,
        rows=3,
        registry=registry,
        coverage=pd.DataFrame(
            [
                {
                    "series": "VIX_3M",
                    "actual": 2929,
                    "filled": 0,
                    "missing": 0,
                    "first_actual": "2015-01-02",
                    "last_actual": "2026-08-26",
                }
            ]
        ),
        # 齊全度那一節(KARST-061)。本條測的是名冊那一節,所以這裡給一份齊全的、
        # 零警報的表——門檻仍然要明給,它沒有預設值。
        completeness=pd.DataFrame(
            [
                {
                    "series": "VIX_3M",
                    "actual": 2929,
                    "filled": 0,
                    "missing": 0,
                    "missing_ratio": 0.0,
                    "first_actual": "2015-01-02",
                    "last_actual": "2026-08-26",
                    "stale_days": 0,
                }
            ]
        ),
        alerts=(),
        thresholds=CompletenessThresholds(max_stale_days=0, max_missing_ratio=0.0),
        calendar_end="2026-08-26",
        notes=(),
    )
    assert "| 序列代號 | 來源代號 | 來源 |" in readme
    assert "`cboe-macro`" in readme


# ----------------------------------------------------------------------
# 四、真實抓取(要連網;離線即 skip)
# ----------------------------------------------------------------------


@pytest.fixture(scope="module")
def online() -> None:
    try:
        CboeMacroSource().fetch_daily_series(
            series_of(["VIX"]), "2026-01-02", "2026-01-09"
        )
    except DataFetchFailed as exc:
        pytest.skip(f"離線或來源不通,跳過真實抓取:{exc}")


def test_the_cboe_file_needs_no_key_and_still_publishes_vix_3m(online):
    """本票的因由:免費轉發那一層自 2026-07-17 停更,官方檔照樣每個交易日有數。"""
    frame = CboeMacroSource().fetch_daily_series(
        series_of(["VIX", "VIX_3M"]), "2026-07-18", "2026-08-26"
    )
    term = frame.loc[frame["series"] == "VIX_3M"]
    assert len(term) >= 20, f"2026-07-18 之後只有 {len(term)} 日有數,期限結構仍然斷"
    assert str(term["date"].max()) >= "2026-08-20"
    # 兩條都在合理水位,不是空表也不是亂碼
    assert 5.0 < float(frame.loc[frame["series"] == "VIX", "value"].mean()) < 60.0
    assert 5.0 < float(term["value"].mean()) < 60.0


def test_the_term_structure_ratio_is_computable_every_day_now(online):
    """期限結構是相除出來的比率:分子分母同源,而且每日都算得出。"""
    frame = CboeMacroSource().fetch_daily_series(
        series_of(["VIX", "VIX_3M"]), "2026-07-18", "2026-08-26"
    )
    panel = frame.pivot(index="date", columns="series", values="value")
    ratio = (panel["VIX"] / panel["VIX_3M"]).dropna()
    assert len(ratio) == len(panel), "有日子算不出比率,即分子分母的日曆對不上"
    assert 0.4 < float(ratio.mean()) < 2.0
