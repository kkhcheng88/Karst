"""KARST-084 善後:快照除名是**加一列**,不是刪一列。

一個快照凍出來之後才發現不可用(三數等式對不上——兩個代號撞同一個實體編號,
有價格序列被靜靜蓋走),要令它不再算可回測。庫身刻意不准刪登記
(``data_snapshot_fetch`` 與因子值批次那三道 ``BEFORE DELETE`` 閘寫明「登記不可刪,
追溯要指得回」),所以除名走的是另一條路:登記冊加一列說明它已除名。

本檔證四件事:
  1. 除名經唯一入口做,蓋得到寫入者簽章,``verify`` 核得過。
  2. 除名之後 ``list_snapshots`` 不再列出它,``get_snapshot`` 照樣讀得到。
  3. 三數等式核對略過已除名的快照,``verify`` 因此回清白。
  4. 有運行掛住的快照不准除名;同一個快照不准除名兩次。
"""

from __future__ import annotations

import pandas as pd
import pytest

from karst.data import StaticSource, UniverseMember, build_price_snapshot
from karst.errors import ContractViolation, DuplicateDefinition, NotFound
from karst.gateway import Gateway

CALENDAR_DAYS = tuple(
    day.strftime("%Y-%m-%d") for day in pd.bdate_range("2024-01-02", "2024-01-31")
)

UNIVERSE = (
    UniverseMember("SPY", "etf", "SPDR S&P 500 ETF Trust"),
    UniverseMember("TESTCO", "company", "Test Company, Inc."),
)


def _bars(offset: float) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for index, day in enumerate(CALENDAR_DAYS):
        for ticker, base in (("SPY", 400.0), ("TESTCO", 50.0)):
            price = base + index + offset
            rows.append(
                {
                    "date": day,
                    "ticker": ticker,
                    "open": price,
                    "high": price + 1.0,
                    "low": price - 1.0,
                    "close": price + 0.5,
                    "volume": 1_000.0 + index,
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture()
def gateway(tmp_path):
    with Gateway.open(str(tmp_path / "karst.sqlite"), writer="KARST-084-test") as opened:
        yield opened


def _freeze(gateway: Gateway, root, offset: float) -> str:
    snapshot = build_price_snapshot(
        gateway.store,
        start=CALENDAR_DAYS[0],
        end=CALENDAR_DAYS[-1],
        universe=UNIVERSE,
        source=StaticSource(_bars(offset), name="static-test"),
        root=root,
        cik_map={"TESTCO": "0000000042"},
        anchor_valid_to={"TESTCO": ""},
        taken_on="2026-08-30",
    )
    gateway.store.record_snapshot_fetch(
        snapshot.snapshot_id,
        fetched_at=snapshot.fetched_at,
        window_start=snapshot.window_start,
        window_end=snapshot.window_end,
        entity_count=len(snapshot.entity_ids),
        row_count=snapshot.rows,
        trading_days=snapshot.trading_days,
        alert_count=None,
        alert_summary=None,
    )
    return snapshot.snapshot_id


# ----------------------------------------------------------------------
# 一、除名經唯一入口,留簽章
# ----------------------------------------------------------------------


def test_retraction_is_signed_and_verify_stays_clean(gateway, tmp_path):
    old = _freeze(gateway, tmp_path / "snapshots", 0.0)
    new = _freeze(gateway, tmp_path / "snapshots", 7.0)

    retraction = gateway.retract_snapshot(
        old, reason="宇宙表三數等式對不上", superseded_by=new
    )
    assert retraction.snapshot_id == old
    assert retraction.superseded_by == new
    assert retraction.retracted_by == "KARST-084-test"
    assert retraction.reason == "宇宙表三數等式對不上"
    assert retraction.retracted_at

    # 除名列本身入治理清單:有簽章,verify 核得過
    assert gateway.verify() == []


def test_unsigned_retraction_is_caught(gateway, tmp_path):
    """繞過唯一入口直接塞一列除名登記,verify 一掃就見到它沒有簽章。"""
    old = _freeze(gateway, tmp_path / "snapshots", 0.0)
    with gateway.store._conn:
        gateway.store._conn.execute(
            "INSERT INTO data_snapshot_retraction (snapshot_id, reason, superseded_by,"
            " retracted_by, retracted_at) VALUES (?, ?, ?, ?, ?)",
            (old, "有人繞過那道門", None, "偷雞者", "2026-08-30T00:00:00"),
        )
    findings = gateway.verify()
    assert any(finding.table == "data_snapshot_retraction" for finding in findings)


# ----------------------------------------------------------------------
# 二、除名之後:登記冊略過,直取仍然讀得到
# ----------------------------------------------------------------------


def test_listing_skips_but_direct_read_still_works(gateway, tmp_path):
    old = _freeze(gateway, tmp_path / "snapshots", 0.0)
    new = _freeze(gateway, tmp_path / "snapshots", 7.0)
    gateway.retract_snapshot(old, reason="被新一代取代", superseded_by=new)

    listed = [listing.snapshot_id for listing in gateway.store.list_snapshots()]
    assert old not in listed
    assert new in listed

    # 追溯照指得回:直取一律讀得到,登記那一列一個字都沒有動
    assert gateway.store.get_snapshot(old).snapshot_id == old
    assert gateway.store.retired_snapshot_ids() == (old,)

    retractions = gateway.store.list_snapshot_retractions()
    assert [item.snapshot_id for item in retractions] == [old]
    assert retractions[0].superseded_by == new


def test_balance_check_skips_retired(gateway, tmp_path):
    """三數等式核對走 list_snapshots,除名之後自然不再核它。"""
    old = _freeze(gateway, tmp_path / "snapshots", 0.0)
    gateway.retract_snapshot(old, reason="不可用", superseded_by=None)
    assert all(
        finding.row_key != old for finding in gateway.snapshot_balance_findings()
    )


# ----------------------------------------------------------------------
# 三、除不到的那幾格
# ----------------------------------------------------------------------


def test_cannot_retract_twice(gateway, tmp_path):
    old = _freeze(gateway, tmp_path / "snapshots", 0.0)
    gateway.retract_snapshot(old, reason="第一次", superseded_by=None)
    with pytest.raises(DuplicateDefinition):
        gateway.retract_snapshot(old, reason="第二次", superseded_by=None)


def test_cannot_retract_unknown_snapshot(gateway):
    with pytest.raises(NotFound):
        gateway.retract_snapshot("2026-08-30-000000000000", reason="無此快照", superseded_by=None)


def test_cannot_retract_a_snapshot_a_run_still_points_at(gateway, tmp_path):
    """有回測運行掛住就拒收:運行要講得出自己跑的是哪一批數。

    只為造出「有一次運行掛住」這個局面而直塞一列運行(外鍵暫時關掉);
    本測試核的是除名那道閘,不是運行登記本身。
    """
    old = _freeze(gateway, tmp_path / "snapshots", 0.0)
    conn = gateway.store._conn
    conn.execute("PRAGMA foreign_keys = OFF")
    with conn:
        conn.execute(
            "INSERT INTO backtest_run (run_id, strategy_version_id, param_set_id,"
            " period_start, period_end, snapshot_id, engine_name, engine_version,"
            " fingerprint, trading_days, origin, sweep_id, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "run-084-test",
                1,
                1,
                CALENDAR_DAYS[0],
                CALENDAR_DAYS[-1],
                old,
                "test-engine",
                "1",
                "fingerprint-084",
                len(CALENDAR_DAYS),
                "formal",
                None,
                "2026-08-30T00:00:00",
            ),
        )
    conn.execute("PRAGMA foreign_keys = ON")

    with pytest.raises(ContractViolation):
        gateway.retract_snapshot(old, reason="有運行掛住", superseded_by=None)


def test_retraction_row_cannot_be_changed_or_deleted(gateway, tmp_path):
    """除名登記只加不改不刪——判斷變了請另開票,不要改寫已發生的除名。"""
    import sqlite3

    old = _freeze(gateway, tmp_path / "snapshots", 0.0)
    gateway.retract_snapshot(old, reason="不可用", superseded_by=None)
    with pytest.raises(sqlite3.IntegrityError):
        with gateway.store._conn:
            gateway.store._conn.execute(
                "UPDATE data_snapshot_retraction SET reason = ? WHERE snapshot_id = ?",
                ("改個講法", old),
            )
    with pytest.raises(sqlite3.IntegrityError):
        with gateway.store._conn:
            gateway.store._conn.execute(
                "DELETE FROM data_snapshot_retraction WHERE snapshot_id = ?", (old,)
            )
