"""Insider-buying signal -- the one Flow family that is a genuine, durable, hard-to-arbitrage edge
(Cohen "decoding insider information"; Lakonishok-Lee). A Phase-3 CORROBORATION signal: it is NOT in
the price chart (it is informed-agent behaviour), so it belongs beside the qualitative thesis, not in
the price layers.

HONEST scope (the edge is in the SUBSET, not raw flow):
- Only OPEN-MARKET PURCHASES count as buys (grants / awards / gifts / option exercises excluded).
- CLUSTER buys (>= 2 distinct insiders) and C-SUITE buys (CEO/CFO/President) are the strong form.
- SELLING is weighted much less -- insiders sell for many noisy reasons (tax, diversification); only
  buying has a single motive. So the score is asymmetric.
- It is SLOW / LAGGED (Form 4 disclosed with a few days' lag) -> a conviction/corroboration signal,
  NOT timing. Bounded so it can only nudge, never drive.

Source: yfinance `insider_transactions` (Yahoo, sourced from SEC Form 4). Cached per run.

    python thesis/insider.py MU ETN AEHR
"""
from __future__ import annotations

import contextlib
import datetime as dt
import io
import sys
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd
import yfinance as yf

_WINDOW = 180                     # look-back (days) for "recent" insider activity
_SCALE = 500_000                  # $0.5M open-market buying ~ a meaningful signal
_CSUITE = ("chief executive", "chief financial", "president")


@dataclass(frozen=True)
class InsiderSignal:
    score: float                  # -1..+1 corroboration (buying strong; selling weak/noisy)
    label: str                    # cluster-buy / buy / neutral / selling / heavy-selling / no-data
    cluster: bool                 # >= 2 distinct open-market buyers
    buyers: int                   # distinct open-market buyers in the window
    net_value: float              # buy$ - sell$ (open-market) over the window
    top_buy: str                  # biggest single open-market buy (who/role/$)
    note: str
    source: str


def _clip(x, lo, hi):
    return max(lo, min(hi, x))


@lru_cache(maxsize=256)
def insider_signal(ticker: str, window_days: int = _WINDOW) -> InsiderSignal:
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            df = yf.Ticker(ticker).insider_transactions
    except Exception:
        df = None
    if df is None or len(df) == 0 or "Text" not in getattr(df, "columns", []):
        return InsiderSignal(0.0, "no-data", False, 0, 0.0, "", "no insider data",
                             "yfinance insider_transactions")

    cutoff = pd.Timestamp(dt.date.today()) - pd.Timedelta(days=window_days)
    d = df.copy()
    d["dt"] = pd.to_datetime(d.get("Start Date"), errors="coerce")
    d = d[d["dt"] >= cutoff]
    if d.empty:
        return InsiderSignal(0.0, "neutral", False, 0, 0.0, "", f"no activity in {window_days}d",
                             "yfinance insider_transactions")

    # the transaction TYPE lives in the free-text `Text` column ("Purchase at price ...",
    # "Sale at price ...", "Stock Award(Grant) ...", "Stock Gift ..."); the `Transaction` column is blank.
    txt = d["Text"].astype(str).str.lower()
    val = pd.to_numeric(d.get("Value"), errors="coerce").fillna(0.0)
    pos = d.get("Position").astype(str)
    who = d.get("Insider").astype(str)

    is_buy = txt.str.contains("purchase at")    # open-market buy only (excludes award/grant/gift/exercise)
    is_sell = txt.str.contains("sale at")
    buys = d[is_buy]
    buy_val = float(val[is_buy].sum())
    sell_val = float(val[is_sell].sum())
    distinct_buyers = int(who[is_buy].nunique())
    cluster = distinct_buyers >= 2
    csuite_buy = bool(pos[is_buy].str.lower().apply(lambda p: any(c in p for c in _CSUITE)).any())

    # BUYING is the real edge (single motive) -> the positive score. But a token buy that is SWAMPED
    # by heavy selling is NOT a buy signal. SELLING is noisy (tax/diversification/10b5-1) -> only a
    # mild, capped negative. So: strong + needs a CLUSTER or a large un-swamped buy; sells barely bite.
    swamped = sell_val > 3 * buy_val
    buy_sig = 0.0
    if buy_val > 0 and not swamped:
        if cluster:
            buy_sig = 0.6 + 0.4 * _clip(buy_val / _SCALE, 0, 1)       # cluster buy = the strong form
        elif buy_val >= _SCALE:
            buy_sig = 0.3 + 0.4 * _clip(buy_val / _SCALE, 0, 1)       # meaningful single buy
        else:
            buy_sig = 0.2                                             # minor single buy
        if csuite_buy:
            buy_sig = min(1.0, buy_sig + 0.15)
    sell_sig = -_clip(0.35 * sell_val / (_SCALE * 40), 0, 0.35)       # $20M+ selling ~ -0.35 (noisy, capped)
    score = _clip(buy_sig + sell_sig, -1, 1)

    if score >= 0.6:
        label = "cluster-buy" if cluster else "buy"
    elif score >= 0.25:
        label = "buy"
    elif score > -0.2:
        label = "neutral"
    elif score > -0.32:
        label = "selling"
    else:
        label = "heavy-selling"

    top_buy = ""
    if not buys.empty:
        b = buys.loc[val[is_buy].idxmax()]
        top_buy = f"{who.loc[b.name]} ({pos.loc[b.name]}) ${val.loc[b.name]:,.0f}"

    asof = d["dt"].max()
    note = (f"{distinct_buyers} buyer(s), buy ${buy_val:,.0f} vs sell ${sell_val:,.0f} in {window_days}d"
            + (f"; top {top_buy}" if top_buy else "")
            + ("; CLUSTER" if cluster else "") + ("; C-suite buy" if csuite_buy else "")
            + " (Form-4 lagged, corroboration not timing)")
    return InsiderSignal(round(score, 2), label, cluster, distinct_buyers, round(buy_val - sell_val, 0),
                         top_buy, note, f"yfinance insider_transactions @ {asof.date() if pd.notna(asof) else '?'}")


if __name__ == "__main__":
    for t in (sys.argv[1:] or ["MU", "ETN", "AEHR"]):
        s = insider_signal(t)
        print(f"\n{t}: {s.label}  score={s.score}  cluster={s.cluster}  net=${s.net_value:,.0f}")
        print(f"   {s.note}")
        print(f"   source: {s.source}")
