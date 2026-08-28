"""KARST-064 驗收:Alpha158 入庫與版本登記。

三件事要證:

  1. 唯一入口一句命令把 158 條全部登記成因子版本,查得到、有簽章、``verify`` 清白。
  2. 三個時點照 D-021 第 3 條落庫:事件=該根 K 線那日開頭、知情=該日收工、
     可執行=下一根可交易 K 線那日開市;最後一日沒有下一根,可執行時點留空。
  3. **滾動窗口未滿的日子留空、不回填**——庫內根本沒有那一列,不是有一列借了
     後來的數。

用的是離線靜態來源砌的小快照(兩個實體、八十幾個交易日),不連網、不碰真快照。
"""

from __future__ import annotations

import io

import pandas as pd
import pytest

from karst.data import StaticSource, UniverseMember, build_price_snapshot, read_price_frame
from karst.errors import ContractViolation
from karst.factors import ALPHA158_NAMES
from karst.factors.alpha158 import ALPHA158_EXPRESSIONS, compute_alpha158_for_entity
from karst.gateway.alpha158 import (
    ALPHA158_FAMILY,
    ALPHA158_PROCEDURE_VERSION,
    _resolve_version,
    factor_name,
)
from karst.gateway.cli import main
from karst.gateway.service import Gateway

# 八十幾個交易日:夠 ROC60 走完頭 60 格暖身之後仍有值,證得到「未滿留空、滿了才有」。
CALENDAR_DAYS = tuple(
    day.strftime("%Y-%m-%d") for day in pd.bdate_range("2024-01-02", "2024-04-30")
)

UNIVERSE = (
    UniverseMember("SPY", "etf", "SPDR S&P 500 ETF Trust"),
    UniverseMember("TESTCO", "company", "Test Company, Inc."),
)
CIK_MAP = {"TESTCO": "0000000042"}


def _bars() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for index, day in enumerate(CALENDAR_DAYS):
        wobble = (index % 7) - 3.0  # 不要單調上升,否則相關系數那幾條整欄留空
        for ticker, base, volume in (("SPY", 400.0, 1_000_000.0), ("TESTCO", 50.0, 2_000.0)):
            close = base + index + wobble
            rows.append(
                {
                    "date": day,
                    "ticker": ticker,
                    "open": close - 0.5,
                    "high": close + 1.0,
                    "low": close - 1.5,
                    "close": close,
                    "volume": volume + index * 13.0,
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture()
def gateway(tmp_path):
    with Gateway.open(str(tmp_path / "karst.sqlite"), writer="測試") as opened:
        yield opened


@pytest.fixture()
def snapshot_id(gateway, tmp_path) -> str:
    snapshot = build_price_snapshot(
        gateway.store,
        start=CALENDAR_DAYS[0],
        end=CALENDAR_DAYS[-1],
        universe=UNIVERSE,
        source=StaticSource(_bars(), name="static-test"),
        root=tmp_path / "snapshots",
        cik_map=CIK_MAP,
        taken_on="2026-08-29",
    )
    return snapshot.snapshot_id


@pytest.fixture()
def report(gateway, snapshot_id):
    return gateway.ingest_alpha158(snapshot_id=snapshot_id)


# ----------------------------------------------------------------------
# 驗收條件 1:158 個因子版本在 factor_version 表可查
# ----------------------------------------------------------------------


def test_all_158_factor_versions_are_registered_and_queryable(gateway, snapshot_id, report):
    conn = gateway.store.connection
    assert report.factor_count == 158
    assert report.registered == 158
    assert conn.execute("SELECT COUNT(*) FROM factor").fetchone()[0] == 158
    assert conn.execute("SELECT COUNT(*) FROM factor_version").fetchone()[0] == 158

    # 逐條查得回,名是「族名·具體定義」,族名一致
    for name in ALPHA158_NAMES:
        version = gateway.store.get_factor_version(factor_name(name))
        assert version.family == ALPHA158_FAMILY
        assert version.version_no == 1
        # 產生程序:公式派——官方表達式原文 + 輸入數據版本(那個數據快照)
        assert version.procedure.kind == "formula"
        assert version.procedure.formula == ALPHA158_EXPRESSIONS[name]
        assert version.procedure.input_data_version == snapshot_id
        # 說明帶得住公式出處與產生程序版本(D-021 第 8 條追溯到批次)
        assert ALPHA158_PROCEDURE_VERSION in version.description
        assert "qlib" in version.description


def test_approximated_factor_says_so_in_its_description(gateway, report):
    vwap = gateway.store.get_factor_version(factor_name("VWAP0"))
    assert "近似" in vwap.description
    assert "(high + low + close) / 3" in vwap.description
    # 其餘 157 條是原式,不應該無端掛住近似註記
    kmid = gateway.store.get_factor_version(factor_name("KMID"))
    assert "近似" not in kmid.description


def test_verify_stays_clean_after_ingest(gateway, report):
    """158 條全部經唯一入口登記,所以每一列定義都有寫入者簽章。"""
    assert gateway.verify() == []


def test_second_ingest_reuses_the_same_version_and_a_new_snapshot_makes_a_new_one(
    gateway, snapshot_id, report
):
    # 同一個快照、同一條公式:沿用原版,不無端出第二版
    assert _resolve_version(gateway, "KMID", snapshot_id) == "reused"
    assert gateway.store.get_factor_version(factor_name("KMID")).version_no == 1

    # 換一個輸入數據版本就是另一批值,照庫內既有做法出新版(舊版一字不變)
    other = gateway.store.list_snapshots()[0].snapshot_id
    assert _resolve_version(gateway, "KMID", other + "-x") == "new_version"
    chain = gateway.store.factor_version_chain(factor_name("KMID"))
    assert [v.version_no for v in chain] == [2, 1]
    assert chain[1].procedure.input_data_version == snapshot_id


# ----------------------------------------------------------------------
# 驗收條件 2 的一半:入庫行數、因子數、缺值比例對得上
# ----------------------------------------------------------------------


def test_report_counts_match_the_database(gateway, report):
    conn = gateway.store.connection
    assert conn.execute("SELECT COUNT(*) FROM factor_value").fetchone()[0] == report.written_rows
    assert report.possible_rows == 2 * len(CALENDAR_DAYS) * 158
    assert report.written_rows + report.missing_rows == report.possible_rows
    assert 0.0 < report.missing_ratio < 0.5
    assert report.entity_count == 2
    assert report.trading_days == len(CALENDAR_DAYS)


def test_cli_subcommand_ingests_through_the_single_gateway(tmp_path, gateway, snapshot_id):
    out = io.StringIO()
    code = main(
        [
            "--store", gateway.path,
            "--writer", "測試",
            "factor", "ingest-alpha158",
            "--snapshot", snapshot_id,
        ],
        out=out,
    )
    text = out.getvalue()
    assert code == 0, text
    assert "已入庫 Alpha158 全部 158 條因子" in text
    assert snapshot_id in text
    assert "缺值比例" in text


# ----------------------------------------------------------------------
# 驗收條件 3:三個時點,與「窗口未滿留空、不回填」
# ----------------------------------------------------------------------


def test_three_timepoints_follow_the_contract(gateway, snapshot_id, report):
    frame = gateway.store.read_factor_values(factor_name("KMID"))
    assert not frame.empty

    first_day, last_day = CALENDAR_DAYS[0], CALENDAR_DAYS[-1]
    head = frame[frame["event_time"].str.startswith(first_day)].iloc[0]
    # 事件時點 = 那一日的開頭;知情時點 = 同一日的結尾(該日收工才算知道)
    assert head["event_time"] == f"{first_day}T00:00:00.000000"
    assert head["knowledge_time"] == f"{first_day}T23:59:59.999999"
    # 可執行時點 = 下一根可交易 K 線那一日的開市,而且嚴格晚於知情時點
    assert head["executable_time"] == f"{CALENDAR_DAYS[1]}T00:00:00.000000"
    assert head["executable_time"] > head["knowledge_time"]

    # 最後一日沒有下一根 K 線:值知得到、成交不到,可執行時點留空而不是當日成交
    tail = frame[frame["event_time"].str.startswith(last_day)]
    assert len(tail) == 2
    assert tail["executable_time"].isna().all()
    assert report.last_executable_date is None
    assert report.not_executable_rows > 0

    # 全庫沒有一列的可執行時點早過或等於知情時點(前視在形狀上表達不到)
    bad = gateway.store.connection.execute(
        "SELECT COUNT(*) FROM factor_value"
        " WHERE executable_time IS NOT NULL AND executable_time <= knowledge_time"
    ).fetchone()[0]
    assert bad == 0


def test_warm_up_days_are_left_empty_and_never_back_filled(gateway, snapshot_id, report):
    """ROC60 頭 60 格窗口未滿:庫內**沒有那一列**,不是有一列借了後來的數。"""
    bars = read_price_frame(gateway.store, snapshot_id)
    entity_id = int(bars["entity_id"].iloc[0])
    reference = compute_alpha158_for_entity(
        bars[bars["entity_id"] == entity_id].sort_values("date", kind="stable")
    )["ROC60"]

    frame = gateway.store.read_factor_values(factor_name("ROC60"), entity_ids=[entity_id])
    stored_days = set(frame["event_time"].str.slice(0, 10))

    # 頭 60 個交易日一列都沒有;第 61 日起逐日都有
    assert stored_days.isdisjoint(CALENDAR_DAYS[:60])
    assert stored_days == set(CALENDAR_DAYS[60:])
    assert len(frame) == int(reference.notna().sum())

    # 有值那幾格逐格對回計算層的原值:沒有被前值填補、沒有被後值補、沒有填零
    stored = frame.set_index(frame["event_time"].str.slice(0, 10))["value"]
    for day in CALENDAR_DAYS[60:]:
        assert stored[day] == pytest.approx(float(reference[day]))


def test_missing_cells_have_no_row_at_all(gateway, report):
    """留空 = 沒有那一列(D-021 第 4 條):不填 0、不填 NULL。"""
    conn = gateway.store.connection
    assert conn.execute("SELECT COUNT(*) FROM factor_value WHERE value IS NULL").fetchone()[0] == 0
    assert report.missing_rows > 0


# ----------------------------------------------------------------------
# 合約:可執行時點必給,而且必須在知情之後
# ----------------------------------------------------------------------


def test_executable_time_is_required_and_must_come_after_knowledge_time(gateway, snapshot_id, report):
    name = factor_name("KMID")
    entity_id = 1

    with pytest.raises(ContractViolation) as missing:
        gateway.write_factor_values(
            name,
            [{"entity_id": entity_id, "event_time": "2030-01-02",
              "knowledge_time": "2030-01-02", "value": 0.1}],
        )
    assert "executable_time" in str(missing.value)

    with pytest.raises(ContractViolation) as lookahead:
        gateway.write_factor_values(
            name,
            [{"entity_id": entity_id, "event_time": "2030-01-02",
              "knowledge_time": "2030-01-02T23:59:59", "executable_time": "2030-01-02",
              "value": 0.1}],
        )
    assert "前視" in str(lookahead.value)

    # 沒有下一根 K 線時給 None 是合法的——那是「知得到、成交不到」,不是漏填
    written = gateway.write_factor_values(
        name,
        [{"entity_id": entity_id, "event_time": "2030-01-02",
          "knowledge_time": "2030-01-02", "executable_time": None, "value": 0.1}],
    )
    assert written == 1
