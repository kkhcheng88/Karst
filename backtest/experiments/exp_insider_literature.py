"""Insider — LITERATURE-ALIGNED test (fair test of the documented edge).

The rigor tests ran the WRONG cut (large-cap / short-horizon / vs-SPY). The literature
(Lakonishok-Lee 2001; Cohen-Malloy-Pomorski 2012; Seyhun) documents the edge as:
SMALL/MICRO caps · 6-12 MONTH hold · diversified PORTFOLIO · size-matched benchmark ·
opportunistic/cluster. This tests that cut on 2006-2025 events (cached).

  PART 1  small-cap events, 126d & 252d, EXCESS vs IWM (size-matched) AND vs SPY (contrast)
  PART 2  PORTFOLIO (monthly cohort) mean/hit/Sharpe, small caps, 126/252d, vs IWM
  PART 3  cost sensitivity (0.5/1/2% round-trip)
  PART 4  survivorship note (matured fraction)

Caveat still open: no opportunistic-vs-routine filter (needs per-insider history — build_events
discards owner IDs); survivorship not point-in-time (delisted micro names may drop → inflation).

    python backtest/experiments/exp_insider_literature.py
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exp_insider_validate as IV       # noqa: E402
import exp_insider_mktcap as MC         # noqa: E402

HORS = [126, 252]


def stat(x):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) < 15:
        return f"{'n<15':>18}"
    t = x.mean() / (x.std() / np.sqrt(len(x)))
    return f"{x.mean()*100:>+6.1f}/{np.median(x)*100:>+6.1f}/{t:>4.1f}[{len(x):>4}]"


def run():
    ev = IV.build_events(IV._quarters("2006q1", "2025q2"))
    IV._batch_prices(ev["ticker"].tolist() + ["IWM", "IJR"])
    MC._batch_mcap(ev["ticker"].tolist())
    spy, iwm = IV._px("SPY"), IV._px("IWM")
    rows = []
    for _, e in ev.iterrows():
        s = IV._px(e["ticker"])
        if s is None:
            continue
        mc = MC._MCAP.get(e["ticker"])
        rec = {"date": e["date"],
               "mcap": mc.asof(pd.Timestamp(e["date"])) if mc is not None else np.nan}
        for h in HORS:
            r = IV._fwd(s, e["date"], h)
            rec[f"iwm{h}"] = (r - IV._fwd(iwm, e["date"], h)) if (r is not None and IV._fwd(iwm, e["date"], h) is not None) else np.nan
            rec[f"spy{h}"] = (r - IV._fwd(spy, e["date"], h)) if (r is not None and IV._fwd(spy, e["date"], h) is not None) else np.nan
        rows.append(rec)
    df = pd.DataFrame(rows)
    have = df.dropna(subset=["mcap"])
    micro = have[have.mcap < 3e8]
    small = have[(have.mcap >= 3e8) & (have.mcap < 2e9)]
    smcap = have[have.mcap < 2e9]

    print(f"\n事件 {len(df)} | 有市值 {len(have)} | micro {len(micro)} small {len(small)} 合<$2B {len(smcap)}")
    print("\n=== PART 1 — 小型股 forward EXCESS,平均%/中位%/t[n] ===")
    for h in HORS:
        print(f"\n  {h}日:            {'vs IWM(size-matched)':>26}{'vs SPY(對照)':>22}")
        for lbl, g in [("micro <$300M", micro), ("small $300M-2B", small), ("合併 <$2B", smcap)]:
            print(f"  {lbl:<16}{stat(g[f'iwm{h}']):>22}{stat(g[f'spy{h}']):>22}")

    print("\n=== PART 2 — 組合(月度 cohort,<$2B 小型股,excess vs IWM)===")
    for h in HORS:
        d = smcap.dropna(subset=[f"iwm{h}"]).copy()
        d["m"] = d["date"].values.astype("datetime64[M]")
        m = d.groupby("m")[f"iwm{h}"].mean().dropna()
        if len(m) < 12:
            continue
        hpy = {126: 2, 252: 1}[h]
        sh = (m.mean() / m.std()) * np.sqrt(hpy) if m.std() else 0
        print(f"  {h}日: {len(m)} 個月 cohort | 平均 excess {m.mean()*100:>+5.1f}% | "
              f"hit {(m > 0).mean()*100:>3.0f}% | Sharpe(ann) {sh:>4.2f}")

    print("\n=== PART 3 — 成本敏感度(<$2B, 252日, 淨 excess vs IWM)===")
    x = smcap["iwm252"].dropna()
    for c in [0.005, 0.010, 0.020]:
        net = x - c
        print(f"  round-trip {c*100:>3.1f}%: 淨平均 {net.mean()*100:>+5.1f}%  正事件 {(net > 0).mean()*100:.0f}%")

    print("\n=== PART 4 — survivorship ===")
    tot = len(df[df.mcap < 2e9]) if "mcap" in df else 0
    mat = smcap["iwm252"].notna().sum()
    print(f"  <$2B 事件 {len(smcap)},當中 252日成熟(有 forward)= {mat} ({mat/max(len(smcap),1)*100:.0f}%)")
    print("  未成熟 = 太近期 OR 退市;退市名跌出 = survivorship 上偏(真實 edge 應更低)。")
    print("\nREAD: 若小型股組合 vs IWM 252日仍顯著正 + Sharpe>0 + 捱得住成本 -> 文獻 edge 喺我哋 data 成立;"
          " 若 vs IWM 縮到唔顯著 -> 之前 vs-SPY 個 +20% 主要係 size premium + survivorship 假象。")


if __name__ == "__main__":
    run()
