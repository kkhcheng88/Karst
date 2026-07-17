"""KOL SPX POINT-FORECAST test -- "順哥" (royal flush 皇者顺888).

WHY THIS EXISTS (the blind spot the three prior reports all share)
------------------------------------------------------------------
2026-07-17_kol_shunge_scorecard.md / _roundtrip.md / _exit_trailing.md all score his
STOCK BUY/SELL calls. The index basket in those reports is n=44-72 round trips, and the
roundtrip report's own verdict on his claimed ~85% index win rate was "n too small, can
neither confirm nor refute".

That n is small for a structural reason: **his index book is almost never a trade
instruction. It is a POINT FORECAST.** He speaks the index in SPX POINTS
("4725-4730 是今天的极限", "这个星期系统目标6750", "今年依然看 7360") -- not "buy SPY".
A round-trip harness cannot see that book at all; it needs an entry and an exit and
these messages have neither.

1,822 of his messages carry an SPX-range point (3700-7999). **Not one has ever been
formally tested.** That is the product he actually sells. This script tests it.

THE CORE DESIGN PROBLEM (this test lives or dies on it)
-------------------------------------------------------
His forecasts are frequently CONDITIONAL BRANCHES:
    "4330-4350 係強 support。如果今天跌不破,下星期 lower high 反彈 4410。
     如果跌破了,我建議大家等待。"
Both branches are covered => the message is "right" no matter what the market does.
A naive scorer that reads this as one claim and asks "was he right?" returns ~100%.
**A ~85% self-reported win rate is exactly what this structure manufactures.** So the
whole test is built around SEPARATING the structure from the signal:

  A  UNCONDITIONAL directional forecast  -> falsifiable, scored properly
  B  CONDITIONAL branch ("hold X -> Y" / "break X -> Z")
         -> each BRANCH is a separate claim. The premise is evaluated FIRST; only
            premise-TRUE branches have their conclusion scored. Premise-true rate and
            conditional hit rate are reported SEPARATELY and never merged.
         -> a branch whose conclusion is "等待"/"觀望" (wait) is UNFALSIFIABLE and is
            counted, not scored. This is the escape hatch and it gets its own number.
  C  DESCRIPTIVE / POST-HOC ("已經到達我預算目標") -> NOT scored, % reported
  D  UNFALSIFIABLE (no number / no horizon / "震盪多次")   -> NOT scored, % reported

The C+D+unfalsifiable-B share IS the answer to "how much of his 85% is water". It is
reported whether or not it flatters him.

HINDSIGHT-BLIND LLM EXTRACTION
-------------------------------
  B1. Extractor sees ONLY message text. No prices, no returns, no market data.
      Extraction subagents are instructed Read/Write only -- no WebSearch/WebFetch/Bash.
  B2. Extractor never sees the message DATE. Dates are stripped from batch files and
      re-joined by msg_id afterwards. (Programmatically verified: zero date leakage.)
      Consequence: the brief's `date` field cannot be an extractor output; it is joined
      in code. `timeframe` likewise -- the extractor emits a linguistic BUCKET and code
      converts it to trading days using the date it never saw (see R6).
  B3. The label is a LINGUISTIC judgment ("is this sentence an if/then?"), never an
      evaluative one ("was he right?"). No extractor is ever asked about correctness.
  B4. Scoring is done in code from STRUCTURED fields. The extractor cannot score.
  B5. INTER-RATER CHECK (this closes an open gap flagged in _roundtrip.md §8.5):
      ~10% of messages are duplicated into a second batch set handed to a DIFFERENT
      agent; claim_type / level agreement is measured and reported.

  *** RESIDUAL RISK -- DECLARED, NOT SOLVED, AND WORSE HERE THAN IN _roundtrip.md ***
  The SPX level IS an era fingerprint. "SPX 4200" dates a message to early 2023;
  "7500" to 2026. An LLM with a knowledge cutoff can therefore date these messages from
  the very numbers it is asked to extract, and it knows 2023->2026 was a bull market.
  B1/B2 close the price and date channels; this one CANNOT be closed. It is mitigated
  only by B3/B4 (the task is mechanical: copy the number, classify the if/then; the
  extractor never judges outcome) -- not eliminated. Weigh every extraction-dependent
  number in this report accordingly.

PRE-REGISTERED RULES
--------------------
*** Every rule below was written and committed to this file BEFORE any claim was
    extracted and BEFORE any hit rate was computed. The analyze stage did not exist in
    runnable form until after this docstring was fixed. ***

R1. PREFILTER. Messages by author containing "皇者顺" whose text matches an SPX-range
    point: a 4-digit number 3700-7999 not glued to other digits/decimals.
    DEVIATION FROM BRIEF (declared): the brief said 4000-7999. SPX traded 3808-4200 in
    2023-03..2023-05, the start of the corpus -- a 4000 floor would silently drop his
    early BEARISH calls and bias the book bullish. Floor lowered to 3700 (corpus-span
    SPX intraday low = 3808.9; 3700 = that minus ~3% margin). The range is a property of
    the ERA's index domain, not of any outcome.
    NO keyword AND-filter. "4725-4730 是今天的极限,应该不会跌破" contains no index
    keyword yet is unambiguously an SPX forecast; a keyword gate would drop it. ALL
    prefilter hits go to the LLM, which decides `is_spx_claim`. Non-SPX numbers (HK/CN
    index levels, dollar amounts, stock prices) are rejected by that flag, not by regex.

R2. REFERENCE PRICE AND WINDOW START (no look-ahead).
    Message timestamp is converted to US/Eastern.
      ts_et strictly before 16:00 ET on a trading day -> window starts THAT day (he
        called it before the close; his "今天跌不破" must be scoreable on 今天).
      otherwise -> window starts the next trading day.
    spot0 = the last SPX close STRICTLY BEFORE the window start. He can never be scored
    against a price he had already seen.

R3. HIT DEFINITIONS -- FIXED HERE BEFORE ANY PRICE WAS READ.
    Window = N trading days from i_start inclusive. Closes only (primary).
    (a) TARGET claim (level_target present):
          target ABOVE spot0 -> HIT iff max(close over window) >= target_near
          target BELOW spot0 -> HIT iff min(close over window) <= target_near
        "target_near" = for a range target ("6750-6800"), the edge CLOSEST to spot0.
        This is the TOUCH rule and it is GENEROUS to him (a level touched once at any
        point in the window counts, even if price closes the window far away).
        Declared generous on purpose: the claim is "他有冇料", and the charitable
        reading must lose before a negative verdict means anything.
        SENSITIVITY: far edge; and intraday high/low instead of closes.
    (b) DIRECTION-ONLY claim (no level, direction up/down):
          HIT iff close(window end) > spot0 (up) / < spot0 (down). TERMINAL, not touch.
          (Touch would be absurd here: SPX ticks up at some point in almost any window.)
    (c) RANGE claim ("震盪 4300-4400"):
          HIT iff close(window end) is inside [lo, hi]. SENSITIVITY: all closes inside.

R4. B-CLASS (conditional branch) -- THE CENTRAL MACHINERY.
    Each branch is its own claim row. Two-stage, never merged:
      Stage 1 PREMISE, evaluated on closes over a 5-trading-day premise window from
        i_start (a premise is a near-term trigger: "如果今天跌不破"):
          hold_above X  -> TRUE iff min(close over premise window) >= X
          break_below X -> TRUE iff min(close over premise window) <  X
          break_above X -> TRUE iff max(close over premise window) >  X
        Range premise -> the edge generous to the premise firing (lo for below-tests,
        hi for above-tests).
      Stage 2 CONCLUSION, scored ONLY on premise-TRUE branches, by R3, over N trading
        days from i_start (overlaps the premise window -- declared; generous to him,
        the conclusion gets the full window to land).
      then_direction in {wait, none} with no level -> UNFALSIFIABLE. NOT scored.
        Counted and reported as its own number.
    REPORTED SEPARATELY, NEVER COMBINED: (i) premise-true rate, (ii) conditional hit
    rate given premise true, (iii) unfalsifiable-branch share.

R5. HEADLINE HORIZON. N = his stated timeframe when he gives one, else 21 trading days.
    The full 5/10/21 grid is reported for the no-timeframe subset. Note 21d is the most
    GENEROUS of the three under the touch rule -- the headline is his best case.

R6. TIMEFRAME BUCKET -> TRADING DAYS (deterministic, in code, from the date the
    extractor never saw):
      intraday->1, days_1_5->5, weeks_1_4->21, months_1_3->63,
      year-> trading days from i_start to Dec 31 of that calendar year (floor 5, cap
             252) -- computed in code precisely because the extractor cannot date "今年",
      none-> 21 (headline default).
    Explicit timeframe_days from the extractor wins, capped at 252.

R7. CONTROLS. **The report is VOID without all three.**
    (a) RANDOM-TARGET CONTROL -- the one that matters. For each scored target claim with
        distance d = (target_near - spot0)/spot0 and horizon N: draw random trading days
        t' uniformly from the corpus span, set a synthetic target close(t')*(1+d), and
        apply the SAME touch rule over N days from t'. 1,000 MC books.
        This quantifies the "support/resistance sits near spot => structurally high hit
        rate" effect directly. Also reported BY |d| BUCKET (<1%, 1-3%, 3-5%, >5%).
    (b) NAIVE CONTROLS on the same claim dates/horizons:
          N1 "trend continuation": predicted direction = sign of the prior 5-day move.
          N2 "always up": predict up every time.
    (c) UNCONDITIONAL BASE RATE over the corpus span: P(close(t+N) > close(t)) for
        N in {5,10,21,63}, and the P(touch +-x% within N) surface for
        x in {0.5,1,2,3,5}% -- the bull-market gimme that any "看升" inherits.

R8. HIS CLAIMED 85%. Reported side by side with the A-class hit rate and the B-class
    conditional hit rate, each with a Wilson 95% CI, and an explicit statement of
    whether 85% falls inside or outside each interval. No basket is allowed to be
    reported alone; A/B/C/D shares are ALWAYS reported together (the brief's discipline:
    reporting only the flattering class is how an 85% gets manufactured).

R9. STATISTICAL HONESTY.
    - Overlapping windows: claims share calendar time. An effective independent-cluster
      count (connected components of the interval-overlap graph) sits next to every raw
      n. _roundtrip.md found this collapses to ~1 cluster; expect the same here and do
      not let any Wilson CI pretend otherwise.
    - Multiple comparisons: the test count is tallied and printed.
    - MC percentile is a one-sided read of a 1,000-draw null; p95 is the bar.
    - Conclusions lean on direction-consistency and effect SIZE, never a single p-value.

R10. NO EXISTING FILE IS MODIFIED. Only this script and its report are added.

Stages:
  PYTHONUTF8=1 python exp_kol_spx_forecast.py --prep      # -> spx_batches/*.json
  (dispatch hindsight-blind extraction subagents -> spx_extract/*.jsonl)
  PYTHONUTF8=1 python exp_kol_spx_forecast.py --merge     # -> spx_claims.json + QA
  PYTHONUTF8=1 python exp_kol_spx_forecast.py --analyze   # -> spx_report.json
Deliverable -> backtest/results/2026-07-17_kol_spx_forecast.md
Intermediates (gitignored, under thesis/.raw/discord/): spx_batches/, spx_extract/,
spx_claims.json, spx_report.json
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backtest import data as kdata  # noqa: E402
from backtest.experiments.exp_kol_shunge_ledger import RAW, _clean, _load_messages  # noqa: E402

SEED = 20260717
BATCHES = RAW / "spx_batches"
EXTRACT = RAW / "spx_extract"
CLAIMS = RAW / "spx_claims.json"
OUT = RAW / "spx_report.json"
PXCSV = RAW / "prices" / "^GSPC.csv"

BATCH_SIZE = 60
OVERLAP_FRAC = 0.10          # B5 inter-rater
N_MC = 1000
TRADING_DAYS = 252
PREMISE_WIN = 5              # R4 stage 1
DEFAULT_N = 21               # R5
GRID = [5, 10, 21]           # R5
MAX_CHARS = 2500

# R1: SPX-range point. 4 digits 3700-7999, not glued to other digits or a decimal.
LEVEL_RE = re.compile(r"(?<![\d.])([3-7]\d{3})(?:\.\d+)?(?![\d.])")
LEVEL_LO, LEVEL_HI = 3700, 7999

CLAIM_TYPES = {"A", "B", "C", "D"}
DIRECTIONS = {"up", "down", "range", "none"}
COND_OPS = {"hold_above", "break_below", "break_above", "none"}
THEN_DIRS = {"up", "down", "range", "wait", "none"}
TF_BUCKETS = {"intraday", "days_1_5", "weeks_1_4", "months_1_3", "year", "none"}
TF_DAYS = {"intraday": 1, "days_1_5": 5, "weeks_1_4": 21, "months_1_3": 63}


def _in_range(v) -> bool:
    return v is not None and LEVEL_LO <= float(v) <= LEVEL_HI


def _levels(text: str) -> list[int]:
    out = []
    for m in LEVEL_RE.finditer(text):
        v = int(m.group(1))
        if LEVEL_LO <= v <= LEVEL_HI:
            out.append(v)
    return out


# ---------------------------------------------------------------------------
# PREP -- hindsight-blind batches (B2: NO dates reach the extractor)
# ---------------------------------------------------------------------------
def stage_prep() -> None:
    msgs = _load_messages()
    kol = [m for m in msgs if "皇者顺" in m["author"]["name"]]

    cand = []
    for m in kol:
        txt = _clean(m.get("content") or "")
        if not txt.strip():
            continue
        lv = _levels(txt)
        if not lv:
            continue
        cand.append({"msg_id": m["id"], "text": txt[:MAX_CHARS],
                     "truncated": len(txt) > MAX_CHARS, "levels_seen": sorted(set(lv))})

    rng = np.random.default_rng(SEED)
    BATCHES.mkdir(parents=True, exist_ok=True)
    for f in BATCHES.glob("*.json"):
        f.unlink()

    # B5: inter-rater overlap set -- same messages, second batch series, other agent.
    n_ov = int(round(OVERLAP_FRAC * len(cand)))
    ov_idx = set(rng.choice(len(cand), size=n_ov, replace=False).tolist())
    overlap = [cand[i] for i in sorted(ov_idx)]

    def _dump(items, prefix):
        nb = 0
        for i in range(0, len(items), BATCH_SIZE):
            chunk = [{"msg_id": c["msg_id"], "text": c["text"],
                      "levels_seen": c["levels_seen"]} for c in items[i:i + BATCH_SIZE]]
            p = BATCHES / f"{prefix}_{i // BATCH_SIZE:03d}.json"
            p.write_text(json.dumps(chunk, ensure_ascii=False, indent=1),
                         encoding="utf-8")
            nb += 1
        return nb

    nb_main = _dump(cand, "b")
    nb_ov = _dump(overlap, "r")   # r = re-rate

    # B2 verification: assert zero date leakage in what we hand the extractor.
    DATE_PAT = re.compile(
        r"\b(19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2}\b|\bT\d{2}:\d{2}:\d{2}\b|timestamp")
    leaks = 0
    for f in BATCHES.glob("*.json"):
        blob = json.loads(f.read_text(encoding="utf-8"))
        for r in blob:
            if set(r.keys()) != {"msg_id", "text", "levels_seen"}:
                leaks += 1
            if DATE_PAT.search(json.dumps(r, ensure_ascii=False)):
                leaks += 1
    qa = {
        "kol_messages": len(kol),
        "prefilter_hits": len(cand),
        "truncated": sum(c["truncated"] for c in cand),
        "batches_main": nb_main,
        "batches_rerate": nb_ov,
        "overlap_messages": len(overlap),
        "date_leak_flags": leaks,
        "level_range": [LEVEL_LO, LEVEL_HI],
    }
    (BATCHES / "_qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=1))
    if leaks:
        raise SystemExit(f"DATE LEAK in batch files: {leaks} -- prep aborted (B2).")


# ---------------------------------------------------------------------------
# MERGE -- validate schema, re-join dates by msg_id, inter-rater agreement
# ---------------------------------------------------------------------------
def _norm(r: dict) -> dict | None:
    """Schema-validate one extracted row. Returns None if unusable (never silently
    coerced -- rejects are counted in QA)."""
    try:
        out = {
            "msg_id": str(r["msg_id"]),
            "is_spx_claim": bool(r.get("is_spx_claim")),
            "claim_type": str(r.get("claim_type", "")).strip().upper(),
            "direction": str(r.get("direction", "none")).strip().lower(),
            "cond_op": str(r.get("cond_op", "none")).strip().lower(),
            "then_direction": str(r.get("then_direction", "none")).strip().lower(),
            "timeframe_bucket": str(r.get("timeframe_bucket", "none")).strip().lower(),
            "raw_quote": str(r.get("raw_quote", ""))[:400],
            "condition_if": str(r.get("condition_if", ""))[:200],
            "condition_then": str(r.get("condition_then", ""))[:200],
        }
    except Exception:
        return None
    for k in ("level_target", "level_target_hi", "level_support", "level_resistance",
              "cond_level", "cond_level_hi", "then_level", "then_level_hi"):
        v = r.get(k)
        try:
            out[k] = float(v) if v is not None and str(v) != "" else None
        except Exception:
            out[k] = None
    v = r.get("timeframe_days")
    try:
        out["timeframe_days"] = int(v) if v is not None and str(v) != "" else None
    except Exception:
        out["timeframe_days"] = None
    if out["claim_type"] not in CLAIM_TYPES:
        return None
    if out["direction"] not in DIRECTIONS:
        out["direction"] = "none"
    if out["cond_op"] not in COND_OPS:
        out["cond_op"] = "none"
    if out["then_direction"] not in THEN_DIRS:
        out["then_direction"] = "none"
    if out["timeframe_bucket"] not in TF_BUCKETS:
        out["timeframe_bucket"] = "none"
    return out


def stage_merge() -> None:
    msgs = _load_messages()
    date_of = {m["id"]: pd.Timestamp(m["timestamp"]) for m in msgs}

    main, rerate, rejects = [], [], 0
    for f in sorted(EXTRACT.glob("*.jsonl")):
        tgt = rerate if f.name.startswith("r_") else main
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                rejects += 1
                continue
            n = _norm(r)
            if n is None or n["msg_id"] not in date_of:
                rejects += 1
                continue
            tgt.append(n)

    for r in main:
        r["ts"] = str(date_of[r["msg_id"]])

    # B5 inter-rater agreement on the overlap set (by msg_id, message level)
    def _sig(rows):
        t = sorted({x["claim_type"] for x in rows})
        s = sorted({x["is_spx_claim"] for x in rows})
        lv = sorted({round(x[k]) for x in rows
                     for k in ("level_target", "cond_level", "then_level")
                     if x.get(k) is not None})
        return "".join(t), s, lv

    m_by = {}
    for r in main:
        m_by.setdefault(r["msg_id"], []).append(r)
    r_by = {}
    for r in rerate:
        r_by.setdefault(r["msg_id"], []).append(r)
    both = sorted(set(m_by) & set(r_by))
    agree_type = agree_spx = agree_lv = 0
    for mid in both:
        a, b = _sig(m_by[mid]), _sig(r_by[mid])
        agree_type += a[0] == b[0]
        agree_spx += a[1] == b[1]
        agree_lv += a[2] == b[2]
    n_ov = max(1, len(both))

    qa = {
        "rows_main": len(main),
        "messages_covered": len(m_by),
        "rejects": rejects,
        "rows_rerate": len(rerate),
        "interrater_messages": len(both),
        "interrater_claimtype_agree_pct": round(100 * agree_type / n_ov, 1),
        "interrater_is_spx_agree_pct": round(100 * agree_spx / n_ov, 1),
        "interrater_levels_agree_pct": round(100 * agree_lv / n_ov, 1),
    }
    CLAIMS.write_text(json.dumps({"qa": qa, "claims": main, "rerate": rerate},
                                 ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=1))


# ---------------------------------------------------------------------------
# ANALYZE
# ---------------------------------------------------------------------------
def _spx() -> pd.DataFrame:
    PXCSV.parent.mkdir(parents=True, exist_ok=True)
    if PXCSV.exists():
        df = pd.read_csv(PXCSV, index_col=0, parse_dates=True)
        if {"close", "high", "low"} <= set(df.columns) and len(df) > 100:
            return df
    df = kdata.load("^GSPC", source="yfinance", min_rows=500)
    df = df[["open", "high", "low", "close"]]
    df.to_csv(PXCSV)
    return df


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    z, p = 1.959964, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def _window_start(ts: pd.Timestamp, idx: pd.DatetimeIndex) -> int | None:
    """R2. ET-aware. Before 16:00 ET on a trading day -> that day; else next."""
    et = ts.tz_convert("US/Eastern") if ts.tzinfo else ts.tz_localize("UTC").tz_convert("US/Eastern")
    d = pd.Timestamp(et.date())
    pos = idx.searchsorted(d)
    if pos < len(idx) and idx[pos] == d and et.hour < 16:
        return int(pos)
    return int(idx.searchsorted(d, side="right"))


def _horizon(rec: dict, i0: int, idx: pd.DatetimeIndex) -> int:
    """R6."""
    if rec.get("timeframe_days"):
        return int(min(252, max(1, rec["timeframe_days"])))
    b = rec.get("timeframe_bucket", "none")
    if b in TF_DAYS:
        return TF_DAYS[b]
    if b == "year":
        yend = pd.Timestamp(year=idx[i0].year, month=12, day=31)
        n = int(idx.searchsorted(yend, side="right") - i0)
        return int(min(252, max(5, n)))
    return DEFAULT_N


def _touch(close: np.ndarray, i0: int, n: int, spot0: float, tgt: float) -> bool | None:
    """R3(a). Touch rule on closes."""
    j = min(len(close), i0 + n)
    if j <= i0:
        return None
    w = close[i0:j]
    return bool(w.max() >= tgt) if tgt > spot0 else bool(w.min() <= tgt)


def _terminal(close: np.ndarray, i0: int, n: int, spot0: float, up: bool) -> bool | None:
    """R3(b)."""
    j = min(len(close), i0 + n) - 1
    if j < i0:
        return None
    return bool(close[j] > spot0) if up else bool(close[j] < spot0)


def _near_far(lo, hi, spot0):
    """Edge of a range target closest to / furthest from spot0 (R3a)."""
    if hi is None:
        return lo, lo
    a, b = min(lo, hi), max(lo, hi)
    return (a, b) if abs(a - spot0) <= abs(b - spot0) else (b, a)


def _premise(close: np.ndarray, i0: int, op: str, lv: float, lv_hi) -> bool | None:
    """R4 stage 1."""
    j = min(len(close), i0 + PREMISE_WIN)
    if j <= i0:
        return None
    w = close[i0:j]
    if op == "hold_above":
        x = min(lv, lv_hi) if lv_hi is not None else lv
        return bool(w.min() >= x)
    if op == "break_below":
        x = min(lv, lv_hi) if lv_hi is not None else lv
        return bool(w.min() < x)
    if op == "break_above":
        x = max(lv, lv_hi) if lv_hi is not None else lv
        return bool(w.max() > x)
    return None


def _score_conclusion(close, i0, n, spot0, direction, lo, hi, far=False):
    """R3 applied to an A claim or a premise-true B conclusion."""
    if lo is not None and _in_range(lo):
        near, farl = _near_far(lo, hi, spot0)
        return _touch(close, i0, n, spot0, farl if far else near), "target"
    if direction in ("up", "down"):
        return _terminal(close, i0, n, spot0, direction == "up"), "direction"
    if direction == "range" and lo is not None and hi is not None:
        j = min(len(close), i0 + n) - 1
        if j < i0:
            return None, "range"
        return bool(min(lo, hi) <= close[j] <= max(lo, hi)), "range"
    return None, "unscoreable"


def _clusters(spans: list[tuple[int, int]]) -> int:
    """R9 effective independent samples: connected components of interval overlap."""
    if not spans:
        return 0
    ev = sorted(spans)
    n, cur = 1, ev[0][1]
    for a, b in ev[1:]:
        if a > cur:
            n += 1
            cur = b
        else:
            cur = max(cur, b)
    return n


def stage_analyze() -> None:
    blob = json.loads(CLAIMS.read_text(encoding="utf-8"))
    claims = blob["claims"]
    px = _spx()
    idx = px.index
    close = px["close"].to_numpy(float)
    high = px["high"].to_numpy(float)
    low = px["low"].to_numpy(float)

    rng = np.random.default_rng(SEED)
    rep: dict = {"qa": blob["qa"], "n_tests": 0}

    # ---- class mix (R8: always reported together) -------------------------
    spxc = [c for c in claims if c["is_spx_claim"]]
    mix = {}
    for t in "ABCD":
        mix[t] = sum(c["claim_type"] == t for c in spxc)
    rep["class_mix"] = {
        "messages_prefiltered": blob["qa"]["messages_covered"],
        "rows_total": len(claims),
        "rows_is_spx": len(spxc),
        "rows_not_spx": len(claims) - len(spxc),
        "counts": mix,
        "pct": {t: round(100 * mix[t] / max(1, len(spxc)), 1) for t in "ABCD"},
    }

    # ---- attach window/horizon -------------------------------------------
    span_lo = idx.searchsorted(pd.Timestamp("2023-03-11"))
    for c in spxc:
        ts = pd.Timestamp(c["ts"])
        i0 = _window_start(ts, idx)
        c["_i0"] = i0 if (i0 is not None and 0 < i0 < len(idx)) else None
        if c["_i0"] is None:
            continue
        c["_spot0"] = float(close[c["_i0"] - 1])
        c["_n"] = _horizon(c, c["_i0"], idx)

    # ---- A class ----------------------------------------------------------
    A = [c for c in spxc if c["claim_type"] == "A" and c.get("_i0")]
    a_rows = []
    for c in A:
        hit, kind = _score_conclusion(close, c["_i0"], c["_n"], c["_spot0"],
                                      c["direction"], c["level_target"],
                                      c["level_target_hi"])
        if hit is None:
            continue
        far, _ = _score_conclusion(close, c["_i0"], c["_n"], c["_spot0"],
                                   c["direction"], c["level_target"],
                                   c["level_target_hi"], far=True)
        near = None
        if c["level_target"] is not None and _in_range(c["level_target"]):
            near = _near_far(c["level_target"], c["level_target_hi"], c["_spot0"])[0]
        a_rows.append({
            "msg_id": c["msg_id"], "ts": c["ts"], "i0": c["_i0"], "n": c["_n"],
            "spot0": c["_spot0"], "kind": kind, "hit": bool(hit),
            "hit_far": None if far is None else bool(far),
            "target": near, "direction": c["direction"],
            "dist": None if near is None else (near - c["_spot0"]) / c["_spot0"],
            "tf_stated": c["timeframe_bucket"] != "none" or bool(c["timeframe_days"]),
            "quote": c["raw_quote"],
        })

    def _rate(rows, key="hit"):
        k = sum(r[key] for r in rows if r[key] is not None)
        n = sum(1 for r in rows if r[key] is not None)
        lo, hi = wilson(k, n)
        return {"n": n, "hits": k, "rate": round(100 * k / n, 1) if n else None,
                "ci": [round(100 * lo, 1), round(100 * hi, 1)]}

    rep["A"] = {
        "headline": _rate(a_rows),
        "by_kind": {kd: _rate([r for r in a_rows if r["kind"] == kd])
                    for kd in sorted({r["kind"] for r in a_rows})},
        "far_edge_sensitivity": _rate([r for r in a_rows if r["hit_far"] is not None],
                                      "hit_far"),
        "clusters": _clusters([(r["i0"], r["i0"] + r["n"]) for r in a_rows]),
        "direction_mix": {d: sum(r["direction"] == d for r in a_rows)
                          for d in sorted({r["direction"] for r in a_rows})},
    }
    rep["n_tests"] += 3

    # A grid on the no-stated-timeframe subset (R5)
    grid = {}
    for n in GRID:
        rows = []
        for c in A:
            if c["timeframe_bucket"] != "none" or c["timeframe_days"]:
                continue
            h, _k = _score_conclusion(close, c["_i0"], n, c["_spot0"], c["direction"],
                                      c["level_target"], c["level_target_hi"])
            if h is not None:
                rows.append({"hit": bool(h)})
        grid[n] = _rate(rows)
    rep["A"]["grid_no_stated_tf"] = grid
    rep["n_tests"] += len(GRID)

    # distance buckets
    def _bucket(d):
        a = abs(d) * 100
        return "<1%" if a < 1 else "1-3%" if a < 3 else "3-5%" if a < 5 else ">5%"
    tgt_rows = [r for r in a_rows if r["dist"] is not None]
    rep["A"]["by_distance"] = {
        b: _rate([r for r in tgt_rows if _bucket(r["dist"]) == b])
        for b in ["<1%", "1-3%", "3-5%", ">5%"]
    }
    rep["A"]["distance_stats"] = {
        "n": len(tgt_rows),
        "median_abs_pct": round(float(np.median([abs(r["dist"]) for r in tgt_rows])) * 100, 2)
        if tgt_rows else None,
        "p25_abs_pct": round(float(np.percentile([abs(r["dist"]) for r in tgt_rows], 25)) * 100, 2)
        if tgt_rows else None,
        "p75_abs_pct": round(float(np.percentile([abs(r["dist"]) for r in tgt_rows], 75)) * 100, 2)
        if tgt_rows else None,
    }

    # ---- B class ----------------------------------------------------------
    B = [c for c in spxc if c["claim_type"] == "B" and c.get("_i0")]
    b_rows = []
    for c in B:
        lv = c["cond_level"]
        prem = None
        if c["cond_op"] != "none" and lv is not None and _in_range(lv):
            prem = _premise(close, c["_i0"], c["cond_op"], lv, c["cond_level_hi"])
        falsifiable = (c["then_direction"] in ("up", "down", "range")
                       or (c["then_level"] is not None and _in_range(c["then_level"])))
        row = {"msg_id": c["msg_id"], "ts": c["ts"], "i0": c["_i0"], "n": c["_n"],
               "premise": prem, "cond_op": c["cond_op"], "falsifiable": bool(falsifiable),
               "then_direction": c["then_direction"], "hit": None,
               "quote": c["raw_quote"]}
        if prem is True and falsifiable:
            h, kd = _score_conclusion(close, c["_i0"], c["_n"], c["_spot0"],
                                      c["then_direction"], c["then_level"],
                                      c["then_level_hi"])
            row["hit"] = None if h is None else bool(h)
            row["kind"] = kd
        b_rows.append(row)

    prem_known = [r for r in b_rows if r["premise"] is not None]
    prem_true = [r for r in prem_known if r["premise"]]
    scored_b = [r for r in b_rows if r["hit"] is not None]
    rep["B"] = {
        "branches_total": len(b_rows),
        "unfalsifiable_branches": sum(not r["falsifiable"] for r in b_rows),
        "unfalsifiable_pct": round(100 * sum(not r["falsifiable"] for r in b_rows)
                                   / max(1, len(b_rows)), 1),
        "then_wait_branches": sum(r["then_direction"] == "wait" for r in b_rows),
        "premise_evaluable": len(prem_known),
        "premise_true": len(prem_true),
        "premise_true_rate": round(100 * len(prem_true) / max(1, len(prem_known)), 1),
        "conditional": _rate(scored_b),
        "clusters": _clusters([(r["i0"], r["i0"] + r["n"]) for r in scored_b]),
    }
    rep["n_tests"] += 3

    # both-branches-covered: messages emitting >=2 B branches
    per_msg = {}
    for r in b_rows:
        per_msg.setdefault(r["msg_id"], []).append(r)
    multi = {m: v for m, v in per_msg.items() if len(v) >= 2}
    covered = 0
    for m, v in multi.items():
        ops = {r["cond_op"] for r in v}
        if {"hold_above", "break_below"} <= ops or {"break_above", "break_below"} <= ops:
            covered += 1
    rep["B"]["messages_with_branches"] = len(per_msg)
    rep["B"]["messages_multi_branch"] = len(multi)
    rep["B"]["messages_both_sides_covered"] = covered
    rep["B"]["both_sides_pct"] = round(100 * covered / max(1, len(per_msg)), 1)

    # ADDED AFTER FIRST RUN (declared): the cond_op signature above undercounts --
    # a both-sides pair can be {break_above, none}. Second, outcome-based signature:
    # a multi-branch message whose branches carry OPPOSITE conclusions (a bullish one
    # and a bearish/wait one) is covered whichever way the market goes.
    opp = 0
    for m, v in multi.items():
        td = {r["then_direction"] for r in v}
        if "up" in td and ({"down", "wait"} & td):
            opp += 1
    rep["B"]["messages_opposite_conclusions"] = opp
    rep["B"]["opposite_conclusions_pct_of_multi"] = round(
        100 * opp / max(1, len(multi)), 1)
    rep["n_tests"] += 1

    # ---- R7(a) RANDOM-TARGET CONTROL --------------------------------------
    ns = sorted({r["n"] for r in tgt_rows})
    fmax, fmin = {}, {}
    for n in ns:
        s = pd.Series(close)
        fmax[n] = s[::-1].rolling(n, min_periods=1).max()[::-1].to_numpy()
        fmin[n] = s[::-1].rolling(n, min_periods=1).min()[::-1].to_numpy()

    lo_i, hi_i = int(span_lo), len(close) - 1
    per_claim_rand, mc_books = [], np.zeros((N_MC, len(tgt_rows)), dtype=bool)
    for j, r in enumerate(tgt_rows):
        n, d = r["n"], r["dist"]
        valid_hi = max(lo_i + 1, hi_i - n)
        t = rng.integers(lo_i, valid_hi, size=N_MC)
        base = close[t]
        synth = base * (1 + d)
        hits = (fmax[n][t] >= synth) if d > 0 else (fmin[n][t] <= synth)
        mc_books[:, j] = hits
        per_claim_rand.append(float(hits.mean()))
    book_rates = mc_books.mean(axis=1) * 100
    actual_rate = 100 * sum(r["hit"] for r in tgt_rows) / max(1, len(tgt_rows))
    rep["control_random_target"] = {
        "n_claims": len(tgt_rows),
        "actual_hit_pct": round(actual_rate, 1),
        "random_mean_hit_pct": round(float(book_rates.mean()), 1),
        "random_p5_p50_p95": [round(float(np.percentile(book_rates, 5)), 1),
                              round(float(np.percentile(book_rates, 50)), 1),
                              round(float(np.percentile(book_rates, 95)), 1)],
        "percentile_of_actual": round(float((book_rates < actual_rate).mean()), 3),
        "by_distance": {},
    }
    for b in ["<1%", "1-3%", "3-5%", ">5%"]:
        sel = [j for j, r in enumerate(tgt_rows) if _bucket(r["dist"]) == b]
        if not sel:
            continue
        act = 100 * sum(tgt_rows[j]["hit"] for j in sel) / len(sel)
        rnd = 100 * float(np.mean([per_claim_rand[j] for j in sel]))
        rep["control_random_target"]["by_distance"][b] = {
            "n": len(sel), "actual_pct": round(act, 1), "random_pct": round(rnd, 1),
            "edge_pp": round(act - rnd, 1)}
    rep["n_tests"] += 1 + len(rep["control_random_target"]["by_distance"])

    # ---- R7(a2) OFFSET-BLOCK NULL ----------------------------------------
    # ADDED AFTER THE FIRST RUN (declared, and declared WHY): the R7(a) null draws an
    # INDEPENDENT random date per claim, but his claims are heavily overlapping
    # (A-class clusters == 1). An independent-draw null therefore has too little
    # variance and its p95 band is too NARROW -- i.e. R7(a) flatters him. This null
    # shifts the ENTIRE book by one common random offset k, preserving the internal
    # correlation structure exactly, and re-scores at the same distances. It can only
    # WEAKEN his edge, never manufacture one, which is why adding it post-hoc is not
    # cherry-picking. Both nulls are reported; the conservative one governs the verdict.
    offs, ok_books = [], []
    max_n = max((r["n"] for r in tgt_rows), default=DEFAULT_N)
    for _ in range(N_MC):
        k = int(rng.integers(-(hi_i - lo_i) + max_n, hi_i - lo_i - max_n))
        hits, tot = 0, 0
        for r in tgt_rows:
            t = r["i0"] + k
            if t < lo_i or t + r["n"] >= hi_i:
                continue
            b = close[t]
            s = b * (1 + r["dist"])
            h = (fmax[r["n"]][t] >= s) if r["dist"] > 0 else (fmin[r["n"]][t] <= s)
            hits += bool(h)
            tot += 1
        if tot >= 0.5 * len(tgt_rows):
            ok_books.append(100 * hits / tot)
            offs.append(k)
    ob = np.array(ok_books)
    rep["control_offset_block"] = {
        "draws_used": len(ob),
        "actual_hit_pct": round(actual_rate, 1),
        "null_mean_hit_pct": round(float(ob.mean()), 1),
        "null_p5_p50_p95": [round(float(np.percentile(ob, 5)), 1),
                            round(float(np.percentile(ob, 50)), 1),
                            round(float(np.percentile(ob, 95)), 1)],
        "percentile_of_actual": round(float((ob < actual_rate).mean()), 3),
    }
    rep["n_tests"] += 1

    # ---- R7(a3) MOMENTUM-MATCHED NULL -- THE DECISIVE CONTROL --------------
    # ADDED AFTER THE FIRST RUN (declared). R7(a)/(a2) randomise the DATE but not the
    # MARKET STATE. He does not issue targets at random moments -- he issues them while
    # the market is already moving. If he says "+3% to 6750" only when SPX is already
    # trending up, then a "+7.5pp edge over a uniformly random date" is MOMENTUM, not
    # him. backtest/results/2026-07-17_kol_bear_confound.md already proved exactly this
    # for his bearish stock calls (his bearish signal = a momentum replica with no
    # information beyond momentum). Without this control the phrase "he has real target
    # skill" is unsupported.
    # Null: for each claim, draw comparison dates ONLY from days in the SAME prior-21d
    # -return quintile as the claim's own date, then apply the identical distance and
    # touch rule. This holds the market state fixed and isolates HIM.
    prior = np.full(len(close), np.nan)
    prior[22:] = close[21:-1] / close[:-22] - 1
    span_mask = np.zeros(len(close), bool)
    span_mask[lo_i:hi_i] = True
    valid_prior = span_mask & ~np.isnan(prior)
    qs = np.nanpercentile(prior[valid_prior], [20, 40, 60, 80])
    bucket = np.digitize(prior, qs)          # 0..4
    pools = {q: np.flatnonzero(valid_prior & (bucket == q)) for q in range(5)}
    mm_per_claim, mm_books, mm_used = [], np.zeros((N_MC, len(tgt_rows)), bool), 0
    for j, r in enumerate(tgt_rows):
        n, d, i0 = r["n"], r["dist"], r["i0"]
        if not valid_prior[i0]:
            mm_per_claim.append(np.nan)
            continue
        pool = pools[int(bucket[i0])]
        pool = pool[pool + n < hi_i]
        if len(pool) < 20:
            mm_per_claim.append(np.nan)
            continue
        t = rng.choice(pool, size=N_MC, replace=True)
        synth = close[t] * (1 + d)
        hits = (fmax[n][t] >= synth) if d > 0 else (fmin[n][t] <= synth)
        mm_books[:, j] = hits
        mm_per_claim.append(float(hits.mean()))
        mm_used += 1
    ok = ~np.isnan(np.array(mm_per_claim, dtype=float))
    mm_rates = mm_books[:, ok].mean(axis=1) * 100
    act_mm = 100 * sum(tgt_rows[j]["hit"] for j in np.flatnonzero(ok)) / max(1, ok.sum())
    rep["control_momentum_matched"] = {
        "claims_used": int(ok.sum()),
        "actual_hit_pct": round(act_mm, 1),
        "null_mean_hit_pct": round(float(mm_rates.mean()), 1),
        "null_p5_p50_p95": [round(float(np.percentile(mm_rates, 5)), 1),
                            round(float(np.percentile(mm_rates, 50)), 1),
                            round(float(np.percentile(mm_rates, 95)), 1)],
        "percentile_of_actual": round(float((mm_rates < act_mm).mean()), 3),
        "edge_pp": round(act_mm - float(mm_rates.mean()), 1),
        "by_distance": {},
    }
    for b in ["<1%", "1-3%", "3-5%", ">5%"]:
        sel = [j for j in np.flatnonzero(ok) if _bucket(tgt_rows[j]["dist"]) == b]
        if not sel:
            continue
        a_ = 100 * sum(tgt_rows[j]["hit"] for j in sel) / len(sel)
        r_ = 100 * float(np.mean([mm_per_claim[j] for j in sel]))
        rep["control_momentum_matched"]["by_distance"][b] = {
            "n": len(sel), "actual_pct": round(a_, 1), "null_pct": round(r_, 1),
            "edge_pp": round(a_ - r_, 1)}
    rep["n_tests"] += 1 + len(rep["control_momentum_matched"]["by_distance"])

    # ---- S-SUPPORT: contamination robustness arm ---------------------------
    # ADDED AFTER SPOT-CHECKING THE EXTRACTION (declared). Found by reading scored
    # rows against their quotes: "第二支撑6760-6780 是否支撑住" gets extracted with the
    # support level in `level_target`, so R3 scores it as "will SPX FALL to 6780?" and
    # marks a MISS when it holds. He never forecast that it WOULD be reached -- he was
    # NAMING A FLOOR. This contamination manufactures misses and therefore biases the
    # verdict AGAINST him, so it must be measured before any negative conclusion.
    # Arm: drop A-target claims whose target sits BELOW spot0 and whose quote names a
    # support/floor, then re-run the headline and the random-target edge.
    SUP = ("支撑", "支撐", "support", "撑住", "撐住", "大底", "底部")
    def _is_sup(r, c):
        return r["dist"] is not None and r["dist"] < 0 and any(
            s in (c.get("raw_quote") or "") for s in SUP)
    qmap = {(c["msg_id"], c["raw_quote"]): c for c in A}
    contam = []
    for r in tgt_rows:
        c = next((x for x in A if x["msg_id"] == r["msg_id"]
                  and x["raw_quote"] == r["quote"]), None)
        if c is not None and _is_sup(r, c):
            contam.append(r)
    keep = [r for r in tgt_rows if r not in contam]
    keep_idx = [j for j, r in enumerate(tgt_rows) if r not in contam]
    act_keep = 100 * sum(r["hit"] for r in keep) / max(1, len(keep))
    rnd_keep = 100 * float(np.mean([per_claim_rand[j] for j in keep_idx])) if keep_idx else None
    a_keep = [r for r in a_rows if r not in contam]
    rep["S_support_contamination"] = {
        "contaminated_target_claims": len(contam),
        "contamination_pct_of_targets": round(100 * len(contam) / max(1, len(tgt_rows)), 1),
        "contaminated_hit_pct": round(
            100 * sum(r["hit"] for r in contam) / max(1, len(contam)), 1) if contam else None,
        "A_headline_ex_contam": _rate(a_keep),
        "target_rate_ex_contam": round(act_keep, 1),
        "random_rate_ex_contam": round(rnd_keep, 1) if rnd_keep is not None else None,
        "edge_pp_ex_contam": round(act_keep - rnd_keep, 1) if rnd_keep is not None else None,
        "edge_pp_all_targets": round(actual_rate - float(np.mean(per_claim_rand)) * 100, 1),
    }
    rep["n_tests"] += 2

    # ---- A-class hit rate by his stated direction (EXPLORATORY, post-hoc) --
    rep["A"]["by_direction_EXPLORATORY"] = {
        d: _rate([r for r in a_rows if r["direction"] == d])
        for d in ["up", "down", "range"]
    }
    rep["n_tests"] += 3

    # ---- R7(b) NAIVE CONTROLS --------------------------------------------
    dir_rows = [r for r in a_rows if r["kind"] == "direction"]
    n1 = n2 = k1 = k2 = 0
    for r in dir_rows:
        i0, n = r["i0"], r["n"]
        j = min(len(close), i0 + n) - 1
        if j < i0 or i0 - 6 < 0:
            continue
        up_real = close[j] > r["spot0"]
        trend_up = close[i0 - 1] > close[i0 - 6]
        n1 += 1
        k1 += (trend_up == up_real)
        n2 += 1
        k2 += bool(up_real)
    lo1, hi1 = wilson(k1, n1)
    lo2, hi2 = wilson(k2, n2)
    rep["control_naive"] = {
        "N1_trend_continuation": {"n": n1, "rate": round(100 * k1 / n1, 1) if n1 else None,
                                  "ci": [round(100 * lo1, 1), round(100 * hi1, 1)]},
        "N2_always_up": {"n": n2, "rate": round(100 * k2 / n2, 1) if n2 else None,
                         "ci": [round(100 * lo2, 1), round(100 * hi2, 1)]},
        "his_direction_only": _rate(dir_rows),
    }
    rep["n_tests"] += 3

    # ---- R7(c) UNCONDITIONAL BASE RATE ------------------------------------
    base = {}
    sl = slice(lo_i, len(close))
    c_s = close[sl]
    for n in [5, 10, 21, 63]:
        if len(c_s) <= n:
            continue
        up = c_s[n:] > c_s[:-n]
        base[f"P_up_{n}d"] = round(100 * float(up.mean()), 1)
    touch = {}
    for n in [5, 10, 21, 63]:
        s = pd.Series(close)
        fx = s[::-1].rolling(n, min_periods=1).max()[::-1].to_numpy()[sl]
        fn = s[::-1].rolling(n, min_periods=1).min()[::-1].to_numpy()[sl]
        row = {}
        for x in [0.5, 1, 2, 3, 5]:
            row[f"+{x}%"] = round(100 * float((fx >= c_s * (1 + x / 100)).mean()), 1)
            row[f"-{x}%"] = round(100 * float((fn <= c_s * (1 - x / 100)).mean()), 1)
        touch[f"{n}d"] = row
    rep["control_base_rate"] = {"span_start": str(idx[lo_i].date()),
                                "span_end": str(idx[-1].date()),
                                "direction": base, "touch_surface": touch}
    rep["n_tests"] += len(base) + len(touch) * 10

    # ---- intraday sensitivity (R3a) ---------------------------------------
    ih = 0
    n_ih = 0
    for r in tgt_rows:
        i0, n, t = r["i0"], r["n"], r["target"]
        j = min(len(close), i0 + n)
        if j <= i0:
            continue
        n_ih += 1
        ih += (high[i0:j].max() >= t) if t > r["spot0"] else (low[i0:j].min() <= t)
    rep["A"]["intraday_sensitivity"] = {
        "n": n_ih, "rate": round(100 * ih / n_ih, 1) if n_ih else None}
    rep["n_tests"] += 1

    # ---- by year ----------------------------------------------------------
    rep["A"]["by_year"] = {}
    for y in [2023, 2024, 2025, 2026]:
        rows = [r for r in a_rows if pd.Timestamp(r["ts"]).year == y]
        if rows:
            rep["A"]["by_year"][y] = _rate(rows)
    rep["n_tests"] += 4

    # ---- his claimed 85% (R8) --------------------------------------------
    def _verdict(block):
        if not block["n"]:
            return "n=0"
        lo, hi = block["ci"]
        return "85% INSIDE CI (cannot refute)" if lo <= 85 <= hi else "85% OUTSIDE CI"
    rep["claim_85"] = {
        "A_headline": {**rep["A"]["headline"], "verdict": _verdict(rep["A"]["headline"])},
        "B_conditional": {**rep["B"]["conditional"],
                          "verdict": _verdict(rep["B"]["conditional"])},
    }

    # ---- WHERE AN 85% COMES FROM (reconstruction, ADDED after first run) ---
    # This is NOT a claim about what he personally counts -- nobody can audit that.
    # It is a MECHANISM DEMONSTRATION on the identical corpus: score the same 2,155
    # claims the way a promoter would -- a post-hoc self-confirmation counts as a hit,
    # and anything unfalsifiable or whose premise never fired counts as "not wrong" --
    # and see what number falls out. If that number lands near 85% with NO change in
    # skill, then 85% is a scoring convention, not a track record.
    n_all = len(spxc)
    n_scored = rep["A"]["headline"]["n"] + rep["B"]["conditional"]["n"]
    n_hits = rep["A"]["headline"]["hits"] + rep["B"]["conditional"]["hits"]
    n_unscoreable = n_all - n_scored
    rep["how_85_is_manufactured"] = {
        "claims_total": n_all,
        "falsifiable_scored": n_scored,
        "unscoreable_or_vacuous": n_unscoreable,
        "unscoreable_pct": round(100 * n_unscoreable / max(1, n_all), 1),
        "breakdown_unscoreable": {
            "C_post_hoc_selfconfirm": mix["C"],
            "D_unfalsifiable": mix["D"],
            "A_extracted_but_unscoreable": mix["A"] - rep["A"]["headline"]["n"],
            "B_branches_never_scored": mix["B"] - rep["B"]["conditional"]["n"],
        },
        "honest_hit_pct_falsifiable_only": round(100 * n_hits / max(1, n_scored), 1),
        "promoter_hit_pct_counting_unscoreable_as_right": round(
            100 * (n_hits + n_unscoreable) / max(1, n_all), 1),
        "his_claim_pct": 85.0,
    }
    rep["n_tests"] += 1

    OUT.write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str),
                   encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k != "control_base_rate"},
                     ensure_ascii=False, indent=1, default=str)[:6000])
    print("\nwrote", OUT)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prep", action="store_true")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--analyze", action="store_true")
    a = ap.parse_args()
    if a.prep:
        stage_prep()
    elif a.merge:
        stage_merge()
    elif a.analyze:
        stage_analyze()
    else:
        ap.print_help()
