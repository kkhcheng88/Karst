"""指標與基準兩層計算(KARST-030;D-020 第 8 條、規格 7.5、8.3、8.5)。

**兩層**是指:

1. **基準層** —— QQQ 與 SPY 的買入持有,由數據快照的日線直接算,一條策略路徑
   都不行(詞彙表:基準是純對照尺,不是策略)。
2. **指標層** —— 一次運行的八項數字,只讀已保存的逐日淨值與逐筆交易,
   **不觸發引擎重跑**(規格 8.5)。

八項按指標兩層制(D-020 第 8 條、規格 8.3):

| 層 | 四項 | 程式名 |
|---|---|---|
| 策略卡 | 累計回報對基準 | ``total_return`` + ``benchmarks`` |
| | 年化回報 | ``annual_return`` |
| | 最大回撤 | ``max_drawdown`` |
| | 勝率盈虧比 | ``win_rate`` / ``profit_loss_ratio`` |
| 運行詳情再加 | 年化超額 | ``annual_excess``(QQQ、SPY 各一個) |
| | Sortino | ``sortino`` |
| | 平均持倉日數 | ``average_holding_days`` |
| | 換手 | ``turnover`` |

年化一律 252 個交易日,與 ``karst.runs.window`` 同一個常數。

用法::

    from karst.metrics import facade_metrics, run_metrics

    # 門面:只取現役設定那次運行(規格 7.5)。指定經唯一入口,才有寫入者簽章
    # (D-020 第 4 條);命令列同一道門:karst params activate --strategy 趨勢波段 --name 現役
    gateway.designate_active_setup("趨勢波段", param_set_name="現役")
    facade = facade_metrics(runs, "趨勢波段", risk_free_rate=0.04)
    facade.annual_excess["QQQ"], facade.annual_excess["SPY"]

    # 指定某一次運行,並只看 2023 年以來那一段(重看不重跑)
    run_metrics(runs, run_id, risk_free_rate=0.04, start="2023-01-01")
"""

from .benchmark import (
    DEFAULT_BENCHMARK_TICKERS,
    BenchmarkCurve,
    benchmark_close,
    benchmark_curve,
    benchmark_entity_id,
)
from .inventory import OpeningLot, opening_inventory, valuation_day
from .ratios import (
    annual_volatility,
    daily_returns,
    downside_deviation,
    sortino_ratio,
    turnover,
    years_of,
)
from .report import (
    BenchmarkComparison,
    RunMetrics,
    active_run,
    facade_metrics,
    run_metrics,
)
from .trades import RoundTrip, TradeStats, round_trips, trade_stats

__all__ = [
    "DEFAULT_BENCHMARK_TICKERS",
    "BenchmarkComparison",
    "BenchmarkCurve",
    "OpeningLot",
    "RoundTrip",
    "RunMetrics",
    "TradeStats",
    "active_run",
    "annual_volatility",
    "benchmark_close",
    "benchmark_curve",
    "benchmark_entity_id",
    "daily_returns",
    "downside_deviation",
    "facade_metrics",
    "opening_inventory",
    "round_trips",
    "run_metrics",
    "sortino_ratio",
    "trade_stats",
    "turnover",
    "valuation_day",
    "years_of",
]
