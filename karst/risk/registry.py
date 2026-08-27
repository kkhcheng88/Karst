"""共用風控層與單一定義庫之間那一格:把三條規則登記入庫、記策略引用了哪幾條。

**庫內沒有第二份定義。** 規則本體(叫什麼、管什麼、參數叫什麼名)的正本住在
``layer.py``;庫裡那三列只是登記處,策略引用只存編號。取值不在規則那一邊——
取值屬用戶領域,住在該策略自己的參數集(D-008)。

D-027 第 4 條:本檔一條 sqlite 連線都不開,全部經 ``karst/store.py`` 的 API。
"""

from __future__ import annotations

from ..store import DefinitionStore, RiskRuleRecord
from .layer import RISK_RULES, RiskSettings, get_risk_rule


def register_risk_layer(store: DefinitionStore) -> tuple[RiskRuleRecord, ...]:
    """把三條共用風控規則登記入庫,回傳它們的登記列。

    重覆呼叫回同一批列(單一定義),不會多出第二份影像。
    """
    return tuple(
        store.register_risk_rules(
            [
                {
                    "key": rule.key,
                    "name": rule.name,
                    "param_key": rule.param_key,
                    "description": f"{rule.english}:{rule.what}",
                }
                for rule in RISK_RULES.values()
            ]
        )
    )


def reference_risk_rules(
    store: DefinitionStore,
    strategy_name: str,
    risk: RiskSettings,
    *,
    strategy_version_no: int | None = None,
) -> tuple[RiskRuleRecord, ...]:
    """記下某策略版本引用了風控層的哪幾條規則。

    引用哪幾條由取值講明:有給值的就是引用,寫 ``None`` 的就是不引用——
    一條都不引用即一列都不寫,那套策略照樣跑得(D-013 第 4 條)。
    """
    if not isinstance(risk, RiskSettings):
        raise TypeError(f"風控設定要是 RiskSettings,收到 {type(risk).__name__}")
    return tuple(
        store.attach_risk_rules(
            strategy_name,
            risk.referenced_keys,
            strategy_version_no=strategy_version_no,
        )
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
