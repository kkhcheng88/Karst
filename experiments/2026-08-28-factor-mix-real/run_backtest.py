"""KARST-041:因子混合策略(ETF 版)示例運行的**重生腳本**。

KARST-031 交出的示例運行 `run-f4c162e5aac34347` 當初是在暫存區用一個從未入倉的
驅動檔跑出來的。本檔把那一次原封不動寫成一個入了倉的腳本:任何人一句命令重跑,
得回**同一個運行編號、同一份成績**。

跑法(倉根目錄)::

    set PYTHONUTF8=1
    python experiments/2026-08-28-factor-mix-real/run_backtest.py

做五件事:

1. 由數據快照 ``2026-08-27-91a5d51339d9`` 砌價格面板(六隻 ETF;SPY 與 QQQ 只做
   基準,四隻因子 ETF 才是持倉)。
2. 經唯一入口登記四個因子、策略與參數集(D-020 第 4 條)。**同名同值即沿用舊版**,
   所以重跑一次一列都不會多寫——參數集版本號入運行編號,多一版就會把同一次回測
   記成兩次(KARST-041)。
3. 四格因子敞口按參數集寫定的權重混成一個組合,跑一次完整回測。
4. 逐日淨值、逐日持倉、逐筆交易經 ``karst.runs`` 落痕。同一組輸入算出同一個運行
   編號,舊記錄還在就原封不動回舊記錄,不重寫(D-020 第 7 條)。
5. 讀回運行算八項指標與 SPY／QQQ 超額(重看不重跑),核對成績與 KARST-031 記低
   那一次是否一字不差,再把摘要落 ``summary.json``。

**本檔的取值全部是示例,不是現役設定。** 現役設定要由用戶自己指定(規格 7.5);
本檔一句 ``designate_active_setup`` 都沒有,正是不想一組示例參數混充門面數字。

倉裡沒有那個數據快照時(``data/`` 不入 git),先重抓一次——同一段窗口重抓得回
同一個編號(KARST-033),但**快照日期要明寫**,因為編號以它做前綴::

    karst data snapshot --start 2015-01-02 --end 2026-08-26 --taken-on 2026-08-27 \
        --ticker SPY --ticker QQQ --ticker QUAL --ticker VLUE --ticker MTUM --ticker USMV
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:      # 未裝套件也跑得動(倉根就在上兩層)
    sys.path.insert(0, str(REPO))

from karst.data.snapshots import read_price_panel  # noqa: E402
from karst.engine import PricePanel  # noqa: E402
from karst.gateway import Gateway  # noqa: E402
from karst.metrics import run_metrics  # noqa: E402
from karst.runs import RunStore  # noqa: E402
from karst.strategies.factor_mix import (  # noqa: E402
    FACTOR_ETF_SLEEVES,
    FactorMixParams,
    record_factor_mix_run,
    register_factor_mix,
    run_factor_mix,
)

HERE = Path(__file__).resolve().parent

STORE_PATH = REPO / "karst.sqlite"
SNAPSHOT_ROOT = REPO / "data" / "snapshots"
RUNS_ROOT = REPO / "data" / "runs"

# 這次用的數據快照(KARST-031 用的同一個:yfinance、已調整價、六隻 ETF)
SNAPSHOT_ID = "2026-08-27-91a5d51339d9"
SNAPSHOT_WINDOW = ("2015-01-02", "2026-08-26")
SNAPSHOT_TAKEN_ON = "2026-08-27"
SNAPSHOT_UNIVERSE = ("SPY", "QQQ", "QUAL", "VLUE", "MTUM", "USMV")

STRATEGY_NAME = "因子混合(ETF 版)"
PARAM_SET_NAME = "示例-四等分季度"
ENGINE_VERSION = "0.1.0"
STRATEGY_DESCRIPTION = "KARST-031 示例參數,不是現役設定"

# ----------------------------------------------------------------------
# 示例取值。**示例參數,不是現役設定。**
# 四格權重與換倉節奏全部寫在這裡再交去參數集——碼裡不留任何一個取值,換一組只需
# 改這幾行或者另登記一個參數集(D-008 第 3 條)。
# ----------------------------------------------------------------------
SAMPLE_CADENCE = "quarterly"
SAMPLE_WEIGHTS = {sleeve.weight_key: "0.25" for sleeve in FACTOR_ETF_SLEEVES}

# Sortino 的分子是「年化回報減無風險利率」,這個數無預設值,要明寫(KARST-030)。
SAMPLE_RISK_FREE_RATE = 0.04

# ----------------------------------------------------------------------
# KARST-031 記低那一次的成績。重跑對不上即當場拋錯——重生腳本交不出同一份成績,
# 就不是重生,是另一次運行。
# ----------------------------------------------------------------------
EXPECTED_RUN_ID = "run-f4c162e5aac34347"
EXPECTED_TRADING_DAYS = 2929
EXPECTED_REBALANCES = 47
EXPECTED_ORDERS = 188
EXPECTED_METRICS = {
    "total_return": 3.2186,      # 累計 +321.86%
    "annual_return": 0.1319,     # 年化 13.19%
    "max_drawdown": -0.3493,     # 最大回撤 −34.93%
}
METRIC_PLACES = 4                # 對到小數點後四位,即百分比的第二個位


def build_panel(store) -> PricePanel:
    """由快照讀回開價表與收價表,砌成目標比重路徑吃得落的價格面板。

    任何一格留空即整行不要(留空是停牌或未上市,不是零,D-026);做法與
    KARST-029 的掃描腳本一字不差,故此兩邊砌出來的是同一張面板。
    """
    opens = read_price_panel(
        store, SNAPSHOT_ID, field="open", root=SNAPSHOT_ROOT
    ).dropna(how="any")
    closes = read_price_panel(
        store, SNAPSHOT_ID, field="close", root=SNAPSHOT_ROOT
    ).dropna(how="any")
    common = opens.index.intersection(closes.index)
    return PricePanel.from_frames(open=opens.loc[common], close=closes.loc[common])


def rebuild(*, store_path: Path | str = STORE_PATH, check: bool = True) -> dict:
    """重跑示例運行,回傳一份摘要。``check`` 為真即順帶核對編號與成績。

    落檔的事不在這裡做(見 ``main``),所以測試引得動它而不會寫爛倉裡的檔。
    """
    with Gateway.open(str(store_path)) as gateway:
        store = gateway.store

        # 1. 價格面板 --------------------------------------------------------
        panel = build_panel(store)
        period = (str(panel.dates[0].date()), str(panel.dates[-1].date()))

        # 2. 登記(唯一入口;同名同值即沿用舊版,重跑不多寫一列)---------------
        version, param_set = register_factor_mix(
            gateway,
            strategy_name=STRATEGY_NAME,
            sleeves=FACTOR_ETF_SLEEVES,
            snapshot_id=SNAPSHOT_ID,
            param_set_name=PARAM_SET_NAME,
            rebalance_cadence=SAMPLE_CADENCE,
            weights=SAMPLE_WEIGHTS,
            description=STRATEGY_DESCRIPTION,
        )

        # 參數一律由參數集讀回來再跑,不用碼裡那一份——證明取值真的住在參數集
        params = FactorMixParams.from_param_set(param_set, FACTOR_ETF_SLEEVES)

        # 3. 跑回測 ----------------------------------------------------------
        result = run_factor_mix(
            store=store, panel=panel, sleeves=FACTOR_ETF_SLEEVES, params=params
        )

        # 4. 落痕(同一組輸入即同一個編號;舊記錄還在就回舊記錄)---------------
        runs = RunStore(store, root=RUNS_ROOT)
        record = record_factor_mix_run(
            runs,
            result,
            strategy_name=version.name,
            param_set_name=param_set.name,
            snapshot_id=SNAPSHOT_ID,
            engine_version=ENGINE_VERSION,
            period_start=period[0],
            period_end=period[1],
            strategy_version_no=version.version_no,
            param_set_version_no=param_set.version_no,
        )

        # 5. 八項指標(讀回已保存的序列,不重跑引擎)--------------------------
        metrics = run_metrics(
            runs,
            record.run_id,
            risk_free_rate=SAMPLE_RISK_FREE_RATE,
            snapshot_root=SNAPSHOT_ROOT,
        )

        summary = {
            "ticket": "KARST-041",
            "reproduces": {"ticket": "KARST-031", "run_id": EXPECTED_RUN_ID},
            "snapshot_id": SNAPSHOT_ID,
            "period": list(period),
            "trading_days": int(len(panel.dates)),
            "universe": list(SNAPSHOT_UNIVERSE),
            "strategy": {
                "name": version.name,
                "version_no": version.version_no,
                "type": version.strategy_type,
                "factors": [f"{f.name}@{f.version_no}" for f in version.factors],
            },
            "param_set": {
                "name": param_set.name,
                "version_no": param_set.version_no,
                "rebalance_cadence": param_set.rebalance_cadence,
                "values": dict(param_set.values),
                "note": "示例參數,不是現役設定",
            },
            "run": {
                "run_id": record.run_id,
                "engine_name": record.engine_name,
                "engine_version": record.engine_version,
                "trading_days": record.trading_days,
                "rebalances": len(result.rebalances),
                "orders": len(result.orders),
                "first_execution_date": result.rebalances[0].execution_date,
                "series_check": list(runs.verify_run(record.run_id)) or ["全對"],
            },
            "metrics": {
                "risk_free_rate": SAMPLE_RISK_FREE_RATE,
                "total_return": metrics.total_return,
                "annual_return": metrics.annual_return,
                "max_drawdown": metrics.max_drawdown,
                "win_rate": metrics.win_rate,
                "profit_loss_ratio": metrics.profit_loss_ratio,
                "sortino": metrics.sortino,
                "average_holding_days": metrics.average_holding_days,
                "turnover": metrics.turnover,
                "closed_trades": metrics.closed_trades,
                "annual_excess": dict(metrics.annual_excess),
                "benchmarks": {
                    ticker: {
                        "total_return": cell.total_return,
                        "annual_return": cell.annual_return,
                        "max_drawdown": cell.max_drawdown,
                        "excess_total_return": cell.excess_total_return,
                        "annual_excess": cell.annual_excess,
                    }
                    for ticker, cell in metrics.benchmarks.items()
                },
            },
            "exposures": result.exposures_frame().to_dict("records"),
        }

    if check:
        check_reproduction(summary)
    return summary


def check_reproduction(summary: dict) -> None:
    """核對重跑出來的編號與成績,對不上即拋 ``AssertionError``。

    對到小數點後四位——即百分比的第二個位,正是 KARST-031 與 KARST-038 兩張票
    記低成績時用的精度。
    """
    run = summary["run"]
    problems: list[str] = []
    if run["run_id"] != EXPECTED_RUN_ID:
        problems.append(f"運行編號 {run['run_id']},應是 {EXPECTED_RUN_ID}")
    for key, expected in (
        ("trading_days", EXPECTED_TRADING_DAYS),
        ("rebalances", EXPECTED_REBALANCES),
        ("orders", EXPECTED_ORDERS),
    ):
        if run[key] != expected:
            problems.append(f"{key} {run[key]},應是 {expected}")
    for key, expected in EXPECTED_METRICS.items():
        actual = round(float(summary["metrics"][key]), METRIC_PLACES)
        if actual != expected:
            problems.append(f"{key} {actual},應是 {expected}")
    if problems:
        raise AssertionError(
            "重生腳本交不出 KARST-031 那一次的成績:" + ";".join(problems)
        )


def main() -> None:
    os.environ.setdefault("KARST_WRITER", "KARST-041-fmreg")
    HERE.mkdir(parents=True, exist_ok=True)

    summary = rebuild()

    strategy, param_set = summary["strategy"], summary["param_set"]
    run, metrics = summary["run"], summary["metrics"]
    print(
        f"[1] 面板 {summary['trading_days']} 根 K 線 × {len(summary['universe'])} 隻 ETF,"
        f"{summary['period'][0]} ~ {summary['period'][1]};快照 {summary['snapshot_id']}"
    )
    print(
        f"[2] 策略「{strategy['name']}」第 {strategy['version_no']} 版,"
        f"參數集「{param_set['name']}」第 {param_set['version_no']} 版"
        f"({param_set['rebalance_cadence']},四格各 {param_set['values']['weight_quality']})"
    )
    print(
        f"[3] 引擎 {run['engine_name']} {run['engine_version']}:換倉 {run['rebalances']} 次"
        f"(首次執行日 {run['first_execution_date']})、成交 {run['orders']} 筆"
    )
    print(f"[4] 運行編號 {run['run_id']};序列核對 {'、'.join(run['series_check'])}")
    print(
        f"[5] 累計回報 {metrics['total_return']:.4f}、年化 {metrics['annual_return']:.4f}、"
        f"最大回撤 {metrics['max_drawdown']:.4f}、換手 {metrics['turnover']:.4f};"
        f"年化超額 {metrics['annual_excess']}"
    )
    print(f"[6] 與 KARST-031 記低那一次核對:編號與成績一字不差")

    (HERE / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("[7] 摘要已落 summary.json")


if __name__ == "__main__":
    main()
