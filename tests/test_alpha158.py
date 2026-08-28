"""KARST-063 驗收:Alpha158 的 pandas 實作。

三件事對住票上三條驗收條件:

1. 逐組條數(9 + 4 + 0 + 145 = 158)與 qlib 官方 ``get_feature_config()``
   核實一致——官方那一跑在臨時環境做過(見模組說明),這裡守住它的結果。
2. 小樣本上二十條因子的數值與**公開定義**對照:期望值在本檔逐條手算,
   用的是 Python 內建算術與 ``statistics``,**一個運算子都不借模組自己的**
   ——借了就變成自己對自己,證不到任何事。
3. 起步宇宙十二隻上 158 條全部算得出(有本機快照才跑,沒有就 skip 並講明)。

只跑本檔:``python -m pytest tests/test_alpha158.py``。
"""

from __future__ import annotations

import math
import statistics
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from karst.errors import ContractViolation
from karst.factors.alpha158 import (
    ALPHA158_APPROXIMATED,
    ALPHA158_EXPRESSIONS,
    ALPHA158_GROUPS,
    ALPHA158_NAMES,
    ALPHA158_WINDOWS,
    LONG_COLUMNS,
    compute_alpha158,
    compute_alpha158_for_entity,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

# 起步宇宙十二隻那個快照(KARST-057 之後凍的那批,data/ 不入 git)。
STARTER_SNAPSHOT = REPO_ROOT / "data" / "snapshots" / "2026-08-28-a508d635a5fa"

# --------------------------------------------------------------------------
# 手算樣本:八根 K 線,全部整數,人手算得清楚。
# 窗口 5 在最後一格(索引 7)蓋住索引 3..7。
# --------------------------------------------------------------------------
OPEN = [10.0, 11.0, 12.0, 11.0, 13.0, 14.0, 12.0, 15.0]
HIGH = [11.0, 13.0, 13.0, 12.0, 15.0, 15.0, 14.0, 16.0]
LOW = [9.0, 10.0, 11.0, 10.0, 12.0, 13.0, 11.0, 14.0]
CLOSE = [11.0, 12.0, 11.0, 12.0, 14.0, 13.0, 13.0, 16.0]
VOLUME = [100.0, 200.0, 150.0, 300.0, 250.0, 400.0, 350.0, 500.0]

LAST = 7  # 最後一格的索引
TOLERANCE = 1e-9


@pytest.fixture(scope="module")
def sample_bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [f"2026-01-{day:02d}" for day in range(5, 13)],
            "open": OPEN,
            "high": HIGH,
            "low": LOW,
            "close": CLOSE,
            "volume": VOLUME,
        }
    )


@pytest.fixture(scope="module")
def sample_factors(sample_bars: pd.DataFrame) -> pd.DataFrame:
    return compute_alpha158_for_entity(sample_bars)


# --------------------------------------------------------------------------
# 驗收條件 1:逐組條數
# --------------------------------------------------------------------------


def test_名單合共一百五十八條且無重複():
    assert len(ALPHA158_NAMES) == 158
    assert len(set(ALPHA158_NAMES)) == 158
    assert set(ALPHA158_NAMES) == set(ALPHA158_EXPRESSIONS)


def test_逐組條數對得上官方核實的數():
    # qlib 0.9.7 的 Alpha158DL.get_feature_config() 實測輸出。
    assert len(ALPHA158_GROUPS["kbar"]) == 9
    assert len(ALPHA158_GROUPS["price"]) == 4
    assert len(ALPHA158_GROUPS["volume"]) == 0
    assert len(ALPHA158_GROUPS["rolling"]) == 145
    assert sum(len(names) for names in ALPHA158_GROUPS.values()) == 158


def test_滾動組是二十九種運算子各五個窗口():
    stems: dict[str, list[int]] = {}
    for name in ALPHA158_GROUPS["rolling"]:
        stem = name.rstrip("0123456789")
        stems.setdefault(stem, []).append(int(name[len(stem):]))
    assert len(stems) == 29
    for stem, windows in stems.items():
        assert sorted(windows) == sorted(ALPHA158_WINDOWS), stem


def test_只有一條用近似值():
    assert ALPHA158_APPROXIMATED == ("VWAP0",)
    # 近似的那一條是唯一一條表達式要用到 $vwap 的。
    uses_vwap = [
        name for name, expr in ALPHA158_EXPRESSIONS.items() if "$vwap" in expr
    ]
    assert uses_vwap == list(ALPHA158_APPROXIMATED)


# --------------------------------------------------------------------------
# 驗收條件 2:二十條因子的數值對照公開定義(期望值全部在本檔手算)
# --------------------------------------------------------------------------


def test_K線形態組五條對照公開定義(sample_factors: pd.DataFrame):
    # KMID =($close-$open)/$open;最後一格 開 15、收 16。
    assert sample_factors["KMID"].iloc[LAST] == pytest.approx(1 / 15, rel=TOLERANCE)
    # KLEN =($high-$low)/$open =(16-14)/15
    assert sample_factors["KLEN"].iloc[LAST] == pytest.approx(2 / 15, rel=TOLERANCE)
    # KUP =($high-Greater($open,$close))/$open =(16-max(15,16))/15 = 0
    assert sample_factors["KUP"].iloc[LAST] == pytest.approx(0.0, abs=TOLERANCE)
    # KLOW =(Less($open,$close)-$low)/$open =(min(15,16)-14)/15
    assert sample_factors["KLOW"].iloc[LAST] == pytest.approx(1 / 15, rel=TOLERANCE)
    # KSFT =(2*$close-$high-$low)/$open =(32-16-14)/15
    assert sample_factors["KSFT"].iloc[LAST] == pytest.approx(2 / 15, rel=TOLERANCE)
    # KSFT2 的分母是振幅加 1e-12:(32-30)/(2+1e-12)
    assert sample_factors["KSFT2"].iloc[LAST] == pytest.approx(
        2 / (2 + 1e-12), rel=TOLERANCE
    )


def test_價格組三條與近似的成交均價那條(sample_factors: pd.DataFrame):
    assert sample_factors["OPEN0"].iloc[LAST] == pytest.approx(15 / 16, rel=TOLERANCE)
    assert sample_factors["HIGH0"].iloc[LAST] == pytest.approx(1.0, rel=TOLERANCE)
    assert sample_factors["LOW0"].iloc[LAST] == pytest.approx(14 / 16, rel=TOLERANCE)
    # VWAP0 用近似值:典型價(高+低+收)/3 除以收市價。
    typical = (16.0 + 14.0 + 16.0) / 3.0
    assert sample_factors["VWAP0"].iloc[LAST] == pytest.approx(
        typical / 16.0, rel=TOLERANCE
    )


def test_ROC與MA與STD對照公開定義(sample_factors: pd.DataFrame):
    # ROC5 = Ref($close,5)/$close:五個交易日前是索引 2,收 11。
    assert sample_factors["ROC5"].iloc[LAST] == pytest.approx(11 / 16, rel=TOLERANCE)
    window = CLOSE[3:8]  # [12, 14, 13, 13, 16]
    # MA5 = Mean($close,5)/$close
    assert sample_factors["MA5"].iloc[LAST] == pytest.approx(
        statistics.fmean(window) / 16.0, rel=TOLERANCE
    )
    # STD5 = Std($close,5)/$close;qlib 用 pandas 預設 ddof=1(樣本標準差)。
    assert sample_factors["STD5"].iloc[LAST] == pytest.approx(
        statistics.stdev(window) / 16.0, rel=TOLERANCE
    )
    # min_periods=1:第一格只有一個觀測,樣本標準差沒有定義,留空。
    assert math.isnan(sample_factors["STD5"].iloc[0])


def test_窗口未滿一樣出值(sample_factors: pd.DataFrame):
    # qlib 的滾動運算子一律 min_periods=1,序列開頭那幾格有值、不是留空。
    assert sample_factors["MA5"].iloc[2] == pytest.approx(
        statistics.fmean(CLOSE[0:3]) / CLOSE[2], rel=TOLERANCE
    )


def test_高低位與隨機值三條(sample_factors: pd.DataFrame):
    high_window = HIGH[3:8]  # [12, 15, 15, 14, 16]
    low_window = LOW[3:8]  # [10, 12, 13, 11, 14]
    assert sample_factors["MAX5"].iloc[LAST] == pytest.approx(
        max(high_window) / 16.0, rel=TOLERANCE
    )
    assert sample_factors["MIN5"].iloc[LAST] == pytest.approx(
        min(low_window) / 16.0, rel=TOLERANCE
    )
    # RSV =($close-Min($low,d))/(Max($high,d)-Min($low,d)+1e-12)
    assert sample_factors["RSV5"].iloc[LAST] == pytest.approx(
        (16.0 - min(low_window)) / (max(high_window) - min(low_window) + 1e-12),
        rel=TOLERANCE,
    )


def test_百分位兩條與名次一條(sample_factors: pd.DataFrame):
    window = sorted(CLOSE[3:8])  # [12, 13, 13, 14, 16]
    # pandas 的滾動 quantile 用線性插值:位置 = q*(n-1)。
    def quantile(values: list[float], q: float) -> float:
        position = q * (len(values) - 1)
        lower = math.floor(position)
        upper = math.ceil(position)
        return values[lower] + (position - lower) * (values[upper] - values[lower])

    assert sample_factors["QTLU5"].iloc[LAST] == pytest.approx(
        quantile(window, 0.8) / 16.0, rel=TOLERANCE
    )
    assert sample_factors["QTLD5"].iloc[LAST] == pytest.approx(
        quantile(window, 0.2) / 16.0, rel=TOLERANCE
    )
    # RANK 是百分位名次:16 是窗口五格之中最高的一格。
    assert sample_factors["RANK5"].iloc[LAST] == pytest.approx(1.0, rel=TOLERANCE)


def test_高低位位置三條(sample_factors: pd.DataFrame):
    # IdxMax 由窗口最舊那格數起、1 起計:高位在窗口最後一格,即 5。
    assert sample_factors["IMAX5"].iloc[LAST] == pytest.approx(5 / 5, rel=TOLERANCE)
    # 低位在窗口第一格(索引 3 的 10),即 1。
    assert sample_factors["IMIN5"].iloc[LAST] == pytest.approx(1 / 5, rel=TOLERANCE)
    assert sample_factors["IMXD5"].iloc[LAST] == pytest.approx(
        (5 - 1) / 5, rel=TOLERANCE
    )
    # 窗口未滿一樣由最舊那格數起:索引 1 的窗口是 [11, 13],高位在第 2 格。
    assert sample_factors["IMAX5"].iloc[1] == pytest.approx(2 / 5, rel=TOLERANCE)


def test_漲跌日佔比三條(sample_factors: pd.DataFrame):
    ups = sum(1 for i in range(3, 8) if CLOSE[i] > CLOSE[i - 1])
    downs = sum(1 for i in range(3, 8) if CLOSE[i] < CLOSE[i - 1])
    assert ups == 3 and downs == 1  # 平手那日(索引 6)兩邊都不計
    assert sample_factors["CNTP5"].iloc[LAST] == pytest.approx(ups / 5, rel=TOLERANCE)
    assert sample_factors["CNTN5"].iloc[LAST] == pytest.approx(downs / 5, rel=TOLERANCE)
    assert sample_factors["CNTD5"].iloc[LAST] == pytest.approx(
        (ups - downs) / 5, rel=TOLERANCE
    )
    # 第一格沒有前一日:np.greater(nan, x) 是 False,所以是 0,不是留空。
    assert sample_factors["CNTP5"].iloc[0] == pytest.approx(0.0, abs=TOLERANCE)


def test_動能三條與量動能三條(sample_factors: pd.DataFrame):
    gains = sum(max(CLOSE[i] - CLOSE[i - 1], 0.0) for i in range(3, 8))
    losses = sum(max(CLOSE[i - 1] - CLOSE[i], 0.0) for i in range(3, 8))
    moves = sum(abs(CLOSE[i] - CLOSE[i - 1]) for i in range(3, 8))
    assert (gains, losses, moves) == (6.0, 1.0, 7.0)
    assert sample_factors["SUMP5"].iloc[LAST] == pytest.approx(
        gains / (moves + 1e-12), rel=TOLERANCE
    )
    assert sample_factors["SUMN5"].iloc[LAST] == pytest.approx(
        losses / (moves + 1e-12), rel=TOLERANCE
    )
    assert sample_factors["SUMD5"].iloc[LAST] == pytest.approx(
        (gains - losses) / (moves + 1e-12), rel=TOLERANCE
    )

    volume_gains = sum(max(VOLUME[i] - VOLUME[i - 1], 0.0) for i in range(3, 8))
    volume_losses = sum(max(VOLUME[i - 1] - VOLUME[i], 0.0) for i in range(3, 8))
    volume_moves = sum(abs(VOLUME[i] - VOLUME[i - 1]) for i in range(3, 8))
    assert sample_factors["VSUMP5"].iloc[LAST] == pytest.approx(
        volume_gains / (volume_moves + 1e-12), rel=TOLERANCE
    )
    assert sample_factors["VSUMN5"].iloc[LAST] == pytest.approx(
        volume_losses / (volume_moves + 1e-12), rel=TOLERANCE
    )
    assert sample_factors["VSUMD5"].iloc[LAST] == pytest.approx(
        (volume_gains - volume_losses) / (volume_moves + 1e-12), rel=TOLERANCE
    )


def test_成交量三條(sample_factors: pd.DataFrame):
    window = VOLUME[3:8]
    assert sample_factors["VMA5"].iloc[LAST] == pytest.approx(
        statistics.fmean(window) / (500.0 + 1e-12), rel=TOLERANCE
    )
    assert sample_factors["VSTD5"].iloc[LAST] == pytest.approx(
        statistics.stdev(window) / (500.0 + 1e-12), rel=TOLERANCE
    )
    # WVMA = Std(|報酬|×量, d)/(Mean(|報酬|×量, d)+1e-12)
    weighted = [
        abs(CLOSE[i] / CLOSE[i - 1] - 1.0) * VOLUME[i] for i in range(3, 8)
    ]
    assert sample_factors["WVMA5"].iloc[LAST] == pytest.approx(
        statistics.stdev(weighted) / (statistics.fmean(weighted) + 1e-12),
        rel=TOLERANCE,
    )


def test_滾動迴歸三條(sample_factors: pd.DataFrame):
    # 自變數是窗口位置 x = 1..5(最新那格 = 5),因變數是窗口內收市價。
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = CLOSE[3:8]
    x_mean = statistics.fmean(xs)
    y_mean = statistics.fmean(ys)
    sxy = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    sxx = sum((x - x_mean) ** 2 for x in xs)
    syy = sum((y - y_mean) ** 2 for y in ys)
    slope = sxy / sxx
    intercept = y_mean - slope * x_mean
    assert (slope, intercept) == (0.7, 11.5)

    # BETA = Slope($close,d)/$close
    assert sample_factors["BETA5"].iloc[LAST] == pytest.approx(
        slope / 16.0, rel=TOLERANCE
    )
    # RSQR = Rsquare($close,d):決定系數 r²
    assert sample_factors["RSQR5"].iloc[LAST] == pytest.approx(
        sxy * sxy / (sxx * syy), rel=TOLERANCE
    )
    # RESI = Resi($close,d)/$close:最新那格(x=5)的殘差
    residual = ys[-1] - (slope * 5.0 + intercept)
    assert residual == pytest.approx(1.0, rel=TOLERANCE)
    assert sample_factors["RESI5"].iloc[LAST] == pytest.approx(
        residual / 16.0, rel=TOLERANCE
    )


def test_價量相關一條(sample_factors: pd.DataFrame):
    # CORR = Corr($close, Log($volume+1), d),即皮爾遜相關系數。
    xs = CLOSE[3:8]
    ys = [math.log(volume + 1.0) for volume in VOLUME[3:8]]
    x_mean = statistics.fmean(xs)
    y_mean = statistics.fmean(ys)
    sxy = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    sxx = sum((x - x_mean) ** 2 for x in xs)
    syy = sum((y - y_mean) ** 2 for y in ys)
    assert sample_factors["CORR5"].iloc[LAST] == pytest.approx(
        sxy / math.sqrt(sxx * syy), rel=TOLERANCE
    )


def test_常數段的相關系數與決定系數留空():
    # 一段完全不動的價格:相關系數與 r² 都沒有意義,qlib 把它們改寫成留空。
    flat = pd.DataFrame(
        {
            "date": [f"2026-02-{day:02d}" for day in range(1, 11)],
            "open": [20.0] * 10,
            "high": [20.0] * 10,
            "low": [20.0] * 10,
            "close": [20.0] * 10,
            "volume": [1000.0 + i for i in range(10)],
        }
    )
    factors = compute_alpha158_for_entity(flat)
    assert math.isnan(factors["CORR5"].iloc[-1])
    assert math.isnan(factors["RSQR5"].iloc[-1])


# --------------------------------------------------------------------------
# 驗收條件 3:起步宇宙十二隻上 158 條全部算得出
# --------------------------------------------------------------------------


def test_長表形狀與欄位():
    bars = pd.DataFrame(
        {
            "date": [f"2026-01-{day:02d}" for day in range(5, 13)] * 2,
            "entity_id": [1] * 8 + [2] * 8,
            "open": OPEN * 2,
            "high": HIGH * 2,
            "low": LOW * 2,
            "close": CLOSE * 2,
            "volume": VOLUME * 2,
            "bar_status": ["actual"] * 16,
        }
    )
    long = compute_alpha158(bars)
    assert list(long.columns) == list(LONG_COLUMNS)
    assert len(long) == 8 * 2 * 158
    assert sorted(long["entity_id"].unique()) == [1, 2]
    assert set(long["factor"].unique()) == set(ALPHA158_NAMES)
    # 同一日同一實體那 158 列維持官方次序。
    first_block = long.loc[
        (long["date"] == "2026-01-05") & (long["entity_id"] == 1), "factor"
    ]
    assert list(first_block.astype(str)) == list(ALPHA158_NAMES)


def test_同日同實體有兩列即拒收():
    bars = pd.DataFrame(
        {
            "date": ["2026-01-05", "2026-01-05"],
            "entity_id": [1, 1],
            "open": [10.0, 10.0],
            "high": [11.0, 11.0],
            "low": [9.0, 9.0],
            "close": [10.5, 10.5],
            "volume": [100.0, 100.0],
        }
    )
    with pytest.raises(ContractViolation):
        compute_alpha158(bars)


def test_缺欄即拒收():
    with pytest.raises(ContractViolation):
        compute_alpha158_for_entity(pd.DataFrame({"close": [1.0, 2.0]}))


@pytest.mark.skipif(
    not (STARTER_SNAPSHOT / "prices.parquet").exists(),
    reason=(
        "本機沒有起步宇宙那個快照(data/ 不入 git)。"
        "重抓:python -m karst.gateway snapshot --universe starter"
    ),
)
def test_起步宇宙十二隻算得出全部一百五十八條():
    prices = pd.read_parquet(STARTER_SNAPSHOT / "prices.parquet")
    assert prices["entity_id"].nunique() == 12

    for entity_id, group in prices.groupby("entity_id"):
        ordered = group.sort_values("date").reset_index(drop=True)
        wide = compute_alpha158_for_entity(ordered)
        assert list(wide.columns) == list(ALPHA158_NAMES)
        assert len(wide) == len(ordered)
        # 每一條在這隻股票上都要有實數值,不可以整欄留空。
        finite = np.isfinite(wide.to_numpy("float64")).sum(axis=0)
        empty = [
            name for name, count in zip(ALPHA158_NAMES, finite) if count == 0
        ]
        assert not empty, f"實體 {entity_id} 整欄算不出:{empty}"
