"""價格歸一化(price normalisation)與等價判定(KARST-033)。

用戶 2026-08-28 裁決(原話「yes normalize it. no duplicated copy」):凍結前先把價格
歸一化到固定精度,令同一段日線重抓後編號相同,不再多出重複快照。

## 事實:飄移有多大、從哪裡來

倉裡本來就躺著一對現成證據——2026-08-27 相隔十分鐘的兩次真實抓取,落成了兩個
不同編號的快照(``61e284eaa998`` 與 ``91a5d51339d9``)。拿它們重疊的 SPY、QQQ
共 23,432 個價格對一對:

    有差的                73.15%
    相對誤差 中位數        1.30e-7
    相對誤差 上限          8.32e-7
    成交量有差的           0%

再量一層就見到成因:那些差以 **float32 的最後幾個 bit** 為單位(中位數 2 個 ULP、
99 分位 6 個、上限 14 個;float32 的 eps 是 1.19e-7,與觀測到的中位數 1.30e-7 對得上)。
即來源的已調整價本身只有 float32 那一級精度(約 7.2 位十進位有效數字),**第 8 位
起全是雜訊**,每次抓回來都不一樣。

## 為什麼單靠歸一化做不到(這條要寫明,它推翻了原本的設想)

飄移是相對誤差,四捨五入的格距也是相對的,兩者的比例決定「剛好跨過格線」的機率。
拿同一對真實快照實測,歸一化之後仍落在不同格的價格佔比:

    7 位有效數字   33.0%
    6 位            3.61%
    5 位            0.31%
    4 位            0.026%
    3 位            0%

一個快照有十幾萬個價格,**只要一個落錯格,內容雜湊就是另一個編號**。要全部落回
同一格得減到 3 位有效數字——3 位即把 285.99 蓋成 286,數據就廢了。所以任何**用得落**
的精度都不可能單靠四捨五入令兩次抓取拿到同一個編號。

## 於是分兩件事做

1. **歸一化**——凍結前把價格四捨五入到 7 位有效數字,即來源真正拿得出的精度;
   多出來那幾位雜訊不再入庫。用有效位數而不是固定小數位,是為了照顧 2015 年的
   已調整舊價(低見 0.45 元),固定小數位會把它們削平。
2. **等價重用**——凍結前再問一句:快取根裡是不是已經有一份「同一個窗口、同一個
   宇宙、同一套規矩」而且價格在容差內一樣的快照?有就沿用它的編號與檔案,不再多
   一份副本。這一條才是「no duplicated copy」真正靠的那件事。

容差怎樣定:歸一化後兩次抓取的價格相對差上限實測 1.17e-6;真實的除權除息或數據
更正至少是 1e-3 那一級(一股 285 元派 0.25 元息 = 8.8e-4)。噪音與真更動之間隔著
三個數量級,容差取 1e-5,離噪音 8.5 倍、離真更動 100 倍。**寧緊莫鬆**:收得太緊,
後果只是多一個快照(即今日的現狀,不會錯);收得太鬆才會把一次真的更正當成噪音吞掉。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .sources import PRICE_FIELDS

# 價格保留的有效數字位數。來源的已調整價實測只有 float32 那級精度(約 7.2 位十進位),
# 取 7 位即「留住來源真正知道的,丟掉它不知道的」。
PRICE_SIGNIFICANT_DIGITS = 7

# 等價容差(相對)。見本檔開頭「容差怎樣定」。
EQUIVALENCE_RTOL = 1e-5

NORMALISATION_POLICY_ID = f"round-sig-{PRICE_SIGNIFICANT_DIGITS}"
EQUIVALENCE_POLICY_ID = f"reuse-equivalent-rtol-{EQUIVALENCE_RTOL:.0e}"


def round_significant(
    values: np.ndarray | pd.Series | list[float],
    digits: int = PRICE_SIGNIFICANT_DIGITS,
) -> np.ndarray:
    """四捨五入到 ``digits`` 位有效數字。

    用十進位格式化(``%.*e``)而不是「乘 10 的冪、取整、再除」:

      · 它就是「有效數字」的定義本身——說明檔寫什麼,程式做的就是什麼,
        兩邊不會各自解讀;
      · **冪等**——歸一化過的值再歸一化一次,結果逐位相同。重入同一條管線
        (例如停牌前值填補把上一根收市價抄過來)不會再飄第二次。

    非有限值(NaN)原樣放行:留空就是留空,不當作 0。
    """
    array = np.asarray(values, dtype="float64")
    out = array.copy()
    finite = np.isfinite(array)
    if not finite.any():
        return out
    fmt = f"%.{int(digits) - 1}e"
    out[finite] = [float(fmt % value) for value in array[finite]]
    return out


def normalise_bars(
    bars: pd.DataFrame, *, digits: int = PRICE_SIGNIFICANT_DIGITS
) -> pd.DataFrame:
    """凍結前的歸一化:價格取 ``digits`` 位有效數字,成交量取整股。

    成交量本來就是整股,來源以浮點回;取整只是把「1234567.0000000001」一類的
    表述差抹平,不改動任何一個真實數字(實測兩次抓取的成交量本來就逐位相同)。

    這一步刻意放在管線最前(抓完就做),不放在寫檔或讀檔:

      · 放在最前,主日曆對齊、停牌前值填補全部行在已歸一化的數上,填出來那一根
        與它抄的那一根逐位相同;
      · **不可以**放在讀檔那一關——已經凍結的舊快照是照舊規矩存的,讀回時再歸一化
        一次,重算出來的內容雜湊就與登記的對不上,舊快照會全部驗不過。
    """
    frame = bars.copy()
    for field in PRICE_FIELDS:
        if field not in frame.columns:
            continue
        column = frame[field].to_numpy(dtype="float64")
        frame[field] = np.round(column) if field == "volume" else round_significant(column, digits)
    return frame


def values_equivalent(
    left: np.ndarray | pd.Series,
    right: np.ndarray | pd.Series,
    *,
    rtol: float = EQUIVALENCE_RTOL,
) -> bool:
    """兩批數值是否在相對容差內相同。

    留空的格要在**同一個位置**留空才算相同——一邊有數一邊沒有,是真的不一樣,
    不是雜訊。
    """
    a = np.asarray(left, dtype="float64")
    b = np.asarray(right, dtype="float64")
    if a.shape != b.shape:
        return False
    a_missing, b_missing = np.isnan(a), np.isnan(b)
    if not np.array_equal(a_missing, b_missing):
        return False
    present = ~a_missing
    if not present.any():
        return True
    x, y = a[present], b[present]
    return bool(np.all(np.abs(x - y) <= rtol * np.maximum(np.abs(x), np.abs(y))))
