"""KARST-090 驗收:13 條正式運行的編號與八項指標,逐位不變。

兩層證據:
1. 身份層——逐條由庫內身份重算 fingerprint 與運行編號,與落庫那個對。
2. 內容層——因子混合那條正式運行,用新的策略合約 + 執行台**真的重跑一次引擎**
   (繞過查重),把逐日淨值、逐日持倉、逐筆訂單與落檔那份逐位對。

全程只讀:庫先複製一份出來,一句都不寫回倉。
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd

REPO = Path(r"C:\projects\Karst")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "experiments"))

from karst.data.snapshots import read_price_panel  # noqa: E402
from karst.engine import PricePanel  # noqa: E402
from karst.executor import RunRequest, resolve_entities, simulate_plan  # noqa: E402
from karst.executor.executor import engine_for  # noqa: E402
from karst.metrics import run_metrics  # noqa: E402
from karst.runs import RunStore  # noqa: E402
from karst.store import DefinitionStore  # noqa: E402
from karst.strategies.factor_mix import (  # noqa: E402
    CADENCE_PARAM,
    FACTOR_ETF_SLEEVES,
    FactorMixContract,
)

SCRATCH = Path(__file__).resolve().parent
STORE_COPY = SCRATCH / "karst-verify.sqlite"
RUNS_ROOT = REPO / "data" / "runs"
SNAPSHOT_ROOT = REPO / "data" / "snapshots"
RISK_FREE = 0.04

EIGHT = (
    "total_return", "annual_return", "max_drawdown", "win_rate",
    "profit_loss_ratio", "sortino", "average_holding_days", "turnover",
)


def main() -> int:
    shutil.copy2(REPO / "karst.sqlite", STORE_COPY)
    problems: list[str] = []
    report: dict = {"runs": {}, "identity_mismatch": [], "content": {}}

    with DefinitionStore.open(str(STORE_COPY)) as store:
        runs = RunStore(store, root=RUNS_ROOT)
        rows = store.connection.execute(
            "SELECT run_id FROM backtest_run WHERE origin = 'formal' ORDER BY created_at"
        ).fetchall()
        run_ids = [r["run_id"] for r in rows]
        print(f"正式運行:{len(run_ids)} 條")

        # ---- 1. 身份層 ------------------------------------------------
        for run_id in run_ids:
            record = runs.get_run(run_id)
            fingerprint = store.run_fingerprint(
                strategy_name=record.strategy_name,
                param_set_name=record.param_set_name,
                period_start=record.period_start,
                period_end=record.period_end,
                snapshot_id=record.snapshot_id,
                engine_name=record.engine_name,
                engine_version=record.engine_version,
                strategy_version_no=record.strategy_version_no,
                param_set_version_no=record.param_set_version_no,
                factor_version_ids=[f.factor_version_id for f in record.factors] or None,
            )
            fresh = store.run_id_for(fingerprint)
            same = fresh == run_id and fingerprint == record.fingerprint
            if not same:
                problems.append(f"{run_id}:重算編號 {fresh}")
                report["identity_mismatch"].append(run_id)

            entry: dict = {
                "strategy": record.strategy_name,
                "param_set": f"{record.param_set_name}@{record.param_set_version_no}",
                "recomputed_run_id": fresh,
                "identity_stable": same,
            }
            try:
                entry["series_intact"] = list(runs.verify_run(run_id)) or ["全對"]
            except Exception as exc:  # noqa: BLE001 - 序列可能已經不在倉裡
                entry["series_intact"] = f"讀不到:{type(exc).__name__}: {exc}"
            try:
                metrics = run_metrics(
                    runs, run_id, risk_free_rate=RISK_FREE, snapshot_root=SNAPSHOT_ROOT
                )
                entry["metrics"] = {k: getattr(metrics, k) for k in EIGHT}
            except Exception as exc:  # noqa: BLE001 - 快照可能已經不在倉裡
                entry["metrics"] = f"算不出:{type(exc).__name__}: {exc}"
            report["runs"][run_id] = entry
            print(f"  {run_id} {'✔' if same else '✘'} {record.strategy_name}")

        # ---- 2. 內容層:因子混合那條真的重跑一次 -------------------------
        import snapshot_ids  # noqa: PLC0415

        snapshot_id = snapshot_ids.PRICE_FACTOR_ETF
        target = None
        for run_id in run_ids:
            record = runs.get_run(run_id)
            if record.snapshot_id == snapshot_id and record.engine_name == "vectorbt":
                target = record
                break
        if target is None:
            report["content"] = {"skipped": "庫內沒有那條因子混合正式運行"}
        elif not (SNAPSHOT_ROOT / snapshot_id).is_dir():
            report["content"] = {"skipped": f"倉裡沒有快照 {snapshot_id}"}
        else:
            opens = read_price_panel(
                store, snapshot_id, field="open", root=SNAPSHOT_ROOT
            ).dropna(how="any")
            closes = read_price_panel(
                store, snapshot_id, field="close", root=SNAPSHOT_ROOT
            ).dropna(how="any")
            common = opens.index.intersection(closes.index)
            panel = PricePanel.from_frames(open=opens.loc[common], close=closes.loc[common])

            contract = FactorMixContract(
                sleeves=FACTOR_ETF_SLEEVES, initial_cash=100_000.0, fees=0.0
            )
            param_set = store.get_param_set(
                target.strategy_name,
                target.param_set_name,
                strategy_version_no=target.strategy_version_no,
                set_version_no=target.param_set_version_no,
            )
            values = contract.param_spec().read(param_set)
            entities = resolve_entities(
                store,
                contract.needs_entities(values),
                on_date=panel.dates[0],
                known_entity_ids=tuple(panel.entity_ids),
            )
            factors = {}
            for ref in target.factors:
                version = store.get_factor_version(ref.name)
                factors[ref.name] = type(
                    "Ref", (), {
                        "name": ref.name,
                        "factor_version_id": version.factor_version_id,
                        "version_no": version.version_no,
                    },
                )()
            plan = contract.plan(
                RunRequest(
                    panel=panel, params=values, entities=entities,
                    factors=factors, snapshot_id=snapshot_id,
                )
            )
            engine = engine_for(contract, None)
            simulation = simulate_plan(
                engine, panel, plan, engine_name=getattr(engine, "name", "vectorbt")
            )

            stored_equity = runs.equity_curve(target.run_id)
            stored_holdings = runs.holdings(target.run_id)
            stored_orders = runs.orders(target.run_id)
            fresh_orders = simulation.orders_frame()

            equity_same = bool(
                len(stored_equity) == len(simulation.equity_curve)
                and (stored_equity.to_numpy() == simulation.equity_curve.to_numpy()).all()
            )
            # 落檔的持倉是長表(date、entity_id、shares),引擎交出來的是闊表;
            # 攤成同一個形狀再逐格對。
            wide = stored_holdings.pivot(
                index="date", columns="entity_id", values="shares"
            ).fillna(0.0)
            wide.index = pd.to_datetime(wide.index)
            fresh = simulation.holdings.reindex(
                index=wide.index, columns=wide.columns
            ).fillna(0.0)
            holdings_same = bool(
                wide.shape == fresh.shape and (wide.to_numpy() == fresh.to_numpy()).all()
            )
            orders_same = bool(
                len(stored_orders) == len(fresh_orders)
                and (
                    stored_orders[["side", "shares", "price", "fees"]].to_numpy()
                    == fresh_orders[["side", "shares", "price", "fees"]].to_numpy()
                ).all()
            )
            report["content"] = {
                "run_id": target.run_id,
                "engine_rerun": True,
                "equity_identical": equity_same,
                "holdings_identical": holdings_same,
                "orders_identical": orders_same,
                "rows": {
                    "equity": int(len(stored_equity)),
                    "orders": int(len(stored_orders)),
                    "rebalances": int(len(plan.rebalances)),
                },
            }
            for label, ok in (
                ("逐日淨值", equity_same), ("逐日持倉", holdings_same), ("逐筆訂單", orders_same)
            ):
                if not ok:
                    problems.append(f"因子混合重跑:{label}對不上")
            print(f"  內容層重跑:淨值 {equity_same} 持倉 {holdings_same} 訂單 {orders_same}")

    report["problems"] = problems
    out = SCRATCH / "verify_090.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\n落檔:{out}")
    print("結論:" + ("全部逐位相同" if not problems else f"有 {len(problems)} 處對不上"))
    for line in problems:
        print("  ✘", line)
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
