"""Backfill outcome{} for matured track_record.jsonl rows (Phase-3 WS1 D2).

`log_predictions.py` (the sole writer -- WS1 D1) appends rows with `outcome: null`. This script
is the SEPARATE step that, once time has passed, fills in what actually happened -- forward_ic.py
(the judge) then reads `outcome` to compute IC; it never touches prices itself for outcomes.

Fills, per row, per horizon in forward_ic.HORIZONS (21/63/126 trading days):
    outcome = {
      "fwd_ret":       {"21": 0.0421, "63": null, "126": null},   # progressive -- 21d matures first
      "excess_vs_spy":  {"21": 0.0113, "63": null, "126": null},  # same-basis (adjusted) vs SPY
      "kill_fired":    null,                                     # MANUAL -- kill is a text condition,
                                                                  # a human/night-session judges it,
                                                                  # this script never sets it
      "filled_at":     "2026-07-08",
    }
A row keeps its `outcome` at null until at least ONE horizon has matured (nothing to report yet).
Once any horizon fills, `outcome` becomes the dict above and gets re-visited on later runs so the
still-null horizons (63d, 126d, ...) get filled in as they mature -- already-filled numbers are
never overwritten.

Price basis matches forward_ic.py exactly (adjusted=True total return via backtest/data.py;
SPY on the same basis) -- reuses forward_ic's `_price`/`_fwd_return`/`_bench_return` rather than
re-implementing them, so the judge and the backfill can never silently drift onto different bases.

No price source (e.g. SIVE -- delisted/renamed, unavailable on both yfinance and defeatbeta):
outcome = {"error": "no_price_source"} -- a terminal state; forward_ic.py's IC calc already skips
tickers with no price, and report() discloses `coverage.price_load_failed`.

Run: python thesis/backfill_outcomes.py
"""
import datetime as dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import forward_ic as fic  # noqa: E402  -- reuse _price/_fwd_return/_bench_return/HORIZONS/BENCH/TRACK

TRACK = fic.TRACK
HORIZONS = fic.HORIZONS


def _load_rows():
    rows = []
    if os.path.exists(TRACK):
        with open(TRACK, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    return rows


def _needs_work(row):
    """True if this row could still gain new outcome information: outcome is null, or is a
    (non-error) dict that still has a null sub-horizon left to fill."""
    oc = row.get("outcome")
    if oc is None:
        return True
    if not isinstance(oc, dict):
        return False
    if oc.get("error"):
        return False  # terminal -- no price source, nothing will change that
    fwd = oc.get("fwd_ret") or {}
    return any(fwd.get(str(n)) is None for n in HORIZONS)


def _fill_row(row, prices, bench, today):
    s = prices.get(row["ticker"])
    if s is None:
        row["outcome"] = {"error": "no_price_source"}
        return "error"

    prior = row.get("outcome") if isinstance(row.get("outcome"), dict) else {}
    fwd_ret = dict(prior.get("fwd_ret") or {})
    excess = dict(prior.get("excess_vs_spy") or {})
    any_new = False
    for n in HORIZONS:
        k = str(n)
        if fwd_ret.get(k) is not None:
            continue  # already filled on a previous run -- never overwrite
        fr = fic._fwd_return(s, row["ts"], n)
        if fr is None:
            fwd_ret[k] = None
            excess[k] = None
            continue
        fwd, tdate = fr
        br = fic._bench_return(bench, row["ts"], tdate)
        fwd_ret[k] = round(fwd, 4)
        excess[k] = round(fwd - br, 4) if br is not None else None
        any_new = True

    if not any_new and not any(v is not None for v in fwd_ret.values()):
        return "pending"  # nothing matured yet -- leave outcome as null

    row["outcome"] = {
        "fwd_ret": fwd_ret,
        "excess_vs_spy": excess,
        "kill_fired": prior.get("kill_fired", None),  # manual field -- never auto-set
        "filled_at": today,
    }
    return "filled"


def backfill():
    rows = _load_rows()
    if not rows:
        print(f"[backfill] {TRACK} empty/missing -- nothing to do.")
        return

    candidates = [r for r in rows if _needs_work(r)]
    n_terminal_before = len(rows) - len(candidates)
    tickers = sorted({r["ticker"] for r in candidates})
    prices = {t: fic._price(t) for t in tickers}
    bench = fic._price(fic.BENCH)
    today = dt.date.today().isoformat()

    counts = {"filled": 0, "error": 0, "pending": 0}
    for r in candidates:
        counts[_fill_row(r, prices, bench, today)] += 1

    with open(TRACK, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"[backfill] rows: {len(rows)} | candidates checked: {len(candidates)} | "
          f"newly filled/updated: {counts['filled']} | no_price_source: {counts['error']} | "
          f"still pending (no horizon matured yet): {counts['pending']} | "
          f"already terminal before this run: {n_terminal_before}")


if __name__ == "__main__":
    backfill()
