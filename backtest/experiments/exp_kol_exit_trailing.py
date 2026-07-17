"""KOL exit-rule control -- "順哥": does a TRAILING STOP replicate his exits?

WHY THIS EXISTS (it closes the gap the round-trip report declared on itself)
---------------------------------------------------------------------------
backtest/results/2026-07-17_kol_shunge_roundtrip.md §5 found his exits beat a dumb
timer by a lot (+19 to +23pp capital efficiency) and then refused to bank it:

    "本測試冇做 trailing stop / 動能出場對照,所以我只能講「贏計時器」,唔能夠講
     「有獨有價值」——呢個係本報告最重要嘅未補洞"

backtest/results/2026-07-17_kol_bear_confound.md is the reason that refusal was right:
his bearish calls are a momentum rule in disguise (paired-control percentile median
pinned at 0.500). An exit does not need FORECASTING power to beat a timer -- "it fell,
so leave" is a STATE RESPONSE and a state response beats a clock for free. If that is
all his exits are, a trailing stop -- a rule that costs nothing and needs no KOL --
should reproduce them. This script runs that control.

THE ONE-VARIABLE A/B
--------------------
ENTRIES ARE FROZEN. Every arm re-exits the EXACT SAME 894 entries taken from the
round-trip primary book (his LLM-extracted entries). The only thing that changes is the
exit rule. Nothing else -- not the extraction, not the price machinery, not the calendar.

  A  (baseline) his own exits (no exit signal -> 126d time-stop; identical to the
                round-trip primary arm, rebuilt here from the same state machine)
  B9 / B15      dumb timer, 9d / 15d (also a REGRESSION CHECK: these cells must
                reproduce the round-trip report's +15.3% / -1.1%)
  C5/C8/C10/C15 trailing stop: close out on the first close that is >= X% below the
                running peak CLOSE since entry (X = 5/8/10/15), no time cap
  D             trailing 10% + 126d time cap, whichever fires first
  E             volatility trailing: close <= peak - 2 x ATRproxy(14)  (see L3)
  F5/F10/F15/F20  POST-HOC, ADVERSARIAL (see P1): profit target +X% else 126d time-stop

SUBSAMPLES (3, reported separately -- the round-trip report's §6a split)
------------------------------------------------------------------------
  (i)  ALL 894
  (ii) HE CALLED AN EXIT  (n=734) -- the fair duel: his exit vs a trailing stop on the
       trades he actually managed
  (iii)HE ABANDONED IT    (n=160, 17.9% of entries, 36.4% of exposure, expectancy
       -5.51%) -- hypothesis: the stop wins big here because he simply was not there.

PRE-REGISTERED RULES (fixed BEFORE any arm's return was computed)
-----------------------------------------------------------------
T1. ENTRY SET = the priced round-trip primary book, frozen. An arm may never add,
    drop or move an entry. (Note this differs from re-running the state machine per
    arm: a different exit rule would let the machine open DIFFERENT later entries, and
    then "exit rule" and "entry set" would both be moving. Freezing entries is what
    makes this an exit-only test.)
T2. TRAILING STOP = peak of CLOSES since entry (entry close included), exit at the
    first close <= peak*(1-X). Scan starts at entry+1 (a 0-day trade is not a trade,
    round-trip R1 convention).
T3. NEVER TRIGGERED -> ride to the last available close, flagged truncated (round-trip
    R3 convention). NOT silently dropped. Arms C have NO time cap by design -- arm D
    is the one that adds the cap, so the cap's effect is isolated rather than baked in.
T4. ALL FOUR trailing widths are reported, always, in every table. Reporting only the
    best width would be the exact overfit this control exists to expose.
T5. METRICS = the round-trip R8 set, same code: capital efficiency (PnL/capital-days,
    annualized) leads; hit rate, expectancy, median excess vs SPY over IDENTICAL
    windows, hold distribution, avg_win/avg_loss (the right-tail read).
T6. VERDICT RULE, fixed before results were seen, so the answer cannot be shopped:
      trailing >= his        -> his exits have NO unique value; they are a free rule.
      his >> all four widths -> his exits carry real information. Positive finding.
      mixed / width-dependent-> ambiguous, and it gets written as ambiguous.

P1. THE POST-HOC ARM, AND WHY IT IS ALLOWED HERE (arms F)
    Arms A-E were pre-registered. Arms F were NOT: they were specified AFTER the A-E
    grid was read. That is normally result-shopping and would be inadmissible.
    It is admitted here for one reason, and the asymmetry is the whole justification:
    arms F can only DESTROY this script's headline, never create one.
      The A-E result was "his exits beat every trailing stop" -> a POSITIVE finding for
      him. But a trailing stop only reacts to a FALL, while his actual behaviour is
      selling into STRENGTH ("反弹目标 165 左右" = take profit at a target). So the
      trailing family may simply be the WRONG free rule to compare him against, and
      "he beats a trailing stop" would silently be inflated into "he is irreplicable".
      A profit-target rule is the closer mechanical mirror of what he actually does,
      and it is free. If a dumb "+X% or 126 days" rule reproduces him, the positive
      finding is FALSE and must not be published.
    A post-hoc search for a rule that WINS is mining. A post-hoc search for a rule that
    KILLS YOUR OWN CONCLUSION is due diligence. Arms F are only ever allowed to weaken
    the verdict, never to strengthen it -- and all four widths are reported (T4).

DECLARED LIMITATIONS
--------------------
L1. STOP ON CLOSE, NOT INTRADAY. The cache is adjusted CLOSE only, so a real intraday
    stop is not implementable. A close-only stop cuts BOTH ways vs a live one: it never
    gets whipsawed by an intraday spike (flattering), and it fills below the stop level
    on gap-downs (punishing). Net sign unknown; not modelled.
L2. NO COSTS. No commission, no slippage, no borrow. The trailing arms trade LESS often
    than his book on the abandoned cohort and MORE often on some others; costs are not
    modelled anywhere, so no arm is advantaged relative to another by this omission --
    but no arm's absolute number is executable either.
L3. ATRproxy IS NOT ATR. True ATR(14) needs high/low; the cache has closes only. Arm E
    uses a 14-day rolling mean of |close_t - close_t-1| -- a close-to-close range proxy.
    It systematically UNDERSTATES true ATR (it cannot see the intraday range), so arm E
    stops TIGHTER than a real 2xATR(14) chandelier would. Arm E is a directional
    indication, not a spec-accurate ATR test. Re-pulling OHLC for 850 tickers would
    also break round-trip R4 (one price machine for the book and every control), which
    is a worse trade than declaring this.
L4. SUBSAMPLE (ii)/(iii) IS AN EX-POST PARTITION AND NOT TRADEABLE. Whether he later
    calls an exit is unknowable at entry. So "use his entries + a stop on the ones he
    abandons" is NOT a strategy -- you cannot know in advance which ones those are.
    Any real deployment must apply one rule to ALL entries; that is what subsample (i)
    measures and it is the only one with a tradeable reading.
L5. EFFECTIVE SAMPLE ~= 1 (round-trip §8.1, inherited unchanged). Windows overlap into
    one connected component; every CI here is optimistic. Conclusions lean on the
    direction and SIZE of gaps across arms, never on a single interval.
L6. MULTIPLE COMPARISONS: 9 arms x 3 subsamples x ~12 metrics. Tallied and printed in
    the report. The verdict rule (T6) was fixed in advance precisely so this grid
    cannot be mined.
L7. ONE KOL, ONE BULL CYCLE (2023-2026). A no-cap trailing stop in an uninterrupted
    bull market is close to buy-and-hold-with-a-floor; that is a regime gift, not a
    discovery. The SPY-over-identical-windows column is carried on EVERY arm so that
    the gift is visible instead of being counted as skill.

Run:  PYTHONUTF8=1 python backtest/experiments/exp_kol_exit_trailing.py --analyze
Deliverable -> backtest/results/2026-07-17_kol_exit_trailing.md
Intermediate (gitignored) -> thesis/.raw/discord/exit_trailing_report.json
Reads only existing material: llm_claims.json (9,088 hindsight-blind records) and
prices/. Nothing is re-extracted.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# VERBATIM REUSE -- the round-trip state machine and price machinery are imported, not
# reimplemented, so this test is apples-to-apples with the report it is patching.
from backtest.experiments.exp_kol_shunge_roundtrip import (  # noqa: E402
    LLM_CLAIMS, OPEN_ACTIONS, TIME_STOP, TRADING_DAYS, build_price_arrays, build_trades,
    effective_clusters, hold_distribution, price_trades, ret_between,
    signals_from_llm, stats,
)
from backtest.experiments.exp_kol_shunge_ledger import RAW, _px  # noqa: E402

OUT = RAW / "exit_trailing_report.json"

TRAIL_WIDTHS = (0.05, 0.08, 0.10, 0.15)   # T4: all four, always
PT_WIDTHS = (0.05, 0.10, 0.15, 0.20)      # P1: post-hoc adversarial arm, all reported
ATR_WIN = 14
ATR_MULT = 2.0
NO_RULE = 10 ** 9        # ret_between clamps to last_i and flags truncated (T3)


# ---------------------------------------------------------------------------
# L3: close-only ATR proxy (declared NOT to be ATR)
# ---------------------------------------------------------------------------
def atr_proxy(px: dict, win: int = ATR_WIN) -> dict:
    out = {}
    for sym, pa in px.items():
        f = pd.Series(pa["filled"])
        out[sym] = f.diff().abs().rolling(win, min_periods=win).mean().to_numpy()
    return out


# ---------------------------------------------------------------------------
# The exit rules under test. Entries frozen (T1); only the exit index moves.
# ---------------------------------------------------------------------------
def exit_index(pa: dict, i0: int, drop: float | None, time_cap: int | None,
               atr: np.ndarray | None, pt: float | None = None) -> tuple[int, str]:
    """Return (target_exit_i, exit_reason). NO_RULE = nothing fired -> ride to last."""
    last = pa["last_i"]
    cands: list[tuple[int, str]] = []

    if drop is not None or atr is not None:
        path = pa["filled"][i0:last + 1]
        peak = np.maximum.accumulate(path)                    # T2: entry close included
        if drop is not None:
            level = peak * (1.0 - drop)
        else:
            a = atr[i0:last + 1]
            level = peak - ATR_MULT * a                       # chandelier, close-only
        hit = np.flatnonzero(path <= level)
        hit = hit[hit >= 1]                                   # T2: scan from entry+1
        if len(hit):
            cands.append((i0 + int(hit[0]), "trail"))

    if pt is not None:                                        # P1: profit target
        path = pa["filled"][i0:last + 1]
        hit = np.flatnonzero(path >= pa["raw"][i0] * (1.0 + pt))
        hit = hit[hit >= 1]                                   # T2: scan from entry+1
        if len(hit):
            cands.append((i0 + int(hit[0]), "target"))

    if time_cap is not None:
        cands.append((i0 + time_cap, "time_cap"))

    if not cands:
        return NO_RULE, "ride_to_end"
    return min(cands, key=lambda c: c[0])


def rebuild_book(df: pd.DataFrame, px: dict, spy_pa: dict, cal, *,
                 drop: float | None = None, time_cap: int | None = None,
                 atr: dict | None = None, pt: float | None = None) -> pd.DataFrame:
    """Re-exit the FROZEN entry set under one alternative rule."""
    rows = []
    for _, t in df.iterrows():
        sym = t["ticker"]
        pa = px[sym]
        i0 = int(t["entry_i"])
        tgt, reason = exit_index(pa, i0, drop, time_cap,
                                 atr[sym] if atr is not None else None, pt)
        r, trunc = ret_between(pa, i0, tgt)
        if r is None:
            continue
        sr, _ = ret_between(spy_pa, i0, tgt)
        if sr is None:
            continue
        end = min(tgt, pa["last_i"])
        rows.append({"ticker": sym, "entry_i": i0, "exit_i_eff": end,
                     "days": end - i0, "ret": r, "spy_ret": sr, "xs": r - sr,
                     "trunc": trunc, "year": t["year"], "basket": t["basket"],
                     "coh": t["exit_type"],          # cohort = HIS behaviour (L4)
                     "reason": reason,
                     "entry_date": t["entry_date"], "exit_date": cal[end]})
    return pd.DataFrame(rows)


def tail_stats(df: pd.DataFrame) -> dict:
    """Right-tail read -- round-trip §3 found his exits amputate it."""
    if df.empty:
        return {}
    r = df["ret"].to_numpy()
    return {"p75_abs": float(np.percentile(r, 75)),
            "p90_abs": float(np.percentile(r, 90)),
            "p99_abs": float(np.percentile(r, 99)),
            "max_abs": float(r.max()),
            "pct_ret_gt_50": float((r > 0.50).mean()),
            "pct_ret_gt_100": float((r > 1.00).mean())}


def common_horizon(s: dict, park_rate: float, H: int = TIME_STOP) -> dict:
    """N1: exposure-normalized read (SENSITIVITY, not the headline).

    cap_eff answers "what rate do I earn WHILE DEPLOYED" and therefore rewards short
    holds -- it implicitly assumes freed capital is redeployed at the book's OWN rate.
    That assumption is only safe if the book is capacity-rich enough to fill the idle
    days with more trades. It also has a perverse edge case that bites subsample (iii):
    on a LOSING cohort a LONGER hold looks BETTER, because the same negative PnL is
    divided by more capital-days. (His abandoned cohort "beats" the 9d timer on cap_eff
    -13.0% vs -46.4% while losing 3.4x more money: -8.81 vs -2.59.)

    So this normalizes every arm onto ONE 126-day capital horizon: hold the trade for
    its mean duration, park the remaining days in SPY at the rate SPY actually did over
    that same cohort's windows. It answers the ONE-UNIT-OF-CAPITAL question instead of
    the rate question. Neither metric is "the" truth -- they bracket the answer:
      cap_eff       -> upper bound on a short-hold arm (assumes perfect redeployment)
      common_horizon-> lower bound on a short-hold arm (assumes only SPY to redeploy into)
    Regime caveat L7: the SPY parking rate is a realized BULL-market rate, so this
    normalization is generous to short-hold arms in exactly the era being measured.
    """
    if not s.get("n"):
        return {}
    mean_days = s["cap_days"] / s["n"]
    idle = max(0.0, H - mean_days)
    return {"mean_days": mean_days, "park_rate": park_rate,
            "ch_ret": s["expectancy"] + idle / TRADING_DAYS * park_rate,
            "ch_spy_only": park_rate * H / TRADING_DAYS}


def arm_report(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"n": 0}
    out = stats(df) | {"clusters": effective_clusters(df)}
    out |= tail_stats(df)
    out["hold"] = hold_distribution(df)
    out["reason_mix"] = {k: int(v) for k, v in df["reason"].value_counts().items()}
    out["cap_eff_minus_spy"] = out["cap_eff"] - out["spy_cap_eff"]
    return out


# ---------------------------------------------------------------------------
def stage_analyze() -> None:
    blob = json.loads(LLM_CLAIMS.read_text(encoding="utf-8"))
    recs = blob["records"]

    # --- rebuild the frozen entry set from the round-trip primary arm (T1) ---
    sigs, close = signals_from_llm(recs, "primary")
    tickers = sorted({r["ticker"] for r in recs})
    cal = _px("SPY").index
    px = build_price_arrays(tickers + ["SPY"], cal)
    spy_pa = px["SPY"]
    tr = build_trades(sigs, cal, px, OPEN_ACTIONS, close)
    base = price_trades(tr, cal, px, spy_pa)
    base["reason"] = base["exit_type"]
    base["coh"] = base["exit_type"]
    print(f"priced {len(px) - 1}/{len(tickers)} tickers | frozen entry set n={len(base)} "
          f"(round-trip primary book = 894 expected)")

    atr = atr_proxy(px)

    # --- the arms (T1: identical entries throughout) ---
    arms: dict[str, pd.DataFrame] = {"A_his_exits": base}
    for d in (9, 15):
        arms[f"B{d}_timer"] = rebuild_book(base, px, spy_pa, cal, time_cap=d)
    for w in TRAIL_WIDTHS:                                    # T4: all four
        arms[f"C{int(w * 100)}_trail"] = rebuild_book(base, px, spy_pa, cal, drop=w)
    arms["D_trail10_cap126"] = rebuild_book(base, px, spy_pa, cal, drop=0.10,
                                            time_cap=TIME_STOP)
    arms["E_atr2x_proxy"] = rebuild_book(base, px, spy_pa, cal, atr=atr)
    # P1: post-hoc, adversarial. Closest free mirror of "sell into strength at a
    # target, else sit". Allowed only because it can kill the headline, not make one.
    for p in PT_WIDTHS:
        arms[f"F{int(p * 100)}_target_cap126"] = rebuild_book(
            base, px, spy_pa, cal, pt=p, time_cap=TIME_STOP)

    # --- 3 subsamples (L4: (ii)/(iii) are ex-post, not tradeable) ---
    subs = {"all": lambda d: d,
            "signal": lambda d: d[d.coh == "signal"],
            "abandoned": lambda d: d[d.coh == "time_stop"]}

    rep: dict = {"meta": {
        "n_entries_frozen": int(len(base)),
        "trail_widths": list(TRAIL_WIDTHS), "atr_win": ATR_WIN, "atr_mult": ATR_MULT,
        "time_stop": TIME_STOP,
        "entry_span": [str(base["entry_date"].min().date()),
                       str(base["entry_date"].max().date())],
        "n_tests": len(arms) * len(subs) * 12,
        "limitations": ["L1 stop-on-close not intraday", "L2 no costs",
                        "L3 ATRproxy != ATR (close-only, understates -> tighter)",
                        "L4 (ii)/(iii) ex-post partition, not tradeable",
                        "L5 effective sample ~= 1", "L6 multiple comparisons",
                        "L7 one KOL / one bull cycle"],
    }, "arms": {}}

    for name, adf in arms.items():
        rep["arms"][name] = {}
        for sname, fn in subs.items():
            rep["arms"][name][sname] = arm_report(fn(adf).reset_index(drop=True))

    # N1: exposure-normalized sensitivity. Parking rate = what SPY ACTUALLY returned
    # over arm A's windows for that cohort -- one rate per subsample, so every arm in a
    # column is charged the same opportunity cost.
    for sname in subs:
        park = rep["arms"]["A_his_exits"][sname]["spy_cap_eff"]
        for name in arms:
            ch = common_horizon(rep["arms"][name][sname], park)
            if ch:
                rep["arms"][name][sname]["common_horizon"] = ch

    OUT.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    print(f"wrote {OUT}\n")

    # --- console: the grid the report is built from (T4: nothing hidden) ---
    for sname in subs:
        n0 = rep["arms"]["A_his_exits"][sname].get("n", 0)
        print(f"\n=== subsample {sname} (n={n0}) "
              f"{'-' * 20}")
        print(f"{'arm':<18} {'n':>4} {'hit':>6} {'exp':>8} {'medXS':>8} "
              f"{'capEff':>8} {'SPYsame':>8} {'delta':>8} {'medD':>5} "
              f"{'avgW':>8} {'avgL':>8} {'p90':>8} {'trunc':>6}")
        for name in arms:
            s = rep["arms"][name][sname]
            if not s.get("n"):
                continue
            print(f"{name:<18} {s['n']:>4} {s['hit_abs']:>6.1%} "
                  f"{s['expectancy']:>+8.2%} {s['median_xs']:>+8.2%} "
                  f"{s['cap_eff']:>+8.1%} {s['spy_cap_eff']:>+8.1%} "
                  f"{s['cap_eff_minus_spy'] * 100:>+8.1f} {s['hold']['median']:>5.0f} "
                  f"{s['avg_win']:>+8.2%} {s['avg_loss']:>+8.2%} "
                  f"{s['p90_abs']:>+8.1%} {s['trunc_pct']:>6.1%}")

    # --- N1: the exposure-normalized column (does the cap_eff ranking survive?) ---
    for sname in subs:
        park = rep["arms"]["A_his_exits"][sname]["spy_cap_eff"]
        spy_only = park * TIME_STOP / TRADING_DAYS
        print(f"\n=== N1 common-horizon {sname}: one unit of capital for {TIME_STOP}d, "
              f"idle days parked in SPY @ {park:+.1%}/yr")
        print(f"{'arm':<18} {'meanD':>6} {'exp/trade':>10} {'126d total':>11} "
              f"{'vs SPY-only':>12}")
        rows = [(n, rep["arms"][n][sname]["common_horizon"]) for n in arms
                if rep["arms"][n][sname].get("common_horizon")]
        for n, ch in sorted(rows, key=lambda r: -r[1]["ch_ret"]):
            print(f"{n:<18} {ch['mean_days']:>6.1f} "
                  f"{rep['arms'][n][sname]['expectancy']:>+10.2%} "
                  f"{ch['ch_ret']:>+11.2%} {(ch['ch_ret'] - spy_only) * 100:>+10.2f}pp")
        print(f"{'(SPY only, no trades)':<18} {'--':>6} {'--':>10} {spy_only:>+11.2%}")

    # --- regression check vs the round-trip report (must reproduce) ---
    print("\n=== REGRESSION CHECK vs 2026-07-17_kol_shunge_roundtrip.md")
    checks = [
        ("entries", len(base), 894),
        ("A all cap_eff %", round(rep["arms"]["A_his_exits"]["all"]["cap_eff"] * 100, 1),
         18.4),
        ("A signal cap_eff %",
         round(rep["arms"]["A_his_exits"]["signal"]["cap_eff"] * 100, 1), 36.3),
        ("A abandoned cap_eff %",
         round(rep["arms"]["A_his_exits"]["abandoned"]["cap_eff"] * 100, 1), -13.0),
        ("B15 all cap_eff %", round(rep["arms"]["B15_timer"]["all"]["cap_eff"] * 100, 1),
         -1.1),
        ("B9 signal cap_eff %",
         round(rep["arms"]["B9_timer"]["signal"]["cap_eff"] * 100, 1), 15.3),
    ]
    for label, got, want in checks:
        ok = "OK " if abs(got - want) < 0.15 else "DIFF"
        print(f"  [{ok}] {label:<22} got={got:<8} report={want}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--analyze", action="store_true")
    a = ap.parse_args()
    if a.analyze:
        stage_analyze()


if __name__ == "__main__":
    main()
