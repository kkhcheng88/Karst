"""Daily core-v2 playbook readout (docs/2026-07-07_core_playbook.md section 1).

Prints the daily gate decision (SPY/QQQ vs 200SMA + cross detection), VIX, SPY RSI-2,
T-bill rate, and — when option chains are reachable — the current Δ0.50 1y LEAP quote
per leg (what the playbook would buy today). Run by Task Scheduler each weekday morning
(HK time, after the US close) and appended to playbook_log.txt for the observation log.

    python backtest/playbook_readout.py
"""
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
from backtest.data import load


def wilder_rsi(close, n=2):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


# A-type crisis-rescue sleeve (Phase-3 WS2, docs/2026-07-08_phase3_ws2_crisis.md section 2 +
# backlog item #2). Mechanism, decided by real-data event study
# (backtest/results/2026-07-08_crisis_rescue.md + its 2026-07-08 addendum): ARM on ^VIX close
# first >40 (no systemic-sector filter -- the addendum found the epicenter/XLF-XLE screen adds
# no reliable value over the plain worst-2, so the live target uses L5's simpler naive-worst-2
# rule); ENTER once VIX closes back below 30. Judged off TODAY's close only -- no look-ahead.
CRISIS_ARM_VIX = 40.0
CRISIS_ENTER_VIX = 30.0
CRISIS_ARM_WINDOW_TD = 60  # trading days -- matches exp_crisis_rescue.py's DEDUP_TD
CRISIS_SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB"]  # 9 orig. SPDRs


def crisis_sleeve_line(spy_index):
    """Returns the 'CRISIS SLEEVE: ...' readout line. Never raises -- any data hiccup degrades
    to a DISARMED-with-caveat line so it can't break the rest of the readout."""
    try:
        vix = load("^VIX")["close"].reindex(spy_index).ffill(limit=3)
        vix_now = float(vix.iloc[-1])
        window = vix.tail(CRISIS_ARM_WINDOW_TD)
        breach = window[window > CRISIS_ARM_VIX]
        if breach.empty:
            return "CRISIS SLEEVE: DISARMED"
        arm_date = breach.index[0]  # earliest VIX>40 close in the trailing 60td window = this
                                    # episode's trigger date (mirrors exp_crisis_rescue's episode
                                    # definition: ARM starts at the FIRST breach, not the latest)
        arm_i = spy_index.get_loc(arm_date)
        tr63 = {}
        for s in CRISIS_SECTORS:
            px = load(s)["close"].reindex(spy_index)
            if arm_i >= 63 and not np.isnan(px.iloc[arm_i]) and not np.isnan(px.iloc[arm_i - 63]):
                tr63[s] = float(px.iloc[arm_i] / px.iloc[arm_i - 63] - 1.0)
        worst2 = sorted(tr63.items(), key=lambda kv: kv[1])[:2]
        targets = "/".join(s for s, _ in worst2) if worst2 else "N/A(insufficient sector data)"
        state = "ENTER-SIGNAL" if vix_now < CRISIS_ENTER_VIX else "ARMED"
        return f"CRISIS SLEEVE: {state}(自 {arm_date.date()}, 目標板塊={targets})"
    except Exception as e:
        return f"CRISIS SLEEVE: DISARMED (status calc failed: {type(e).__name__} -- treat as disarmed pending investigation)"


def main():
    from datetime import datetime
    print(f"==== {datetime.now():%Y-%m-%d %H:%M} ====")
    print("=== Core v2 playbook readout ===")
    legs = {}
    for sym in ["SPY", "QQQ"]:
        df = load(sym)
        c = df["close"]
        sma = c.rolling(200).mean()
        above_t = bool(c.iloc[-1] > sma.iloc[-1])
        above_y = bool(c.iloc[-2] > sma.iloc[-2])
        cross = "FRESH-CROSS -> T+1 ACTION!" if above_t != above_y else "no-change"
        legs[sym] = dict(px=float(c.iloc[-1]))
        print(f"{sym}: close({c.index[-1].date()})={c.iloc[-1]:.2f}  200SMA={sma.iloc[-1]:.2f}  "
              f"{'ABOVE' if above_t else 'BELOW'} ({(c.iloc[-1]/sma.iloc[-1]-1)*100:+.1f}%)  {cross}")
    spy = load("SPY")["close"]
    rsi2 = float(wilder_rsi(spy).iloc[-1])
    vix = float(load("^VIX")["close"].iloc[-1])
    irx = float(load("^IRX")["close"].iloc[-1])
    m1 = "OPEN(牛+VIX>28)" if vix > 28 else "closed"
    m3 = "TRIGGER(RSI-2>90)" if rsi2 > 90 else "off"
    print(f"VIX={vix:.2f} (M1 panic window: {m1})  SPY RSI-2={rsi2:.1f} (M3 sell-call: {m3})  ^IRX={irx:.2f}%")
    print(crisis_sleeve_line(spy.index))

    # Optional: current delta-0.50 1y LEAP quote per leg (graceful if chain unreachable)
    try:
        import yfinance as yf
        from scipy.stats import norm
        r = irx / 100.0
        for sym in ["SPY", "QQQ"]:
            tk = yf.Ticker(sym)
            S = legs[sym]["px"]
            divs = tk.dividends
            q = float(divs[divs.index > (divs.index.max() - pd.Timedelta(days=365))].sum()) / S if len(divs) else 0.0
            exps = pd.to_datetime(tk.options)
            dte = (exps - pd.Timestamp.now().normalize()).days
            ok = [(e, d) for e, d in zip(tk.options, dte) if 330 <= d <= 420] or \
                 [(e, d) for e, d in zip(tk.options, dte) if d > 300][:1]
            exp, days = min(ok, key=lambda x: abs(x[1] - 365))
            T = days / 365.0
            calls = tk.option_chain(exp).calls
            calls = calls[(calls["impliedVolatility"] > 0.01) & (calls["strike"] > S * 0.4)].copy()
            # After-hours chain snapshots often carry stale/near-zero IVs which wreck the
            # delta-based strike pick. Floor sigma at 12% for SELECTION ONLY (a valid 1y
            # index IV ~18-30% is untouched); warn when the chain looks stale.
            stale = float((calls["impliedVolatility"] < 0.05).mean())
            sig = calls["impliedVolatility"].clip(lower=0.12)
            d1 = (np.log(S / calls["strike"]) + (r - q + 0.5 * sig ** 2) * T) / (sig * np.sqrt(T))
            calls["delta"] = np.exp(-q * T) * norm.cdf(d1)
            if stale > 0.5:
                print(f"({sym}: {stale*100:.0f}% of chain IVs look stale — after-hours snapshot; "
                      f"strike pick uses floored vol, re-check quotes intraday)")
            row = calls.iloc[(calls["delta"] - 0.50).abs().argsort()].iloc[0]
            mid = (row["bid"] + row["ask"]) / 2 if row["bid"] > 0 else row["lastPrice"]
            print(f"{sym} leg quote: {exp} ({days}d) K={row['strike']:.0f} delta={row['delta']:.2f} "
                  f"mid={mid:.2f} (1 contract = ${mid*100:,.0f})")
    except Exception as e:
        print(f"(option-chain quote unavailable: {type(e).__name__} — gate readings above are unaffected)")


if __name__ == "__main__":
    main()
