"""KARST-071 驗收:選股引擎按知情時點取值時,表與因子值批次兩邊一齊看。

D-032 把 Alpha158 一類大批因子值遷出 ``factor_value`` 表(KARST-068),選股引擎
原本只問表,於是取不到數。三件事要證:

  1. **策略經現有介面取得到檔裡的值**:``read_factor_panel`` 與
     ``run_ranking_rebalance`` 簽名一格沒有改,而值來自 Parquet。
  2. **知情時間閘一格沒有鬆**(D-021 第 3 條):某決策日取回的最新已知值與
     Parquet 內那一格一致,而知情時點在該日之後的值一個都不會出現;
     成交仍然是可執行時點那一根 K 線的開價。
  3. **表那條路照舊**:值住表的因子照樣讀得回、挑得中最新那一個;
     一條因子兩邊都有值時,兩邊都看得見。
     (取值口換成 ``karst.factorvalues.FactorValueReader`` 之後,「與已退役那三份
     實作逐格相同」那一項由 ``tests/test_factorvalues.py`` 對凍檔比,不在本檔。)

玩具數據,固定日子,不連外部數據;全部用即用即棄的小庫與臨時目錄。
"""

from __future__ import annotations

import pandas as pd
import pytest

from karst.engine import PricePanel, read_factor_panel, run_ranking_rebalance
from karst.factorvalues import FactorValueReader
from karst.gateway.service import Gateway
from karst.models import FormulaProcedure

BATCH_FACTOR = "動量·批次玩具"
TABLE_FACTOR = "質素·表玩具"
BOTH_FACTOR = "價值·兩邊玩具"

BATCH_KEY = "toy-batch"
PROCEDURE_VERSION = "karst.tests.toy@1"

# 六個交易日(2026-03-02 是星期一)。最後一日之後沒有下一根 K 線,所以只有頭五日
# 有值——可執行時點必須真的存在(D-021 第 3 條)。
DAYS = ("2026-03-02", "2026-03-03", "2026-03-04", "2026-03-05", "2026-03-06", "2026-03-09")
DATES = pd.DatetimeIndex([pd.Timestamp(day) for day in DAYS])

#: 遲到那一隻:值的事件時點是第一日,但第四日收工才知道(披露滯後那一類)。
LATE_VALUE = 99.0
LATE_KNOWN_ON = 3  # DAYS[3] 收工才知道


def _procedure(snapshot_id: str) -> FormulaProcedure:
    return FormulaProcedure(formula="close[-21] / close[-252] - 1", input_data_version=snapshot_id)


@pytest.fixture()
def gateway(tmp_path):
    with Gateway.open(str(tmp_path / "karst.sqlite"), writer="KARST-071-測試") as opened:
        yield opened


@pytest.fixture()
def factor_root(tmp_path) -> str:
    return str(tmp_path / "factors")


@pytest.fixture()
def snapshot_id(gateway) -> str:
    return gateway.store.register_snapshot(
        source="test", taken_on="2026-03-10", content_hash="b" * 64,
        universe=("AAA", "BBB", "CCC"),
    )


@pytest.fixture()
def entities(gateway) -> list[int]:
    return [
        gateway.store.register_entity(
            kind="company", display_name=f"Toy {index} Inc.", cik=str(700000 + index)
        )
        for index in range(3)
    ]


@pytest.fixture()
def panel(entities) -> PricePanel:
    """開價與收價各自不同,好證得到成交取的是哪一個。"""
    closes = pd.DataFrame(
        {entity: [100.0 + index * 10 + step for step in range(len(DAYS))]
         for index, entity in enumerate(entities)},
        index=DATES,
    )
    opens = closes - 1.5
    return PricePanel.from_frames(open=opens, close=closes)


def _row(version_id: int, entity_id: int, *, event: int, known: int, value: float) -> dict:
    """一列因子值。可執行時點=知情之後下一根 K 線的開市,沒有下一根即留空。"""
    executable = DAYS[known + 1] if known + 1 < len(DAYS) else None
    return {
        "factor_version_id": version_id,
        "entity_id": entity_id,
        "event_time": f"{DAYS[event]}T00:00:00",
        "knowledge_time": f"{DAYS[known]}T23:59:59.999999",
        "executable_time": None if executable is None else f"{executable}T00:00:00",
        "value": float(value),
    }


@pytest.fixture()
def batch_factor(gateway, factor_root, snapshot_id, entities):
    """一條值全部住 Parquet 的因子。

    頭兩隻逐日有值(分數逐日遞增,第二隻永遠高過第一隻);第三隻只有一個值,而且
    第四日收工才知道——之前它根本不參與(D-021 第 4 條),之後它分數最高。
    """
    version, _ = gateway.register_factor(
        BATCH_FACTOR, scale_kind="cardinal", procedure=_procedure(snapshot_id)
    )
    version_id = version.factor_version_id
    rows = [
        _row(version_id, entities[which], event=index, known=index,
             value=1.0 + which + 0.1 * index)
        for index in range(len(DAYS) - 1)
        for which in (0, 1)
    ]
    rows.append(
        _row(version_id, entities[2], event=0, known=LATE_KNOWN_ON, value=LATE_VALUE)
    )
    gateway.write_factor_batch(
        pd.DataFrame(rows),
        batch_key=BATCH_KEY,
        snapshot_id=snapshot_id,
        procedure_version=PROCEDURE_VERSION,
        root=factor_root,
    )
    return version


@pytest.fixture()
def values(gateway, factor_root, batch_factor):
    """因子值批次的讀取介面——用來核對「引擎取到的,就是檔裡那一格」。"""
    return gateway.factor_values(factor_root)


# ----------------------------------------------------------------------
# 驗收條件 1:策略經現有介面取得到因子值批次裡的值
# ----------------------------------------------------------------------


def test_batch_values_reach_the_strategy_through_the_unchanged_interface(
    gateway, panel, entities, batch_factor
):
    decision_days = list(DATES[:-1])
    factor_panel = read_factor_panel(
        gateway.store, BATCH_FACTOR, decision_days, entity_ids=entities
    )

    assert list(factor_panel.index) == decision_days
    assert list(factor_panel.columns) == entities

    # 頭兩隻逐日有值;第三隻要到第四日收工才知道,之前一格都沒有(缺失=不參與)
    assert factor_panel.loc[DATES[0], entities[0]] == pytest.approx(1.0)
    assert factor_panel.loc[DATES[2], entities[1]] == pytest.approx(2.2)
    assert pd.isna(factor_panel.loc[DATES[2], entities[2]])
    assert factor_panel.loc[DATES[LATE_KNOWN_ON], entities[2]] == pytest.approx(LATE_VALUE)

    # 值真的住檔案:表裡一列都沒有
    assert gateway.store.connection.execute(
        "SELECT COUNT(*) FROM factor_value"
    ).fetchone()[0] == 0

    result = run_ranking_rebalance(
        store=gateway.store,
        panel=panel,
        factor_name=BATCH_FACTOR,
        cadence="daily",
        top_n=1,
        direction="high",
    )
    assert result.factor_version_id == batch_factor.factor_version_id
    assert len(result.orders) > 0

    picks = {rebalance.decision_date: rebalance.selected for rebalance in result.rebalances}
    # 第三隻未知之前揀第二隻(分數 2.x 高過 1.x);它一知道就以 99 分壓過所有人
    assert picks[DAYS[2]] == (entities[1],)
    assert picks[DAYS[LATE_KNOWN_ON]] == (entities[2],)


# ----------------------------------------------------------------------
# 驗收條件 2:某決策日的最新已知值與 Parquet 內一致,取不到知情時點之後的值
# ----------------------------------------------------------------------


def test_latest_known_value_matches_the_parquet_and_stops_at_the_knowledge_gate(
    gateway, values, factor_root, snapshot_id, entities
):
    reader = FactorValueReader(gateway.store, factor_root)
    day = DAYS[2]

    taken = reader.latest_known(BATCH_FACTOR, day, snapshot_id=None, entity_ids=entities)
    # 同一日、同一條因子,直接由檔案讀回來自己挑一次:兩邊逐格一樣
    long = values.read_long([BATCH_FACTOR], snapshot_id=snapshot_id, as_of=day)
    expected = (
        long.sort_values(["entity_id", "event_time", "knowledge_time"],
                         ascending=[True, False, False], kind="mergesort")
        .drop_duplicates("entity_id", keep="first")
        .set_index("entity_id")["value"]
    )
    assert dict(zip(taken["entity_id"], taken["value"])) == pytest.approx(dict(expected))
    assert list(taken["entity_id"]) == entities[:2]

    # 知情時點在該日之後的值,一個都不准出現:第三隻那個 99 分要到 DAYS[3] 才見得到
    assert LATE_VALUE not in list(taken["value"])
    assert entities[2] not in list(taken["entity_id"])
    assert (pd.to_datetime(taken["knowledge_time"]) <= pd.Timestamp(f"{day}T23:59:59.999999")).all()

    # 檔裡明明有那一列,只是知情時點未到——不是缺值,是未知
    whole = values.read_long([BATCH_FACTOR], snapshot_id=snapshot_id)
    assert LATE_VALUE in list(whole["value"])

    # 到知情那一日就見得到,而且欄位與表那條路一模一樣
    later = reader.latest_known(
        BATCH_FACTOR, DAYS[LATE_KNOWN_ON], snapshot_id=None, entity_ids=entities
    )
    assert list(later["entity_id"]) == entities
    assert float(later.set_index("entity_id").loc[entities[2], "value"]) == LATE_VALUE


def test_fills_still_happen_at_the_executable_time(gateway, panel, entities, batch_factor):
    """成交按可執行時點:知情之後下一根 K 線的**開價**(D-021 第 3 條)。"""
    result = run_ranking_rebalance(
        store=gateway.store,
        panel=panel,
        factor_name=BATCH_FACTOR,
        cadence="daily",
        top_n=1,
        direction="high",
    )
    decided = [r for r in result.rebalances if r.decision_date == DAYS[LATE_KNOWN_ON]]
    assert len(decided) == 1
    assert decided[0].execution_date == DAYS[LATE_KNOWN_ON + 1]

    bought = [
        order for order in result.orders
        if order.trade_date == DAYS[LATE_KNOWN_ON + 1]
        and order.entity_id == entities[2]
        and order.side == "buy"
    ]
    assert len(bought) == 1
    assert bought[0].price == pytest.approx(
        float(panel.open.loc[DATES[LATE_KNOWN_ON + 1], entities[2]])
    )


# ----------------------------------------------------------------------
# 驗收條件 3:表那條路照舊;兩邊都有值時兩邊都看得見
# ----------------------------------------------------------------------


def test_table_values_read_exactly_as_before(gateway, factor_root, snapshot_id, entities):
    gateway.register_factor(
        TABLE_FACTOR, scale_kind="cardinal", procedure=_procedure(snapshot_id)
    )
    gateway.write_factor_values(
        TABLE_FACTOR,
        [
            {"entity_id": entities[0], "event_time": f"{DAYS[0]}T00:00:00",
             "knowledge_time": f"{DAYS[0]}T23:59:59.999999",
             "executable_time": f"{DAYS[1]}T00:00:00", "value": 5.0},
            {"entity_id": entities[1], "event_time": f"{DAYS[1]}T00:00:00",
             "knowledge_time": f"{DAYS[1]}T23:59:59.999999",
             "executable_time": f"{DAYS[2]}T00:00:00", "value": 7.0},
        ],
        snapshot_id=snapshot_id,
    )
    reader = FactorValueReader(gateway.store, factor_root)

    # 逐日該見到什麼:第一日只有第一隻,第二日起兩隻都在(值住表,批次一格都沒有)。
    expected_by_day = {
        DAYS[0]: {entities[0]: 5.0},
        DAYS[1]: {entities[0]: 5.0, entities[1]: 7.0},
        DAYS[2]: {entities[0]: 5.0, entities[1]: 7.0},
        DAYS[3]: {entities[0]: 5.0, entities[1]: 7.0},
        DAYS[4]: {entities[0]: 5.0, entities[1]: 7.0},
        DAYS[5]: {entities[0]: 5.0, entities[1]: 7.0},
    }
    for day in DAYS:
        taken = reader.latest_known(TABLE_FACTOR, day, snapshot_id=None, entity_ids=entities)
        assert dict(zip(taken["entity_id"], taken["value"])) == expected_by_day[day]
        # 交出來的欄與已退役那條表路一字不差(逐格對照見 tests/test_factorvalues.py)
        assert list(taken.columns) == [
            "entity_id", "event_time", "knowledge_time", "executable_time",
            "value", "snapshot_id", "factor_version_id",
        ]


def test_table_and_batch_are_read_together(gateway, factor_root, snapshot_id, entities):
    """同一條因子,一部分值住表、一部分住檔:一次問就兩邊都拎得到。"""
    version, _ = gateway.register_factor(
        BOTH_FACTOR, scale_kind="cardinal", procedure=_procedure(snapshot_id)
    )
    gateway.write_factor_values(
        BOTH_FACTOR,
        [
            {"entity_id": entities[0], "event_time": f"{DAYS[1]}T00:00:00",
             "knowledge_time": f"{DAYS[1]}T23:59:59.999999",
             "executable_time": f"{DAYS[2]}T00:00:00", "value": 11.0},
        ],
        snapshot_id=snapshot_id,
    )
    gateway.write_factor_batch(
        pd.DataFrame([_row(version.factor_version_id, entities[1], event=1, known=1, value=22.0)]),
        batch_key="toy-both",
        snapshot_id=snapshot_id,
        procedure_version=PROCEDURE_VERSION,
        root=factor_root,
    )

    taken = FactorValueReader(gateway.store, factor_root).latest_known(
        BOTH_FACTOR, DAYS[2], snapshot_id=None, entity_ids=entities
    )
    assert dict(zip(taken["entity_id"], taken["value"])) == {
        entities[0]: 11.0,
        entities[1]: 22.0,
    }
