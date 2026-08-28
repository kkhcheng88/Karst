"""因子計算層:由 K 線面板算出因子值,**只算不入庫**。

本套件一列都不寫庫。算出來的長表要落庫,一律另經唯一入口
``karst.gateway``(D-020 第 4 條)——本層不認識 sqlite,亦不認識因子版本。

現有成員:

    alpha158    qlib Alpha158 的 158 條公式,純 pandas/numpy 實作(KARST-063)
"""

from .alpha158 import (
    ALPHA158_APPROXIMATED,
    ALPHA158_EXPRESSIONS,
    ALPHA158_GROUPS,
    ALPHA158_NAMES,
    ALPHA158_WINDOWS,
    LONG_COLUMNS,
    VWAP_APPROXIMATION,
    compute_alpha158,
    compute_alpha158_for_entity,
)

__all__ = [
    "ALPHA158_APPROXIMATED",
    "ALPHA158_EXPRESSIONS",
    "ALPHA158_GROUPS",
    "ALPHA158_NAMES",
    "ALPHA158_WINDOWS",
    "LONG_COLUMNS",
    "VWAP_APPROXIMATION",
    "compute_alpha158",
    "compute_alpha158_for_entity",
]
