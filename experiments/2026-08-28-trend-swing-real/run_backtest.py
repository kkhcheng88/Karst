"""KARST-028:趨勢波段策略在真實美股日線上的第一次完整回測。

跑法(倉根目錄)::

    set PYTHONUTF8=1
    python experiments/2026-08-28-trend-swing-real/run_backtest.py

做六件事:

1. 由數據快照砌 K 線面板(宇宙 = 快照裡的十隻大型股;SPY 與 QQQ 只做基準,不落注)。
2. 經唯一入口登記入場突破因子、策略與參數集(策略九格 + 風控三格全部寫入參數集)。
3. 五件規則加共用風控層全開,跑一次完整回測。
4. 逐日淨值、逐日持倉、逐筆交易經 ``karst.runs`` 落痕,拿一個運行編號。
5. 讀回運行算八項指標與 QQQ／SPY 超額(重看不重跑)。
6. 把入場規則在全部實體 × 全期觸發的每一個案例攤成一張案例表,連驗證結果一併落檔;
   另跑一輪小掃描,證明每一格參數都掃得動。

**本檔的取值全部是示例,不是現役設定。** 現役設定要由用戶自己指定(規格 7.5);
本檔一句 ``set_active_setup`` 都沒有,正是不想一組示例參數混充門面數字。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:      # 未裝套件也跑得動(倉根就在上兩層)
    sys.path.insert(0, str(REPO))

from karst.data import read_universe
from karst.gateway import Gateway
from karst.metrics import run_metrics
from karst.risk import RiskSettings, sweep_grid
from karst.runs import RunStore
from karst.strategies.trend_swing import (
    BREAKOUT_FACTOR_NAME,
    TrendSwingParams,
    build_bar_panel,
    case_stats,
    cases_frame,
    entry_cases,
    param_values,
    params_grid,
    read_setup,
    record_trend_swing_run,
    register_trend_swing,
    run_trend_swing,
    sweep_trend_swing,
)

HERE = Path(__file__).resolve().parent

STORE_PATH = REPO / "karst.sqlite"
SNAPSHOT_ROOT = REPO / "data" / "snapshots"
RUNS_ROOT = REPO / "data" / "runs"

# 這次用的數據快照(KARST-027 已凍結:SPY、QQQ 加十隻大型股,2015-01-02~2026-08-26)
SNAPSHOT_ID = "2026-08-27-61e284eaa998"

STRATEGY_NAME = "趨勢波段"
PARAM_SET_NAME = "示例-KARST-028"
ENGINE_VERSION = "0.1.0"

# 基準之外的兩隻 ETF 不落注:趨勢波段的宇宙是股票,SPY／QQQ 只做對照尺。
BENCHMARK_TICKERS = ("SPY", "QQQ")

# ----------------------------------------------------------------------
# 示例取值。**示例參數,不是現役設定。**
# 九格策略參數與三格風控參數全部寫在這裡再交去參數集——碼裡不留任何一個取值,
# 換一組只需改這幾行或者另登記一個參數集(D-008 第 3 條)。
# N 與賠率門檻兩格取在 KARST-013 掃出來那片穩健平原之內(規格 6.5:N 50–120 ×
# 門檻 1.0–1.5),不取那次的單點最優(孤峰視為擬合噪音)。
# ----------------------------------------------------------------------
SAMPLE_PARAMS = TrendSwingParams(
    breakout_lookback_days=50,
    swing_lookback_days=10,
    min_stop_fraction=0.01,
    max_stop_fraction=0.25,
    max_position_fraction=0.25,
    equity_basis="current_equity",
    initial_cash=1_000_000.0,
    fees=0.0,
    tie_break_seed=20260828,
)
SAMPLE_RISK = RiskSettings(
    per_trade_risk=0.02,
    monthly_loss_cap=0.06,
    reward_risk_floor=1.5,
)
SAMPLE_CADENCE = "daily"          # 規則路徑逐根 K 線檢查訊號

# Sortino 的分子是「年化回報減無風險利率」,這個數無預設值,要明寫(KARST-030)。
SAMPLE_RISK_FREE_RATE = 0.04

# 小掃描:證明每一格都掃得動。取值同樣是示例。
SWEEP_BREAKOUT = (20, 50, 90)
SWEEP_SWING = (10, 20)
SWEEP_PER_TRADE_RISK = (0.01, 0.02)
SWEEP_MONTHLY_LOSS_CAP = (0.06, None)
SWEEP_REWARD_RISK_FLOOR = (1.5, 2.0)


def main() -> None:
    os.environ.setdefault("KARST_WRITER", "KARST-028-trendswing")
    HERE.mkdir(parents=True, exist_ok=True)

    with Gateway.open(str(STORE_PATH)) as gateway:
        store = gateway.store

        # 1. 宇宙與 K 線面板 ------------------------------------------------
        universe = read_universe(store, SNAPSHOT_ID, root=SNAPSHOT_ROOT)
        traded = sorted(
            int(entity_id)
            for ticker, entity_id in zip(universe["ticker"], universe["entity_id"])
            if ticker not in BENCHMARK_TICKERS
        )
        ticker_of = {
            int(entity_id): str(ticker)
            for ticker, entity_id in zip(universe["ticker"], universe["entity_id"])
        }
        panel = build_bar_panel(store, SNAPSHOT_ID, entity_ids=traded, root=SNAPSHOT_ROOT)
        period_start = str(panel.dates[0].date())
        period_end = str(panel.dates[-1].date())
        print(
            f"[1] 面板 {len(panel.dates)} 根 K 線 × {len(panel.entity_ids)} 隻股票,"
            f"{period_start} ~ {period_end}"
        )

        # 2. 登記(唯一入口)------------------------------------------------
        version, param_set = register_trend_swing(
            gateway,
            strategy_name=STRATEGY_NAME,
            snapshot_id=SNAPSHOT_ID,
            param_set_name=PARAM_SET_NAME,
            rebalance_cadence=SAMPLE_CADENCE,
            values=param_values(SAMPLE_PARAMS, SAMPLE_RISK),
            description="趨勢波段(D-016、規格 5.4):突破 N 日新高入場、波段低位止蝕、"
                        "量度移動目標、賠率門檻,加共用風控層。示例參數,不是現役設定。",
        )
        print(
            f"[2] 策略「{version.name}」第 {version.version_no} 版,"
            f"參數集「{param_set.name}」第 {param_set.version_no} 版,"
            f"引用因子 {[f.name for f in version.factors]}"
        )

        # 參數一律由參數集讀回來再跑,不用碼裡那一份——證明取值真的住在參數集
        params, risk = read_setup(param_set)
        assert params == SAMPLE_PARAMS and risk == SAMPLE_RISK

        # 3. 跑回測 ----------------------------------------------------------
        result = run_trend_swing(panel=panel, params=params, risk=risk)
        print(
            f"[3] 引擎 {result.engine_name}:入場訊號 {result.entry_signals} 張、"
            f"成交 {len(result.orders)} 筆、熔斷封鎖 {result.blocked_days} 日;"
            f"累計回報 {result.total_return:.4f}、最大回撤 {result.max_drawdown:.4f}、"
            f"單月最深 {result.worst_month_drawdown:.4f}"
        )

        # 4. 落痕 ------------------------------------------------------------
        runs = RunStore(store, root=RUNS_ROOT)
        record = record_trend_swing_run(
            runs,
            result,
            strategy_name=version.name,
            param_set_name=param_set.name,
            snapshot_id=SNAPSHOT_ID,
            engine_version=ENGINE_VERSION,
            period_start=period_start,
            period_end=period_end,
            strategy_version_no=version.version_no,
            param_set_version_no=param_set.version_no,
        )
        print(
            f"[4] 運行編號 {record.run_id}:策略版本 {record.strategy_version_no} × "
            f"參數集 {record.param_set_name} 第 {record.param_set_version_no} 版 × "
            f"{record.period_start}~{record.period_end} × 快照 {record.snapshot_id} × "
            f"引擎 {record.engine_name} {record.engine_version};"
            f"序列核對 {runs.verify_run(record.run_id) or '全對'}"
        )

        # 5. 八項指標(讀回已保存的序列,不重跑引擎)--------------------------
        metrics = run_metrics(
            runs,
            record.run_id,
            risk_free_rate=SAMPLE_RISK_FREE_RATE,
            snapshot_root=SNAPSHOT_ROOT,
        )
        print(
            f"[5] 累計回報 {metrics.total_return:.4f}、年化 {metrics.annual_return:.4f}、"
            f"最大回撤 {metrics.max_drawdown:.4f}、勝率 {metrics.win_rate}、"
            f"盈虧比 {metrics.profit_loss_ratio}、Sortino {metrics.sortino}、"
            f"平均持倉日數 {metrics.average_holding_days}、換手 {metrics.turnover:.4f};"
            f"年化超額 {metrics.annual_excess}"
        )

        # 6. 案例表 ----------------------------------------------------------
        cases = entry_cases(panel, params.rule_params(risk))
        stats = case_stats(cases)
        frame = cases_frame(cases)
        frame.insert(1, "ticker", [ticker_of[int(e)] for e in frame["entity_id"]])
        frame.to_parquet(HERE / "cases.parquet", engine="pyarrow", index=False)
        frame.to_csv(HERE / "cases.csv", index=False, encoding="utf-8-sig")
        print(
            f"[6] 案例 {stats.cases} 個(止蝕 {stats.by_reason['stop']}、"
            f"目標 {stats.by_reason['target']}、期末未平 {stats.by_reason['unclosed']});"
            f"勝率 {stats.win_rate:.4f}、平均已實現賠率 {stats.average_r_multiple:.4f}、"
            f"平均計劃賠率 {stats.average_reward_risk:.4f}、"
            f"平均持倉 {stats.average_holding_days:.2f} 日"
        )

        # 7. 小掃描 ----------------------------------------------------------
        grid = params_grid(
            breakout_lookback_days=SWEEP_BREAKOUT,
            swing_lookback_days=SWEEP_SWING,
            min_stop_fraction=(params.min_stop_fraction,),
            max_stop_fraction=(params.max_stop_fraction,),
            max_position_fraction=(params.max_position_fraction,),
            equity_basis=(params.equity_basis,),
            initial_cash=(params.initial_cash,),
            fees=(params.fees,),
            tie_break_seed=(params.tie_break_seed,),
        )
        swept = sweep_trend_swing(
            panel=panel,
            grid=grid,
            risk_grid=sweep_grid(
                per_trade_risk=SWEEP_PER_TRADE_RISK,
                monthly_loss_cap=SWEEP_MONTHLY_LOSS_CAP,
                reward_risk_floor=SWEEP_REWARD_RISK_FLOOR,
            ),
        )
        sweep_frame = swept.frame()
        sweep_frame.to_csv(HERE / "sweep.csv", index=False, encoding="utf-8-sig")
        print(f"[7] 掃描 {len(swept)} 格已落 sweep.csv")

        # 8. 摘要落檔 --------------------------------------------------------
        summary = {
            "ticket": "KARST-028",
            "snapshot_id": SNAPSHOT_ID,
            "period": [period_start, period_end],
            "trading_days": int(len(panel.dates)),
            "universe": [ticker_of[int(e)] for e in panel.entity_ids],
            "strategy": {"name": version.name, "version_no": version.version_no,
                         "type": version.strategy_type,
                         "factors": [f"{f.name}@{f.version_no}" for f in version.factors]},
            "param_set": {"name": param_set.name, "version_no": param_set.version_no,
                          "rebalance_cadence": param_set.rebalance_cadence,
                          "values": dict(param_set.values),
                          "note": "示例參數,不是現役設定"},
            "run": {"run_id": record.run_id, "engine_name": record.engine_name,
                    "engine_version": record.engine_version,
                    "trading_days": record.trading_days,
                    "artifacts": {k: {"path": a.path, "rows": a.rows}
                                  for k, a in record.artifacts.items()}},
            "metrics": {
                "risk_free_rate": SAMPLE_RISK_FREE_RATE,
                "total_return": metrics.total_return,
                "annual_return": metrics.annual_return,
                "max_drawdown": metrics.max_drawdown,
                "win_rate": metrics.win_rate,
                "profit_loss_ratio": metrics.profit_loss_ratio,
                "annual_excess": metrics.annual_excess,
                "sortino": metrics.sortino,
                "average_holding_days": metrics.average_holding_days,
                "turnover": metrics.turnover,
                "closed_trades": metrics.closed_trades,
                "benchmarks": {
                    ticker: {"total_return": c.total_return,
                             "annual_return": c.annual_return,
                             "max_drawdown": c.max_drawdown,
                             "excess_total_return": c.excess_total_return,
                             "annual_excess": c.annual_excess}
                    for ticker, c in metrics.benchmarks.items()
                },
            },
            "engine_run": {
                "entry_signals": result.entry_signals,
                "orders": len(result.orders),
                "blocked_days": result.blocked_days,
                "worst_month_drawdown": result.worst_month_drawdown,
            },
            "cases": stats.as_row(),
            "sweep": {"cells": len(swept), "columns": list(sweep_frame.columns)},
            "breakout_factor": BREAKOUT_FACTOR_NAME,
        }
        (HERE / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("[8] 摘要已落 summary.json")


if __name__ == "__main__":
    main()
