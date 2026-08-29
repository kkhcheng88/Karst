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

import numpy as np
import pandas as pd
import pytest

from karst import DefinitionStore
from karst.batches import content_hash
from karst.data import (
    BAR_ACTUAL,
    BAR_FILLED,
    BAR_MISSING,
    DIVIDEND_POLICY_ID,
    EQUIVALENCE_RTOL,
    FFILL_LIMIT,
    NORMALISATION_POLICY,
    NORMALISATION_POLICY_ID,
    PRICE_SIGNIFICANT_DIGITS,
    SNAPSHOT_README_TEMPLATE,
    DataFetchFailed,
    StaticSource,
    UniverseMember,
    build_price_snapshot,
    read_manifest,
    read_price_frame,
    read_price_panel,
    read_universe,
    round_significant,
    verify_snapshot,
)
from karst.data.snapshots import README_FILE, snapshot_dir
from karst.gateway import Gateway

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
    # 快照登記要經唯一入口簽章(KARST-087),所以庫身由那道門開出來
    with Gateway.open(":memory:").store as opened:
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


# ----------------------------------------------------------------------
# KARST-033 價格歸一化:重抓不多一份副本
#
# 飄移量取自實測——2026-08-27 相隔十分鐘的兩次真實抓取,重疊的 23,432 個價格
# 有 73% 不同,相對誤差上限 8.32e-7(成因是來源的已調整價只有 float32 精度)。
# 下面的擾動就照這個量級擺,證的是「這一級的飄移吞得下,再大一級的真更動吞不下」。
# ----------------------------------------------------------------------

REFETCH_DRIFT = 9e-7  # 略高於實測上限 8.32e-7


def _drifted_bars(scale: float) -> pd.DataFrame:
    """把價格乘上一個各自不同的微小相對誤差,模擬重抓回來的那一批。"""
    bars = _bars()
    rng = np.random.default_rng(20260828)
    for field in ("open", "high", "low", "close"):
        values = bars[field].to_numpy("float64")
        bars[field] = values * (1.0 + rng.uniform(-scale, scale, size=len(values)))
    return bars


def test_refetch_drift_does_not_make_a_second_snapshot(store, tmp_path):
    """驗收 1(離線版):重抓級的飄移不改編號、不多一份副本。

    真實抓取那半在 ``test_data_yfinance.py``;這一條把同一件事做成離線、
    每次都跑得到、而且飄移幅度寫死的證據。
    """
    first = _build(store, tmp_path)
    drifted = _drifted_bars(REFETCH_DRIFT)

    # 先證這一組擾動確實跨了捨入格線——否則測試會白過
    assert not np.array_equal(
        round_significant(_bars()["close"].to_numpy("float64")),
        round_significant(drifted["close"].to_numpy("float64")),
    )

    second = _build(store, tmp_path, drifted)

    assert second.snapshot_id == first.snapshot_id
    assert second.content_hash == first.content_hash
    assert second.reused
    # 快取根裡只得一個快照目錄:no duplicated copy
    assert [path.name for path in sorted(tmp_path.iterdir()) if path.is_dir()] == [
        first.snapshot_id
    ]
    # 沿用的是原本那份檔案,連抓取時間都沒有被改寫
    assert verify_snapshot(store, second.snapshot_id) == first.content_hash


def test_a_real_revision_still_gets_its_own_snapshot(store, tmp_path):
    """容差只吞雜訊,不吞真更動:改動大過容差即另一個編號,舊快照不動。

    這一條是上一條的另一半——若容差把真的數據更正也吞掉,快照就會靜靜地與
    來源不符,比多一份副本嚴重得多。改一格 1%(遠大於容差 1e-5、遠小於
    ``test_changed_content_gets_another_snapshot_id`` 那種粗改)。
    """
    first = _build(store, tmp_path)

    revised = _bars()
    revised.loc[revised.index[0], "close"] *= 1.01
    second = _build(store, tmp_path, revised)

    assert second.snapshot_id != first.snapshot_id
    assert not second.reused
    assert snapshot_dir(store, first.snapshot_id).is_dir()  # 舊快照原封不動
    assert len([path for path in tmp_path.iterdir() if path.is_dir()]) == 2


def test_prices_are_stored_at_the_declared_precision(store, tmp_path):
    """凍下來的每個價格都在說明檔宣告的精度上,多餘的位數不入庫。"""
    bars = _bars()
    bars["close"] = bars["close"] + 0.123456789  # 遠多過 7 位有效數字
    snapshot = _build(store, tmp_path, bars)

    frame = read_price_frame(store, snapshot.snapshot_id)
    for field in ("open", "high", "low", "close"):
        values = frame[field].to_numpy("float64")
        present = np.isfinite(values)
        assert np.array_equal(values[present], round_significant(values[present]))

    spy = int(read_universe(store, snapshot.snapshot_id).set_index("ticker").loc["SPY", "entity_id"])
    first = frame.loc[(frame["entity_id"] == spy) & (frame["date"] == CALENDAR_DAYS[0])].iloc[0]
    assert first["close"] == 400.6235  # 400.623456789 取 7 位有效數字


def test_round_significant_is_idempotent_and_keeps_gaps():
    """歸一化冪等,且留空的格照樣留空(不當作 0)。"""
    values = np.array([400.623456789, 0.453904271, 1234567.891, np.nan, 0.0, -12.3456789])
    once = round_significant(values)

    assert np.array_equal(once, round_significant(once), equal_nan=True)
    assert np.isnan(once[3])
    assert once[0] == 400.6235
    assert once[1] == 0.4539043  # 已調整舊價低見 0.45,有效位數照樣留住 7 位
    assert once[4] == 0.0


def test_normalisation_rule_is_in_the_readme_template(store, tmp_path):
    """驗收 2:歸一化規則寫在說明檔範本正本,且每個快照都查得到。"""
    # 範本正本(單一定義,無第二影像)本身有這一節
    assert "價格歸一化處置" in SNAPSHOT_README_TEMPLATE
    assert "{normalisation_policy}" in SNAPSHOT_README_TEMPLATE
    assert "有效數字" in NORMALISATION_POLICY
    assert str(PRICE_SIGNIFICANT_DIGITS) in NORMALISATION_POLICY

    snapshot = _build(store, tmp_path)
    readme = (snapshot_dir(store, snapshot.snapshot_id) / README_FILE).read_text(encoding="utf-8")
    manifest = read_manifest(store, snapshot.snapshot_id)

    assert "價格歸一化" in readme
    assert f"{PRICE_SIGNIFICANT_DIGITS} 位有效數字" in readme
    assert manifest["normalisation_policy"] == NORMALISATION_POLICY
    assert manifest["core"]["price_significant_digits"] == PRICE_SIGNIFICANT_DIGITS
    assert manifest["core"]["normalisation_policy_id"] == NORMALISATION_POLICY_ID
    assert manifest["core"]["equivalence_rtol"] == EQUIVALENCE_RTOL


def test_actual_bars_keep_their_own_numbers(store, tmp_path):
    snapshot = _build(store, tmp_path)
    frame = read_price_frame(store, snapshot.snapshot_id)
    spy = int(read_universe(store, snapshot.snapshot_id).set_index("ticker").loc["SPY", "entity_id"])

    first = frame.loc[(frame["entity_id"] == spy) & (frame["date"] == CALENDAR_DAYS[0])].iloc[0]
    assert first["bar_status"] == BAR_ACTUAL
    assert first["close"] == pytest.approx(400.5)
    assert first["volume"] == pytest.approx(1_000_000.0)
