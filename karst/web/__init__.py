"""KARST-032 本機網頁殼:瀏覽器開一個本機網址,睇真實回測運行的圖與指標。

起服務:``python -m karst.web``(唯一入口 ``karst`` 的子命令登記是寫死的
if-chain,加不到外掛子命令,所以本頁殼自成一道門;見票上留言)。

這一層只讀不寫,全部數字都由 ``karst.runs`` / ``karst.metrics`` /
``karst.data.snapshots`` 供給,頁內沒有任何寫死的假數據(規格 8.7)。
"""

from __future__ import annotations

from karst.web.data import DEFAULT_RISK_FREE_RATE, RunReader, build_reader
from karst.web.server import make_server, serve_in_background

__all__ = [
    "DEFAULT_RISK_FREE_RATE",
    "RunReader",
    "build_reader",
    "make_server",
    "serve_in_background",
]
