"""Alpha158:qlib 那 158 條公式的純 pandas/numpy 實作(KARST-063)。

**抄的是公式,不是程式庫。** qlib 以 MIT 授權公開發表這 158 條表達式的文字
定義;本檔照那份文字自己用 pandas/numpy 寫一次,Karst 的運行依賴一列都不多
(``research/2026-08-29-alpha158-feasibility.md`` 第二節的裁決)。

出處(2026-08-29 以 pyqlib 0.9.7 的官方檔案核實):

  · https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/loader.py
    ——``Alpha158DL.get_feature_config()``,158 條的名稱與表達式正本。
  · https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/handler.py
    ——``Alpha158`` handler 以無參數方式呼叫上面那個函式,即預設設定就是 158 條。
  · https://github.com/microsoft/qlib/blob/main/qlib/data/ops.py
    ——每個運算子的確切語意(下面〈運算子語意〉一節逐條列明)。
  · https://github.com/microsoft/qlib/blob/main/qlib/data/_libs/rolling.pyx
    ——``Slope`` / ``Rsquare`` / ``Resi`` 的滾動迴歸算法。

核實方法:在臨時目錄(本倉之外)下載 pyqlib 0.9.7 的官方輪檔,把
``Alpha158DL.get_feature_config`` 由原始碼抽出來原封不動跑一次,取回它吐出的
``(fields, names)``。**沒有在本倉裝過 qlib,亦沒有把它加進依賴。**

逐組條數(官方輸出實測,合計 158)
---------------------------------

===========  ====  ===========================================================
組            條數  內容
===========  ====  ===========================================================
K 線形態組       9  KMID KLEN KMID2 KUP KUP2 KLOW KLOW2 KSFT KSFT2,不分窗口
價格組           4  OPEN0 HIGH0 LOW0 VWAP0(官方預設只取窗口 0,故每欄一條;
                    CLOSE 不在官方預設的 ``feature`` 清單內)
成交量組         0  官方預設的 config **沒有** ``volume`` 這一格,所以原始
                    ``VOLUME{d}`` 一條都不出;成交量只經滾動組的 VMA/VSTD/
                    WVMA/VSUM* 入賬(調研檔第 1.3 節把它當成獨立一組,實測不是)
滾動窗口組     145  29 種運算子 × 5 個窗口(5、10、20、30、60)
===========  ====  ===========================================================

滾動組那 29 種運算子(調研檔第 1.4 節寫「28 種」,實測是 29——它把
VSUMP/VSUMN/VSUMD 併成一行數):ROC MA STD BETA RSQR RESI MAX MIN QTLU QTLD
RANK RSV IMAX IMIN IMXD CORR CORD CNTP CNTN CNTD SUMP SUMN SUMD VMA VSTD WVMA
VSUMP VSUMN VSUMD。

近似處理(唯一一條)
-------------------

``VWAP0 = $vwap/$close`` 是 158 條之中**唯一**要用到日線 OHLCV 以外欄位的
一條。日線來源(yfinance 一類)不提供逐日成交量加權平均價,本檔以**典型價**
代之::

    vwap ≈ (high + low + close) / 3

這是近似值,不是真的成交量加權平均價:當日成交集中在某個價位時兩者會分開。
``ALPHA158_APPROXIMATED`` 列住這一條,下游要剔走或改算法時照那個清單走,
不必逐條翻。其餘 157 條全部是原式,無近似。

運算子語意(逐條對過 qlib/data/ops.py,差一個位就對不上官方數值)
-----------------------------------------------------------------

  · **全部滾動運算子 ``min_periods=1``**。qlib 的 ``Rolling._load_internal``
    寫死 ``series.rolling(N, min_periods=1)``,所以序列開頭那 N-1 格**有值**
    (以不足一個窗口的資料算),不是留空。這一格最容易寫錯。
  · ``Ref(x, d)`` = ``x.shift(d)``。
  · ``Mean`` / ``Sum`` / ``Max`` / ``Min`` / ``Quantile`` = pandas 同名滾動函式;
    ``Std`` 是 pandas 預設的 ``ddof=1``(樣本標準差),不是母體標準差。
  · ``Greater(a, b)`` = ``np.maximum``、``Less(a, b)`` = ``np.minimum``
    (不是布林比較);``a > b`` 才是布林比較 ``np.greater``,而
    ``np.greater(nan, x)`` 是 ``False`` ——所以 CNTP/CNTN 的第一格是 0,不是留空。
  · ``Rank(x, d)`` = ``rolling.rank(pct=True)``,即今日值在窗口內的百分位名次。
  · ``IdxMax(x, d)`` = ``rolling.apply(lambda w: w.argmax() + 1)``——**由窗口
    最舊那格數起、1 起計**,不是「距今幾日」(調研檔第 1.4 節的白話解說在這一
    點上反了)。滿窗時最新一格中選即得 d,故 ``IMAX{d}`` 的上限是 1。並列時
    ``argmax`` 取最早那格。
  · ``Corr(a, b, d)``:兩邊任何一邊的滾動標準差貼近 0(``np.isclose(·, 0,
    atol=2e-05)``)那幾格,qlib 事後改寫成留空,本檔照做——否則常數段會吐出
    ±inf 或無意義的相關系數。
  · ``Rsquare(x, d)``:同樣以輸入的滾動標準差貼近 0 為留空條件。
  · ``Slope`` / ``Rsquare`` / ``Resi`` 是窗口內的一元線性迴歸,自變數是**窗口
    位置** x = 1..d(最新那格 = d)。不足一個窗口時 qlib 以 NaN 補在最舊那邊,
    有效點的 x 仍是靠右那幾個;斜率與 R² 對 x 平移不變,故等同對 1..N 迴歸。
    ``Resi`` 取的是**最新那格**的殘差 ``y_d - (slope*d + intercept)``。

與官方數值的差距(2026-08-29 實測)
-----------------------------------

在起步宇宙十二隻、2015-01-02 至 2026-08-26 共 2,929 個交易日上,把本檔算出的
158 欄逐欄對住「官方表達式獨立求值」(以 qlib 自己那個編譯好的滾動核心算
Slope/Rsquare/Resi)::

    12 隻 × 158 欄 = 1,896 次對照
      1,716 欄  逐位相同(bit-identical)
         19 欄  相對差 < 1e-9
        161 欄  相對差 ≥ 1e-9,全部落在 BETA / RSQR / RESI 三族,最大 6.7e-05

那 161 欄的差**不是算法不同,是 qlib 那邊的浮點漂移**:它的滾動迴歸用一條
「加新的、減舊的」增量累加器貫穿整條序列,誤差沿 2,929 格一路累積;本檔每個
窗口重新算一次。以有理數(``fractions.Fraction``)算出精確值再比,本檔在雙方
分歧最大那幾格上比 qlib **近 2 至 5 個數量級**——差的是官方那邊。其餘 155 條
沒有這回事,逐位相同。

本檔不做的事
------------

  · **不入庫**。輸出是一張記憶體裡的長表;要落 ``factor_value``,經唯一入口
    ``karst.gateway``(D-020 第 4 條),那是 KARST-063 之後另一張票的事。
  · **不設參數預設值**(D-008 第 3 條)。窗口 ``(5, 10, 20, 30, 60)`` 與
    epsilon ``1e-12`` 不是參數——它們是 Alpha158 這個定義本身的一部分,改了
    就不再是 Alpha158,所以以常數寫死,不開成可調的入參。
  · **不理會 ``bar_status``**。停牌填補的那根 K 線是不是要餵進來,由呼叫方
    決定(D-026 第 6 條);本檔照收到的數算,留空的格算出來照樣留空。

用法::

    from karst.data import read_price_frame
    from karst.factors import compute_alpha158

    bars = read_price_frame(store, snapshot_id)      # 日期 × 實體 的日線長表
    values = compute_alpha158(bars)                  # 日期 × 實體 × 因子名 → 值
    values.head()
    #          date  entity_id factor     value
    #    2015-01-02          1   KMID  0.001234
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

import numpy as np
import pandas as pd

from ..errors import ContractViolation

# Alpha158 定義的一部分,不是參數(見模組說明〈本檔不做的事〉)。
ALPHA158_WINDOWS: Final[tuple[int, ...]] = (5, 10, 20, 30, 60)
EPSILON: Final[float] = 1e-12

# qlib 對「滾動標準差貼近 0」的判準(ops.py 的 Corr 與 Rsquare 都用這一個)。
FLAT_ATOL: Final[float] = 2e-05

#: 本檔對成交量加權平均價的近似(唯一一處近似,見模組說明)。
VWAP_APPROXIMATION: Final[str] = "(high + low + close) / 3"

#: 用了近似值的因子名。其餘 157 條全部是官方原式。
ALPHA158_APPROXIMATED: Final[tuple[str, ...]] = ("VWAP0",)

#: 輸出長表的欄序。
LONG_COLUMNS: Final[tuple[str, ...]] = ("date", "entity_id", "factor", "value")

_REQUIRED_COLUMNS: Final[tuple[str, ...]] = ("open", "high", "low", "close", "volume")

# --------------------------------------------------------------------------
# 官方表達式清單(pyqlib 0.9.7 的 Alpha158DL.get_feature_config() 逐字輸出)。
# 這一份是「算得對不對」的正本:本檔的計算碼與它並排放,對不上就是本檔錯。
# --------------------------------------------------------------------------
ALPHA158_EXPRESSIONS: Final[Mapping[str, str]] = MappingProxyType(
    {
        # ---- K 線形態組(9)----
        "KMID": "($close-$open)/$open",
        "KLEN": "($high-$low)/$open",
        "KMID2": "($close-$open)/($high-$low+1e-12)",
        "KUP": "($high-Greater($open, $close))/$open",
        "KUP2": "($high-Greater($open, $close))/($high-$low+1e-12)",
        "KLOW": "(Less($open, $close)-$low)/$open",
        "KLOW2": "(Less($open, $close)-$low)/($high-$low+1e-12)",
        "KSFT": "(2*$close-$high-$low)/$open",
        "KSFT2": "(2*$close-$high-$low)/($high-$low+1e-12)",
        # ---- 價格組(4)----
        "OPEN0": "$open/$close",
        "HIGH0": "$high/$close",
        "LOW0": "$low/$close",
        "VWAP0": "$vwap/$close",
        # ---- 滾動窗口組(145 = 29 × 5)----
        "ROC5": "Ref($close, 5)/$close",
        "ROC10": "Ref($close, 10)/$close",
        "ROC20": "Ref($close, 20)/$close",
        "ROC30": "Ref($close, 30)/$close",
        "ROC60": "Ref($close, 60)/$close",
        "MA5": "Mean($close, 5)/$close",
        "MA10": "Mean($close, 10)/$close",
        "MA20": "Mean($close, 20)/$close",
        "MA30": "Mean($close, 30)/$close",
        "MA60": "Mean($close, 60)/$close",
        "STD5": "Std($close, 5)/$close",
        "STD10": "Std($close, 10)/$close",
        "STD20": "Std($close, 20)/$close",
        "STD30": "Std($close, 30)/$close",
        "STD60": "Std($close, 60)/$close",
        "BETA5": "Slope($close, 5)/$close",
        "BETA10": "Slope($close, 10)/$close",
        "BETA20": "Slope($close, 20)/$close",
        "BETA30": "Slope($close, 30)/$close",
        "BETA60": "Slope($close, 60)/$close",
        "RSQR5": "Rsquare($close, 5)",
        "RSQR10": "Rsquare($close, 10)",
        "RSQR20": "Rsquare($close, 20)",
        "RSQR30": "Rsquare($close, 30)",
        "RSQR60": "Rsquare($close, 60)",
        "RESI5": "Resi($close, 5)/$close",
        "RESI10": "Resi($close, 10)/$close",
        "RESI20": "Resi($close, 20)/$close",
        "RESI30": "Resi($close, 30)/$close",
        "RESI60": "Resi($close, 60)/$close",
        "MAX5": "Max($high, 5)/$close",
        "MAX10": "Max($high, 10)/$close",
        "MAX20": "Max($high, 20)/$close",
        "MAX30": "Max($high, 30)/$close",
        "MAX60": "Max($high, 60)/$close",
        "MIN5": "Min($low, 5)/$close",
        "MIN10": "Min($low, 10)/$close",
        "MIN20": "Min($low, 20)/$close",
        "MIN30": "Min($low, 30)/$close",
        "MIN60": "Min($low, 60)/$close",
        "QTLU5": "Quantile($close, 5, 0.8)/$close",
        "QTLU10": "Quantile($close, 10, 0.8)/$close",
        "QTLU20": "Quantile($close, 20, 0.8)/$close",
        "QTLU30": "Quantile($close, 30, 0.8)/$close",
        "QTLU60": "Quantile($close, 60, 0.8)/$close",
        "QTLD5": "Quantile($close, 5, 0.2)/$close",
        "QTLD10": "Quantile($close, 10, 0.2)/$close",
        "QTLD20": "Quantile($close, 20, 0.2)/$close",
        "QTLD30": "Quantile($close, 30, 0.2)/$close",
        "QTLD60": "Quantile($close, 60, 0.2)/$close",
        "RANK5": "Rank($close, 5)",
        "RANK10": "Rank($close, 10)",
        "RANK20": "Rank($close, 20)",
        "RANK30": "Rank($close, 30)",
        "RANK60": "Rank($close, 60)",
        "RSV5": "($close-Min($low, 5))/(Max($high, 5)-Min($low, 5)+1e-12)",
        "RSV10": "($close-Min($low, 10))/(Max($high, 10)-Min($low, 10)+1e-12)",
        "RSV20": "($close-Min($low, 20))/(Max($high, 20)-Min($low, 20)+1e-12)",
        "RSV30": "($close-Min($low, 30))/(Max($high, 30)-Min($low, 30)+1e-12)",
        "RSV60": "($close-Min($low, 60))/(Max($high, 60)-Min($low, 60)+1e-12)",
        "IMAX5": "IdxMax($high, 5)/5",
        "IMAX10": "IdxMax($high, 10)/10",
        "IMAX20": "IdxMax($high, 20)/20",
        "IMAX30": "IdxMax($high, 30)/30",
        "IMAX60": "IdxMax($high, 60)/60",
        "IMIN5": "IdxMin($low, 5)/5",
        "IMIN10": "IdxMin($low, 10)/10",
        "IMIN20": "IdxMin($low, 20)/20",
        "IMIN30": "IdxMin($low, 30)/30",
        "IMIN60": "IdxMin($low, 60)/60",
        "IMXD5": "(IdxMax($high, 5)-IdxMin($low, 5))/5",
        "IMXD10": "(IdxMax($high, 10)-IdxMin($low, 10))/10",
        "IMXD20": "(IdxMax($high, 20)-IdxMin($low, 20))/20",
        "IMXD30": "(IdxMax($high, 30)-IdxMin($low, 30))/30",
        "IMXD60": "(IdxMax($high, 60)-IdxMin($low, 60))/60",
        "CORR5": "Corr($close, Log($volume+1), 5)",
        "CORR10": "Corr($close, Log($volume+1), 10)",
        "CORR20": "Corr($close, Log($volume+1), 20)",
        "CORR30": "Corr($close, Log($volume+1), 30)",
        "CORR60": "Corr($close, Log($volume+1), 60)",
        "CORD5": "Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), 5)",
        "CORD10": "Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), 10)",
        "CORD20": "Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), 20)",
        "CORD30": "Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), 30)",
        "CORD60": "Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), 60)",
        "CNTP5": "Mean($close>Ref($close, 1), 5)",
        "CNTP10": "Mean($close>Ref($close, 1), 10)",
        "CNTP20": "Mean($close>Ref($close, 1), 20)",
        "CNTP30": "Mean($close>Ref($close, 1), 30)",
        "CNTP60": "Mean($close>Ref($close, 1), 60)",
        "CNTN5": "Mean($close<Ref($close, 1), 5)",
        "CNTN10": "Mean($close<Ref($close, 1), 10)",
        "CNTN20": "Mean($close<Ref($close, 1), 20)",
        "CNTN30": "Mean($close<Ref($close, 1), 30)",
        "CNTN60": "Mean($close<Ref($close, 1), 60)",
        "CNTD5": "Mean($close>Ref($close, 1), 5)-Mean($close<Ref($close, 1), 5)",
        "CNTD10": "Mean($close>Ref($close, 1), 10)-Mean($close<Ref($close, 1), 10)",
        "CNTD20": "Mean($close>Ref($close, 1), 20)-Mean($close<Ref($close, 1), 20)",
        "CNTD30": "Mean($close>Ref($close, 1), 30)-Mean($close<Ref($close, 1), 30)",
        "CNTD60": "Mean($close>Ref($close, 1), 60)-Mean($close<Ref($close, 1), 60)",
        "SUMP5": (
            "Sum(Greater($close-Ref($close, 1), 0), 5)"
            "/(Sum(Abs($close-Ref($close, 1)), 5)+1e-12)"
        ),
        "SUMP10": (
            "Sum(Greater($close-Ref($close, 1), 0), 10)"
            "/(Sum(Abs($close-Ref($close, 1)), 10)+1e-12)"
        ),
        "SUMP20": (
            "Sum(Greater($close-Ref($close, 1), 0), 20)"
            "/(Sum(Abs($close-Ref($close, 1)), 20)+1e-12)"
        ),
        "SUMP30": (
            "Sum(Greater($close-Ref($close, 1), 0), 30)"
            "/(Sum(Abs($close-Ref($close, 1)), 30)+1e-12)"
        ),
        "SUMP60": (
            "Sum(Greater($close-Ref($close, 1), 0), 60)"
            "/(Sum(Abs($close-Ref($close, 1)), 60)+1e-12)"
        ),
        "SUMN5": (
            "Sum(Greater(Ref($close, 1)-$close, 0), 5)"
            "/(Sum(Abs($close-Ref($close, 1)), 5)+1e-12)"
        ),
        "SUMN10": (
            "Sum(Greater(Ref($close, 1)-$close, 0), 10)"
            "/(Sum(Abs($close-Ref($close, 1)), 10)+1e-12)"
        ),
        "SUMN20": (
            "Sum(Greater(Ref($close, 1)-$close, 0), 20)"
            "/(Sum(Abs($close-Ref($close, 1)), 20)+1e-12)"
        ),
        "SUMN30": (
            "Sum(Greater(Ref($close, 1)-$close, 0), 30)"
            "/(Sum(Abs($close-Ref($close, 1)), 30)+1e-12)"
        ),
        "SUMN60": (
            "Sum(Greater(Ref($close, 1)-$close, 0), 60)"
            "/(Sum(Abs($close-Ref($close, 1)), 60)+1e-12)"
        ),
        "SUMD5": (
            "(Sum(Greater($close-Ref($close, 1), 0), 5)"
            "-Sum(Greater(Ref($close, 1)-$close, 0), 5))"
            "/(Sum(Abs($close-Ref($close, 1)), 5)+1e-12)"
        ),
        "SUMD10": (
            "(Sum(Greater($close-Ref($close, 1), 0), 10)"
            "-Sum(Greater(Ref($close, 1)-$close, 0), 10))"
            "/(Sum(Abs($close-Ref($close, 1)), 10)+1e-12)"
        ),
        "SUMD20": (
            "(Sum(Greater($close-Ref($close, 1), 0), 20)"
            "-Sum(Greater(Ref($close, 1)-$close, 0), 20))"
            "/(Sum(Abs($close-Ref($close, 1)), 20)+1e-12)"
        ),
        "SUMD30": (
            "(Sum(Greater($close-Ref($close, 1), 0), 30)"
            "-Sum(Greater(Ref($close, 1)-$close, 0), 30))"
            "/(Sum(Abs($close-Ref($close, 1)), 30)+1e-12)"
        ),
        "SUMD60": (
            "(Sum(Greater($close-Ref($close, 1), 0), 60)"
            "-Sum(Greater(Ref($close, 1)-$close, 0), 60))"
            "/(Sum(Abs($close-Ref($close, 1)), 60)+1e-12)"
        ),
        "VMA5": "Mean($volume, 5)/($volume+1e-12)",
        "VMA10": "Mean($volume, 10)/($volume+1e-12)",
        "VMA20": "Mean($volume, 20)/($volume+1e-12)",
        "VMA30": "Mean($volume, 30)/($volume+1e-12)",
        "VMA60": "Mean($volume, 60)/($volume+1e-12)",
        "VSTD5": "Std($volume, 5)/($volume+1e-12)",
        "VSTD10": "Std($volume, 10)/($volume+1e-12)",
        "VSTD20": "Std($volume, 20)/($volume+1e-12)",
        "VSTD30": "Std($volume, 30)/($volume+1e-12)",
        "VSTD60": "Std($volume, 60)/($volume+1e-12)",
        "WVMA5": (
            "Std(Abs($close/Ref($close, 1)-1)*$volume, 5)"
            "/(Mean(Abs($close/Ref($close, 1)-1)*$volume, 5)+1e-12)"
        ),
        "WVMA10": (
            "Std(Abs($close/Ref($close, 1)-1)*$volume, 10)"
            "/(Mean(Abs($close/Ref($close, 1)-1)*$volume, 10)+1e-12)"
        ),
        "WVMA20": (
            "Std(Abs($close/Ref($close, 1)-1)*$volume, 20)"
            "/(Mean(Abs($close/Ref($close, 1)-1)*$volume, 20)+1e-12)"
        ),
        "WVMA30": (
            "Std(Abs($close/Ref($close, 1)-1)*$volume, 30)"
            "/(Mean(Abs($close/Ref($close, 1)-1)*$volume, 30)+1e-12)"
        ),
        "WVMA60": (
            "Std(Abs($close/Ref($close, 1)-1)*$volume, 60)"
            "/(Mean(Abs($close/Ref($close, 1)-1)*$volume, 60)+1e-12)"
        ),
        "VSUMP5": (
            "Sum(Greater($volume-Ref($volume, 1), 0), 5)"
            "/(Sum(Abs($volume-Ref($volume, 1)), 5)+1e-12)"
        ),
        "VSUMP10": (
            "Sum(Greater($volume-Ref($volume, 1), 0), 10)"
            "/(Sum(Abs($volume-Ref($volume, 1)), 10)+1e-12)"
        ),
        "VSUMP20": (
            "Sum(Greater($volume-Ref($volume, 1), 0), 20)"
            "/(Sum(Abs($volume-Ref($volume, 1)), 20)+1e-12)"
        ),
        "VSUMP30": (
            "Sum(Greater($volume-Ref($volume, 1), 0), 30)"
            "/(Sum(Abs($volume-Ref($volume, 1)), 30)+1e-12)"
        ),
        "VSUMP60": (
            "Sum(Greater($volume-Ref($volume, 1), 0), 60)"
            "/(Sum(Abs($volume-Ref($volume, 1)), 60)+1e-12)"
        ),
        "VSUMN5": (
            "Sum(Greater(Ref($volume, 1)-$volume, 0), 5)"
            "/(Sum(Abs($volume-Ref($volume, 1)), 5)+1e-12)"
        ),
        "VSUMN10": (
            "Sum(Greater(Ref($volume, 1)-$volume, 0), 10)"
            "/(Sum(Abs($volume-Ref($volume, 1)), 10)+1e-12)"
        ),
        "VSUMN20": (
            "Sum(Greater(Ref($volume, 1)-$volume, 0), 20)"
            "/(Sum(Abs($volume-Ref($volume, 1)), 20)+1e-12)"
        ),
        "VSUMN30": (
            "Sum(Greater(Ref($volume, 1)-$volume, 0), 30)"
            "/(Sum(Abs($volume-Ref($volume, 1)), 30)+1e-12)"
        ),
        "VSUMN60": (
            "Sum(Greater(Ref($volume, 1)-$volume, 0), 60)"
            "/(Sum(Abs($volume-Ref($volume, 1)), 60)+1e-12)"
        ),
        "VSUMD5": (
            "(Sum(Greater($volume-Ref($volume, 1), 0), 5)"
            "-Sum(Greater(Ref($volume, 1)-$volume, 0), 5))"
            "/(Sum(Abs($volume-Ref($volume, 1)), 5)+1e-12)"
        ),
        "VSUMD10": (
            "(Sum(Greater($volume-Ref($volume, 1), 0), 10)"
            "-Sum(Greater(Ref($volume, 1)-$volume, 0), 10))"
            "/(Sum(Abs($volume-Ref($volume, 1)), 10)+1e-12)"
        ),
        "VSUMD20": (
            "(Sum(Greater($volume-Ref($volume, 1), 0), 20)"
            "-Sum(Greater(Ref($volume, 1)-$volume, 0), 20))"
            "/(Sum(Abs($volume-Ref($volume, 1)), 20)+1e-12)"
        ),
        "VSUMD30": (
            "(Sum(Greater($volume-Ref($volume, 1), 0), 30)"
            "-Sum(Greater(Ref($volume, 1)-$volume, 0), 30))"
            "/(Sum(Abs($volume-Ref($volume, 1)), 30)+1e-12)"
        ),
        "VSUMD60": (
            "(Sum(Greater($volume-Ref($volume, 1), 0), 60)"
            "-Sum(Greater(Ref($volume, 1)-$volume, 0), 60))"
            "/(Sum(Abs($volume-Ref($volume, 1)), 60)+1e-12)"
        ),
    }
)

#: 158 條因子名,官方次序。
ALPHA158_NAMES: Final[tuple[str, ...]] = tuple(ALPHA158_EXPRESSIONS)

_KBAR_NAMES: Final[tuple[str, ...]] = (
    "KMID", "KLEN", "KMID2", "KUP", "KUP2", "KLOW", "KLOW2", "KSFT", "KSFT2",
)
_PRICE_NAMES: Final[tuple[str, ...]] = ("OPEN0", "HIGH0", "LOW0", "VWAP0")

#: 逐組因子名(模組說明那張表的機讀版)。
ALPHA158_GROUPS: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "kbar": _KBAR_NAMES,
        "price": _PRICE_NAMES,
        "volume": (),
        "rolling": tuple(
            name
            for name in ALPHA158_NAMES
            if name not in _KBAR_NAMES and name not in _PRICE_NAMES
        ),
    }
)


# --------------------------------------------------------------------------
# 運算子層:一個函式對一個 qlib 運算子,語意見模組說明〈運算子語意〉。
# --------------------------------------------------------------------------


def op_ref(series: pd.Series, periods: int) -> pd.Series:
    """``Ref(x, d)``:d 個交易日之前那一格的值。"""
    return series.shift(periods)


def op_mean(series: pd.Series, window: int) -> pd.Series:
    """``Mean(x, d)``。"""
    return series.rolling(window, min_periods=1).mean()


def op_sum(series: pd.Series, window: int) -> pd.Series:
    """``Sum(x, d)``。"""
    return series.rolling(window, min_periods=1).sum()


def op_std(series: pd.Series, window: int) -> pd.Series:
    """``Std(x, d)``,pandas 預設 ``ddof=1``(樣本標準差)。"""
    return series.rolling(window, min_periods=1).std()


def op_max(series: pd.Series, window: int) -> pd.Series:
    """``Max(x, d)``。"""
    return series.rolling(window, min_periods=1).max()


def op_min(series: pd.Series, window: int) -> pd.Series:
    """``Min(x, d)``。"""
    return series.rolling(window, min_periods=1).min()


def op_quantile(series: pd.Series, window: int, quantile: float) -> pd.Series:
    """``Quantile(x, d, q)``。"""
    return series.rolling(window, min_periods=1).quantile(quantile)


def op_rank(series: pd.Series, window: int) -> pd.Series:
    """``Rank(x, d)``:今日值在窗口內的百分位名次(1 = 窗口內最高)。"""
    return series.rolling(window, min_periods=1).rank(pct=True)


def op_idxmax(series: pd.Series, window: int) -> pd.Series:
    """``IdxMax(x, d)``:窗口內最高那格的位置,**由最舊那格數起、1 起計**。"""
    return series.rolling(window, min_periods=1).apply(
        lambda block: block.argmax() + 1, raw=True
    )


def op_idxmin(series: pd.Series, window: int) -> pd.Series:
    """``IdxMin(x, d)``:窗口內最低那格的位置,由最舊那格數起、1 起計。"""
    return series.rolling(window, min_periods=1).apply(
        lambda block: block.argmin() + 1, raw=True
    )


def _flat(series: pd.Series, window: int) -> np.ndarray:
    """窗口內近乎沒有波動的那幾格(qlib 用它把相關系數與 R² 改寫成留空)。"""
    return np.isclose(
        op_std(series, window).to_numpy("float64"), 0.0, atol=FLAT_ATOL
    )


def op_corr(left: pd.Series, right: pd.Series, window: int) -> pd.Series:
    """``Corr(a, b, d)``:任何一邊在窗口內近乎不動,那一格留空。"""
    with np.errstate(invalid="ignore", divide="ignore"):
        result = left.rolling(window, min_periods=1).corr(right)
    result[_flat(left, window) | _flat(right, window)] = np.nan
    return result


def _regression_terms(
    series: pd.Series, window: int
) -> tuple[np.ndarray, ...]:
    """窗口內一元線性迴歸的六個累加項,自變數是窗口位置 x = 1..d。

    以 NaN 補在最舊那一邊還原 qlib 的做法(``rolling.pyx`` 那條 deque 一開始
    就是 d 格 NaN):窗口未滿時有效點靠右排,x 仍然是 ``d-N+1 .. d``。
    """
    values = series.to_numpy("float64")
    padded = np.concatenate([np.full(window - 1, np.nan, dtype="float64"), values])
    view = np.lib.stride_tricks.sliding_window_view(padded, window)
    present = ~np.isnan(view)
    y = np.where(present, view, 0.0)
    x = np.where(present, np.arange(1, window + 1, dtype="float64"), 0.0)
    count = present.sum(axis=1).astype("float64")
    return (
        count,
        x.sum(axis=1),
        (x * x).sum(axis=1),
        y.sum(axis=1),
        (y * y).sum(axis=1),
        (x * y).sum(axis=1),
    )


def op_slope(series: pd.Series, window: int) -> pd.Series:
    """``Slope(x, d)``:窗口內對窗口位置做一元線性迴歸的斜率。"""
    count, sum_x, sum_x2, sum_y, _, sum_xy = _regression_terms(series, window)
    with np.errstate(invalid="ignore", divide="ignore"):
        slope = (count * sum_xy - sum_x * sum_y) / (count * sum_x2 - sum_x * sum_x)
    return pd.Series(slope, index=series.index)


def op_rsquare(series: pd.Series, window: int) -> pd.Series:
    """``Rsquare(x, d)``:同一條迴歸的 R²;窗口內近乎不動那幾格留空。"""
    count, sum_x, sum_x2, sum_y, sum_y2, sum_xy = _regression_terms(series, window)
    with np.errstate(invalid="ignore", divide="ignore"):
        r_value = (count * sum_xy - sum_x * sum_y) / np.sqrt(
            (count * sum_x2 - sum_x * sum_x) * (count * sum_y2 - sum_y * sum_y)
        )
        result = pd.Series(r_value * r_value, index=series.index)
    result[_flat(series, window)] = np.nan
    return result


def op_resi(series: pd.Series, window: int) -> pd.Series:
    """``Resi(x, d)``:同一條迴歸之下,**最新那一格**的殘差。"""
    count, sum_x, sum_x2, sum_y, _, sum_xy = _regression_terms(series, window)
    with np.errstate(invalid="ignore", divide="ignore"):
        slope = (count * sum_xy - sum_x * sum_y) / (count * sum_x2 - sum_x * sum_x)
        intercept = sum_y / count - slope * (sum_x / count)
        residual = series.to_numpy("float64") - (slope * window + intercept)
    return pd.Series(residual, index=series.index)


# --------------------------------------------------------------------------
# 158 條的計算
# --------------------------------------------------------------------------


def compute_alpha158_for_entity(bars: pd.DataFrame) -> pd.DataFrame:
    """一個實體的日線 OHLCV → 「日期 × 因子名」寬表(158 欄,官方次序)。

    ``bars`` 要有 ``open``、``high``、``low``、``close``、``volume`` 五欄,
    **已按日期由舊到新排好**;有 ``date`` 欄就用它做索引,否則沿用原索引。
    多出來的欄(``entity_id``、``bar_status`` 一類)一概不理。

    留空的格留空:停牌那日算出來就是留空,不是零(D-026 第 6 條)。
    """
    missing = [column for column in _REQUIRED_COLUMNS if column not in bars.columns]
    if missing:
        raise ContractViolation(f"日線缺欄:{'、'.join(missing)}")

    frame = bars.reset_index(drop=True) if "date" in bars.columns else bars
    index = pd.Index(frame["date"], name="date") if "date" in frame.columns else frame.index

    open_ = pd.Series(frame["open"].to_numpy("float64"), index=index)
    high = pd.Series(frame["high"].to_numpy("float64"), index=index)
    low = pd.Series(frame["low"].to_numpy("float64"), index=index)
    close = pd.Series(frame["close"].to_numpy("float64"), index=index)
    volume = pd.Series(frame["volume"].to_numpy("float64"), index=index)

    # 唯一一處近似:日線來源沒有成交量加權平均價,以典型價代之(見模組說明)。
    vwap = (high + low + close) / 3.0

    amplitude = high - low + EPSILON
    body_top = pd.Series(np.maximum(open_.to_numpy(), close.to_numpy()), index=index)
    body_bottom = pd.Series(np.minimum(open_.to_numpy(), close.to_numpy()), index=index)

    out: dict[str, pd.Series] = {}

    # ---- K 線形態組(9)----
    out["KMID"] = (close - open_) / open_
    out["KLEN"] = (high - low) / open_
    out["KMID2"] = (close - open_) / amplitude
    out["KUP"] = (high - body_top) / open_
    out["KUP2"] = (high - body_top) / amplitude
    out["KLOW"] = (body_bottom - low) / open_
    out["KLOW2"] = (body_bottom - low) / amplitude
    out["KSFT"] = (2.0 * close - high - low) / open_
    out["KSFT2"] = (2.0 * close - high - low) / amplitude

    # ---- 價格組(4)----
    out["OPEN0"] = open_ / close
    out["HIGH0"] = high / close
    out["LOW0"] = low / close
    out["VWAP0"] = vwap / close

    # ---- 滾動窗口組(145)的共用中間量 ----
    previous_close = op_ref(close, 1)
    previous_volume = op_ref(volume, 1)
    close_change = close - previous_close
    volume_change = volume - previous_volume
    with np.errstate(invalid="ignore", divide="ignore"):
        log_volume = pd.Series(
            np.log(volume.to_numpy("float64") + 1.0), index=index
        )
        log_volume_ratio = pd.Series(
            np.log((volume / previous_volume).to_numpy("float64") + 1.0), index=index
        )
    close_ratio = close / previous_close
    weighted_move = (close_ratio - 1.0).abs() * volume

    close_gain = pd.Series(
        np.maximum(close_change.to_numpy("float64"), 0.0), index=index
    )
    close_loss = pd.Series(
        np.maximum(-close_change.to_numpy("float64"), 0.0), index=index
    )
    close_move = close_change.abs()
    volume_gain = pd.Series(
        np.maximum(volume_change.to_numpy("float64"), 0.0), index=index
    )
    volume_loss = pd.Series(
        np.maximum(-volume_change.to_numpy("float64"), 0.0), index=index
    )
    volume_move = volume_change.abs()

    up_day = (close > previous_close).astype("float64")
    down_day = (close < previous_close).astype("float64")

    for window in ALPHA158_WINDOWS:
        rolling_low = op_min(low, window)
        rolling_high = op_max(high, window)
        gain_sum = op_sum(close_gain, window)
        loss_sum = op_sum(close_loss, window)
        move_sum = op_sum(close_move, window) + EPSILON
        volume_gain_sum = op_sum(volume_gain, window)
        volume_loss_sum = op_sum(volume_loss, window)
        volume_move_sum = op_sum(volume_move, window) + EPSILON
        up_share = op_mean(up_day, window)
        down_share = op_mean(down_day, window)

        out[f"ROC{window}"] = op_ref(close, window) / close
        out[f"MA{window}"] = op_mean(close, window) / close
        out[f"STD{window}"] = op_std(close, window) / close
        out[f"BETA{window}"] = op_slope(close, window) / close
        out[f"RSQR{window}"] = op_rsquare(close, window)
        out[f"RESI{window}"] = op_resi(close, window) / close
        out[f"MAX{window}"] = rolling_high / close
        out[f"MIN{window}"] = rolling_low / close
        out[f"QTLU{window}"] = op_quantile(close, window, 0.8) / close
        out[f"QTLD{window}"] = op_quantile(close, window, 0.2) / close
        out[f"RANK{window}"] = op_rank(close, window)
        out[f"RSV{window}"] = (close - rolling_low) / (
            rolling_high - rolling_low + EPSILON
        )
        out[f"IMAX{window}"] = op_idxmax(high, window) / window
        out[f"IMIN{window}"] = op_idxmin(low, window) / window
        out[f"IMXD{window}"] = (
            op_idxmax(high, window) - op_idxmin(low, window)
        ) / window
        out[f"CORR{window}"] = op_corr(close, log_volume, window)
        out[f"CORD{window}"] = op_corr(close_ratio, log_volume_ratio, window)
        out[f"CNTP{window}"] = up_share
        out[f"CNTN{window}"] = down_share
        out[f"CNTD{window}"] = up_share - down_share
        out[f"SUMP{window}"] = gain_sum / move_sum
        out[f"SUMN{window}"] = loss_sum / move_sum
        out[f"SUMD{window}"] = (gain_sum - loss_sum) / move_sum
        out[f"VMA{window}"] = op_mean(volume, window) / (volume + EPSILON)
        out[f"VSTD{window}"] = op_std(volume, window) / (volume + EPSILON)
        out[f"WVMA{window}"] = op_std(weighted_move, window) / (
            op_mean(weighted_move, window) + EPSILON
        )
        out[f"VSUMP{window}"] = volume_gain_sum / volume_move_sum
        out[f"VSUMN{window}"] = volume_loss_sum / volume_move_sum
        out[f"VSUMD{window}"] = (
            volume_gain_sum - volume_loss_sum
        ) / volume_move_sum

    wide = pd.DataFrame({name: out[name] for name in ALPHA158_NAMES}, index=index)
    return wide.astype("float64")


def compute_alpha158(bars: pd.DataFrame) -> pd.DataFrame:
    """K 線面板(日線長表)→ 「日期 × 實體 × 因子名 → 值」長表。

    ``bars`` 是 ``karst.data.read_price_frame`` 那個形狀:``date``、
    ``entity_id`` 加開高低收量五欄(``bar_status`` 一類多出來的欄不理)。
    逐個實體按日期排好之後各自算一次,**實體之間互不影響**——Alpha158 全部
    158 條都是單一實體的時序運算,沒有橫斷面的一條。

    回傳欄位 ``date``、``entity_id``、``factor``、``value``:一列一格因子值,
    按日期、實體、官方因子次序排好。``factor`` 是有序類別欄(categorical),
    類別次序就是 ``ALPHA158_NAMES``——5,000 萬列的長表用字串欄裝不下,
    這一格的次序同時就是官方次序。

    **只算不入庫**:這張表要落 ``factor_value``,經唯一入口另辦。
    """
    for column in ("date", "entity_id", *_REQUIRED_COLUMNS):
        if column not in bars.columns:
            raise ContractViolation(f"日線長表缺欄:{column}")
    if bars.duplicated(["date", "entity_id"]).any():
        raise ContractViolation("日線長表同一日同一實體有多過一列,分不出哪一根 K 線")

    pieces: list[pd.DataFrame] = []
    for entity_id, group in bars.groupby("entity_id", sort=True):
        ordered = group.sort_values("date", kind="stable")
        wide = compute_alpha158_for_entity(ordered)
        rows = len(wide)
        factor_codes = np.tile(np.arange(len(ALPHA158_NAMES), dtype="int16"), rows)
        pieces.append(
            pd.DataFrame(
                {
                    "date": np.repeat(wide.index.to_numpy(), len(ALPHA158_NAMES)),
                    "entity_id": np.full(rows * len(ALPHA158_NAMES), entity_id, "int64"),
                    "factor": pd.Categorical.from_codes(
                        factor_codes, categories=ALPHA158_NAMES, ordered=True
                    ),
                    "value": wide.to_numpy("float64").reshape(-1),
                }
            )
        )

    if not pieces:
        return pd.DataFrame(
            {
                "date": pd.Series(dtype=bars["date"].dtype),
                "entity_id": pd.Series(dtype="int64"),
                "factor": pd.Categorical([], categories=ALPHA158_NAMES, ordered=True),
                "value": pd.Series(dtype="float64"),
            }
        )

    long = pd.concat(pieces, ignore_index=True)
    # stable 排序:同一日同一實體那 158 列維持官方次序,不用再排第三個鍵。
    long = long.sort_values(["date", "entity_id"], kind="stable").reset_index(drop=True)
    return long.loc[:, list(LONG_COLUMNS)]
