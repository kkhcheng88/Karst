"""回測運行留痕(規格 7.4、8.5;KARST-026)。

一次回測運行 = **策略版本 × 參數集 × 期間 × 數據快照 × 引擎版本** 的唯一組合。
五件蓋齊算出一個運行編號(內容雜湊):同一組輸入永遠得同一個編號,改任何一件
即另一次運行。運行一經落痕**不可改**;因子或策略日後出新版,舊運行內容一字不變
——只是查得出它已經過時(D-021 第 9 條、規格 7.3)。

每次運行保存三條序列(parquet,按運行編號分目錄):逐日淨值、逐日持倉、逐筆交易。
規則路徑另交得出兩條**查帳序列**(逐日注碼基數、逐日熔斷狀態),一併落在同一個
目錄;查帳序列不入運行編號,舊運行沒有這兩條照樣讀得回。
有了逐日淨值,揀 2023 年以來那一段重看就**不用重跑引擎**——那就是「檢視視窗」
(規格 8.5)。

用法::

    from karst import DefinitionStore
    from karst.runs import FORMAL_RUN, RunStore, synthetic_simulation

    runs = RunStore(store, root="data/runs")
    result = synthetic_simulation(start="2020-01-01", end="2026-06-30",
                                  entity_ids=(1, 2, 3), seed=7)
    record = runs.record_simulation(
        result,
        strategy_name="趨勢波段",
        param_set_name="現役",
        snapshot_id=snapshot_id,
        engine_version="0.1.0",
        origin=FORMAL_RUN,
    )
    runs.window_stats(record.run_id, "2023-01-01", "2026-06-30").total_return

每次落痕都要講明**來歷**(``origin``):正式運行 ``FORMAL_RUN``,參數掃描其中一格
``SWEEP_RUN`` 連掃描編號。無預設值——庫身分得出兩者,靠的就是這一格(KARST-054)。
"""

from ..store import FORMAL_RUN, SWEEP_RUN, RunArtifact, RunRecord
from .registry import (
    AUDIT_SERIES_KINDS,
    BREAKER_BLOCKED,
    SELECTION_CANDIDATES,
    SELECTION_KINDS,
    SELECTION_SCORES,
    SIZING_BASIS,
    RunStore,
)
from .synthetic import SyntheticSimulation, synthetic_simulation
from .window import (
    BASE,
    TRADING_DAYS_PER_YEAR,
    WindowStats,
    max_drawdown,
    rebase,
    window_slice,
    window_stats,
)

__all__ = [
    "AUDIT_SERIES_KINDS",
    "BASE",
    "BREAKER_BLOCKED",
    "FORMAL_RUN",
    "SELECTION_CANDIDATES",
    "SELECTION_KINDS",
    "SELECTION_SCORES",
    "SIZING_BASIS",
    "SWEEP_RUN",
    "TRADING_DAYS_PER_YEAR",
    "RunArtifact",
    "RunRecord",
    "RunStore",
    "SyntheticSimulation",
    "WindowStats",
    "max_drawdown",
    "rebase",
    "synthetic_simulation",
    "window_slice",
    "window_stats",
]
