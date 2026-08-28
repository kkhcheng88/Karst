"""KARST-022 驗收:唯一入口 CLI v0。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況。
全部經命令列那道門(``karst.gateway.cli.main``)入庫,與人手用的是同一條路。
"""

from __future__ import annotations

import io
import json
import sqlite3
from pathlib import Path

import pytest

from karst.errors import NotFound
from karst.gateway import Gateway
from karst.gateway.cli import main
from karst.store import DefinitionStore

MOMENTUM = "動量·12-1 月"
FORMULA = "close[-21] / close[-252] - 1"
INPUT_VERSION = "2026-08-27-a1b2c3d4e5f6"


@pytest.fixture()
def karst(tmp_path, monkeypatch):
    """回傳一個「跑一句 karst 命令」的函數:(回傳碼, 螢幕輸出)。"""
    monkeypatch.delenv("KARST_GATEWAY_KEY", raising=False)
    monkeypatch.setenv("KARST_WRITER", "KARST-022-builder")
    path = str(tmp_path / "karst.sqlite")

    def run(*argv: str) -> tuple[int, str]:
        buffer = io.StringIO()
        code = main(["--store", path, *argv], out=buffer)
        return code, buffer.getvalue()

    run.path = path  # type: ignore[attr-defined]
    return run


def register_momentum(karst) -> tuple[int, str]:
    return karst(
        "factor", "register", "--name", MOMENTUM, "--scale", "cardinal",
        "--formula", FORMULA, "--input-data-version", INPUT_VERSION,
    )


# 驗收條件 1:經命令寫入因子與策略皆成功,兩者自動蓋齊版本、時間戳與父版本
def test_cli_stamps_version_timestamp_and_parent(karst):
    code, output = register_momentum(karst)
    assert code == 0
    assert "第 1 版(父版本:無)" in output

    code, output = karst(
        "factor", "new-version", "--name", MOMENTUM, "--scale", "cardinal",
        "--formula", FORMULA + "  # 剔除最近一週", "--input-data-version", INPUT_VERSION,
    )
    assert code == 0
    assert "第 2 版(父版本:factor_version_id=1)" in output

    code, output = karst(
        "strategy", "register", "--name", "趨勢波段", "--type", "technical",
        "--factor", f"{MOMENTUM}@1",
        "--param-set", "現役", "--cadence", "monthly",
        "--set", "breakout_window=50", "--set", "stop_atr=2.0",
    )
    assert code == 0
    assert "第 1 版(父版本:無)" in output
    assert "technical(技術趨勢)" in output

    with DefinitionStore.open(karst.path) as store:
        strategy = store.get_strategy_version("趨勢波段")
        assert strategy.version_no == 1
        assert strategy.parent_version_id is None
        assert strategy.created_at.startswith("20")  # 時間戳由庫層自動蓋
        # 引用釘死在具體定義的第 1 版,不會跟著因子出新版浮動
        assert [(f.name, f.version_no) for f in strategy.factors] == [(MOMENTUM, 1)]

        param_set = store.get_param_set("趨勢波段", "現役")
        assert param_set.rebalance_cadence == "monthly"
        assert param_set.values == {"breakout_window": "50", "stop_atr": "2.0"}

    assert karst("verify")[0] == 0  # 全部經同一道門寫入,核對清白


# 驗收條件 2:合約不合格者被拒收,庫內一個字都寫不入
def test_cli_rejects_incomplete_contracts(karst, tmp_path):
    code, output = karst("factor", "register", "--name", MOMENTUM,
                         "--formula", FORMULA, "--input-data-version", INPUT_VERSION)
    assert code == 1
    assert "刻度型" in output

    code, output = karst("factor", "register", "--name", MOMENTUM, "--scale", "cardinal")
    assert code == 1
    assert "產生程序" in output

    with DefinitionStore.open(karst.path) as store:
        with pytest.raises(NotFound):
            store.get_factor_version(MOMENTUM)  # 兩次都寫不入,庫裡一個因子都沒有

    assert register_momentum(karst)[0] == 0

    # 策略類型不在策略總覽八類之內
    code, output = karst(
        "strategy", "register", "--name", "亂來", "--type", "vibes",
        "--factor", MOMENTUM, "--param-set", "現役", "--cadence", "monthly",
        "--set", "n=1",
    )
    assert code == 1
    assert "策略類型只收" in output

    # 知情時間早過事件時間即前視,同一道門一樣擋
    values_file = tmp_path / "values.json"
    values_file.write_text(
        json.dumps([{"entity_id": 1, "event_time": "2026-08-26",
                     "knowledge_time": "2026-08-25", "executable_time": "2026-08-27",
                     "value": 0.31}]),
        encoding="utf-8",
    )
    code, output = karst("factor", "write-values", "--name", MOMENTUM,
                         "--from-json", str(values_file))
    assert code == 1
    assert "前視" in output

    with DefinitionStore.open(karst.path) as store:
        assert store.read_factor_values(MOMENTUM, as_of="2026-08-27").empty
        with pytest.raises(NotFound):
            store.get_strategy_version("亂來")


# 驗收條件 2(續):換倉節奏無預設值,缺就拒,策略亦不會寫成半截
def test_cli_rejects_param_set_without_cadence(karst):
    assert register_momentum(karst)[0] == 0

    code, output = karst(
        "strategy", "register", "--name", "趨勢波段", "--type", "technical",
        "--factor", MOMENTUM, "--param-set", "現役", "--set", "breakout_window=50",
    )
    assert code == 1
    assert "換倉節奏" in output
    assert "不設預設值" in output

    with DefinitionStore.open(karst.path) as store:
        with pytest.raises(NotFound):
            store.get_strategy_version("趨勢波段")


# 驗收條件 3:繞過命令直接改庫,下次核對即報得出該處不合格
def test_verify_catches_writes_that_bypass_the_gateway(karst):
    assert register_momentum(karst)[0] == 0
    assert karst(
        "strategy", "register", "--name", "趨勢波段", "--type", "technical",
        "--factor", MOMENTUM, "--param-set", "現役", "--cadence", "monthly",
        "--set", "breakout_window=50",
    )[0] == 0
    assert karst("verify")[0] == 0

    # 有人直接開庫檔,自己塞一套策略進去(沒有經唯一入口,自然沒有簽章)
    smuggled = sqlite3.connect(karst.path)
    smuggled.execute(
        "INSERT INTO strategy (name, strategy_type, created_at) VALUES (?, ?, ?)",
        ("暗手策略", "technical", "2026-08-27T00:00:00+00:00"),
    )
    smuggled.commit()

    # 改寫已落庫的定義連 trigger 那一關都過不到
    with pytest.raises(sqlite3.IntegrityError):
        smuggled.execute("UPDATE factor_version SET formula = 'x' WHERE factor_version_id = 1")
    smuggled.close()

    code, output = karst("verify")
    assert code == 3
    assert "未經唯一入口寫入" in output
    assert "strategy" in output
    assert "不會被當作正常定義用落去" in output


# 驗收條件 4:同一項定義只有一個正本,命令講得出唯一落點,查不到第二份影像
def test_definition_has_exactly_one_home(karst):
    assert register_momentum(karst)[0] == 0
    assert karst(
        "factor", "new-version", "--name", MOMENTUM, "--scale", "cardinal",
        "--formula", FORMULA + "  # 第二版", "--input-data-version", INPUT_VERSION,
    )[0] == 0
    assert karst(
        "strategy", "register", "--name", "趨勢波段", "--type", "technical",
        "--factor", MOMENTUM, "--param-set", "現役", "--cadence", "quarterly",
        "--set", "breakout_window=50",
    )[0] == 0

    code, output = karst("where", "--kind", "factor", "--name", MOMENTUM)
    assert code == 0
    assert "factor(factor_id=1)" in output
    assert "共 2 版" in output  # 版本鏈同表,不是第二份定義
    assert "第二影像  無" in output

    with DefinitionStore.open(karst.path) as store:
        location = store.locate_definition("factor", MOMENTUM)
        # 全庫掃描:這個名字只出現在正本那一欄;引用它的策略只存編號
        assert location.occurrences == ("factor.name(1 列)",)
        assert not location.has_second_image


# ----------------------------------------------------------------------
# KARST-046:「同名同值沿用舊版」收歸唯一入口一處
# ----------------------------------------------------------------------


def _register_trend_swing(karst) -> None:
    assert register_momentum(karst)[0] == 0
    assert karst(
        "strategy", "register", "--name", "趨勢波段", "--type", "technical",
        "--factor", MOMENTUM, "--param-set", "現役", "--cadence", "monthly",
        "--set", "breakout_window=50",
    )[0] == 0


# KARST-046 驗收條件 1(前半):唯一入口自己就會沿用同名、同節奏、同取值的舊版
def test_the_gateway_itself_reuses_the_same_name_cadence_and_values(karst):
    _register_trend_swing(karst)
    with Gateway.open(karst.path) as gateway:
        first, first_receipt = gateway.register_param_set(
            "趨勢波段", param_set_name="示例",
            rebalance_cadence="monthly", values={"breakout_window": "50"},
        )
        assert first.version_no == 1
        assert first_receipt.reused is False
        assert first_receipt.signed_rows  # 真的寫過,所以蓋了章

        # 一字不改再登記一次:回的是同一列,庫裡不會多一版
        second, second_receipt = gateway.register_param_set(
            "趨勢波段", param_set_name="示例",
            rebalance_cadence="monthly", values={"breakout_window": "50"},
        )
        assert second.param_set_id == first.param_set_id
        assert second.version_no == first.version_no
        assert second.created_at == first.created_at  # 真是舊那一列,不是新寫的
        assert second_receipt.reused is True
        # 沿用不會補蓋新簽章,回的是那一列本來就有的
        assert second_receipt.signed_rows == first_receipt.signed_rows

        # 取值寫成數字而不是文字,一樣認得是同一組(庫層一律收成文字)
        as_number, number_receipt = gateway.register_param_set(
            "趨勢波段", param_set_name="示例",
            rebalance_cadence="monthly", values={"breakout_window": 50},
        )
        assert as_number.param_set_id == first.param_set_id
        assert number_receipt.reused is True

        # 沿用不會過頭:節奏不同要出新版,取值不同亦然
        other_cadence, cadence_receipt = gateway.register_param_set(
            "趨勢波段", param_set_name="示例",
            rebalance_cadence="quarterly", values={"breakout_window": "50"},
        )
        assert other_cadence.version_no == 2
        assert cadence_receipt.reused is False

        other_values, values_receipt = gateway.register_param_set(
            "趨勢波段", param_set_name="示例",
            rebalance_cadence="quarterly", values={"breakout_window": "80"},
        )
        assert other_values.version_no == 3
        assert values_receipt.reused is False

    # 沿用那幾次一列都沒有寫入,核對照樣清白
    assert karst("verify")[0] == 0


# KARST-046 驗收條件 1(後半):策略層查不到第二份同樣邏輯
def test_the_strategy_layer_keeps_no_second_copy_of_the_reuse_rule():
    from karst.gateway import service
    from karst.strategies import factor_mix, trend_swing
    from karst.sweep import factor_mix as sweep_factor_mix

    # 正本只有入口那一份
    assert hasattr(service.Gateway, "_existing_param_set")

    for module in (trend_swing, factor_mix, sweep_factor_mix):
        assert not hasattr(module, "_existing_param_set")
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "_existing_param_set" not in source
        # 連比對那兩句本身都不應該再出現在策略層
        assert "rebalance_cadence ==" not in source
        assert "rebalance_cadence !=" not in source
