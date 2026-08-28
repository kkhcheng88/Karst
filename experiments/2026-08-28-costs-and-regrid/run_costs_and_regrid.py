"""KARST-043:交易成本入引擎——輪動與固定權重連成本重評,兩個贏家加密重掃。

跑法(倉根目錄)::

    set PYTHONUTF8=1
    python experiments/2026-08-28-costs-and-regrid/run_costs_and_regrid.py

KARST-036 收檔時留下一個未答的問題:輪動驅動器的**換手是固定權重的一百倍**
(3–4 轉/年對 0.03),而那次掃描的成本設為零——所以「相對強弱贏固定權重 2.8 個
百分點」這個結論,從來沒有經過成本這一關。另外,兩個贏家的最優格皆判**孤峰**,
而格只有 16 至 24 格,根本判不出**平原**。

本檔做三件事:

1. **成本前後並列**——四個驅動器的最優格與兩個固定權重對照格,各跑兩次:一次零
   成本(讀回 KARST-036 / KARST-029 的舊運行,一格都不重跑),一次連示例成本。
   兩次是兩個獨立的運行編號,並排擺出對 SPY 年化超額與換手。
2. **加密重掃**——相對強弱與因子動量兩個驅動器,回望期由「1/3/6/9/12」改成**逐月
   1 至 15**,節奏月與季,即每個驅動器 60 格(票上要求不少於 60;KARST-036 原本
   只有 20 格)。零成本與連成本各掃一次,同一個格判兩次,看平原/孤峰的裁決會不會
   被成本翻轉。
3. **分段超額**——2015–2019 / 2020–2022 / 2023–2026 三段各自對 SPY 的年化超額
   (同一批運行,只換檢視視窗重看——重看不重跑,規格 8.5)。

示例成本:**每股 US$0.005 加滑點 5 個基點**。票上寫明它**只是示例**——一組合理的
美股零售經紀數字,不是裁定值。哪一組成本才對是用戶的事(D-008);本檔只把成本
做成可掃描參數,交出數,不裁取值。

**本檔一句 ``set_active_setup`` 都沒有**:掃出來的最優不是現役設定(規格 7.5)。
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

HERE = Path(__file__).resolve().parent

import pandas as pd  # noqa: E402

from karst.data.snapshots import read_price_panel  # noqa: E402
from karst.engine import PricePanel, TradingCosts  # noqa: E402
from karst.gateway.service import Gateway  # noqa: E402
from karst.runs import RunStore  # noqa: E402
from karst.strategies.factor_mix import FACTOR_ETF_SLEEVES  # noqa: E402
from karst.strategies.factor_rotation import DRIVER_PARAMETERS  # noqa: E402
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
    CostPair,
    FactorRotationJob,
    ScoreEntry,
    cost_comparison,
    ensure_factor_rotation_setup,
    provenance_note,
    rotation_grid,
    scoreboard,
    segment_excess,
)

STORE_PATH = REPO / "karst.sqlite"
SNAPSHOT_ROOT = REPO / "data" / "snapshots"
RUNS_ROOT = REPO / "data" / "runs"

SNAPSHOT_ID = "2026-08-27-91a5d51339d9"
ROTATION_STRATEGY = "因子輪動(ETF 版)"
MIX_STRATEGY = "因子混合(ETF 版)"
ENGINE_VERSION = "0.1.0"
MARKET_TICKER = "SPY"

SETUP_PARAM_SET = "掃描基座-KARST-036"
# 對照那邊要**原封不動**沿用 KARST-029 的參數集命名,零成本那次才撞得回同一個運行
# 編號。連成本那次會自動在名字後面加一截成本(見 ``sweep.factor_mix.cost_slug``),
# 所以兩次各自獨立,舊運行一條都不會被改寫。
MIX_PARAM_SET_PREFIX = "掃描w-"

RISK_FREE_RATE = 0.04
WARMUP_BARS = 252
WARMUP_WEIGHTS = {sleeve.weight_key: 0.25 for sleeve in FACTOR_ETF_SLEEVES}

# KARST-036 原本那批取值(零成本最優格由這裡選出來,好與舊結論對得上)。
ORIGINAL_VALUES: dict[str, dict[str, list]] = {
    "factor_momentum": {"lookback_months": [1, 3, 6, 9, 12], "mode": ["winner", "rank"]},
    "relative_strength": {"lookback_months": [1, 3, 6, 9, 12], "fallback": ["cash", "equal"]},
    "inverse_volatility": {"lookback_days": [21, 63, 126, 252], "power": [1.0, 2.0]},
    "trend_switch": {"ma_days": [50, 100, 150, 200], "tilt": [0.5, 0.75, 1.0]},
}
ORIGINAL_CADENCES = ("monthly", "quarterly")

# 加密重掃:回望期**逐月 1 至 15**,節奏月與季。15 × 2 × 2 = 60 格(票上的下限)。
#
# 回望期去到 15 個月,已經長過熱身期(252 根,約一年):頭幾個決策日算不出訊號,
# 那幾格會退回熱身權重並記為「數據不足」。這是驅動器本身的事實,不是缺件。
#
# **節奏刻意只有月與季,沒有 daily**,兩個原因:
#   1. 定義庫(``store``)那張節奏選單只有 daily / monthly / quarterly,weekly 登記
#      不了(引擎認得,兩邊對不上——已在票上舉手);剩下可加的只有 daily。
#   2. daily 那一行每年換手十六轉,與月/季差一個數量級。它一入格,每一個月度格都
#      多了一個差得遠的鄰居,鄰域平均被拉低,平原於是更難出現——量到的變成「加了
#      daily 沒有」,不是參數面本身崎嶇不崎嶇。
# 另外 daily 有一格(因子動量、回望 3 個月、連成本)在指標層撞牆:逐日換倉一隻
# 實體累積到兩千多筆成交,先入先出配對的浮點殘差去到 1.4e-12 股,超過
# ``karst/metrics/trades.py`` 那個 1e-12 的絕對容差,於是報「賣出但手上沒有貨」。
# 那是指標層一個與成本無關的舊有脆弱點(本票不准改 ``metrics/``),已在票上舉手。
DENSE_VALUES: dict[str, dict[str, list]] = {
    "relative_strength": {
        "lookback_months": list(range(1, 16)),
        "fallback": ["cash", "equal"],
    },
    "factor_momentum": {
        "lookback_months": list(range(1, 16)),
        "mode": ["winner", "rank"],
    },
}
DENSE_CADENCES = ("monthly", "quarterly")
DENSE_DRIVERS = ("relative_strength", "factor_momentum")

DRIVER_TITLES = {
    "factor_momentum": "因子動量排名",
    "relative_strength": "相對強弱對 SPY",
    "inverse_volatility": "逆波幅",
    "trend_switch": "大市趨勢開關",
}

SEGMENTS = (
    ("2015–2019", "2015-01-02", "2019-12-31"),
    ("2020–2022", "2020-01-01", "2022-12-31"),
    ("2023–2026", "2023-01-01", "2026-08-26"),
)

FIXED_BEST = {
    "weight_quality": 0.0, "weight_value": 0.05,
    "weight_momentum": 0.95, "weight_low_vol": 0.0,
}
FIXED_EVEN = {sleeve.weight_key: 0.25 for sleeve in FACTOR_ETF_SLEEVES}
CONTROLS = (
    ("固定權重·動能95價值5", FIXED_BEST),
    ("固定權重·各佔25%", FIXED_EVEN),
)


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
    parser = argparse.ArgumentParser(description="交易成本重評與加密重掃(KARST-043)")
    parser.add_argument(
        "--fee-model", default="per_share", choices=["per_share", "fraction_of_value"],
        help="手續費型別:每股固定金額,還是按成交金額比例",
    )
    parser.add_argument(
        "--fee-rate", type=float, default=0.005,
        help="手續費:每股型別即每股多少錢(示例 0.005),比例型別即比例(0.001 = 10 基點)",
    )
    parser.add_argument(
        "--slippage", type=float, default=0.0005, help="滑點,佔成交價比例(示例 0.0005 = 5 基點)"
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
        "--drivers", default=",".join(DENSE_DRIVERS), help="加密重掃哪幾個驅動器,逗號分隔"
    )
    parser.add_argument(
        "--skip-dense", action="store_true", help="只做成本前後並列,不做加密重掃"
    )
    return parser.parse_args()


def _progress(label: str, every: int = 10):
    began = time.perf_counter()

    def report(index: int, total: int, cell) -> None:
        if index % every == 0 or index == total:
            elapsed = time.perf_counter() - began
            print(
                f"  [{label}] {index}/{total} 格,已用 {elapsed:.0f} 秒"
                f"(每格 {elapsed / index:.2f} 秒)",
                flush=True,
            )

    return report


def _rotation_job(gateway, panel, driver_key, period, version_no, warmup, costs):
    return FactorRotationJob(
        gateway=gateway,
        panel=panel,
        driver_key=driver_key,
        strategy_name=ROTATION_STRATEGY,
        snapshot_id=SNAPSHOT_ID,
        engine_version=ENGINE_VERSION,
        param_set_prefix=f"掃描r-{driver_key}-",
        period_start=period[0],
        period_end=period[1],
        warmup_bars=warmup,
        warmup_weights=WARMUP_WEIGHTS,
        strategy_version_no=version_no,
        market_ticker=MARKET_TICKER,
        costs=costs,
    )


def _mix_job(gateway, panel, period, version_no, costs):
    return FactorMixJob(
        gateway=gateway,
        panel=panel,
        sleeves=FACTOR_ETF_SLEEVES,
        strategy_name=MIX_STRATEGY,
        snapshot_id=SNAPSHOT_ID,
        engine_version=ENGINE_VERSION,
        param_set_prefix=MIX_PARAM_SET_PREFIX,
        period_start=period[0],
        period_end=period[1],
        strategy_version_no=version_no,
        costs=costs,
    )


def _cell_summary(sweep, cell) -> dict | None:
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
        "max_drawdown": run_cell.metrics.max_drawdown,
        "turnover": run_cell.metrics.turnover,
        "annual_excess": dict(run_cell.annual_excess),
        "run_id": run_cell.run_id,
    }


def main() -> None:
    args = parse_args()
    os.environ.setdefault("KARST_WRITER", "KARST-043-costs")
    costs = TradingCosts(
        fee_model=args.fee_model,
        fee_rate=args.fee_rate,
        slippage_fraction=args.slippage,
    )
    zero = TradingCosts.zero()
    dense_drivers = tuple(d.strip() for d in args.drivers.split(",") if d.strip())
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
        print(f"示例成本:{costs.label} —— {costs.as_params()}", flush=True)

        rotation = ensure_factor_rotation_setup(
            gateway,
            strategy_name=ROTATION_STRATEGY,
            snapshot_id=SNAPSHOT_ID,
            setup_param_set_name=SETUP_PARAM_SET,
            setup_weights=WARMUP_WEIGHTS,
            cadence=ORIGINAL_CADENCES[0],
            description="KARST-036 驅動器掃描的基座,不是現役設定",
        )
        mix_version = store.get_strategy_version(MIX_STRATEGY)
        runs = RunStore(store, root=RUNS_ROOT)

        summary: dict = {
            "ticket": "KARST-043",
            "snapshot_id": SNAPSHOT_ID,
            "period": list(period),
            "trading_days": len(panel.dates),
            "warmup_bars": args.warmup,
            "warmup_weights": WARMUP_WEIGHTS,
            "objective": args.objective,
            "costs": costs.as_params() | {"label": costs.label},
            "thresholds": {
                "min_trades": args.min_trades,
                "lonely_peak_margin": args.margin,
                "plateau_quantile": args.quantile,
            },
            "market_ticker": MARKET_TICKER,
            "segments": [list(s) for s in SEGMENTS],
        }

        # ------------------------------------------------------------------
        # 第一部分:成本前後並列(四個驅動器最優格 + 兩個固定權重對照格)
        # ------------------------------------------------------------------
        print("\n=== 第一部分:成本前後並列 ===", flush=True)
        pairs: list[CostPair] = []
        entries_before: list[ScoreEntry] = []
        entries_after: list[ScoreEntry] = []
        rerun: dict = {}

        for driver_key in ORIGINAL_VALUES:
            title = DRIVER_TITLES[driver_key]
            grid = rotation_grid(
                driver_key, values=ORIGINAL_VALUES[driver_key], cadences=ORIGINAL_CADENCES
            )
            before = run_sweep(
                runs=runs, grid=grid,
                job=_rotation_job(
                    gateway, panel, driver_key, period, rotation.version_no, args.warmup, None
                ),
                risk_free_rate=RISK_FREE_RATE, snapshot_root=SNAPSHOT_ROOT,
            )
            verdict_before = judge(
                before.scores(args.objective), grid, objective=args.objective,
                min_trades=args.min_trades, lonely_peak_margin=args.margin,
                plateau_quantile=args.quantile,
            )
            best = verdict_before.best
            if best is None:
                print(f"  【{title}】零成本掃描一格有效的都沒有,略過", flush=True)
                continue

            point = best.point
            after = run_sweep(
                runs=runs, grid=ExplicitGrid([point], label=f"{title}·最優格(連成本)"),
                job=_rotation_job(
                    gateway, panel, driver_key, period, rotation.version_no, args.warmup, costs
                ),
                risk_free_rate=RISK_FREE_RATE, snapshot_root=SNAPSHOT_ROOT,
            )
            before_cell = before.cell_for(point)
            after_cell = after.cells[0]
            label = f"{title}·最優格"
            pairs.append(
                CostPair(
                    label=label, kind="驅動器",
                    before=before_cell, after=after_cell,
                    verdict_before=best,
                    note=f"零成本掃描({len(before)} 格)的單點最優;{best.verdict}",
                )
            )
            entries_before.append(
                ScoreEntry(label=label, kind="驅動器", cell=before_cell, verdict=best)
            )
            entries_after.append(ScoreEntry(label=label, kind="驅動器", cell=after_cell))
            print(
                f"  【{title}】{point.label}|零成本讀回 {before.reused}/{len(before)} 格;"
                f"連成本今次跑 {after.executed} 格",
                flush=True,
            )

        # 兩個固定權重對照格(月度與季度各一)
        control_points = [
            reference_point(FACTOR_ETF_SLEEVES, weights, cadence=cadence)
            for _, weights in CONTROLS
            for cadence in ORIGINAL_CADENCES
        ]
        control_grid = ExplicitGrid(control_points, label="對照格(固定權重)")
        control_before = run_sweep(
            runs=runs, grid=control_grid,
            job=_mix_job(gateway, panel, period, mix_version.version_no, None),
            risk_free_rate=RISK_FREE_RATE, snapshot_root=SNAPSHOT_ROOT,
        )
        control_after = run_sweep(
            runs=runs, grid=control_grid,
            job=_mix_job(gateway, panel, period, mix_version.version_no, costs),
            risk_free_rate=RISK_FREE_RATE, snapshot_root=SNAPSHOT_ROOT,
        )
        print(
            f"  【固定權重對照】零成本讀回 {control_before.reused}/{len(control_before)} 格"
            f"(KARST-029 的舊運行);連成本今次跑 {control_after.executed} 格",
            flush=True,
        )
        for point in control_points:
            cadence = point.get(CADENCE_AXIS)
            name = next(
                label for label, weights in CONTROLS
                if all(point.get(key) == value for key, value in weights.items())
            )
            label = f"{name}({cadence})"
            before_cell = control_before.cell_for(point)
            after_cell = control_after.cell_for(point)
            pairs.append(
                CostPair(
                    label=label, kind="固定權重對照",
                    before=before_cell, after=after_cell,
                    note="KARST-029 固定權重,不在任何掃描格上",
                )
            )
            entries_before.append(ScoreEntry(label=label, kind="對照", cell=before_cell))
            entries_after.append(ScoreEntry(label=label, kind="對照", cell=after_cell))

        comparison = cost_comparison(pairs, objective=args.objective, costs=costs)
        comparison.to_csv(out / "成本前後並列表.csv", index=False, encoding="utf-8-sig")
        summary["cost_comparison"] = json.loads(comparison.to_json(orient="records"))

        # 成本前後各一張成績表(對照仍然是季度那兩個固定權重)
        baselines = [
            entry.label for entry in entries_before
            if entry.kind == "對照" and entry.label.endswith("(quarterly)")
        ]
        for tag, entries in (("成本前", entries_before), ("成本後", entries_after)):
            table = scoreboard(entries, objective=args.objective, baselines=baselines)
            table.to_csv(out / f"成績表-{tag}.csv", index=False, encoding="utf-8-sig")
            summary[f"scoreboard_{tag}"] = json.loads(table.to_json(orient="records"))

        # 分段超額:成本前後各一份(同一批運行,只換檢視視窗重看)
        for tag, entries in (("成本前", entries_before), ("成本後", entries_after)):
            segments = segment_excess(
                runs, entries, segments=SEGMENTS, risk_free_rate=RISK_FREE_RATE,
                benchmark=MARKET_TICKER, snapshot_root=SNAPSHOT_ROOT,
            )
            segments.to_csv(out / f"分段超額-{tag}.csv", index=False, encoding="utf-8-sig")
            summary[f"segments_{tag}"] = json.loads(segments.to_json(orient="records"))

        rerun["run_ids"] = sorted(
            {pair.before.run_id for pair in pairs} | {pair.after.run_id for pair in pairs}
        )
        summary["rerun"] = rerun

        with pd.option_context("display.width", 220, "display.max_columns", 40):
            print("\n--- 成本前後並列(對 SPY 年化超額與換手) ---", flush=True)
            print(
                comparison[
                    [
                        "名稱", f"成本前{args.objective}", f"成本後{args.objective}",
                        "成本代價", "成本前換手", "成本後換手",
                    ]
                ].to_string(index=False),
                flush=True,
            )

        # ------------------------------------------------------------------
        # 第二部分:加密重掃(相對強弱與因子動量)
        # ------------------------------------------------------------------
        if not args.skip_dense:
            print("\n=== 第二部分:加密重掃 ===", flush=True)
            summary["dense"] = {}
            for driver_key in dense_drivers:
                title = DRIVER_TITLES[driver_key]
                grid = rotation_grid(
                    driver_key, values=DENSE_VALUES[driver_key], cadences=DENSE_CADENCES
                )
                print(f"\n【{title}】{grid.describe()}({len(grid)} 格)", flush=True)
                driver_out = out / f"dense-{driver_key}"

                results = {}
                for tag, cost in (("成本前", None), ("成本後", costs)):
                    sweep = run_sweep(
                        runs=runs, grid=grid,
                        job=_rotation_job(
                            gateway, panel, driver_key, period, rotation.version_no,
                            args.warmup, cost,
                        ),
                        risk_free_rate=RISK_FREE_RATE, snapshot_root=SNAPSHOT_ROOT,
                        progress=_progress(f"{title}·{tag}", every=12),
                    )
                    verdict = judge(
                        sweep.scores(args.objective), grid, objective=args.objective,
                        min_trades=args.min_trades, lonely_peak_margin=args.margin,
                        plateau_quantile=args.quantile,
                    )
                    print(
                        f"  {tag}:{sweep.executed} 格今次跑、{sweep.reused} 格讀回;"
                        f"判讀 {verdict.summary()}",
                        flush=True,
                    )
                    results[tag] = (sweep, verdict)

                    used = zero if cost is None else cost
                    axes = [*DRIVER_PARAMETERS[driver_key], CADENCE_AXIS]
                    charts = list(
                        draw_projection_set(
                            verdict, driver_out, axes=axes,
                            title=f"{title}·加密重掃({tag})",
                            subtitle=(
                                f"{args.objective}|{period[0]} ~ {period[1]}|{used.label}"
                            ),
                            prefix=f"projection-{'before' if cost is None else 'after'}",
                        )
                    )
                    write_report(
                        sweep, verdict, driver_out,
                        title=f"因子輪動·{title}·加密重掃({tag})",
                        charts=charts,
                        filename=f"報告-{tag}.md",
                        notes=(
                            provenance_note(
                                snapshot_id=SNAPSHOT_ID, period=period, costs=used,
                                run_ids=sweep.run_ids(),
                                extra=(
                                    f"- 掃描格:回望期逐月 1 至 "
                                    f"{max(DENSE_VALUES[driver_key]['lookback_months'])} 個月 × "
                                    f"{'/'.join(DENSE_CADENCES)} 兩個節奏,共 {len(grid)} 格"
                                    f"(KARST-036 原本只有 20 格)"
                                ),
                            )
                            + "\n\n"
                            + "回望期由「1/3/6/9/12」改成**逐月**之後,「一步之遙」由三個月"
                            "變成一個月——鄰域的定義本身變了,所以本份判讀的平原/孤峰"
                            "**不可以與 KARST-036 那次直接比較**。\n\n"
                            f"熱身期 {args.warmup} 根 K 線,期間四格各佔 25%;訊號一律只用"
                            "決策日收工前的數據,成交在下一根 K 線的開價(D-021 第 3 條)。"
                        ),
                    )

                before_sweep, before_verdict = results["成本前"]
                after_sweep, after_verdict = results["成本後"]

                # 加密格上的最優格,成本前後並列一次(這是加密格自己的贏家,
                # 與第一部分那個「原本 20 格的贏家」未必是同一格)
                dense_pairs: list[CostPair] = []
                dense_entries: list[ScoreEntry] = []
                for kind, cell_before in (
                    ("加密最優", before_verdict.best),
                    ("加密鄰域最高", before_verdict.most_robust),
                ):
                    if cell_before is None:
                        continue
                    point = cell_before.point
                    label = f"{title}·{kind}"
                    if any(pair.label == label for pair in dense_pairs):
                        continue
                    dense_pairs.append(
                        CostPair(
                            label=label, kind=kind,
                            before=before_sweep.cell_for(point),
                            after=after_sweep.cell_for(point),
                            verdict_before=cell_before,
                            verdict_after=after_verdict.cell_for(point),
                        )
                    )
                    dense_entries.append(
                        ScoreEntry(
                            label=label, kind=kind, cell=after_sweep.cell_for(point),
                            verdict=after_verdict.cell_for(point),
                        )
                    )
                # 連成本之後,加密格自己的贏家(成本後才選的那一格)
                after_best = after_verdict.best
                if after_best is not None:
                    label = f"{title}·成本後最優"
                    if not any(pair.label == label for pair in dense_pairs):
                        dense_pairs.append(
                            CostPair(
                                label=label, kind="成本後最優",
                                before=before_sweep.cell_for(after_best.point),
                                after=after_sweep.cell_for(after_best.point),
                                verdict_before=before_verdict.cell_for(after_best.point),
                                verdict_after=after_best,
                            )
                        )
                        dense_entries.append(
                            ScoreEntry(
                                label=label, kind="成本後最優",
                                cell=after_sweep.cell_for(after_best.point),
                                verdict=after_best,
                            )
                        )

                dense_table = cost_comparison(
                    dense_pairs, objective=args.objective, costs=costs
                )
                dense_table.to_csv(
                    driver_out / "成本前後並列表.csv", index=False, encoding="utf-8-sig"
                )
                dense_segments = segment_excess(
                    runs, dense_entries, segments=SEGMENTS, risk_free_rate=RISK_FREE_RATE,
                    benchmark=MARKET_TICKER, snapshot_root=SNAPSHOT_ROOT,
                )
                dense_segments.to_csv(
                    driver_out / "分段超額-成本後.csv", index=False, encoding="utf-8-sig"
                )

                summary["dense"][driver_key] = {
                    "title": title,
                    "grid": grid.describe(),
                    "cells": len(grid),
                    "cadences": list(DENSE_CADENCES),
                    "lookback_months": DENSE_VALUES[driver_key]["lookback_months"],
                    "成本前": {
                        "executed": before_sweep.executed,
                        "reused": before_sweep.reused,
                        "seconds": round(before_sweep.seconds, 2),
                        "counts": {
                            "plateau": len(before_verdict.plateaus),
                            "lonely_peak": len(before_verdict.lonely_peaks),
                            "invalid": len(before_verdict.invalid_cells),
                        },
                        "plateau_threshold": before_verdict.plateau_threshold,
                        "best_single": _cell_summary(before_sweep, before_verdict.best),
                        "best_neighbourhood": _cell_summary(
                            before_sweep, before_verdict.most_robust
                        ),
                        "top5": [
                            _cell_summary(before_sweep, c) for c in before_verdict.top(5)
                        ],
                    },
                    "成本後": {
                        "executed": after_sweep.executed,
                        "reused": after_sweep.reused,
                        "seconds": round(after_sweep.seconds, 2),
                        "counts": {
                            "plateau": len(after_verdict.plateaus),
                            "lonely_peak": len(after_verdict.lonely_peaks),
                            "invalid": len(after_verdict.invalid_cells),
                        },
                        "plateau_threshold": after_verdict.plateau_threshold,
                        "best_single": _cell_summary(after_sweep, after_verdict.best),
                        "best_neighbourhood": _cell_summary(
                            after_sweep, after_verdict.most_robust
                        ),
                        "top5": [_cell_summary(after_sweep, c) for c in after_verdict.top(5)],
                    },
                    "cost_comparison": json.loads(dense_table.to_json(orient="records")),
                    "segments": json.loads(dense_segments.to_json(orient="records")),
                }

                with pd.option_context("display.width", 220, "display.max_columns", 40):
                    print(f"\n--- {title}·加密格成本前後 ---", flush=True)
                    print(
                        dense_table[
                            [
                                "名稱", "參數", f"成本前{args.objective}",
                                f"成本後{args.objective}", "成本代價", "成本後換手",
                                "成本前裁決", "成本後裁決",
                            ]
                        ].to_string(index=False),
                        flush=True,
                    )

        (out / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n落檔:{out}", flush=True)


if __name__ == "__main__":
    main()
