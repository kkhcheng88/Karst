"""Karst backtest — data layer.

Primary source : defeatbeta-api (Yahoo-backed, reliable; also exposes fundamentals
                 / earnings transcripts / news for later Tree + LLM layers).
                 Requires defeatbeta-api >= 0.0.60 (native Windows support).
Fallback       : yfinance (esp. for indices like ^VIX / ^VXN that defeatbeta's
                 equity dataset may not cover).

Note: defeatbeta prints an emoji banner on import that crashes cp950 (zh-TW)
consoles. We swallow stdout during import so the module is console-safe without
needing PYTHONUTF8.

Returns standardized daily OHLCV: DataFrame indexed by tz-naive DatetimeIndex,
columns = [open, high, low, close, volume]. Prices are RAW (not dividend-adjusted)
— the backtester handles total-return adjustment for B&H benchmarks.
"""
from __future__ import annotations

import contextlib
import io

import pandas as pd

# Swallow defeatbeta's import-time banner (emoji -> cp950 crash).
with contextlib.redirect_stdout(io.StringIO()):
    from defeatbeta_api.data.ticker import Ticker

import yfinance as yf

STD_COLS = ["open", "high", "low", "close", "volume"]


def _from_defeatbeta(symbol: str) -> pd.DataFrame | None:
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            df = Ticker(symbol).price()
        if df is None or len(df) == 0:
            return None
        df = df.rename(columns={"report_date": "date"}).copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date").sort_index()
        return df[STD_COLS].astype("float64")
    except Exception:
        return None


def _from_yfinance(symbol: str) -> pd.DataFrame | None:
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            df = yf.download(symbol, period="max", auto_adjust=False, progress=False)
        if df is None or len(df) == 0:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.rename(columns=str.lower)
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df.index.name = "date"
        return df[STD_COLS].astype("float64")
    except Exception:
        return None


def load(symbol: str, source: str = "auto", min_rows: int = 100) -> pd.DataFrame:
    """Load standardized daily OHLCV for `symbol`.

    source: "auto" (defeatbeta then yfinance), "defeatbeta", or "yfinance".
    """
    if source in ("auto", "defeatbeta"):
        df = _from_defeatbeta(symbol)
        if df is not None and len(df) >= min_rows:
            df.attrs["source"] = "defeatbeta"
            return df
        if source == "defeatbeta":
            raise RuntimeError(f"defeatbeta returned no usable data for {symbol!r}")
    df = _from_yfinance(symbol)
    if df is not None and len(df) >= min_rows:
        df.attrs["source"] = "yfinance"
        return df
    raise RuntimeError(f"no data source returned usable data for {symbol!r}")


if __name__ == "__main__":
    # Coverage probe for the 3 core ETFs + the two index-IV proxies.
    for sym in ["SPY", "QQQ", "SPMO", "^VIX", "^VXN"]:
        try:
            df = load(sym)
            print(
                f"{sym:6} {df.attrs['source']:10} rows={len(df):6} "
                f"{df.index.min().date()} -> {df.index.max().date()} "
                f"last_close={df['close'].iloc[-1]:.2f}"
            )
        except Exception as e:
            print(f"{sym:6} FAILED: {type(e).__name__}: {str(e)[:120]}")
