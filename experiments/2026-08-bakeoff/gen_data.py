"""KARST-009:產生可重現的合成日線面板(500 股 x 10 年)。

不依賴任何外部 API。固定種子,同一部機重跑必得同一份資料。
輸出:data/panel.parquet,長格式 (date, symbol, open, high, low, close, volume, factor)。

因子設計:每隻股票有一條慢變的潛在「質素」q(AR(1)),明日報酬 = mu + beta*q_today + 雜訊,
而可觀察的 factor = q + 觀察雜訊。即因子對「下一日起的報酬」有真實預測力,
但不是完美——這樣「選頭 N 名」才會有意義的分散,參數掃描才會有形狀。
"""

from __future__ import annotations

import hashlib
import os

import numpy as np
import pandas as pd

import karst_spec as spec


def main() -> None:
    os.makedirs(spec.DATA_DIR, exist_ok=True)
    rng = np.random.default_rng(spec.SEED)

    dates = spec.trading_days()
    T = len(dates)
    K = spec.N_SYMBOLS

    # --- 潛在質素 q:AR(1),半衰期約 60 個交易日 ---
    phi = 0.98
    q = np.zeros((T, K), dtype=np.float64)
    q[0] = rng.standard_normal(K)
    shocks = rng.standard_normal((T, K)) * np.sqrt(1.0 - phi**2)
    for t in range(1, T):
        q[t] = phi * q[t - 1] + shocks[t]

    # --- 報酬:今日收市看得到的 q,驅動下一日的報酬(無前視) ---
    mu = 0.0003
    beta = 0.00012
    sigma = 0.016
    idio = rng.standard_normal((T, K)) * sigma
    market = (rng.standard_normal((T, 1)) * 0.008).repeat(K, axis=1)

    rets = np.zeros((T, K), dtype=np.float64)
    rets[1:] = mu + beta * q[:-1] + idio[1:] + market[1:]

    base_price = 20.0 * np.exp(rng.standard_normal(K) * 0.5)
    close = base_price * np.exp(np.cumsum(rets, axis=0))

    # --- 由收市價造出 OHLCV(PyBroker 需要完整 OHLCV 欄位)---
    prev_close = np.vstack([close[:1], close[:-1]])
    open_ = prev_close * (1.0 + rng.standard_normal((T, K)) * 0.003)
    hi_pad = np.abs(rng.standard_normal((T, K))) * 0.004
    lo_pad = np.abs(rng.standard_normal((T, K))) * 0.004
    high = np.maximum(open_, close) * (1.0 + hi_pad)
    low = np.minimum(open_, close) * (1.0 - lo_pad)
    volume = np.round(np.exp(11.0 + rng.standard_normal((T, K)) * 0.6))

    # --- 可觀察因子:q 加觀察雜訊 ---
    factor = q + rng.standard_normal((T, K)) * 0.8

    symbols = np.array(spec.SYMBOLS)
    panel = pd.DataFrame(
        {
            "date": np.repeat(dates.to_numpy(), K),
            "symbol": np.tile(symbols, T),
            "open": open_.reshape(-1),
            "high": high.reshape(-1),
            "low": low.reshape(-1),
            "close": close.reshape(-1),
            "volume": volume.reshape(-1),
            "factor": factor.reshape(-1),
        }
    )
    panel["symbol"] = panel["symbol"].astype("string")
    panel = panel.sort_values(["date", "symbol"], kind="stable").reset_index(drop=True)
    panel.to_parquet(spec.PANEL_PATH, index=False)

    digest = hashlib.sha256(
        np.ascontiguousarray(panel["close"].to_numpy(dtype=np.float64)).tobytes()
    ).hexdigest()[:16]

    print(f"寫出 {spec.PANEL_PATH}")
    print(f"列數={len(panel)} 股票數={K} 交易日={T} 日期={dates[0].date()}..{dates[-1].date()}")
    print(f"檔案大小={os.path.getsize(spec.PANEL_PATH) / 1e6:.1f} MB")
    print(f"close 欄位 sha256[:16]={digest}")
    print(f"換倉日數(每月)={len(spec.rebalance_dates(dates, 1))}")


if __name__ == "__main__":
    main()
