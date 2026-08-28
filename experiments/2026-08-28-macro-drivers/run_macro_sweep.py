"""KARST-040:宏觀驅動器矩陣掃描——價格以外的訊號推動移權,值不值得。

跑法(倉根目錄)::

    set PYTHONUTF8=1
    python experiments/2026-08-28-macro-drivers/run_macro_sweep.py

做七件事:

1. 由價格快照砌價格面板(四隻因子 ETF 加 SPY)。**編號不寫死在這裡**:七支成績
   腳本共用 ``experiments/snapshot_ids.py`` 那一份,重抓之後只改那一個檔
   (現用 ``PRICE_FACTOR_ETF``,舊 ``2026-08-27-91a5d51339d9``)。
2. 抓宏觀序列入**宏觀快照**(第一次要連網;之後等價重用,沿用原編號原檔案),
   對齊價格快照那條主日曆。宏觀序列**不是可投資對象**——處置見 ``karst.data.macro``。
3. 六個宏觀驅動器各掃一個參數格(門檻/回望期 × 押注比重 × 換倉節奏)。
   **主報那一份用零成本**(D-030:基準情境不計交易成本),跑法加
   ``--fee-rate 0 --slippage 0``,落 ``results/``;連示例成本(每股 US$0.005 +
   滑點 5 個基點)那一份只作對照,落 ``results-連成本/``。命令列預設仍是連成本,
   所以主報那一句一定要顯式寫出兩個零——這是刻意的,免得口徑靜靜地變。
4. 逐個驅動器判平原 / 孤峰,出報告與投影圖。
5. 把六個宏觀最優格、兩個**價格驅動器**最優格(KARST-043 的加密最優)、四個
   **固定權重對照格**擺上**同一張成績表**。
6. 分三段時期(2015–2019 / 2020–2022 / 2023–2026)列對 SPY 的年化超額。
7. 第二層宏觀序列(美元指數、油價、IWF/IWD、IWM/SPY)只作**對照**列表,
   不做驅動器參數格(用戶 2026-08-28 裁定)。

**本檔一句 ``set_active_setup`` 都沒有**:掃出來的最優不是現役設定(規格 7.5)。
只交表與判讀,不裁定哪一個驅動器該用(D-008)。
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

from snapshot_ids import MACRO as MACRO_SNAPSHOT_ID  # noqa: E402
from snapshot_ids import PRICE_FACTOR_ETF  # noqa: E402

HERE = Path(__file__).resolve().parent

# 掃描編號(sweep id):一次掃描的識別字,逐格隨運行入庫(KARST-054)。慣例跟參數
# 掃描頁認掃描那個一樣——落檔目錄的倉內相對路徑;同一個實驗跑幾次掃描就補字尾分開。
EXPERIMENT_ID = HERE.relative_to(REPO).as_posix()

import pandas as pd  # noqa: E402

from karst.data import (  # noqa: E402
    DRIVER_TIER_CODES,
    REFERENCE_TIER_CODES,
    YFinanceMacroSource,
    build_macro_snapshot,
    macro_coverage,
    read_macro_frame,
    read_macro_panel,
)
from karst.data.snapshots import read_calendar, read_price_panel  # noqa: E402
from karst.engine import PricePanel, TradingCosts  # noqa: E402
from karst.gateway.service import Gateway  # noqa: E402
from karst.runs import RunStore  # noqa: E402
from karst.strategies.factor_mix import FACTOR_ETF_SLEEVES  # noqa: E402
from karst.strategies.factor_rotation import (  # noqa: E402
    DRIVER_PARAMETERS,
    EXTERNAL_DATA,
    MACRO_DRIVER_KEYS,
    macro_series_needed,
)
from karst.sweep import (  # noqa: E402
    CADENCE_AXIS,
    ExplicitGrid,
    FactorMixJob,
    SweepPoint,
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
    provenance_note,
    rotation_grid,
    scoreboard,
    segment_excess,
)

STORE_PATH = REPO / "karst.sqlite"
SNAPSHOT_ROOT = REPO / "data" / "snapshots"
MACRO_ROOT = REPO / "data" / "macro_snapshots"
RUNS_ROOT = REPO / "data" / "runs"

SNAPSHOT_ID = PRICE_FACTOR_ETF   # 見 experiments/snapshot_ids.py(KARST-057 重建)
ROTATION_STRATEGY = "因子輪動(ETF 版)"
MIX_STRATEGY = "因子混合(ETF 版)"
SETUP_PARAM_SET = "掃描基座-KARST-036"
MIX_PARAM_SET_PREFIX = "掃描w-"
ENGINE_VERSION = "0.1.0"
MARKET_TICKER = "SPY"
RISK_FREE_RATE = 0.04
WARMUP_BARS = 252
WARMUP_WEIGHTS = {sleeve.weight_key: 0.25 for sleeve in FACTOR_ETF_SLEEVES}

SEGMENTS = (
    ("2015–2019", "2015-01-02", "2019-12-31"),
    ("2020–2022", "2020-01-01", "2022-12-31"),
    ("2023–2026", "2023-01-01", "2026-08-26"),
)

# 六個宏觀驅動器的掃描取值。**無預設值**(D-008 第 3 條)——掃哪幾個門檻、
# 哪幾個回望期,全部在這裡寫明。
MACRO_VALUES: dict[str, dict[str, tuple]] = {
    "vix_level": {"threshold": (16.0, 18.0, 20.0, 22.0, 25.0), "tilt": (0.5, 0.75, 1.0)},
    "vix_term": {"threshold": (0.90, 0.95, 1.00, 1.05, 1.10), "tilt": (0.5, 0.75, 1.0)},
    "credit_trend": {"lookback_days": (10, 20, 40, 60, 120), "tilt": (0.5, 0.75, 1.0)},
    "curve_trend": {"lookback_days": (10, 20, 40, 60, 120), "tilt": (0.5, 0.75, 1.0)},
    "rate_trend": {"lookback_days": (10, 20, 40, 60, 120), "tilt": (0.5, 0.75, 1.0)},
    "fed_expectation": {"lookback_days": (10, 20, 40, 60, 120), "tilt": (0.5, 0.75, 1.0)},
}

DRIVER_TITLES = {
    "vix_level": "VIX 水平開關",
    "vix_term": "VIX 期限結構開關",
    "credit_trend": "信用利差變化方向",
    "curve_trend": "曲線斜度變化方向",
    "rate_trend": "10 年息率趨勢",
    "fed_expectation": "聯邦基金利率預期方向",
}

# 價格驅動器的對照格:KARST-043 加密重掃的兩個最優格(連成本)。
# 參數集名前綴與熱身期照抄 KARST-036/043,所以這兩格**一格都不會重跑**,
# 直接由運行庫讀回舊運行。
PRICE_BEST = {
    "relative_strength": (
        ("lookback_months", 7),
        ("fallback", "cash"),
        (CADENCE_AXIS, "monthly"),
    ),
    "factor_momentum": (
        ("lookback_months", 8),
        ("mode", "winner"),
        (CADENCE_AXIS, "monthly"),
    ),
}
PRICE_TITLES = {
    "relative_strength": "相對強弱對 SPY",
    "factor_momentum": "因子動量排名",
}

FIXED_BEST = {
    "weight_quality": 0.0,
    "weight_value": 0.05,
    "weight_momentum": 0.95,
    "weight_low_vol": 0.0,
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


def _repo_path(path: Path) -> str:
    """報告路徑寫成相對倉根;輸出目錄搬到倉外(試跑)就照原樣寫。"""
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def _progress(label: str, every: int = 10):
    began = time.perf_counter()

    def progress(index: int, total: int, cell) -> None:
        if index % every == 0 or index == total:
            elapsed = time.perf_counter() - began
            print(
                f"  {label} {index}/{total} 格,已用 {elapsed:.0f} 秒"
                f"(每格 {elapsed / index:.2f} 秒)",
                flush=True,
            )

    return progress


def main() -> int:
    parser = argparse.ArgumentParser(description="KARST-040 宏觀驅動器矩陣掃描")
    parser.add_argument("--out", default=None, help="輸出目錄,預設 results/")
    parser.add_argument("--objective", default="annual_excess:SPY", help="目標指標")
    parser.add_argument("--min-trades", type=int, default=30, help="少過這個成交筆數判無效")
    parser.add_argument("--margin", type=float, default=0.005, help="孤峰要高出鄰域平均多少")
    parser.add_argument("--quantile", type=float, default=0.90, help="高地由哪一個分位起計")
    parser.add_argument("--warmup", type=int, default=WARMUP_BARS, help="熱身期(根 K 線)")
    parser.add_argument("--fee-model", default="per_share", choices=["per_share", "fraction_of_value"])
    parser.add_argument("--fee-rate", type=float, default=0.005, help="示例手續費:每股 US$")
    parser.add_argument("--slippage", type=float, default=0.0005, help="示例滑點,佔成交價比例")
    parser.add_argument(
        "--drivers",
        default=",".join(MACRO_DRIVER_KEYS),
        help="要掃的宏觀驅動器,逗號分隔",
    )
    parser.add_argument(
        "--macro-snapshot", default=MACRO_SNAPSHOT_ID,
        help="沿用某個宏觀快照編號,不再抓數(預設沿用現役那個;給 new 即重抓一份)",
    )
    args = parser.parse_args()

    out = Path(args.out) if args.out else HERE / "results"
    out.mkdir(parents=True, exist_ok=True)
    drivers = tuple(d.strip() for d in args.drivers.split(",") if d.strip())

    costs = TradingCosts(
        fee_model=args.fee_model, fee_rate=args.fee_rate, slippage_fraction=args.slippage
    )
    print(f"示例成本:{costs.label} —— {costs.as_params()}", flush=True)

    os.environ.setdefault("KARST_WRITER", "KARST-040-macro")

    with Gateway.open(str(STORE_PATH)) as gateway:
        store = gateway.store
        panel = build_panel(store)
        period = (str(panel.dates[0].date()), str(panel.dates[-1].date()))
        runs = RunStore(store, root=RUNS_ROOT)
        print(
            f"價格面板:{len(panel.dates)} 個交易日,{period[0]} ~ {period[1]},"
            f"{len(panel.entity_ids)} 個實體",
            flush=True,
        )

        # ---- 1. 宏觀快照 ----
        calendar = read_calendar(store, SNAPSHOT_ID, root=SNAPSHOT_ROOT)
        if args.macro_snapshot and args.macro_snapshot != "new":
            macro_id = args.macro_snapshot
            print(f"沿用宏觀快照 {macro_id}(不抓數)", flush=True)
        else:
            print("抓宏觀序列(第一次要連網;等價即沿用原編號)……", flush=True)
            macro_snapshot = build_macro_snapshot(
                store,
                start=calendar[0],
                end=calendar[-1],
                calendar=calendar,
                calendar_ticker=MARKET_TICKER,
                source=YFinanceMacroSource(),
                root=MACRO_ROOT,
                taken_on=None,      # 抓取當日;編號以它做前綴,不寫死在腳本裡
            )
            macro_id = macro_snapshot.snapshot_id
            print(
                f"宏觀快照 {macro_id}"
                f"{'(沿用已凍結的等價快照)' if macro_snapshot.reused else '(新凍結)'}:"
                f"{macro_snapshot.rows} 列、{len(macro_snapshot.series)} 條序列",
                flush=True,
            )
            for note in macro_snapshot.notes:
                print(f"  註記:{note}", flush=True)

        macro_panel = read_macro_panel(store, macro_id, root=MACRO_ROOT)
        coverage = macro_coverage(read_macro_frame(store, macro_id, root=MACRO_ROOT))
        coverage.to_csv(out / "宏觀序列齊全度.csv", index=False, encoding="utf-8-sig")

        # ---- 2. 策略基座 ----
        rotation = ensure_factor_rotation_setup(
            gateway,
            strategy_name=ROTATION_STRATEGY,
            snapshot_id=SNAPSHOT_ID,
            setup_param_set_name=SETUP_PARAM_SET,
            setup_weights=WARMUP_WEIGHTS,
            cadence="monthly",
            description="KARST-036 驅動器掃描的基座,不是現役設定",
        )
        mix_version = store.get_strategy_version(MIX_STRATEGY)

        entries: list[ScoreEntry] = []
        summary: dict[str, object] = {
            "ticket": "KARST-040",
            "price_snapshot_id": SNAPSHOT_ID,
            "macro_snapshot_id": macro_id,
            "period": list(period),
            "trading_days": len(panel.dates),
            "warmup_bars": args.warmup,
            "warmup_weights": WARMUP_WEIGHTS,
            "objective": args.objective,
            "costs": costs.as_params(),
            "costs_label": costs.label,
            "thresholds": {
                "min_trades": args.min_trades,
                "lonely_peak_margin": args.margin,
                "plateau_quantile": args.quantile,
            },
            "segments": [list(s) for s in SEGMENTS],
            "external_data": [dict(row) for row in EXTERNAL_DATA],
            "macro_series_first_tier": list(DRIVER_TIER_CODES),
            "macro_series_second_tier": list(REFERENCE_TIER_CODES),
            "macro_coverage": json.loads(coverage.to_json(orient="records")),
            "drivers": {},
        }
        all_run_ids: list[str] = []

        # ---- 3. 六個宏觀驅動器 ----
        for driver_key in drivers:
            title = DRIVER_TITLES.get(driver_key, driver_key)
            series = macro_series_needed(driver_key)
            grid = rotation_grid(
                driver_key, values=MACRO_VALUES[driver_key], cadences=("monthly", "quarterly")
            )
            print(f"\n=== {title}({driver_key}):{len(grid)} 格,序列 {'、'.join(series)} ===", flush=True)

            job = FactorRotationJob(
                gateway=gateway,
                panel=panel,
                driver_key=driver_key,
                strategy_name=ROTATION_STRATEGY,
                snapshot_id=SNAPSHOT_ID,
                engine_version=ENGINE_VERSION,
                param_set_prefix=f"掃描mac-{driver_key}-",
                period_start=period[0],
                period_end=period[1],
                warmup_bars=args.warmup,
                warmup_weights=WARMUP_WEIGHTS,
                strategy_version_no=rotation.version_no,
                market_ticker=MARKET_TICKER,
                costs=costs,
                macro=macro_panel,
                macro_snapshot_id=macro_id,
            )
            sweep = run_sweep(
                runs=runs,
                grid=grid,
                job=job,
                sweep_id=f"{EXPERIMENT_ID}/mac-{driver_key}",
                risk_free_rate=RISK_FREE_RATE,
                snapshot_root=SNAPSHOT_ROOT,
                progress=_progress(title, every=10),
            )
            print(
                f"  掃描完成:{len(sweep)} 格,{sweep.executed} 格今次跑、"
                f"{sweep.reused} 格讀回舊運行",
                flush=True,
            )
            all_run_ids.extend(sweep.run_ids())

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
                    subtitle=(
                        f"{args.objective}|{period[0]} ~ {period[1]}|"
                        f"價格快照 {SNAPSHOT_ID}|宏觀快照 {macro_id}"
                    ),
                    prefix="projection",
                )
            )
            report = write_report(
                sweep,
                verdict,
                driver_out,
                title=f"宏觀驅動器·{title}(對 SPY 年化超額,連成本)",
                charts=charts,
                notes=provenance_note(
                    snapshot_id=SNAPSHOT_ID,
                    period=period,
                    costs=costs,
                    run_ids=sweep.run_ids(),
                    extra=(
                        f"- 宏觀快照:`{macro_id}`(序列 {'、'.join(series)};"
                        "知情時間=收市後可得;宏觀序列不是可投資對象,只影響四格怎樣分)"
                    ),
                ),
            )

            best, robust = verdict.best, verdict.most_robust
            if best is not None:
                entries.append(
                    ScoreEntry(
                        label=f"宏觀·{title}·最優格",
                        kind="宏觀驅動器",
                        cell=sweep.cell_for(best.point),
                        verdict=best,
                        note=f"序列 {'、'.join(series)}",
                    )
                )
            if robust is not None and (best is None or robust.point != best.point):
                entries.append(
                    ScoreEntry(
                        label=f"宏觀·{title}·鄰域平均最高",
                        kind="宏觀驅動器",
                        cell=sweep.cell_for(robust.point),
                        verdict=robust,
                        note="穩健平原的中心",
                    )
                )

            summary["drivers"][driver_key] = {  # type: ignore[index]
                "title": title,
                "series": list(series),
                "cells": len(sweep),
                "verdict_summary": verdict.summary(),
                "best_single": None
                if best is None
                else {
                    "point": best.point.label,
                    "value": best.value,
                    "verdict": best.verdict,
                    "neighbourhood_mean": best.neighbourhood_mean,
                    "trades": best.trades,
                    "run_id": sweep.cell_for(best.point).run_id,
                },
                "best_neighbourhood": None
                if robust is None
                else {
                    "point": robust.point.label,
                    "value": robust.value,
                    "verdict": robust.verdict,
                    "neighbourhood_mean": robust.neighbourhood_mean,
                    "run_id": sweep.cell_for(robust.point).run_id,
                },
                "report": _repo_path(report),
            }

        # ---- 4. 價格驅動器對照格(KARST-043 的加密最優,讀回舊運行) ----
        print("\n=== 價格驅動器對照格(KARST-043 加密最優,連成本) ===", flush=True)
        for driver_key, values in PRICE_BEST.items():
            point = SweepPoint(values=values)
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
                costs=costs,
            )
            sweep = run_sweep(
                runs=runs,
                grid=ExplicitGrid([point], label=f"價格對照·{driver_key}"),
                job=job,
                sweep_id=f"{EXPERIMENT_ID}/價格對照·{driver_key}",
                risk_free_rate=RISK_FREE_RATE,
                snapshot_root=SNAPSHOT_ROOT,
            )
            cell = sweep.cells[0]
            all_run_ids.extend(sweep.run_ids())
            print(
                f"  {PRICE_TITLES[driver_key]}:{point.label} → "
                f"{cell.value_of(args.objective):+.4%}"
                f"({'讀回舊運行' if cell.reused else '今次跑'})",
                flush=True,
            )
            entries.append(
                ScoreEntry(
                    label=f"價格·{PRICE_TITLES[driver_key]}·最優格",
                    kind="價格驅動器",
                    cell=cell,
                    note="KARST-043 加密重掃的最優格(孤峰)",
                )
            )

        # ---- 5. 固定權重對照格 ----
        print("\n=== 固定權重對照格 ===", flush=True)
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
            costs=costs,
        )
        controls = [("固定權重·動能95價值5", FIXED_BEST), ("固定權重·各佔25%", FIXED_EVEN)]
        control_points = [
            reference_point(FACTOR_ETF_SLEEVES, weights, cadence=cadence)
            for _, weights in controls
            for cadence in ("monthly", "quarterly")
        ]
        control_sweep = run_sweep(
            runs=runs,
            grid=ExplicitGrid(control_points, label="對照格(固定權重)"),
            job=mix_job,
            sweep_id=f"{EXPERIMENT_ID}/固定權重對照",
            risk_free_rate=RISK_FREE_RATE,
            snapshot_root=SNAPSHOT_ROOT,
        )
        all_run_ids.extend(control_sweep.run_ids())
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
            print(f"  {label}:{cell.value_of(args.objective):+.4%}", flush=True)

        # ---- 6. 一張成績表 + 分三段 ----
        baselines = [
            label for label in control_labels if label.endswith("(quarterly)")
        ] or control_labels
        table = scoreboard(entries, objective=args.objective, baselines=baselines)
        table.to_csv(out / "成績表.csv", index=False, encoding="utf-8-sig")

        segments = segment_excess(
            runs,
            entries,
            segments=SEGMENTS,
            risk_free_rate=RISK_FREE_RATE,
            benchmark=MARKET_TICKER,
            snapshot_root=SNAPSHOT_ROOT,
        )
        segments.to_csv(out / "分段超額.csv", index=False, encoding="utf-8-sig")

        # ---- 7. 第二層宏觀序列:只作對照,不作驅動器參數格 ----
        reference = _reference_table(macro_panel, panel, store)
        reference.to_csv(out / "第二層對照.csv", index=False, encoding="utf-8-sig")

        summary["scoreboard"] = json.loads(table.to_json(orient="records"))
        summary["segments"] = json.loads(segments.to_json(orient="records"))
        summary["second_tier_reference"] = json.loads(reference.to_json(orient="records"))
        summary["baselines"] = baselines
        summary["run_ids"] = list(dict.fromkeys(all_run_ids))
        (out / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        with pd.option_context("display.width", 220, "display.max_columns", 40):
            print(f"\n=== 成績表(目標指標 {args.objective}) ===", flush=True)
            print(
                table[
                    ["名稱", "類別", "參數", args.objective, "max_drawdown", "turnover", "裁決", "鄰域平均"]
                ].to_string(index=False),
                flush=True,
            )
            print("\n=== 分段年化超額(對 SPY) ===", flush=True)
            print(
                segments.pivot(index="名稱", columns="段", values="年化超額").to_string(),
                flush=True,
            )
            print("\n=== 第二層宏觀序列(只作對照) ===", flush=True)
            print(reference.to_string(index=False), flush=True)

        print(f"\n落檔:{out}", flush=True)
    return 0


def _reference_table(macro_panel: pd.DataFrame, panel: PricePanel, store) -> pd.DataFrame:
    """第二層宏觀序列的對照表:**只擺數,不做驅動器**(用戶 2026-08-28 裁定)。

    每條序列報三件:期間變化、與「動能減低波」那條因子價差月度變化的相關系數、
    以及齊全度。相關系數只是一個描述性的數,**不是訊號、不是裁決**——它答的是
    「這條序列與因子輪動的方向有沒有關係」,答完就算,不入任何一格參數。
    """
    momentum = next(s for s in FACTOR_ETF_SLEEVES if s.weight_key == "weight_momentum")
    low_vol = next(s for s in FACTOR_ETF_SLEEVES if s.weight_key == "weight_low_vol")
    momentum_id = int(store.resolve_ticker(momentum.ticker, str(panel.dates[0].date())))
    low_vol_id = int(store.resolve_ticker(low_vol.ticker, str(panel.dates[0].date())))
    spread = (panel.close[momentum_id] / panel.close[low_vol_id]).resample("ME").last()
    spread_change = spread.pct_change().dropna()

    rows: list[dict[str, object]] = []
    for code in REFERENCE_TIER_CODES:
        if code not in macro_panel.columns:
            continue
        series = macro_panel[code].dropna()
        monthly = series.resample("ME").last().pct_change().dropna()
        joined = pd.concat([monthly, spread_change], axis=1, join="inner").dropna()
        rows.append(
            {
                "序列": code,
                "分層": "第二層(只作對照)",
                "首日": str(series.index[0].date()),
                "尾日": str(series.index[-1].date()),
                "有讀數日數": int(series.notna().sum()),
                "期內變化": float(series.iloc[-1] / series.iloc[0] - 1.0)
                if float(series.iloc[0]) != 0.0
                else None,
                "與動能減低波月變化的相關": float(joined.iloc[:, 0].corr(joined.iloc[:, 1]))
                if len(joined) > 2
                else None,
                "備註": "不作驅動器參數格",
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    raise SystemExit(main())
