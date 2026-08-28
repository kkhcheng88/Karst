"""KARST-040 驗收(一)(二):宏觀序列入快照,離線那半。

用靜態來源(不連網)證兩件事,對住票上頭兩條驗收條件:

  1. VIX 與四條美債息率序列經**來源適配器**入數據快照,知情時間處置寫明
     (收市後可得),快照編號查得到登記、可引用、重讀一字不差。
  2. FedWatch 的免費替代(聯邦基金期貨 ZQ=F)列明並接入,而且**明文寫出**
     FedWatch 與 FRED 為何不用——一把 API 鑰匙、一分錢都沒有用。

另加一條本票最要緊的處置:宏觀序列**不是可投資實體**,一個都不入 entity 表、
不入價格面板。真實抓取那半在 ``test_macro_yfinance.py``。

全部離線:讀數是砌出來的,一次都不連網。
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from karst import DefinitionStore
from karst.errors import NotFound, TickerNotResolved
from karst.data import (
    BAR_ACTUAL,
    BAR_FILLED,
    BAR_MISSING,
    FFILL_LIMIT,
    PRICE_SIGNIFICANT_DIGITS,
    DataFetchFailed,
    MacroSeries,
    StaticMacroSource,
    build_macro_snapshot,
    read_macro_frame,
    read_macro_manifest,
    read_macro_panel,
    verify_macro_snapshot,
)
from karst.data.macro import (
    MACRO_SERIES,
    README_FILE,
    SERIES_BY_CODE,
    TIER_DRIVER,
    macro_snapshot_dir,
    series_of,
)
from karst.strategies.factor_rotation import EXTERNAL_DATA

CALENDAR = tuple(
    day.strftime("%Y-%m-%d") for day in pd.bdate_range("2024-01-02", "2024-03-29")
)

# 這次測試要接入的序列:VIX 一條 + 美債息率四條(驗收一),加聯邦基金期貨(驗收二),
# 以及信用利差那兩條。全部第一層。
CODES = ("VIX", "VIX_3M", "UST_3M", "UST_5Y", "UST_10Y", "UST_30Y", "FF_FUTURE", "HY_ETF", "IG_ETF")

# VIX_3M 刻意在尾段停數,證「留空不當零」那條處置在數據上驗得到
STALE_TAIL = CALENDAR[-10:]

# 每條序列一個合理水位,免得測出來的數字像亂碼
LEVEL = {
    "VIX": 16.0,
    "VIX_3M": 18.0,
    "UST_3M": 5.2,
    "UST_5Y": 4.1,
    "UST_10Y": 4.0,
    "UST_30Y": 4.3,
    "FF_FUTURE": 94.7,
    "HY_ETF": 77.0,
    "IG_ETF": 108.0,
}


def _values(codes=CODES, *, stale: tuple[str, ...] = STALE_TAIL) -> pd.DataFrame:
    """砌一批合成宏觀讀數:一條慢慢走的線,VIX_3M 在尾段停數。"""
    rows: list[dict[str, object]] = []
    for index, day in enumerate(CALENDAR):
        for code in codes:
            if code == "VIX_3M" and day in stale:
                continue  # 尾段沒有讀數
            rows.append(
                {
                    "date": day,
                    "series": code,
                    "value": LEVEL[code] + 0.01 * index,
                }
            )
    return pd.DataFrame(rows)


def _build(store: DefinitionStore, root, values: pd.DataFrame | None = None, codes=CODES):
    return build_macro_snapshot(
        store,
        start=CALENDAR[0],
        end=CALENDAR[-1],
        calendar=CALENDAR,
        calendar_ticker="SPY",
        codes=codes,
        source=StaticMacroSource(_values(codes) if values is None else values),
        root=root,
        taken_on="2026-08-28",
    )


# ----------------------------------------------------------------------
# 驗收條件(一)
# ----------------------------------------------------------------------


def test_vix_and_treasury_yields_enter_a_citable_snapshot(tmp_path):
    """驗收一:VIX 與至少三條美債息率經適配器入快照,知情時間寫明,編號可引用。"""
    with DefinitionStore.open(":memory:") as store:
        snapshot = _build(store, tmp_path)

        # --- VIX 與四條美債息率真的入了快照 ---
        panel = read_macro_panel(store, snapshot.snapshot_id, root=tmp_path)
        yields = [code for code in panel.columns if code.startswith("UST_")]
        assert "VIX" in panel.columns
        assert len(yields) >= 3, f"美債息率序列只有 {yields},驗收要至少三條"
        assert set(("UST_3M", "UST_5Y", "UST_10Y", "UST_30Y")) <= set(panel.columns)

        # 讀數是真的數,不是空表;對齊主日曆之後日子與主日曆一樣
        assert list(panel.index.strftime("%Y-%m-%d")) == list(CALENDAR)
        assert float(panel["VIX"].iloc[0]) == pytest.approx(LEVEL["VIX"])

        # --- 快照編號可引用:查得到登記,來源與路徑都在 ---
        registered = store.get_snapshot(snapshot.snapshot_id)
        assert registered.source == "static-macro"
        assert registered.content_hash == snapshot.content_hash
        assert snapshot.snapshot_id.startswith("2026-08-28-")

        # --- 重讀一字不差:由檔案重算的雜湊對得上登記 ---
        assert verify_macro_snapshot(store, snapshot.snapshot_id, root=tmp_path) == (
            snapshot.content_hash
        )

        # --- 知情時間處置寫明(收市後可得),機讀與人讀兩邊都有 ---
        manifest = read_macro_manifest(store, snapshot.snapshot_id, root=tmp_path)
        assert "收市後可得" in manifest["informed_policy"]
        assert manifest["core"]["informed_at"] == "close"
        readme = (macro_snapshot_dir(store, snapshot.snapshot_id, root=tmp_path) / README_FILE).read_text(
            encoding="utf-8"
        )
        assert "收市後可得" in readme
        assert "## 二、知情時間" in readme


def test_missing_readings_stay_missing_and_are_visible_in_the_data(tmp_path):
    """留空不當零:VIX_3M 尾段停數,前值填補至多 3 日,其餘留空,而且驗得到。"""
    with DefinitionStore.open(":memory:") as store:
        snapshot = _build(store, tmp_path)
        frame = read_macro_frame(store, snapshot.snapshot_id, root=tmp_path)
        block = frame.loc[frame["series"] == "VIX_3M"].sort_values("date")

        tail = block.loc[block["date"].isin(STALE_TAIL)]
        assert (tail["value_status"] == BAR_FILLED).sum() == FFILL_LIMIT
        assert (tail["value_status"] == BAR_MISSING).sum() == len(STALE_TAIL) - FFILL_LIMIT
        # 留空的格是 NaN,**不是零**
        assert tail.loc[tail["value_status"] == BAR_MISSING, "value"].isna().all()
        # 其餘的日子照樣真有讀數
        assert (block.loc[~block["date"].isin(STALE_TAIL), "value_status"] == BAR_ACTUAL).all()

        # 逐條齊全度寫入了 manifest,人不用翻數據就見到
        manifest = read_macro_manifest(store, snapshot.snapshot_id, root=tmp_path)
        coverage = {row["series"]: row for row in manifest["coverage"]}
        assert coverage["VIX_3M"]["missing"] == len(STALE_TAIL) - FFILL_LIMIT
        assert coverage["VIX"]["missing"] == 0


# ----------------------------------------------------------------------
# 驗收條件(二)
# ----------------------------------------------------------------------


def test_fedwatch_free_substitute_is_named_ingested_and_the_paywall_written_down(tmp_path):
    """驗收二:FedWatch 的免費替代列明並接入,並明文寫出為何不用 FedWatch / FRED。"""
    # --- 名冊上講得出那條替代是什麼、來源是什麼 ---
    fed = SERIES_BY_CODE["FF_FUTURE"]
    assert fed.symbol == "ZQ=F"
    assert fed.tier == TIER_DRIVER
    # 明文寫出 FedWatch 本身不免費、FRED 要鑰匙
    assert "FedWatch" in fed.note and "不免費" in fed.note
    assert "鑰匙" in fed.note

    # --- 信用利差與 2 年期那兩個替代同樣寫明了代價 ---
    assert "鑰匙" in SERIES_BY_CODE["HY_ETF"].note  # FRED 高收益 OAS 要鑰匙
    assert "替代" in SERIES_BY_CODE["UST_3M"].note  # 2 年期用 ^IRX 替代

    # --- 策略層的外部數據清單逐條講明「來源、免費與否、知情時間」 ---
    assert EXTERNAL_DATA, "外部數據清單不可以是空的:有宏觀驅動器就要逐條列明"
    for row in EXTERNAL_DATA:
        assert set(row) >= {"序列", "來源", "免費", "知情時間", "用途"}
        assert row["免費"].startswith("是"), f"{row['序列']} 不是免費來源,不可用"
        assert row["知情時間"] == "當日收市後可得"
    assert any("FedWatch" in row["用途"] for row in EXTERNAL_DATA)

    # --- 真的接入了:它入了快照,讀得回來 ---
    with DefinitionStore.open(":memory:") as store:
        snapshot = _build(store, tmp_path)
        panel = read_macro_panel(store, snapshot.snapshot_id, root=tmp_path)
        assert "FF_FUTURE" in panel.columns
        assert panel["FF_FUTURE"].notna().all()

    # --- 全倉一條付費 / 要鑰匙的來源都沒有引入 ---
    for series in MACRO_SERIES:
        assert not series.symbol.lower().startswith("fred")


# ----------------------------------------------------------------------
# 本票最要緊的處置:非可投資序列
# ----------------------------------------------------------------------


def test_macro_series_are_never_investable_entities(tmp_path):
    """宏觀序列不入 entity 表、不佔實體編號、不入價格面板——處置寫明且驗得到。"""
    with DefinitionStore.open(":memory:") as store:
        snapshot = _build(store, tmp_path)

        # 一個實體都沒有登記:整條宏觀管線根本沒有 register_entity 那一步
        with pytest.raises(NotFound):
            store.get_entity(1)
        # 序列代號亦解析不到實體——它不是代號,是序列名
        for code in ("VIX", "UST_10Y", "FF_FUTURE"):
            with pytest.raises(TickerNotResolved):
                store.resolve_ticker(code, CALENDAR[-1])

        # 快照的主鍵是序列代號,不是實體編號
        frame = read_macro_frame(store, snapshot.snapshot_id, root=tmp_path)
        assert "entity_id" not in frame.columns
        assert "series" in frame.columns
        assert set(frame["series"]) == set(CODES)

        # 處置在 manifest 與說明檔兩邊都寫明
        manifest = read_macro_manifest(store, snapshot.snapshot_id, root=tmp_path)
        assert "不是可投資對象" in manifest["non_investable_policy"]
        assert "不入 entity 表" in manifest["non_investable_policy"]
        assert manifest["core"]["non_investable"] is True
        assert manifest["snapshot_kind"] == "macro"

        readme = (
            macro_snapshot_dir(store, snapshot.snapshot_id, root=tmp_path) / README_FILE
        ).read_text(encoding="utf-8")
        assert "非可投資序列處置" in readme

        # ^VIX 一類指數代號沒有 CIK,亦不會被當作公司:名冊上根本沒有 CIK 這一欄
        assert not hasattr(MACRO_SERIES[0], "cik")


def test_refetching_the_same_window_reuses_the_frozen_snapshot(tmp_path):
    """等價重用(D-028 第 2 條):同一批數重抓不多一份副本。"""
    with DefinitionStore.open(":memory:") as store:
        first = _build(store, tmp_path)
        assert first.reused is False

        second = _build(store, tmp_path)
        assert second.reused is True
        assert second.snapshot_id == first.snapshot_id

        directories = [p.name for p in tmp_path.iterdir() if p.is_dir()]
        assert directories == [first.snapshot_id]


def test_an_unknown_series_is_refused_not_guessed():
    """名冊上沒有的序列當場拒收,不猜。"""
    with pytest.raises(Exception) as caught:
        series_of(["VIX", "沒有這條"])
    assert "沒有" in str(caught.value)


def test_a_source_that_returns_nothing_is_a_failure_not_an_empty_series(tmp_path):
    """抓不到不當作「這條序列沒有數」,一律當抓取失敗。"""
    values = _values()
    values = values.loc[values["series"] != "UST_10Y"]  # 少了一條
    with DefinitionStore.open(":memory:") as store:
        with pytest.raises(DataFetchFailed) as caught:
            _build(store, tmp_path, values=values)
    assert "UST_10Y" in str(caught.value)
