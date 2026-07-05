"""Mean-reversion family, increment C — the NO-NEWS filter (user agreed most important; principled
reason it's RSI-2 first: RSI-2 is the only PURE-PRICE, information-blind signal — it can't tell a
panic dip (bounces) from an earnings-driven collapse (drifts). F&G bakes fear-extremity in; an insider
buy IS the information.)

Test: individual liquid stocks, RSI-2 trades (entry RSI2<{20,15,10,5} × exit RSI2>{75,80,85,90}).
Split each ENTRY by whether an EARNINGS announcement sits in [-3,+1] trading days around it:
  NO-NEWS   entry  = no earnings within [-5,+2]  (oversold NOT caused by news -> should bounce)
  EARNINGS  entry  = earnings within [-3,+1]     (oversold caused by news -> should drift/keep falling)
Per entry×exit, per group: per-trade% / win% / hold[n] / 部署效率%/yr. Increment = NO-NEWS minus
EARNINGS (does dropping earnings-window entries improve RSI-2?). Split large(>$10B) vs small/mid.

Earnings dates: defeatbeta earning_call_transcripts() (~ announcement), cached to earnings_dates.pkl.
Universe: top ~250 by market cap from the shared cache (liquid, tradeable). 2016+, 2bp/trade round-trip.

    python backtest/experiments/exp_rsi2_news_filter.py
"""
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from signals import rsi  # noqa: E402

_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".insider_data")
_ECACHE = os.path.join(_DATA, "earnings_dates.pkl")
ENTRIES = [20, 15, 10, 5]
EXITS = [75, 80, 85, 90]
RT = 0.0002
START = pd.Timestamp("2016-01-01")
NTOP = 250
PRE, POST = 3, 1          # earnings-adjacent window around entry
CLR_PRE, CLR_POST = 5, 2  # no-news clearance window


def earnings_dates(tk):
    try:
        from defeatbeta_api.data.ticker import Ticker
        d = Ticker(tk).earning_call_transcripts().get_transcripts_list()
        return sorted(pd.to_datetime(d["report_date"], errors="coerce").dropna().dt.normalize().unique())
    except Exception:
        return []


def load_earnings(tickers):
    cache = {}
    if os.path.exists(_ECACHE):
        try:
            cache = pickle.load(open(_ECACHE, "rb"))
        except Exception:
            cache = {}
    need = [t for t in tickers if t not in cache]
    for i, t in enumerate(need):
        cache[t] = earnings_dates(t)
        if i % 25 == 24:
            pickle.dump(cache, open(_ECACHE, "wb"))
            print(f"  [earnings] fetched {i+1}/{len(need)}")
    if need:
        pickle.dump(cache, open(_ECACHE, "wb"))
    return cache


def _trades(s, r2, E, X):
    n = len(s); pos = np.zeros(n); inp = False
    for i in range(n):
        if not inp and r2[i] < E:
            inp = True
        elif inp and r2[i] > X:
            inp = False
        pos[i] = 1.0 if inp else 0.0
    pos = pd.Series(pos, index=s.index).shift(1).fillna(0).values
    p = s.values; out = []; e = None
    for i in range(1, n):
        if pos[i] > 0 and pos[i - 1] == 0:
            e = i
        elif pos[i] == 0 and pos[i - 1] > 0 and e is not None:
            out.append((p[i] / p[e] - 1 - RT, i - e, e)); e = None
    return out


def _near(entry_date, edates, pre, post):
    for ed in edates:
        d = (entry_date - ed).days
        if -post <= d <= pre:   # earnings within [entry-pre, entry+post]
            return True
    return False


def _print_group(label, pool, key):
    print(f"\n----- {label} -----")
    print(f"{'ent\\exit':<8}" + "".join(f"{'>'+str(x):>19}" for x in EXITS))
    for E in ENTRIES:
        row = f"<{E:<7}"
        for X in EXITS:
            tr = pool.get((key, E, X), [])
            if len(tr) < 20:
                row += f"{'n<20':>19}"; continue
            r = np.array([a for a, _ in tr]); h = np.array([b for _, b in tr])
            eff = (r.mean() / max(h.mean(), 1)) * 252 * 100
            row += f"{r.mean()*100:>+5.1f}/{(r>0).mean()*100:>3.0f}/{h.mean():>2.0f}[{len(tr):>4}]{eff:>+5.0f}%".rjust(19)
        print(row)


def run():
    px = pickle.load(open(os.path.join(_DATA, "px_defeatbeta.pkl"), "rb"))
    mc = pickle.load(open(os.path.join(_DATA, "mktcap_defeatbeta.pkl"), "rb"))
    cand = [(t, mc[t].dropna().iloc[-1]) for t in px
            if isinstance(px.get(t), pd.Series) and mc.get(t) is not None
            and len(px[t]) > 400 and len(mc[t].dropna()) > 0]
    cand.sort(key=lambda x: -x[1])
    large = [t for t, c in cand if c >= 1e10][:150]
    smid = [t for t, c in cand if 3e8 <= c < 1e10][:300]   # span caps so small/mid populates
    top = large + smid
    print(f"[news-filter] universe {len(large)} large + {len(smid)} small/mid; fetching earnings dates ...")
    ed_all = load_earnings(top)

    pool = {}   # (grp+news, E, X) -> [(ret, hold)]
    kept = 0
    for t in top:
        s = px[t]; s = s[~s.index.duplicated()].sort_index()
        s = s[s.index >= START]
        if len(s) < 260:
            continue
        edates = [d for d in ed_all.get(t, []) if d >= START]
        if not edates:
            continue
        kept += 1
        cap = mc[t].dropna().iloc[-1]
        grp = "large>$10B" if cap >= 1e10 else "small/mid<$10B"
        r2 = rsi(s, 2).values
        for E in ENTRIES:
            for X in EXITS:
                for ret, hold, ei in _trades(s, r2, E, X):
                    ed_flag = "NEWS" if _near(s.index[ei], edates, PRE, POST) else (
                        "NONEWS" if not _near(s.index[ei], edates, CLR_PRE, CLR_POST) else "MID")
                    if ed_flag == "MID":
                        continue
                    pool.setdefault((f"{grp}|{ed_flag}", E, X), []).append((ret, hold))
    print(f"[news-filter] {kept} stocks with earnings dates; per-cell 每筆%/勝%/持有d[n] 部署效率%/yr")

    for grp in ["large>$10B", "small/mid<$10B"]:
        print(f"\n========== {grp} ==========")
        _print_group(f"{grp}  NO-NEWS 入場(避開財報)", pool, f"{grp}|NONEWS")
        _print_group(f"{grp}  EARNINGS 入場(財報窗內)", pool, f"{grp}|NEWS")

    print("\nREAD: 增量 = NO-NEWS 減 EARNINGS。若 NO-NEWS 每筆%/勝%/效率 明顯高過 EARNINGS,"
          "\n即『避開財報窗嘅超賣入場』改善 RSI-2(消息跌 drift、無消息跌先 revert)。SURVIVORSHIP 偏高睇相對。")


if __name__ == "__main__":
    run()
