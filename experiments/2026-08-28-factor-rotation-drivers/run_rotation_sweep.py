"""KARST-036:因子輪動驅動器矩陣掃描——只用四隻因子 ETF,靠什麼推動移權最有效。

跑法(倉根目錄)::

    set PYTHONUTF8=1
    python experiments/2026-08-28-factor-rotation-drivers/run_rotation_sweep.py

做七件事:

1. 由數據快照砌價格面板(六隻 ETF;四隻因子 ETF 才是持倉,SPY 另做**訊號**與基準,
   QQQ 只做基準)。**編號不寫死在這裡**:七支成績腳本共用
   ``experiments/snapshot_ids.py`` 那一份,重抓之後只改那一個檔
   (現用 ``PRICE_FACTOR_ETF``,舊 ``2026-08-27-91a5d51339d9``)。
2. 確保四個因子與「因子輪動(ETF 版)」策略已經登記(經唯一入口;已經有就一個字
   都不寫)。
3. 四個驅動器逐個掃自己的參數格 × 換倉節奏,每格經 ``karst.runs`` 落痕拿一個運行
   編號。**同一格重掃不重跑。**
4. 逐個驅動器判平原 / 孤峰 / 無效格(``karst.sweep.verdict``,KARST-029 那一套),
   出報告與投影圖;年化超額與最大回撤各一份(同一批運行,換個目標指標重判)。
5. 跑四個**對照格**:固定權重的「動能 95% / 價值 5%」與「各佔 25%」,月度與季度
   各一個。它們是 KARST-029 已經跑過的運行,所以這裡一格都不會重跑,直接讀回。
6. 出一張**成績表**:每個驅動器的最優格與鄰域平均最高格,連八項指標,以及對兩個
   固定權重對照的差距。
7. 出**分段超額**:2015–2019 / 2020–2022 / 2023–2026 三段各自對 SPY 的年化超額
   (同一批運行,只換檢視視窗重看——重看不重跑,規格 8.5)。

**本檔一句 ``set_active_setup`` 都沒有**:掃出來的最優不是現役設定(規格 7.5)。
只交表與判讀,不裁定哪一個驅動器該用(D-008)。

外部數據:**零**。四個驅動器的訊號全部由這六隻 ETF 自身的收價算出來,沒有 VIX、
沒有債息、沒有第三方來源要付費(見 ``karst.strategies.factor_rotation.EXTERNAL_DATA``)。
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

# 掃描編號(sweep id):一次掃描的識別字,逐格隨運行入庫(KARST-054)。慣例跟參數
# 掃描頁認掃描那個一樣——落檔目錄的倉內相對路徑;同一個實驗跑幾次掃描就補字尾分開。
EXPERIMENT_ID = HERE.relative_to(REPO).as_posix()

import pandas as pd  # noqa: E402

from karst.data.snapshots import read_price_panel  # noqa: E402
from karst.engine import PricePanel  # noqa: E402
from karst.gateway.service import Gateway  # noqa: E402
from karst.runs import RunStore  # noqa: E402
from karst.strategies.factor_mix import FACTOR_ETF_SLEEVES  # noqa: E402
from karst.strategies.factor_rotation import (  # noqa: E402
    DRIVER_PARAMETERS,
    EXTERNAL_DATA,
    build_driver,
)
from karst.sweep import (  # noqa: E402
    CADENCE_AXIS,
    ExplicitGrid,
    FactorMixJob,
    draw_projection_set,
    judge,
    reference_point,
    run_sweep,
    write_report,
)
from karst.sweep.factor_rotation import (  # noqa: E402
    FactorRotationJob,
    ScoreEntry,
    ensure_factor_rotation_setup,
    rotation_grid,
    scoreboard,
    segment_excess,
)

STORE_PATH = REPO / "karst.sqlite"
SNAPSHOT_ROOT = REPO / "data" / "snapshots"
RUNS_ROOT = REPO / "data" / "runs"

SNAPSHOT_ID = PRICE_FACTOR_ETF   # 見 experiments/snapshot_ids.py(KARST-057 重建)
ROTATION_STRATEGY = "因子輪動(ETF 版)"
MIX_STRATEGY = "因子混合(ETF 版)"
ENGINE_VERSION = "0.1.0"
MARKET_TICKER = "SPY"

SETUP_PARAM_SET = "掃描基座-KARST-036"
# 對照那邊要**原封不動**沿用 KARST-029 的參數集命名,否則撞不回同一個運行編號,
# 就會白白重跑一次固定權重。
MIX_PARAM_SET_PREFIX = "掃描w-"

RISK_FREE_RATE = 0.04

# 熱身期:一年(252 根 K 線)。整次掃描共用同一個數,所以每一格走同一段日子,
# 回望期 L 那條軸才乾淨——不會出現「L 越長、熱身越久」的混淆。
WARMUP_BARS = 252
WARMUP_WEIGHTS = {sleeve.weight_key: 0.25 for sleeve in FACTOR_ETF_SLEEVES}

# 每個驅動器要掃哪些取值。**無預設值**——這裡就是「寫明」那一份(D-008 第 3 條)。
DRIVER_VALUES: dict[str, dict[str, list]] = {
    "factor_momentum": {
        "lookback_months": [1, 3, 6, 9, 12],
        "mode": ["winner", "rank"],
    },
    "relative_strength": {
        "lookback_months": [1, 3, 6, 9, 12],
        "fallback": ["cash", "equal"],
    },
    "inverse_volatility": {
        "lookback_days": [21, 63, 126, 252],
        "power": [1.0, 2.0],
    },
    "trend_switch": {
        "ma_days": [50, 100, 150, 200],
        "tilt": [0.5, 0.75, 1.0],
    },
}

DRIVER_TITLES = {
    "factor_momentum": "因子動量排名",
    "relative_strength": "相對強弱對 SPY",
    "inverse_volatility": "逆波幅",
    "trend_switch": "大市趨勢開關",
}

# 三段分期。分幾段、怎樣分,寫明在這裡,不由任何一層代設。
SEGMENTS = (
    ("2015–2019", "2015-01-02", "2019-12-31"),
    ("2020–2022", "2020-01-01", "2022-12-31"),
    ("2023–2026", "2023-01-01", "2026-08-26"),
)

# 兩個固定權重對照(KARST-029 的成績)。前者是那次掃描的單點最優格。
FIXED_BEST = {
    "weight_quality": 0.0, "weight_value": 0.05,
    "weight_momentum": 0.95, "weight_low_vol": 0.0,
}
FIXED_EVEN = {sleeve.weight_key: 0.25 for sleeve in FACTOR_ETF_SLEEVES}


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
    parser = argparse.ArgumentParser(description="因子輪動驅動器矩陣掃描")
    parser.add_argument(
        "--cadences", default="monthly,quarterly", help="換倉節奏,逗號分隔"
    )
    parser.add_argument(
        "--objective", default="annual_excess:SPY", help="判讀的目標指標(一律越大越好)"
    )
    parser.add_argument("--min-trades", type=int, default=30, help="成交少於這個數的格判無效")
    parser.add_argument(
        "--margin", type=float, default=0.005, help="孤峰門檻:高出鄰域平均幾多才算明顯"
    )
    parser.add_argument("--quantile", type=float, default=0.90, help="平原高地由哪一個分位起計")
    parser.add_argument("--warmup", type=int, default=WARMUP_BARS, help="熱身期(根 K 線)")
    parser.add_argument("--out", default=None, help="輸出目錄,預設 results/")
    parser.add_argument(
        "--drivers", default=",".join(DRIVER_VALUES), help="要跑哪幾個驅動器,逗號分隔"
    )
    return parser.parse_args()


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


def main() -> None:
    args = parse_args()
    os.environ.setdefault("KARST_WRITER", "KARST-036-rotation2")
    cadences = tuple(c.strip() for c in args.cadences.split(",") if c.strip())
    drivers = tuple(d.strip() for d in args.drivers.split(",") if d.strip())
    out = Path(args.out) if args.out else HERE / "results"
    out.mkdir(parents=True, exist_ok=True)

    with Gateway.open(str(STORE_PATH)) as gateway:
        store = gateway.store
        panel = build_panel(store)
        period = (str(panel.dates[0].date()), str(panel.dates[-1].date()))
        print(
            f"價格面板:{len(panel.dates)} 個交易日 × {len(panel.entity_ids)} 隻"
            f"({period[0]} ~ {period[1]});熱身期 {args.warmup} 根",
            flush=True,
        )

        rotation = ensure_factor_rotation_setup(
            gateway,
            strategy_name=ROTATION_STRATEGY,
            snapshot_id=SNAPSHOT_ID,
            setup_param_set_name=SETUP_PARAM_SET,
            setup_weights=WARMUP_WEIGHTS,
            cadence=cadences[0],
            description="KARST-036 驅動器掃描的基座,不是現役設定",
        )
        print(f"策略:{rotation.name} 第 {rotation.version_no} 版", flush=True)

        runs = RunStore(store, root=RUNS_ROOT)
        entries: list[ScoreEntry] = []
        summary: dict = {
            "snapshot_id": SNAPSHOT_ID,
            "period": list(period),
            "trading_days": len(panel.dates),
            "warmup_bars": args.warmup,
            "warmup_weights": WARMUP_WEIGHTS,
            "cadences": list(cadences),
            "objective": args.objective,
            "thresholds": {
                "min_trades": args.min_trades,
                "lonely_peak_margin": args.margin,
                "plateau_quantile": args.quantile,
            },
            "external_data": list(EXTERNAL_DATA),
            "market_ticker": MARKET_TICKER,
            "drivers": {},
        }

        # ---- 四個驅動器,逐個掃自己的參數格 ----
        for driver_key in drivers:
            title = DRIVER_TITLES[driver_key]
            grid = rotation_grid(
                driver_key, values=DRIVER_VALUES[driver_key], cadences=cadences
            )
            job = FactorRotationJob(
                gateway=gateway,
                panel=panel,
                driver_key=driver_key,
                strategy_name=ROTATION_STRATEGY,
                snapshot_id=SNAPSHOT_ID,
                engine_version=ENGINE_VERSION,
                param_set_prefix=f"掃描r-{driver_key}-",
                period_start=period[0],
                period_end=period[1],
                warmup_bars=args.warmup,
                warmup_weights=WARMUP_WEIGHTS,
                strategy_version_no=rotation.version_no,
                market_ticker=MARKET_TICKER,
            )
            print(f"\n【{title}】{grid.describe()}", flush=True)

            began = time.perf_counter()

            def progress(index: int, total: int, cell, began=began) -> None:
                if index % 10 == 0 or index == total:
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
                sweep_id=f"{EXPERIMENT_ID}/{driver_key}",
                risk_free_rate=RISK_FREE_RATE,
                snapshot_root=SNAPSHOT_ROOT,
                progress=progress,
            )
            print(
                f"  掃描完成:{len(sweep)} 格,{sweep.executed} 格今次跑、"
                f"{sweep.reused} 格讀回舊運行;新寫入參數集 {job.param_sets_written} 個",
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
            print(f"  判讀({args.objective}):{verdict.summary()}", flush=True)

            driver_out = out / driver_key
            axes = [*DRIVER_PARAMETERS[driver_key], CADENCE_AXIS]
            charts = list(
                draw_projection_set(
                    verdict,
                    driver_out,
                    axes=axes,
                    title=title,
                    subtitle=f"{args.objective}|{period[0]} ~ {period[1]}|快照 {SNAPSHOT_ID}",
                    prefix="projection",
                )
            )
            sample = build_driver(
                driver_key,
                **{
                    name: DRIVER_VALUES[driver_key][name][0]
                    for name in DRIVER_PARAMETERS[driver_key]
                },
            )
            report = write_report(
                sweep,
                verdict,
                driver_out,
                title=f"因子輪動·{title}(對 SPY 年化超額)",
                charts=charts,
                notes=(
                    f"驅動器:{sample.describe()}(這一句是其中一格的寫法,"
                    "參數逐格不同,見掃描表)。\n\n"
                    f"熱身期 {args.warmup} 根 K 線,期間四格各佔 25%——即與「各佔 25%」"
                    "那個對照一模一樣;驅動器由第 "
                    f"{args.warmup} 根之後的第一個決策日才開始話事。\n\n"
                    "訊號一律只用**決策日收工前**的數據,成交在下一根 K 線的開價"
                    "(D-021 第 3 條);大市那條線(SPY)只做訊號,一股不持。\n\n"
                    "外部數據:一個都沒有用——全部訊號由這六隻 ETF 自身的收價算出來。"
                ),
            )
            drawdown = judge(
                sweep.scores("max_drawdown"),
                grid,
                objective="max_drawdown",
                min_trades=args.min_trades,
                lonely_peak_margin=args.margin,
                plateau_quantile=args.quantile,
            )
            drawdown_charts = list(
                draw_projection_set(
                    drawdown,
                    driver_out,
                    axes=axes,
                    title=f"{title}·最大回撤",
                    subtitle=f"max_drawdown(負數,越接近零越好)|{period[0]} ~ {period[1]}",
                    prefix="drawdown",
                )
            )
            drawdown_report = write_report(
                sweep,
                drawdown,
                driver_out,
                title=f"因子輪動·{title}(最大回撤)",
                charts=drawdown_charts,
                filename="報告-最大回撤.md",
                notes=(
                    "最大回撤以**負數**表示,所以判讀那句「越大越好」在這裡就是"
                    "「跌得越少越好」。與年化超額那一份**用的是同一批運行**,"
                    "只換一個目標指標重判一次,一格都沒有重跑。"
                ),
            )

            best, robust = verdict.best, verdict.most_robust
            if best is not None:
                entries.append(
                    ScoreEntry(
                        label=f"{title}·最優格",
                        kind="驅動器",
                        cell=sweep.cell_for(best.point),
                        verdict=best,
                        note=sample.name,
                    )
                )
            if robust is not None and (best is None or robust.point != best.point):
                entries.append(
                    ScoreEntry(
                        label=f"{title}·鄰域平均最高",
                        kind="驅動器",
                        cell=sweep.cell_for(robust.point),
                        verdict=robust,
                        note="穩健平原的中心",
                    )
                )

            summary["drivers"][driver_key] = {
                "title": title,
                "grid": grid.describe(),
                "cells": len(sweep),
                "executed": sweep.executed,
                "reused": sweep.reused,
                "seconds": round(sweep.seconds, 2),
                "counts": {
                    "plateau": len(verdict.plateaus),
                    "lonely_peak": len(verdict.lonely_peaks),
                    "invalid": len(verdict.invalid_cells),
                },
                "plateau_threshold": verdict.plateau_threshold,
                "best_single": _cell_summary(sweep, verdict, best),
                "best_neighbourhood": _cell_summary(sweep, verdict, robust),
                "top5": [_cell_summary(sweep, verdict, c) for c in verdict.top(5)],
                "max_drawdown_axis": {
                    "shallowest": _cell_summary(sweep, drawdown, drawdown.best),
                    "counts": {
                        "plateau": len(drawdown.plateaus),
                        "lonely_peak": len(drawdown.lonely_peaks),
                        "invalid": len(drawdown.invalid_cells),
                    },
                    "report": str(drawdown_report.relative_to(out)),
                },
                "report": str(report.relative_to(out)),
                "charts": [str(c.relative_to(out)) for c in charts + drawdown_charts],
            }

        # ---- 對照格:固定權重(KARST-029 已經跑過,這裡只讀回) ----
        mix_version = store.get_strategy_version(MIX_STRATEGY)
        mix_job = FactorMixJob(
            gateway=gateway,
            panel=panel,
            sleeves=FACTOR_ETF_SLEEVES,
            strategy_name=MIX_STRATEGY,
            snapshot_id=SNAPSHOT_ID,
            engine_version=ENGINE_VERSION,
            param_set_prefix=MIX_PARAM_SET_PREFIX,
            period_start=period[0],
            period_end=period[1],
            strategy_version_no=mix_version.version_no,
        )
        controls = [
            ("固定權重·動能95價值5", FIXED_BEST),
            ("固定權重·各佔25%", FIXED_EVEN),
        ]
        control_points = [
            reference_point(FACTOR_ETF_SLEEVES, weights, cadence=cadence)
            for _, weights in controls
            for cadence in cadences
        ]
        control_sweep = run_sweep(
            runs=runs,
            grid=ExplicitGrid(control_points, label="對照格(固定權重)"),
            job=mix_job,
            sweep_id=f"{EXPERIMENT_ID}/固定權重對照",
            risk_free_rate=RISK_FREE_RATE,
            snapshot_root=SNAPSHOT_ROOT,
        )
        print(
            f"\n對照格:{len(control_sweep)} 格,{control_sweep.executed} 格今次跑、"
            f"{control_sweep.reused} 格讀回 KARST-029 的舊運行",
            flush=True,
        )
        control_labels: list[str] = []
        for cell in control_sweep.cells:
            cadence = cell.point.get(CADENCE_AXIS)
            name = next(
                label
                for label, weights in controls
                if all(cell.point.get(k) == v for k, v in weights.items())
            )
            label = f"{name}({cadence})"
            control_labels.append(label)
            entries.append(
                ScoreEntry(label=label, kind="對照", cell=cell, note="KARST-029 固定權重")
            )

        # ---- 成績表 ----
        baselines = [
            label for label in control_labels if label.endswith("(quarterly)")
        ] or control_labels
        table = scoreboard(entries, objective=args.objective, baselines=baselines)
        table.to_csv(out / "成績表.csv", index=False, encoding="utf-8-sig")

        # ---- 分段超額 ----
        segments = segment_excess(
            runs,
            entries,
            segments=SEGMENTS,
            risk_free_rate=RISK_FREE_RATE,
            benchmark="SPY",
            snapshot_root=SNAPSHOT_ROOT,
        )
        segments.to_csv(out / "分段超額.csv", index=False, encoding="utf-8-sig")

        summary["scoreboard"] = json.loads(table.to_json(orient="records"))
        summary["segments"] = json.loads(segments.to_json(orient="records"))
        summary["baselines"] = baselines
        (out / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        with pd.option_context("display.width", 200, "display.max_columns", 40):
            print("\n=== 成績表(目標指標 " + args.objective + ") ===", flush=True)
            print(
                table[["名稱", "類別", "參數", args.objective, "max_drawdown", "裁決"]]
                .to_string(index=False),
                flush=True,
            )
            print("\n=== 分段年化超額(對 SPY) ===", flush=True)
            print(
                segments.pivot(index="名稱", columns="段", values="年化超額").to_string(),
                flush=True,
            )
        print(f"\n落檔:{out}", flush=True)


if __name__ == "__main__":
    main()
