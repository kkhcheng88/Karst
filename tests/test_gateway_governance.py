"""KARST-035 驗收:現役設定與共用風控規則亦經唯一入口,並納入簽章核對。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況。
一律經命令列那道門(``karst.gateway.cli.main``)——與人手用的是同一條路。

跑法:``PYTHONUTF8=1 python -m pytest tests/test_gateway_governance.py -q``
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pytest

from karst.gateway.cli import main
from karst.gateway.ledger import GOVERNED_TABLES
from karst.gateway.service import Gateway
from karst.store import DefinitionStore

REPO_ROOT = Path(__file__).resolve().parents[1]

MOMENTUM = "動量·12-1 月"
FORMULA = "close[-21] / close[-252] - 1"
INPUT_VERSION = "2026-08-28-a1b2c3d4e5f6"
STRATEGY = "趨勢波段"
RULE_KEYS = ("per_trade_risk", "monthly_loss_cap", "reward_risk_floor")


@pytest.fixture()
def karst(tmp_path, monkeypatch):
    """回傳一個「跑一句 karst 命令」的函數:(回傳碼, 螢幕輸出)。"""
    monkeypatch.delenv("KARST_GATEWAY_KEY", raising=False)
    monkeypatch.setenv("KARST_WRITER", "KARST-035-gateway")
    path = str(tmp_path / "karst.sqlite")

    def run(*argv: str) -> tuple[int, str]:
        buffer = io.StringIO()
        code = main(["--store", path, *argv], out=buffer)
        return code, buffer.getvalue()

    run.path = path  # type: ignore[attr-defined]
    return run


@pytest.fixture()
def strategy(karst):
    """一套經唯一入口登記好的策略,連兩個參數集。"""
    assert karst(
        "factor", "register", "--name", MOMENTUM, "--scale", "cardinal",
        "--formula", FORMULA, "--input-data-version", INPUT_VERSION,
    )[0] == 0
    assert karst(
        "strategy", "register", "--name", STRATEGY, "--type", "technical",
        "--factor", MOMENTUM, "--param-set", "現役", "--cadence", "monthly",
        "--set", "breakout_window=50", "--set", "risk.per_trade_risk=0.06",
    )[0] == 0
    assert karst(
        "params", "add", "--strategy", STRATEGY, "--name", "保守",
        "--cadence", "monthly", "--set", "breakout_window=80",
        "--set", "risk.per_trade_risk=0.03",
    )[0] == 0
    return karst


# 驗收條件 1:karst params activate 指定現役設定並印出生效序號
def test_params_activate_pins_one_param_set_and_prints_the_sequence(strategy):
    code, output = strategy("params", "activate", "--strategy", STRATEGY,
                            "--name", "現役", "--note", "首次指定")
    assert code == 0
    assert "生效序號  第 1 次指定(seq_no=1)" in output
    assert "現役 第 1 版" in output

    # 換一個 = 加一筆新指定,序號遞增;舊指定一字不變
    code, output = strategy("params", "activate", "--strategy", STRATEGY, "--name", "保守")
    assert code == 0
    assert "生效序號  第 2 次指定(seq_no=2)" in output

    with DefinitionStore.open(strategy.path) as store:
        current = store.get_active_setup(STRATEGY)
        assert current.param_set_name == "保守"
        history = store.active_setup_history(STRATEGY)
        assert [(s.seq_no, s.param_set_name) for s in history] == [(1, "現役"), (2, "保守")]
        assert history[0].note == "首次指定"    # 舊指定原封不動


# 驗收條件 2:karst risk 一類子命令列得出三條規則與各策略的引用
def test_risk_commands_list_the_three_rules_and_each_strategy_reference(strategy):
    assert strategy("risk", "register")[0] == 0

    code, output = strategy("risk", "list")
    assert code == 0
    assert "共 3 條" in output
    for key in RULE_KEYS:
        assert key in output
    assert "risk.per_trade_risk" in output          # 取值住在參數集的哪個參數名

    assert strategy(
        "risk", "attach", "--strategy", STRATEGY,
        "--rule", "per_trade_risk", "--rule", "monthly_loss_cap",
    )[0] == 0

    code, output = strategy("risk", "refs")         # 留空即全部策略
    assert code == 0
    assert f"{STRATEGY} 第 1 版  引用 2 條" in output
    assert "單筆風險上限" in output

    with DefinitionStore.open(strategy.path) as store:
        assert [r.key for r in store.strategy_risk_rules(STRATEGY)] == [
            "per_trade_risk", "monthly_loss_cap",
        ]


# 驗收條件 3:三張表納入簽章治理;經入口寫入的列核對清白,繞過入口的列被揪出
def test_the_three_tables_are_under_signature_governance(strategy):
    assert {"active_setup", "risk_rule", "strategy_risk_ref"} <= set(GOVERNED_TABLES)

    assert strategy("params", "activate", "--strategy", STRATEGY, "--name", "現役")[0] == 0
    assert strategy("risk", "register")[0] == 0
    assert strategy("risk", "attach", "--strategy", STRATEGY, "--rule", "per_trade_risk")[0] == 0

    code, output = strategy("verify")
    assert code == 0                                 # 全部經同一道門,核對清白
    # KARST-087 起報告分三類講(定義、因子批次、快照),不再只得一句總帳
    assert "三類全部清白" in output
    assert "定義:清白" in output

    # 重覆跑一次:回同一批列、同一個簽章,不會多出第二份影像,亦不會撞簽章
    assert strategy("risk", "register")[0] == 0
    assert strategy("risk", "attach", "--strategy", STRATEGY, "--rule", "per_trade_risk")[0] == 0
    assert strategy("verify")[0] == 0

    # 有人繞過入口,用庫層 API 直接指定一個現役設定(沒有經入口,自然沒有簽章)
    with DefinitionStore.open(strategy.path) as store:
        store.set_active_setup(STRATEGY, "保守")

    code, output = strategy("verify")
    assert code == 3
    assert "未經唯一入口寫入" in output
    assert "active_setup" in output
    assert "不會被當作正常定義用落去" in output


# KARST-091:批次登記同樣納入簽章治理
#
# 一次掃描收工寫的那一列,載住門面左半那四個數(達標幾條/共幾條、中位年化、中位
# Sortino、中位最大回撤)與判讀口徑,而 D-042 用「達標運行的中位數年化最高」排批次
# 名次——即那一列直接決定用戶見到哪一批成績。繞過那道門塞一批看似達標的成績進去,
# 核對一掃就要見到。
def test_a_sweep_batch_written_behind_the_gateway_is_caught_by_verify(strategy, tmp_path):
    assert "sweep_batch" in GOVERNED_TABLES

    assert strategy("verify")[0] == 0                # 未有批次登記,全庫清白

    report = tmp_path / "掃描報告.md"
    report.write_text("# 一份假報告\n", encoding="utf-8")

    # 批次登記那一列要指得回一個真的數據快照,所以先**經唯一入口**登記一個
    # ——這一句是清白的,核對揪的是下面那一句。
    with Gateway.open(strategy.path) as gateway:
        snapshot_id = gateway.store.register_snapshot(
            source="test", taken_on="2026-08-28", content_hash="a1b2c3d4e5f60000",
        )

    # 有人繞過入口,用庫層 API 直接寫一列批次登記(沒有經入口,自然沒有簽章)
    with DefinitionStore.open(strategy.path) as store:
        store.register_sweep_batch(
            "測試-繞過入口的批次",
            strategy_name=STRATEGY,
            strategy_version_no=1,
            period_start="2021-01-04",
            period_end="2022-12-30",
            snapshot_id=snapshot_id,
            engine_name="synthetic",
            engine_version="0.1.0",
            cell_count=49,
            qualified_cells=9,
            failed_cells=0,
            error_cells=0,
            median_annual_return=0.12,
            median_sortino=1.5,
            median_max_drawdown=-0.2,
            objective="annual_return",
            min_trades=4,
            lonely_peak_margin=0.05,
            plateau_quantile=0.78,
            best_point="fast=6、slow=6",
            best_run_id=None,
            representative_point="fast=3、slow=3",
            report_path=str(report),
            report_hash="0" * 64,
        )

    code, output = strategy("verify")
    assert code == 3
    assert "未經唯一入口寫入" in output
    assert "sweep_batch" in output
    assert "測試-繞過入口的批次" in output
    # 批次登記歸「定義」那一類(KARST-087 起報告分三類講)
    assert "定義:" in output


# 驗收條件 4:不繞過 karst/store.py 開連線(D-027 第 4 條護欄二)
def test_gateway_writes_the_three_tables_only_through_the_store_api():
    for path in sorted((REPO_ROOT / "karst" / "gateway").glob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "sqlite3.connect" not in source, path.name
        # 三張表的 SQL 一律住在 karst/store.py,入口只呼叫它的 API
        for table in ("active_setup", "risk_rule", "strategy_risk_ref"):
            assert not re.search(rf"(?i)(insert|update|delete)[^\n]*{table}\b", source), (
                path.name,
                table,
            )
