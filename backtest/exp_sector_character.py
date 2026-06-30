"""2b — sector character: is the right play buy-dip-HOLD (trend) or sell-the-bounce (chop)?

The user's hypothesis: some sectors (tech-linked) are persistent uptrends -> ride the dip;
others (consumer/health/...) are range-bound -> mean-revert. We do NOT hardcode that map --
we MEASURE it, per the project's iron rule, across the full (multi-regime) history with
total-return prices, and check it out-of-sample.

Per sector, on TOTAL-RETURN (adjusted) closes:
  character : %>200SMA, B&H MaxDD, Kaufman trend-efficiency
  3 variants (look-ahead-safe via engine.backtest):
    HOLD   : enter RSI2<10 & >200SMA ; exit when close<200SMA      (trend-follow / let-it-run)
    BOUNCE : enter RSI2<10 & >200SMA ; exit RSI2>70                (gated mean-revert)
    MR     : enter RSI2<10 (no gate) ; exit RSI2>70                (pure mean-revert)
  vs B&H. Tag = TREND if HOLD wins, CHOP if BOUNCE/MR wins; beats_bh + IS/OOS stability +
  deflated Sharpe (Bailey/LdP) over ALL trials so we don't fool ourselves with 33 variants.

Run: python backtest/exp_sector_character.py
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import load
from engine import backtest, buy_hold
from metrics import ann_sharpe, cagr, deflated_sharpe_ratio, max_drawdown
from signals import rsi, sma

SPDR = [("XLK", "Tech"), ("XLC", "Comm"), ("XLY", "Discr"), ("XLI", "Indus"), ("XLF", "Fin"),
        ("XLB", "Materl"), ("XLE", "Energy"), ("XLV", "Health"), ("XLP", "Staples"),
        ("XLU", "Util"), ("XLRE", "RealEst")]
OOS = 756       # last ~3y held out
COST_BPS = 2.0


def trend_efficiency(close, win=20):
    c = np.asarray(close, float)
    er = []
    for i in range(win, len(c)):
        path = np.sum(np.abs(np.diff(c[i - win:i + 1])))
        if path > 0:
            er.append(abs(c[i] - c[i - win]) / path)
    return float(np.mean(er)) if er else np.nan


def variant_returns(close, entry, exit):
    pos, strat, equity = backtest(close, entry, exit, cost_bps=COST_BPS)
    return pos, strat, equity


def metr(strat, equity, pos=None):
    d = {"CAGR": cagr(equity), "Sharpe": ann_sharpe(strat), "MaxDD": max_drawdown(equity)}
    if pos is not None:
        d["Exp"] = float(np.asarray(pos).mean())
        d["Trades"] = int(np.sum(np.diff(np.asarray(pos)) > 0))
    return d


def run():
    results = []
    all_sharpes = []   # the multiple-testing universe (every variant, every sector)

    for etf, name in SPDR:
        try:
            df = load(etf, adjusted=True, min_rows=300)
        except Exception as e:
            print(f"{etf:5} SKIP: {str(e)[:50]}")
            continue
        c = df["close"]
        r2 = rsi(c, 2)
        s200 = sma(c, 200)
        close = c.to_numpy()
        up = (c > s200).to_numpy()
        dip = (r2 < 10).to_numpy()
        ob = (r2 > 70).to_numpy()

        variants = {
            "HOLD":   (dip & up,      ~up),     # trend-follow: exit when trend breaks
            "BOUNCE": (dip & up,      ob),       # gated mean-revert
            "MR":     (dip,           ob),       # pure mean-revert
        }
        v_full, v_is, v_oos, strat_of = {}, {}, {}, {}
        n = len(close)
        cut = max(n - OOS, n // 2)
        bh_ret, bh_eq = buy_hold(close)
        bh = {"CAGR": cagr(bh_eq), "Sharpe": ann_sharpe(bh_ret), "MaxDD": max_drawdown(bh_eq)}

        for k, (en, ex) in variants.items():
            pos, strat, equity = variant_returns(close, en, ex)
            v_full[k] = metr(strat, equity, pos)
            strat_of[k] = strat
            all_sharpes.append(v_full[k]["Sharpe"])
            # IS / OOS
            v_is[k] = ann_sharpe(strat[:cut])
            v_oos[k] = ann_sharpe(strat[cut:])

        # character
        mask = s200.notna().to_numpy()
        pct_above = float((close[mask] > s200.to_numpy()[mask]).mean())
        te = trend_efficiency(close)

        # winner by full-period Sharpe
        winner = max(v_full, key=lambda k: (v_full[k]["Sharpe"] if v_full[k]["Sharpe"] == v_full[k]["Sharpe"] else -9))
        tag = "TREND" if winner == "HOLD" else "CHOP"
        beats_bh = v_full[winner]["Sharpe"] > bh["Sharpe"]
        is_winner = max(v_is, key=lambda k: (v_is[k] if v_is[k] == v_is[k] else -9))
        oos_winner = max(v_oos, key=lambda k: (v_oos[k] if v_oos[k] == v_oos[k] else -9))
        stable = (is_winner == oos_winner)

        results.append({"etf": etf, "name": name, "start": str(df.index[0].date()), "n": n,
                        "pct_above": pct_above, "te": te, "bh": bh, "v": v_full, "strat": strat_of,
                        "winner": winner, "tag": tag, "beats_bh": beats_bh,
                        "is_winner": is_winner, "oos_winner": oos_winner, "stable": stable})

    # deflated Sharpe for each sector's winner against the full trial universe
    print(f"\n=== 2b SECTOR CHARACTER (total-return, cost {COST_BPS}bp, OOS={OOS}d) ===")
    print(f"trial universe = {len(all_sharpes)} variant-Sharpes (for deflated SR)\n")
    hdr = f"{'sec':12}{'%>200':>6}{'TE':>5} | {'HOLD':>6}{'BNCE':>6}{'MR':>6}{'B&H':>6} | {'win':6}{'tag':6}{'>BH':>4}{'stable':>7}{'DSR':>6}"
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        sh = {k: r["v"][k]["Sharpe"] for k in r["v"]}
        dsr = deflated_sharpe_ratio(r["strat"][r["winner"]], all_sharpes)
        print(f"{r['name']:12}{r['pct_above']*100:5.0f}%{r['te']:5.2f} | "
              f"{sh['HOLD']:6.2f}{sh['BOUNCE']:6.2f}{sh['MR']:6.2f}{r['bh']['Sharpe']:6.2f} | "
              f"{r['winner']:6}{r['tag']:6}{'Y' if r['beats_bh'] else 'n':>4}"
              f"{('Y' if r['stable'] else 'NO'):>7}{dsr:6.2f}")

    print("\nCAGR / MaxDD (winner vs B&H):")
    for r in results:
        w = r["v"][r["winner"]]
        print(f"  {r['name']:10} {r['winner']:6} CAGR {w['CAGR']*100:6.1f}% MaxDD {w['MaxDD']*100:6.1f}% Exp {w['Exp']*100:3.0f}% Tr {w['Trades']:3d}"
              f"   | B&H CAGR {r['bh']['CAGR']*100:6.1f}% MaxDD {r['bh']['MaxDD']*100:6.1f}%   ({r['start']}, {r['n']}d)")

    n_trend = sum(1 for r in results if r["tag"] == "TREND")
    n_beat = sum(1 for r in results if r["beats_bh"])
    n_stable = sum(1 for r in results if r["stable"])
    print(f"\nTAGS: {n_trend}/{len(results)} TREND, {len(results)-n_trend} CHOP | "
          f"{n_beat}/{len(results)} winner beats B&H (Sharpe) | {n_stable}/{len(results)} IS/OOS-stable")
    print("Read: only trust a tag that BEATS B&H, is IS/OOS-STABLE, and survives DSR. "
          "Otherwise the sector's right play is just hold (timing adds nothing).")


if __name__ == "__main__":
    run()
