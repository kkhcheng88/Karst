"""Karst 單一定義庫(single definition store)。

一個 sqlite 檔裝住全庫的正本定義:實體與代號歷史、因子定義與版本鏈、因子值、
數據快照登記。大批數據住在 parquet,本庫只記它的快照編號(D-026)。

用法:

    from karst import DefinitionStore, FormulaProcedure

    with DefinitionStore.open("karst.sqlite") as store:
        apple = store.register_entity(kind="company", display_name="Apple Inc.", cik="320193")
        store.register_ticker(apple, "AAPL", "1980-12-12")
        momentum = store.register_factor(
            "動量·12-1 月",
            scale_kind="cardinal",
            procedure=FormulaProcedure("close[-21]/close[-252] - 1", "2026-08-27-ab12cd34ef56"),
        )
        store.write_factor_values("動量·12-1 月", [
            {"entity_id": apple, "event_time": "2026-08-26",
             "knowledge_time": "2026-08-27", "executable_time": "2026-08-28",
             "value": 0.31},
        ])
        store.value_for("動量·12-1 月", apple, as_of="2026-08-27")
"""

from .batches import content_hash, freeze_batch, read_batch
from .errors import (
    ContractViolation,
    DuplicateDefinition,
    ImmutabilityViolation,
    KarstError,
    NotFound,
    TickerNotResolved,
)
from .models import (
    NOT_APPLICABLE,
    SCALE_KINDS,
    Entity,
    FactorVersion,
    FormulaProcedure,
    MaterialProcedure,
    Snapshot,
    TickerPeriod,
)
from .store import DefinitionStore

__all__ = [
    "NOT_APPLICABLE",
    "SCALE_KINDS",
    "ContractViolation",
    "DefinitionStore",
    "DuplicateDefinition",
    "Entity",
    "FactorVersion",
    "FormulaProcedure",
    "ImmutabilityViolation",
    "KarstError",
    "MaterialProcedure",
    "NotFound",
    "Snapshot",
    "TickerNotResolved",
    "TickerPeriod",
    "content_hash",
    "freeze_batch",
    "read_batch",
]
