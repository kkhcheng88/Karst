"""參數掃描與穩健平原報告(KARST-029;D-016 第 3 條、D-008、規格 6.5、7.4)。

一次掃描就是同一套策略、同一段期間、同一個數據快照,只換參數跑很多次。本套件
把 KARST-013 那次一次性的示範(144 組、3×3 鄰域判孤峰)做成可重複用的四層:

``grid``
    **掃描格**:要走哪些格,以及哪兩格算**相鄰**。三種——笛卡兒積格(二維即
    3×3 鄰域)、權重單純形格(相鄰 = 一步權重由一格移去另一格)、拼合格。
    每條軸自報**軸型**:連續軸(回望期一類,鄰域沿住它走)與選擇軸(節奏、退路
    一類,不入鄰域,把格切成**層**)。

``runner``
    逐格經引擎跑並經 ``karst.runs`` 落痕,**每格一個運行編號、同一格重掃不重跑**。
    交回一張逐格八項指標的表。

``verdict``
    判**平原**、**山脊**、**孤峰**、**無效格**。三個門檻無預設值,報告一定要印
    出來。山脊 = 沿連續軸站得住,換一層即跌穿高地門檻。

``report``
    **熱力圖**(二維)與**投影圖**(高維每一對參數一張),加一份頂頭寫住
    策略版本 × 期間 × 數據快照 × 引擎版本的報告(規格 7.4)。

``factor_mix``
    因子混合策略的接法:一格權重 = 一個參數集 = 一次運行。

**本套件不裁定哪一組參數該用**——那是用戶的領域(D-008)。它只交表與判讀。

用法::

    from karst.sweep import FactorMixJob, judge, run_sweep, weight_grid, write_report

    grid = weight_grid(FACTOR_ETF_SLEEVES, step=0.05, cadences=("monthly", "quarterly"))
    sweep = run_sweep(runs=runs, grid=grid, job=job, risk_free_rate=0.04)
    verdict = judge(
        sweep.scores("annual_excess:SPY"), grid,
        objective="annual_excess:SPY", min_trades=30,
        lonely_peak_margin=0.01, plateau_quantile=0.9,
    )
    write_report(sweep, verdict, "experiments/…", title="…")
"""

from .factor_mix import (
    CADENCE_AXIS,
    FactorMixJob,
    ensure_factor_mix_setup,
    reference_point,
    weight_grid,
    weight_text,
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
    ProjectionCell,
    draw_heatmap,
    draw_layer_projections,
    draw_projection_set,
    projection,
    projection_cells,
    write_report,
)
from .runner import (
    METRIC_COLUMNS,
    CellJob,
    CellPlan,
    SweepCell,
    SweepProvenance,
    SweepRun,
    objective_value,
    run_sweep,
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
    "INVALID",
    "LONELY_PEAK",
    "METRIC_COLUMNS",
    "NO_NEIGHBOUR",
    "ORDINARY",
    "PLATEAU",
    "RIDGE",
    "VERDICTS",
    "CellJob",
    "CellPlan",
    "CellScore",
    "CellVerdict",
    "CompositeGrid",
    "ExplicitGrid",
    "FactorMixJob",
    "LayerKey",
    "ProductGrid",
    "ProjectionCell",
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
    "draw_heatmap",
    "draw_layer_projections",
    "draw_projection_set",
    "ensure_factor_mix_setup",
    "judge",
    "layer_label",
    "layer_slug",
    "objective_value",
    "points_frame",
    "product_grid",
    "projection",
    "projection_cells",
    "reference_point",
    "run_sweep",
    "simplex_grid",
    "weight_grid",
    "weight_text",
    "write_report",
]
