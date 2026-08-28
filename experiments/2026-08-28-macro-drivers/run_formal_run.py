"""KARST-070:跑一次帶宏觀快照的**正式運行**(FORMAL_RUN),不是掃描格。

背景:KARST-067 發現庫內「因子輪動(ETF 版)」策略至今只有掃描格(``SWEEP_RUN``),
一次正式運行都沒有——策略頁新加的「序列齊全度」標記因此在正路上見不到,要靠
只帶 ``?run=`` 的網址硬催。本檔補上第一次正式運行。

取值來源:``experiments/2026-08-28-macro-rejudge/`` 按軸型重判之後,曲線斜度變化
方向(``curve_trend``)那一格仍是全部六個宏觀驅動器裡最高的一格,而且鄰域平均
由重判前的 +1.59% 升到 +2.89%——鄰域本身站得住,不是被隔壁層拖出來的假象
(見該目錄 README「三件要記住的事」第二點)。取
``lookback_days=20、tilt=1、cadence=monthly``,來源掃描編號
``experiments/2026-08-28-macro-drivers/mac-curve_trend``(即 KARST-040/048 那 30 格)。

跑法(倉根目錄)::

    set PYTHONUTF8=1
    python experiments/2026-08-28-macro-drivers/run_formal_run.py

做四件事:
1. 由現役價格快照(``PRICE_FACTOR_ETF``)與現役宏觀快照(``MACRO``,
   ``2026-08-28-dc2d9f1a1778``)砌面板。
2. **經唯一入口**(``gateway.register_param_set``)登記一個新參數集,名稱注明
   「示例」與來源掃描編號:``示例正式-KARST-070-來源mac-curve_trend``。
3. 跑一次因子輪動(曲線斜度驅動器),**不經掃描跑法**——直接呼叫
   ``run_factor_rotation`` + ``record_factor_rotation_run``,來歷寫
   ``FORMAL_RUN``(掃描跑法 ``karst.sweep.runner`` 一律記 ``SWEEP_RUN``,不管格數
   是一格還是一百格,見 ``record_factor_rotation_run`` docstring)。
4. 印運行編號、參數集版本,落一份 summary.json。

**本檔不改任何引擎、策略或掃描碼,亦不加任何參數預設值**——取值全部在這裡明寫。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
_EXPERIMENTS = REPO / "experiments"
if str(_EXPERIMENTS) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTS))

from snapshot_ids import MACRO as MACRO_SNAPSHOT_ID  # noqa: E402
from snapshot_ids import PRICE_FACTOR_ETF  # noqa: E402

from karst.data import read_macro_panel  # noqa: E402
from karst.data.snapshots import read_price_panel  # noqa: E402
from karst.engine import PricePanel  # noqa: E402
from karst.gateway.service import Gateway  # noqa: E402
from karst.runs import RunStore  # noqa: E402
from karst.strategies.factor_mix import FACTOR_ETF_SLEEVES  # noqa: E402
from karst.strategies.factor_rotation import (  # noqa: E402
    FactorRotationParams,
    build_driver,
    record_factor_rotation_run,
    run_factor_rotation,
)
from karst.sweep.factor_mix import weight_text  # noqa: E402
from karst.sweep.factor_rotation import param_text  # noqa: E402

HERE = Path(__file__).resolve().parent
STORE_PATH = REPO / "karst.sqlite"
SNAPSHOT_ROOT = REPO / "data" / "snapshots"
MACRO_ROOT = REPO / "data" / "macro_snapshots"
RUNS_ROOT = REPO / "data" / "runs"

SNAPSHOT_ID = PRICE_FACTOR_ETF
MACRO_ID = MACRO_SNAPSHOT_ID
STRATEGY_NAME = "因子輪動(ETF 版)"
ENGINE_VERSION = "0.1.0"
MARKET_TICKER = "SPY"
WARMUP_BARS = 252
WARMUP_WEIGHTS = {sleeve.weight_key: 0.25 for sleeve in FACTOR_ETF_SLEEVES}

# 取值來源:experiments/2026-08-28-macro-rejudge/results/summary.json 的
# drivers.curve_trend.best(全部六個宏觀驅動器裡最高、且鄰域真站得住的一格)。
DRIVER_KEY = "curve_trend"
DRIVER_PARAMS = {"lookback_days": 20, "tilt": 1.0}
CADENCE = "monthly"
SOURCE_SWEEP_ID = "experiments/2026-08-28-macro-drivers/mac-curve_trend"
PARAM_SET_NAME = f"示例正式-KARST-070-來源mac-{DRIVER_KEY}"


def main() -> int:
    os.environ.setdefault("KARST_WRITER", "KARST-070-formal-macro")

    with Gateway.open(str(STORE_PATH)) as gateway:
        store = gateway.store

        opens = read_price_panel(store, SNAPSHOT_ID, field="open", root=SNAPSHOT_ROOT).dropna(
            how="any"
        )
        closes = read_price_panel(store, SNAPSHOT_ID, field="close", root=SNAPSHOT_ROOT).dropna(
            how="any"
        )
        common = opens.index.intersection(closes.index)
        panel = PricePanel.from_frames(open=opens.loc[common], close=closes.loc[common])
        period_start = str(panel.dates[0].date())
        period_end = str(panel.dates[-1].date())
        print(
            f"[1] 面板 {len(panel.dates)} 個交易日,{period_start} ~ {period_end}",
            flush=True,
        )

        macro_panel = read_macro_panel(store, MACRO_ID, root=MACRO_ROOT)
        print(f"    宏觀快照 {MACRO_ID}(現役)", flush=True)

        version = store.get_strategy_version(STRATEGY_NAME)

        # ---- 2. 經唯一入口登記參數集 ----
        values: dict[str, str] = {"driver": DRIVER_KEY}
        values.update({name: param_text(value) for name, value in DRIVER_PARAMS.items()})
        values["warmup_bars"] = param_text(WARMUP_BARS)
        values.update(
            {f"warmup_{key}": weight_text(value) for key, value in WARMUP_WEIGHTS.items()}
        )
        # 零成本(D-030 主報口徑):costs 留空,cost_values 一格都不寫。
        values["macro_snapshot"] = MACRO_ID
        values["macro_series"] = "UST_10Y、UST_3M"

        param_set, receipt = gateway.register_param_set(
            STRATEGY_NAME,
            param_set_name=PARAM_SET_NAME,
            rebalance_cadence=CADENCE,
            values=values,
            strategy_version_no=version.version_no,
        )
        print(
            f"[2] 參數集「{param_set.name}」第 {param_set.version_no} 版"
            f"({'沿用舊版' if receipt.reused else '新登記'});取值 {dict(param_set.values)}",
            flush=True,
        )

        # ---- 3. 正式運行(不經掃描跑法) ----
        driver = build_driver(DRIVER_KEY, **DRIVER_PARAMS)
        params = FactorRotationParams(
            cadence=CADENCE,
            warmup_bars=WARMUP_BARS,
            warmup_weights=WARMUP_WEIGHTS,
            initial_cash=100_000.0,
            fees=0.0,
            costs=None,
        )
        result = run_factor_rotation(
            store=store,
            panel=panel,
            sleeves=FACTOR_ETF_SLEEVES,
            driver=driver,
            params=params,
            market_ticker=MARKET_TICKER,
            macro=macro_panel,
        )
        print(
            f"[3] 引擎 {result.engine_name}:{len(result.orders)} 筆成交、"
            f"{len(result.rebalances)} 次移權",
            flush=True,
        )

        runs = RunStore(store, root=RUNS_ROOT)
        record = record_factor_rotation_run(
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
            f"[4] 運行編號 {record.run_id};來歷 {record.origin};"
            f"策略版本 {record.strategy_version_no} × 參數集「{record.param_set_name}」"
            f"第 {record.param_set_version_no} 版 × {record.period_start}~{record.period_end} × "
            f"快照 {record.snapshot_id} × 引擎 {record.engine_name} {record.engine_version};"
            f"序列核對 {runs.verify_run(record.run_id) or '全對'}",
            flush=True,
        )

        summary = {
            "ticket": "KARST-070",
            "source_best_cell": "experiments/2026-08-28-macro-rejudge/results/summary.json"
            ":drivers.curve_trend.best",
            "source_sweep_id": SOURCE_SWEEP_ID,
            "strategy": {"name": version.name, "version_no": version.version_no},
            "param_set": {
                "name": param_set.name,
                "version_no": param_set.version_no,
                "rebalance_cadence": param_set.rebalance_cadence,
                "values": dict(param_set.values),
            },
            "snapshot_id": SNAPSHOT_ID,
            "macro_snapshot_id": MACRO_ID,
            "period": [period_start, period_end],
            "run": {"run_id": record.run_id, "origin": record.origin},
        }
        (HERE / "formal-run-2026-08-29-summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("[5] 摘要已落 formal-run-2026-08-29-summary.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
