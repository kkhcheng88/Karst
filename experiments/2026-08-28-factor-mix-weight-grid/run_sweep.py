"""KARST-029:因子混合策略四隻因子 ETF 的權重單純形格,第一次真實掃描。

跑法(倉根目錄)::

    set PYTHONUTF8=1
    python experiments/2026-08-28-factor-mix-weight-grid/run_sweep.py --step 0.10
    python experiments/2026-08-28-factor-mix-weight-grid/run_sweep.py --step 0.05

做六件事:

1. 由數據快照砌價格面板(六隻 ETF;SPY 與 QQQ 只做基準,四隻因子 ETF 才是持倉)。
   **編號不寫死在這裡**:七支成績腳本共用 ``experiments/snapshot_ids.py`` 那一份,
   重抓之後只改那一個檔(現用 ``PRICE_FACTOR_ETF``,舊 ``2026-08-27-91a5d51339d9``)。
2. 確保四個因子與策略已經登記(經唯一入口;已經有就一個字都不寫)。
3. 砌權重單純形格 × 換倉節奏一維,逐格經引擎跑,每格經 ``karst.runs`` 落痕拿一個
   運行編號。**同一格重掃不重跑**。
4. 判平原 / 孤峰 / 無效格(``karst.sweep.verdict``),門檻三個全部由命令列指定,
   報告一定印得出。
5. 畫投影圖:四個權重每一對一張(六張),節奏 × 每個權重再四張;月度與季度各一套。
6. 落報告、掃描表、判讀表與 ``summary.json``。

**本檔一句 ``set_active_setup`` 都沒有**:掃出來的最優不是現役設定,現役設定要由
用戶自己指定(規格 7.5)。本票只交表與判讀,不裁定哪一組參數該用(D-008)。

一件要記住的事:**10% 步長排不出「各 25%」**(十步分不均四格),所以固定四等分
那一格是用 ``--reference`` 另外跑的對照格;5% 步長的格本身就含住它。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:  # 未裝套件也跑得動(倉根就在上兩層)
    sys.path.insert(0, str(REPO))
_EXPERIMENTS = REPO / "experiments"
if str(_EXPERIMENTS) not in sys.path:   # 現役快照編號七支腳本共用一份(KARST-057)
    sys.path.insert(0, str(_EXPERIMENTS))

from snapshot_ids import PRICE_FACTOR_ETF  # noqa: E402

HERE = Path(__file__).resolve().parent


def sweep_id_for(out: Path, suffix: str = "") -> str:
    """掃描編號:一次掃描的識別字,逐格隨運行入庫(KARST-054)。

    慣例跟參數掃描頁認掃描那個一樣——落檔目錄的倉內相對路徑;同一個目錄跑多過
    一次掃描,就在後面補一個字尾分開。
    """
    base = out.resolve()
    try:
        name = base.relative_to(REPO).as_posix()
    except ValueError:  # --out 指到倉外,唯有用絕對路徑
        name = base.as_posix()
    return f"{name}{suffix}"


from karst.data.snapshots import read_price_panel  # noqa: E402
from karst.engine import PricePanel  # noqa: E402
from karst.gateway.service import Gateway  # noqa: E402
from karst.runs import RunStore  # noqa: E402
from karst.strategies.factor_mix import FACTOR_ETF_SLEEVES  # noqa: E402
from karst.sweep import (  # noqa: E402
    CADENCE_AXIS,
    ExplicitGrid,
    FactorMixJob,
    draw_projection_set,
    ensure_factor_mix_setup,
    judge,
    reference_point,
    run_sweep,
    weight_grid,
    write_report,
)

STORE_PATH = REPO / "karst.sqlite"
SNAPSHOT_ROOT = REPO / "data" / "snapshots"
RUNS_ROOT = REPO / "data" / "runs"

SNAPSHOT_ID = PRICE_FACTOR_ETF   # 見 experiments/snapshot_ids.py(KARST-057 重建)
STRATEGY = "因子混合(ETF 版)"
ENGINE_VERSION = "0.1.0"

# 掃描每一格的參數集名前綴。一格一個名,查重靠名不靠版本鏈。
PARAM_SET_PREFIX = "掃描w-"
SETUP_PARAM_SET = "掃描基座-KARST-029"

# 無風險利率:Sortino 的分子要用它,無預設值(規格 8.3)。這是示例取值。
RISK_FREE_RATE = 0.04


def build_panel(store) -> PricePanel:
    opens = read_price_panel(store, SNAPSHOT_ID, field="open", root=SNAPSHOT_ROOT).dropna(
        how="any"
    )
    closes = read_price_panel(store, SNAPSHOT_ID, field="close", root=SNAPSHOT_ROOT).dropna(
        how="any"
    )
    common = opens.index.intersection(closes.index)
    return PricePanel.from_frames(open=opens.loc[common], close=closes.loc[common])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="因子混合權重單純形格掃描")
    parser.add_argument("--step", type=float, default=0.10, help="權重步長,例如 0.10 或 0.05")
    parser.add_argument(
        "--cadences", default="monthly,quarterly", help="換倉節奏,逗號分隔;寫一個即不掃節奏"
    )
    parser.add_argument(
        "--objective", default="annual_excess:SPY", help="判讀的目標指標(一律越大越好)"
    )
    parser.add_argument("--min-trades", type=int, default=30, help="成交少於這個數的格判無效")
    parser.add_argument(
        "--margin", type=float, default=0.01, help="孤峰門檻:高出鄰域平均幾多才算明顯"
    )
    parser.add_argument("--quantile", type=float, default=0.90, help="平原高地由哪一個分位起計")
    parser.add_argument("--out", default=None, help="輸出目錄名,預設按步長改")
    parser.add_argument(
        "--no-reference", action="store_true", help="不跑固定四等分那個對照格"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.environ.setdefault("KARST_WRITER", "KARST-029-sweep")
    cadences = tuple(c.strip() for c in args.cadences.split(",") if c.strip())
    out = Path(args.out) if args.out else HERE / f"results-{int(round(args.step * 100))}pct"
    out.mkdir(parents=True, exist_ok=True)

    with Gateway.open(str(STORE_PATH)) as gateway:
        store = gateway.store
        panel = build_panel(store)
        period = (str(panel.dates[0].date()), str(panel.dates[-1].date()))
        print(
            f"價格面板:{len(panel.dates)} 個交易日 × {len(panel.entity_ids)} 隻"
            f"({period[0]} ~ {period[1]})",
            flush=True,
        )

        strategy = ensure_factor_mix_setup(
            gateway,
            strategy_name=STRATEGY,
            sleeves=FACTOR_ETF_SLEEVES,
            snapshot_id=SNAPSHOT_ID,
            setup_param_set_name=SETUP_PARAM_SET,
            setup_weights={s.weight_key: 0.25 for s in FACTOR_ETF_SLEEVES},
            cadence=cadences[0],
            description="KARST-029 權重掃描的基座,不是現役設定",
        )
        print(f"策略:{strategy.name} 第 {strategy.version_no} 版", flush=True)

        runs = RunStore(store, root=RUNS_ROOT)
        grid = weight_grid(FACTOR_ETF_SLEEVES, step=args.step, cadences=cadences)
        job = FactorMixJob(
            gateway=gateway,
            panel=panel,
            sleeves=FACTOR_ETF_SLEEVES,
            strategy_name=STRATEGY,
            snapshot_id=SNAPSHOT_ID,
            engine_version=ENGINE_VERSION,
            param_set_prefix=PARAM_SET_PREFIX,
            period_start=period[0],
            period_end=period[1],
            strategy_version_no=strategy.version_no,
        )
        print(f"掃描格:{grid.describe()}", flush=True)

        began = time.perf_counter()

        def progress(index: int, total: int, cell) -> None:
            if index % 50 == 0 or index == total:
                elapsed = time.perf_counter() - began
                print(
                    f"  {index}/{total} 格,已用 {elapsed:.0f} 秒"
                    f"(每格 {elapsed / index:.2f} 秒)",
                    flush=True,
                )

        sweep = run_sweep(
            runs=runs,
            grid=grid,
            job=job,
            sweep_id=sweep_id_for(out),
            risk_free_rate=RISK_FREE_RATE,
            snapshot_root=SNAPSHOT_ROOT,
            progress=progress,
        )
        print(
            f"掃描完成:{len(sweep)} 格,{sweep.executed} 格今次跑、{sweep.reused} 格讀回舊運行,"
            f"耗時 {sweep.seconds:.1f} 秒;新寫入參數集 {job.param_sets_written} 個",
            flush=True,
        )

        verdict = judge(
            sweep.scores(args.objective),
            grid,
            objective=args.objective,
            min_trades=args.min_trades,
            lonely_peak_margin=args.margin,
            plateau_quantile=args.quantile,
        )
        print(f"判讀:{verdict.summary()}", flush=True)

        references = []
        if not args.no_reference:
            points = [
                reference_point(
                    FACTOR_ETF_SLEEVES,
                    {s.weight_key: 0.25 for s in FACTOR_ETF_SLEEVES},
                    cadence=cadence,
                )
                for cadence in cadences
            ]
            reference_sweep = run_sweep(
                runs=runs,
                grid=ExplicitGrid(points, label="對照格(固定四等分)"),
                job=job,
                sweep_id=sweep_id_for(out, "·對照格"),
                risk_free_rate=RISK_FREE_RATE,
                snapshot_root=SNAPSHOT_ROOT,
            )
            references = list(reference_sweep.cells)
            for cell in references:
                print(
                    f"對照格 {cell.point.label}:{args.objective} = "
                    f"{cell.value_of(args.objective):.4f},運行編號 {cell.run_id}",
                    flush=True,
                )

        weight_axes = [s.weight_key for s in FACTOR_ETF_SLEEVES]
        charts: list[Path] = []
        for cadence in cadences:
            slice_ = verdict.where(**{CADENCE_AXIS: cadence}) if len(cadences) > 1 else verdict
            charts.extend(
                draw_projection_set(
                    slice_,
                    out,
                    axes=weight_axes,
                    title=f"因子混合權重格({cadence})",
                    subtitle=f"{args.objective}|{period[0]} ~ {period[1]}|快照 {SNAPSHOT_ID}",
                    prefix=f"projection-{cadence}",
                )
            )
        if len(cadences) > 1:
            charts.extend(
                draw_projection_set(
                    verdict,
                    out,
                    axes=[CADENCE_AXIS, *weight_axes],
                    title="換倉節奏 × 權重",
                    subtitle=f"{args.objective}|{period[0]} ~ {period[1]}",
                    prefix="projection-cadence",
                )[: len(weight_axes)]
            )
        print(f"圖:{len(charts)} 張", flush=True)

        best = verdict.best
        robust = verdict.most_robust
        report = write_report(
            sweep,
            verdict,
            out,
            title=f"因子混合權重掃描(步長 {args.step:.0%})",
            charts=charts,
            references=references,
            notes=(
                "四隻因子 ETF:QUAL(質素)、VLUE(價值)、MTUM(動能)、USMV(低波);"
                "SPY 與 QQQ 在同一個快照裡,但只做基準,一股不持。\n\n"
                "步長 10% 排不出「各 25%」(十步分不均四格),所以固定四等分是**對照格**"
                "另外跑的,不在 10% 那個格上;5% 步長的格本身就含住它。\n\n"
                "無風險利率 4% 是示例取值,不是裁決;換一個數,Sortino 會跟住變,"
                "年化超額與最大回撤不受影響。"
            ),
        )

        # 第二條主軸:最大回撤(以負數表示,所以「越大」就是「跌得越少」)。
        # 同一批運行、同一個格,只換一個目標指標重判一次——一格都不用重跑。
        drawdown = judge(
            sweep.scores("max_drawdown"),
            grid,
            objective="max_drawdown",
            min_trades=args.min_trades,
            lonely_peak_margin=args.margin,
            plateau_quantile=args.quantile,
        )
        drawdown_charts: list[Path] = []
        for cadence in cadences:
            slice_ = drawdown.where(**{CADENCE_AXIS: cadence}) if len(cadences) > 1 else drawdown
            drawdown_charts.extend(
                draw_projection_set(
                    slice_,
                    out,
                    axes=weight_axes,
                    title=f"因子混合權重格·最大回撤({cadence})",
                    subtitle=f"max_drawdown(負數,越接近零越好)|{period[0]} ~ {period[1]}",
                    prefix=f"drawdown-{cadence}",
                )
            )
        drawdown_report = write_report(
            sweep,
            drawdown,
            out,
            title=f"因子混合權重掃描·最大回撤(步長 {args.step:.0%})",
            charts=drawdown_charts,
            references=references,
            filename="報告-最大回撤.md",
            notes=(
                "最大回撤以**負數**表示(−0.34 即由高位跌 34%),所以判讀那句「越大越好」"
                "在這裡剛好就是「跌得越少越好」,方向不用另設參數。\n\n"
                "這一份與年化超額那一份**用的是同一批運行**——同一個格、同一批運行編號,"
                "只是換一個目標指標重判一次,一格都沒有重跑。"
            ),
        )
        print(f"最大回撤判讀:{drawdown.summary()};報告 {drawdown_report}", flush=True)

        summary = {
            "step": args.step,
            "cadences": list(cadences),
            "cells": len(sweep),
            "executed": sweep.executed,
            "reused": sweep.reused,
            "seconds": round(sweep.seconds, 2),
            "objective": args.objective,
            "thresholds": {
                "min_trades": args.min_trades,
                "lonely_peak_margin": args.margin,
                "plateau_quantile": args.quantile,
                "plateau_threshold": verdict.plateau_threshold,
            },
            "provenance": {
                "strategy": strategy.name,
                "strategy_version_no": strategy.version_no,
                "period": list(period),
                "snapshot_id": SNAPSHOT_ID,
                "engine": f"vectorbt {ENGINE_VERSION}",
                "trading_days": len(panel.dates),
            },
            "counts": {
                "plateau": len(verdict.plateaus),
                "lonely_peak": len(verdict.lonely_peaks),
                "invalid": len(verdict.invalid_cells),
            },
            "max_drawdown_axis": {
                "counts": {
                    "plateau": len(drawdown.plateaus),
                    "lonely_peak": len(drawdown.lonely_peaks),
                    "invalid": len(drawdown.invalid_cells),
                },
                "shallowest": _cell_summary(sweep, drawdown, drawdown.best),
                "report": drawdown_report.name,
                "charts": [c.name for c in drawdown_charts],
            },
            "best_single": _cell_summary(sweep, verdict, best),
            "best_neighbourhood": _cell_summary(sweep, verdict, robust),
            "top5": [_cell_summary(sweep, verdict, c) for c in verdict.top(5)],
            "reference": [
                {
                    "params": cell.point.as_dict(),
                    "value": cell.value_of(args.objective),
                    "annual_return": cell.metrics.annual_return,
                    "max_drawdown": cell.metrics.max_drawdown,
                    "run_id": cell.run_id,
                }
                for cell in references
            ],
            "report": report.name,
            "charts": [c.name for c in charts],
        }
        (out / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"報告:{report}", flush=True)


def _cell_summary(sweep, verdict, cell) -> dict | None:
    if cell is None:
        return None
    run_cell = sweep.cell_for(cell.point)
    return {
        "params": cell.point.as_dict(),
        "value": cell.value,
        "neighbourhood_mean": cell.neighbourhood_mean,
        "neighbour_mean": cell.neighbour_mean,
        "lift": cell.lift,
        "peak_over_neighbourhood": cell.ratio,
        "verdict": cell.verdict,
        "trades": cell.trades,
        "annual_return": run_cell.metrics.annual_return,
        "total_return": run_cell.metrics.total_return,
        "max_drawdown": run_cell.metrics.max_drawdown,
        "sortino": run_cell.metrics.sortino,
        "turnover": run_cell.metrics.turnover,
        "win_rate": run_cell.metrics.win_rate,
        "profit_loss_ratio": run_cell.metrics.profit_loss_ratio,
        "average_holding_days": run_cell.metrics.average_holding_days,
        "annual_excess": dict(run_cell.annual_excess),
        "run_id": run_cell.run_id,
    }


if __name__ == "__main__":
    main()
