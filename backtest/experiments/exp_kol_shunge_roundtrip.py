"""KOL round-trip test -- "順哥" (royal flush 皇者顺888). MIRROR + EXTRACTION FIX.

WHY THIS EXISTS (two acknowledged errors in the prior reports)
--------------------------------------------------------------
E1. WRONG MIRROR. backtest/results/2026-07-17_kol_shunge_scorecard.md scored every
    bullish claim by holding a FIXED 21/63/126 trading days -> "bull calls = negative
    alpha". He does not give buy-and-hold recommendations; he gives trades WITH AN
    EXIT. His own words:
        "soxl 144 這裡有些支撐...如果要買就只能進進出出。反彈目標 165 左右 lower high"
    Taking his entry and holding 126 days measures a strategy he never proposed. Repo
    principle (memory: validation-mirror-and-increment): the mirror MUST match how the
    signal is actually used.
E2. LOSSY EXTRACTION. The scorecard's keyword rule discarded 45.1% of ticker-bearing
    messages as "ambiguous", and applied ONE per-MESSAGE direction to EVERY ticker in
    that message (a message naming 11 tickers produced 11 identical-direction claims).
    He writes colloquial mixed zh/en ("Bot spy 381 开始小量买了一点", "进进出出",
    "反弹目标165 左右"). A rigid keyword rule cannot catch that book.

This script rebuilds BOTH layers and re-answers the question.

HINDSIGHT-BLIND LLM EXTRACTION (the reason LLM extraction is allowed here)
--------------------------------------------------------------------------
The original ban on LLM extraction existed to stop hindsight bias. That risk is
addressed structurally rather than by avoidance -- the extractor is blinded on the
only channels through which hindsight could enter:
  B1. It sees ONLY message text. No prices, no returns, no market data; extraction
      subagents are instructed to use Read/Write only (no WebSearch/WebFetch/Bash).
  B2. It never sees the message DATE. Dates are stripped from the batch files and
      re-joined afterwards by message id. An extractor that cannot date a message
      cannot apply "I know what this stock did next".
  B3. The label is a LINGUISTIC judgment ("is this sentence a buy/sell instruction?"),
      never an evaluative one ("was he right?").
  B4. The ticker vocabulary is FROZEN to the same regex + exchange-universe filter the
      keyword arm used. The LLM may only label candidates it is handed, never invent
      one. So the keyword-vs-LLM A/B isolates ACTION LABELLING, holding ticker
      resolution constant.
  Residual risk (declared, not solved): an LLM has a knowledge cutoff and could in
  principle infer an era from content (e.g. a bank-crisis reference). B1-B3 remove the
  price channel and the date channel; the era channel cannot be fully closed.

SCHEMA (per message x candidate ticker):
  {ticker, action: entry|exit|trim|add|warning|none, conviction: strong|normal|
   tentative, price_level, target, timeframe, is_index_call, raw_quote}

PRE-REGISTERED RULES (fixed in this file BEFORE any extraction output or return was
read; the analyze stage did not exist in runnable form until after they were written)
--------------------------------------------------------------------------------
R1. ACTION -> TRADE MAPPING (primary arm):
      flat + entry|add   -> OPEN at the close of the FIRST trading day strictly after
                            the message date (same next-close convention as the
                            scorecard; no look-ahead). "add" opens when flat because a
                            flat book means we missed the original entry -- following
                            him from here means buying now.
      long + entry|add   -> IGNORED (no pyramiding; first entry of a run only).
      long + exit|trim   -> CLOSE at the first trading day strictly after that message,
                            provided exit_i > entry_i (a 0-day trade is not a trade; if
                            exit_i == entry_i the signal is skipped and the next one
                            used). "trim" closes because in a 1-unit book "reduce" is
                            the risk-off instruction he gave.
      long + warning     -> IGNORED in the primary arm.
      none               -> ignored.
    SENSITIVITY ARMS (reported, never used to pick a headline):
      S-A "exit-only"    : only action=exit closes (trim ignored).
      S-B "warning-exits": warning also closes.
R2. NO EXIT -> TIME-STOP at entry_i + 126 trading days, reported as a SEPARATE cohort
    with its % of the book. "He never calls the exit on losers" would be a hidden bias
    that silently turns a trade book into a buy-and-hold book, so this cohort is never
    pooled away.
R3. TRUNCATION -- if a window runs past available price history (recent calls,
    delistings) the last available close is used and the trade is flagged truncated
    (scorecard S5 convention). Not silently dropped.
R4. PRICE MACHINERY -- ONE machine for the book and all controls: adjusted closes
    reindexed onto the SPY trading calendar and forward-filled; entry requires a RAW
    close on the entry day; exit uses index min(exit_i, last_valid_i). Returns are
    recomputed from prices, NOT read from scored.json, so book and controls are exactly
    comparable. (So numbers here need not tie out to the scorecard's dropna-last
    variant -- do not cross-subtract between reports.)
R5. BASKETS (his claim: ~75% win rate on stocks, ~85% on the index -> must be split):
      INDEX basket (primary, deterministic ticker list fixed here):
        SPY QQQ DIA IWM VOO IVV SPX NDX TQQQ SQQQ UPRO SPXU SPXL SPXS QLD SSO PSQ SH
        QID SDS UDOW SDOW DDM RSP  (broad-market trackers incl. leveraged/inverse)
      STOCK basket: everything else (sector/thematic ETFs like SOXL count as STOCK --
        they are not 大盤).
      SENSITIVITY: the LLM's is_index_call flag as an alternative split.
R6. WIN RATE = his own game: round trip (his entry -> his exit), ABSOLUTE return > 0.
    Reported with n and a Wilson 95% CI, against his claimed 75% / 85%.
R7. EXPECTANCY = win_rate*avg_win - loss_rate*avg_loss (mean return per trade).
    Reported ALONGSIDE win rate, never instead of it. Both are facts and they answer
    different questions: a 75% win rate can still lose money (win small / lose big),
    and a positive expectancy can come with a sub-50% win rate. Neither number is
    allowed to cancel the other in the write-up.
R8. METRICS -- three, together:
      hit rate + median ABSOLUTE return   -> what the follower actually feels
      excess vs SPY over IDENTICAL entry/exit dates -> better than beta?
      capital efficiency = sum(PnL)/sum(capital-days)*252 -> Karst's primary metric:
        annualized return on capital WHILE DEPLOYED. Short trades tie up little
        capital, so a book can be efficient with a small absolute PnL. A fixed-horizon
        mirror structurally cannot see this.
R9. CONTROLS (report is void without all three):
      (a) SAME-EXPOSURE RANDOM ENTRY -- same ticker, same holding length D, random
          start, 1,000 MC draws. Entry drawn uniformly from trading days inside the
          corpus span where the ticker has a raw close. Restricting to the corpus span
          holds the (bull) regime fixed, isolating HIS TIMING instead of re-testing the
          era. Answers: "is his timing better than a random day?"
      (b) SPY BUY&HOLD over the identical entry/exit dates.
      (c) NAIVE FIXED HOLD -- his entry, exit after a fixed number of days (the
          cohort's median hold) instead of his exit signal. The ONLY control that
          isolates the EXIT signal: if (c) ~= actual, his exits add nothing and any
          timer does the same job.
R10. SEGMENTS -- entry year, exit type (signal vs time-stop), basket, conviction.

STATISTICAL HONESTY
-------------------
- Overlapping windows: trades share calendar time, so raw n overstates independence. An
  approximate independent-cluster count (connected components of the interval-overlap
  graph) sits next to every raw n.
- Multiple comparisons: the test count is tallied and printed; conclusions lean on
  direction-consistency across independent designs, not on a single p-value.
- MC percentile is a one-sided read of a 1,000-draw null; p95 is the bar.
- The keyword arm is rebuilt here on the SAME price machinery, so "old mirror vs new
  mirror" and "keyword vs LLM" are clean one-variable A/Bs.

Stages:
  PYTHONUTF8=1 python exp_kol_shunge_roundtrip.py --prep      # -> llm_batches/*.json
  (dispatch extraction subagents -> llm_extract/*.jsonl)
  PYTHONUTF8=1 python exp_kol_shunge_roundtrip.py --merge     # -> llm_claims.json + QA
  PYTHONUTF8=1 python exp_kol_shunge_roundtrip.py --analyze   # -> roundtrip_report.json
Deliverable -> backtest/results/2026-07-17_kol_shunge_roundtrip.md
Intermediates (gitignored, under thesis/.raw/discord/): llm_batches/, llm_extract/,
llm_claims.json, roundtrip_report.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backtest.experiments.exp_kol_shunge_ledger import (  # noqa: E402
    CLAIMS, ENGLISH_BLOCKLIST, RAW, TOKEN_RE, _clean, _direction, _load_messages,
    _px, load_universe,
)

SEED = 20260717
BATCHES = RAW / "llm_batches"
EXTRACT = RAW / "llm_extract"
LLM_CLAIMS = RAW / "llm_claims.json"
OUT = RAW / "roundtrip_report.json"

BATCH_SIZE = 96
TIME_STOP = 126
N_MC = 1000
TRADING_DAYS = 252

OPEN_ACTIONS = {"entry", "add"}          # R1 primary
CLOSE_ACTIONS = {"exit", "trim"}         # R1 primary
VALID_ACTIONS = {"entry", "add", "exit", "trim", "warning", "none"}

# R5: index basket -- fixed here, before any return was read.
INDEX_TICKERS = {
    "SPY", "QQQ", "DIA", "IWM", "VOO", "IVV", "SPX", "NDX", "TQQQ", "SQQQ",
    "UPRO", "SPXU", "SPXL", "SPXS", "QLD", "SSO", "PSQ", "SH", "QID", "SDS",
    "UDOW", "SDOW", "DDM", "RSP",
}


# ---------------------------------------------------------------------------
# PREP: hindsight-blind batch files (B2: NO dates go to the extractor)
# ---------------------------------------------------------------------------
def stage_prep() -> None:
    msgs = _load_messages()
    uni = load_universe()
    kol = [m for m in msgs if "皇者顺" in m["author"]["name"]]

    rows = []
    for m in kol:
        text = _clean(m.get("content") or "")
        if not text.strip():
            continue
        toks = {t.upper() for t in TOKEN_RE.findall(text)
                if t.lower() not in ENGLISH_BLOCKLIST}
        tk = sorted(t for t in toks if t in uni)      # B4: frozen vocabulary
        if not tk:
            continue
        rows.append({"mid": m["id"], "text": text.strip(), "candidates": tk,
                     "_ts": m["timestamp"], "_kw_dir": _direction(text)})

    # side table keeps ts + keyword label OUT of the batch files, joined later by mid
    side = {r["mid"]: {"ts": r["_ts"], "kw_dir": r["_kw_dir"],
                       "candidates": r["candidates"], "text": r["text"]} for r in rows}
    (RAW / "roundtrip_side.json").write_text(
        json.dumps(side, ensure_ascii=False), encoding="utf-8")

    BATCHES.mkdir(exist_ok=True)
    for f in BATCHES.glob("*.json"):
        f.unlink()
    n = 0
    for i in range(0, len(rows), BATCH_SIZE):
        chunk = [{"mid": r["mid"], "text": r["text"], "candidates": r["candidates"]}
                 for r in rows[i:i + BATCH_SIZE]]
        (BATCHES / f"batch_{n:03d}.json").write_text(
            json.dumps(chunk, ensure_ascii=False, indent=1), encoding="utf-8")
        n += 1
    exp = sum(len(r["candidates"]) for r in rows)
    print(f"messages={len(rows)} batches={n} expected_records={exp}")
    print(f"keyword-arm labels on these: "
          f"{pd.Series([r['_kw_dir'] for r in rows]).value_counts().to_dict()}")


# ---------------------------------------------------------------------------
# MERGE: validate extractor output, join dates back, QA vs keyword arm
# ---------------------------------------------------------------------------
def stage_merge() -> None:
    side = json.loads((RAW / "roundtrip_side.json").read_text(encoding="utf-8"))
    recs, bad = [], []
    seen: set[tuple[str, str]] = set()
    for f in sorted(EXTRACT.glob("*.jsonl")):
        for ln, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                bad.append(f"{f.name}:{ln} unparseable")
                continue
            mid, tk, act = str(r.get("mid")), r.get("ticker"), r.get("action")
            if mid not in side:
                bad.append(f"{f.name}:{ln} unknown mid {mid}")
                continue
            if tk not in side[mid]["candidates"]:
                bad.append(f"{f.name}:{ln} ticker {tk} not a candidate of {mid}")
                continue
            if act not in VALID_ACTIONS:
                bad.append(f"{f.name}:{ln} bad action {act}")
                continue
            if (mid, tk) in seen:
                continue
            seen.add((mid, tk))
            recs.append({"mid": mid, "ticker": tk, "action": act,
                         "conviction": r.get("conviction"),
                         "price_level": r.get("price_level"),
                         "target": r.get("target"), "timeframe": r.get("timeframe"),
                         "is_index_call": bool(r.get("is_index_call", False)),
                         "raw_quote": r.get("raw_quote"),
                         "ts": side[mid]["ts"]})           # B2: date rejoined HERE

    expected = {(m, t) for m, v in side.items() for t in v["candidates"]}
    missing = expected - seen
    qa = {"records": len(recs), "expected": len(expected), "missing": len(missing),
          "coverage_pct": round(100 * len(seen) / max(1, len(expected)), 2),
          "bad_lines": len(bad), "bad_sample": bad[:20],
          "missing_sample": [f"{m}:{t}" for m, t in list(missing)[:20]]}

    # --- keyword-vs-LLM A/B: what did the old rule miss? (message level) ---
    act_by_mid: dict[str, set[str]] = {}
    for r in recs:
        act_by_mid.setdefault(r["mid"], set()).add(r["action"])
    actionable = {m for m, a in act_by_mid.items() if a & (OPEN_ACTIONS | CLOSE_ACTIONS)}
    kw_amb = {m for m, v in side.items() if v["kw_dir"] == "ambiguous"}
    kw_dir = {m for m, v in side.items() if v["kw_dir"] in ("bull", "bear")}
    qa["ab_keyword_vs_llm"] = {
        "msgs_total": len(side),
        "kw_ambiguous_discarded": len(kw_amb),
        "kw_ambiguous_but_llm_actionable": len(kw_amb & actionable),
        "miss_rate_pct_of_discarded": round(
            100 * len(kw_amb & actionable) / max(1, len(kw_amb)), 1),
        "miss_rate_pct_of_all_msgs": round(
            100 * len(kw_amb & actionable) / max(1, len(side)), 1),
        "kw_directional_but_llm_none": len(kw_dir - actionable),
        "kw_fp_rate_pct": round(100 * len(kw_dir - actionable) / max(1, len(kw_dir)), 1),
    }
    qa["miss_examples"] = [
        {"mid": m, "text": side[m]["text"][:180],
         "llm": [{k: r[k] for k in ("ticker", "action", "raw_quote")}
                 for r in recs if r["mid"] == m and r["action"] != "none"]}
        for m in list(kw_amb & actionable)[:12]]

    from collections import Counter
    qa["action_counts"] = dict(Counter(r["action"] for r in recs))
    qa["conviction_counts"] = dict(Counter(
        r["conviction"] for r in recs if r["action"] != "none"))
    qa["timeframe_counts"] = dict(Counter(
        r["timeframe"] for r in recs if r["action"] != "none"))

    LLM_CLAIMS.write_text(json.dumps({"qa": qa, "records": recs}, ensure_ascii=False),
                          encoding="utf-8")
    print(json.dumps({k: v for k, v in qa.items()
                      if k not in ("miss_examples", "bad_sample", "missing_sample")},
                     indent=1, ensure_ascii=False))


# ---------------------------------------------------------------------------
# R4: price machinery -- one machine for the book and every control
# ---------------------------------------------------------------------------
def build_price_arrays(tickers: list[str], cal: pd.DatetimeIndex) -> dict:
    out = {}
    for sym in tickers:
        s = _px(sym)
        if s is None or s.empty:
            continue
        s = s[~s.index.duplicated(keep="last")]
        raw = s.reindex(cal).astype("float64")
        valid = np.flatnonzero(np.isfinite(raw.to_numpy()))
        if len(valid) < 2:
            continue
        out[sym] = {"raw": raw.to_numpy(), "filled": raw.ffill().to_numpy(),
                    "first_i": int(valid[0]), "last_i": int(valid[-1])}
    return out


def ret_between(pa: dict, i0: int, i1: int) -> tuple[float | None, bool]:
    if i0 < pa["first_i"] or i0 > pa["last_i"]:
        return None, False
    a = pa["raw"][i0]
    if not np.isfinite(a) or a <= 0:
        return None, False
    end = min(i1, pa["last_i"])
    if end <= i0:
        return None, False
    b = pa["filled"][end]
    if not np.isfinite(b) or b <= 0:
        return None, False
    return float(b / a - 1.0), bool(end < i1)


def next_trading_i(cal: pd.DatetimeIndex, d: pd.Timestamp) -> int | None:
    i = int(cal.searchsorted(d, side="right"))
    return i if i < len(cal) else None


# ---------------------------------------------------------------------------
# R1: trade construction (shared by the LLM arm and the keyword arm)
# ---------------------------------------------------------------------------
def build_trades(signals: list[dict], cal: pd.DatetimeIndex, px: dict,
                 open_acts: set[str], close_acts: set[str]) -> list[dict]:
    """signals: [{ticker, date, action, ...}] -- any labelling scheme."""
    by_ticker: dict[str, list[dict]] = {}
    for s in signals:
        by_ticker.setdefault(s["ticker"], []).append(s)

    trades = []
    for sym, sigs in sorted(by_ticker.items()):
        pa = px.get(sym)
        if pa is None:
            continue
        sigs = sorted(sigs, key=lambda s: (s["ts"], 0 if s["action"] in open_acts else 1))
        entry_i, entry_sig = None, None
        for s in sigs:
            if s["action"] not in open_acts and s["action"] not in close_acts:
                continue
            i = next_trading_i(cal, pd.Timestamp(s["date"]))
            if i is None:
                continue
            if s["action"] in open_acts:
                if entry_i is None and np.isfinite(pa["raw"][i]) \
                        and pa["first_i"] <= i <= pa["last_i"]:
                    entry_i, entry_sig = i, s
            else:
                if entry_i is None or i <= entry_i:
                    continue
                trades.append({"ticker": sym, "entry_i": entry_i, "exit_i": i,
                               "signal_date": entry_sig["date"], "exit_date_sig": s["date"],
                               "exit_type": "signal",
                               "conviction": entry_sig.get("conviction"),
                               "timeframe": entry_sig.get("timeframe"),
                               "is_index_call": entry_sig.get("is_index_call", False)})
                entry_i, entry_sig = None, None
        if entry_i is not None:
            trades.append({"ticker": sym, "entry_i": entry_i,
                           "exit_i": entry_i + TIME_STOP, "signal_date": entry_sig["date"],
                           "exit_date_sig": None, "exit_type": "time_stop",
                           "conviction": entry_sig.get("conviction"),
                           "timeframe": entry_sig.get("timeframe"),
                           "is_index_call": entry_sig.get("is_index_call", False)})
    return trades


def price_trades(trades: list[dict], cal, px: dict, spy_pa: dict) -> pd.DataFrame:
    rows = []
    for t in trades:
        pa = px[t["ticker"]]
        r, trunc = ret_between(pa, t["entry_i"], t["exit_i"])
        if r is None:
            continue
        sr, _ = ret_between(spy_pa, t["entry_i"], t["exit_i"])
        if sr is None:
            continue
        end = min(t["exit_i"], pa["last_i"])
        rows.append({**t, "exit_i_eff": end, "days": end - t["entry_i"], "ret": r,
                     "spy_ret": sr, "xs": r - sr, "trunc": trunc,
                     "entry_date": cal[t["entry_i"]], "exit_date": cal[end],
                     "year": int(cal[t["entry_i"]].year),
                     "basket": "index" if t["ticker"] in INDEX_TICKERS else "stock"})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# R6/R7/R8: metrics
# ---------------------------------------------------------------------------
def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def stats(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"n": 0}
    r, x, d = df["ret"].to_numpy(), df["xs"].to_numpy(), df["days"].to_numpy()
    wins, losses = r[r > 0], r[r <= 0]
    cap_days = float(d.sum())
    k = int((r > 0).sum())
    lo, hi = wilson(k, len(r))
    return {
        "n": int(len(df)), "wins": k,
        "hit_abs": float((r > 0).mean()), "ci95_lo": lo, "ci95_hi": hi,
        "median_abs": float(np.median(r)), "mean_abs": float(r.mean()),
        "avg_win": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss": float(losses.mean()) if len(losses) else 0.0,
        "expectancy": float(r.mean()),          # R7: = hit*avg_win + (1-hit)*avg_loss
        "hit_xs": float((x > 0).mean()), "median_xs": float(np.median(x)),
        "mean_xs": float(x.mean()), "p10_abs": float(np.percentile(r, 10)),
        "median_days": float(np.median(d)), "cap_days": cap_days,
        "pnl_sum": float(r.sum()),
        "cap_eff": float(r.sum() / cap_days * TRADING_DAYS) if cap_days else float("nan"),
        "spy_pnl_sum": float(df["spy_ret"].sum()),
        "spy_cap_eff": (float(df["spy_ret"].sum() / cap_days * TRADING_DAYS)
                        if cap_days else float("nan")),
        "trunc_pct": float(df["trunc"].mean()),
    }


def hold_distribution(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"n": 0}
    d = df["days"].to_numpy()
    return {"n": int(len(d)), "min": int(d.min()), "p25": float(np.percentile(d, 25)),
            "median": float(np.median(d)), "p75": float(np.percentile(d, 75)),
            "p90": float(np.percentile(d, 90)), "max": int(d.max()),
            "mean": float(d.mean())}


def effective_clusters(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    iv = sorted(zip(df["entry_i"], df["exit_i_eff"]))
    clusters, cur_end = 1, iv[0][1]
    for a, b in iv[1:]:
        if a > cur_end:
            clusters += 1
            cur_end = b
        else:
            cur_end = max(cur_end, b)
    return clusters


# ---------------------------------------------------------------------------
# R9a: same-exposure random-entry Monte Carlo
# ---------------------------------------------------------------------------
def mc_random_entry(df: pd.DataFrame, px: dict, spy_pa: dict, lo_i: int, hi_i: int,
                    n_mc: int = N_MC, seed: int = SEED) -> dict:
    if df.empty:
        return {"n_trades": 0}
    rng = np.random.default_rng(seed)
    n = len(df)
    rets = np.full((n, n_mc), np.nan)
    xss = np.full((n, n_mc), np.nan)
    days = df["days"].to_numpy()

    for k, (_, t) in enumerate(df.iterrows()):
        pa = px[t["ticker"]]
        lo, hi = max(pa["first_i"], lo_i), min(pa["last_i"], hi_i)
        if hi <= lo:
            continue
        cand = np.arange(lo, hi + 1)
        cand = cand[np.isfinite(pa["raw"][cand])]
        if len(cand) == 0:
            continue
        draws = rng.choice(cand, size=n_mc, replace=True)
        D = int(t["days"])
        for j, i0 in enumerate(draws):
            r, _ = ret_between(pa, int(i0), int(i0) + D)
            if r is None:
                continue
            sr, _ = ret_between(spy_pa, int(i0), int(i0) + D)
            if sr is None:
                continue
            rets[k, j], xss[k, j] = r, r - sr

    act = stats(df)
    out = {"n_mc": n_mc, "n_trades": n}
    for name, mat, actual in (("abs", rets, act["median_abs"]),
                              ("xs", xss, act["median_xs"])):
        meds = np.nanmedian(mat, axis=0)
        out[f"null_median_{name}_mean"] = float(np.nanmean(meds))
        out[f"null_median_{name}_p95"] = float(np.nanpercentile(meds, 95))
        out[f"actual_median_{name}"] = float(actual)
        out[f"pctile_median_{name}"] = float((meds < actual).mean())
    # NaN cells = draws with no usable price. They must be EXCLUDED, not counted as
    # losses / zero-return: `rets > 0` reads NaN as False and `nansum/days.sum()` reads
    # NaN as 0 PnL while still charging its capital-days. Both would weaken the null and
    # flatter him. Denominators below count only valid draws.
    valid = np.isfinite(rets)
    nvalid = valid.sum(axis=0)
    out["null_valid_frac"] = float(valid.mean())
    hits = np.nansum(rets > 0, axis=0) / np.maximum(nvalid, 1)
    out.update({"null_hit_mean": float(np.nanmean(hits)),
                "null_hit_p95": float(np.nanpercentile(hits, 95)),
                "actual_hit": act["hit_abs"],
                "pctile_hit": float((hits < act["hit_abs"]).mean())})
    ce = (np.nansum(rets, axis=0)
          / np.maximum((valid * days[:, None]).sum(axis=0), 1) * TRADING_DAYS)
    out.update({"null_cap_eff_mean": float(np.nanmean(ce)),
                "null_cap_eff_p95": float(np.nanpercentile(ce, 95)),
                "actual_cap_eff": act["cap_eff"],
                "pctile_cap_eff": float((ce < act["cap_eff"]).mean())})
    return out


# ---------------------------------------------------------------------------
# R9c: naive fixed-hold control -- isolates the EXIT signal
# ---------------------------------------------------------------------------
def naive_fixed_hold(df: pd.DataFrame, px: dict, spy_pa: dict, hold_d: int) -> pd.DataFrame:
    rows = []
    for _, t in df.iterrows():
        pa = px[t["ticker"]]
        i0 = int(t["entry_i"])
        r, trunc = ret_between(pa, i0, i0 + hold_d)
        if r is None:
            continue
        sr, _ = ret_between(spy_pa, i0, i0 + hold_d)
        if sr is None:
            continue
        end = min(i0 + hold_d, pa["last_i"])
        rows.append({"ticker": t["ticker"], "entry_i": i0, "exit_i_eff": end,
                     "days": end - i0, "ret": r, "spy_ret": sr, "xs": r - sr,
                     "trunc": trunc, "year": t["year"], "basket": t["basket"]})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
def signals_from_llm(recs: list[dict], arm: str = "primary") -> list[dict]:
    close = set(CLOSE_ACTIONS)
    if arm == "exit_only":
        close = {"exit"}
    elif arm == "warning_exits":
        close = CLOSE_ACTIONS | {"warning"}
    out = []
    for r in recs:
        if r["action"] not in (OPEN_ACTIONS | close):
            continue
        ts = pd.Timestamp(r["ts"]).tz_convert("US/Eastern")
        out.append({"ticker": r["ticker"], "ts": str(ts), "date": str(ts.date()),
                    "action": r["action"], "conviction": r.get("conviction"),
                    "timeframe": r.get("timeframe"),
                    "is_index_call": r.get("is_index_call", False)})
    return out, close


def signals_from_keyword() -> list[dict]:
    """Rebuild the scorecard's episodes as entry/exit signals -- the A/B baseline."""
    blob = json.loads(CLAIMS.read_text(encoding="utf-8"))
    return [{"ticker": e["ticker"], "ts": e["ts"], "date": e["date"],
             "action": "entry" if e["dir"] == "bull" else "exit",
             "conviction": None, "timeframe": None,
             "is_index_call": e["ticker"] in INDEX_TICKERS}
            for e in blob["episodes"]]


def analyze_book(df: pd.DataFrame, px, spy_pa, lo_i, hi_i, label: str,
                 with_mc: bool = True) -> dict:
    rep = {"label": label}
    rep["stats"] = stats(df) | {"clusters": effective_clusters(df)}
    rep["hold"] = hold_distribution(df)
    mix = df["exit_type"].value_counts().to_dict()
    rep["exit_mix"] = {k: {"n": int(v), "pct": float(v / len(df))} for k, v in mix.items()}

    sig = df[df.exit_type == "signal"].reset_index(drop=True)
    ts_ = df[df.exit_type == "time_stop"].reset_index(drop=True)
    rep["signal_cohort"] = stats(sig) | {"clusters": effective_clusters(sig)}
    rep["timestop_cohort"] = stats(ts_) | {"clusters": effective_clusters(ts_)}
    rep["hold_signal"] = hold_distribution(sig)
    rep["hold_timestop"] = hold_distribution(ts_)

    # R5/R6: baskets -- his 75% / 85% claim
    rep["baskets"] = {}
    for b in ("stock", "index"):
        sub = df[df.basket == b].reset_index(drop=True)
        rep["baskets"][b] = stats(sub) | {"clusters": effective_clusters(sub)}
        s2 = sub[sub.exit_type == "signal"].reset_index(drop=True)
        rep["baskets"][b + "_signal_only"] = stats(s2)
    # sensitivity: LLM is_index_call flag
    if "is_index_call" in df.columns:
        for b, mask in (("index_llmflag", df.is_index_call.astype(bool)),
                        ("stock_llmflag", ~df.is_index_call.astype(bool))):
            rep["baskets"][b] = stats(df[mask].reset_index(drop=True))

    # R9c: naive fixed hold
    rep["naive"] = {}
    for tag, sub in (("all", df), ("signal", sig), ("stock", df[df.basket == "stock"]),
                     ("index", df[df.basket == "index"])):
        sub = sub.reset_index(drop=True)
        if sub.empty:
            continue
        hold_d = int(round(np.median(sub["days"].to_numpy()))) or 1
        nv = naive_fixed_hold(sub, px, spy_pa, hold_d)
        rep["naive"][tag] = stats(nv) | {"hold_d": hold_d}

    # R10: segments
    rep["by_year"] = {}
    for y in sorted(df["year"].unique()):
        sub = df[df.year == y].reset_index(drop=True)
        rep["by_year"][str(y)] = stats(sub) | {"clusters": effective_clusters(sub)}
    rep["by_conviction"] = {}
    for c in sorted({str(x) for x in df["conviction"].dropna().unique()}):
        sub = df[df.conviction == c].reset_index(drop=True)
        if len(sub) >= 10:
            rep["by_conviction"][c] = stats(sub)
    rep["by_timeframe"] = {}
    for c in sorted({str(x) for x in df["timeframe"].dropna().unique()}):
        sub = df[df.timeframe == c].reset_index(drop=True)
        if len(sub) >= 10:
            rep["by_timeframe"][c] = stats(sub)

    if with_mc:
        print(f"  MC {label} all ...", flush=True)
        rep["mc_all"] = mc_random_entry(df, px, spy_pa, lo_i, hi_i)
        print(f"  MC {label} signal-cohort ...", flush=True)
        rep["mc_signal"] = mc_random_entry(sig, px, spy_pa, lo_i, hi_i)
        for b in ("stock", "index"):
            sub = df[df.basket == b].reset_index(drop=True)
            if not sub.empty:
                print(f"  MC {label} {b} ...", flush=True)
                rep[f"mc_{b}"] = mc_random_entry(sub, px, spy_pa, lo_i, hi_i)
    return rep


def stage_analyze() -> None:
    blob = json.loads(LLM_CLAIMS.read_text(encoding="utf-8"))
    recs = blob["records"]
    tickers = sorted({r["ticker"] for r in recs}
                     | {e["ticker"] for e in
                        json.loads(CLAIMS.read_text(encoding="utf-8"))["episodes"]})
    spy_series = _px("SPY")
    cal = spy_series.index
    px = build_price_arrays(tickers + ["SPY"], cal)
    spy_pa = px["SPY"]
    print(f"priced {len(px) - 1}/{len(tickers)} tickers")

    rep: dict = {"meta": {"seed": SEED, "time_stop": TIME_STOP, "n_mc": N_MC,
                          "extraction_qa": blob["qa"]}}

    books = {}
    # --- LLM arm: primary + 2 sensitivity arms ---
    for arm in ("primary", "exit_only", "warning_exits"):
        sigs, close = signals_from_llm(recs, arm)
        tr = build_trades(sigs, cal, px, OPEN_ACTIONS, close)
        df = price_trades(tr, cal, px, spy_pa)
        books[f"llm_{arm}"] = df
        print(f"llm_{arm}: signals={len(sigs)} trades={len(tr)} priced={len(df)}")

    # --- keyword arm rebuilt on the SAME machinery (one-variable A/B) ---
    ksigs = signals_from_keyword()
    ktr = build_trades(ksigs, cal, px, {"entry"}, {"exit"})
    books["keyword"] = price_trades(ktr, cal, px, spy_pa)
    print(f"keyword: signals={len(ksigs)} trades={len(ktr)} priced={len(books['keyword'])}")

    lo_i = int(min(b["entry_i"].min() for b in books.values() if not b.empty))
    hi_i = int(max(b["entry_i"].max() for b in books.values() if not b.empty))
    rep["meta"]["corpus_entry_span"] = [str(cal[lo_i].date()), str(cal[hi_i].date())]

    for name, df in books.items():
        if df.empty:
            continue
        print(f"analyzing {name} (n={len(df)}) ...", flush=True)
        rep[name] = analyze_book(df, px, spy_pa, lo_i, hi_i, name,
                                 with_mc=name in ("llm_primary", "keyword"))

    # --- E1 demonstration: the OLD mirror on the SAME entries (fixed 126d hold) ---
    df = books["llm_primary"]
    entries = df.drop_duplicates(subset=["ticker", "entry_i"]).reset_index(drop=True)
    rep["old_mirror_126d"] = {}
    for h in (21, 63, 126):
        nv = naive_fixed_hold(entries, px, spy_pa, h)
        rep["old_mirror_126d"][f"h{h}"] = stats(nv)

    OUT.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {OUT}")

    for name in ("llm_primary", "keyword"):
        if name not in rep:
            continue
        a = rep[name]["stats"]
        h = rep[name]["hold"]
        print(f"\n=== {name} n={a['n']} clusters={a['clusters']}")
        print(f"  hit={a['hit_abs']:.1%} [{a['ci95_lo']:.1%},{a['ci95_hi']:.1%}] "
              f"med_abs={a['median_abs']:+.2%} exp={a['expectancy']:+.2%} "
              f"med_xs={a['median_xs']:+.2%}")
        print(f"  cap_eff={a['cap_eff']:+.1%} vs SPY_same_windows={a['spy_cap_eff']:+.1%}")
        print(f"  hold p25/med/p75/p90 = {h['p25']:.0f}/{h['median']:.0f}/"
              f"{h['p75']:.0f}/{h['p90']:.0f}  mix={rep[name]['exit_mix']}")
        for b in ("stock", "index"):
            s = rep[name]["baskets"][b]
            if s.get("n"):
                print(f"  {b}: n={s['n']} hit={s['hit_abs']:.1%} "
                      f"[{s['ci95_lo']:.1%},{s['ci95_hi']:.1%}] "
                      f"exp={s['expectancy']:+.2%} cap_eff={s['cap_eff']:+.1%}")
        if "mc_all" in rep[name]:
            m = rep[name]["mc_all"]
            print(f"  MC pctile: hit={m['pctile_hit']:.2f} "
                  f"med_abs={m['pctile_median_abs']:.2f} "
                  f"med_xs={m['pctile_median_xs']:.2f} cap_eff={m['pctile_cap_eff']:.2f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", action="store_true")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--analyze", action="store_true")
    a = ap.parse_args()
    if a.prep:
        stage_prep()
    if a.merge:
        stage_merge()
    if a.analyze:
        stage_analyze()


if __name__ == "__main__":
    main()
