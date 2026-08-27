"""KARST-031 驗收:因子混合策略(ETF 版),四類因子敞口混權重跑回測。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況。

驗收條件 1 用**真實**行情(四隻因子 ETF 加 SPY、QQQ,經 karst.data 現有管線
凍成快照);離線即 skip 並註明,做法沿用 tests/test_data_yfinance.py——不以
合成數據冒充真實抓取,亦不讓離線變成假綠燈。其餘三條不需連網。
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from karst import ContractViolation
from karst.data import (
    DataFetchFailed,
    UniverseMember,
    YFinanceSource,
    build_price_snapshot,
    read_price_panel,
)
from karst.engine import PricePanel
from karst.gateway.service import Gateway
from karst.runs import RunStore, window_stats
from karst.store import FAMILY_SEPARATOR
from karst.strategies.factor_mix import (
    FACTOR_ETF_SLEEVES,
    FactorMixParams,
    FactorSleeve,
    record_factor_mix_run,
    register_factor_mix,
    resolve_exposures,
    run_factor_mix,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

STRATEGY = "因子混合(ETF 版)"
ENGINE_VERSION = "0.1.0"

# 真實抓取那半:四格因子敞口,加主日曆代號 SPY 與 QQQ(證明面板有其他實體時
# 不屬敞口的一律不持有)。窗口刻意收在一個已收市的年度,重抓得回同一個快照。
REAL_UNIVERSE = (
    UniverseMember("SPY", "etf", "SPDR S&P 500 ETF Trust"),
    UniverseMember("QQQ", "etf", "Invesco QQQ Trust, Series 1"),
    *[
        UniverseMember(sleeve.ticker, "etf", sleeve.display_name)
        for sleeve in FACTOR_ETF_SLEEVES
    ],
)
REAL_WINDOW = ("2024-01-02", "2024-12-31")

# 示例權重。**只是示例**,不是現役設定;四格的值住在參數集,不住在碼裡。
SAMPLE_WEIGHTS = {
    "weight_quality": "0.25",
    "weight_value": "0.25",
    "weight_momentum": "0.25",
    "weight_low_vol": "0.25",
}
SAMPLE_CADENCE = "quarterly"

TOY_DATES = pd.bdate_range("2024-01-02", periods=180)
TOY_SNAPSHOT = "2026-08-27-toy000000000"


# ----------------------------------------------------------------------
# 玩具裝置(不連網):實體、代號、因子、策略、參數集全部走真路徑登記
# ----------------------------------------------------------------------


@pytest.fixture()
def gateway(tmp_path, monkeypatch):
    monkeypatch.setenv("KARST_WRITER", "KARST-031-factormix")
    with Gateway.open(str(tmp_path / "karst.sqlite")) as opened:
        yield opened


def _toy_panel(store, sleeves, *, kinds=None) -> PricePanel:
    """按名單登記實體與代號,砌一張玩具價格面板。

    ``kinds`` 留空即全部當 ETF;傳入即逐格指定種類——用來證明同一條路徑
    照樣行得通,ETF 與股票沒有兩條路。
    """
    kinds = list(kinds or ["etf"] * len(sleeves))
    entity_ids = []
    for sleeve, kind in zip(sleeves, kinds, strict=True):
        if kind == "company":
            anchor = "9" + str(sum(ord(c) for c in sleeve.ticker)).zfill(9)
            entity_id = store.register_entity(
                kind="company", display_name=sleeve.display_name, cik=anchor
            )
        else:
            entity_id = store.register_entity(
                kind=kind, display_name=sleeve.display_name, local_code=sleeve.ticker
            )
        store.register_ticker(entity_id, sleeve.ticker, valid_from=str(TOY_DATES[0].date()))
        entity_ids.append(entity_id)

    generator = np.random.default_rng(20260828)
    steps = generator.normal(0.0003, 0.009, (len(TOY_DATES), len(entity_ids)))
    steps += np.linspace(0.0, 0.0006, len(entity_ids))  # 每格漂移不同,權重改得出分別
    close = pd.DataFrame(
        100.0 * np.exp(np.cumsum(steps, axis=0)), index=TOY_DATES, columns=entity_ids
    )
    open_prices = close.shift(1)
    open_prices.iloc[0] = 100.0
    return PricePanel.from_frames(open=open_prices * 1.001, close=close)


@pytest.fixture()
def toy(gateway):
    """四格因子敞口的玩具場:因子、策略、參數集全部經唯一入口登記。"""
    panel = _toy_panel(gateway.store, FACTOR_ETF_SLEEVES)
    version, param_set = register_factor_mix(
        gateway,
        strategy_name=STRATEGY,
        sleeves=FACTOR_ETF_SLEEVES,
        snapshot_id=TOY_SNAPSHOT,
        param_set_name="示例-四等分",
        rebalance_cadence=SAMPLE_CADENCE,
        weights=SAMPLE_WEIGHTS,
    )
    return {"gateway": gateway, "store": gateway.store, "panel": panel,
            "strategy": version, "param_set": param_set}


# ----------------------------------------------------------------------
# 真實抓取那半
# ----------------------------------------------------------------------


@pytest.fixture(scope="module")
def online() -> None:
    try:
        YFinanceSource().fetch_daily_bars(["QUAL"], "2024-01-02", "2024-01-05")
    except DataFetchFailed as exc:
        pytest.skip(f"離線或來源不通,跳過真實抓取:{exc}")


@pytest.fixture(scope="module")
def real(online, tmp_path_factory):
    """真實一次:抓快照 → 登記定義 → 跑回測 → 落痕。"""
    root = tmp_path_factory.mktemp("factor-mix")
    with Gateway.open(str(root / "karst.sqlite")) as opened:
        store = opened.store
        snapshot = build_price_snapshot(
            store,
            start=REAL_WINDOW[0],
            end=REAL_WINDOW[1],
            universe=REAL_UNIVERSE,
            source=YFinanceSource(),
            root=root / "snapshots",
        )
        opens = read_price_panel(store, snapshot.snapshot_id, field="open").dropna(how="any")
        closes = read_price_panel(store, snapshot.snapshot_id, field="close").dropna(how="any")
        common = opens.index.intersection(closes.index)
        panel = PricePanel.from_frames(open=opens.loc[common], close=closes.loc[common])

        strategy, param_set = register_factor_mix(
            opened,
            strategy_name=STRATEGY,
            sleeves=FACTOR_ETF_SLEEVES,
            snapshot_id=snapshot.snapshot_id,
            param_set_name="示例-四等分",
            rebalance_cadence=SAMPLE_CADENCE,
            weights=SAMPLE_WEIGHTS,
            description="KARST-031 示例參數,不是現役設定",
        )
        params = FactorMixParams.from_param_set(param_set, FACTOR_ETF_SLEEVES)
        result = run_factor_mix(
            store=store, panel=panel, sleeves=FACTOR_ETF_SLEEVES, params=params
        )
        runs = RunStore(store, root=root / "runs")
        record = record_factor_mix_run(
            runs,
            result,
            strategy_name=strategy.name,
            param_set_name=param_set.name,
            snapshot_id=snapshot.snapshot_id,
            engine_version=ENGINE_VERSION,
        )
        yield {"store": store, "snapshot": snapshot, "panel": panel, "params": params,
               "result": result, "runs": runs, "record": record}


# 驗收條件 1:四類因子 ETF 按指定權重混成一個組合,跑得出一次完整回測並交得出逐日淨值(D-012)
def test_four_factor_etfs_mix_into_one_portfolio_with_a_daily_equity_curve(real):
    result, panel = real["result"], real["panel"]

    # 四格敞口,四隻真 ETF,權重由參數集而來
    assert len(result.exposures) == 4
    assert [e.sleeve.ticker for e in result.exposures] == ["QUAL", "VLUE", "MTUM", "USMV"]
    assert all(e.entity_kind == "etf" for e in result.exposures)
    assert sum(e.weight for e in result.exposures) == pytest.approx(1.0)

    # 逐日淨值:每一根 K 線一個數,無缺口,由起始本金起步
    assert isinstance(result.equity_curve, pd.Series)
    assert list(result.equity_curve.index) == list(panel.dates)
    assert result.equity_curve.notna().all()
    assert (result.equity_curve > 0).all()
    assert result.equity_curve.iloc[0] == pytest.approx(result.params.initial_cash)
    assert np.isfinite(result.total_return)
    assert 240 <= len(result.equity_curve) <= 260  # 2024 一整年的美股交易日

    # 逐日持倉、逐筆訂單
    assert result.holdings.shape == (len(panel.dates), len(panel.entity_ids))
    orders = result.orders_frame()
    assert len(orders) > 0
    assert set(orders["side"]) <= {"buy", "sell"}

    # 四隻因子 ETF 全部真的買過;同一個面板裡的 SPY、QQQ 一股都不持有
    held = result.holdings.iloc[-1]
    exposed = {e.entity_id for e in result.exposures}
    assert all(held[entity_id] > 0 for entity_id in exposed)
    assert all(held[entity_id] == 0 for entity_id in set(panel.entity_ids) - exposed)

    # 混出來的組合走勢落在四隻成份之間——這是「混」不是「揀一隻」。
    # 兩邊都由**執行日的開價**起計:組合第一根 K 線持現金,第二根按開價建倉。
    mixed = float(result.equity_curve.iloc[-1] / result.equity_curve.iloc[0])
    singles = [
        float(panel.close[entity_id].iloc[-1] / panel.open[entity_id].iloc[1])
        for entity_id in exposed
    ]
    assert min(singles) < mixed < max(singles)

    # 經 karst.runs 登記,引用得到快照編號與四個因子版本(D-021 第 8、9 條)
    record = real["record"]
    assert record.snapshot_id == real["snapshot"].snapshot_id
    assert record.rebalance_cadence == SAMPLE_CADENCE
    assert sorted(f.name for f in record.factors) == sorted(
        s.factor_name for s in FACTOR_ETF_SLEEVES
    )
    assert record.trading_days == len(result.equity_curve)
    # 落痕之後讀得回逐日淨值,不用重跑引擎
    replayed = real["runs"].equity_curve(record.run_id)
    assert len(replayed) == len(result.equity_curve)
    assert float(replayed.iloc[-1]) == pytest.approx(float(result.equity_curve.iloc[-1]))
    assert np.isfinite(window_stats(replayed).max_drawdown)


# 驗收條件 2:ETF 與股票走同一條可投資對象路徑,適配層無為 ETF 另設的分支(D-012)
def test_etfs_and_stocks_share_one_investable_path(gateway):
    store = gateway.store

    # (a) 適配層由頭到尾不知道「ETF」這回事:全個 karst/engine/ 的碼(不計說明
    #     文字)查不到 etf,亦查不到 entity_kind——它只認得實體編號。
    offenders = {}
    for path in (REPO_ROOT / "karst" / "engine").rglob("*.py"):
        hits = [s for s in _code_symbols(path) if "etf" in s.lower() or "entity_kind" in s]
        if hits:
            offenders[path.name] = hits
    assert offenders == {}

    # (b) 一格換成上市公司,同一個函式照跑——策略層一個字不用改
    mixed_sleeves = (
        FACTOR_ETF_SLEEVES[0],
        FactorSleeve(
            family="價值",
            specific="玩具股票版價值(TOYV)",
            ticker="TOYV",
            display_name="Toy Value Inc.",
            weight_key="weight_value",
        ),
    )
    panel = _toy_panel(store, mixed_sleeves, kinds=["etf", "company"])
    register_factor_mix(
        gateway,
        strategy_name="因子混合(ETF 加股票玩具版)",
        sleeves=mixed_sleeves,
        snapshot_id=TOY_SNAPSHOT,
        param_set_name="玩具-對半",
        rebalance_cadence="monthly",
        weights={"weight_quality": "0.5", "weight_value": "0.5"},
    )
    params = FactorMixParams(
        cadence="monthly", weights={"weight_quality": 0.5, "weight_value": 0.5}
    )
    result = run_factor_mix(
        store=store, panel=panel, sleeves=mixed_sleeves, params=params
    )

    # 兩格種類不同,但兩格都是同一張映射表解析出來的實體編號、同一張價格面板的一欄
    kinds = {e.sleeve.ticker: e.entity_kind for e in result.exposures}
    assert kinds == {"QUAL": "etf", "TOYV": "company"}
    for exposure in result.exposures:
        assert exposure.entity_id in panel.entity_ids
        assert exposure.entity_id == store.resolve_ticker(
            exposure.sleeve.ticker, panel.dates[0]
        )
        assert isinstance(exposure.entity_id, int)

    # 兩格都真的落到注,而且淨值行得出來
    traded = set(result.orders_frame()["entity_id"])
    assert traded == {e.entity_id for e in result.exposures}
    assert result.equity_curve.notna().all()

    # (c) 解析路徑本身沒有分岔:同一個 resolve_exposures 收兩種實體,一樣的回法
    again = resolve_exposures(store, mixed_sleeves, params, on_date=panel.dates[0])
    assert [e.entity_id for e in again] == [e.entity_id for e in result.exposures]


# 驗收條件 3:落庫的因子名全部在「族名·具體定義」一級,查不到單以族名登記的因子(規格 1.8)
def test_no_factor_is_registered_under_a_family_name_alone(toy):
    store = toy["store"]

    # 查庫:每一個落了庫的因子,名都是「族名·具體定義」,兩邊都不空
    rows = store.connection.execute(
        "SELECT name, family FROM factor ORDER BY name"
    ).fetchall()
    assert len(rows) == 4
    for row in rows:
        name, family = row["name"], row["family"]
        assert FAMILY_SEPARATOR in name
        head, _, tail = name.partition(FAMILY_SEPARATOR)
        assert head.strip() and tail.strip()
        assert head == family
        assert name != family  # 單以族名登記的因子:一個都沒有

    # 四個族名一個都不是因子名
    families = {row["family"] for row in rows}
    assert families == {"質素", "價值", "動能", "低波"}
    names = {row["name"] for row in rows}
    assert families.isdisjoint(names)
    bare = store.connection.execute(
        "SELECT COUNT(*) AS n FROM factor WHERE name = family"
    ).fetchone()
    assert int(bare["n"]) == 0

    # 連寫都寫不入:族名單獨登記,合約當場拒收
    for family in sorted(families):
        with pytest.raises(ContractViolation, match="族名"):
            toy["gateway"].register_factor(family, scale_kind="cardinal")
        with pytest.raises(ContractViolation, match="族名"):
            store.get_factor_version(family)

    # 每個因子全庫只有一處正本,無第二影像(D-002 第 4 條)
    for sleeve in FACTOR_ETF_SLEEVES:
        location = store.locate_definition("factor", sleeve.factor_name)
        assert location.has_second_image is False
        assert location.table == "factor"

    # 策略引用的也是具體定義那一級,不是族名
    assert sorted(f.name for f in toy["strategy"].factors) == sorted(names)


# 驗收條件 4:四類的權重是可掃描參數,不寫死在碼裡(D-008)
def test_the_four_weights_are_scannable_parameters(toy):
    gateway, store, panel = toy["gateway"], toy["store"], toy["panel"]

    # 掃描一格參數 = 多登記一個參數集 + 多叫一次,一行碼都不用改
    grid = {
        "掃描-四等分": ("quarterly", ("0.25", "0.25", "0.25", "0.25")),
        "掃描-偏動能": ("quarterly", ("0.1", "0.1", "0.7", "0.1")),
        "掃描-偏低波": ("quarterly", ("0.1", "0.1", "0.1", "0.7")),
        "掃描-半倉四等分": ("quarterly", ("0.125", "0.125", "0.125", "0.125")),
        "掃描-四等分月度": ("monthly", ("0.25", "0.25", "0.25", "0.25")),
    }
    keys = [sleeve.weight_key for sleeve in FACTOR_ETF_SLEEVES]

    finals = {}
    for set_name, (cadence, values) in grid.items():
        _, param_set = register_factor_mix(
            gateway,
            strategy_name=STRATEGY,
            sleeves=FACTOR_ETF_SLEEVES,
            snapshot_id=TOY_SNAPSHOT,
            param_set_name=set_name,
            rebalance_cadence=cadence,
            weights=dict(zip(keys, values, strict=True)),
        )
        params = FactorMixParams.from_param_set(param_set, FACTOR_ETF_SLEEVES)
        assert params.cadence == cadence
        assert params.weights == {k: float(v) for k, v in zip(keys, values, strict=True)}

        result = run_factor_mix(
            store=store, panel=panel, sleeves=FACTOR_ETF_SLEEVES, params=params
        )
        finals[set_name] = round(float(result.equity_curve.iloc[-1]), 6)

    # 五格參數跑出五條不同的淨值曲線
    assert len(set(finals.values())) == 5

    # 半倉那格與全倉那格只差在權重(節奏一樣),結果照樣不同:權重真的入了數
    assert finals["掃描-四等分"] != finals["掃描-半倉四等分"]

    # 權重沒有預設值:參數集缺一格即拒收,不代用戶決定
    _, short = register_factor_mix(
        gateway,
        strategy_name=STRATEGY,
        sleeves=FACTOR_ETF_SLEEVES,
        snapshot_id=TOY_SNAPSHOT,
        param_set_name="掃描-缺一格",
        rebalance_cadence="quarterly",
        weights={keys[0]: "0.5", keys[1]: "0.5"},
    )
    with pytest.raises(ContractViolation, match="缺權重"):
        FactorMixParams.from_param_set(short, FACTOR_ETF_SLEEVES)
    with pytest.raises(ContractViolation, match="缺權重"):
        FactorMixParams(cadence="quarterly", weights={})

    # 簽名本身沒有預設值(權重與節奏都是)
    for field in ("weights", "cadence"):
        parameter = inspect.signature(FactorMixParams).parameters[field]
        assert parameter.default is inspect.Parameter.empty

    # 策略層原始碼裡查不到任何權重數值(看語法樹,不看註解與說明文字)
    for path in (REPO_ROOT / "karst" / "strategies").rglob("*.py"):
        assert _weight_defaults(path) == [], path


# ----------------------------------------------------------------------
# 掃原始碼用的兩個小工具
# ----------------------------------------------------------------------


def _code_symbols(path: Path) -> list[str]:
    """這個檔的碼裡出現過的名與字串(說明文字不算)。

    看語法樹而不是逐個字搜:說明文字裡提一句「ETF」不代表碼裡有一條為 ETF
    而設的分支,只有識別字與真正用到的字串才算。
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None:
                docstrings.add(doc)

    symbols: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            symbols.append(node.id)
        elif isinstance(node, ast.Attribute):
            symbols.append(node.attr)
        elif isinstance(node, ast.arg):
            symbols.append(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(node.name)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value not in docstrings:
                symbols.append(node.value)
    return symbols


def _weight_defaults(path: Path) -> list[str]:
    """找出這個檔裡有沒有人偷偷給某格權重一個數值。

    與節奏那一關同制(tests/test_engine_ranking_rebalance.py):說明文字裡的
    用法示範不算,只有真的寫進簽名或賦值那一格才算。
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders: list[str] = []

    def is_number(node: ast.AST | None) -> bool:
        return (
            isinstance(node, ast.Constant)
            and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool)
        )

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            positional = node.args.posonlyargs + node.args.args
            tail = positional[len(positional) - len(node.args.defaults) :]
            pairs = list(zip(tail, node.args.defaults))
            pairs += [
                (argument, default)
                for argument, default in zip(node.args.kwonlyargs, node.args.kw_defaults)
                if default is not None
            ]
            offenders += [
                f"{path.name}:{node.name}({argument.arg}=...)"
                for argument, default in pairs
                if "weight" in argument.arg and is_number(default)
            ]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if "weight" in node.target.id and is_number(node.value):
                offenders.append(f"{path.name}:{node.target.id}")
        elif isinstance(node, ast.Assign):
            offenders += [
                f"{path.name}:{target.id}"
                for target in node.targets
                if isinstance(target, ast.Name) and "weight" in target.id and is_number(node.value)
            ]
    return offenders
