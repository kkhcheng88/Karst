"""參數掃描與穩健平原報告(KARST-029;D-016 第 3 條、D-008、規格 6.5、7.4)。

一次掃描就是同一套策略、同一段期間、同一個數據快照,只換參數跑很多次;**一次
掃描 = 一個批次**(D-042)。本套件是那件事的三層,加報告:

``grid``
    **掃描格**:要走哪些格,以及哪兩格算**相鄰**。三種——笛卡兒積格(二維即
    3×3 鄰域)、權重單純形格(相鄰 = 一步權重由一格移去另一格)、拼合格。
    每條軸自報**軸型**:連續軸(回望期一類,鄰域沿住它走)與選擇軸(節奏、退路
    一類,不入鄰域,把格切成**層**)。

``verdict``
    判**平原**、**山脊**、**孤峰**、**無效格**。三個門檻無預設值,報告一定要印
    出來。山脊 = 沿連續軸站得住,換一層即跌穿高地門檻。

``report``
    **熱力圖**(二維)與**投影圖**(高維每一對參數一張),加一份頂頭寫住
    策略版本 × 期間 × 數據快照 × 引擎版本的報告(規格 7.4);另有成績表、分段
    超額與成本對照。

``runner``
    掃描表的形狀:一格(``SweepCell``)、一次掃描(``SweepRun``)、來歷
    (``SweepProvenance``)。

**逐格怎樣跑已經不在本套件**(KARST-091):登記、驗參數、查重、跑引擎、落痕
與失敗運行判定,與一次正式運行做法一模一樣,所以全部住在**策略執行台**。掃描
是執行台的第二個入口::

    from karst.executor import Executor, BatchReport
    from karst.sweep import weight_grid

    grid = weight_grid(FACTOR_ETF_SLEEVES, step=0.05, cadences=("monthly", "quarterly"))
    outcome = executor.sweep(
        contract, setup=setup, grid=grid, panel=panel,
        period=("2015-01-01", "2025-12-31"), engine_version="…",
        risk_free_rate=0.04, sweep_id="experiments/…", param_set_prefix="mix-",
        param_set_suffix="", base_values={}, objective="annual_excess:SPY",
        min_trades=30, lonely_peak_margin=0.01, plateau_quantile=0.9,
        report=BatchReport(directory="experiments/…", title="…"),
    )

**本套件不裁定哪一組參數該用**——那是用戶的領域(D-008)。它只交表與判讀。
"""

from .factor_mix import (
    CADENCE_AXIS,
    cost_inputs,
    cost_slug,
    cost_text,
    reference_point,
    weight_grid,
    weight_text,
)
from .factor_rotation import (
    DRIVER_CHOICE_PARAMETERS,
    DRIVER_KEY,
    param_text,
    point_slug,
    rotation_grid,
)
from .grid import (
    AXIS_KINDS,
    CHOICE,
    CONTINUOUS,
    CompositeGrid,
    ExplicitGrid,
    LayerKey,
    ProductGrid,
    SimplexGrid,
    SweepAxis,
    SweepGrid,
    SweepPoint,
    all_continuous,
    choice_axis,
    compose,
    continuous_axis,
    layer_label,
    layer_slug,
    points_frame,
    product_grid,
    simplex_grid,
)
from .report import (
    CostPair,
    ProjectionCell,
    ScoreEntry,
    cost_comparison,
    draw_heatmap,
    draw_layer_projections,
    draw_projection_set,
    projection,
    projection_cells,
    provenance_note,
    scoreboard,
    segment_excess,
    write_report,
)
from .runner import (
    METRIC_COLUMNS,
    CellPlan,
    SweepCell,
    SweepProvenance,
    SweepRun,
    objective_value,
)
from .verdict import (
    INVALID,
    LONELY_PEAK,
    NO_NEIGHBOUR,
    ORDINARY,
    PLATEAU,
    RIDGE,
    VERDICTS,
    CellScore,
    CellVerdict,
    SweepJudgement,
    judge,
)

__all__ = [
    "AXIS_KINDS",
    "CADENCE_AXIS",
    "CHOICE",
    "CONTINUOUS",
    "DRIVER_CHOICE_PARAMETERS",
    "DRIVER_KEY",
    "INVALID",
    "LONELY_PEAK",
    "METRIC_COLUMNS",
    "NO_NEIGHBOUR",
    "ORDINARY",
    "PLATEAU",
    "RIDGE",
    "VERDICTS",
    "CellPlan",
    "CellScore",
    "CellVerdict",
    "CompositeGrid",
    "CostPair",
    "ExplicitGrid",
    "LayerKey",
    "ProductGrid",
    "ProjectionCell",
    "ScoreEntry",
    "SimplexGrid",
    "SweepAxis",
    "SweepCell",
    "SweepGrid",
    "SweepJudgement",
    "SweepPoint",
    "SweepProvenance",
    "SweepRun",
    "all_continuous",
    "choice_axis",
    "compose",
    "continuous_axis",
    "cost_comparison",
    "cost_inputs",
    "cost_slug",
    "cost_text",
    "draw_heatmap",
    "draw_layer_projections",
    "draw_projection_set",
    "judge",
    "layer_label",
    "layer_slug",
    "objective_value",
    "param_text",
    "point_slug",
    "points_frame",
    "product_grid",
    "projection",
    "projection_cells",
    "provenance_note",
    "reference_point",
    "rotation_grid",
    "scoreboard",
    "segment_excess",
    "simplex_grid",
    "weight_grid",
    "weight_text",
    "write_report",
]
