"""單一定義庫的錯誤型別。

寫不入就是寫不入——合約缺件一律當場拒收,不做默認補值。
"""

from __future__ import annotations


class KarstError(Exception):
    """本庫全部錯誤的根。"""


class ContractViolation(KarstError):
    """因子合約(D-021)缺件或違反:缺刻度型、缺產生程序、前視、非有限數值。"""


class ImmutabilityViolation(KarstError):
    """試圖改動已落庫的定義(D-021 第 9 條:只可出新版)。"""


class DuplicateDefinition(KarstError):
    """同一正本重複登記(D-002 單一定義:無第二影像)。"""


class NotFound(KarstError):
    """查不到該定義。"""


class TickerNotResolved(NotFound):
    """該日期沒有任何實體持有這個代號(代號會被回收,故必須連日期解析)。"""
