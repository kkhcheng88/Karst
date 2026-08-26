"""KARST-013:趨勢波段玩具版——共用規格與特徵計算。

考題照 D-016 骨幹設,只用價格數據,五件規則:
  1) 入場:收市價突破前 N 日最高(不含當日)
  2) 止蝕:前波段低位(過去 SWING_LB 日最低價)——一個絕對價位,不是固定百分比
  3) 賠率門檻:目標 = 入場 + 前 N 日區間高度(量度移動,即 D-016 的支持阻力擺位);
     賠率 =(目標-入場)/(入場-止蝕),低過門檻就不入場
  4) 注碼:按止蝕距離反推,令單筆風險 = 權益的 RISK_PER_TRADE,並設單一持倉市值上限
  5) 月度熔斷:組合權益由本月起點回落超過 BREAKER_DD,即停止該月餘下日子的新入場

數據沿用 KARST-009 的合成面板(500 股 x 2608 個交易日,種子 20260825),不重新發明:
見 ../2026-08-bakeoff/gen_data.py(重生指令:python gen_data.py)。

執行慣例與 KARST-009 一致:訊號在 t 日收市成形,t+1 日收市成交(無同日前視)。
止蝕/目標的百分比一律用 t+1 日收市價(即真正成交價)做分母,所以換算回絕對價位
剛好等於前波段低位本身,沒有因為「引擎只收百分比」而走樣。
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

# ---- 規格常數(兩條實作路徑必須一模一樣)----
SEED = 20260826

INIT_CASH = 1_000_000.0
RISK_PER_TRADE = 0.02      # 單筆風險 2% 權益(D-016 共用風控層)
MAX_POS_FRAC = 0.20        # 單一持倉市值上限:權益的 20%
SWING_LB = 10              # 前波段低位回望日數
BREAKER_DD = 0.06          # 月度熔斷門檻:本月回撤 6%
MIN_STOP_FRAC = 0.01       # 止蝕太貼(注碼會爆)一律不做
MAX_STOP_FRAC = 0.25       # 止蝕太遠一律不做

# 基準參數組(單次回測用)
BASE_N = 20
BASE_RR = 1.5

# 參數掃描網格:N(突破日數) x 賠率門檻 = 12 x 12 = 144 組
GRID_N = [5, 10, 15, 20, 25, 30, 40, 50, 60, 75, 90, 120]
GRID_RR = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]

HERE = os.path.dirname(os.path.abspath(__file__))
RESULT_DIR = os.path.join(HERE, "results")
PANEL_PATH = os.path.abspath(
    os.path.join(HERE, "..", "2026-08-bakeoff", "data", "panel.parquet")
)


def param_grid() -> list[dict]:
    """N x 賠率門檻,次序固定。"""
    return [{"n_break": n, "rr_min": rr} for rr in GRID_RR for n in GRID_N]


def load_wide() -> dict[str, pd.DataFrame]:
    """自家長格式面板 -> vectorbt 要的寬表(日期 x 股票)。"""
    panel = pd.read_parquet(PANEL_PATH)
    out = {}
    for field in ("open", "high", "low", "close"):
        w = panel.pivot(index="date", columns="symbol", values=field)
        w.columns.name = "symbol"
        out[field] = w.astype(np.float64)
    return out


def build_features(wide: dict[str, pd.DataFrame]) -> dict:
    """算出與 N、賠率門檻無關的部分(只做一次,掃描時重用)。"""
    close = wide["close"]
    C = close.to_numpy()
    exec_price = np.full_like(C, np.nan)
    exec_price[:-1] = C[1:]  # 訊號日 t 的成交價 = t+1 日收市

    swing_low = wide["low"].rolling(SWING_LB, min_periods=SWING_LB).min().to_numpy()

    return {
        "close": C,
        "swing_low": swing_low,     # 規則 2:前波段低位
        "exec_price": exec_price,
        "index": close.index,
        "columns": close.columns,
    }


def rolling_range(wide: dict[str, pd.DataFrame], n_break: int) -> tuple[np.ndarray, np.ndarray]:
    """前 N 日的最高與最低(皆不含當日)。只有這一件隨 N 變。"""
    ph = wide["high"].rolling(n_break, min_periods=n_break).max().shift(1).to_numpy()
    pl = wide["low"].rolling(n_break, min_periods=n_break).min().shift(1).to_numpy()
    return ph, pl


def build_signals(feat: dict, prior_high: np.ndarray, prior_low: np.ndarray,
                  rr_min: float) -> dict[str, np.ndarray]:
    """把規則 1、2、3 算成引擎吃得落的陣列。

    回傳的陣列全部已經對齊到「成交那一根」(訊號日 + 1),引擎收到就是「今日要做的事」。
    """
    C = feat["close"]
    px = feat["exec_price"]
    stop_abs = feat["swing_low"]                    # 規則 2
    tgt_abs = C + (prior_high - prior_low)          # 目標:量度移動

    with np.errstate(invalid="ignore"):
        breakout = C > prior_high                   # 規則 1
        plan_risk = C - stop_abs                    # 交易計劃在訊號日成形
        plan_reward = tgt_abs - C
        rr = plan_reward / plan_risk                # 規則 3:賠率

        stop_frac = (px - stop_abs) / px            # 換算成引擎收的百分比(分母 = 真正成交價)
        tp_frac = (tgt_abs - px) / px

        ok = (
            np.isfinite(rr)
            & np.isfinite(stop_frac)
            & np.isfinite(tp_frac)
            & (plan_risk > 0)
            & (stop_frac >= MIN_STOP_FRAC)
            & (stop_frac <= MAX_STOP_FRAC)
            & (tp_frac > 0)
            & (rr >= rr_min)
        )
        sig = breakout & ok

    T, K = C.shape
    entries = np.zeros((T, K), dtype=np.bool_)
    sl = np.full((T, K), np.nan)
    tp = np.full((T, K), np.nan)
    stop_lvl = np.full((T, K), np.nan)
    tgt_lvl = np.full((T, K), np.nan)

    entries[1:] = sig[:-1]
    sl[1:] = stop_frac[:-1]
    tp[1:] = tp_frac[:-1]
    stop_lvl[1:] = stop_abs[:-1]
    tgt_lvl[1:] = tgt_abs[:-1]

    sl = np.where(entries, sl, np.nan)
    tp = np.where(entries, tp, np.nan)
    return {
        "entries": entries,
        "sl_stop": sl,
        "tp_stop": tp,
        "stop_abs": np.where(entries, stop_lvl, np.nan),
        "tgt_abs": np.where(entries, tgt_lvl, np.nan),
        "n_signals": int(entries.sum()),
    }


def exec_price_aligned(feat: dict) -> np.ndarray:
    """成交那一根的成交價(= 該根收市價),與 build_signals 的對齊方式一致。"""
    px = np.full_like(feat["close"], np.nan)
    px[1:] = feat["exec_price"][:-1]
    return px


def month_id(index: pd.DatetimeIndex) -> np.ndarray:
    """每根 bar 屬於第幾個月,熔斷用來判斷「新一個月」。"""
    return (index.year * 12 + index.month).to_numpy().astype(np.int64)
