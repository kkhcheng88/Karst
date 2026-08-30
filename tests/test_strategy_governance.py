"""KARST-116 驗收:策略合約兩格必填(D-058)——屬三層哪一層、離場治理屬哪一型。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況(用戶明令實作期驗證從簡)。
一律經命令列那道門(``karst.gateway.cli.main``)——與人手用的是同一條路。

要證的那三件:
  一、**拒收**:未填 layer 或 exit_governance,唯一入口當場拒收,錯誤訊息指明依據
      (D-054/D-056)與可選值;庫內一個字都寫不入;
  二、**成功**:兩格填齊即登記得到,宣告落庫、入治理清單、有簽章,``verify`` 清白;
  三、**補填**:兩格必填之前登記的策略補得回,追加式(舊宣告一字不變),同樣留簽章。

另加一件防漂移閘:庫內宣告與合約宣告對不上時,執行台當場拒收,不靜靜覆蓋。

跑法:``PYTHONUTF8=1 python -m pytest tests/test_strategy_governance.py -q``
"""

from __future__ import annotations

import io
import sqlite3

import pytest

from karst.errors import ContractViolation
from karst.gateway.cli import main
from karst.gateway.ledger import (
    CATEGORY_DEFINITION,
    GOVERNED_TABLES,
    TABLE_CATEGORIES,
)
from karst.store import (
    CONTINUATION_EXIT,
    EXIT_GOVERNANCES,
    LAYERS,
    RULE_BASED_EXIT,
    SECTOR_LAYER,
    STOCK_LAYER,
    DefinitionStore,
)

MOMENTUM = "動量·12-1 月"
FORMULA = "close[-21] / close[-252] - 1"
INPUT_VERSION = "2026-08-30-a1b2c3d4e5f6"
STRATEGY = "板塊輪動"
PARAM_SET = "示例-KARST-116"


@pytest.fixture()
def karst(tmp_path, monkeypatch):
    """回傳一個「跑一句 karst 命令」的函數:(回傳碼, 螢幕輸出)。"""
    monkeypatch.delenv("KARST_GATEWAY_KEY", raising=False)
    monkeypatch.setenv("KARST_WRITER", "KARST-116-test")
    path = str(tmp_path / "karst.sqlite")

    def run(*argv: str) -> tuple[int, str]:
        buffer = io.StringIO()
        code = main(["--store", path, *argv], out=buffer)
        return code, buffer.getvalue()

    run.path = path  # type: ignore[attr-defined]
    return run


@pytest.fixture()
def factor(karst):
    assert karst(
        "factor", "register", "--name", MOMENTUM, "--scale", "cardinal",
        "--formula", FORMULA, "--input-data-version", INPUT_VERSION,
    )[0] == 0
    return karst


def _register(karst, *extra: str) -> tuple[int, str]:
    return karst(
        "strategy", "register", "--name", STRATEGY, "--type", "multifactor",
        "--factor", MOMENTUM, "--param-set", PARAM_SET, "--cadence", "monthly",
        "--set", "top_n=4", *extra,
    )


# ---- 一、未答即拒收,而且講得出依據與可選值 ------------------------------


def test_registering_without_a_layer_is_refused_with_the_reason_and_the_choices(factor):
    code, text = _register(factor, "--exit-governance", RULE_BASED_EXIT)
    assert code == 1
    # 依據:講得出是哪一條決策要求的
    assert "D-054" in text
    # 可選值:三個都印出來,不用人去翻碼
    for value in LAYERS:
        assert value in text
    # 庫內一個字都寫不入——拒收不是「寫了再說」
    with pytest.raises(Exception):
        with DefinitionStore.open(factor.path) as store:
            store.get_strategy_version(STRATEGY)


def test_registering_without_an_exit_governance_is_refused_with_the_reason(factor):
    code, text = _register(factor, "--layer", SECTOR_LAYER)
    assert code == 1
    assert "D-056" in text
    for value in EXIT_GOVERNANCES:
        assert value in text


def test_a_layer_outside_the_three_is_refused(factor):
    code, text = _register(
        factor, "--layer", "crypto", "--exit-governance", RULE_BASED_EXIT
    )
    assert code == 1
    assert "'crypto'" in text
    assert "D-054" in text


# ---- 二、兩格填齊即登記得到,落庫、入治理清單、有簽章、verify 清白 --------


def test_the_governance_table_is_governed_and_classified():
    """治理清單與報告分類兩份都要有這張表;只加一邊,``category_of`` 會當場撞板。"""
    assert GOVERNED_TABLES["strategy_governance"] == ("strategy_id", "seq_no")
    assert TABLE_CATEGORIES["strategy_governance"] == CATEGORY_DEFINITION
    assert set(TABLE_CATEGORIES) == set(GOVERNED_TABLES)


def test_registering_with_both_answers_lands_signed_and_verifies_clean(factor):
    code, text = _register(
        factor, "--layer", SECTOR_LAYER, "--exit-governance", RULE_BASED_EXIT
    )
    assert code == 0
    assert "板塊層" in text and "規則型" in text

    with DefinitionStore.open(factor.path) as store:
        version = store.get_strategy_version(STRATEGY)
        governance = store.strategy_governance(version.strategy_id)
    assert governance is not None
    assert (governance.layer, governance.exit_governance) == (SECTOR_LAYER, RULE_BASED_EXIT)
    assert governance.seq_no == 1
    assert governance.basis  # 依據一句不可留空

    # 經唯一入口寫入 = 那一列有簽章
    with sqlite3.connect(factor.path) as conn:
        signed = {
            row[0] for row in conn.execute(
                "SELECT row_key FROM gateway_write WHERE table_name = 'strategy_governance'"
            )
        }
    assert signed == {f"{governance.strategy_id}|1"}

    assert factor("verify")[0] == 0


# ---- 三、補填:兩格必填之前登記的策略,經唯一入口補得回 ------------------


def test_a_strategy_registered_before_the_gate_can_be_backfilled_through_the_gateway(factor):
    """補填走的是同一道門:宣告落庫、有簽章、查得回。

    生產庫那三條策略正是這個局面——它們在兩格必填之前登記,而登記按設計不可刪不可改,
    所以補填只有一條路:加一筆宣告。這裡照樣造出那個局面(策略那兩列直接寫入,不經
    宣告那一步),再證補得回。
    """
    with sqlite3.connect(factor.path) as conn:
        conn.execute(
            "INSERT INTO strategy (name, strategy_type, created_at) VALUES (?, ?, ?)",
            (STRATEGY, "multifactor", "2026-08-27T16:27:00+00:00"),
        )
        strategy_id = int(conn.execute(
            "SELECT strategy_id FROM strategy WHERE name = ?", (STRATEGY,)
        ).fetchone()[0])
        conn.execute(
            "INSERT INTO strategy_version (strategy_id, version_no, parent_version_id,"
            " description, created_at) VALUES (?, 1, NULL, NULL, ?)",
            (strategy_id, "2026-08-27T16:27:00+00:00"),
        )

    with DefinitionStore.open(factor.path) as store:
        version = store.get_strategy_version(STRATEGY)
        assert store.strategy_governance(version.strategy_id) is None

    code, text = factor(
        "strategy", "declare-governance", "--name", STRATEGY,
        "--layer", STOCK_LAYER, "--exit-governance", CONTINUATION_EXIT,
        "--basis", "D-058:KARST-116 補填,照實際形態判",
    )
    assert code == 0
    assert "個股層" in text and "延續型注" in text

    with DefinitionStore.open(factor.path) as store:
        governance = store.strategy_governance_by_name(STRATEGY)
    assert governance is not None
    assert (governance.layer, governance.exit_governance) == (STOCK_LAYER, CONTINUATION_EXIT)
    assert "KARST-116" in governance.basis


def test_changing_a_declaration_appends_and_leaves_the_old_one_word_for_word(factor):
    assert _register(
        factor, "--layer", SECTOR_LAYER, "--exit-governance", RULE_BASED_EXIT
    )[0] == 0
    assert factor(
        "strategy", "declare-governance", "--name", STRATEGY,
        "--layer", STOCK_LAYER, "--exit-governance", CONTINUATION_EXIT,
        "--basis", "改編制:改押板塊內強者",
    )[0] == 0

    with DefinitionStore.open(factor.path) as store:
        version = store.get_strategy_version(STRATEGY)
        history = store.strategy_governance_history(version.strategy_id)
    assert [(one.seq_no, one.layer, one.exit_governance) for one in history] == [
        (1, SECTOR_LAYER, RULE_BASED_EXIT),
        (2, STOCK_LAYER, CONTINUATION_EXIT),
    ]
    assert factor("verify")[0] == 0


def test_declaring_the_same_thing_twice_does_not_add_a_row(factor):
    assert _register(
        factor, "--layer", SECTOR_LAYER, "--exit-governance", RULE_BASED_EXIT
    )[0] == 0
    with DefinitionStore.open(factor.path) as store:
        first = store.strategy_governance_by_name(STRATEGY)
        assert first is not None
        again = store.declare_strategy_governance(
            STRATEGY,
            layer=SECTOR_LAYER,
            exit_governance=RULE_BASED_EXIT,
            basis=first.basis,
        )
        assert again.seq_no == 1
        assert len(store.strategy_governance_history(first.strategy_id)) == 1


def test_a_declaration_without_a_basis_is_refused(factor):
    assert _register(
        factor, "--layer", SECTOR_LAYER, "--exit-governance", RULE_BASED_EXIT
    )[0] == 0
    with DefinitionStore.open(factor.path) as store:
        with pytest.raises(ContractViolation, match="依據"):
            store.declare_strategy_governance(
                STRATEGY, layer=STOCK_LAYER, exit_governance=CONTINUATION_EXIT, basis="  "
            )


# ---- 四、防漂移閘:庫內宣告與合約宣告對不上,當場拒收 ---------------------


def test_a_contract_that_drifts_from_the_recorded_declaration_is_refused(factor):
    """合約改了層別而庫內宣告沒有改 = 漂移。哪一邊才對不是執行台判得出的事。"""
    from karst.executor.executor import check_governance
    from karst.gateway import Gateway

    assert _register(
        factor, "--layer", SECTOR_LAYER, "--exit-governance", RULE_BASED_EXIT
    )[0] == 0
    with Gateway.open(factor.path) as gateway:
        head = gateway.store.get_strategy_version(STRATEGY)
        with pytest.raises(ContractViolation, match="對不上"):
            check_governance(
                gateway, head, layer=STOCK_LAYER, exit_governance=CONTINUATION_EXIT
            )
