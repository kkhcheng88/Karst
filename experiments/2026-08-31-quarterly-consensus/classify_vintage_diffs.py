"""KARST-125: turn the raw then/now pairs into an honest verdict.

Reads out/vintage_results.json (written by verify_yahoo_estimate_vintage.py) and
classifies every comparable cell. No network access -- pure re-analysis, so the
classification rules can be revised without re-fetching anything.

Four buckets:
  unchanged          - archived estimate == today's estimate
  split-rescaled     - both estimate and actual moved by the SAME factor, so only
                       the per-share units changed (a stock split), not the forecast
  precision-degraded - today's value is so small that Yahoo's 2-decimal rounding
                       swamps the comparison. Typical of heavily split tickers:
                       NVDA's 2017 estimate is stored today as 0.03, where one
                       rounding step is +-17%. NOT evidence of anything; the cell
                       simply cannot carry a verdict (and is useless as a
                       denominator either way, which is a finding in itself).
  REWRITTEN          - the estimate moved while the actual stayed put. Since a
                       reported result is a fact and never gets re-forecast, this
                       is a genuine post-hoc change to the stored consensus.

Run: set PYTHONUTF8=1 && python classify_vintage_diffs.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

# a cell is too coarse to judge when one rounding step is a big fraction of it
ROUND_STEP = 0.005
MAX_ROUNDING_NOISE = 0.02      # 2%
SAME_TOL = 0.011


def classify(p):
    if not p.get("joined"):
        return "not-joined", None
    te, ne = p.get("then_est"), p.get("now_est")
    ta, na = p.get("then_act"), p.get("now_act")
    if te is None or ne is None:
        return "no-estimate", None
    if abs(te - ne) < SAME_TOL:
        return "unchanged", None
    # too small to judge?
    if abs(ne) > 0 and ROUND_STEP / abs(ne) > MAX_ROUNDING_NOISE:
        return "precision-degraded", None
    if ta and na and ne and na != 0 and ne != 0:
        r_est, r_act = te / ne, ta / na
        # same factor on both -> units moved, not the forecast
        if abs(r_est - r_act) <= 0.05 * abs(r_act):
            return "split-rescaled", round(r_est, 3)
        return "REWRITTEN", (te, ne, ta, na)
    return "unjudgeable-no-actual", None


def main():
    with open(os.path.join(OUT, "vintage_results.json"), encoding="utf-8") as f:
        res = json.load(f)

    tally = {}
    rewritten = []
    per_ticker = {}
    for tkr, t in res.items():
        pt = {}
        for chk in t.get("checked", []):
            for p in chk.get("pairs", []):
                verdict, extra = classify(p)
                tally[verdict] = tally.get(verdict, 0) + 1
                pt[verdict] = pt.get(verdict, 0) + 1
                if verdict == "REWRITTEN":
                    rewritten.append({
                        "ticker": tkr, "snapshot": chk["timestamp"],
                        "quarter": p["date"],
                        "est_then": p["then_est"], "est_now": p["now_est"],
                        "act_then": p["then_act"], "act_now": p["now_act"]})
        per_ticker[tkr] = pt

    print("=== overall ===")
    total = sum(tally.values())
    for k, v in sorted(tally.items(), key=lambda x: -x[1]):
        print(f"  {k:22s} {v:4d}  ({v/total*100:.1f}%)")
    print(f"  {'TOTAL':22s} {total:4d}")

    judgeable = tally.get("unchanged", 0) + tally.get("split-rescaled", 0) \
        + tally.get("REWRITTEN", 0)
    if judgeable:
        rw = tally.get("REWRITTEN", 0)
        print(f"\nOf the {judgeable} cells that CAN carry a verdict: "
              f"{judgeable - rw} intact, {rw} rewritten "
              f"({rw/judgeable*100:.1f}%)")

    print("\n=== per ticker ===")
    for t, pt in per_ticker.items():
        print(f"  {t}: {pt}")

    if rewritten:
        print("\n=== every genuinely rewritten cell ===")
        for r in rewritten:
            print(f"  {r['ticker']} {r['quarter']} (snap {r['snapshot'][:8]}): "
                  f"estimate {r['est_then']} -> {r['est_now']}   "
                  f"actual {r['act_then']} -> {r['act_now']}")

    with open(os.path.join(OUT, "vintage_verdict.json"), "w", encoding="utf-8") as f:
        json.dump({"tally": tally, "per_ticker": per_ticker,
                   "rewritten": rewritten}, f, indent=2, ensure_ascii=False)
    print("\nsaved -> out/vintage_verdict.json")


if __name__ == "__main__":
    main()
