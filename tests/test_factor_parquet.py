"""KARST-068 驗收:因子值改存壓縮檔案(D-032)。

四件事要證:

  1. **讀取介面**:給定快照 × 因子版本 × 日期窗口,取得回長表與寬表;知情時間
     閘照 D-021 一問就中。
  2. **合約一格沒有鬆**:前視(知情早過事件、可執行不在知情之後)、非有限數、
     重複的值,一律在落檔**之前**拒收。
  3. **``karst verify`` 納入因子檔雜湊**:檔被改過一個字、或者檔不在登記的落點,
     全庫核對即報;登記那一列本身亦有寫入者簽章。
  4. **遷移**:舊庫那批已經搬去檔案的值,重開時清空重建;行數對不上就一列不動。

全部用即用即棄的小庫與臨時目錄,不碰倉內那份真的。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from karst.errors import ContractViolation, ImmutabilityViolation, NotFound
from karst.factorstore import BATCH_COLUMNS, FILE_MISSING, FILE_TAMPERED, normalise_batch
from karst.gateway.service import Gateway
from karst.models import FormulaProcedure
from karst.schema import FACTOR_VALUES_TO_FILES_MIGRATION_KEY

BATCH = "toy"
PROCEDURE = "karst.tests.toy@1"
FIRST = "動量·12-1 月"
SECOND = "質素·毛利率"
DAYS = ("2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08")


@pytest.fixture()
def gateway(tmp_path):
    with Gateway.open(str(tmp_path / "karst.sqlite"), writer="測試") as opened:
        yield opened


@pytest.fixture()
def factor_root(tmp_path):
    return str(tmp_path / "factors")


@pytest.fixture()
def snapshot_id(gateway) -> str:
    return gateway.store.register_snapshot(
        source="test", taken_on="2026-01-09", content_hash="a" * 64, universe=("AAA", "BBB")
    )


@pytest.fixture()
def entities(gateway) -> tuple[int, int]:
    store = gateway.store
    return (
        store.register_entity(kind="etf", display_name="甲 ETF", local_code="ETF-000001"),
        store.register_entity(kind="etf", display_name="乙 ETF", local_code="ETF-000002"),
    )


@pytest.fixture()
def versions(gateway, snapshot_id) -> tuple[int, int]:
    ids = []
    for name, formula in ((FIRST, "close[-21] / close[-252] - 1"), (SECOND, "gp / assets")):
        version, _ = gateway.register_factor(
            name,
            scale_kind="cardinal",
            procedure=FormulaProcedure(formula=formula, input_data_version=snapshot_id),
        )
        ids.append(version.factor_version_id)
    return tuple(ids)


def _frame(versions, entities, *, days=DAYS) -> pd.DataFrame:
    """一張齊整的批次長表:兩條因子 × 兩隻 × 四日,最後一日沒有下一根 K 線。"""
    rows: list[dict[str, object]] = []
    for offset, version_id in enumerate(versions):
        for entity_id in entities:
            for index, day in enumerate(days):
                nxt = days[index + 1] if index + 1 < len(days) else None
                rows.append(
                    {
                        "factor_version_id": version_id,
                        "entity_id": entity_id,
                        "event_time": f"{day}T00:00:00",
                        "knowledge_time": f"{day}T23:59:59.999999",
                        "executable_time": None if nxt is None else f"{nxt}T00:00:00",
                        "value": 0.1 * (index + 1) + offset + 0.01 * entity_id,
                    }
                )
    return pd.DataFrame(rows)


@pytest.fixture()
def batch(gateway, factor_root, snapshot_id, versions, entities):
    return gateway.write_factor_batch(
        _frame(versions, entities),
        batch_key=BATCH,
        snapshot_id=snapshot_id,
        procedure_version=PROCEDURE,
        root=factor_root,
    )


@pytest.fixture()
def values(gateway, factor_root, batch):
    """讀取介面。要有東西讀才讀得到,所以連那一批值一齊備好。"""
    return gateway.factor_values(factor_root)


# ----------------------------------------------------------------------
# 驗收條件 1:讀取介面(快照 × 因子版本 × 日期窗口 → 長表 / 寬表)
# ----------------------------------------------------------------------


def test_values_live_in_the_file_and_the_store_only_registers_it(
    gateway, batch, snapshot_id, versions
):
    conn = gateway.store.connection
    assert conn.execute("SELECT COUNT(*) FROM factor_value").fetchone()[0] == 0
    assert batch.rows == 16
    assert batch.procedure_version == PROCEDURE
    assert batch.factor_version_ids == tuple(sorted(versions))
    assert batch.rows_of(versions[0]) == 8
    assert gateway.store.get_factor_value_batch(BATCH, snapshot_id).content_hash == batch.content_hash


def test_read_long_takes_a_snapshot_a_factor_version_and_a_date_window(values, snapshot_id):
    whole = values.read_long([FIRST], snapshot_id=snapshot_id)
    assert list(whole.columns) == list(BATCH_COLUMNS)
    assert len(whole) == 8

    window = values.read_long(
        [FIRST], snapshot_id=snapshot_id, start=DAYS[1], end=DAYS[2]
    )
    assert set(window["event_time"].dt.strftime("%Y-%m-%d")) == {DAYS[1], DAYS[2]}
    assert len(window) == 4

    # 釘死版本號的寫法與策略引用因子一樣(名稱@版本號)
    assert len(values.read_long([f"{FIRST}@1"], snapshot_id=snapshot_id)) == 8

    # 兩條因子一次過取回同一張長表
    both = values.read_long([FIRST, SECOND], snapshot_id=snapshot_id)
    assert len(both) == 16
    assert both["factor_version_id"].nunique() == 2


def test_read_long_gates_on_knowledge_time(values, snapshot_id):
    """D-021:一切查詢以知情時間為閘——當日收工才算知道那一日的值。"""
    as_of = values.read_long([FIRST], snapshot_id=snapshot_id, as_of=DAYS[1])
    assert set(as_of["event_time"].dt.strftime("%Y-%m-%d")) == {DAYS[0], DAYS[1]}
    assert values.read_long([FIRST], snapshot_id=snapshot_id, as_of="2026-01-04").empty


def test_read_panel_returns_a_date_by_entity_wide_table(values, snapshot_id, entities):
    panel = values.read_panel(FIRST, snapshot_id=snapshot_id)
    assert list(panel.columns) == sorted(entities)          # 欄名是實體編號,不是交易代號
    assert list(panel.index.strftime("%Y-%m-%d")) == list(DAYS)
    assert panel.shape == (4, 2)
    assert panel.iloc[0, 0] == pytest.approx(0.1 + 0.01 * sorted(entities)[0])

    narrowed = values.read_panel(
        FIRST, snapshot_id=snapshot_id, start=DAYS[2], entity_ids=[entities[0]]
    )
    assert narrowed.shape == (2, 1)


def test_reading_a_factor_that_was_never_computed_on_this_snapshot_says_so(
    gateway, values, snapshot_id, batch
):
    """查不到即拋,不回一張空表頂替:「沒有算過」與「算過而沒有值」是兩件事。"""
    gateway.register_factor(
        "動量·6 月",
        scale_kind="cardinal",
        procedure=FormulaProcedure(formula="close[-21] / close[-126] - 1",
                                   input_data_version=snapshot_id),
    )
    with pytest.raises(NotFound):
        values.read_long(["動量·6 月"], snapshot_id=snapshot_id)


# ----------------------------------------------------------------------
# 驗收條件 2:合約一格沒有鬆,而且在落檔之前擋
# ----------------------------------------------------------------------


def test_lookahead_is_refused_before_anything_is_written(
    gateway, values, factor_root, snapshot_id, versions, entities
):
    frame = _frame(versions, entities)
    frame.loc[0, "knowledge_time"] = "2026-01-04T00:00:00"      # 知情早過事件
    with pytest.raises(ContractViolation) as caught:
        gateway.write_factor_batch(
            frame, batch_key="bad", snapshot_id=snapshot_id,
            procedure_version=PROCEDURE, root=factor_root,
        )
    assert "前視" in str(caught.value)
    assert not values.path_for(batch_key="bad", snapshot_id=snapshot_id).exists()


def test_same_bar_execution_is_refused(gateway, factor_root, snapshot_id, versions, entities):
    frame = _frame(versions, entities)
    frame.loc[0, "executable_time"] = frame.loc[0, "knowledge_time"]
    with pytest.raises(ContractViolation) as caught:
        gateway.write_factor_batch(
            frame, batch_key="bad", snapshot_id=snapshot_id,
            procedure_version=PROCEDURE, root=factor_root,
        )
    assert "可執行時點" in str(caught.value)


def test_non_finite_values_and_duplicates_are_refused(versions, entities):
    nan = _frame(versions, entities)
    nan.loc[0, "value"] = np.nan
    with pytest.raises(ContractViolation) as blank:
        normalise_batch(nan)
    assert "非有限數" in str(blank.value)

    doubled = pd.concat([_frame(versions, entities), _frame(versions, entities)])
    with pytest.raises(ContractViolation) as twice:
        normalise_batch(doubled)
    assert "重複" in str(twice.value)


def test_a_batch_is_never_overwritten(
    gateway, factor_root, snapshot_id, versions, entities, batch
):
    """原封不動重寫當沿用;內容不同即拒收——改了算法就是另一批值,請用另一個批次名。"""
    again = gateway.write_factor_batch(
        _frame(versions, entities), batch_key=BATCH, snapshot_id=snapshot_id,
        procedure_version=PROCEDURE, root=factor_root,
    )
    assert again.content_hash == batch.content_hash
    assert again.written_at == batch.written_at

    changed = _frame(versions, entities)
    changed.loc[0, "value"] = 99.0
    with pytest.raises(ImmutabilityViolation):
        gateway.write_factor_batch(
            changed, batch_key=BATCH, snapshot_id=snapshot_id,
            procedure_version=PROCEDURE, root=factor_root,
        )


# ----------------------------------------------------------------------
# 驗收條件 3:karst verify 納入因子檔雜湊
# ----------------------------------------------------------------------


def test_verify_is_clean_after_a_batch_goes_through_the_gateway(gateway, factor_root, batch):
    assert gateway.verify(factor_root=factor_root) == []


def test_verify_catches_a_file_edited_behind_the_gateway(gateway, factor_root, values, batch):
    frame = pd.read_parquet(batch.path, engine="pyarrow")
    frame.loc[0, "value"] = 42.0
    frame.to_parquet(batch.path, engine="pyarrow", index=False)

    findings = gateway.verify(factor_root=factor_root)
    assert [f.problem for f in findings] == [FILE_TAMPERED]
    assert findings[0].row_key.startswith(BATCH)


def test_verify_catches_a_missing_file(gateway, factor_root, batch):
    values_path = batch.path
    import os

    os.remove(values_path)
    findings = gateway.verify(factor_root=factor_root)
    assert [f.problem for f in findings] == [FILE_MISSING]


def test_the_registration_row_itself_needs_a_gateway_signature(
    gateway, factor_root, snapshot_id, versions, entities
):
    """繞過唯一入口自己塞一列登記,``verify`` 一掃就見到——那一列雜湊是整批值的憑證。"""
    store = gateway.store
    store.register_factor_value_batch(
        batch_key="smuggled", snapshot_id=snapshot_id, procedure_version=PROCEDURE,
        path=str(gateway.factor_values(factor_root).path_for(
            batch_key="smuggled", snapshot_id=snapshot_id)),
        content_hash="b" * 64, rows=1, members={versions[0]: 1},
    )
    problems = {f.table for f in gateway.verify(factor_root=factor_root)}
    assert "factor_value_batch" in problems
    assert "factor_value_batch_member" in problems


# ----------------------------------------------------------------------
# 驗收條件 4:舊庫那批值搬走之後清空重建
# ----------------------------------------------------------------------


def _legacy_rows(entity_id: int) -> list[dict[str, object]]:
    return [
        {
            "entity_id": entity_id,
            "event_time": f"{day}T00:00:00",
            "knowledge_time": f"{day}T23:59:59.999999",
            "executable_time": None,
            "value": 0.5 + index,
        }
        for index, day in enumerate(DAYS)
    ]


def test_old_values_are_cleared_only_after_the_file_registration_matches(
    tmp_path, factor_root, snapshot_id
):
    """三項齊備才清:登記得到、行數對得上、檔案真的在。缺一項就一列都不動。"""
    path = str(tmp_path / "legacy.sqlite")
    with Gateway.open(path, writer="測試") as gateway:
        store = gateway.store
        snapshot = store.register_snapshot(
            source="test", taken_on="2026-01-09", content_hash="a" * 64
        )
        entity = store.register_entity(kind="etf", display_name="甲 ETF")
        version, _ = gateway.register_factor(
            FIRST, scale_kind="cardinal",
            procedure=FormulaProcedure(formula="x", input_data_version=snapshot),
        )
        gateway.write_factor_values(FIRST, _legacy_rows(entity), snapshot_id=snapshot)
        assert store.connection.execute("SELECT COUNT(*) FROM factor_value").fetchone()[0] == 4

    # 未有檔案登記:重開一次,舊值一列都不動
    with Gateway.open(path, writer="測試") as gateway:
        conn = gateway.store.connection
        assert conn.execute("SELECT COUNT(*) FROM factor_value").fetchone()[0] == 4
        assert conn.execute(
            "SELECT COUNT(*) FROM schema_meta WHERE key = ?",
            (FACTOR_VALUES_TO_FILES_MIGRATION_KEY,),
        ).fetchone()[0] == 0

        # 搬去檔案(行數逐個因子版本對得上)
        frame = pd.DataFrame(_legacy_rows(entity))
        frame["factor_version_id"] = version.factor_version_id
        gateway.write_factor_batch(
            frame, batch_key=BATCH, snapshot_id=snapshot,
            procedure_version=PROCEDURE, root=factor_root,
        )

    # 再重開:三項齊備,舊值清空重建,而因子、版本、實體編號一個都沒有動
    with Gateway.open(path, writer="測試") as gateway:
        conn = gateway.store.connection
        assert conn.execute("SELECT COUNT(*) FROM factor_value").fetchone()[0] == 0
        note = conn.execute(
            "SELECT value FROM schema_meta WHERE key = ?",
            (FACTOR_VALUES_TO_FILES_MIGRATION_KEY,),
        ).fetchone()
        assert note is not None and "4 個因子值" in note[0]
        assert conn.execute("SELECT value FROM schema_meta WHERE key = 'schema_version'"
                            ).fetchone()[0] == "11"
        assert gateway.store.get_factor_version(FIRST).factor_version_id == version.factor_version_id
        assert gateway.store.get_entity(entity).entity_id == entity
        # 表結構仍在:寫得入、讀得回(小批人手登記那條路照舊)
        assert gateway.write_factor_values(FIRST, _legacy_rows(entity), snapshot_id=snapshot) == 4


def test_a_short_registration_leaves_every_old_value_alone(tmp_path, factor_root):
    """檔案登記的行數少過表內的:寧可庫檔留著大,不猜「應該搬完了」。"""
    path = str(tmp_path / "mismatch.sqlite")
    with Gateway.open(path, writer="測試") as gateway:
        store = gateway.store
        snapshot = store.register_snapshot(
            source="test", taken_on="2026-01-09", content_hash="a" * 64
        )
        entity = store.register_entity(kind="etf", display_name="甲 ETF")
        version, _ = gateway.register_factor(
            FIRST, scale_kind="cardinal",
            procedure=FormulaProcedure(formula="x", input_data_version=snapshot),
        )
        gateway.write_factor_values(FIRST, _legacy_rows(entity), snapshot_id=snapshot)
        frame = pd.DataFrame(_legacy_rows(entity)[:2])       # 只搬走一半
        frame["factor_version_id"] = version.factor_version_id
        gateway.write_factor_batch(
            frame, batch_key=BATCH, snapshot_id=snapshot,
            procedure_version=PROCEDURE, root=factor_root,
        )

    with Gateway.open(path, writer="測試") as gateway:
        conn = gateway.store.connection
        assert conn.execute("SELECT COUNT(*) FROM factor_value").fetchone()[0] == 4
        assert conn.execute(
            "SELECT COUNT(*) FROM schema_meta WHERE key = ?",
            (FACTOR_VALUES_TO_FILES_MIGRATION_KEY,),
        ).fetchone()[0] == 0
