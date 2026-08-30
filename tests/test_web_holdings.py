"""KARST-080 驗收:每次運行的持股彙總 API(D-037)。

「策略詳情頁的『因子分布』改『持股分布』」那一票新增的端點
``karst.web.api_strategy.holdings()``——直接讀 ``RunStore.holdings()``(逐日
持倉長表)與 ``RunStore.orders()``(逐筆成交)現算,不另建快取表。

這裡只驗票面明文要求的那一項:兩隻股票各一筆完整交易(一買一賣),累計
報酬 = 該股票已平倉損益 ÷ 該次運行起始資金,算對。不掃邊界情況(D-020
驗收從簡守則同一套)。

測試全程離線:價格快照走 ``StaticSource``(不連網),庫與序列根一律開在
``tmp_path``;直接呼叫 ``holdings()`` 這個函式,不另起 HTTP 伺服器
——與 ``api_strategy.py`` 其餘端點同一種可測法。
"""

from __future__ import annotations

import pandas as pd
import pytest

from karst import FormulaProcedure
from karst.data import StaticSource, UniverseMember, build_price_snapshot, read_universe
from karst.gateway import Gateway
from karst.runs import RunStore
from karst.store import FORMAL_RUN
from karst.web import api_strategy
from karst.web.data import RunReader

MOMENTUM = "動量·12-1 月"
MOMENTUM_PROCEDURE = FormulaProcedure(
    formula="close[-21] / close[-252] - 1",
    input_data_version="2026-08-27-a1b2c3d4e5f6",
)
STRATEGY = "測試策略·持股分布"
PARAM_SET = "現役"
ENGINE = ("vectorbt-adapter", "0.1.0")

PERIOD_START = "2024-01-02"
PERIOD_END = "2024-01-10"

CALENDAR_DAYS = tuple(
    day.strftime("%Y-%m-%d") for day in pd.bdate_range(PERIOD_START, PERIOD_END)
)
# 兩隻股票,各自造夠幾日持倉、各一筆完整交易(一買一賣)。SPY 是主日曆代號
# (``build_price_snapshot`` 硬性要求宇宙名單內有它),不是這次運行持有的標的。
UNIVERSE = (
    UniverseMember("SPY", "etf", "SPDR S&P 500 ETF Trust"),
    UniverseMember("AAA", "company", "AAA Test Co."),
    UniverseMember("BBB", "company", "BBB Test Co."),
)
CIK_MAP = {"AAA": "0000000001", "BBB": "0000000002"}

STARTING_CAPITAL = 100_000.0


def _bars() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for index, day in enumerate(CALENDAR_DAYS):
        for ticker, base in (("SPY", 400.0), ("AAA", 100.0), ("BBB", 50.0)):
            rows.append(
                {
                    "date": day,
                    "ticker": ticker,
                    "open": base,
                    "high": base + 1.0,
                    "low": base - 1.0,
                    "close": base,
                    "volume": 1_000_000.0,
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture()
def snapshot_root(tmp_path):
    return tmp_path / "snapshots"


@pytest.fixture()
def runs_root(tmp_path):
    return tmp_path / "runs"


@pytest.fixture()
def store(tmp_path):
    # 快照登記要經唯一入口簽章(KARST-087),所以庫身由那道門開出來
    with Gateway.open(str(tmp_path / "karst.sqlite")).store as opened:
        yield opened


@pytest.fixture()
def snapshot(store, snapshot_root):
    return build_price_snapshot(
        store,
        start=PERIOD_START,
        end=PERIOD_END,
        universe=UNIVERSE,
        source=StaticSource(_bars(), name="static-test"),
        root=snapshot_root,
        cik_map=CIK_MAP,
        taken_on="2026-08-29",
    )


@pytest.fixture()
def entities(store, snapshot, snapshot_root):
    """(AAA 的實體編號, BBB 的實體編號)——與 ``UNIVERSE`` 同一個次序。"""
    frame = read_universe(store, snapshot.snapshot_id, root=snapshot_root)
    by_symbol = dict(zip(frame["ticker"], frame["entity_id"]))
    return int(by_symbol["AAA"]), int(by_symbol["BBB"])


@pytest.fixture()
def strategy(store, entities):
    store.register_factor(MOMENTUM, scale_kind="cardinal", procedure=MOMENTUM_PROCEDURE)
    version = store.register_strategy(
        STRATEGY,
        strategy_type="technical",
        layer="stock",
        exit_governance="continuation",
        factor_refs=[MOMENTUM],
    )
    store.register_param_set(
        STRATEGY,
        param_set_name=PARAM_SET,
        rebalance_cadence="monthly",
        values={"top_n": "2", "direction": "high"},
    )
    return version


@pytest.fixture()
def runs(store, runs_root):
    return RunStore(store, root=runs_root)


@pytest.fixture()
def reader(store, runs_root, snapshot_root):
    return RunReader(store, runs_root=runs_root, snapshot_root=snapshot_root)


@pytest.fixture()
def record(runs, entities, snapshot):
    """一次運行,兩隻股票各一筆完整交易,持股天數 AAA 多過 BBB。

    AAA:買 10 股 @100,賣出 @110 -> 已平倉損益 +100
    BBB:買 5 股 @50,賣出 @40   -> 已平倉損益 -50
    起始資金(``equity_curve`` 首日)= 100000.0,所以預期累計報酬:
    AAA +0.10%、BBB -0.05%。
    """
    aaa_id, bbb_id = entities
    index = pd.DatetimeIndex(CALENDAR_DAYS)
    equity = pd.Series([STARTING_CAPITAL] * len(index), index=index, name="equity")

    day0, day1, day2, day3 = CALENDAR_DAYS[0], CALENDAR_DAYS[1], CALENDAR_DAYS[2], CALENDAR_DAYS[3]

    holdings = pd.DataFrame(
        [
            # AAA 持有四日(day0~day3),BBB 只持有兩日(day0~day1)——
            # 持有日數排名 AAA 排前。
            {"date": day0, "entity_id": aaa_id, "shares": 10.0},
            {"date": day1, "entity_id": aaa_id, "shares": 10.0},
            {"date": day2, "entity_id": aaa_id, "shares": 10.0},
            {"date": day3, "entity_id": aaa_id, "shares": 10.0},
            {"date": day0, "entity_id": bbb_id, "shares": 5.0},
            {"date": day1, "entity_id": bbb_id, "shares": 5.0},
        ]
    )
    orders = pd.DataFrame(
        [
            {"trade_date": day0, "entity_id": aaa_id, "side": "buy", "shares": 10.0, "price": 100.0, "fees": 0.0},
            {"trade_date": day3, "entity_id": aaa_id, "side": "sell", "shares": 10.0, "price": 110.0, "fees": 0.0},
            {"trade_date": day0, "entity_id": bbb_id, "side": "buy", "shares": 5.0, "price": 50.0, "fees": 0.0},
            {"trade_date": day1, "entity_id": bbb_id, "side": "sell", "shares": 5.0, "price": 40.0, "fees": 0.0},
        ]
    )

    return runs.record_run(
        strategy_name=STRATEGY,
        param_set_name=PARAM_SET,
        snapshot_id=snapshot.snapshot_id,
        engine_name=ENGINE[0],
        engine_version=ENGINE[1],
        equity_curve=equity,
        holdings=holdings,
        orders=orders,
        origin=FORMAL_RUN,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )


def test_兩隻股票各一筆交易累計報酬算對(reader, strategy, entities, record):
    aaa_id, bbb_id = entities

    payload = api_strategy.holdings(reader, {"run": [record.run_id]})

    assert payload["runId"] == record.run_id
    assert payload["rankBasis"] == "holdingDays"
    assert payload["startingCapital"] == pytest.approx(STARTING_CAPITAL)
    # 現有實體登記冊沒有行業欄:這裡只做前十股票 + 累計報酬,行業佔比
    # 照票面指示交回 None 並在 notes 講明,不假裝有資料。
    assert payload["sectorBreakdown"] is None
    assert payload["notes"]["sectorAvailable"] is False

    by_entity = {row["entityId"]: row for row in payload["topHoldings"]}
    assert set(by_entity) == {aaa_id, bbb_id}

    aaa_row = by_entity[aaa_id]
    assert aaa_row["symbol"] == "AAA"
    assert aaa_row["holdingDays"] == 4
    assert aaa_row["realizedProfit"] == pytest.approx(100.0)
    assert aaa_row["cumulativeReturnPct"] == pytest.approx(0.10, abs=1e-9)

    bbb_row = by_entity[bbb_id]
    assert bbb_row["symbol"] == "BBB"
    assert bbb_row["holdingDays"] == 2
    assert bbb_row["realizedProfit"] == pytest.approx(-50.0)
    assert bbb_row["cumulativeReturnPct"] == pytest.approx(-0.05, abs=1e-9)

    # 持有日數排名:AAA(4 日)排在 BBB(2 日)前面
    ordered_symbols = [row["symbol"] for row in payload["topHoldings"]]
    assert ordered_symbols == ["AAA", "BBB"]


def test_沒帶run參數要清楚拒收(reader):
    from karst.errors import ContractViolation

    with pytest.raises(ContractViolation):
        api_strategy.holdings(reader, {})
