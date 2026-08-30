"""兩個假引擎,對應引擎適配層的兩條路徑。

``RecordingEngine``
    目標比重路徑(``PortfolioEngine.simulate``)。收下目標比重表原樣記低,回一條
    算得出、但與行情無關的淨值線。用它來看**策略層交了什麼給引擎**:換一個驅動器、
    換一套權重之後,交出去那張表除了那幾行數字之外有沒有變過形狀。

``RecordingRuleEngine``
    規則路徑(``RuleEngine.simulate_rules``)。收下訊號原樣記低,回一條平的淨值線
    與兩條查帳序列。

兩個都收 ``name``:**引擎名是運行編號的一部分**,所以測試要指定得到它,才驗得到
「落痕寫的引擎名與真正跑的那件對不上就當場拒收」那條規矩。

淨值線的形狀由 ``drift`` 話事:``0.0`` 即全期平線(只想證明「引擎收到了什麼」時
用它),``0.5`` 即由起始本金線性升到 1.5 倍(想淨值算得出指標時用它)。**沒有一個
是真行情**,不要拿它們的成績當數。
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from karst.engine.contracts import SimulationOutput
from karst.engine.rules import RuleSimulationOutput


class RecordingEngine:
    """目標比重路徑的可換件引擎替身。"""

    def __init__(self, *, name: str = "recorder", drift: float = 0.5) -> None:
        self.name = str(name)
        self.drift = float(drift)
        #: 逐次呼叫收到的目標比重表(已複製,之後改原表不會影響這裡)。
        self.calls: list[pd.DataFrame] = []
        #: 逐次呼叫收到的組合參數。驗「填空格那句填了什麼」時用。
        self.seen_params: list[Any] = []

    @property
    def seen_targets(self) -> pd.DataFrame | None:
        """最後一次收到的目標比重表;一次都未被呼叫就是 ``None``。"""
        return self.calls[-1] if self.calls else None

    def simulate(self, panel: Any, targets: pd.DataFrame, params: Any) -> SimulationOutput:
        self.calls.append(targets.copy())
        self.seen_params.append(params)
        equity = pd.Series(
            params.initial_cash * np.linspace(1.0, 1.0 + self.drift, len(panel.dates)),
            index=panel.dates,
            name="equity",
            dtype=float,
        )
        holdings = pd.DataFrame(0.0, index=panel.dates, columns=list(panel.entity_ids))
        return SimulationOutput(equity_curve=equity, holdings=holdings, orders=())


class RecordingRuleEngine:
    """規則路徑的可換件引擎替身。"""

    def __init__(self, *, name: str = "fake") -> None:
        self.name = str(name)
        #: 逐次呼叫收到的訊號。
        self.calls: list[Any] = []
        self.seen_params: list[Any] = []

    @property
    def seen_signals(self) -> Any | None:
        """最後一次收到的訊號;一次都未被呼叫就是 ``None``。"""
        return self.calls[-1] if self.calls else None

    def simulate_rules(self, panel: Any, signals: Any, params: Any) -> RuleSimulationOutput:
        self.calls.append(signals)
        self.seen_params.append(params)

        def flat(value: float) -> pd.Series:
            return pd.Series(value, index=panel.dates, dtype=float)

        return RuleSimulationOutput(
            equity_curve=flat(params.initial_cash),
            holdings=pd.DataFrame(0.0, index=panel.dates, columns=list(panel.entity_ids)),
            cash=flat(params.initial_cash),
            sizing_basis=flat(params.initial_cash),
            breaker_blocked=pd.Series(False, index=panel.dates, dtype=bool),
            orders=(),
        )
