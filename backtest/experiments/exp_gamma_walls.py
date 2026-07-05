"""GAMMA WALLS — live 支持/阻力「區」+ 強度 + 企穩線(gamma flip),街坊投資者版。
SPY/QQQ 詳細睇 0DTE / 1週 / 1月;板塊/Mag7 compact(可信度較低)。強度 = 該 strike 佔嗰邊 gamma 幾多 %
(佔得愈多 = 牆愈實)。LIVE snapshot(yfinance 免費;無歷史→自己回測唔到;理論+研究撐,見
docs/2026-07-05_gamma_walls.md)。

  支持=put wall · 阻力=call wall · 磁鐵=最大總 gamma strike · 企穩線=gamma flip(🟢之上釘住/🔴之下脆弱)。
  強度 [████░ 21%]:該 strike 佔嗰邊 gamma 21%;>15%=強、8-15%=中、<8%=弱(牆愈弱愈易穿)。

    python backtest/experiments/exp_gamma_walls.py
"""
import math

import numpy as np
import pandas as pd

R = 0.04
DETAIL = ["SPY", "QQQ"]
COMPACT = [
    ("板塊ETF", ["XLK", "XLF", "XLE", "XLV", "XLP", "XLU", "XLI", "XLB", "XLY", "XLC", "XLRE"]),
    ("Mag7 (個股 sign 易破,只作參考,財報避)", ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]),
]


def bs_gamma(S, K, T, sig):
    if T <= 0 or sig <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = (math.log(S / K) + (R + 0.5 * sig * sig) * T) / (sig * math.sqrt(T))
    return math.exp(-d1 * d1 / 2) / math.sqrt(2 * math.pi) / (S * sig * math.sqrt(T))


def sides(calls, puts, S, T):
    cg, pg = {}, {}
    for df, d in [(calls, cg), (puts, pg)]:
        for K, oi, iv in zip(df["strike"], df["openInterest"], df["impliedVolatility"]):
            if K > 0 and oi and oi > 0 and iv and iv > 0:
                d[K] = d.get(K, 0.0) + bs_gamma(S, K, T, iv) * oi * 100 * S * S * 0.01
    return (pd.Series(cg).sort_index() if cg else pd.Series(dtype=float),
            pd.Series(pg).sort_index() if pg else pd.Series(dtype=float))


def walls(calls, puts, S, T):
    """each wall -> (strike, pct-of-that-side-gamma, $magnitude-per-1%)."""
    cg, pg = sides(calls, puts, S, T)

    def wk(series, side_total):
        if not len(series) or series.max() <= 0:
            return (float("nan"), 0.0, 0.0)
        return (float(series.idxmax()), float(series.max() / side_total * 100) if side_total else 0.0, float(series.max()))
    pw = wk(pg[pg.index <= S], pg.sum()); cw = wk(cg[cg.index >= S], cg.sum())
    tot = cg.add(pg, fill_value=0)
    pin = (float(tot.idxmax()), float(tot.max() / tot.sum() * 100), float(tot.max())) if len(tot) and tot.sum() else (float("nan"), 0.0, 0.0)
    return pw, cw, pin


def flip_level(opts, S):
    grid = np.linspace(0.85 * S, 1.15 * S, 61)
    tot = np.array([sum(sign * bs_gamma(Sp, K, T, iv) * oi * 100 for (K, oi, iv, T, sign) in opts) for Sp in grid])
    for i in range(len(grid) - 1):
        if (tot[i] < 0 <= tot[i + 1]) or (tot[i] > 0 >= tot[i + 1]):
            den = tot[i] - tot[i + 1]
            return grid[i] + (tot[i] / den if den else 0) * (grid[i + 1] - grid[i])
    return float("nan")


def fetch(tk, yf):
    t = yf.Ticker(tk)
    try:
        S = float(t.fast_info["lastPrice"])
    except Exception:
        S = float(t.history(period="1d")["Close"].iloc[-1])
    exps = list(t.options)
    if not exps:
        return None
    today = pd.Timestamp.today().normalize()
    dted = [(e, (pd.Timestamp(e) - today).days) for e in exps if (pd.Timestamp(e) - today).days >= 0]
    chains, all_opts = {}, []
    for e, d in dted:
        if d > 45:
            continue
        try:
            oc = t.option_chain(e); T = max(d, 0.4) / 365
            chains[e] = (oc.calls, oc.puts, d)
            for df, sign in [(oc.calls, 1.0), (oc.puts, -1.0)]:
                for K, oi, iv in zip(df["strike"], df["openInterest"], df["impliedVolatility"]):
                    if K > 0 and oi and oi > 0 and iv and iv > 0:
                        all_opts.append((K, oi, iv, T, sign))
        except Exception:
            pass
    return S, flip_level(all_opts, S), dted, chains


def pick(dted, lo, hi):
    c = [e for e, d in dted if lo <= d <= hi]
    return c[0] if c else (min(dted, key=lambda x: abs(x[1] - (lo + hi) / 2))[0] if dted else None)


def zone(x, S):
    if x != x:
        return "—"
    b = max(1, round(0.003 * S))
    return f"{x - b:.0f}-{x + b:.0f}"


def bar(pct):
    n = min(5, max(0, round(pct / 5)))
    lab = "強" if pct >= 15 else ("中" if pct >= 8 else "弱")
    return f"[{'█'*n}{'░'*(5-n)} {pct:.0f}% {lab}]"


def run():
    import yfinance as yf
    print("========== 大盤指數(tier-1,最可信)==========")
    for tk in DETAIL:
        r = fetch(tk, yf)
        if not r:
            print(f"{tk}: 無期權"); continue
        S, flip, dted, chains = r
        above = bool(S > flip) if flip == flip else None
        reg = (f"🟢 現價【喺企穩線之上】= 釘住區(正gamma):支持/阻力較實,傾向區間內上落;跌穿企穩線 {flip:.0f} 先變脆弱" if above is True
               else f"🔴 現價【喺企穩線之下】= 脆弱區(負gamma):跌穿支持易【急跌加速】唔係反彈;升返上企穩線 {flip:.0f} 先算轉穩" if above is False
               else "企穩線計唔到")
        print(f"\n▶ {tk}  現價 {S:.1f}   企穩線(gamma flip)= {flip:.1f}")
        print(f"   {reg}")
        for lbl, lo, hi in [("今日0DTE", 0, 1), ("本週1W", 4, 10), ("本月1M", 20, 40)]:
            e = pick(dted, lo, hi)
            if e is None or e not in chains:
                print(f"   {lbl}: —"); continue
            c, p, d = chains[e]
            pw, cw, pin = walls(c, p, S, max(d, 0.4) / 365)
            print(f"   {lbl}({d}d)  支持 {zone(pw[0],S):>9} {bar(pw[1])}   阻力 {zone(cw[0],S):>9} {bar(cw[1])}   磁鐵 {pin[0]:.0f}")

    for grp, tks in COMPACT:
        print(f"\n========== {grp} ==========")
        print(f"{'tk':<7}{'現價':>7}{'企穩線':>7}{'狀態':>7}   本月 支持[強度] / 阻力[強度]")
        for tk in tks:
            r = fetch(tk, yf)
            if not r:
                print(f"{tk:<7} 無期權"); continue
            S, flip, dted, chains = r
            st = "釘🟢" if (flip == flip and S > flip) else ("脆🔴" if flip == flip else "—")
            e = pick(dted, 20, 40)
            cell = "—"
            if e and e in chains:
                c, p, d = chains[e]
                pw, cw, _ = walls(c, p, S, max(d, 0.4) / 365)
                cell = f"{zone(pw[0],S)}{bar(pw[1])} / {zone(cw[0],S)}{bar(cw[1])}"
            fl = f"{flip:.1f}" if flip == flip else "—"
            print(f"{tk:<7}{S:>7.1f}{fl:>7}{st:>7}   {cell}")

    print("\n讀法:強度 [████ 21% 強]=該 strike 佔嗰邊 gamma 21%,佔愈多牆愈實、愈難穿;弱牆易穿。"
          "\n企穩線🟢之上=牆較實(區間上落);🔴之下=跌穿支持會急跌(唔好當地板)。磁鐵=價易被吸過去(月度到期尤甚)。"
          "\nLIVE 快照無歷史回測;個股 Mag7 sign 易破、財報避;SPY/QQQ 0DTE 係開市/多日結構圖。")


if __name__ == "__main__":
    run()
