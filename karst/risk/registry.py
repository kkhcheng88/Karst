"""共用風控層與單一定義庫之間那一格:交出登記單、讀回引用與取值。

**庫內沒有第二份定義。** 規則本體(叫什麼、管什麼、參數叫什麼名)的正本住在
``layer.py``;庫裡那三列只是登記處,策略引用只存編號。取值不在規則那一邊——
取值屬用戶領域,住在該策略自己的參數集(D-008)。

**本檔一列都不寫**(KARST-038)。三條規則入庫、記某策略引用哪幾條,一律經唯一
入口 ``karst.gateway.Gateway``(D-020 第 4 條):風控層只交出一份「登記單」,
入口照單入庫並蓋寫入者簽章,``karst verify`` 才核對得到。方向亦只有一條——
入口 import 風控層,風控層永不反過來 import 入口。

D-027 第 4 條:本檔一條 sqlite 連線都不開,全部經 ``karst/store.py`` 的 API。
"""

from __future__ import annotations

from ..store import DefinitionStore
from .layer import RISK_RULES, RiskSettings, get_risk_rule


def risk_rule_definitions() -> tuple[dict[str, str], ...]:
    """三條共用風控規則的登記單(叫什麼、管什麼、取值住在哪個參數名)。

    交給唯一入口照單入庫;本函式不寫庫,亦不在此另寫一份定義(D-002 第 4 條)。
    """
    return tuple(
        {
            "key": rule.key,
            "name": rule.name,
            "param_key": rule.param_key,
            "description": f"{rule.english}:{rule.what}",
        }
        for rule in RISK_RULES.values()
    )


def risk_settings_of(
    store: DefinitionStore,
    strategy_name: str,
    param_set_name: str,
    *,
    strategy_version_no: int | None = None,
    set_version_no: int | None = None,
) -> RiskSettings:
    """由某策略的某個參數集讀回它的風控取值。

    參數集內其他參數一概不理。同一份定義、各自的取值:改一套策略的參數集,
    另一套一個字都不會變。
    """
    param_set = store.get_param_set(
        strategy_name,
        param_set_name,
        strategy_version_no=strategy_version_no,
        set_version_no=set_version_no,
    )
    return RiskSettings.from_param_values(param_set.values)


def referenced_rule_keys(
    store: DefinitionStore, strategy_name: str, *, strategy_version_no: int | None = None
) -> tuple[str, ...]:
    """這套策略引用了哪幾條風控規則(程式名),一條都沒有就回空。"""
    return tuple(
        get_risk_rule(record.key).key
        for record in store.strategy_risk_rules(
            strategy_name, strategy_version_no=strategy_version_no
        )
    )
