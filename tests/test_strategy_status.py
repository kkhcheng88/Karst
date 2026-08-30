"""KARST-117 驗收:策略登記狀態(現役/封存)——D-058 第 1 條,承 D-055。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況(用戶明令實作期驗證從簡)。
一律經命令列那道門(``karst.gateway.cli.main``)——與人手用的是同一條路。

要證的那三件:
  一、**狀態變更留痕**:封存經唯一入口寫入、蓋簽章、留得低依據(邊條決策)與時戳;
      追加式(舊紀錄一字不變);而**不可刪的登記一列未動**——策略、參數集照查得到;
  二、**預設過濾**:策略清單預設只列現役,封存了的線不出現在「現在有哪幾條線」的答案裡;
  三、**旗標全列**:加 ``--include-archived`` 即連封存一齊列。

跑法:``PYTHONUTF8=1 python -m pytest tests/test_strategy_status.py -q``
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
)
from karst.store import (
    ACTIVE_STATUS,
    ARCHIVED_STATUS,
    RULE_BASED_EXIT,
    SECTOR_LAYER,
    STOCK_LAYER,
    DefinitionStore,
)

MOMENTUM = "動量·12-1 月"
FORMULA = "close[-21] / close[-252] - 1"
INPUT_VERSION = "2026-08-30-a1b2c3d4e5f6"
KEEPER = "板塊輪動"
DOOMED = "因子混合(示例)"
PARAM_SET = "示例-KARST-117"
BASIS = "D-055:因子混合線降級封存"


@pytest.fixture()
def karst(tmp_path, monkeypatch):
    """回傳一個「跑一句 karst 命令」的函數:(回傳碼, 螢幕輸出)。"""
    monkeypatch.delenv("KARST_GATEWAY_KEY", raising=False)
    monkeypatch.setenv("KARST_WRITER", "KARST-117-test")
    path = str(tmp_path / "karst.sqlite")

    def run(*argv: str) -> tuple[int, str]:
        buffer = io.StringIO()
        code = main(["--store", path, *argv], out=buffer)
        return code, buffer.getvalue()

    run.path = path  # type: ignore[attr-defined]
    return run


def _register(karst, name: str, layer: str) -> None:
    assert karst(
        "strategy", "register", "--name", name, "--type", "multifactor",
        "--factor", MOMENTUM, "--param-set", PARAM_SET, "--cadence", "monthly",
        "--set", "top_n=4", "--layer", layer,
        "--exit-governance", RULE_BASED_EXIT,
    )[0] == 0


@pytest.fixture()
def two_strategies(karst):
    """一個現役、一個等住被封存的庫。"""
    assert karst(
        "factor", "register", "--name", MOMENTUM, "--scale", "cardinal",
        "--formula", FORMULA, "--input-data-version", INPUT_VERSION,
    )[0] == 0
    _register(karst, KEEPER, SECTOR_LAYER)
    _register(karst, DOOMED, STOCK_LAYER)
    return karst


# ---- 一、狀態變更留痕:經唯一入口、蓋簽章、可追溯依據 ---------------------


def test_the_status_table_is_governed_and_classified():
    """治理清單與報告分類兩份都要有這張表;只加一邊,``category_of`` 會當場撞板。"""
    assert GOVERNED_TABLES["strategy_status"] == ("strategy_id", "seq_no")
    assert TABLE_CATEGORIES["strategy_status"] == CATEGORY_DEFINITION
    assert set(TABLE_CATEGORIES) == set(GOVERNED_TABLES)


def test_archiving_lands_signed_with_its_basis_and_verifies_clean(two_strategies):
    """封存 = 經唯一入口加一列:有簽章、有依據、有時戳,``verify`` 照舊清白。"""
    code, text = two_strategies(
        "strategy", "set-status", "--name", DOOMED,
        "--status", ARCHIVED_STATUS, "--basis", BASIS,
    )
    assert code == 0
    assert "封存" in text and "D-055" in text

    with DefinitionStore.open(two_strategies.path) as store:
        record = store.strategy_status_by_name(DOOMED)
        assert record is not None
        assert record.status == ARCHIVED_STATUS
        assert record.seq_no == 1
        assert record.basis == BASIS          # 依哪條決策封存,查得到
        assert record.recorded_at             # 幾時封存,查得到
        assert store.is_strategy_archived(record.strategy_id)
        # 未記過狀態的那條照舊算現役——不必補一列 active 才算數
        keeper = store.get_strategy_version(KEEPER)
        assert store.strategy_status(keeper.strategy_id) is None
        assert not store.is_strategy_archived(keeper.strategy_id)
        archived_id = record.strategy_id

    # 經唯一入口寫入 = 那一列有簽章
    with sqlite3.connect(two_strategies.path) as conn:
        signed = {
            row[0] for row in conn.execute(
                "SELECT row_key FROM gateway_write WHERE table_name = 'strategy_status'"
            )
        }
    assert signed == {f"{archived_id}|1"}

    assert two_strategies("verify")[0] == 0


def test_archiving_leaves_every_existing_registration_untouched(two_strategies):
    """定義庫不可刪:封存之後,那條線的登記與參數集一列未動、照查得到(D-058 第 1 條)。"""
    with DefinitionStore.open(two_strategies.path) as store:
        before_version = store.get_strategy_version(DOOMED)
        before_params = [(p.name, p.version_no) for p in store.list_param_sets(DOOMED)]
    with sqlite3.connect(two_strategies.path) as conn:
        before_rows = conn.execute(
            "SELECT table_name, row_key, content_digest, signature FROM gateway_write"
            " ORDER BY write_id"
        ).fetchall()

    assert two_strategies(
        "strategy", "set-status", "--name", DOOMED,
        "--status", ARCHIVED_STATUS, "--basis", BASIS,
    )[0] == 0

    with DefinitionStore.open(two_strategies.path) as store:
        after_version = store.get_strategy_version(DOOMED)
        after_params = [(p.name, p.version_no) for p in store.list_param_sets(DOOMED)]
    # 指名查一條封存了的策略,照樣查得到它的登記與參數集
    assert after_version == before_version
    assert after_params == before_params
    assert after_params  # 真的有嘢查,不是兩邊都空

    with sqlite3.connect(two_strategies.path) as conn:
        after_rows = conn.execute(
            "SELECT table_name, row_key, content_digest, signature FROM gateway_write"
            " ORDER BY write_id"
        ).fetchall()
    # 既有簽章零消失零改動,新增的只有狀態那一列
    assert after_rows[: len(before_rows)] == before_rows
    assert [row[0] for row in after_rows[len(before_rows):]] == ["strategy_status"]


def test_changing_the_status_appends_and_leaves_the_old_record_word_for_word(two_strategies):
    """改狀態 = 加一筆;歷次改過什麼、幾時、依據是什麼,全部查得回。"""
    assert two_strategies(
        "strategy", "set-status", "--name", DOOMED,
        "--status", ARCHIVED_STATUS, "--basis", BASIS,
    )[0] == 0
    assert two_strategies(
        "strategy", "set-status", "--name", DOOMED,
        "--status", ACTIVE_STATUS, "--basis", "日後復役:重新納入重心",
    )[0] == 0

    with DefinitionStore.open(two_strategies.path) as store:
        head = store.get_strategy_version(DOOMED)
        history = store.strategy_status_history(head.strategy_id)
        current = store.strategy_status(head.strategy_id)

    assert [(r.seq_no, r.status) for r in history] == [
        (1, ARCHIVED_STATUS), (2, ACTIVE_STATUS),
    ]
    assert history[0].basis == BASIS  # 舊紀錄一字不變
    assert current is not None and current.seq_no == 2
    # 復役之後又再算現役
    assert not current.is_archived


def test_recording_the_same_status_twice_does_not_add_a_row(two_strategies):
    """重覆記同一件事即當同一件事,原封不動回上一筆,不會白加一列。"""
    for _ in range(2):
        assert two_strategies(
            "strategy", "set-status", "--name", DOOMED,
            "--status", ARCHIVED_STATUS, "--basis", BASIS,
        )[0] == 0
    with DefinitionStore.open(two_strategies.path) as store:
        head = store.get_strategy_version(DOOMED)
        assert len(store.strategy_status_history(head.strategy_id)) == 1


def test_a_status_without_a_basis_is_refused(two_strategies):
    """無理由的封存等於沒有封存:依據一句不准留空。"""
    code, text = two_strategies(
        "strategy", "set-status", "--name", DOOMED,
        "--status", ARCHIVED_STATUS, "--basis", "   ",
    )
    assert code == 1
    assert "依據" in text
    with DefinitionStore.open(two_strategies.path) as store:
        head = store.get_strategy_version(DOOMED)
        assert store.strategy_status(head.strategy_id) is None


def test_a_status_outside_the_two_is_refused_with_the_choices(two_strategies):
    code, text = two_strategies(
        "strategy", "set-status", "--name", DOOMED,
        "--status", "deleted", "--basis", BASIS,
    )
    assert code == 1
    assert "'deleted'" in text
    assert ACTIVE_STATUS in text and ARCHIVED_STATUS in text
    assert "D-058" in text


def test_the_status_row_cannot_be_updated_or_deleted(two_strategies):
    """追加式不是靠自律,是庫身兩道閘擋住(與治理宣告、除名同制)。"""
    assert two_strategies(
        "strategy", "set-status", "--name", DOOMED,
        "--status", ARCHIVED_STATUS, "--basis", BASIS,
    )[0] == 0
    with sqlite3.connect(two_strategies.path) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE strategy_status SET status = 'active'")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM strategy_status")


# ---- 二、預設過濾:清單預設只列現役 --------------------------------------


def test_the_strategy_list_defaults_to_active_only(two_strategies):
    with DefinitionStore.open(two_strategies.path) as store:
        assert store.list_strategy_names() == [KEEPER, DOOMED]

    assert two_strategies(
        "strategy", "set-status", "--name", DOOMED,
        "--status", ARCHIVED_STATUS, "--basis", BASIS,
    )[0] == 0

    with DefinitionStore.open(two_strategies.path) as store:
        assert store.list_strategy_names() == [KEEPER]

    code, text = two_strategies("strategy", "list")
    assert code == 0
    assert KEEPER in text
    assert DOOMED not in text
    assert "只列現役" in text


def test_risk_refs_also_defaults_to_active_only(two_strategies):
    """CLI 另一處列策略的地方(risk refs)同一條規矩。"""
    assert two_strategies("risk", "register")[0] == 0
    assert two_strategies(
        "strategy", "set-status", "--name", DOOMED,
        "--status", ARCHIVED_STATUS, "--basis", BASIS,
    )[0] == 0

    code, text = two_strategies("risk", "refs")
    assert code == 0
    assert KEEPER in text
    assert DOOMED not in text

    # 指名查一條封存了的策略,照樣查得到——封存不是刪除
    code, text = two_strategies("risk", "refs", "--strategy", DOOMED)
    assert code == 0
    assert DOOMED in text


# ---- 三、旗標全列:加 --include-archived 即連封存一齊列 -------------------


def test_the_flag_lists_the_archived_ones_too(two_strategies):
    assert two_strategies(
        "strategy", "set-status", "--name", DOOMED,
        "--status", ARCHIVED_STATUS, "--basis", BASIS,
    )[0] == 0

    with DefinitionStore.open(two_strategies.path) as store:
        assert store.list_strategy_names(include_archived=True) == [KEEPER, DOOMED]

    code, text = two_strategies("strategy", "list", "--include-archived")
    assert code == 0
    assert KEEPER in text and DOOMED in text
    # 全列時看得出邊條係封存,同埋依邊條決策封存
    assert "封存" in text and "D-055" in text

    code, text = two_strategies("risk", "refs", "--include-archived")
    assert code == 0
    assert KEEPER in text and DOOMED in text


def test_show_prints_the_status_for_active_and_archived_alike(two_strategies):
    """``strategy show`` 兩邊都講得出:未記過即現役,封存的印埋依據。"""
    code, text = two_strategies("strategy", "show", "--name", KEEPER)
    assert code == 0
    assert "現役" in text

    assert two_strategies(
        "strategy", "set-status", "--name", DOOMED,
        "--status", ARCHIVED_STATUS, "--basis", BASIS,
    )[0] == 0
    code, text = two_strategies("strategy", "show", "--name", DOOMED)
    assert code == 0
    assert "封存" in text and "D-055" in text
