"""八項指標與 QQQ／SPY 超額:一次運行的成績單。

指標兩層制(D-020 第 8 條、規格 8.3):

| 層 | 四項 |
|---|---|
| 策略卡 | 累計回報對基準、年化回報、最大回撤、勝率盈虧比 |
| 運行詳情再加 | 年化超額、Sortino、平均持倉日數、換手 |

八項全部由**已保存的逐日淨值與逐筆交易**算出,一條引擎都不觸發(規格 8.5):
入口只有 ``RunStore`` 讀回的三張表,加上快照裡的基準日線。

**門面數字只取現役設定那次運行**(規格 7.5):``facade_metrics`` 由現役設定
反查是哪一次運行,換一個現役設定,八個數字隨之換。歷史最佳要另列的話,
用 ``run_metrics`` 明明白白指定那次運行的編號——它不會冒充門面。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ..errors import NotFound
from ..runs import RunStore
from ..runs.window import window_stats
from ..store import ActiveSetup, RunRecord
from .benchmark import DEFAULT_BENCHMARK_TICKERS, BenchmarkCurve, benchmark_curve
from .ratios import sortino_ratio, turnover
from .trades import TradeStats, trade_stats


@dataclass(frozen=True, slots=True)
class BenchmarkComparison:
    """策略對住一條基準的比較:基準自己三個數,加兩個超額數。

    ``annual_excess`` = 策略年化 − 基準年化(原型 ``run.html``:「策略減 QQQ」),
    這就是運行詳情四項之中的**年化超額**。
    """

    ticker: str
    entity_id: int
    start: str
    end: str
    trading_days: int
    total_return: float
    annual_return: float
    max_drawdown: float
    excess_total_return: float
    annual_excess: float


@dataclass(frozen=True, slots=True)
class RunMetrics:
    """一次運行(或它的一段檢視視窗)的八項指標。

    ``win_rate`` / ``profit_loss_ratio`` / ``average_holding_days`` / ``sortino``
    算不出時是 ``None``,不是 0——沒有平過倉就沒有勝率,一日都未跌穿目標就沒有
    Sortino;填 0 會被讀成「輸清」或者「零風險」,兩者都不是事實。
    """

    run_id: str
    strategy_name: str
    param_set_name: str
    param_set_version_no: int
    strategy_version_no: int
    snapshot_id: str
    is_active_setup: bool
    is_stale: bool
    start: str
    end: str
    trading_days: int

    # ---- 策略卡四項 ----
    total_return: float
    annual_return: float
    max_drawdown: float
    win_rate: float | None
    profit_loss_ratio: float | None

    # ---- 運行詳情再加四項 ----
    annual_excess: dict[str, float]
    sortino: float | None
    average_holding_days: float | None
    turnover: float

    # ---- 對照與口徑 ----
    benchmarks: dict[str, BenchmarkComparison]
    closed_trades: int
    risk_free_rate: float

    def excess_against(self, ticker: str) -> float:
        """對某一條基準的年化超額。"""
        symbol = str(ticker).strip().upper()
        try:
            return self.annual_excess[symbol]
        except KeyError as exc:
            raise NotFound(
                f"這份成績單沒有對 {symbol} 的超額數;算過的有:"
                f"{'、'.join(sorted(self.annual_excess))}"
            ) from exc


def run_metrics(
    runs: RunStore,
    run_id: str,
    *,
    risk_free_rate: float,
    benchmarks: Sequence[str] = DEFAULT_BENCHMARK_TICKERS,
    start: date | datetime | str | None = None,
    end: date | datetime | str | None = None,
    snapshot_root: str | Path | None = None,
) -> RunMetrics:
    """指定一次運行(可另加檢視視窗),算出八項指標與各基準的超額。

    ``risk_free_rate`` **無預設值**:Sortino 的分子是「年化回報減無風險利率」,
    當它是 0 還是 4% 可以差出一倍的 Sortino,不由本層代決定(參數無預設值)。
    ``benchmarks`` 相反,有預設——基準不是可調參數,是 D-010 第 4 條裁死的
    QQQ 與 SPY 兩隻;預設寫成那兩隻正是要令各處都比同一把尺。

    ``start`` / ``end`` 留空即全期;給了就是檢視視窗——**重看不重跑**,八項全部
    按那一段重算,運行本身一個字不變(規格 8.5)。
    """
    record = runs.get_run(run_id)
    equity = runs.equity_curve(record.run_id)
    stats = window_stats(equity, start, end)
    # ``stats.equity`` 已重設基準為 100;算比率要用原本的金額,故按同一段索引取回
    window_equity = equity.loc[stats.equity.index]

    orders = runs.orders(record.run_id)
    in_window = orders.loc[
        (orders["trade_date"].astype(str) >= stats.start)
        & (orders["trade_date"].astype(str) <= stats.end)
    ]
    trades: TradeStats = trade_stats(in_window, window_equity.index)

    comparisons: dict[str, BenchmarkComparison] = {}
    for ticker in benchmarks:
        curve = benchmark_curve(
            runs.store,
            record.snapshot_id,
            ticker,
            stats.start,
            stats.end,
            root=snapshot_root,
        )
        comparisons[curve.ticker] = _compare(stats.total_return, stats.annual_return, curve)

    return RunMetrics(
        run_id=record.run_id,
        strategy_name=record.strategy_name,
        param_set_name=record.param_set_name,
        param_set_version_no=record.param_set_version_no,
        strategy_version_no=record.strategy_version_no,
        snapshot_id=record.snapshot_id,
        is_active_setup=_is_active_setup(runs, record),
        is_stale=runs.is_stale(record.run_id),
        start=stats.start,
        end=stats.end,
        trading_days=stats.trading_days,
        total_return=stats.total_return,
        annual_return=stats.annual_return,
        max_drawdown=stats.max_drawdown,
        win_rate=trades.win_rate,
        profit_loss_ratio=trades.profit_loss_ratio,
        annual_excess={
            ticker: comparison.annual_excess for ticker, comparison in comparisons.items()
        },
        sortino=sortino_ratio(
            window_equity,
            annual_return=stats.annual_return,
            risk_free_rate=float(risk_free_rate),
        ),
        average_holding_days=trades.average_holding_days,
        turnover=turnover(window_equity, traded_value=trades.traded_value),
        benchmarks=comparisons,
        closed_trades=trades.closed_trades,
        risk_free_rate=float(risk_free_rate),
    )


def active_run(runs: RunStore, strategy_name: str) -> RunRecord:
    """現役設定那次運行。未指定現役設定、或者現役設定未跑過,一律拋錯不猜。

    「未跑過」與「跑過但成績差」是兩回事:寧可講「現役設定未有運行」,也不可以
    順手挑另一次成績好的頂上——那正是規格 7.5 要防的那件事。
    """
    setup: ActiveSetup = runs.store.get_active_setup(strategy_name)
    matched = [
        record
        for record in runs.list_runs(setup.strategy_name)
        if record.param_set_id == setup.param_set_id
        and record.strategy_version_id == setup.strategy_version_id
    ]
    if not matched:
        raise NotFound(
            f"策略「{setup.strategy_name}」的現役設定是參數集「{setup.param_set_name}」"
            f"第 {setup.param_set_version_no} 版,但它一次運行都未有;"
            "門面數字只取現役設定那次運行(規格 7.5)"
        )
    return matched[-1]


def facade_metrics(
    runs: RunStore,
    strategy_name: str,
    *,
    risk_free_rate: float,
    benchmarks: Sequence[str] = DEFAULT_BENCHMARK_TICKERS,
    start: date | datetime | str | None = None,
    end: date | datetime | str | None = None,
    snapshot_root: str | Path | None = None,
) -> RunMetrics:
    """門面八個數字:只取現役設定那次運行(規格 7.5)。

    換一個現役設定,這裡回的就是新設定那次運行的八個數——門面隨現役設定走,
    不隨「哪一次跑得最靚」走。
    """
    record = active_run(runs, strategy_name)
    return run_metrics(
        runs,
        record.run_id,
        risk_free_rate=risk_free_rate,
        benchmarks=benchmarks,
        start=start,
        end=end,
        snapshot_root=snapshot_root,
    )


def _compare(
    total_return: float, annual_return: float, curve: BenchmarkCurve
) -> BenchmarkComparison:
    return BenchmarkComparison(
        ticker=curve.ticker,
        entity_id=curve.entity_id,
        start=curve.stats.start,
        end=curve.stats.end,
        trading_days=curve.stats.trading_days,
        total_return=curve.stats.total_return,
        annual_return=curve.stats.annual_return,
        max_drawdown=curve.stats.max_drawdown,
        excess_total_return=float(total_return - curve.stats.total_return),
        annual_excess=float(annual_return - curve.stats.annual_return),
    )


def _is_active_setup(runs: RunStore, record: RunRecord) -> bool:
    try:
        setup = runs.store.get_active_setup(record.strategy_name)
    except NotFound:
        return False
    return (
        setup.param_set_id == record.param_set_id
        and setup.strategy_version_id == record.strategy_version_id
    )
