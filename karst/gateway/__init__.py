"""唯一入口(single gateway):全平台唯一一條寫入通道(D-020 第 4 條)。

    from karst.gateway import Gateway

    with Gateway.open("karst.sqlite") as gateway:
        version, receipt = gateway.register_factor(
            "動量·12-1 月",
            scale_kind="cardinal",
            procedure=FormulaProcedure("close[-21]/close[-252]-1", "2026-08-27-ab12cd34ef56"),
        )
        gateway.verify()   # 空 list = 全庫清白

命令列同一道門:``python -m karst.gateway ...``(裝好套件後亦可直接叫 ``karst``)。
"""

from .cli import build_parser, main
from .ledger import Finding, verify
from .service import Gateway, WriteReceipt, build_procedure

__all__ = [
    "Finding",
    "Gateway",
    "WriteReceipt",
    "build_parser",
    "build_procedure",
    "main",
    "verify",
]
