"""KARST-088 驗收:因子取值只留一條路——新模組與舊三份實作逐格相同。

架構審視候選五要抓的是**靜默分歧**:同一個問題(某隻股票在某個知情時點上,這條
因子最新已知的值是多少)以前有三份實作各自答,分岔了不會有人發現。所以本檔比的
不是「新模組跑得動」,是「新模組與舊三份逐格相同」:

  舊甲  定義庫 sqlite 那條   ``DefinitionStore.latest_known_values`` / ``value_for``
  舊乙  因子值批次那條       ``FactorValueStore.read_long`` / ``read_panel``
  舊丙  引擎那份合流         ``engine.factorvalues.FactorValueSource``

再加兩處**生產呼叫者**換路前後不變:引擎選股的因子面板、因子預測力的對齊表。
(派工原以為網頁取數層是第三處呼叫者;實查 ``karst/web/`` 一處都沒有讀因子值,
見 ``.kira/assumptions.jsonl`` 的 A-013。)

舊三份既然要刪,對照怎樣留得住
------------------------------

本檔先在**舊實作未刪之前**跑一次三方對照(全部通過),同一批玩具數據上把舊三份
的輸出逐格抄進 ``tests/frozen/karst-088-retired-implementations.json``。之後刪了
舊實作,這裡比的仍然是那三份當日交出來的那幾格數,不是新模組自己等於自己。
凍檔要重生,即等於改口徑——那是一次裁決,不是一次修測試。

舊乙那條的**長表**(``FactorValueStore.read_long``)不在凍檔裡:它是批次檔的讀檔
層,新模組建基於它,留在原地,所以照舊即場對照。

玩具數據,固定日子,不連外部數據;全部用即用即棄的小庫與臨時目錄。
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from karst.factorpredict import align_factor_to_forward_returns, daily_ic, summarize_ic
from karst.factorstore import BATCH_COLUMNS
from karst.factorvalues import FactorValueReader
from karst.gateway.service import Gateway
from karst.models import FormulaProcedure

BATCH_FACTOR = "動量·批次玩具"
TABLE_FACTOR = "質素·表玩具"
BOTH_FACTOR = "價值·兩邊玩具"

BATCH_KEY = "toy-batch"
BOTH_KEY = "toy-both"
PROCEDURE_VERSION = "karst.tests.toy@1"

DAYS = ("2026-03-02", "2026-03-03", "2026-03-04", "2026-03-05", "2026-03-06", "2026-03-09")
DATES = pd.DatetimeIndex([pd.Timestamp(day) for day in DAYS])

#: 遲到那一隻:值的事件時點是第一日,但第四日收工才知道(披露滯後那一類)。
LATE_VALUE = 99.0
LATE_KNOWN_ON = 3

#: 舊三份實作在本檔這批玩具數據上交出來的那幾格(刪它們之前抄下來的)。
FROZEN = json.loads(
    (Path(__file__).parent / "frozen" / "karst-088-retired-implementations.json").read_text(
        encoding="utf-8"
    )
)


def _records(frame: pd.DataFrame) -> list[dict]:
    """一張表收成可以與凍檔逐格比的樣子(缺值一律寫成 ``None``)。"""
    return [
        {column: (None if pd.isna(record[column]) else record[column]) for column in frame.columns}
        for record in frame.to_dict("records")
    ]


def _procedure(snapshot_id: str) -> FormulaProcedure:
    return FormulaProcedure(formula="close[-21] / close[-252] - 1", input_data_version=snapshot_id)


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
def gateway(tmp_path):
    with Gateway.open(str(tmp_path / "karst.sqlite"), writer="KARST-088-測試") as opened:
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
def batch_factor(gateway, factor_root, snapshot_id, entities):
    """一條值全部住 Parquet 的因子(舊乙那條路的對象)。"""
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
    rows.append(_row(version_id, entities[2], event=0, known=LATE_KNOWN_ON, value=LATE_VALUE))
    gateway.write_factor_batch(
        pd.DataFrame(rows),
        batch_key=BATCH_KEY,
        snapshot_id=snapshot_id,
        procedure_version=PROCEDURE_VERSION,
        root=factor_root,
    )
    return version


@pytest.fixture()
def table_factor(gateway, snapshot_id, entities):
    """一條值全部住 ``factor_value`` 表的因子(舊甲那條路的對象)。"""
    version, _ = gateway.register_factor(
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
            # 同一隻、同一個事件時點,更遲知道的一個值取代前者(D-021 第 5 條)。
            {"entity_id": entities[0], "event_time": f"{DAYS[0]}T00:00:00",
             "knowledge_time": f"{DAYS[2]}T23:59:59.999999",
             "executable_time": f"{DAYS[3]}T00:00:00", "value": 5.5},
            # 不可執行值:知得到,成交不到(該快照日曆上沒有下一根 K 線)。
            {"entity_id": entities[2], "event_time": f"{DAYS[5]}T00:00:00",
             "knowledge_time": f"{DAYS[5]}T23:59:59.999999",
             "executable_time": None, "value": 3.0},
        ],
        snapshot_id=snapshot_id,
    )
    return version


@pytest.fixture()
def both_factor(gateway, factor_root, snapshot_id, entities):
    """一條因子一部分值住表、一部分住檔(舊丙那份合流的對象)。"""
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
        batch_key=BOTH_KEY,
        snapshot_id=snapshot_id,
        procedure_version=PROCEDURE_VERSION,
        root=factor_root,
    )
    return version


@pytest.fixture()
def reader(gateway, factor_root) -> FactorValueReader:
    return FactorValueReader(gateway.store, factor_root)


def _price_frame(entities) -> pd.DataFrame:
    """日線長表(開價與收價各自不同,好證得到回報起點取的是哪一個)。"""
    rows = []
    for index, entity in enumerate(entities):
        for step, day in enumerate(DAYS):
            close = 100.0 + index * 10 + step
            rows.append(
                {"date": day, "entity_id": entity, "open": close - 1.5, "close": close}
            )
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# 舊甲:定義庫 sqlite 那條
# ----------------------------------------------------------------------


def test_matches_the_retired_sqlite_path_cell_for_cell(
    reader, batch_factor, table_factor, both_factor, entities
):
    """值住表那條因子:新模組逐日取回的面板,與舊 SQL 視窗函數那條逐格相同。"""
    assert list(FROZEN["sqlite_columns"]) == list(
        reader.latest_known(TABLE_FACTOR, DAYS[0], snapshot_id=None, entity_ids=entities).columns
    )
    for day in DAYS:
        taken = reader.latest_known(TABLE_FACTOR, day, snapshot_id=None, entity_ids=entities)
        assert _records(taken) == FROZEN["sqlite_latest"][day]


def test_matches_the_retired_single_point_lookup(
    reader, batch_factor, table_factor, both_factor, entities
):
    """單點查詢:舊 ``value_for`` 答什麼,新模組答什麼(查不到即「不參與」)。"""
    from karst.models import NOT_APPLICABLE

    for day in DAYS:
        for entity in entities:
            taken = reader.value_for(TABLE_FACTOR, entity, day, snapshot_id=None)
            frozen = FROZEN["value_for"][day][str(entity)]
            if frozen is None:
                assert taken is NOT_APPLICABLE
            else:
                assert taken == frozen


# ----------------------------------------------------------------------
# 舊乙:因子值批次那條
# ----------------------------------------------------------------------


def test_matches_the_batch_long_table_cell_for_cell(
    gateway, factor_root, reader, batch_factor, snapshot_id, entities
):
    """整段長表:新模組的 ``history`` 與舊 ``read_long`` 前六格逐格相同。"""
    files = gateway.factor_values(factor_root)
    before = files.read_long([BATCH_FACTOR], snapshot_id=snapshot_id)
    after = reader.history(
        [BATCH_FACTOR], snapshot_id=snapshot_id, as_of=None, start=None, end=None,
        entity_ids=None,
    )
    assert list(after.columns)[: len(BATCH_COLUMNS)] == list(BATCH_COLUMNS)
    pd.testing.assert_frame_equal(
        after[list(BATCH_COLUMNS)].reset_index(drop=True),
        before[list(BATCH_COLUMNS)].reset_index(drop=True),
        check_dtype=False,
    )
    # 快照那一格由登記補回來,批次檔本身沒有這一欄。
    assert set(after["snapshot_id"]) == {snapshot_id}


def test_matches_the_batch_long_table_under_every_window(
    gateway, factor_root, reader, batch_factor, snapshot_id, entities
):
    """知情閘、事件窗口、實體收窄三格,新舊逐格相同。"""
    files = gateway.factor_values(factor_root)
    cases = [
        {"as_of": DAYS[2], "start": None, "end": None, "entity_ids": None},
        {"as_of": None, "start": DAYS[1], "end": DAYS[3], "entity_ids": None},
        {"as_of": None, "start": None, "end": None, "entity_ids": entities[:2]},
        {"as_of": DAYS[LATE_KNOWN_ON], "start": DAYS[0], "end": DAYS[0],
         "entity_ids": entities},
    ]
    for case in cases:
        before = files.read_long([BATCH_FACTOR], snapshot_id=snapshot_id, **case)
        after = reader.history([BATCH_FACTOR], snapshot_id=snapshot_id, **case)
        pd.testing.assert_frame_equal(
            after[list(BATCH_COLUMNS)].reset_index(drop=True),
            before[list(BATCH_COLUMNS)].reset_index(drop=True),
            check_dtype=False,
        )


def test_matches_the_batch_wide_panel_cell_for_cell(
    reader, batch_factor, table_factor, both_factor, snapshot_id
):
    """寬面板:新模組的 ``panel`` 與舊 ``read_panel`` 逐格相同。"""
    for as_of in (None, DAYS[2], DAYS[LATE_KNOWN_ON]):
        wide = reader.panel(
            BATCH_FACTOR, snapshot_id=snapshot_id, as_of=as_of, start=None, end=None,
            entity_ids=None,
        )
        frozen = FROZEN["batch_panels"]["整段" if as_of is None else as_of]
        assert [str(stamp.date()) for stamp in wide.index] == frozen["index"]
        assert [int(column) for column in wide.columns] == frozen["columns"]
        assert [
            [None if pd.isna(cell) else float(cell) for cell in row]
            for row in wide.to_numpy()
        ] == frozen["values"]


def test_a_factor_with_no_batch_in_that_snapshot_is_not_papered_over(
    reader, table_factor, snapshot_id
):
    """指名快照而沒有批次登記即拋——「沒有算過」不可以用一張空表頂替。"""
    from karst.errors import NotFound

    with pytest.raises(NotFound):
        reader.history(
            [TABLE_FACTOR], snapshot_id=snapshot_id, as_of=None, start=None, end=None,
            entity_ids=None,
        )


# ----------------------------------------------------------------------
# 舊丙:引擎那份合流
# ----------------------------------------------------------------------


def test_matches_the_retired_engine_source_cell_for_cell(
    reader, batch_factor, table_factor, both_factor, entities
):
    """三條因子(住檔、住表、兩邊都有)逐日比:新模組與舊合流那份逐格相同。"""
    for name in (BATCH_FACTOR, TABLE_FACTOR, BOTH_FACTOR):
        for day in DAYS:
            after = reader.latest_known(name, day, snapshot_id=None, entity_ids=entities)
            assert list(after.columns) == list(FROZEN["merged_columns"])
            assert _records(after) == FROZEN["merged"][name][day]


def test_the_knowledge_gate_still_hides_the_late_value(reader, batch_factor, entities):
    """遲到那一隻在知情之前一格都看不見,知情當日起才入面板(D-021 第 3 條)。"""
    late = entities[2]
    for index, day in enumerate(DAYS):
        frame = reader.latest_known(
            BATCH_FACTOR, day, snapshot_id=None, entity_ids=entities
        )
        seen = dict(zip(frame["entity_id"], frame["value"]))
        if index < LATE_KNOWN_ON:
            assert late not in seen
        else:
            assert seen[late] == LATE_VALUE


def test_non_executable_values_come_back_with_an_empty_executable_time(
    reader, table_factor, entities
):
    """不可執行值照樣交出去,可執行時點留空——留空不等於缺值。"""
    frame = reader.latest_known(
        TABLE_FACTOR, DAYS[5], snapshot_id=None, entity_ids=[entities[2]]
    )
    assert len(frame) == 1
    assert frame.iloc[0]["value"] == 3.0
    # 留空的時點讀回來是缺值標記(pandas 把 object 欄的 None 收成 NaN),
    # 與已退役那三條路交出來的一模一樣。
    assert pd.isna(frame.iloc[0]["executable_time"])


# ----------------------------------------------------------------------
# 兩處生產呼叫者:換路前後不變
# ----------------------------------------------------------------------


def test_the_engine_panel_is_the_readers_panel(
    gateway, factor_root, reader, batch_factor, entities
):
    """引擎選股那張「決策日 × 實體」面板,逐格等於新模組逐日取回的值。"""
    from karst.engine import read_factor_panel

    panel = read_factor_panel(
        gateway.store, BATCH_FACTOR, list(DATES), entity_ids=entities
    )
    for day, stamp in zip(DAYS, DATES):
        taken = reader.latest_known(
            BATCH_FACTOR, day, snapshot_id=None, entity_ids=entities
        )
        expected = dict(zip(taken["entity_id"], taken["value"]))
        for entity in entities:
            cell = panel.loc[stamp, entity]
            if entity in expected:
                assert cell == pytest.approx(expected[entity])
            else:
                assert pd.isna(cell)


def test_the_predictive_power_alignment_is_unchanged(
    gateway, factor_root, reader, batch_factor, snapshot_id, entities
):
    """因子預測力:由新模組餵入與由舊 ``read_long`` 餵入,對齊表與 IC 摘要逐格相同。"""
    files = gateway.factor_values(factor_root)
    prices = _price_frame(entities)

    before_long = files.read_long([BATCH_FACTOR], snapshot_id=snapshot_id)
    after_long = reader.history(
        [BATCH_FACTOR], snapshot_id=snapshot_id, as_of=None, start=None, end=None,
        entity_ids=None,
    )
    for horizon in (1, 2):
        before = align_factor_to_forward_returns(before_long, prices, horizon=horizon)
        after = align_factor_to_forward_returns(after_long, prices, horizon=horizon)
        pd.testing.assert_frame_equal(before, after, check_dtype=False)
        pd.testing.assert_frame_equal(
            summarize_ic(daily_ic(before)), summarize_ic(daily_ic(after)),
            check_dtype=False,
        )
