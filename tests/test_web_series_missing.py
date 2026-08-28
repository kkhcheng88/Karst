"""KARST-057 驗收:登記還在、序列不在的那批運行,讀取層要標得出、隔得走。

背景:2026-08-28 倉根 ``data/`` 被誤清空,``karst.sqlite`` 完好——四千條運行
登記全部還在,它們指向的序列 parquet 與價格快照卻沒有了。定義表不可刪
(D-026),所以登記留住;讀取層要把這種運行標成「序列缺失運行 series-missing
run」,並且不列入正式運行清單與掃描清單。

(KARST-060:這個名本來寫作「過時運行(序列缺失)」,與詞彙表的「過時運行
stale run」撞名——一個講版本過時、一個講序列檔不在,兩者無關。)

每個測試對住一項行為,只證「行得通」,不掃邊界情況。

測試全程離線:價格快照走 ``StaticSource``(不連網),庫與序列根一律開在
``tmp_path``,一個字都不會碰到倉根那個定義庫與 ``data/``。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from karst import DefinitionStore, FormulaProcedure
from karst.data import StaticSource, UniverseMember, build_price_snapshot, read_universe
from karst.errors import NotFound
from karst.runs import RunStore, synthetic_simulation
from karst.store import FORMAL_RUN
from karst.web.data import RunReader

MOMENTUM = "動量·12-1 月"
MOMENTUM_PROCEDURE = FormulaProcedure(
    formula="close[-21] / close[-252] - 1",
    input_data_version="2026-08-27-a1b2c3d4e5f6",
)
STRATEGY = "趨勢波段"
PARAM_SET = "現役"
ENGINE = ("vectorbt-adapter", "0.1.0")

# 兩次運行:期間不同即兩個運行編號(期間是運行身份的五件之一,規格 7.4)。
PERIOD_START = "2024-01-02"
PERIOD_END = "2024-03-29"
SHORT_PERIOD_END = "2024-03-15"

CALENDAR_DAYS = tuple(
    day.strftime("%Y-%m-%d") for day in pd.bdate_range(PERIOD_START, PERIOD_END)
)
UNIVERSE = (
    UniverseMember("SPY", "etf", "SPDR S&P 500 ETF Trust"),
    UniverseMember("TESTCO", "company", "Test Company, Inc."),
)
CIK_MAP = {"TESTCO": "0000000042"}


def _bars() -> pd.DataFrame:
    """一份靜態日線,只為造得出一個真的價格快照目錄——不連網。"""
    rows: list[dict[str, object]] = []
    for index, day in enumerate(CALENDAR_DAYS):
        for ticker, base in (("SPY", 400.0), ("TESTCO", 50.0)):
            rows.append(
                {
                    "date": day,
                    "ticker": ticker,
                    "open": base + index,
                    "high": base + 1.0 + index,
                    "low": base - 1.0 + index,
                    "close": base + 0.5 + index,
                    "volume": 1_000_000.0 + index,
                }
            )
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# 造數:一律開在 tmp_path
# ----------------------------------------------------------------------


@pytest.fixture()
def snapshot_root(tmp_path):
    return tmp_path / "snapshots"


@pytest.fixture()
def runs_root(tmp_path):
    return tmp_path / "runs"


@pytest.fixture()
def store(tmp_path):
    with DefinitionStore.open(str(tmp_path / "karst.sqlite")) as opened:
        yield opened


@pytest.fixture()
def snapshot(store, snapshot_root):
    """一個真的價格快照:目錄落在 ``snapshot_root``,登記落庫。"""
    return build_price_snapshot(
        store,
        start=PERIOD_START,
        end=PERIOD_END,
        universe=UNIVERSE,
        source=StaticSource(_bars(), name="static-test"),
        root=snapshot_root,
        cik_map=CIK_MAP,
        taken_on="2026-08-28",
    )


@pytest.fixture()
def entities(store, snapshot, snapshot_root):
    """快照一併凍結的宇宙名單裡那批實體編號。"""
    frame = read_universe(store, snapshot.snapshot_id, root=snapshot_root)
    return tuple(int(entity_id) for entity_id in frame["entity_id"])


@pytest.fixture()
def strategy(store, entities):
    store.register_factor(MOMENTUM, scale_kind="cardinal", procedure=MOMENTUM_PROCEDURE)
    version = store.register_strategy(
        STRATEGY, strategy_type="technical", factor_refs=[MOMENTUM]
    )
    store.register_param_set(
        STRATEGY,
        param_set_name=PARAM_SET,
        rebalance_cadence="monthly",
        values={"top_n": "10", "direction": "high"},
    )
    return version


@pytest.fixture()
def runs(store, runs_root):
    return RunStore(store, root=runs_root)


@pytest.fixture()
def reader(store, runs_root, snapshot_root):
    return RunReader(store, runs_root=runs_root, snapshot_root=snapshot_root)


def _record(runs, entities, snapshot_id, *, period_end=PERIOD_END):
    """落一次正式運行的痕(造法同 tests/test_runs.py)。"""
    return runs.record_simulation(
        synthetic_simulation(
            start=PERIOD_START, end=period_end, entity_ids=entities, seed=7
        ),
        strategy_name=STRATEGY,
        param_set_name=PARAM_SET,
        snapshot_id=snapshot_id,
        engine_name=ENGINE[0],
        engine_version=ENGINE[1],
        origin=FORMAL_RUN,
        period_start=PERIOD_START,
        period_end=period_end,
    )


def _delete_series(runs, run_id, kind):
    """把其中一條序列的 parquet 由磁碟刪走,登記一個字不動。"""
    path = Path(runs.get_run(run_id).artifact(kind).path)
    path.unlink()
    return path


# ----------------------------------------------------------------------
# 行為一:RunStore.missing_series 認得出哪一條序列不在磁碟上
# ----------------------------------------------------------------------


def test_序列齊全時回空刪走一份之後報得出是哪一種(runs, strategy, entities, snapshot):
    record = _record(runs, entities, snapshot.snapshot_id)

    # 三份 parquet 都在:一條都不缺
    assert runs.missing_series(record.run_id) == ()
    assert runs.series_intact(record.run_id) is True

    # 刪走逐日淨值那一份(正是誤清空 data/ 那一下的樣子)
    _delete_series(runs, record.run_id, "equity")

    assert "equity" in runs.missing_series(record.run_id)
    assert runs.series_intact(record.run_id) is False


# ----------------------------------------------------------------------
# 行為二:list_runs 濾走序列缺失那批,但登記仍然查得回
# ----------------------------------------------------------------------


def test_清單濾走序列缺失的運行而登記照舊查得回(reader, runs, strategy, entities, snapshot):
    intact = _record(runs, entities, snapshot.snapshot_id)
    broken = _record(runs, entities, snapshot.snapshot_id, period_end=SHORT_PERIOD_END)
    assert intact.run_id != broken.run_id

    # 未刪之前:兩條都畫得出,兩條都在正式運行清單裡
    before = reader.list_runs()
    assert {item["runId"] for item in before["runs"]} == {intact.run_id, broken.run_id}
    assert before["total"] == 2
    assert before["missingSeries"] == 0

    # 刪走其中一條的逐日淨值
    _delete_series(runs, broken.run_id, "equity")

    after = reader.list_runs()
    listed = {item["runId"] for item in after["runs"]}
    assert broken.run_id not in listed, "序列缺失那條不應該再出現在正式運行清單"
    assert listed == {intact.run_id}, "序列齊全那條要照樣列得出"
    # total 只算留低那批,被濾走那批另報一個數
    assert after["total"] == 1
    assert after["shown"] == 1
    assert after["missingSeries"] == 1

    # 定義表沒有被刪:登記仍然查得回,來歷、期間、快照一個字沒變
    still_registered = {record.run_id for record in runs.list_runs()}
    assert broken.run_id in still_registered
    again = runs.get_run(broken.run_id)
    assert again.origin == FORMAL_RUN
    assert (again.period_start, again.period_end) == (PERIOD_START, SHORT_PERIOD_END)
    assert again.snapshot_id == snapshot.snapshot_id


# ----------------------------------------------------------------------
# 行為三:get_run 對序列缺失那條拋 NotFound,訊息講明它是什麼
# ----------------------------------------------------------------------


def test_取序列缺失的運行拋出序列缺失運行(reader, runs, strategy, entities, snapshot):
    record = _record(runs, entities, snapshot.snapshot_id)
    _delete_series(runs, record.run_id, "equity")

    with pytest.raises(NotFound) as raised:
        reader.get_run(record.run_id)

    message = str(raised.value)
    # KARST-060:這句訊息本來寫「過時運行(序列缺失)」,與詞彙表的「過時運行」
    # (版本過時)撞名。名一律改為「序列缺失運行」,舊名不准再出現。
    assert "序列缺失運行" in message
    assert "過時運行" not in message
    assert record.run_id in message
