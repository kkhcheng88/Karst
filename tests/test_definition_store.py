"""KARST-021 驗收:單一定義庫骨架。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況。
"""

from __future__ import annotations

import sqlite3

import pandas as pd
import pytest

from karst import (
    NOT_APPLICABLE,
    ContractViolation,
    DefinitionStore,
    DuplicateDefinition,
    FormulaProcedure,
    MaterialProcedure,
    NotFound,
    TickerNotResolved,
    freeze_batch,
    read_batch,
)

MOMENTUM = "動量·12-1 月"
MOMENTUM_PROCEDURE = FormulaProcedure(
    formula="close[-21] / close[-252] - 1",
    input_data_version="2026-08-27-a1b2c3d4e5f6",
)


@pytest.fixture()
def store(tmp_path):
    with DefinitionStore.open(str(tmp_path / "karst.sqlite")) as opened:
        yield opened


@pytest.fixture()
def apple(store):
    return store.register_entity(kind="company", display_name="Apple Inc.", cik="320193")


# 驗收條件 1:寫得入、讀得回,值帶事件時間與知情時間(D-021 第 1、3 條)
def test_value_round_trips_with_both_timestamps(store, apple):
    store.register_factor(MOMENTUM, scale_kind="cardinal", procedure=MOMENTUM_PROCEDURE)
    store.write_factor_values(
        MOMENTUM,
        [
            {
                "entity_id": apple,
                "event_time": "2026-08-25",
                "knowledge_time": "2026-08-27T13:30:00",
                "value": 0.3142,
            }
        ],
    )

    frame = store.read_factor_values(MOMENTUM, as_of="2026-08-27")
    assert len(frame) == 1
    row = frame.iloc[0]
    assert row["entity_id"] == apple
    assert row["event_time"].startswith("2026-08-25")
    assert row["knowledge_time"].startswith("2026-08-27T13:30")
    assert row["value"] == pytest.approx(0.3142)

    # 知情時間是閘:8 月 26 日還未知道這個值
    assert store.read_factor_values(MOMENTUM, as_of="2026-08-26").empty
    assert store.value_for(MOMENTUM, apple, as_of="2026-08-27") == pytest.approx(0.3142)


# 驗收條件 2:出第二版時舊版一字不變,新版記得住父版本,追得回上一版(D-021 第 9 條)
def test_second_version_keeps_first_intact_and_records_parent(store, apple):
    first = store.register_factor(
        MOMENTUM, scale_kind="cardinal", procedure=MOMENTUM_PROCEDURE, description="初版"
    )
    store.write_factor_values(
        MOMENTUM,
        [{"entity_id": apple, "event_time": "2026-08-25", "knowledge_time": "2026-08-26", "value": 0.11}],
    )

    second = store.new_factor_version(
        MOMENTUM,
        scale_kind="cardinal",
        procedure=FormulaProcedure(
            formula="close[-21] / close[-252] - 1  # 剔除最近一週",
            input_data_version="2026-08-27-a1b2c3d4e5f6",
        ),
        description="剔除最近一週",
    )

    assert second.version_no == 2
    assert second.parent_version_id == first.factor_version_id

    reread_first = store.get_factor_version(MOMENTUM, version_no=1)
    assert reread_first == first  # 舊版一字不變
    assert store.get_factor_version(MOMENTUM).version_no == 2  # 留空取最新版

    chain = store.factor_version_chain(MOMENTUM)
    assert [v.version_no for v in chain] == [2, 1]
    assert chain[-1].parent_version_id is None

    # 舊版的值照舊掛在舊版上;新版未寫值就是沒有值
    assert len(store.read_factor_values(MOMENTUM, version_no=1, as_of="2026-08-27")) == 1
    assert store.read_factor_values(MOMENTUM, version_no=2, as_of="2026-08-27").empty

    # 落庫後不可改,只可出新版——連直接改庫都擋
    with pytest.raises(sqlite3.IntegrityError):
        store._conn.execute(
            "UPDATE factor_version SET formula = 'x' WHERE factor_version_id = ?",
            (first.factor_version_id,),
        )


# 驗收條件 3:缺失=不參與,不是 0;兩者分辨得到(D-021 第 4 條)
def test_missing_value_is_not_applicable_not_zero(store, apple):
    quiet = store.register_entity(kind="company", display_name="Quiet Co.", cik="111111")
    store.register_factor(MOMENTUM, scale_kind="cardinal", procedure=MOMENTUM_PROCEDURE)
    store.write_factor_values(
        MOMENTUM,
        [{"entity_id": apple, "event_time": "2026-08-25", "knowledge_time": "2026-08-26", "value": 0.0}],
    )

    really_zero = store.value_for(MOMENTUM, apple, as_of="2026-08-27")  # 值真的是零
    not_in_play = store.value_for(MOMENTUM, quiet, as_of="2026-08-27")  # 不參與

    assert really_zero == 0.0
    assert really_zero is not NOT_APPLICABLE
    assert not_in_play is NOT_APPLICABLE

    # 缺失不是「填了 0」,而是根本沒有那一列
    latest = store.latest_known_values(MOMENTUM, as_of="2026-08-27")
    assert list(latest["entity_id"]) == [apple]

    # 「不參與」不可當真假值用,逼調用方寫明,免得與 0 混為一談
    with pytest.raises(TypeError):
        bool(not_in_play)


# 驗收條件 4:缺刻度型或缺產生程序即寫不入(D-021 第 2、6 條)
def test_registration_rejects_missing_scale_kind_or_procedure(store):
    with pytest.raises(ContractViolation, match="刻度型"):
        store.register_factor(MOMENTUM, procedure=MOMENTUM_PROCEDURE)

    with pytest.raises(ContractViolation, match="產生程序"):
        store.register_factor(MOMENTUM, scale_kind="cardinal")

    with pytest.raises(ContractViolation, match="輸入數據版本"):
        store.register_factor(
            MOMENTUM,
            scale_kind="cardinal",
            procedure=FormulaProcedure(formula="close[-21] / close[-252] - 1", input_data_version=""),
        )

    with pytest.raises(ContractViolation, match="判官版本"):
        store.register_factor(
            "人物判官·Situational Awareness",
            scale_kind="boolean",
            procedure=MaterialProcedure(material="13F 2026Q2", judge_version=""),
        )

    # 四次都寫不入,庫裡一個因子都沒有
    with pytest.raises(NotFound):
        store.get_factor_version(MOMENTUM)


# D-026 第 2 條:代號有生效起訖,按日期解析到正確實體
def test_ticker_resolves_by_date_to_the_right_entity(store):
    old = store.register_entity(kind="company", display_name="Randgold Resources", cik="1003986")
    new = store.register_entity(kind="company", display_name="Barrick Gold", cik="756894")

    store.register_ticker(old, "GOLD", "2010-01-01", "2018-12-31")
    store.register_ticker(new, "GOLD", "2019-01-02")

    assert store.resolve_ticker("GOLD", "2015-06-30") == old
    assert store.resolve_ticker("GOLD", "2026-08-27") == new

    with pytest.raises(TickerNotResolved):
        store.resolve_ticker("GOLD", "2019-01-01")  # 交接中間那日沒有人持有

    with pytest.raises(DuplicateDefinition):
        store.register_ticker(new, "GOLD", "2015-01-01")  # 日子重疊即拒收

    assert [(p.entity_id, p.valid_to) for p in store.ticker_history("GOLD")] == [
        (old, "2018-12-31"),
        (new, None),
    ]


# D-026 第 3 條:每次拉數一個快照編號(日期+內容雜湊),值可掛回快照追溯
def test_snapshot_registers_a_frozen_parquet_batch(store, apple, tmp_path):
    prices = pd.DataFrame(
        {"entity_id": [apple, apple], "date": ["2026-08-25", "2026-08-26"], "close": [231.5, 233.0]}
    )
    snapshot_id = freeze_batch(
        store,
        prices,
        root=tmp_path / "data",
        source="yfinance",
        taken_on="2026-08-27",
        universe=["AAPL"],
    )

    assert snapshot_id.startswith("2026-08-27-")
    snapshot = store.get_snapshot(snapshot_id)
    assert snapshot.source == "yfinance"
    assert snapshot.universe == ("AAPL",)
    assert read_batch(store, snapshot_id).shape == prices.shape

    # 同一批內容重登記回同一個編號,不會生第二個影像
    assert freeze_batch(
        store, prices, root=tmp_path / "data", source="yfinance", taken_on="2026-08-27"
    ) == snapshot_id

    # 因子值掛得住快照編號,追溯到批次:因子版本 × 數據快照 × 產生程序版本
    store.register_factor(MOMENTUM, scale_kind="cardinal", procedure=MOMENTUM_PROCEDURE)
    store.write_factor_values(
        MOMENTUM,
        [{"entity_id": apple, "event_time": "2026-08-26", "knowledge_time": "2026-08-27", "value": 0.2}],
        snapshot_id=snapshot_id,
    )
    assert store.read_factor_values(MOMENTUM, as_of="2026-08-27").iloc[0]["snapshot_id"] == snapshot_id


# ----------------------------------------------------------------------
# KARST-044:換倉節奏選單只有一份正本,定義庫與引擎同取一處
# ----------------------------------------------------------------------


# KARST-044 驗收條件 1:節奏清單全倉只有一份正本,定義庫校驗與引擎同取一處
def test_the_cadence_menu_has_exactly_one_source_of_truth():
    from karst.engine.contracts import CADENCES
    from karst.store import rebalance_cadences

    roster = rebalance_cadences()

    # 定義庫的選單不是另存一份,是由引擎那份正本推出來的:兩邊逐個取值對得上
    assert set(roster) == set(CADENCES)
    # 週度在正本裡,所以定義庫的校驗自然收得到(KARST-043 撞到的正是這一格漏了)
    assert "weekly" in roster
    assert roster["weekly"] == "每週"

    # 正本加一個節奏,定義庫即刻認得——不用再改本檔一個字
    import karst.engine.contracts as contracts

    original = contracts.CADENCES
    try:
        contracts.CADENCES = frozenset({*original, "fortnightly"})
        grown = rebalance_cadences()
        assert "fortnightly" in grown
        # 中文名漏了就用取值本身頂上,不會反過來令那個節奏收不到
        assert grown["fortnightly"] == "fortnightly"
    finally:
        contracts.CADENCES = original


# KARST-044 驗收條件 1(下半):校驗確實取自那一處,不是另一份清單
def test_the_store_validates_every_cadence_the_engine_knows(store):
    from karst.engine.contracts import CADENCES
    from karst.store import rebalance_cadences

    store.register_factor(MOMENTUM, scale_kind="cardinal", procedure=MOMENTUM_PROCEDURE)
    store.register_strategy("趨勢波段", strategy_type="technical", factor_refs=[MOMENTUM])

    # 引擎認得的每一個節奏,定義庫的合約檢查都收得住
    for cadence in sorted(CADENCES):
        assert DefinitionStore._check_cadence(cadence, "示例") == cadence

    # 不在正本裡的照樣拒收,而且錯訊列的是正本那份清單
    with pytest.raises(ContractViolation) as caught:
        DefinitionStore._check_cadence("fortnightly", "示例")
    assert sorted(rebalance_cadences()) == sorted(CADENCES)
    assert "fortnightly" in str(caught.value)

    # 缺節奏一樣拒收:不設預設值,不代用戶揀一個
    with pytest.raises(ContractViolation) as missing:
        DefinitionStore._check_cadence(None, "示例")
    assert "不設預設值" in str(missing.value)
