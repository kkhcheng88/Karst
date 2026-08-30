"""KARST-031 / KARST-041 驗收:因子混合策略(ETF 版)。

每個測試對住票上一項驗收條件,只證「行得通」,不掃邊界情況。

KARST-031 驗收條件 1 用**真實**行情(四隻因子 ETF 加 SPY、QQQ,經 karst.data
現有管線凍成快照);離線即 skip 並註明,做法沿用 tests/test_data_yfinance.py
——不以合成數據冒充真實抓取,亦不讓離線變成假綠燈。其餘三條不需連網。

KARST-041 那三條在本檔尾:同值重登記沿用舊版、示例運行的重生腳本、沿用不過頭
加公開接口不變。第一條與第三條完全離線(靜態來源重放同一條管線凍一個真快照,
D-026 第 7 條);第二條要倉裡有示例運行那個數據快照(``data/`` 不入 git),
沒有就 skip 並講明怎樣重抓。
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from karst import ContractViolation, DefinitionStore
from karst.data import (
    DataFetchFailed,
    StaticSource,
    UniverseMember,
    YFinanceSource,
    build_price_snapshot,
    read_price_panel,
)
from karst.engine import PricePanel
from karst.errors import NotFound
from karst.gateway.service import Gateway
from karst.runs import RunStore, window_stats
from karst.store import FAMILY_SEPARATOR
from karst.executor import (
    RISK_MAX_POSITION,
    RISK_MONTHLY_CAP,
    RISK_PER_TRADE,
    SAMPLE,
    SLOT_CADENCE,
    Executor,
    MissingParameter,
    ParameterOutOfRange,
    RunRequest,
    UnknownParameter,
    register_setup,
    risk_fields,
)
from karst.strategies.factor_mix import (
    CADENCE_PARAM,
    FACTOR_ETF_SLEEVES,
    FactorMixContract,
    FactorMixParams,
    FactorSleeve,
    resolve_exposures,
    run_factor_mix,
)
from karst.sweep.factor_mix import weight_grid

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


def _contract(
    sleeves=FACTOR_ETF_SLEEVES, *, initial_cash: float = 100_000.0, fees: float = 0.0
) -> FactorMixContract:
    """這條策略的合約。帳戶設定明寫——它們無預設值,亦不入參數集。"""
    return FactorMixContract(
        sleeves=tuple(sleeves), initial_cash=initial_cash, fees=fees
    )


def _values(weights, cadence: str = SAMPLE_CADENCE) -> dict:
    """一組取值:四格權重加換倉節奏。節奏在參數規格裡與權重同級,一樣要明寫。"""
    return {**dict(weights), CADENCE_PARAM: cadence}


def _register_toy(gateway, *, sleeves=FACTOR_ETF_SLEEVES, snapshot_id=None,
                  param_set_name="示例-四等分", weights=None, cadence=SAMPLE_CADENCE):
    """經策略執行台登記一次。示例取值一律自報「示例」(D-038)。"""
    return register_setup(
        gateway,
        _contract(sleeves),
        strategy_name=STRATEGY,
        snapshot_id=snapshot_id or TOY_SNAPSHOT,
        param_set_name=param_set_name,
        values=_values(weights or SAMPLE_WEIGHTS, cadence),
        alignment=SAMPLE,
    )


@pytest.fixture()
def toy(gateway):
    """四格因子敞口的玩具場:因子、策略、參數集全部經唯一入口登記。"""
    panel = _toy_panel(gateway.store, FACTOR_ETF_SLEEVES)
    setup = _register_toy(gateway)
    return {"gateway": gateway, "store": gateway.store, "panel": panel,
            "strategy": setup.strategy, "param_set": setup.param_set, "setup": setup}


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

        contract = _contract()
        setup = register_setup(
            opened,
            contract,
            strategy_name=STRATEGY,
            snapshot_id=snapshot.snapshot_id,
            param_set_name="示例-四等分",
            values=_values(SAMPLE_WEIGHTS),
            alignment=SAMPLE,
            description="KARST-031 示例參數,不是現役設定",
        )
        param_set = setup.param_set
        params = FactorMixParams.from_param_set(param_set, FACTOR_ETF_SLEEVES)
        runs = RunStore(store, root=root / "runs")
        executor = Executor(opened, runs)
        outcome = executor.run(
            contract,
            setup=setup,
            panel=panel,
            period=(str(panel.dates[0].date()), str(panel.dates[-1].date())),
            engine_version=ENGINE_VERSION,
            risk_free_rate=0.0,
            benchmarks=(),
        )
        result = run_factor_mix(
            store=store, panel=panel, sleeves=FACTOR_ETF_SLEEVES, params=params
        )
        yield {"store": store, "snapshot": snapshot, "panel": panel, "params": params,
               "result": result, "runs": runs, "record": outcome.record,
               "outcome": outcome, "setup": setup}


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
    register_setup(
        gateway,
        _contract(mixed_sleeves),
        strategy_name="因子混合(ETF 加股票玩具版)",
        snapshot_id=TOY_SNAPSHOT,
        param_set_name="玩具-對半",
        values=_values({"weight_quality": "0.5", "weight_value": "0.5"}, "monthly"),
        alignment=SAMPLE,
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
        param_set = _register_toy(
            gateway,
            param_set_name=set_name,
            weights=dict(zip(keys, values, strict=True)),
            cadence=cadence,
        ).param_set
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

    # 權重沒有預設值:缺一格根本寫不入參數集,不代用戶決定
    with pytest.raises(MissingParameter):
        _register_toy(
            gateway,
            param_set_name="掃描-缺一格",
            weights={keys[0]: "0.5", keys[1]: "0.5"},
        )
    with pytest.raises(ContractViolation, match="缺權重"):
        FactorMixParams(cadence="quarterly", weights={})

    # 簽名本身沒有預設值(權重與節奏都是)
    for field in ("weights", "cadence"):
        parameter = inspect.signature(FactorMixParams).parameters[field]
        assert parameter.default is inspect.Parameter.empty


# 驗收條件 4(續):參數規格**就是**那張掃描格,每格有值域無取值
def test_the_param_spec_declares_exactly_the_axes_the_sweep_grid_knows():
    spec = _contract().param_spec()

    # (a) 宣告的格數 = 掃描格認得的軸數。多一格會掃不到,少一格會寫不入。
    grid = weight_grid(FACTOR_ETF_SLEEVES, step=0.05, cadences=("monthly", "quarterly"))
    assert set(spec.names) == set(grid.axis_names)
    assert len(spec.fields) == len(grid.axis_names) == 5

    # (b) 每格有值域、無取值——規格裡根本沒有「取值」這個欄位可以填
    assert not hasattr(spec.fields[0], "value")
    assert not hasattr(spec.fields[0], "default")
    for item in spec.fields:
        assert item.range_text.strip()
        assert item.what.strip()

    # (c) 換倉節奏無預設:它是規格裡一格普通可掃軸,只不過落庫時落在自己那一欄
    cadence = spec.cadence_field
    assert cadence is not None
    assert cadence.name == CADENCE_PARAM
    assert cadence.slot == SLOT_CADENCE
    assert set(cadence.choices) >= {"monthly", "quarterly"}

    # (d) 缺一格拒收、多一格拒收、值域不合拒收
    full = _values(SAMPLE_WEIGHTS)
    assert spec.validate(full)                        # 齊的那組照收
    with pytest.raises(MissingParameter):
        spec.validate({k: v for k, v in full.items() if k != CADENCE_PARAM})
    with pytest.raises(UnknownParameter):
        spec.validate({**full, "weight_不存在的族": "0.1"})
    with pytest.raises(ParameterOutOfRange):
        spec.validate({**full, "weight_quality": "1.5"})
    with pytest.raises(ParameterOutOfRange):
        spec.validate({**full, CADENCE_PARAM: "每兩星期"})

    # (e) 風控三格同制:它們是**普通可掃軸**,不是 RunRequest 上一格特權輸入。
    #     單筆風險由 2% 改做 1.5% 要換一個運行編號,所以它們一定要入參數集。
    risk = risk_fields()
    assert [item.name for item in risk] == [
        RISK_PER_TRADE, RISK_MAX_POSITION, RISK_MONTHLY_CAP
    ]
    for item in risk:
        assert item.range_text.strip()
        assert not hasattr(item, "value")
        assert item.check("0.02") == pytest.approx(0.02)
        with pytest.raises(ParameterOutOfRange):
            item.check("1.5")
    assert "risk" not in inspect.signature(RunRequest).parameters


# ======================================================================
# KARST-041:同值重登記沿用舊版,示例運行有入倉的重生腳本
# ======================================================================

# 離線凍一個**真快照**:同一條管線、同一種登記,只是日線由靜態來源重放而不是
# 由 yfinance 抓(D-026 第 7 條)。要有真快照,是因為運行編號蓋住數據快照那一格
# ——沒有快照就算不出編號,而「重登記之後編號相同」正是本票要證的事。
FROZEN_UNIVERSE = tuple(
    UniverseMember(sleeve.ticker, "etf", sleeve.display_name)
    for sleeve in FACTOR_ETF_SLEEVES
)
FROZEN_PARAM_SET = "示例-四等分季度"

SAMPLE_RUN_SCRIPT = (
    REPO_ROOT / "experiments" / "2026-08-28-factor-mix-real" / "run_backtest.py"
)


def _toy_bars() -> pd.DataFrame:
    """四隻因子 ETF 的玩具日線長表,欄位照來源合約(date、ticker、開高低收量)。"""
    generator = np.random.default_rng(20260828)
    rows = []
    for offset, sleeve in enumerate(FACTOR_ETF_SLEEVES):
        steps = generator.normal(0.0003 + offset * 0.0002, 0.009, len(TOY_DATES))
        closes = 100.0 * np.exp(np.cumsum(steps))
        opens = np.concatenate(([100.0], closes[:-1])) * 1.001
        for day, open_price, close_price in zip(TOY_DATES, opens, closes, strict=True):
            rows.append(
                {
                    "date": day.date(),
                    "ticker": sleeve.ticker,
                    "open": float(open_price),
                    "high": float(max(open_price, close_price)) * 1.002,
                    "low": float(min(open_price, close_price)) * 0.998,
                    "close": float(close_price),
                    "volume": 1_000_000.0,
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture()
def frozen(gateway, tmp_path):
    """凍一個離線快照,並砌好它那張價格面板。"""
    snapshot = build_price_snapshot(
        gateway.store,
        start=str(TOY_DATES[0].date()),
        end=str(TOY_DATES[-1].date()),
        universe=FROZEN_UNIVERSE,
        source=StaticSource(_toy_bars(), name="toy"),
        root=tmp_path / "snapshots",
        calendar_ticker=FACTOR_ETF_SLEEVES[0].ticker,
    )
    opens = read_price_panel(
        gateway.store, snapshot.snapshot_id, field="open", root=tmp_path / "snapshots"
    ).dropna(how="any")
    closes = read_price_panel(
        gateway.store, snapshot.snapshot_id, field="close", root=tmp_path / "snapshots"
    ).dropna(how="any")
    common = opens.index.intersection(closes.index)
    panel = PricePanel.from_frames(open=opens.loc[common], close=closes.loc[common])
    return {
        "snapshot_id": snapshot.snapshot_id,
        "panel": panel,
        "runs": RunStore(gateway.store, root=tmp_path / "runs"),
        "period": (str(panel.dates[0].date()), str(panel.dates[-1].date())),
    }


def _register(gateway, frozen, *, param_set_name=FROZEN_PARAM_SET, weights=None, cadence=None):
    return _register_toy(
        gateway,
        snapshot_id=frozen["snapshot_id"],
        param_set_name=param_set_name,
        weights=weights or SAMPLE_WEIGHTS,
        cadence=cadence or SAMPLE_CADENCE,
    )


def _record(gateway, frozen, setup):
    """跑一次正式運行並落痕,全程經策略執行台。"""
    executor = Executor(gateway, frozen["runs"])
    return executor.run(
        _contract(),
        setup=setup,
        panel=frozen["panel"],
        period=frozen["period"],
        engine_version=ENGINE_VERSION,
        risk_free_rate=0.0,
        benchmarks=(),
    )


def _version_count(store, param_set_name: str) -> int:
    row = store.connection.execute(
        "SELECT COUNT(*) AS n FROM param_set WHERE name = ?", (param_set_name,)
    ).fetchone()
    return int(row["n"])


# 驗收條件 1:同一組取值重登記兩次,參數集版本數不變,運行編號相同
def test_registering_the_same_values_twice_keeps_one_version_and_one_run_id(gateway, frozen):
    store = gateway.store

    first = _register(gateway, frozen)
    first_version, first_set = first.strategy, first.param_set
    assert first_set.version_no == 1
    assert _version_count(store, FROZEN_PARAM_SET) == 1
    first_run = _record(gateway, frozen, first)
    assert first_run.reused is False           # 第一次真的叫過引擎

    # 一字不改再登記一次:庫裡一列都不應該多出來
    second = _register(gateway, frozen)
    second_version, second_set = second.strategy, second.param_set
    assert _version_count(store, FROZEN_PARAM_SET) == 1
    assert second_set.param_set_id == first_set.param_set_id
    assert second_set.version_no == first_set.version_no
    assert second_set.created_at == first_set.created_at      # 真的是舊那一列,不是新寫的
    assert dict(second_set.values) == dict(first_set.values)
    assert second_version.version_no == first_version.version_no

    # 權重寫成數字而不是文字,一樣認得是同一組取值(庫層一律收成文字)
    as_numbers = _register(
        gateway,
        frozen,
        weights={key: float(value) for key, value in SAMPLE_WEIGHTS.items()},
    ).param_set
    assert _version_count(store, FROZEN_PARAM_SET) == 1
    assert as_numbers.param_set_id == first_set.param_set_id

    # 同一次回測不會記成兩次:運行編號相同,而且回的是同一筆舊留痕
    second_outcome = _record(gateway, frozen, second)
    second_run = second_outcome.record
    assert second_outcome.reused is True        # 一格都沒改,一次引擎都沒有碰
    assert second_run.run_id == first_run.record.run_id
    assert second_run.created_at == first_run.record.created_at
    assert second_run.fingerprint == first_run.record.fingerprint
    assert (
        int(
            store.connection.execute("SELECT COUNT(*) AS n FROM backtest_run").fetchone()["n"]
        )
        == 1
    )


# 驗收條件 2:experiments/ 內有重生腳本,執行後運行編號與成績不變
def test_the_sample_run_script_rebuilds_the_same_run_id_and_figures(tmp_path):
    assert SAMPLE_RUN_SCRIPT.is_file(), SAMPLE_RUN_SCRIPT

    spec = importlib.util.spec_from_file_location("karst_factor_mix_real", SAMPLE_RUN_SCRIPT)
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)

    # 示例運行認的是 KARST-031 那一次;數據目錄重建(KARST-057)之後,
    # 快照重抓、編號跟住換:舊 run-f4c162e5aac34347 → 新 run-024df83fb4891c89。
    # 三項核對指標一個都沒有變,見 experiments/2026-08-28-rebuild/成績新舊對照.md。
    assert script.EXPECTED_RUN_ID == "run-024df83fb4891c89"

    # 快照編號不在這裡寫死:七支腳本共用 experiments/snapshot_ids.py 那一份,
    # 腳本 import 過,所以這裡拿得到同一個值——下次重抓只改那一個檔。
    import snapshot_ids  # noqa: PLC0415 — 要等腳本先把 experiments/ 放上 sys.path

    assert script.SNAPSHOT_ID == snapshot_ids.PRICE_FACTOR_ETF
    assert script.SAMPLE_CADENCE == "quarterly"
    assert set(script.SAMPLE_WEIGHTS.values()) == {"0.25"}

    if not script.STORE_PATH.is_file() or not (script.SNAPSHOT_ROOT / script.SNAPSHOT_ID).is_dir():
        pytest.skip(
            f"倉裡沒有數據快照 {script.SNAPSHOT_ID}(data/ 不入 git),跳過重生核對;"
            "重抓一句見腳本開頭的 karst data snapshot。重抓必然換一個快照編號"
            "(假設 A-007),換完要同步改 experiments/snapshot_ids.py"
        )

    # 複製一份庫來跑:核對重生,不動倉裡那個庫
    store_copy = tmp_path / "karst.sqlite"
    shutil.copy2(script.STORE_PATH, store_copy)
    with DefinitionStore.open(str(store_copy)) as store:
        try:
            store.get_snapshot(script.SNAPSHOT_ID)
        except NotFound:
            pytest.skip(f"庫內沒有快照 {script.SNAPSHOT_ID} 的登記,跳過重生核對")

    summary = script.rebuild(store_path=store_copy, check=False)

    assert summary["run"]["run_id"] == script.EXPECTED_RUN_ID
    assert summary["run"]["trading_days"] == script.EXPECTED_TRADING_DAYS == 2929
    assert summary["run"]["rebalances"] == script.EXPECTED_REBALANCES == 47
    assert summary["run"]["orders"] == script.EXPECTED_ORDERS == 188
    assert round(summary["metrics"]["total_return"], 4) == 3.2186     # 累計 +321.86%
    assert round(summary["metrics"]["annual_return"], 4) == 0.1319    # 年化 13.19%
    assert round(summary["metrics"]["max_drawdown"], 4) == -0.3493    # 最大回撤 −34.93%

    # 重跑沒有把參數集推出新版——正是驗收條件 1 那條在真庫上的樣子
    assert summary["param_set"]["version_no"] == 1
    assert summary["param_set"]["name"] == "示例-四等分季度"

    # 腳本自己那道核對閘亦要行得通(對不上它會拋 AssertionError)
    script.check_reproduction(summary)


# 驗收條件 3:既有測試全部照過——沿用不可以過頭,公開接口一個字不變
def test_reuse_does_not_overreach_and_the_public_signature_is_unchanged(gateway, frozen):
    store = gateway.store
    _register(gateway, frozen)
    assert _version_count(store, FROZEN_PARAM_SET) == 1

    # 名一樣而**取值**不同:照舊出新版(沿用只認同值)
    tilted = _register(
        gateway,
        frozen,
        weights={**SAMPLE_WEIGHTS, "weight_momentum": "0.4", "weight_low_vol": "0.1"},
    ).param_set
    assert tilted.version_no == 2
    assert _version_count(store, FROZEN_PARAM_SET) == 2

    # 名一樣、取值一樣而**節奏**不同:一樣要出新版(節奏是參數集的一部分)
    monthly = _register(gateway, frozen, cadence="monthly").param_set
    assert monthly.version_no == 3
    assert monthly.rebalance_cadence == "monthly"

    # 登記那道門的簽名:別的票 import 得住,而且**參數集要自報已對齊還是示例**。
    # KARST-094 加了兩格:對齊依據一句與對齊日期,兩者都是標為「已對齊」時才要給
    # (標為示例時 D-038 已經替全部未對齊的取值講了那一句),所以 alignment 那格
    # 照舊無預設值,新加的兩格可以留空。
    signature = inspect.signature(register_setup)
    assert list(signature.parameters) == [
        "gateway", "contract", "strategy_name", "snapshot_id", "param_set_name",
        "values", "alignment", "description", "alignment_basis", "aligned_on",
    ]
    assert signature.parameters["alignment"].default is inspect.Parameter.empty
    with pytest.raises(ContractViolation, match="示例"):
        register_setup(
            gateway,
            _contract(),
            strategy_name=STRATEGY,
            snapshot_id=frozen["snapshot_id"],
            param_set_name="示例-沒有自報",
            values=_values(SAMPLE_WEIGHTS),
            alignment="",
        )


def test_registering_writes_the_alignment_mark_into_the_store(toy):
    """執行台登記參數集時,把那個申報寫入對齊標記旁表(D-038;KARST-094)。

    以前 ``alignment`` 只掛在記憶體的 ``Setup`` 上,庫內查不到哪個參數集是示例。
    """
    store = toy["store"]
    param_set_id = toy["param_set"].param_set_id

    alignment = store.param_set_alignment(param_set_id)
    assert alignment is not None
    assert alignment.mark == SAMPLE
    assert alignment.label == "示例"
    assert alignment.aligned_on is None
    assert alignment.basis  # 依據句不留空

    # 那一列有唯一入口的簽章,全庫核對清白。
    signed = {
        (row["table_name"], row["row_key"])
        for row in store.connection.execute(
            "SELECT table_name, row_key FROM gateway_write"
        )
    }
    assert ("param_set_alignment", f"{param_set_id}|1") in signed
    assert toy["gateway"].verify() == []


def test_registering_the_same_setup_twice_does_not_pile_up_marks(toy):
    """同名同值即沿用舊參數集版本,標記亦不應該每登記一次多一列。"""
    gateway = toy["gateway"]
    _register_toy(gateway)
    _register_toy(gateway)
    history = gateway.store.param_set_alignment_history(toy["param_set"].param_set_id)
    assert [one.seq_no for one in history] == [1]


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

