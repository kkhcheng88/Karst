"""KARST-056 驗收:因子分數與候選名單落成運行產物,選股快照與漏斗自此有真數據可畫。

三項驗收條件,一項一個測試,只證「行得通」,不掃邊界情況(照 test_runs.py、
test_web_strategy.py 同一套)。

第二個測試打的是**本機庫內真實的回測運行**——這正是要驗的那件事(規格 8.7:
頁面上不准有假數據)。庫或痕跡不在,就跳過,不用捏一組數頂上。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from karst import DefinitionStore, FormulaProcedure
from karst.engine.funnel import (
    STAGE_HELD,
    STAGE_SCOPE,
    STAGE_SELECTED,
    STAGE_TECHNICAL,
    STATUS_HELD,
    STATUS_OUT,
    STATUS_SELECTED,
    STATUS_WATCH,
    SelectionTraceBuilder,
)
from karst.runs import SELECTION_CANDIDATES, SELECTION_SCORES, RunStore, synthetic_simulation
from karst.store import FORMAL_RUN, SWEEP_RUN

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MOMENTUM = "動量·12-1 月"
MOMENTUM_PROCEDURE = FormulaProcedure(
    formula="close[-21] / close[-252] - 1",
    input_data_version="2026-08-27-a1b2c3d4e5f6",
)
STRATEGY = "趨勢波段"
PARAM_SET = "現役"
PERIOD = ("2020-01-01", "2026-06-30")
ENGINE = ("vectorbt-adapter", "0.1.0")


@pytest.fixture()
def store(tmp_path):
    with DefinitionStore.open(str(tmp_path / "karst.sqlite")) as opened:
        yield opened


@pytest.fixture()
def entities(store):
    return tuple(
        store.register_entity(kind="company", display_name=name, cik=cik)
        for name, cik in (("Apple Inc.", "320193"), ("Microsoft Corp.", "789019"))
    )


@pytest.fixture()
def snapshot_id(store):
    return store.register_snapshot(
        source="yfinance", taken_on="2026-06-30", content_hash="a1b2c3d4e5f67890"
    )


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
def runs(store, tmp_path):
    return RunStore(store, root=tmp_path / "runs")


class _WithTrace:
    """一份帶住選股痕跡的運行結果。形狀就是引擎交回來那個形狀。"""

    def __init__(self, simulation, entity_ids):
        self._simulation = simulation
        days = [str(day.date()) for day in simulation.equity_curve.index[:3]]
        builder = SelectionTraceBuilder()
        for index, day in enumerate(days):
            builder.stage(day, STAGE_SCOPE, entity_ids)
            builder.stage(day, STAGE_TECHNICAL, entity_ids[: 1 + index % 2])
            builder.stage(day, STAGE_SELECTED, entity_ids[:1])
            builder.score(day, MOMENTUM, dict(zip(entity_ids, (0.31, 0.12))))
        trace = builder.build()
        self.candidates = trace.candidates
        self.factor_scores = trace.factor_scores

    def __getattr__(self, name):
        return getattr(self._simulation, name)


def _simulation(entities, seed=7):
    return synthetic_simulation(
        start=PERIOD[0], end=PERIOD[1], entity_ids=entities, seed=seed
    )


def _record(runs, simulation, snapshot_id, **overrides):
    fields = {
        "strategy_name": STRATEGY,
        "param_set_name": PARAM_SET,
        "snapshot_id": snapshot_id,
        "engine_name": ENGINE[0],
        "engine_version": ENGINE[1],
        "origin": FORMAL_RUN,
    }
    fields.update(overrides)
    return runs.record_simulation(simulation, **fields)


# ---------------------------------------------------------------- 驗收一


def test_重跑後產物多出候選名單與逐股分數而運行編號逐位不變(
    runs, strategy, entities, snapshot_id
):
    """先落一次沒有痕跡的運行,再原樣重跑一次帶住痕跡的:編號一個位都不准變。"""
    plain = _record(runs, _simulation(entities), snapshot_id)
    assert runs.selection_kinds(plain.run_id) == (), "本來就不應該有痕跡"
    before = {
        kind: artifact.content_hash for kind, artifact in plain.artifacts.items()
    }

    again = _record(runs, _WithTrace(_simulation(entities), entities), snapshot_id)

    # 一、編號逐位不變,三條序列一個雜湊都沒有動——痕跡不入運行編號
    assert again.run_id == plain.run_id
    assert {k: a.content_hash for k, a in again.artifacts.items()} == before
    assert runs.verify_run(again.run_id) == ()

    # 二、產物真的多了兩份,而且核對得到(karst verify 才會清白)
    assert runs.selection_kinds(again.run_id) == (SELECTION_CANDIDATES, SELECTION_SCORES)
    assert runs.verify_selection(again.run_id) == ()
    directory = runs.root / again.run_id
    for name in ("candidates.parquet", "factor_scores.parquet", "selection.json"):
        assert (directory / name).is_file(), name

    # 三、讀得回,而且各層與分數都在
    candidates = runs.candidates(again.run_id)
    assert set(candidates["stage"]) == {STAGE_SCOPE, STAGE_TECHNICAL, STAGE_SELECTED}
    scores = runs.factor_scores(again.run_id)
    assert set(scores["score_name"]) == {MOMENTUM}
    assert set(scores["rank"]) == {1, 2}

    # 四、掃描格不收痕跡:一次掃描動輒四千格,格格存一份磁碟先爆,
    #     而掃描頁看的是格與格之間的成績差異,不看逐日名單
    cell = _record(
        runs,
        _WithTrace(_simulation(entities), entities),
        snapshot_id,
        origin=SWEEP_RUN,
        sweep_id="sweep-000000000000",
        engine_version="0.2.0",          # 換一格身份,免得撞正上面那次運行的編號
    )
    assert cell.run_id != again.run_id
    assert runs.selection_kinds(cell.run_id) == ()


# ---------------------------------------------------------------- 驗收二


def _live_reader():
    if not (PROJECT_ROOT / "karst.sqlite").is_file():
        pytest.skip("本機沒有定義庫,選股快照無從讀起")
    from karst.web.data import build_reader

    return build_reader(PROJECT_ROOT)


def test_選股快照有逐股分數漏斗畫齊有數據的各層(
):
    """打本機庫內真實的運行:漏斗每一層、每一隻的分數,全部由運行產物來。"""
    from karst.web import api_strategy

    reader = _live_reader()
    traced = None
    for name in reader.store.list_strategy_names():
        for record in reversed(reader.store.list_runs(name, origin=FORMAL_RUN)):
            if reader.series_missing(record):
                continue
            if reader.runs.selection_kinds(record.run_id):
                traced = record
                break
        if traced is not None:
            break
    if traced is None:
        pytest.skip("庫內未有留過選股痕跡的正式運行(重跑一次示例運行即有)")

    payload = api_strategy.picks(reader, {"run": [traced.run_id]})

    # 一、不再是「未有逐日因子分數」:分數名交得出,每一隻都有分數
    assert payload["notes"]["scoresAvailable"] is True
    assert payload["scoreNames"], "一個分數名都交不出"
    assert payload["decisionDate"] and payload["decisionDate"] <= payload["date"]
    scored = [row for row in payload["rows"] if row["scores"]]
    assert scored, "一隻都沒有分數"
    for row in scored:
        for name in row["scores"]:
            assert name in payload["scoreNames"]
            assert row["scores"][name]["value"] is not None
            assert row["scores"][name]["rank"] >= 1

    # 二、漏斗畫齊有數據的各層:比從前那兩層多,而且逐層收窄(到達該層的語意)
    keys = [layer["key"] for layer in payload["funnel"]]
    assert keys[0] == STAGE_SCOPE and keys[-1] == STAGE_HELD
    assert len(keys) > 2, "仍然只得範圍與持倉兩層"
    assert len(set(keys)) == len(keys)
    counts = [layer["count"] for layer in payload["funnel"]]
    assert counts == sorted(counts, reverse=True), counts

    # 三、每一行自己講得出到過哪幾層,而且與狀態對得上(詞彙表「選股快照」四個狀態)
    for row in payload["rows"]:
        assert row["stages"][0] == STAGE_SCOPE
        assert row["status"] in {STATUS_HELD, STATUS_SELECTED, STATUS_WATCH, STATUS_OUT}
        assert (row["status"] == STATUS_HELD) == (STAGE_HELD in row["stages"])
        # 到達的層一定是漏斗上真有的那幾層,不會冒出一層畫面畫不到的
        assert set(row["stages"]) <= set(keys)

    # 四、篩到某一層,剩下的就是到達了那一層的名單(畫面就是這樣篩)
    for index, layer in enumerate(payload["funnel"]):
        reached = [r for r in payload["rows"] if layer["key"] in r["stages"]]
        assert len(reached) == layer["count"], layer["key"]


# ---------------------------------------------------------------- 驗收三


def test_未有痕跡的舊運行照舊畫得出而且不虛構(runs, strategy, entities, snapshot_id):
    """沒有痕跡的運行不准報錯,亦不准變出一層假的關口出來。"""
    record = _record(runs, _simulation(entities), snapshot_id)

    assert runs.selection_kinds(record.run_id) == ()
    assert runs.verify_selection(record.run_id) == ()
    with pytest.raises(Exception):
        runs.candidates(record.run_id)

    # 空的一張不收:交一張沒有內容的痕跡等於甚麼都沒記
    with pytest.raises(Exception):
        runs.record_run(
            strategy_name=STRATEGY,
            param_set_name=PARAM_SET,
            snapshot_id=snapshot_id,
            engine_name=ENGINE[0],
            engine_version=ENGINE[1],
            equity_curve=_simulation(entities).equity_curve,
            holdings=_simulation(entities).holdings,
            orders=_simulation(entities).orders,
            origin=FORMAL_RUN,
            selection={SELECTION_CANDIDATES: pd.DataFrame(
                columns=["decision_date", "stage", "entity_id"]
            )},
        )


# ---------------------------------------------------------------- 痕跡本身


def test_分數面板留空的一格不會變成一個排最尾的假名次():
    """缺失=不參與(D-021 第 4 條):沒有分數就沒有那一列,不填 0、不排名。"""
    builder = SelectionTraceBuilder()
    builder.score_panel(
        "動量",
        ["2026-01-05", "2026-01-06"],
        [11, 12, 13],
        np.array([[0.3, np.nan, 0.1], [np.nan, np.nan, 0.9]]),
    )
    trace = builder.build()
    scores = trace.factor_scores

    assert len(scores) == 3, scores
    assert set(zip(scores["decision_date"], scores["entity_id"])) == {
        ("2026-01-05", 11), ("2026-01-05", 13), ("2026-01-06", 13),
    }
    first = scores[scores["decision_date"] == "2026-01-05"].set_index("entity_id")
    assert first.loc[11, "rank"] == 1 and first.loc[13, "rank"] == 2
    assert scores[scores["decision_date"] == "2026-01-06"]["rank"].tolist() == [1]
