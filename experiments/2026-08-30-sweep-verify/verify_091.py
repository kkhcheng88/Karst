"""KARST-091 核對:掃描搬入執行台之後,逐格的運行編號與參數集**逐位不變**。

跑法::

    python experiments/2026-08-30-sweep-verify/verify_091.py

做三件事,全部在 ``karst.sqlite`` 的**一份複本**上做——正本一個字都不碰:

1. **逐格重算。** 每一幅落了檔的掃描,逐格由**策略合約的參數規格**重新砌一次參數集
   的名與逐格文字,再重算一次運行編號,與當日落檔那個編號逐位比對。編號對得上,即
   代表新的 ``Executor.sweep`` 走同一幅格會**查得回舊運行、一次引擎都不碰**;對不上
   就是白跑幾千格。這比「再跑一次看看」誠實:引擎在不在,編號都要對得上。

2. **因子輪動補一次像樣的首次登記。** 以前輪動借用因子混合那份登記程序落庫
   (``ensure_factor_rotation_setup`` 直接叫 ``ensure_factor_mix_setup``),所以庫裡
   那個策略版本其實是用混合的合約寫出來的。現在用 ``FactorRotationContract`` 正式
   登記一次,並如實報告:有沒有出新版本、有幾多次運行因此變成**過時運行**。

3. **正式運行的數目一個不變。** 掃描那條路只寫掃描格;正式運行是另一條路,本票
   一個字都不應該碰到它。

輸出:``結果.json``(機器讀)與本檔旁邊的 ``報告.md``(人讀)。
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from karst.engine.contracts import TradingCosts  # noqa: E402
from karst.executor.contract import cost_inputs, cost_slug  # noqa: E402
from karst.gateway.service import Gateway  # noqa: E402
from karst.strategies.factor_mix import (  # noqa: E402
    CADENCE_PARAM,
    FACTOR_ETF_SLEEVES,
    FactorMixContract,
)
from karst.strategies.factor_rotation import (  # noqa: E402
    DRIVER_KEY,
    DRIVER_PARAMETERS,
    MACRO_SERIES_KEY,
    MACRO_SERIES_SEPARATOR,
    MACRO_SNAPSHOT_KEY,
    WARMUP_BARS_KEY,
    WARMUP_PREFIX,
    FactorRotationContract,
    macro_series_needed,
)

ROTATION_STRATEGY = "因子輪動(ETF 版)"
MIX_STRATEGY = "因子混合(ETF 版)"

# 這兩格是帳戶設定,不入參數集亦不入運行編號;寫在這裡只為砌得出一份跑得動的合約。
INITIAL_CASH = 100_000.0
FEES = 0.0


# ----------------------------------------------------------------------
# 由一次舊運行倒查這幅掃描的來歷
# ----------------------------------------------------------------------


def _costs_of(values: dict[str, str]) -> TradingCosts | None:
    keys = ("fee_model", "fee_rate", "slippage")
    present = [key for key in keys if key in values]
    if not present:
        return None
    if len(present) != len(keys):
        raise SystemExit(f"成本三格不齊:只有 {present}")
    return TradingCosts(
        fee_model=str(values["fee_model"]).strip(),
        fee_rate=float(values["fee_rate"]),
        slippage_fraction=float(values["slippage"]),
    )


def _typed_like(sample: Any, text: Any) -> Any:
    """照參數集記住那一格的寫法決定型別:記住的沒有小數點,就當整數。

    型別要對得住——``6`` 與 ``6.0`` 砌出來的參數集名不同,一不同就當成另一格。
    """
    raw = str(text).strip()
    hint = str(sample).strip()
    try:
        number = float(raw)
    except ValueError:
        return raw
    if "." not in hint and "e" not in hint.lower() and number.is_integer():
        return int(number)
    return number


def _contract_for(strategy_name: str, values: dict[str, str], market_ticker: str | None):
    """由參數集那一組取值砌回當日跑那一格用的策略合約。"""
    costs = _costs_of(values)
    if strategy_name == MIX_STRATEGY:
        contract = FactorMixContract(
            sleeves=FACTOR_ETF_SLEEVES,
            initial_cash=INITIAL_CASH,
            fees=FEES,
            costs=costs,
        )
        return contract, costs, dict(cost_inputs(costs))

    driver = str(values.get(DRIVER_KEY) or "").strip()
    if driver not in DRIVER_PARAMETERS:
        raise SystemExit(f"認不得驅動器 {driver!r}")
    warmup_weights = {
        key[len(WARMUP_PREFIX):]: float(text)
        for key, text in values.items()
        if key.startswith(WARMUP_PREFIX) and key != WARMUP_BARS_KEY
    }
    macro_id = str(values.get(MACRO_SNAPSHOT_KEY) or "").strip() or None
    contract = FactorRotationContract(
        driver_key=driver,
        sleeves=FACTOR_ETF_SLEEVES,
        warmup_bars=int(float(values[WARMUP_BARS_KEY])),
        warmup_weights=warmup_weights,
        market_ticker=market_ticker,
        initial_cash=INITIAL_CASH,
        fees=FEES,
        costs=costs,
        macro_snapshot_id=macro_id,
    )
    base = {
        DRIVER_KEY: driver,
        WARMUP_BARS_KEY: int(float(values[WARMUP_BARS_KEY])),
        **{f"{WARMUP_PREFIX}{key}": value for key, value in warmup_weights.items()},
        **cost_inputs(costs),
    }
    if macro_id:
        base[MACRO_SNAPSHOT_KEY] = macro_id
        base[MACRO_SERIES_KEY] = MACRO_SERIES_SEPARATOR.join(macro_series_needed(driver))
    return contract, costs, base


def _prefix_of(param_set_name: str, tail: str) -> str:
    if tail and param_set_name.endswith(tail):
        return param_set_name[: len(param_set_name) - len(tail)]
    raise SystemExit(f"倒推不出前綴:「{param_set_name}」不是以「{tail}」收尾")


# ----------------------------------------------------------------------
# 一幅掃描
# ----------------------------------------------------------------------


def check_sweep(store: Any, directory: Path) -> dict[str, Any]:
    frame = pd.read_csv(directory / "掃描表.csv", encoding="utf-8-sig")
    if "run_id" not in frame.columns:
        return {"sweep": str(directory), "skipped": "掃描表沒有 run_id 一欄"}

    sample_run = store.get_run(str(frame["run_id"].iloc[0]))
    strategy_name = sample_run.strategy_name
    values = dict(sample_run.param_values)

    market = None
    summary_path = directory / "summary.json"
    if summary_path.exists():
        market = json.loads(summary_path.read_text(encoding="utf-8")).get("market_ticker")
    if market is None and strategy_name == ROTATION_STRATEGY:
        market = "SPY"

    contract, costs, base_values = _contract_for(strategy_name, values, market)
    spec = contract.param_spec()

    # 軸 = 掃描表裡那幾條參數欄(規格認得的那幾格,按表上的次序)
    known = {field.name for field in spec.fields}
    axes = [column for column in frame.columns if column in known]
    if not axes:
        return {"sweep": str(directory), "skipped": "掃描表認不出任何一條軸"}

    suffix = cost_slug(costs)
    sample_point = [
        (axis, _typed_like(values.get(axis, sample_run.rebalance_cadence), frame[axis].iloc[0]))
        for axis in axes
    ]
    checked = spec.validate({**base_values, **dict(sample_point)})
    tail = "-".join(spec.field(axis).slug(checked[axis]) for axis, _ in sample_point) + suffix
    prefix = _prefix_of(sample_run.param_set_name, tail)

    cells = 0
    name_ok = 0
    values_ok = 0
    id_ok = 0
    problems: list[str] = []

    for row in frame.itertuples(index=False):
        record = store.get_run(str(getattr(row, "run_id")))
        point = [
            (axis, _typed_like(values.get(axis, sample_run.rebalance_cadence), getattr(row, axis)))
            for axis in axes
        ]
        checked = spec.validate({**base_values, **dict(point)})
        cadence, texts = spec.as_param_set({**base_values, **dict(point)})
        name = prefix + "-".join(
            spec.field(axis).slug(checked[axis]) for axis, _ in point
        ) + suffix

        cells += 1
        if name == record.param_set_name:
            name_ok += 1
        elif len(problems) < 5:
            problems.append(f"參數集名對不上:算出 {name},落檔是 {record.param_set_name}")

        if dict(record.param_values) == texts and str(record.rebalance_cadence) == str(cadence):
            values_ok += 1
        elif len(problems) < 5:
            problems.append(
                f"{record.param_set_name} 的取值對不上:算出 {texts}/{cadence},"
                f"落檔是 {dict(record.param_values)}/{record.rebalance_cadence}"
            )

        fingerprint = store.run_fingerprint(
            strategy_name=strategy_name,
            param_set_name=record.param_set_name,
            period_start=record.period_start,
            period_end=record.period_end,
            snapshot_id=record.snapshot_id,
            engine_name=record.engine_name,
            engine_version=record.engine_version,
            strategy_version_no=record.strategy_version_no,
            param_set_version_no=record.param_set_version_no,
            factor_version_ids=tuple(f.factor_version_id for f in record.factors) or None,
        )
        if store.run_id_for(fingerprint) == record.run_id:
            id_ok += 1
        elif len(problems) < 5:
            problems.append(f"運行編號重算對不上:{record.run_id}")

    return {
        "sweep": str(directory.relative_to(ROOT)).replace("\\", "/"),
        "strategy": strategy_name,
        "driver": values.get(DRIVER_KEY),
        "costed": costs is not None and not costs.is_zero,
        "axes": axes,
        "cells": cells,
        "param_set_name_matches": name_ok,
        "param_set_values_match": values_ok,
        "run_id_matches": id_ok,
        "problems": problems,
    }


# ----------------------------------------------------------------------
# 因子輪動的首次登記
# ----------------------------------------------------------------------


def register_rotation(gateway: Any) -> dict[str, Any]:
    from karst.executor.executor import SAMPLE, register_setup

    store = gateway.store
    before = store.get_strategy_version(ROTATION_STRATEGY)
    runs_before = [
        row["run_id"]
        for row in store._conn.execute(
            "SELECT run_id FROM backtest_run WHERE strategy_version_id = ?",
            (before.strategy_version_id,),
        )
    ]
    stale_before = sum(1 for run_id in runs_before if store.run_stale_reasons(run_id))

    sample = store.get_run(runs_before[0])
    values = dict(sample.param_values)
    driver = str(values.get(DRIVER_KEY) or "").strip()
    contract = FactorRotationContract.for_setup(driver)

    setup = register_setup(
        gateway,
        contract,
        strategy_name=ROTATION_STRATEGY,
        snapshot_id=sample.snapshot_id,
        param_set_name="登記-因子輪動-起步",
        values={
            **{
                key: _typed_like(values[key], values[key])
                for key in (DRIVER_KEY, *DRIVER_PARAMETERS[driver], WARMUP_BARS_KEY)
            },
            **{
                key: float(text)
                for key, text in values.items()
                if key.startswith(WARMUP_PREFIX) and key != WARMUP_BARS_KEY
            },
            CADENCE_PARAM: sample.rebalance_cadence,
        },
        alignment=SAMPLE,
        description="因子輪動(ETF 版)的首次正式登記:以前借用因子混合那份登記程序落庫",
    )

    after = store.get_strategy_version(ROTATION_STRATEGY)
    stale_after = sum(1 for run_id in runs_before if store.run_stale_reasons(run_id))
    return {
        "version_before": before.version_no,
        "version_after": after.version_no,
        "new_version": after.version_no != before.version_no,
        "registered_version": setup.strategy.version_no,
        "factor_refs_before": sorted(f"{f.name}@{f.version_no}" for f in before.factors),
        "factor_refs_after": sorted(f"{f.name}@{f.version_no}" for f in after.factors),
        "runs_on_old_version": len(runs_before),
        "stale_before": stale_before,
        "stale_after": stale_after,
        "newly_stale": stale_after - stale_before,
    }


def formal_runs(store: Any) -> int:
    row = store._conn.execute(
        "SELECT COUNT(*) FROM backtest_run r WHERE r.origin = 'formal' "
        "AND NOT EXISTS (SELECT 1 FROM backtest_run_retraction x WHERE x.run_id = r.run_id)"
    ).fetchone()
    return int(row[0])


# ----------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(ROOT / "karst.sqlite"))
    parser.add_argument(
        "--register", action="store_true",
        help="連因子輪動的首次登記一齊做(在複本上做,正本不變)",
    )
    args = parser.parse_args()

    work = Path(tempfile.mkdtemp(prefix="karst-091-"))
    copy = work / "karst.sqlite"
    shutil.copy2(args.db, copy)
    key = Path(args.db).with_name(".gateway-key")
    if key.exists():
        shutil.copy2(key, work / ".gateway-key")

    report: dict[str, Any] = {"database": str(copy), "sweeps": []}
    with Gateway.open(str(copy), writer="KARST-091-verify") as gateway:
        store = gateway.store
        report["formal_runs_before"] = formal_runs(store)
        for directory in sorted(ROOT.glob("experiments/**/掃描表.csv")):
            outcome = check_sweep(store, directory.parent)
            report["sweeps"].append(outcome)
            label = outcome.get("sweep", outcome.get("skipped"))
            print(
                f"{label}: {outcome.get('cells', 0)} 格,"
                f"名 {outcome.get('param_set_name_matches', 0)}、"
                f"值 {outcome.get('param_set_values_match', 0)}、"
                f"編號 {outcome.get('run_id_matches', 0)}"
            )
        if args.register:
            report["rotation_registration"] = register_rotation(gateway)
            print("輪動首次登記:", report["rotation_registration"])
        report["formal_runs_after"] = formal_runs(store)

    total = sum(item.get("cells", 0) for item in report["sweeps"])
    matched = sum(item.get("run_id_matches", 0) for item in report["sweeps"])
    report["total_cells"] = total
    report["total_run_id_matches"] = matched
    report["all_run_ids_unchanged"] = total == matched and total > 0
    report["formal_runs_unchanged"] = (
        report["formal_runs_before"] == report["formal_runs_after"]
    )

    out = Path(__file__).with_name("結果.json")
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"\n合共 {total} 格,運行編號對得上 {matched} 格。落檔:{out}")
    return 0 if report["all_run_ids_unchanged"] and report["formal_runs_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
