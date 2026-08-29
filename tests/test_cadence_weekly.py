"""KARST-044 驗收:換倉節奏加週度,定義庫與引擎同一份節奏清單。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況。

另外兩條(節奏清單只有一份正本、定義庫收得住引擎認得的每一個節奏)住在
``tests/test_definition_store.py``,與它們守住的那一層同一個檔。
"""

from __future__ import annotations

import re
import sqlite3

import numpy as np
import pandas as pd
import pytest

from karst import DefinitionStore, FormulaProcedure, schema
from karst.engine import PricePanel, run_ranking_rebalance
from karst.gateway import Gateway
from karst.gateway.cli import main

FACTOR = "動量·玩具 12-1 月"
PROCEDURE = FormulaProcedure(
    formula="close[-21] / close[-252] - 1",
    input_data_version="2026-08-28-toy000000000",
)
STRATEGY = "週度輪動"
PARAM_SET = "現役"

# 改表之前那條寫死的 CHECK:日/月/季,沒有週度(KARST-043 就是撞到它)。
LEGACY_CADENCES = "'daily', 'monthly', 'quarterly'"

DATES = pd.bdate_range("2026-01-02", periods=90)


@pytest.fixture()
def karst(tmp_path, monkeypatch):
    """回傳一個「跑一句 karst 命令」的函數:(回傳碼, 螢幕輸出)。"""
    import io

    monkeypatch.delenv("KARST_GATEWAY_KEY", raising=False)
    monkeypatch.setenv("KARST_WRITER", "KARST-044-cadence")
    path = str(tmp_path / "karst.sqlite")

    def run(*argv: str) -> tuple[int, str]:
        buffer = io.StringIO()
        code = main(["--store", path, *argv], out=buffer)
        return code, buffer.getvalue()

    run.path = path  # type: ignore[attr-defined]
    return run


def _toy_panel(entity_ids):
    """玩具價格面板:固定種子,不連外部數據。"""
    generator = np.random.default_rng(20260828)
    steps = generator.normal(0.0004, 0.01, (len(DATES), len(entity_ids)))
    close = pd.DataFrame(
        100.0 * np.exp(np.cumsum(steps, axis=0)), index=DATES, columns=entity_ids
    )
    open_prices = close.shift(1)
    open_prices.iloc[0] = 100.0
    return PricePanel.from_frames(open=open_prices * 1.002, close=close)


def _toy_rows(entity_ids):
    """玩具因子值:前半期由頭到尾遞減,後半期倒轉,換倉時排名一定會翻。"""
    half = len(DATES) // 2
    rows = []
    for position, day in enumerate(DATES):
        stamp = day.strftime("%Y-%m-%d")
        # 可執行時點 = 下一根 K 線;最後一根之後沒有下一根,留空(D-021 第 3 條)
        next_stamp = (
            DATES[position + 1].strftime("%Y-%m-%d") if position + 1 < len(DATES) else None
        )
        high_first = position < half
        for rank, entity_id in enumerate(entity_ids):
            rows.append(
                {
                    "entity_id": entity_id,
                    "event_time": stamp,
                    "knowledge_time": stamp,
                    "executable_time": next_stamp,
                    "value": float(len(entity_ids) - rank if high_first else rank + 1),
                }
            )
    return rows


def _param_set_rows(path: str) -> list[tuple]:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return [
            tuple(row)
            for row in conn.execute(
                "SELECT param_set_id, strategy_version_id, name, version_no,"
                " parent_version_id, rebalance_cadence, created_at FROM param_set"
                " ORDER BY param_set_id"
            )
        ]
    finally:
        conn.close()


def _triggers(conn: sqlite3.Connection) -> list[str]:
    return sorted(
        str(row[0])
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger'"
            " AND tbl_name IN ('param_set', 'param_value')"
        )
    )


def _downgrade_to_the_old_cadence_check(path: str) -> None:
    """把一個現成的庫改回舊版表結構,好證得到遷移真的搬得動有資料的舊庫。

    與遷移同一套機械動作,只是方向倒轉:新表用回舊那條寫死的 CHECK。
    """
    legacy_ddl = schema._DDL_TEMPLATE.replace(schema._CADENCE_SLOT, LEGACY_CADENCES)
    statement = re.search(
        r"CREATE TABLE IF NOT EXISTS param_set \(.*?\n\);", legacy_ddl, re.DOTALL
    )
    assert statement is not None
    create_legacy = statement.group(0).replace(
        "CREATE TABLE IF NOT EXISTS param_set (", "CREATE TABLE param_set_legacy (", 1
    )

    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            "PRAGMA foreign_keys = OFF;\n"
            "BEGIN;\n"
            f"{create_legacy}\n"
            "INSERT INTO param_set_legacy SELECT * FROM param_set;\n"
            "DROP TABLE param_set;\n"
            "ALTER TABLE param_set_legacy RENAME TO param_set;\n"
            "COMMIT;\n"
        )
        conn.executescript(legacy_ddl)  # 補回隨舊表一齊消失的觸發器
        conn.execute(
            "UPDATE schema_meta SET value = '6' WHERE key = 'schema_version'"
        )
        conn.commit()
    finally:
        conn.close()


# 驗收條件 2:週度參數集經唯一入口登記成功並跑得出一次回測
def test_a_weekly_param_set_registers_through_the_gateway_and_runs_a_backtest(karst):
    code, _ = karst(
        "factor", "register", "--name", FACTOR, "--scale", "cardinal",
        "--formula", PROCEDURE.formula,
        "--input-data-version", PROCEDURE.input_data_version,
    )
    assert code == 0

    # 週度經同一道門寫得入庫身——以前 sqlite 那條 CHECK 會在這一句當場擋住。
    code, output = karst(
        "strategy", "register", "--name", STRATEGY, "--type", "technical",
        "--factor", FACTOR, "--param-set", PARAM_SET, "--cadence", "weekly",
        "--set", "top_n=2", "--set", "direction=high",
    )
    assert code == 0, output

    with Gateway.open(karst.path) as gateway:
        store = gateway.store
        param_set = store.get_param_set(STRATEGY, PARAM_SET)
        assert param_set.rebalance_cadence == "weekly"
        assert param_set.values == {"top_n": "2", "direction": "high"}

        entity_ids = [
            store.register_entity(
                kind="company", display_name=f"Toy {index} Inc.", cik=str(940000 + index)
            )
            for index in range(4)
        ]
        gateway.write_factor_values(FACTOR, _toy_rows(entity_ids))

        # 跑得出一次回測:節奏取自庫身那個參數集,不是測試自己寫死一句 "weekly"
        result = run_ranking_rebalance(
            store=store,
            panel=_toy_panel(entity_ids),
            factor_name=FACTOR,
            cadence=param_set.rebalance_cadence,
            top_n=int(param_set.values["top_n"]),
            direction=param_set.values["direction"],
        )

    assert list(result.equity_curve.index) == list(DATES)
    assert result.equity_curve.notna().all()
    assert np.isfinite(result.total_return)
    assert len(result.orders) > 0
    # 90 根 K 線按週度排得出十幾次換倉,遠多過同一段日子的月度
    assert len(result.rebalances) > 12
    assert all(len(rebalance.selected) == 2 for rebalance in result.rebalances)

    code, output = karst("verify")
    assert code == 0
    # KARST-087 起報告分三類講(定義、因子批次、快照)
    assert "三類全部清白" in output


# 驗收條件 2(續):舊庫重開即自動搬表,param_set_id 與內容逐個原封不變
def test_an_old_database_migrates_in_place_without_touching_a_single_row(karst):
    code, _ = karst(
        "factor", "register", "--name", FACTOR, "--scale", "cardinal",
        "--formula", PROCEDURE.formula,
        "--input-data-version", PROCEDURE.input_data_version,
    )
    assert code == 0
    for index, cadence in enumerate(("daily", "monthly", "quarterly")):
        code, output = karst(
            "strategy", "register", "--name", f"{STRATEGY}-{cadence}",
            "--type", "technical", "--factor", FACTOR,
            "--param-set", PARAM_SET, "--cadence", cadence,
            "--set", f"top_n={index + 1}", "--set", "direction=high",
        )
        assert code == 0, output

    _downgrade_to_the_old_cadence_check(karst.path)

    conn = sqlite3.connect(f"file:{karst.path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    assert schema._cadences_in_db(conn) == frozenset({"daily", "monthly", "quarterly"})
    conn.close()
    before = _param_set_rows(karst.path)
    assert len(before) == 3

    # 重開一次就搬完:param_set_id 與內容逐個原封不變
    with DefinitionStore.open(karst.path) as store:
        assert _param_set_rows(karst.path) == before
        head = store.get_param_set(f"{STRATEGY}-daily", PARAM_SET)
        assert head.rebalance_cadence == "daily"
        assert head.values == {"top_n": "1", "direction": "high"}

    opened = sqlite3.connect(karst.path)
    opened.row_factory = sqlite3.Row
    try:
        # 收得住週度了,觸發器仍在,外鍵仍然對得上
        assert "weekly" in schema._cadences_in_db(opened)
        assert _triggers(opened) == [
            "trg_param_set_no_delete",
            "trg_param_set_no_update",
            "trg_param_value_no_delete",
            "trg_param_value_no_update",
        ]
        assert opened.execute("PRAGMA foreign_key_check").fetchall() == []
        with pytest.raises(sqlite3.IntegrityError):
            opened.execute("UPDATE param_set SET name = 'x' WHERE param_set_id = 1")
        stamp = opened.execute(
            "SELECT value FROM schema_meta WHERE key = 'schema_version'"
        ).fetchone()[0]
        assert stamp == str(schema.SCHEMA_VERSION)
    finally:
        opened.close()

    # 簽章仍然有效:取值一個字沒改,內容雜湊不變
    code, output = karst("verify")
    assert code == 0
    # KARST-087 起報告分三類講(定義、因子批次、快照)
    assert "三類全部清白" in output

    # 週度自此寫得入這個舊庫
    code, output = karst(
        "params", "add", "--strategy", f"{STRATEGY}-daily", "--name", "週度",
        "--cadence", "weekly", "--set", "top_n=2", "--set", "direction=high",
    )
    assert code == 0, output

    # 重開不重跑:第二次開庫已經無嘢好搬
    with DefinitionStore.open(karst.path) as store:
        assert schema._migrate_param_set_cadence(store.connection) is False
