"""exp_attendance_timing.py -- Is "analyst attendance collapses" a TIMING signal?

WHY THIS EXISTS
---------------
thesis/crowding_composite.py's docstring records a single striking observation, and it is the
ONLY empirical basis on which analyst-attendance was adopted as the crowding axis:

    "MU's 20-year LOW attendance quarter landed exactly at its 'dead cyclical' price bottom
     (2023-09-27, 4 analysts)"

Mechanism claimed: nobody can even be bothered to ask a question => attention capitulation =>
bottom. That observation has NEVER been tested as a timing signal. This script tests it, across
the whole corpus, with the controls that kill most such stories.

WHY IT IS WORTH TESTING (vs. the price-derived filters that already died): attendance is NOT a
function of price. RSI / momentum / valuation are all price transforms -- mutually contaminated
and universally known. Analyst attendance is ATTENTION data that Karst happens to have and most
do not. And unlike a from-scratch hypothesis it already has one validated point (MU 2023-09-27).

DESIGN FROZEN BEFORE ANY RETURN WAS COMPUTED (extraction rule, thresholds, horizons, control
grid, hit definition, segment cuts are all written here and were not tuned after seeing results).

MEASUREMENT DISCIPLINE (user instruction 2026-07-17)
---------------------------------------------------
* Primary metrics = CAPITAL EFFICIENCY (PnL / average exposure) AND ABSOLUTE PnL, side by side.
* The word "alpha" is NOT used as a verdict at the signal/sleeve layer -- a single signal has no
  benchmark to speak of. SPY is reported as a BENCHMARK, never as "alpha".
* Capital efficiency has two known failure modes (memory: capital-efficiency-two-traps):
    (a) a small denominator inflates the ratio;
    (b) on a LOSING book the ranking INVERTS (hold longer -> the ratio looks better).
  => every CapEff table below carries an absolute-PnL column, and CapEff is NEVER used to rank
  arms when any arm has negative PnL. `capeff_rank_safe()` enforces this in code.

DATA
----
* Attendance   : thesis/crowding_composite.py's attendance_series() imported VERBATIM (not
                 reimplemented) -- it already carries the 2026-07-17 D1 fix (NON_ANALYST_CALL_DOCS
                 excludes 6 non-earnings-call ASML docs; `failed_*` prefix handling).
                 NOTE: the module's CORPUS_DB constant resolves to thesis/corpus.db (11.5 GB,
                 195,957 transcripts / 5,339 tickers). The task brief said thesis/.raw/corpus.db,
                 but that path is a 0-byte placeholder; we use the same DB the live module uses.
* Prices       : yfinance adjusted closes (auto_adjust=True, period="max") -- IDENTICAL vendor and
                 adjustment to backtest/data.py load(symbol, adjusted=True), which is what that
                 function does internally. We batch the download (yf.download accepts a list)
                 because the universe is ~4.2k symbols and per-symbol load() would take ~70 min vs
                 ~9 min batched. equivalence_check() below verifies, on a sample, that the batched
                 frame matches load(..., adjusted=True) exactly, so the deviation is throughput
                 only, not semantics. Adjusted closes are REQUIRED here: horizons run to 252d.
* Sector       : thesis/.raw/ticker_sector_cache.json (covers all 5,339 corpus tickers).
* Size         : point-in-time median dollar volume over the prior 63d, computed from the price
                 data itself. NOT backtest/.insider_data/mktcap_defeatbeta.pkl -- that cache covers
                 only 47% of the universe and is missing BOTH MU and TSM (the two named case
                 studies), so it cannot carry the size cut. Dollar volume is point-in-time (no
                 look-ahead), available for 100% of the priced universe, and is the axis the
                 concern is actually about (neglected / illiquid names).

Intermediate caches are written OUTSIDE the repo (scratchpad; override with KARST_ATT_CACHE) --
this task is allowed to add exactly two repo files (this script + its results .md).

Run: PYTHONUTF8=1 python backtest/experiments/exp_attendance_timing.py
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import random
import sqlite3
import sys
from datetime import datetime, timezone

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# VERBATIM import -- do not reimplement (carries the 2026-07-17 D1 fixes).
from thesis.crowding_composite import (  # noqa: E402
    CORPUS_DB,
    GENERIC_TAGS,
    MIN_QUARTERS,
    attendance_series,
)

SECTOR_CACHE = os.path.join(REPO_ROOT, "thesis", ".raw", "ticker_sector_cache.json")
CACHE_DIR = os.environ.get(
    "KARST_ATT_CACHE",
    os.path.join(
        os.environ.get("TEMP", "/tmp"), "claude", "C--projects-Investment-karst",
        "f26b2e5c-22b5-49fe-9cf6-81e08b44ffaa", "scratchpad", "attendance_timing",
    ),
)
os.makedirs(CACHE_DIR, exist_ok=True)

# ============================== FROZEN DESIGN CONSTANTS ==============================
# (written before any forward return was inspected; not tuned afterwards)

LOW_THRESHOLDS = (5.0, 10.0, 20.0)   # "own-history low" percentile cutoffs (<=)
HIGH_THRESHOLD = 90.0                # inverse test: "own-history high" (>=)
HORIZONS = (63, 126, 252)            # trading days -- attention-capitulation -> recovery scale
BENCHMARK = "SPY"

# momentum-confound control grid -- bin edges frozen here, before any return was seen.
# Mirrors backtest/results/2026-07-17_kol_bear_confound.md's method (8 x 5 = 40 cells).
MOM63_BINS = [-np.inf, -0.30, -0.20, -0.10, 0.0, 0.10, 0.20, 0.40, np.inf]
OFFHIGH_BINS = [-0.001, 0.05, 0.10, 0.20, 0.40, np.inf]   # distance BELOW 52wk high, positive
N_CONTROLS = 20                      # controls sampled per event
N_MC = 1000                          # random same-exposure Monte-Carlo iterations
SEED = 20260717

ERA_SPLIT = pd.Timestamp("2021-01-01")
ERA_START = pd.Timestamp("2016-01-01")   # brief's segment window: 2016-2020 vs 2021+
TRADING_DAYS_YR = 252

rng = np.random.default_rng(SEED)
random.seed(SEED)


# ============================== metrics ==============================

def capeff_annualized(rets: np.ndarray, days: int) -> float:
    """Capital efficiency = PnL / exposure, annualized.

    Each event is $1 of notional held `days` trading days. Exposure = sum of dollar-days.
    CapEff = sum(PnL) / sum(dollar-days) * 252  ->  "return per dollar-YEAR of exposure".
    Comparable across horizons (a 63d hold earning 5% is more capital-efficient than a 252d
    hold earning 5%) -- which is exactly why it must be read next to absolute PnL (trap b:
    on a losing book, a LONGER hold makes this ratio look BETTER).
    """
    if len(rets) == 0:
        return float("nan")
    return float(np.sum(rets) / (len(rets) * days) * TRADING_DAYS_YR)


def arm_stats(rets: np.ndarray, days: int) -> dict:
    rets = np.asarray(rets, dtype=float)
    rets = rets[~np.isnan(rets)]
    if len(rets) == 0:
        return {"n": 0}
    return {
        "n": int(len(rets)),
        "hit": float(np.mean(rets > 0) * 100),
        "median": float(np.median(rets) * 100),
        "mean": float(np.mean(rets) * 100),
        "p10": float(np.percentile(rets, 10) * 100),
        "pnl_abs": float(np.sum(rets)),            # total return points on $1/event
        "pnl_per_event": float(np.mean(rets) * 100),
        "capeff": float(capeff_annualized(rets, days) * 100),
    }


def capeff_rank_safe(arms: dict) -> bool:
    """Trap (b) guard: CapEff may only be used to RANK arms when every arm has positive PnL."""
    return all(a.get("pnl_abs", 0) > 0 for a in arms.values() if a.get("n", 0) > 0)


def effective_sample(entries: list[pd.Timestamp], days: int) -> int:
    """Crude independence probe: merge overlapping [entry, entry+days] windows (pooled across
    tickers, same method as the kol_bear_confound report) and count connected components."""
    if not entries:
        return 0
    iv = sorted((e, e + pd.Timedelta(days=int(days * 1.45))) for e in entries)
    clusters, cur_end = 1, iv[0][1]
    for s, e in iv[1:]:
        if s > cur_end:
            clusters += 1
            cur_end = e
        else:
            cur_end = max(cur_end, e)
    return clusters


# ============================== stage 1: attendance ==============================

def build_universe(con) -> list[str]:
    rows = con.execute(
        "SELECT primary_ticker, COUNT(*) c FROM docs WHERE thesistype='transcript' "
        "AND primary_ticker IS NOT NULL AND primary_ticker != '' GROUP BY 1 HAVING c >= ?",
        (MIN_QUARTERS,),
    ).fetchall()
    return sorted(r[0] for r in rows)


def stage1_attendance(force: bool = False) -> pd.DataFrame:
    """Parse every universe ticker's attendance history via the imported extractor."""
    cache = os.path.join(CACHE_DIR, "attendance.parquet")
    if os.path.exists(cache) and not force:
        return pd.read_parquet(cache)
    con = sqlite3.connect(f"file:{CORPUS_DB}?mode=ro", uri=True)
    uni = build_universe(con)
    print(f"[stage1] universe (>= {MIN_QUARTERS} transcripts in corpus.db): {len(uni)} tickers")
    frames = []
    for i, t in enumerate(uni):
        if i % 250 == 0:
            print(f"[stage1]   parsing {i}/{len(uni)} ...", flush=True)
        try:
            df = attendance_series(con, t)
        except Exception as e:
            print(f"[stage1]   {t} FAILED: {type(e).__name__}: {str(e)[:60]}")
            continue
        if not df.empty:
            frames.append(df)
    con.close()
    out = pd.concat(frames, ignore_index=True)
    out.to_parquet(cache, index=False)
    print(f"[stage1] parsed {len(out)} transcripts -> {cache}")
    return out


def stage1b_signal(att: pd.DataFrame) -> pd.DataFrame:
    """Expanding-window own-history percentile -- NO LOOK-AHEAD.

    thesis/crowding_composite.ticker_attendance_pctile() ranks the LATEST quarter against the
    ticker's FULL history: correct for a live snapshot, but using it in a backtest would let a
    2016 event 'know' 2026 attendance. We use the SAME estimator -- (hist <= x).mean()*100 --
    restricted to quarters available AT THAT TIME (expanding), requiring >= MIN_QUARTERS
    observations (incl. the current one) before a quarter is eligible, mirroring the module's
    MIN_QUARTERS gate. The full-sample (look-ahead) variant is reported as a sensitivity only.

    TIE HANDLING: analyst counts are small integers, so ties are common. `<=` puts a tied group
    at the TOP of its own range (max-rank convention) -- this makes the percentile HIGHER and
    therefore triggers FEWER events. Conservative, and identical to the live module's convention.
    """
    ok = att[~att["method"].str.startswith("failed")].copy()
    ok["published"] = pd.to_datetime(ok["published"])
    ok = ok.sort_values(["ticker", "published"]).reset_index(drop=True)
    rows = []
    for t, g in ok.groupby("ticker", sort=False):
        n = g["n_analysts"].to_numpy()
        pub = g["published"].to_numpy()
        for i in range(len(g)):
            if i + 1 < MIN_QUARTERS:      # need >= MIN_QUARTERS observations incl. current
                continue
            hist = n[: i + 1]
            pct_exp = float((hist <= n[i]).mean() * 100.0)
            pct_full = float((n <= n[i]).mean() * 100.0)
            rows.append({"ticker": t, "published": pub[i], "n_analysts": int(n[i]),
                         "pctile_expanding": pct_exp, "pctile_fullsample": pct_full,
                         "quarter_idx": i + 1, "n_hist": int(i + 1)})
    return pd.DataFrame(rows)


# ============================== stage 1c: parse health ==============================

def stage1c_parse_health(force: bool = False) -> pd.DataFrame:
    """Per-transcript parse-health probe -- added AFTER the main run, because the TSM case study
    exposed a systematic extractor failure that the null result could otherwise be blamed on.

    THE BUG (demonstrated on transcript-TSM-2018-07-19): TSMC hosts an IN-ROOM Q&A relayed by
    Elizabeth Sun (Corp Comms) and only LATER lets the phone Operator open the line. _qa_boundary()
    locates the Q&A by the Operator's "first question" phrase, which in that transcript sits at
    speaker turn 180 of 196 -- so the ~11 analysts who already asked in-room (Bill Lu, Charlie Chan,
    Randy Abrams, Roland Shu, Sebastian Hou, Steven Pelayo, Michael Chou, Donald Lu, Douglas Smith,
    Gokul, William Lu) land in `pre_roster` and are EXCLUDED as prepared-remarks speakers. Reported
    attendance = 1; true attendance ~= 12. The doc is NOT truncated (it ends with the normal
    sign-off), so this is a parser failure, not a data gap.

    HEALTH METRIC: qa_share = (n_turns - boundary_idx) / n_turns. A genuine Q&A is a large share of
    an earnings call's turns (typically 40-60%). qa_share < QA_SHARE_MIN means the located "Q&A" is
    a sliver at the very end of the document -> the boundary almost certainly landed too late and
    the count is an undercount. Threshold set at 0.15 on structural grounds (a Q&A cannot plausibly
    be under 15% of turns) BEFORE looking at any return of the healthy subset.
    """
    cache = os.path.join(CACHE_DIR, "parse_health.parquet")
    if os.path.exists(cache) and not force:
        return pd.read_parquet(cache)
    from thesis.crowding_composite import (_clean_name, _dialogue_speakers_ordered,
                                            _extract_header_block, _qa_boundary, extract_analysts)
    con = sqlite3.connect(f"file:{CORPUS_DB}?mode=ro", uri=True)
    uni = build_universe(con)
    rows = []
    for i, t in enumerate(uni):
        if i % 500 == 0:
            print(f"[stage1c]   {i}/{len(uni)} ...", flush=True)
        for did, slug, pub in con.execute(
            "SELECT d.id, d.slug, d.published FROM docs d WHERE d.thesistype='transcript' "
            "AND d.primary_ticker=? ORDER BY d.published", (t,)
        ).fetchall():
            r = con.execute("SELECT body FROM docs_fts_en WHERE rowid=?", (did,)).fetchone()
            body = r[0] if r else ""
            if not body:
                continue
            sp = _dialogue_speakers_ordered(body)
            b, tag = _qa_boundary(sp)
            n_turns = len(sp)
            qa_share = float("nan") if (b is None or n_turns == 0) else (n_turns - b) / n_turns
            # UPPER BOUND on true attendance: every distinct speaker tag in the whole document,
            # minus the header-block Executives and the operator. This is format-agnostic -- it does
            # NOT depend on locating the Q&A boundary, so it survives the TSMC two-stage-Q&A bug
            # that defeats qa_share. reported/upper_bound << 1 => the boundary logic dropped real
            # questioners (they spoke before the boundary and were excluded as prepared remarks).
            tags = {_clean_name(x) for x, _ in sp}
            execs = _extract_header_block(body, "Executives") or set()
            execs = {_clean_name(e) for e in execs}
            nonexec = {x for x in tags
                       if x and x != tag and x not in execs and x.lower() not in GENERIC_TAGS}
            names, _m = extract_analysts(body)
            ub = len(nonexec)
            rows.append({"ticker": t, "slug": slug, "published": pub, "n_turns": n_turns,
                         "boundary_idx": -1 if b is None else int(b), "qa_share": qa_share,
                         "n_analysts": len(names), "upper_bound": ub,
                         "parse_ratio": (len(names) / ub) if ub > 0 else float("nan")})
    con.close()
    out = pd.DataFrame(rows)
    out.to_parquet(cache, index=False)
    print(f"[stage1c] parse-health computed for {len(out)} transcripts -> {cache}")
    return out


QA_SHARE_MIN = 0.15      # extreme-form screen only -- shown INADEQUATE, see below
PARSE_RATIO_MIN = 0.50   # keep a quarter only if the extractor found >= half the plausible
# questioners. Set on STRUCTURAL grounds (an extractor that finds under half the non-exec speakers
# in the room has demonstrably failed) and fixed BEFORE any return of the clean subset was looked
# at -- it is a data-quality gate, not a performance knob.
#
# WHY parse_ratio AND NOT qa_share: qa_share was written first, to catch the TSM-2018-07-19 shape
# (Q&A boundary landing at turn 180 of 196). It flags only 0.3-0.5% of events and it MISSES the very
# bug it was built for -- TSM 2019-10-17 scores a healthy qa_share=0.523 yet still reports 1 analyst
# across a 113-turn Q&A, which is structurally impossible. Root cause: `exclude = pre_roster | ...`
# drops every speaker who appeared before the boundary, and TSMC's analysts ask in BOTH the in-room
# and the phone Q&A, so they are excluded even when they speak again after the boundary. parse_ratio
# compares the reported count against a boundary-independent upper bound (distinct non-exec speaker
# tags anywhere in the doc) and therefore survives that failure mode.
#
# MEASURED CONTAMINATION (share of quarters with parse_ratio < 0.5, by reported count):
#   n=1 -> 88.5% | n=2 -> 58.8% | n=3 -> 17.3% | n=5-8 -> 0.27% | n>12 -> 0.01%
# The misparse rate is MONOTONE in the reported count: the lower the reading, the likelier it is
# an extractor failure. That is fatal for a signal defined as "the lowest readings in own history"
# -- the tail the signal selects on is the tail the parser corrupts. Hence the clean rebuild below.


# ============================== stage 2: prices ==============================

def stage2_prices(tickers: list[str], force: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Batched yfinance adjusted closes + volume. Returns (close, dollar_volume) matrices."""
    cache_c = os.path.join(CACHE_DIR, "close.parquet")
    cache_v = os.path.join(CACHE_DIR, "dvol.parquet")
    if os.path.exists(cache_c) and os.path.exists(cache_v) and not force:
        return pd.read_parquet(cache_c), pd.read_parquet(cache_v)
    import yfinance as yf
    syms = sorted(set(tickers) | {BENCHMARK})
    print(f"[stage2] downloading {len(syms)} symbols (yfinance, auto_adjust=True, period=max)")
    closes, dvols = [], []
    CH = 60
    for i in range(0, len(syms), CH):
        chunk = syms[i: i + CH]
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                df = yf.download(chunk, period="max", auto_adjust=True, progress=False,
                                 threads=True, group_by="column")
        except Exception as e:
            print(f"[stage2]   chunk {i} FAILED: {type(e).__name__}: {str(e)[:60]}")
            continue
        if df is None or len(df) == 0:
            continue
        try:
            c = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df[["Close"]]
            v = df["Volume"] if isinstance(df.columns, pd.MultiIndex) else df[["Volume"]]
            if not isinstance(df.columns, pd.MultiIndex):
                c.columns, v.columns = [chunk[0]], [chunk[0]]
        except KeyError:
            continue
        closes.append(c.astype("float32"))
        dvols.append((c * v).astype("float32"))
        if (i // CH) % 10 == 0:
            print(f"[stage2]   {i}/{len(syms)} ...", flush=True)
    close = pd.concat(closes, axis=1).sort_index()
    dvol = pd.concat(dvols, axis=1).sort_index()
    close = close.loc[:, ~close.columns.duplicated()]
    dvol = dvol.loc[:, ~dvol.columns.duplicated()]
    close.index = pd.to_datetime(close.index).tz_localize(None)
    dvol.index = pd.to_datetime(dvol.index).tz_localize(None)
    close = close.dropna(axis=1, how="all")
    dvol = dvol[close.columns]
    close.to_parquet(cache_c)
    dvol.to_parquet(cache_v)
    print(f"[stage2] priced {close.shape[1]} symbols, {close.shape[0]} days -> {cache_c}")
    return close, dvol


def equivalence_check(close: pd.DataFrame) -> list[str]:
    """Prove the batched download == backtest/data.py load(sym, adjusted=True) on a sample."""
    from backtest.data import load
    out = []
    for sym in ["MU", "TSM", "SPY"]:
        try:
            ref = load(sym, adjusted=True)["close"]
            mine = close[sym].dropna()
            j = pd.concat([ref.rename("ref"), mine.rename("mine")], axis=1).dropna()
            if len(j) == 0:
                out.append(f"{sym}: NO OVERLAP")
                continue
            d = (j["ref"] - j["mine"]).abs() / j["ref"].abs()
            out.append(f"{sym}: n={len(j)} max_rel_diff={d.max():.2e} "
                       f"{'MATCH' if d.max() < 1e-3 else 'MISMATCH'}")
        except Exception as e:
            out.append(f"{sym}: check failed {type(e).__name__}: {str(e)[:50]}")
    return out


# ============================== stage 3: event assembly ==============================

def build_matrices(close: pd.DataFrame):
    mom63 = close / close.shift(63) - 1.0
    hi252 = close.rolling(252, min_periods=200).max()
    offhigh = 1.0 - close / hi252              # distance BELOW 52wk high, positive
    fwd = {h: close.shift(-h) / close - 1.0 for h in HORIZONS}
    return mom63, offhigh, fwd


def assemble_events(sig: pd.DataFrame, close: pd.DataFrame, dvol: pd.DataFrame,
                    mom63: pd.DataFrame, offhigh: pd.DataFrame, fwd: dict) -> pd.DataFrame:
    """Entry = FIRST TRADING DAY STRICTLY AFTER the transcript's `published` date, at the close.

    `published` in corpus.db is the CALL date itself (verified: MU 2023-09-27 == MU's FQ4-23
    call), and calls land outside/after the session, so next-session close is a tradeable,
    look-ahead-free entry. We deliberately do NOT use the fiscal quarter-end date, which would
    embed the filing lag and be look-ahead.
    """
    idx = close.index
    cols = set(close.columns)
    dvol63 = dvol.rolling(63, min_periods=40).median()
    recs = []
    for r in sig.itertuples(index=False):
        t = r.ticker
        if t not in cols:
            continue
        pub = pd.Timestamp(r.published)
        pos = idx.searchsorted(pub, side="right")     # strictly AFTER published
        if pos >= len(idx):
            continue
        entry_date = idx[pos]
        px = close[t]
        if not np.isfinite(px.iat[pos]):
            nxt = px.iloc[pos:pos + 5].first_valid_index()
            if nxt is None:
                continue
            pos = idx.get_loc(nxt)
            entry_date = idx[pos]
        rec = {"ticker": t, "published": pub, "entry_date": entry_date, "entry_pos": pos,
               "n_analysts": r.n_analysts, "pctile_expanding": r.pctile_expanding,
               "pctile_fullsample": r.pctile_fullsample, "n_hist": r.n_hist,
               "mom63": float(mom63[t].iat[pos]) if pos < len(idx) else np.nan,
               "offhigh": float(offhigh[t].iat[pos]) if pos < len(idx) else np.nan,
               "dvol63": float(dvol63[t].iat[pos]) if pos < len(idx) else np.nan}
        for h in HORIZONS:
            rec[f"fwd{h}"] = float(fwd[h][t].iat[pos])
            b = fwd[h][BENCHMARK]
            rec[f"spy{h}"] = float(b.iat[pos]) if pos < len(b) else np.nan
        recs.append(rec)
    return pd.DataFrame(recs)


# ============================== stage 4: controls ==============================

def mc_same_exposure(events: pd.DataFrame, fwd: dict, h: int, n_mc: int = N_MC) -> dict:
    """Control (a): same ticker, same number of holding days, RANDOM entry. n_mc synthetic event
    sets of identical size/ticker-mix/horizon. Answers: is this just the stock's own drift?"""
    f = fwd[h]
    pools = {}
    for t in events["ticker"].unique():
        if t in f.columns:
            v = f[t].to_numpy()
            v = v[np.isfinite(v)]
            if len(v) > 0:
                pools[t] = v
    ev = events[events["ticker"].isin(pools)]
    if len(ev) == 0:
        return {}
    tick = ev["ticker"].to_numpy()
    actual = arm_stats(ev[f"fwd{h}"].to_numpy(), h)
    # vectorized: build an (n_mc x n_events) draw matrix, ticker-block at a time, so every event
    # is resampled ONLY from its own ticker's return distribution (same-exposure by construction).
    draws = np.empty((n_mc, len(ev)), dtype=float)
    for t in np.unique(tick):
        cols = np.flatnonzero(tick == t)
        pool = pools[t]
        draws[:, cols] = pool[rng.integers(0, len(pool), size=(n_mc, len(cols)))]
    med = np.median(draws, axis=1) * 100
    mean_ = np.mean(draws, axis=1) * 100
    cap = np.sum(draws, axis=1) / (len(ev) * h) * TRADING_DAYS_YR * 100
    return {
        "actual_median": actual["median"], "actual_capeff": actual["capeff"],
        "actual_mean": actual["mean"],
        "mc_median_mean": float(med.mean()), "mc_capeff_mean": float(cap.mean()),
        "mc_mean_mean": float(mean_.mean()),
        "p_median": float(np.mean(med >= actual["median"])),
        "p_capeff": float(np.mean(cap >= actual["capeff"])),
        "p_mean": float(np.mean(mean_ >= actual["mean"])),
        "mc_median_p95": float(np.percentile(med, 95)),
        "mc_capeff_p95": float(np.percentile(cap, 95)),
        "n_mc": n_mc,
    }


def momentum_matched(events: pd.DataFrame, close: pd.DataFrame, mom63: pd.DataFrame,
                     offhigh: pd.DataFrame, fwd: dict, h: int) -> dict:
    """Control (b) -- THE decisive one. "Analysts stopped showing up" almost certainly overlaps
    with "the stock has already fallen a lot". Same trap as the kol_bear_confound report.

    For each event: on the SAME DAY, sample up to 20 other universe names sitting in the SAME
    (mom63 x offhigh) grid cell, and rank the event's own forward return inside that control set.
    Median percentile 0.500 == the theoretical value for NO edge.

    NOTE (contamination, honestly stated): controls are NOT screened for having their own
    low-attendance event nearby. That biases the test TOWARD the null (some controls carry the
    signal), i.e. it is conservative, not flattering.
    """
    f = fwd[h]
    m_np = mom63.to_numpy()
    o_np = offhigh.to_numpy()
    f_np = f.to_numpy()
    colpos = {c: i for i, c in enumerate(close.columns)}
    mb = np.digitize(m_np, MOM63_BINS)
    ob = np.digitize(o_np, OFFHIGH_BINS)
    pcts, filled, n_drawn = [], [], []
    for r in events.itertuples(index=False):
        if not np.isfinite(r.mom63) or not np.isfinite(r.offhigh) or not np.isfinite(getattr(r, f"fwd{h}")):
            continue
        p = r.entry_pos
        ti = colpos.get(r.ticker)
        if ti is None:
            continue
        my_mb, my_ob = mb[p, ti], ob[p, ti]
        row_ok = (mb[p] == my_mb) & (ob[p] == my_ob) & np.isfinite(f_np[p])
        row_ok[ti] = False
        cand = np.flatnonzero(row_ok)
        if len(cand) == 0:
            continue
        if len(cand) > N_CONTROLS:
            cand = rng.choice(cand, N_CONTROLS, replace=False)
        cr = f_np[p, cand]
        mine = getattr(r, f"fwd{h}")
        pcts.append(float(np.mean(cr < mine)))
        filled.append(len(cand) >= N_CONTROLS)
        n_drawn.append(len(cand))
    if not pcts:
        return {}
    pcts = np.array(pcts)
    return {
        "n_events": int(len(pcts)),
        "median_pctile": float(np.median(pcts)),
        "mean_pctile": float(np.mean(pcts)),
        "share_gt_p75": float(np.mean(pcts > 0.75) * 100),
        "share_p25_p75": float(np.mean((pcts >= 0.25) & (pcts <= 0.75)) * 100),
        "share_lt_p25": float(np.mean(pcts < 0.25) * 100),
        "fill_rate": float(np.mean(filled) * 100),
        "avg_controls": float(np.mean(n_drawn)),
        "total_controls": int(np.sum(n_drawn)),
    }


# ============================== reporting helpers ==============================

def fmt_arm(a: dict) -> str:
    if not a or a.get("n", 0) == 0:
        return "n=0"
    return (f"n={a['n']:>4}  hit={a['hit']:>5.1f}%  med={a['median']:>+6.2f}%  "
            f"mean={a['mean']:>+6.2f}%  p10={a['p10']:>+7.2f}%  "
            f"PnL={a['pnl_abs']:>+8.1f}  CapEff={a['capeff']:>+6.1f}%/yr")


def case_study(events_all: pd.DataFrame, ticker: str, att: pd.DataFrame) -> pd.DataFrame:
    e = events_all[events_all["ticker"] == ticker].copy()
    return e.sort_values("pctile_expanding")


# ============================== main ==============================

def run():
    t_start = datetime.now()
    print("=" * 100)
    print("exp_attendance_timing -- is 'analyst attendance collapse' a timing signal?")
    print(f"CORPUS_DB = {CORPUS_DB}")
    print(f"CACHE_DIR = {CACHE_DIR}")
    print("=" * 100)

    att = stage1_attendance()
    n_parsed_ok = int((~att["method"].str.startswith("failed")).sum())
    print(f"\n[stage1] transcripts={len(att)}  parsed_ok={n_parsed_ok} "
          f"({n_parsed_ok/len(att)*100:.1f}%)  tickers={att['ticker'].nunique()}")
    print("[stage1] parse-method mix:")
    print(att["method"].value_counts().to_string())

    sig = stage1b_signal(att)
    print(f"\n[stage1b] signal-eligible quarters (>= {MIN_QUARTERS} own history): {len(sig)} "
          f"across {sig['ticker'].nunique()} tickers")

    tickers = sorted(sig["ticker"].unique())
    close, dvol = stage2_prices(tickers)
    priced = [t for t in tickers if t in close.columns]
    print(f"[stage2] priced {len(priced)}/{len(tickers)} signal-eligible tickers "
          f"({len(priced)/len(tickers)*100:.1f}%)")

    print("\n[stage2b] equivalence vs backtest/data.py load(adjusted=True):")
    for line in equivalence_check(close):
        print("   ", line)

    mom63, offhigh, fwd = build_matrices(close)
    events_all = assemble_events(sig[sig["ticker"].isin(priced)], close, dvol, mom63, offhigh, fwd)
    print(f"\n[stage3] events assembled: {len(events_all)} "
          f"({events_all['ticker'].nunique()} tickers)")
    for h in HORIZONS:
        print(f"          fwd{h} available: {int(events_all[f'fwd{h}'].notna().sum())}")

    sectors = {}
    if os.path.exists(SECTOR_CACHE):
        with open(SECTOR_CACHE, encoding="utf-8") as fh:
            sectors = json.load(fh)
    events_all["sector"] = events_all["ticker"].map(sectors).fillna("Unknown")
    events_all["is_tech"] = events_all["sector"].eq("Technology")

    results = {"generated_at": datetime.now(timezone.utc).isoformat()}

    # ---------- case studies (MU = the original observation, TSM = user asked by name) ----------
    print("\n" + "=" * 100)
    print("CASE STUDIES")
    print("=" * 100)
    case = {}
    for t in ["MU", "TSM"]:
        e = case_study(events_all, t, att)
        print(f"\n--- {t}: {len(e)} signal-eligible quarters, "
              f"attendance range {e['n_analysts'].min()}-{e['n_analysts'].max()} ---")
        show = e.head(6)[["published", "n_analysts", "pctile_expanding", "fwd63", "fwd126",
                          "fwd252", "spy252"]]
        print(show.to_string(index=False))
        case[t] = e.to_dict("records")
    results["case_studies"] = {k: [
        {kk: (str(vv) if isinstance(vv, pd.Timestamp) else vv) for kk, vv in r.items()}
        for r in v] for k, v in case.items()}

    # ---------- main grid ----------
    print("\n" + "=" * 100)
    print("MAIN GRID -- low-attendance events (expanding, no look-ahead)")
    print("=" * 100)
    grid = {}
    for thr in LOW_THRESHOLDS:
        ev = events_all[events_all["pctile_expanding"] <= thr]
        print(f"\n### attendance <= {thr:.0f}th pctile: {len(ev)} events, "
              f"{ev['ticker'].nunique()} tickers")
        for h in HORIZONS:
            sub = ev[ev[f"fwd{h}"].notna()]
            a = arm_stats(sub[f"fwd{h}"].to_numpy(), h)
            b = arm_stats(sub[f"spy{h}"].to_numpy(), h)
            eff = effective_sample(list(sub["entry_date"]), h)
            print(f"  h={h:>3}d  EVENT  {fmt_arm(a)}")
            print(f"          SPY    {fmt_arm(b)}   [benchmark, NOT alpha]")
            print(f"          eff_sample_clusters={eff}  freq={len(sub)/max(1,(sub['entry_date'].max()-sub['entry_date'].min()).days/365.25):.0f}/yr")
            grid[f"{thr}_{h}"] = {"event": a, "spy": b, "eff_clusters": eff}
    results["main_grid"] = grid

    # ---------- inverse test ----------
    print("\n" + "=" * 100)
    print(f"INVERSE TEST -- attendance >= {HIGH_THRESHOLD:.0f}th pctile (if low=bottom, high should=top)")
    print("=" * 100)
    inv = {}
    evh = events_all[events_all["pctile_expanding"] >= HIGH_THRESHOLD]
    print(f"{len(evh)} events, {evh['ticker'].nunique()} tickers")
    for h in HORIZONS:
        sub = evh[evh[f"fwd{h}"].notna()]
        a = arm_stats(sub[f"fwd{h}"].to_numpy(), h)
        b = arm_stats(sub[f"spy{h}"].to_numpy(), h)
        print(f"  h={h:>3}d  HIGH-ATT {fmt_arm(a)}")
        print(f"          SPY      {fmt_arm(b)}   [benchmark, NOT alpha]")
        inv[str(h)] = {"event": a, "spy": b}
    results["inverse_test"] = inv

    # ---------- control (a): random same-exposure MC ----------
    print("\n" + "=" * 100)
    print(f"CONTROL (a) -- random same-exposure Monte-Carlo ({N_MC} draws, same ticker/days)")
    print("=" * 100)
    mc = {}
    for thr in LOW_THRESHOLDS:
        ev = events_all[events_all["pctile_expanding"] <= thr]
        for h in HORIZONS:
            sub = ev[ev[f"fwd{h}"].notna()]
            if len(sub) < 5:
                continue
            m = mc_same_exposure(sub, fwd, h)
            if not m:
                continue
            mc[f"{thr}_{h}"] = m
            print(f"  thr<={thr:>4.0f} h={h:>3}d  actual_med={m['actual_median']:>+6.2f}% vs "
                  f"MC_med={m['mc_median_mean']:>+6.2f}% (p={m['p_median']:.3f})   "
                  f"actual_CapEff={m['actual_capeff']:>+6.1f}%/yr vs MC={m['mc_capeff_mean']:>+6.1f}%/yr "
                  f"(p={m['p_capeff']:.3f})")
    results["control_mc"] = mc

    # ---------- control (b): momentum-matched ----------
    print("\n" + "=" * 100)
    print("CONTROL (b) -- momentum/off-high matched, 20 same-day controls (THE decisive test)")
    print("median percentile 0.500 == no edge")
    print("=" * 100)
    mm = {}
    for thr in LOW_THRESHOLDS:
        ev = events_all[events_all["pctile_expanding"] <= thr]
        for h in HORIZONS:
            sub = ev[ev[f"fwd{h}"].notna()]
            if len(sub) < 5:
                continue
            m = momentum_matched(sub, close, mom63, offhigh, fwd, h)
            if not m:
                continue
            mm[f"{thr}_{h}"] = m
            print(f"  thr<={thr:>4.0f} h={h:>3}d  n={m['n_events']:>4}  "
                  f"median_pctile={m['median_pctile']:.3f}  mean={m['mean_pctile']:.3f}  "
                  f">p75={m['share_gt_p75']:>4.1f}%  <p25={m['share_lt_p25']:>4.1f}%  "
                  f"fill={m['fill_rate']:>5.1f}%  avg_ctrl={m['avg_controls']:.1f}")
    results["control_momentum"] = mm

    # ---------- segments ----------
    print("\n" + "=" * 100)
    print("SEGMENTS (threshold <= 10th pctile)")
    print("=" * 100)
    seg = {}
    ev10 = events_all[events_all["pctile_expanding"] <= 10.0]
    segdefs = {
        "2016-2020": lambda d: (d["entry_date"] >= ERA_START) & (d["entry_date"] < ERA_SPLIT),
        "2021+": lambda d: d["entry_date"] >= ERA_SPLIT,
        "pre-2016": lambda d: d["entry_date"] < ERA_START,
        "tech": lambda d: d["is_tech"],
        "non-tech": lambda d: ~d["is_tech"],
    }
    q = ev10["dvol63"].quantile([1 / 3, 2 / 3])
    segdefs["size:large(top tercile $vol)"] = lambda d: d["dvol63"] >= q.iloc[1]
    segdefs["size:small(bottom tercile $vol)"] = lambda d: d["dvol63"] <= q.iloc[0]
    for name, fn in segdefs.items():
        sub_all = ev10[fn(ev10)]
        line = {}
        print(f"\n--- {name}: n={len(sub_all)} ---")
        for h in HORIZONS:
            sub = sub_all[sub_all[f"fwd{h}"].notna()]
            if len(sub) < 5:
                print(f"  h={h:>3}d  n<5, skipped")
                continue
            a = arm_stats(sub[f"fwd{h}"].to_numpy(), h)
            b = arm_stats(sub[f"spy{h}"].to_numpy(), h)
            mmx = momentum_matched(sub, close, mom63, offhigh, fwd, h)
            line[str(h)] = {"event": a, "spy": b,
                            "median_pctile": mmx.get("median_pctile")}
            print(f"  h={h:>3}d  {fmt_arm(a)}")
            print(f"          SPY {fmt_arm(b)}")
            print(f"          momentum-matched median_pctile="
                  f"{mmx.get('median_pctile', float('nan')):.3f}")
        seg[name] = line
    results["segments"] = seg

    # ---------- look-ahead sensitivity ----------
    print("\n" + "=" * 100)
    print("SENSITIVITY -- full-sample percentile (LOOK-AHEAD) vs expanding (honest)")
    print("=" * 100)
    sens = {}
    for h in HORIZONS:
        a_exp = arm_stats(
            events_all.loc[(events_all["pctile_expanding"] <= 10) & events_all[f"fwd{h}"].notna(),
                           f"fwd{h}"].to_numpy(), h)
        a_full = arm_stats(
            events_all.loc[(events_all["pctile_fullsample"] <= 10) & events_all[f"fwd{h}"].notna(),
                           f"fwd{h}"].to_numpy(), h)
        sens[str(h)] = {"expanding": a_exp, "fullsample": a_full}
        print(f"  h={h:>3}d expanding  {fmt_arm(a_exp)}")
        print(f"        fullsample {fmt_arm(a_full)}")
    results["lookahead_sensitivity"] = sens

    # ---------- capeff rank-safety audit (trap b) ----------
    print("\n" + "=" * 100)
    print("CAPEFF RANK-SAFETY AUDIT (memory: capital-efficiency-two-traps)")
    print("=" * 100)
    for thr in LOW_THRESHOLDS:
        for h in HORIZONS:
            k = f"{thr}_{h}"
            if k not in grid:
                continue
            arms = {"event": grid[k]["event"], "spy": grid[k]["spy"]}
            safe = capeff_rank_safe(arms)
            print(f"  thr<={thr:>4.0f} h={h:>3}d  capeff_rank_safe={safe}"
                  f"{'' if safe else '  <-- NEGATIVE PnL ARM PRESENT: CapEff ranking FORBIDDEN'}")

    # ---------- ROBUSTNESS: is the null just a broken parser? ----------
    print("\n" + "=" * 100)
    print("ROBUSTNESS -- clean-parse subset only (does the null survive a healthy extractor?)")
    print(f"healthy ticker := median qa_share >= {QA_SHARE_MIN} across its parsed quarters")
    print("=" * 100)
    ph = stage1c_parse_health()
    ph["published"] = pd.to_datetime(ph["published"])

    # contamination profile: misparse rate vs the reported count (the headline data-quality fact)
    ph_ok = ph[ph["n_analysts"] > 0].copy()
    ph_ok["nb"] = pd.cut(ph_ok["n_analysts"], [0, 1, 2, 3, 5, 8, 12, 100])
    prof = ph_ok.groupby("nb", observed=True).agg(
        n=("parse_ratio", "size"), med_ratio=("parse_ratio", "median"),
        med_upper_bound=("upper_bound", "median"),
        pct_parse_ratio_lt_50=("parse_ratio", lambda s: float((s < PARSE_RATIO_MIN).mean() * 100)))
    print("\nmisparse rate vs REPORTED count (parse_ratio = reported / boundary-free upper bound):")
    print(prof.round(2).to_string())
    print("\n=> the misparse rate is MONOTONE in the reported count: the lowest readings are the")
    print("   least trustworthy. The signal selects on exactly the tail the parser corrupts.")

    # rebuild the signal using ONLY cleanly-parsed quarters, then recompute own-history percentiles
    att2 = att.merge(ph[["ticker", "published", "parse_ratio", "upper_bound"]],
                     on=["ticker", "published"], how="left", suffixes=("", "_ph"))
    clean_q = att2[(~att2["method"].str.startswith("failed"))
                   & (att2["parse_ratio"] >= PARSE_RATIO_MIN)]
    print(f"\nclean quarters: {len(clean_q)}/{n_parsed_ok} parsed "
          f"({len(clean_q)/n_parsed_ok*100:.1f}%) -- {n_parsed_ok - len(clean_q)} dropped as misparses")
    sig_c = stage1b_signal(clean_q)
    print(f"clean signal-eligible quarters: {len(sig_c)} across {sig_c['ticker'].nunique()} tickers")
    ev_c_all = assemble_events(sig_c[sig_c["ticker"].isin(priced)], close, dvol, mom63, offhigh, fwd)
    rob = {"clean_quarters": int(len(clean_q)), "parsed_quarters": int(n_parsed_ok),
           "contamination_profile": json.loads(prof.round(4).to_json(orient="index")),
           "cells": {}}
    for thr in LOW_THRESHOLDS:
        ev_h = ev_c_all[ev_c_all["pctile_expanding"] <= thr]
        print(f"\n### CLEAN attendance <= {thr:.0f}th pctile: {len(ev_h)} events, "
              f"{ev_h['ticker'].nunique()} tickers")
        for h in HORIZONS:
            sub = ev_h[ev_h[f"fwd{h}"].notna()]
            if len(sub) < 5:
                continue
            a = arm_stats(sub[f"fwd{h}"].to_numpy(), h)
            b = arm_stats(sub[f"spy{h}"].to_numpy(), h)
            mmx = momentum_matched(sub, close, mom63, offhigh, fwd, h)
            rob["cells"][f"{thr}_{h}"] = {"event": a, "spy": b,
                                          "median_pctile": mmx.get("median_pctile"),
                                          "mean_pctile": mmx.get("mean_pctile")}
            print(f"  h={h:>3}d  {fmt_arm(a)}")
            print(f"          SPY {fmt_arm(b)}   [benchmark, NOT alpha]")
            print(f"          momentum-matched median_pctile="
                  f"{mmx.get('median_pctile', float('nan')):.3f}"
                  f"  mean={mmx.get('mean_pctile', float('nan')):.3f}  n={mmx.get('n_events')}")
    results["robustness_clean_parse"] = rob

    # case-study parse audit -- the honest answer to "is TSM the same as MU?"
    print("\n--- case-study parse audit (reported vs boundary-free upper bound) ---")
    for t in ["MU", "TSM"]:
        sub = ph[ph["ticker"] == t].nsmallest(6, "n_analysts")
        print(f"  {t}:")
        print(sub[["published", "n_analysts", "upper_bound", "parse_ratio", "qa_share"]]
              .to_string(index=False))
    results["case_parse_audit"] = {
        t: ph[ph["ticker"] == t].nsmallest(6, "n_analysts")[
            ["published", "n_analysts", "upper_bound", "parse_ratio", "qa_share"]
        ].astype(str).to_dict("records") for t in ["MU", "TSM"]}

    outp = os.path.join(CACHE_DIR, "attendance_timing_report.json")
    with open(outp, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2, default=str)
    print(f"\nWrote {outp}")
    print(f"Elapsed: {(datetime.now() - t_start).total_seconds() / 60:.1f} min")
    return results


if __name__ == "__main__":
    run()
