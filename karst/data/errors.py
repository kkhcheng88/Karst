"""行情管線的錯誤型別。

抓不到就拋錯,不靜靜跳過——舊倉最貴的兩單事故(代號回收、快取先撞先贏)
都是「靜靜失敗」養出來的。
"""

from __future__ import annotations

from ..errors import KarstError


class DataFetchFailed(KarstError):
    """向外部來源抓數失敗,或抓回來的批次缺了要求的代號。

    網絡斷、來源改版、代號寫錯一律走這條路,絕不以空白批次冒充成功。
    """


class SnapshotBroken(KarstError):
    """快照目錄缺件,或檔案內容與登記的內容雜湊對不上。"""


class TickerRecycled(KarstError):
    """同一個代號在同一段日子指向另一個實體(舊倉 GOLD 事故的防線)。"""
