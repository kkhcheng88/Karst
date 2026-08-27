"""KARST-027 驗收:離線那半。

用靜態來源(不連網)證四件事:
  1. 同一個快照編號讀兩次一字不差(用雜湊比)。
  2. 停牌處置在數據上驗得到:最多前值填補 3 日,超過留空。
  3. 快照編號查得到登記,連當時的宇宙名單一併凍結。
  4. 來源名與抓取時間查得出;兩條處置寫在說明檔。
真實抓取那半在 ``test_data_yfinance.py``。
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from karst import DefinitionStore
from karst.batches import content_hash
from karst.data import (
    BAR_ACTUAL,
    BAR_FILLED,
    BAR_MISSING,
    DIVIDEND_POLICY_ID,
    FFILL_LIMIT,
    DataFetchFailed,
    StaticSource,
    UniverseMember,
    build_price_snapshot,
    read_manifest,
    read_price_frame,
    read_price_panel,
    read_universe,
    verify_snapshot,
)
from karst.data.snapshots import README_FILE, snapshot_dir

CALENDAR_DAYS = tuple(
    day.strftime("%Y-%m-%d") for day in pd.bdate_range("2024-01-02", "2024-02-29")
)
# TESTCO 停牌:連續 6 個交易日沒有成交(前 3 日填補,其餘留空)
HALT_DAYS = CALENDAR_DAYS[8:14]

UNIVERSE = (
    UniverseMember("SPY", "etf", "SPDR S&P 500 ETF Trust"),
    UniverseMember("TESTCO", "company", "Test Company, Inc."),
)
CIK_MAP = {"TESTCO": "0000000042"}


def _bars() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for index, day in enumerate(CALENDAR_DAYS):
        rows.append(
            {
                "date": day,
                "ticker": "SPY",
                "open": 400.0 + index,
                "high": 401.0 + index,
                "low": 399.0 + index,
                "close": 400.5 + index,
                "volume": 1_000_000.0 + index,
            }
        )
        if day in HALT_DAYS:
            continue
        rows.append(
            {
                "date": day,
                "ticker": "TESTCO",
                "open": 50.0 + index,
                "high": 51.0 + index,
                "low": 49.0 + index,
                "close": 50.5 + index,
                "volume": 2_000.0 + index,
            }
        )
    return pd.DataFrame(rows)


def _build(store: DefinitionStore, root, bars: pd.DataFrame | None = None):
    return build_price_snapshot(
        store,
        start=CALENDAR_DAYS[0],
        end=CALENDAR_DAYS[-1],
        universe=UNIVERSE,
        source=StaticSource(bars if bars is not None else _bars(), name="static-test"),
        root=root,
        cik_map=CIK_MAP,
        taken_on="2026-08-28",
    )


@pytest.fixture()
def store():
    with DefinitionStore.open(":memory:") as opened:
        yield opened


# ----------------------------------------------------------------------
# 驗收 1:同一個快照編號重算兩次,結果一字不差
# ----------------------------------------------------------------------


def test_same_snapshot_id_reads_identical(store, tmp_path):
    snapshot = _build(store, tmp_path)

    first = read_price_frame(store, snapshot.snapshot_id)
    second = read_price_frame(store, snapshot.snapshot_id)
    assert content_hash(first) == content_hash(second)
    pd.testing.assert_frame_equal(first, second)

    # 由檔案重算的內容雜湊,對得上登記的那一個
    assert verify_snapshot(store, snapshot.snapshot_id) == snapshot.content_hash


def test_same_content_falls_back_to_same_snapshot_id(store, tmp_path):
    first = _build(store, tmp_path)
    fetched_at_first = read_manifest(store, first.snapshot_id)["fetched_at"]

    second = _build(store, tmp_path)

    assert second.snapshot_id == first.snapshot_id
    assert second.content_hash == first.content_hash
    # 舊快照不動:重跑不覆寫已凍結的目錄,抓取時間仍是第一次那個
    assert read_manifest(store, second.snapshot_id)["fetched_at"] == fetched_at_first


def test_changed_content_gets_another_snapshot_id(store, tmp_path):
    first = _build(store, tmp_path)

    bumped = _bars()
    bumped.loc[bumped.index[0], "close"] = 999.0
    second = _build(store, tmp_path, bumped)

    assert second.snapshot_id != first.snapshot_id
    assert snapshot_dir(store, first.snapshot_id).is_dir()  # 舊快照原封不動


# ----------------------------------------------------------------------
# 驗收 2:除權除息與停牌各有一條明文處置,寫在說明檔並在數據上驗得到
# ----------------------------------------------------------------------


def test_halt_fills_three_days_then_leaves_empty(store, tmp_path):
    snapshot = _build(store, tmp_path)
    frame = read_price_frame(store, snapshot.snapshot_id)
    testco = int(read_universe(store, snapshot.snapshot_id).set_index("ticker").loc["TESTCO", "entity_id"])

    halted = frame.loc[
        (frame["entity_id"] == testco) & (frame["date"].isin(HALT_DAYS))
    ].sort_values("date")
    statuses = list(halted["bar_status"])

    assert statuses == [BAR_FILLED] * FFILL_LIMIT + [BAR_MISSING] * (len(HALT_DAYS) - FFILL_LIMIT)
    # 留空就是留空:超過上限的那幾日在面板上是 NaN,不是 0
    panel = read_price_panel(store, snapshot.snapshot_id, field="close")
    tail = panel.loc[pd.to_datetime(list(HALT_DAYS[FFILL_LIMIT:])), testco]
    assert tail.isna().all()


def test_filled_bar_is_flat_with_zero_volume(store, tmp_path):
    snapshot = _build(store, tmp_path)
    frame = read_price_frame(store, snapshot.snapshot_id)

    filled = frame.loc[frame["bar_status"] == BAR_FILLED]
    assert len(filled) == FFILL_LIMIT
    assert (filled["open"] == filled["close"]).all()
    assert (filled["high"] == filled["close"]).all()
    assert (filled["low"] == filled["close"]).all()
    assert (filled["volume"] == 0.0).all()  # 沒有交易就是沒有交易,不抄上一日


def test_both_policies_are_written_down(store, tmp_path):
    snapshot = _build(store, tmp_path)
    manifest = read_manifest(store, snapshot.snapshot_id)
    readme = (snapshot_dir(store, snapshot.snapshot_id) / README_FILE).read_text(encoding="utf-8")

    assert manifest["core"]["dividend_policy_id"] == DIVIDEND_POLICY_ID
    assert manifest["core"]["auto_adjust"] is True
    assert manifest["core"]["ffill_limit"] == FFILL_LIMIT
    assert "除權除息" in readme and "停牌" in readme
    assert "已調整價" in manifest["dividend_policy"]
    assert "留空" in manifest["halt_policy"]


# ----------------------------------------------------------------------
# 驗收 3:快照有唯一編號,查得到登記,宇宙名單一併凍結
# ----------------------------------------------------------------------


def test_snapshot_is_registered_with_universe(store, tmp_path):
    snapshot = _build(store, tmp_path)
    registered = store.get_snapshot(snapshot.snapshot_id)

    assert registered.snapshot_id == snapshot.snapshot_id
    assert registered.source == "static-test"
    assert registered.content_hash == snapshot.content_hash
    assert registered.universe == ("SPY", "TESTCO")  # 當時的宇宙名單一併凍結
    assert registered.path == snapshot.path
    assert snapshot.snapshot_id.startswith(f"{snapshot.taken_on}-")


def test_prices_hang_on_entity_id_not_ticker(store, tmp_path):
    snapshot = _build(store, tmp_path)
    frame = read_price_frame(store, snapshot.snapshot_id)
    universe = read_universe(store, snapshot.snapshot_id)

    assert "ticker" not in frame.columns  # 代號不是主鍵,落地之後連欄都沒有
    panel = read_price_panel(store, snapshot.snapshot_id)
    assert list(panel.columns) == sorted(int(e) for e in universe["entity_id"])
    for row in universe.to_dict("records"):
        assert store.resolve_ticker(row["ticker"], CALENDAR_DAYS[0]) == int(row["entity_id"])


# ----------------------------------------------------------------------
# 驗收 4:查得出來源與抓取時間;抓取失敗要有明確錯誤
# ----------------------------------------------------------------------


def test_source_and_fetch_time_are_queryable(store, tmp_path):
    snapshot = _build(store, tmp_path)
    manifest = read_manifest(store, snapshot.snapshot_id)

    assert manifest["source"] == "static-test" == store.get_snapshot(snapshot.snapshot_id).source
    assert pd.Timestamp(manifest["fetched_at"]).tz is not None  # 抓取時間帶時區
    assert manifest["window_start"] == CALENDAR_DAYS[0]
    assert manifest["window_end"] == CALENDAR_DAYS[-1]
    assert json.loads(json.dumps(manifest)) == manifest  # 清單純文字,原樣讀得回


def test_missing_ticker_raises_instead_of_skipping(store, tmp_path):
    bars = _bars()
    thinned = bars.loc[bars["ticker"] != "TESTCO"]

    with pytest.raises(DataFetchFailed) as caught:
        _build(store, tmp_path, thinned)
    assert "TESTCO" in str(caught.value)


def test_actual_bars_keep_their_own_numbers(store, tmp_path):
    snapshot = _build(store, tmp_path)
    frame = read_price_frame(store, snapshot.snapshot_id)
    spy = int(read_universe(store, snapshot.snapshot_id).set_index("ticker").loc["SPY", "entity_id"])

    first = frame.loc[(frame["entity_id"] == spy) & (frame["date"] == CALENDAR_DAYS[0])].iloc[0]
    assert first["bar_status"] == BAR_ACTUAL
    assert first["close"] == pytest.approx(400.5)
    assert first["volume"] == pytest.approx(1_000_000.0)
