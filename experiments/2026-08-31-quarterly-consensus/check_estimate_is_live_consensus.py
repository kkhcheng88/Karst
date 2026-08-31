"""KARST-125 supporting evidence, self-contained (no external archive needed).

Question: what IS the "EPS Estimate" that Yahoo stores against each earnings date?

Test: for every ticker, take the NEXT (not yet reported) earnings date. Its stored
EPS Estimate should equal today's live forward consensus for the current quarter
(earnings_estimate, period "0q"). If they match, then the value written against an
earnings date is the live analyst consensus for that quarter as of now -- which
means the value sitting against an ALREADY reported quarter is whatever the
consensus was at the moment that quarter stopped being "0q", i.e. the
pre-announcement consensus, PROVIDED it is never rewritten afterwards.
(The "never rewritten" half is what verify_yahoo_estimate_vintage.py tests.)

Also reports the announcement-time gap: report date vs fiscal quarter end, which
is the knowledge lag that any PIT alignment has to respect.

Run: set PYTHONUTF8=1 && python check_estimate_is_live_consensus.py
"""
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)
lines = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    lines.append(s)


def main():
    import pandas as pd
    import yfinance as yf

    rows = []
    for t in ["AAPL", "AXTI", "NVDA", "PLUG", "CROX", "MU", "ORCL", "COST"]:
        try:
            tk = yf.Ticker(t)
            ed = tk.get_earnings_dates(limit=100)
            ee = tk.earnings_estimate
            if ed is None or ee is None or ed.empty or ee.empty:
                log(f"{t}: no data"); continue

            # next unreported earnings date = the earliest FUTURE row with no
            # Reported EPS. Must filter on "in the future": old rows can also be
            # missing Reported EPS simply because Yahoo has a hole there.
            today = pd.Timestamp.utcnow().tz_localize(None)
            fut = ed[ed.index.tz_localize(None) > today]
            unrep = fut[fut["Reported EPS"].isna()]
            if unrep.empty:
                log(f"{t}: no upcoming date on record"); continue
            nxt = unrep.iloc[-1]           # oldest unreported = the next one due
            nxt_date = unrep.index[-1]
            stored = nxt["EPS Estimate"]
            live = ee.loc["0q", "avg"] if "0q" in ee.index else None
            nan = (stored != stored)
            match = (not nan and live is not None
                     and abs(float(stored) - float(live)) < 0.011)
            log(f"{t:5s} next={str(nxt_date)[:10]} stored_est={stored} "
                f"live_0q_consensus={live} MATCH={match}")
            rows.append({"ticker": t, "next_date": str(nxt_date)[:10],
                         "stored_estimate": stored, "live_0q_consensus": live,
                         "match": match})

            # knowledge lag: report date minus fiscal quarter end
            eh = tk.earnings_history
            if eh is not None and not eh.empty:
                rep = ed[ed["Reported EPS"].notna()]
                lags = []
                for q in eh.index:
                    after = rep.index[rep.index.tz_localize(None) >= pd.Timestamp(q)]
                    if len(after):
                        lags.append((after[-1].tz_localize(None) - pd.Timestamp(q)).days)
                if lags:
                    log(f"      report-date minus quarter-end (days): {sorted(lags)}")
        except Exception as e:
            log(f"{t}: FAILED {type(e).__name__}: {str(e)[:160]}")

    if rows:
        df = pd.DataFrame(rows)
        p = os.path.join(OUT, "estimate_is_live_consensus.csv")
        df.to_csv(p, index=False, encoding="utf-8")
        log("\nsaved ->", p)
        log(f"\nMATCH rate: {df['match'].sum()}/{len(df)}")


if __name__ == "__main__":
    main()
    with open(os.path.join(OUT, "estimate_is_live_consensus.txt"), "w",
              encoding="utf-8") as f:
        f.write("\n".join(lines))
