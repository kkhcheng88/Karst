"""KARST-091 冒煙:真的走一次 ``Executor.sweep``,看批次登記落不落到庫、驗不驗得清白。

跑法::

    python experiments/2026-08-30-sweep-verify/smoke_091.py

在 ``karst.sqlite`` 的**一份複本**上,挑一幅已經跑過的因子輪動掃描重跑一次。因為
逐格的運行編號一位不變(見 ``verify_091.py``),執行台會逐格查得回舊運行,**一次
引擎都不會碰**——所以這次冒煙只花讀庫與算指標的時間,而它驗的正是要驗那三件:

1. 逐格的運行編號與當日落檔那張掃描表**逐格相同**;
2. 逐格的裁決與當日那張判讀表**逐格相同**;
3. 收尾寫得出一列**批次登記**,而且經唯一入口簽了名——``karst verify`` 見到它
   在「定義」那一欄,清白;之後再直接寫庫塞一列進去,``verify`` 就要點名。
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from karst.executor import SAMPLE, BatchReport, Executor  # noqa: E402
from karst.gateway.service import Gateway  # noqa: E402
from karst.runs import RunStore  # noqa: E402
from karst.sweep.factor_rotation import rotation_grid  # noqa: E402

from verify_091 import _contract_for, _prefix_of, _typed_like  # noqa: E402

SWEEP_DIR = ROOT / "experiments/2026-08-28-factor-rotation-drivers/results/factor_momentum"
RISK_FREE = 0.04

# 判讀目標與三條門檻不准在這裡自己估——照當日那幅掃描落檔的 summary.json 讀回來,
# 否則「判讀逐格相同」驗的只是我猜得準不準,不是執行台對不對。
SUMMARY = json.loads((SWEEP_DIR.parent / "summary.json").read_text(encoding="utf-8"))
OBJECTIVE = str(SUMMARY["objective"])
THRESHOLDS = dict(SUMMARY["thresholds"])

# 當日那幅掃描判讀了兩次:一次用 summary 那個主目標,一次用最大回撤。落檔那張
# ``判讀表.csv`` 是**後者**(它的 value 欄逐格等於掃描表的 max_drawdown,已核對)。
# 要逐格對得上,就要用同一個目標判,否則對的是兩件不同的東西。
FILED_VERDICT_OBJECTIVE = "max_drawdown"

# 掃描表逐格落了檔的指標欄,對得上才算「數字重現」,不是只有編號重現。
METRIC_COLUMNS_FILED = ("annual_return", "max_drawdown", "annual_excess_SPY", "annual_excess_QQQ")


def _first_seen(series: Any) -> list:
    """照當日落檔的行序取軸值,不排序——排序會改軸上的鄰居,連帶改裁決。"""
    seen: list = []
    for value in series:
        if value not in seen:
            seen.append(value)
    return seen


def price_panel(store: Any, snapshot_id: str) -> Any:
    from karst.data import read_price_panel
    from karst.engine.contracts import PricePanel

    root = ROOT / "data" / "snapshots"
    opens = read_price_panel(store, snapshot_id, field="open", root=root).dropna(how="any")
    closes = read_price_panel(store, snapshot_id, field="close", root=root).dropna(how="any")
    common = opens.index.intersection(closes.index)
    return PricePanel.from_frames(open=opens.loc[common], close=closes.loc[common])


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="karst-091-smoke-"))
    copy = work / "karst.sqlite"
    shutil.copy2(ROOT / "karst.sqlite", copy)
    key = (ROOT / ".gateway-key")
    if key.exists():
        shutil.copy2(key, work / ".gateway-key")

    filed = pd.read_csv(SWEEP_DIR / "掃描表.csv", encoding="utf-8-sig")
    filed_verdicts = pd.read_csv(SWEEP_DIR / "判讀表.csv", encoding="utf-8-sig")

    report: dict[str, Any] = {"sweep": str(SWEEP_DIR.relative_to(ROOT)).replace("\\", "/")}
    with Gateway.open(str(copy), writer="KARST-091-smoke") as gateway:
        store = gateway.store
        sample = store.get_run(str(filed["run_id"].iloc[0]))
        values = dict(sample.param_values)
        contract, costs, base_values = _contract_for(sample.strategy_name, values, "SPY")
        spec = contract.param_spec()
        axes = [column for column in filed.columns if column in {f.name for f in spec.fields}]

        grid = rotation_grid(
            contract.driver_key,
            values={
                name: [_typed_like(values.get(name, ""), v) for v in _first_seen(filed[name])]
                for name in axes
                if name != "cadence"
            },
            cadences=[str(v) for v in _first_seen(filed["cadence"])],
        )
        first = [
            (axis, _typed_like(values.get(axis, sample.rebalance_cadence), filed[axis].iloc[0]))
            for axis in axes
        ]
        checked = spec.validate({**base_values, **dict(first)})
        tail = "-".join(spec.field(axis).slug(checked[axis]) for axis, _ in first)
        prefix = _prefix_of(sample.param_set_name, tail)

        executor = Executor(gateway, RunStore(store, root=ROOT / "data" / "runs"),
                            snapshot_root=ROOT / "data" / "snapshots")
        setup = executor.setup_from(
            contract,
            strategy_name=sample.strategy_name,
            snapshot_id=sample.snapshot_id,
            param_set_name=sample.param_set_name,
            alignment=SAMPLE,
            strategy_version_no=sample.strategy_version_no,
            param_set_version_no=sample.param_set_version_no,
        )
        outcome = executor.sweep(
            contract,
            setup=setup,
            grid=grid,
            panel=price_panel(store, sample.snapshot_id),
            period=(sample.period_start, sample.period_end),
            engine_version=sample.engine_version,
            risk_free_rate=RISK_FREE,
            sweep_id="experiments/2026-08-30-sweep-verify/冒煙",
            param_set_prefix=prefix,
            param_set_suffix="",
            base_values=base_values,
            objective=OBJECTIVE,
            min_trades=int(THRESHOLDS["min_trades"]),
            lonely_peak_margin=float(THRESHOLDS["lonely_peak_margin"]),
            plateau_quantile=float(THRESHOLDS["plateau_quantile"]),
            report=BatchReport(directory=work / "報告", title="KARST-091 冒煙"),
            engine_name=sample.engine_name,
        )

        # 同一個掃描編號、同一幅格再掃一次:批次登記只加不改,所以第二次應該**重用**
        # 那一列,不是多寫一列、更加不是撞「內容不同」被拒收。報告要逐位相同才過得到
        # 這一關,所以這一步同時驗住報告不含產出時刻與耗時。
        again = executor.sweep(
            contract,
            setup=setup,
            grid=grid,
            panel=price_panel(store, sample.snapshot_id),
            period=(sample.period_start, sample.period_end),
            engine_version=sample.engine_version,
            risk_free_rate=RISK_FREE,
            sweep_id="experiments/2026-08-30-sweep-verify/冒煙",
            param_set_prefix=prefix,
            param_set_suffix="",
            base_values=base_values,
            objective=OBJECTIVE,
            min_trades=int(THRESHOLDS["min_trades"]),
            lonely_peak_margin=float(THRESHOLDS["lonely_peak_margin"]),
            plateau_quantile=float(THRESHOLDS["plateau_quantile"]),
            report=BatchReport(directory=work / "報告", title="KARST-091 冒煙"),
            engine_name=sample.engine_name,
        )
        report["rescan_reuses_batch"] = bool(again.reused_batch)
        report["rescan_same_run_ids"] = again.run_ids == outcome.run_ids

        filed_ids = {
            tuple(str(getattr(row, axis)) for axis in axes): str(getattr(row, "run_id"))
            for row in filed.itertuples(index=False)
        }
        fresh_ids = {
            tuple(str(cell.point.get(axis)) for axis in axes): cell.run_id
            for cell in outcome.sweep.cells
        }
        report["cells"] = len(outcome.sweep.cells)
        report["reused"] = outcome.sweep.reused
        report["executed"] = outcome.sweep.executed
        report["errors"] = len(outcome.failures)
        report["run_ids_identical"] = fresh_ids == filed_ids
        report["run_id_differences"] = [
            {"point": list(point), "filed": filed_ids.get(point), "fresh": run_id}
            for point, run_id in fresh_ids.items()
            if filed_ids.get(point) != run_id
        ][:5]

        # 逐格數字:掃描表落了檔的指標欄,逐格對回這次跑出來的成績單。
        filed_metrics = {
            tuple(str(getattr(row, axis)) for axis in axes): row
            for row in filed.itertuples(index=False)
        }
        metric_gaps: list[dict[str, Any]] = []
        for cell in outcome.sweep.cells:
            point = tuple(str(cell.point.get(axis)) for axis in axes)
            row = filed_metrics[point]
            for column in METRIC_COLUMNS_FILED:
                objective = column.replace("annual_excess_", "annual_excess:")
                fresh_value = cell.value_of(objective)
                was = float(getattr(row, column))
                if fresh_value is None or abs(float(fresh_value) - was) > 1e-9:
                    metric_gaps.append(
                        {"point": list(point), "metric": column, "filed": was, "fresh": fresh_value}
                    )
        report["metrics_identical"] = not metric_gaps
        report["metric_differences"] = metric_gaps[:5]

        # 逐格裁決:用落檔那張判讀表所用的目標重判一次,再逐格對。
        from karst.sweep.verdict import judge

        filed_judgement = judge(
            outcome.sweep.scores(FILED_VERDICT_OBJECTIVE),
            grid,
            objective=FILED_VERDICT_OBJECTIVE,
            min_trades=int(THRESHOLDS["min_trades"]),
            lonely_peak_margin=float(THRESHOLDS["lonely_peak_margin"]),
            plateau_quantile=float(THRESHOLDS["plateau_quantile"]),
        )
        report["verdict_objective"] = FILED_VERDICT_OBJECTIVE
        filed_verdict_of = {
            tuple(str(getattr(row, axis)) for axis in axes): str(getattr(row, "verdict"))
            for row in filed_verdicts.itertuples(index=False)
        }
        fresh_verdict_of = {
            tuple(str(cell.point.get(axis)) for axis in axes): cell.verdict
            for cell in filed_judgement.cells
        }
        report["verdicts_identical"] = fresh_verdict_of == filed_verdict_of
        report["verdict_differences"] = [
            {"point": list(point), "filed": filed_verdict_of.get(point), "fresh": verdict}
            for point, verdict in fresh_verdict_of.items()
            if filed_verdict_of.get(point) != verdict
        ][:5]

        batch = outcome.batch
        report["batch"] = {
            "sweep_id": batch.sweep_id,
            "cells": batch.cell_count,
            "qualified": batch.qualified_cells,
            "failed": batch.failed_cells,
            "errors": batch.error_cells,
            "median_annual_return": batch.median_annual_return,
            "objective": batch.objective,
            "best_point": batch.best_point,
            "best_run_id": batch.best_run_id,
            "representative_point": batch.representative_point,
        }

        from karst.gateway import ledger as ledger_mod

        key_bytes = ledger_mod.load_or_create_key(str(copy))
        clean = ledger_mod.verify(store._conn, key_bytes)
        report["verify_findings_after_gateway_write"] = [
            f"{f.table}:{f.row_key}:{f.problem}" for f in clean
            if getattr(f, "table", "") == "sweep_batch"
        ]
        report["verify_clean_after_gateway_write"] = not report[
            "verify_findings_after_gateway_write"
        ]

        # 之後直接寫庫塞一列(繞過唯一入口),verify 應該即刻點名。
        store._conn.execute(
            "INSERT INTO sweep_batch (sweep_id, strategy_version_id, period_start, period_end,"
            " snapshot_id, engine_name, engine_version, cell_count, qualified_cells, failed_cells,"
            " error_cells, objective, min_trades, lonely_peak_margin, plateau_quantile,"
            " report_path, report_hash, created_at)"
            " VALUES ('繞過唯一入口', ?, ?, ?, ?, 'x', 'y', 1, 0, 0, 0, 'annual_return', 0, 0.0, 0.0,"
            " 'nowhere', 'deadbeef', '2026-08-30')",
            (setup.strategy.strategy_version_id, sample.period_start, sample.period_end,
             sample.snapshot_id),
        )
        store._conn.commit()
        flagged = ledger_mod.verify(store._conn, key_bytes)
        report["verify_findings_after_direct_write"] = [
            f"{f.table}:{f.row_key}:{f.problem}" for f in flagged
            if getattr(f, "table", "") == "sweep_batch"
        ]
        report["verify_flags_direct_write"] = any(
            "繞過唯一入口" in text for text in report["verify_findings_after_direct_write"]
        )

    out = Path(__file__).with_name("冒煙結果.json")
    out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    ok = (
        report["run_ids_identical"]
        and report["rescan_reuses_batch"]
        and report["rescan_same_run_ids"]
        and report["metrics_identical"]
        and report["verdicts_identical"]
        and report["verify_clean_after_gateway_write"]
        and report["verify_flags_direct_write"]
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
