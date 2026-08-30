"""KARST-094 驗收:參數集對齊標記(D-038)落庫,經唯一入口簽章的旁表。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況。
一律經命令列那道門(``karst.gateway.cli.main``)——與人手用的是同一條路。

要證的那幾件:
  一、標記落庫、入治理清單、經唯一入口有簽章,``karst verify`` 核得到;
  二、追加式:不可改、不可刪,改標記是加一筆新申報而舊申報一字不變;
  三、繞過唯一入口直接塞一列標記,verify 一掃就見到,而且歸「定義」類;
  四、執行台登記參數集時把申報寫入此表;
  五、定義庫與取數層讀得回;
  六、**標記不進運行編號雜湊**:寫幾多列,同一組身份算出來的運行編號一位不變。

跑法:``PYTHONUTF8=1 python -m pytest tests/test_param_alignment.py -q``
"""

from __future__ import annotations

import io
import sqlite3

import pytest

from karst.gateway.cli import main
from karst.gateway.ledger import (
    CATEGORY_DEFINITION,
    GOVERNED_TABLES,
    TABLE_CATEGORIES,
    UNSIGNED,
)
from karst.store import ALIGNED, SAMPLE, DefinitionStore

MOMENTUM = "動量·12-1 月"
FORMULA = "close[-21] / close[-252] - 1"
INPUT_VERSION = "2026-08-30-a1b2c3d4e5f6"
STRATEGY = "趨勢波段"
PARAM_SET = "示例-KARST-094"


@pytest.fixture()
def karst(tmp_path, monkeypatch):
    """回傳一個「跑一句 karst 命令」的函數:(回傳碼, 螢幕輸出)。"""
    monkeypatch.delenv("KARST_GATEWAY_KEY", raising=False)
    monkeypatch.setenv("KARST_WRITER", "KARST-094-test")
    path = str(tmp_path / "karst.sqlite")

    def run(*argv: str) -> tuple[int, str]:
        buffer = io.StringIO()
        code = main(["--store", path, *argv], out=buffer)
        return code, buffer.getvalue()

    run.path = path  # type: ignore[attr-defined]
    return run


@pytest.fixture()
def strategy(karst):
    """一套經唯一入口登記好的策略,連一個參數集。"""
    assert karst(
        "factor", "register", "--name", MOMENTUM, "--scale", "cardinal",
        "--formula", FORMULA, "--input-data-version", INPUT_VERSION,
    )[0] == 0
    assert karst(
        "strategy", "register", "--name", STRATEGY, "--type", "technical",
        "--factor", MOMENTUM, "--param-set", PARAM_SET, "--cadence", "monthly",
        "--set", "breakout_window=59", "--set", "risk.per_trade_risk=0.02",
    )[0] == 0
    return karst


def _param_set_id(path: str) -> int:
    with DefinitionStore.open(path) as store:
        return store.get_param_set(STRATEGY, PARAM_SET).param_set_id


# ---- 一、落庫、入治理清單、有簽章、verify 清白 --------------------------


def test_alignment_table_is_governed_and_classified():
    """治理清單與報告分類兩份都要有這張表;只加一邊,category_of 會當場撞板。"""
    assert GOVERNED_TABLES["param_set_alignment"] == ("param_set_id", "seq_no")
    assert TABLE_CATEGORIES["param_set_alignment"] == CATEGORY_DEFINITION
    assert set(TABLE_CATEGORIES) == set(GOVERNED_TABLES)


def test_marking_through_the_gateway_is_signed_and_verifies_clean(strategy):
    code, text = strategy(
        "params", "mark-alignment", "--strategy", STRATEGY, "--name", PARAM_SET,
        "--mark", SAMPLE, "--basis", "D-038:未經用戶對齊",
    )
    assert code == 0
    assert "示例" in text
    assert "D-038:未經用戶對齊" in text

    with sqlite3.connect(strategy.path) as conn:
        conn.row_factory = sqlite3.Row
        signed = {
            (row["table_name"], row["row_key"]): row["writer"]
            for row in conn.execute("SELECT table_name, row_key, writer FROM gateway_write")
        }
    param_set_id = _param_set_id(strategy.path)
    assert signed[("param_set_alignment", f"{param_set_id}|1")] == "KARST-094-test"

    code, text = strategy("verify")
    assert code == 0
    assert "定義:清白" in text


def test_aligned_mark_needs_a_date_and_sample_must_not_have_one(strategy):
    """已對齊要講得出哪一日對的;示例從來沒有對齊過,不可以有日期。"""
    code, _ = strategy(
        "params", "mark-alignment", "--strategy", STRATEGY, "--name", PARAM_SET,
        "--mark", ALIGNED, "--basis", "2026-08-30 與用戶逐格對過",
    )
    assert code != 0

    code, _ = strategy(
        "params", "mark-alignment", "--strategy", STRATEGY, "--name", PARAM_SET,
        "--mark", SAMPLE, "--basis", "通鏈用取值", "--aligned-on", "2026-08-30",
    )
    assert code != 0


# ---- 二、追加式:不可改、不可刪,改標記是加一筆 -------------------------


def test_marks_cannot_be_changed_or_deleted(strategy):
    """對齊標記只加不改不刪:一次申報是一件已經發生的事。"""
    assert strategy(
        "params", "mark-alignment", "--strategy", STRATEGY, "--name", PARAM_SET,
        "--mark", SAMPLE, "--basis", "D-038:未經用戶對齊",
    )[0] == 0

    with DefinitionStore.open(strategy.path) as store:
        with pytest.raises(sqlite3.IntegrityError):
            with store.connection:
                store.connection.execute(
                    "UPDATE param_set_alignment SET mark = ?", (ALIGNED,)
                )
        with pytest.raises(sqlite3.IntegrityError):
            with store.connection:
                store.connection.execute("DELETE FROM param_set_alignment")


def test_changing_the_mark_adds_a_row_and_leaves_the_old_one_alone(strategy):
    """由示例改為已對齊 = 加一筆新申報;舊申報一字不變,查得回當日的講法。"""
    assert strategy(
        "params", "mark-alignment", "--strategy", STRATEGY, "--name", PARAM_SET,
        "--mark", SAMPLE, "--basis", "D-038:未經用戶對齊",
    )[0] == 0
    assert strategy(
        "params", "mark-alignment", "--strategy", STRATEGY, "--name", PARAM_SET,
        "--mark", ALIGNED, "--basis", "2026-08-30 與用戶逐格對過",
        "--aligned-on", "2026-08-30",
    )[0] == 0

    param_set_id = _param_set_id(strategy.path)
    with DefinitionStore.open(strategy.path) as store:
        history = store.param_set_alignment_history(param_set_id)
        current = store.param_set_alignment(param_set_id)

    assert [one.seq_no for one in history] == [1, 2]
    assert history[0].mark == SAMPLE
    assert history[0].basis == "D-038:未經用戶對齊"
    assert history[0].aligned_on is None
    assert current.mark == ALIGNED
    assert current.aligned_on == "2026-08-30"
    assert current.label == "已對齊(2026-08-30)"
    assert current.is_aligned

    # 兩筆都要有自己的簽章,verify 照樣清白。
    assert strategy("verify")[0] == 0


def test_repeating_the_same_declaration_does_not_add_a_row(strategy):
    """重覆申報同一件事回上一筆:執行台每次登記都會走這裡,不應該每跑一次多一列。"""
    for _ in range(3):
        assert strategy(
            "params", "mark-alignment", "--strategy", STRATEGY, "--name", PARAM_SET,
            "--mark", SAMPLE, "--basis", "D-038:未經用戶對齊",
        )[0] == 0
    param_set_id = _param_set_id(strategy.path)
    with DefinitionStore.open(strategy.path) as store:
        assert len(store.param_set_alignment_history(param_set_id)) == 1


# ---- 三、繞過唯一入口即被 verify 揪住 -----------------------------------


def test_a_mark_written_behind_the_gateway_is_caught_by_verify(strategy):
    """有人繞過那道門把示例取值標成已對齊送上門面,正是 D-038 要防的那件事。"""
    param_set_id = _param_set_id(strategy.path)
    with DefinitionStore.open(strategy.path) as store:
        with store.connection:
            store.connection.execute(
                "INSERT INTO param_set_alignment (param_set_id, seq_no, mark,"
                " aligned_on, basis, recorded_at) VALUES (?, ?, ?, ?, ?, ?)",
                (param_set_id, 1, ALIGNED, "2026-08-30", "我說對齊了就對齊了",
                 "2026-08-30T00:00:00"),
            )

    code, text = strategy("verify")
    assert code == 3
    assert UNSIGNED in text
    assert "param_set_alignment" in text
    assert "定義:揪到" in text


# ---- 六、標記不進運行編號雜湊 -------------------------------------------


def test_marks_touch_neither_the_param_set_nor_its_signature(strategy):
    """寫幾多列標記,參數集那幾列與它們的簽章一位不變(KARST-026、A-014)。

    這一條就是本票整個設計的理由。運行編號由參數集內容雜湊而來,而寫入者簽章蓋的
    正是同一份內容:標記若果做成參數集一格取值,13 條正式運行會全部改號;做成
    ``param_set`` 一條新欄,8326 列既有簽章會一次過作廢。走旁表,兩樣都不碰——
    這裡逐格對的就是那兩樣東西。

    (真庫那邊:`backtest_run` 裡 origin='formal' 的 13 列——當中 12 條算數、1 條已由
    KARST-093 除名——逐格不變,由 experiments/2026-08-30-param-alignment/verify_094.py
    對住倉裡那個真庫核,連 51832 列既有簽章一齊全表逐列比。)
    """
    def snapshot_of_param_tables() -> tuple[list, list]:
        with sqlite3.connect(strategy.path) as conn:
            rows = list(conn.execute(
                "SELECT * FROM param_set ORDER BY param_set_id"
            )) + list(conn.execute(
                "SELECT * FROM param_value ORDER BY param_set_id, param_key"
            ))
            signatures = list(conn.execute(
                "SELECT table_name, row_key, content_digest, signature, writer, written_at"
                " FROM gateway_write WHERE table_name IN ('param_set', 'param_value')"
                " ORDER BY table_name, row_key"
            ))
        return rows, signatures

    before = snapshot_of_param_tables()
    assert strategy(
        "params", "mark-alignment", "--strategy", STRATEGY, "--name", PARAM_SET,
        "--mark", SAMPLE, "--basis", "D-038:未經用戶對齊",
    )[0] == 0
    assert strategy(
        "params", "mark-alignment", "--strategy", STRATEGY, "--name", PARAM_SET,
        "--mark", ALIGNED, "--basis", "2026-08-30 與用戶逐格對過",
        "--aligned-on", "2026-08-30",
    )[0] == 0
    assert snapshot_of_param_tables() == before
    assert strategy("verify")[0] == 0


# ---- 五、讀得回:定義庫的介面與 params show ------------------------------


def test_params_show_tells_sample_from_aligned_and_from_never_declared(strategy):
    """畫面與紀錄要分得出三句話:未申報、示例、已對齊(某日)——D-038 的正題。"""
    code, text = strategy("params", "show", "--strategy", STRATEGY)
    assert code == 0
    assert "未申報" in text

    assert strategy(
        "params", "mark-alignment", "--strategy", STRATEGY, "--name", PARAM_SET,
        "--mark", SAMPLE, "--basis", "D-038:未經用戶對齊",
    )[0] == 0
    code, text = strategy("params", "show", "--strategy", STRATEGY)
    assert code == 0
    assert "示例" in text
    assert "未申報" not in text


def test_bulk_reader_skips_param_sets_that_never_declared(strategy):
    """一次過取一批:未申報的不在回傳內——未申報不等於示例。"""
    param_set_id = _param_set_id(strategy.path)
    with DefinitionStore.open(strategy.path) as store:
        assert store.param_set_alignments([param_set_id]) == {}
        assert store.param_set_alignment(param_set_id) is None

    assert strategy(
        "params", "mark-alignment", "--strategy", STRATEGY, "--name", PARAM_SET,
        "--mark", SAMPLE, "--basis", "D-038:未經用戶對齊",
    )[0] == 0
    with DefinitionStore.open(strategy.path) as store:
        marks = store.param_set_alignments([param_set_id, 999999])
        assert set(marks) == {param_set_id}
        assert marks[param_set_id].label == "示例"
