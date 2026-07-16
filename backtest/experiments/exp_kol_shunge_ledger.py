"""KOL judgement scorecard -- "順哥" (royal flush 皇者顺888), Discord `皇者顺-美股`.

QUESTION
--------
Does this paid-subscription KOL's stock commentary carry forward alpha, measured
with the SAME yardstick Karst applies to its own theses (forward excess return /
hit-rate / IC-style scoring)? We are NOT copying his book; we are keeping score.

PRE-REGISTERED EXTRACTION RULES  (fixed BEFORE any outcome was computed; see the
"POST-HOC" section at the bottom of the results .md for anything added after)
--------------------------------------------------------------------------------
R1. Author filter: `author.name` contains "皇者顺" (the KOL himself). All other
    members (subscribers) are dropped.

R2. Ticker extraction:
    - Strip URLs / code-blocks / the exporter's "(已编辑)" marker first.
    - Candidate token = \b[A-Za-z]{2,5}\b  -- CASE-INSENSITIVE.
      RATIONALE (decided at inspection time, before scoring): the KOL does NOT
      write tickers in caps. Real samples: "Sold Frc 21.2", "Kre Kbe caty
      今天不错", "Dpst 今天premarket 8 也加了". An ALL-CAPS-only regex (the naive
      pre-registration) would have discarded the large majority of the corpus.
      Known cost of going case-insensitive: 1-letter tickers (F, C) and 2-letter
      tickers colliding with English words are unrecoverable -> we accept the
      loss and declare it, rather than tune the rule per-result.
    - Must appear in the REAL universe: Nasdaq Trader nasdaqlisted.txt +
      otherlisted.txt (13,058 symbols), UNION any candidate that yfinance can
      still serve history for (this recovers DELISTED names like FRC / PACW,
      which are exactly the ones a bank-crisis call hinges on).
    - Must NOT be in ENGLISH_BLOCKLIST (below): a fixed, OUTCOME-BLIND list of
      common English + trading-jargon words that are also real tickers (AI, USA,
      CEO, ALL, ON, IT, NOW, BIG, CAN, GO, HAS, FAST ...). Written once, from
      language knowledge only, never revised after seeing a return.

R3. Direction classification: KEYWORD RULES ONLY. No LLM per-message judgement --
    an LLM reading a 2023 message in 2026 cannot un-know how it turned out, and
    would silently import hindsight into the extraction ("this one was clearly a
    buy call"). That is the single largest fraud risk in this study.
    - The Chinese lists are the pre-registered ones. English equivalents were
      added at the same time (the corpus is bilingual: "Sold Kre 44.9", "Buy
      slowly with each big dips"). The extension is deliberately SYMMETRIC --
      every bullish English term has a bearish counterpart -- so it cannot tilt
      the bull/bear balance.
    - Both directions present, or neither -> `ambiguous`, EXCLUDED from the main
      sample. The excluded % is reported.

R4. Episode de-duplication: same (ticker, direction) within 7 CALENDAR days
    collapses to ONE claim episode (dated at the first message). Stops a name he
    repeats daily from counting as 40 independent claims.

PRE-REGISTERED SCORING RULES
----------------------------
S1. Entry = CLOSE of the first US trading day STRICTLY AFTER the message's date
    in US/Eastern (the export timestamps are +08:00; a 21:56+08:00 message is
    09:56 ET the SAME US day, so this is a genuine next-close entry -- no
    intraday look-ahead).
S2. Horizons: 21 / 63 / 126 TRADING days. Total-return closes (data.load
    adjusted=True) -- required for multi-month cross-sector work.
S3. Metrics: absolute return; excess vs SPY and vs QQQ over the identical window.
    BEARISH claims have their excess NEGATED (he told you to leave; a fall = he
    was right).
S4. Hit rate = share of claims with excess > 0. Plus median excess and p10
    (left tail).
S5. Delisting: if a ticker's history ends inside the window, the last available
    close is used as the terminal value (a bank failure IS a -99% outcome and
    must not be quietly dropped). Affected claims are counted and a
    sensitivity-excluding-them is reported.

PRE-REGISTERED CONTROLS  (the report is void without these)
-----------------------------------------------------------
C1. 2023-2026 is a bull market: ANY "buy something" claim has a high base rate.
    Excess vs SPY/QQQ is therefore the headline, never absolute return.
C2. Monte-Carlo null, 1000 draws each:
    - MC-A (stock selection): keep his ACTUAL claim dates and directions, shuffle
      the TICKERS randomly from his own mentioned pool. Holds market regime
      exactly constant -> isolates "did he pick the right name".
    - MC-B (timing): keep the pool draw, randomise the DATES uniformly across his
      active range -> isolates "did he pick the right moment".
    He must beat these, not just beat zero.
C3. Bullish and bearish claims reported SEPARATELY (in a bull market only the
    bearish book really tests judgement).

Stages:  python exp_kol_shunge_ledger.py --extract | --prices | --score | --all
Intermediates -> thesis/.raw/discord/ (gitignored). Deliverable ->
backtest/results/2026-07-17_kol_shunge_scorecard.md
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backtest import data as kdata  # noqa: E402

SRC = Path(r"C:\TradingView\Discord\RoyalFlush_2020_to_now.json")
SRC_INCR = Path(r"C:\TradingView\Discord\RoyalFlush_incr_20260717.json")


def _load_messages() -> list[dict]:
    """Merge base + incremental export, de-duplicating by message `id` (the two
    files overlap 2026-06-20..06-24). Also asserts the delete-bias evidence over
    the FULL merged sample and stashes it for the report's limitations section."""
    msgs = json.loads(SRC.read_text(encoding="utf-8"))["messages"]
    seen = {m["id"] for m in msgs}
    if SRC_INCR.exists():
        for m in json.loads(SRC_INCR.read_text(encoding="utf-8"))["messages"]:
            if m["id"] not in seen:
                seen.add(m["id"])
                msgs.append(m)
    msgs.sort(key=lambda m: pd.Timestamp(m["timestamp"]))
    kol = [m for m in msgs if "皇者顺" in m["author"]["name"]]
    ts = [pd.Timestamp(m["timestamp"]) for m in kol]
    max_gap = max((ts[i + 1] - ts[i]).days for i in range(len(ts) - 1))
    bias = {
        "merged_messages": len(msgs),
        "date_range": [str(ts[0]), str(ts[-1])],
        "kol_isBot_true_pct": round(
            100 * sum(m["author"].get("isBot") is True for m in kol) / len(kol), 1),
        "kol_edited_pct": round(
            100 * sum(bool(m.get("timestampEdited")) for m in kol) / len(kol), 1),
        "non_default_types": {k: v for k, v in
                              _count_types(msgs).items() if k != "Default"},
        "max_kol_gap_days": max_gap,
    }
    (RAW / "delete_bias_evidence.json").write_text(
        json.dumps(bias, ensure_ascii=False, indent=1), encoding="utf-8")
    return msgs


def _count_types(msgs: list[dict]) -> dict:
    out: dict[str, int] = {}
    for m in msgs:
        out[m["type"]] = out.get(m["type"], 0) + 1
    return out
RAW = ROOT / "thesis" / ".raw" / "discord"
RAW.mkdir(parents=True, exist_ok=True)
PRICES = RAW / "prices"
PRICES.mkdir(exist_ok=True)
CLAIMS = RAW / "claims.json"
SCORED = RAW / "scored.json"

BENCH = ["SPY", "QQQ"]
HORIZONS = [21, 63, 126]
SEED = 20260717

# --- R2: outcome-blind English/jargon blocklist -------------------------------
ENGLISH_BLOCKLIST = {
    # articles / pronouns / preps / conj / aux
    "a", "an", "the", "i", "me", "my", "we", "us", "our", "you", "your", "he",
    "him", "his", "she", "her", "it", "its", "they", "them", "who", "whom",
    "this", "that", "these", "those", "in", "on", "at", "to", "of", "for", "by",
    "up", "off", "out", "over", "with", "from", "into", "onto", "as", "and",
    "or", "but", "if", "so", "than", "then", "when", "how", "why", "not", "no",
    "yes", "all", "any", "each", "few", "more", "most", "some", "such", "only",
    "own", "same", "too", "very", "can", "will", "just", "now", "also", "am",
    "is", "are", "was", "were", "be", "been", "has", "have", "had", "do", "does",
    "did", "may", "might", "must", "shall", "would", "could", "want", "need",
    "let", "get", "got", "go", "goes", "went", "come", "came", "make", "made",
    "take", "took", "give", "gave", "see", "saw", "look", "know", "knew",
    "think", "say", "said", "tell", "told", "keep", "kept", "put", "puts",
    "find", "left", "back", "next", "last", "new", "old", "good", "bad", "best",
    "big", "small", "high", "low", "long", "short", "fast", "slow", "hard",
    "easy", "sure", "real", "true", "well", "much", "many", "lot", "lots",
    "here", "there", "where", "what", "which", "while", "after", "before",
    "again", "still", "even", "ever", "never", "away", "down", "under", "about",
    "one", "two", "six", "ten", "day", "days", "week", "year", "time", "today",
    "am", "pm", "eod", "ok", "okay", "yeah", "lol", "haha", "pls", "thx", "hi",
    "hey", "guys", "man", "own", "run", "runs", "ran", "win", "wins", "won",
    "lose", "lost", "hit", "hits", "top", "tops", "bit", "bits", "cut", "cuts",
    "add", "adds", "hold", "held", "buy", "buys", "sell", "sold", "sale",
    # trading jargon that collides with real tickets
    "call", "calls", "put", "price", "cost", "gain", "loss", "risk", "cash",
    "fund", "funds", "bank", "banks", "stock", "index", "money", "trade", "bull",
    "bear", "dip", "dips", "pump", "moon", "flat", "open", "close", "gap", "iv",
    "atm", "otm", "itm", "pe", "eps", "usd", "usa", "us", "ai", "ceo", "cfo",
    "ipo", "etf", "eft", "fed", "cpi", "ppi", "gdp", "pmi", "ecb", "boj", "sec",
    "irs", "tax", "vix", "spx", "ndx", "dow", "sp", "nyse", "otc", "ah", "pre",
    "eu", "uk", "cn", "hk", "jp", "tw", "kr", "ny", "la", "sf", "dc",
    "wow", "omg", "wtf", "btw", "fyi", "imo", "asap", "aka", "etc", "vs", "re",
    "min", "max", "avg", "num", "qty", "vol", "info", "data", "list", "line",
    "part", "type", "kind", "sort", "way", "ways", "end", "ends", "start",
    "help", "free", "full", "half", "rate", "rates", "hour", "wait", "watch",
    "gone", "done", "gets", "goal", "plan", "idea", "news", "note", "post",
    "read", "seen", "send", "sent", "show", "size", "step", "stop", "sure",
    "talk", "team", "test", "text", "than", "that", "them", "they", "thus",
    "try", "turn", "use", "used", "uses", "wall", "war", "week", "wise", "word",
    "work", "yet", "young", "zone", "life", "like", "live", "love", "luck",
    "nice", "pick", "play", "post", "pray", "safe", "same", "save", "self",
    "sit", "site", "soon", "stay", "sun", "hope", "huge", "job", "jobs",
    # --- OUTCOME-BLIND additions made at extraction-QA time (before ANY return was
    # computed; justified by LANGUAGE evidence only, never by a result):
    #   "bot" -- the KOL's own shorthand for "bought": "Bot spy 381 开始小量买了一点",
    #           "Bot Kre 42.7", "Bot little bit PL 3.89". 103 hits, ~all false.
    #   "com" -- from bare "Dot.com" / "xxx.com" text that survives URL stripping. 83 hits.
    "bot", "com",
}

# The yfinance-probe recovery arm for candidates outside the Nasdaq universe was BUILT
# (stage_resolve) and then DISABLED after an outcome-blind QA read of what it recovered:
# it resolved 9/216 candidates, of which 7 were English words that happen to be listed
# somewhere (DROP, TERM, BOTH, OIL, FAIR, ORG, CAPEX) and only 2 were genuine (FNGA,
# OCEA). Net: it injects more noise than signal. Critically it did NOT recover FRC or
# PACW -- yfinance serves no history for either -- so the delisted-bank names stay
# unscoreable regardless. See the report's limitations section (upward bias).
RECOVER_DELISTED = False

# --- R3: direction keywords (Chinese = pre-registered; English = symmetric ext.)
BULL_ZH = ["买", "買", "建仓", "建倉", "加仓", "加倉", "看好", "目标", "目標", "支撑",
           "支撐", "抄底", "中长线", "中長線", "持有", "上望", "看多", "做多"]
BEAR_ZH = ["卖", "賣", "清仓", "清倉", "减仓", "減倉", "看空", "危险", "危險", "见顶",
           "見頂", "别碰", "別碰", "走人", "下望", "做空"]
BULL_EN = [r"\bbuy\b", r"\bbuying\b", r"\bbought\b", r"\badd\b", r"\badding\b",
           r"\blong\b", r"\bbullish\b", r"\btarget\b", r"\bsupport\b",
           r"\bhold\b", r"\bholding\b", r"\baccumulate\b", r"\bupside\b"]
BEAR_EN = [r"\bsell\b", r"\bselling\b", r"\bsold\b", r"\btrim\b", r"\btrimming\b",
           r"\bshort\b", r"\bbearish\b", r"\bdanger\b", r"\bavoid\b",
           r"\bdump\b", r"\bexit\b", r"\bdownside\b"]

URL_RE = re.compile(r"https?://\S+")
TOKEN_RE = re.compile(r"\b[A-Za-z]{2,5}\b")


def _clean(text: str) -> str:
    text = URL_RE.sub(" ", text)
    text = text.replace("(已编辑)", " ").replace("(已編輯)", " ")
    text = re.sub(r"`[^`]*`", " ", text)
    return text


def _direction(text: str) -> str:
    bull = any(k in text for k in BULL_ZH) or any(
        re.search(p, text, re.I) for p in BULL_EN)
    bear = any(k in text for k in BEAR_ZH) or any(
        re.search(p, text, re.I) for p in BEAR_EN)
    if bull and not bear:
        return "bull"
    if bear and not bull:
        return "bear"
    return "ambiguous"


def load_universe() -> set[str]:
    uni = set()
    for fn in ("nasdaqlisted.txt", "otherlisted.txt"):
        p = RAW / fn
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
            parts = line.split("|")
            if len(parts) > 1 and re.fullmatch(r"[A-Z]{1,5}", parts[0]):
                uni.add(parts[0])
    return uni


def stage_extract() -> None:
    msgs = _load_messages()
    uni = load_universe()

    kol = [m for m in msgs if "皇者顺" in m["author"]["name"]]
    stats = {"total_messages": len(msgs), "kol_messages": len(kol)}

    rows, with_ticker = [], 0
    cand_counter: dict[str, int] = {}
    for m in kol:
        text = _clean(m.get("content") or "")
        toks = {t.upper() for t in TOKEN_RE.findall(text)
                if t.lower() not in ENGLISH_BLOCKLIST}
        tk = sorted(t for t in toks if t in uni)
        # unresolved candidates -> yfinance probe later (delisted recovery)
        unresolved = sorted(t for t in toks if t not in uni and len(t) >= 3)
        for t in unresolved:
            cand_counter[t] = cand_counter.get(t, 0) + 1
        if tk or unresolved:
            with_ticker += 1
        rows.append({"ts": m["timestamp"], "tickers": tk,
                     "unresolved": unresolved, "dir": _direction(text),
                     "len": len(text)})

    stats["kol_msgs_with_ticker_candidate"] = with_ticker
    (RAW / "extract_stage1.json").write_text(json.dumps(
        {"stats": stats, "rows": rows,
         "unresolved_counts": cand_counter}, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(stats, indent=1))
    print("unresolved candidates (top 40):",
          sorted(cand_counter.items(), key=lambda x: -x[1])[:40])


def stage_resolve(min_mentions: int = 3) -> None:
    """yfinance-probe frequent unresolved candidates -> recover delisted tickers."""
    blob = json.loads((RAW / "extract_stage1.json").read_text(encoding="utf-8"))
    cands = [t for t, n in blob["unresolved_counts"].items() if n >= min_mentions]
    ok = {}
    for t in cands:
        try:
            df = kdata.load(t, source="yfinance", min_rows=60, adjusted=True)
            ok[t] = [str(df.index[0].date()), str(df.index[-1].date()), len(df)]
            print("RESOLVED(delisted/odd):", t, ok[t])
        except Exception:
            pass
    (RAW / "resolved_extra.json").write_text(json.dumps(ok, ensure_ascii=False),
                                             encoding="utf-8")
    print(f"probed {len(cands)} -> resolved {len(ok)}")


def stage_claims() -> None:
    blob = json.loads((RAW / "extract_stage1.json").read_text(encoding="utf-8"))
    extra = (set(json.loads((RAW / "resolved_extra.json").read_text(encoding="utf-8")))
             if RECOVER_DELISTED else set())
    rows = blob["rows"]

    raw_claims = []
    n_amb_msgs = 0
    n_dir_msgs = 0
    for r in rows:
        tks = sorted(set(r["tickers"]) | (set(r["unresolved"]) & extra))
        if not tks:
            continue
        if r["dir"] == "ambiguous":
            n_amb_msgs += 1
            continue
        n_dir_msgs += 1
        ts = pd.Timestamp(r["ts"]).tz_convert("US/Eastern")
        for t in tks:
            raw_claims.append({"ts": str(ts), "date": str(ts.date()),
                               "ticker": t, "dir": r["dir"]})

    # R4: 7-calendar-day episode collapse per (ticker, direction)
    raw_claims.sort(key=lambda c: c["ts"])
    last: dict[tuple, pd.Timestamp] = {}
    episodes = []
    for c in raw_claims:
        key = (c["ticker"], c["dir"])
        t = pd.Timestamp(c["date"])
        if key in last and (t - last[key]) <= timedelta(days=7):
            continue
        last[key] = t
        episodes.append(c)

    stats = dict(blob["stats"])
    stats.update({
        "msgs_with_resolved_ticker_and_direction": n_dir_msgs,
        "msgs_with_ticker_but_ambiguous_direction": n_amb_msgs,
        "ambiguous_pct_of_ticker_msgs": round(
            100 * n_amb_msgs / max(1, n_amb_msgs + n_dir_msgs), 1),
        "raw_ticker_direction_pairs": len(raw_claims),
        "claim_episodes_after_7d_collapse": len(episodes),
        "unique_tickers": len({c["ticker"] for c in episodes}),
        "bull_episodes": sum(c["dir"] == "bull" for c in episodes),
        "bear_episodes": sum(c["dir"] == "bear" for c in episodes),
    })
    CLAIMS.write_text(json.dumps({"stats": stats, "episodes": episodes},
                                 ensure_ascii=False), encoding="utf-8")
    print(json.dumps(stats, indent=1, ensure_ascii=False))


def _px(sym: str) -> pd.Series | None:
    f = PRICES / f"{sym}.csv"
    if f.exists():
        s = pd.read_csv(f, index_col=0, parse_dates=True)["close"]
        return None if s.empty else s
    try:
        df = kdata.load(sym, source="yfinance", min_rows=60, adjusted=True)
        df[["close"]].to_csv(f)
        return df["close"]
    except Exception:
        f.write_text("date,close\n")
        return None


def stage_prices() -> None:
    blob = json.loads(CLAIMS.read_text(encoding="utf-8"))
    syms = sorted({c["ticker"] for c in blob["episodes"]} | set(BENCH))
    okc = 0
    for i, s in enumerate(syms, 1):
        if _px(s) is not None:
            okc += 1
        if i % 25 == 0:
            print(f"  {i}/{len(syms)} ...", flush=True)
    print(f"prices: {okc}/{len(syms)} usable")


def _fwd(series: pd.Series, cal: pd.DatetimeIndex, entry_i: int, h: int):
    """Total return from close at cal[entry_i] to close at cal[entry_i+h].
    S5: if history ends inside the window, use the last available close."""
    if entry_i >= len(cal):
        return None, None
    a = series.get(cal[entry_i])
    if a is None or not np.isfinite(a):
        return None, None
    end_i = min(entry_i + h, len(cal) - 1)
    win = series.reindex(cal[entry_i:end_i + 1]).dropna()
    if len(win) < 2:
        return None, None
    truncated = win.index[-1] < cal[end_i] or (entry_i + h) > len(cal) - 1
    return float(win.iloc[-1] / a - 1.0), truncated


def stage_score() -> None:
    blob = json.loads(CLAIMS.read_text(encoding="utf-8"))
    eps = blob["episodes"]
    spy, qqq = _px("SPY"), _px("QQQ")
    cal = spy.index
    px = {}
    for s in sorted({c["ticker"] for c in eps}):
        v = _px(s)
        if v is not None:
            px[s] = v

    out = []
    for c in eps:
        s = px.get(c["ticker"])
        if s is None:
            continue
        d = pd.Timestamp(c["date"])
        nxt = cal.searchsorted(d, side="right")  # S1: strictly after
        if nxt >= len(cal):
            continue
        rec = {**c, "entry": str(cal[nxt].date())}
        keep = False
        for h in HORIZONS:
            r, trunc = _fwd(s, cal, nxt, h)
            rb, _ = _fwd(spy, cal, nxt, h)
            rq, _ = _fwd(qqq, cal, nxt, h)
            if r is None or rb is None:
                continue
            sign = 1.0 if c["dir"] == "bull" else -1.0
            rec[f"ret_{h}"] = r
            rec[f"xs_spy_{h}"] = sign * (r - rb)
            rec[f"xs_qqq_{h}"] = sign * (r - rq)
            rec[f"trunc_{h}"] = bool(trunc)
            keep = True
        if keep:
            out.append(rec)
    SCORED.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"scored {len(out)} / {len(eps)} episodes")


# ---------------- reporting -------------------------------------------------
def _agg(df: pd.DataFrame, col: str) -> dict:
    v = df[col].dropna()
    if len(v) == 0:
        return {}
    return {"n": len(v), "hit": float((v > 0).mean()), "median": float(v.median()),
            "mean": float(v.mean()), "p10": float(v.quantile(0.10))}


def _fwd_matrix(px: dict, cal: pd.DatetimeIndex, h: int) -> dict:
    """Vectorised equivalent of _fwd for every entry index of every ticker.
    Returns {ticker: np.array len(cal)} of forward total returns; NaN where the
    entry close is missing. S5 truncation is handled by forward/backward-filling
    to the last available close before the horizon window (a name that stops
    trading keeps its final close as the terminal value)."""
    n = len(cal)
    out = {}
    for t, s in px.items():
        arr = s.reindex(cal).to_numpy(dtype="float64")
        # terminal value = close h bars ahead, or last available if truncated
        filled = pd.Series(arr).ffill().to_numpy()
        end = np.minimum(np.arange(n) + h, n - 1)
        term = filled[end]
        with np.errstate(invalid="ignore", divide="ignore"):
            fr = term / arr - 1.0     # entry uses RAW arr -> NaN if no entry close
        out[t] = fr
    return out


def _mc(df: pd.DataFrame, fwd: dict, spy_fr: np.ndarray, cal, h: int, mode: str,
        iters: int = 1000) -> dict:
    """Vectorised Monte-Carlo null. `fwd`/`spy_fr` are precomputed forward-return
    arrays indexed by cal position. Semantics identical to the per-claim path."""
    rng = np.random.default_rng(SEED)
    pool = sorted(fwd)
    pool_mat = np.vstack([fwd[t] for t in pool])      # (P, N)
    dates = pd.to_datetime(df["date"])
    ei_fixed = cal.searchsorted(dates.to_numpy(), side="right")  # mode A entries
    signs = np.where(df["dir"].to_numpy() == "bull", 1.0, -1.0)
    m = len(df)
    n = len(cal)
    lo, hi = int(cal.searchsorted(dates.min())), int(cal.searchsorted(dates.max()))
    meds, hits = [], []
    for _ in range(iters):
        pidx = rng.integers(0, len(pool), size=m)
        if mode == "A":                       # keep dates, shuffle tickers
            eidx = ei_fixed.copy()
        else:                                 # randomise dates
            eidx = rng.integers(lo, hi + 1, size=m)
        valid = eidx < n
        eidx = np.clip(eidx, 0, n - 1)
        r = pool_mat[pidx, eidx]
        rb = spy_fr[eidx]
        xs = signs * (r - rb)
        mask = valid & np.isfinite(r) & np.isfinite(rb)
        xs = xs[mask]
        if xs.size:
            meds.append(float(np.median(xs)))
            hits.append(float(np.mean(xs > 0)))
    return {"median_dist": meds, "hit_dist": hits}


def _pct_rank(dist: list[float], val: float) -> float:
    return float(np.mean([d < val for d in dist]))


def stage_report() -> None:
    recs = json.loads(SCORED.read_text(encoding="utf-8"))
    df = pd.DataFrame(recs)
    stats = json.loads(CLAIMS.read_text(encoding="utf-8"))["stats"]
    spy = _px("SPY")
    cal = spy.index
    px = {s: _px(s) for s in sorted(df["ticker"].unique())}
    px = {k: v for k, v in px.items() if v is not None}

    rep = {"stats": stats, "overall": {}, "by_dir": {}, "by_year": {},
           "by_ticker": {}, "mc": {}, "trunc": {}, "sens_excl_trunc": {}}
    df["year"] = pd.to_datetime(df["entry"]).dt.year
    for h in HORIZONS:
        for b in ("spy", "qqq"):
            rep["overall"][f"{b}_{h}"] = _agg(df, f"xs_{b}_{h}")
        rep["trunc"][h] = int(df.get(f"trunc_{h}", pd.Series(dtype=bool)).sum())
        sub = df[~df.get(f"trunc_{h}", False).astype(bool)]
        rep["sens_excl_trunc"][f"spy_{h}"] = _agg(sub, f"xs_spy_{h}")
        for d in ("bull", "bear"):
            rep["by_dir"][f"{d}_spy_{h}"] = _agg(df[df["dir"] == d], f"xs_spy_{h}")
            rep["by_dir"][f"{d}_qqq_{h}"] = _agg(df[df["dir"] == d], f"xs_qqq_{h}")
        for y in sorted(df["year"].unique()):
            rep["by_year"][f"{y}_spy_{h}"] = _agg(df[df["year"] == y], f"xs_spy_{h}")
        rep["overall"][f"abs_{h}"] = _agg(df, f"ret_{h}")

    top = df["ticker"].value_counts().head(10)
    for t in top.index:
        sub = df[df["ticker"] == t]
        rep["by_ticker"][t] = {
            "n": int(len(sub)), "bull": int((sub["dir"] == "bull").sum()),
            "bear": int((sub["dir"] == "bear").sum()),
            **{f"spy_{h}": _agg(sub, f"xs_spy_{h}") for h in HORIZONS}}

    for h in HORIZONS:
        act = _agg(df, f"xs_spy_{h}")
        fwd = _fwd_matrix(px, cal, h)
        spy_fr = _fwd_matrix({"SPY": spy}, cal, h)["SPY"]
        for mode in ("A", "B"):
            m = _mc(df, fwd, spy_fr, cal, h, mode)
            rep["mc"][f"{mode}_{h}"] = {
                "null_median_mean": float(np.mean(m["median_dist"])),
                "null_median_p95": float(np.percentile(m["median_dist"], 95)),
                "null_hit_mean": float(np.mean(m["hit_dist"])),
                "null_hit_p95": float(np.percentile(m["hit_dist"], 95)),
                "actual_median": act.get("median"),
                "actual_hit": act.get("hit"),
                "pctile_median": _pct_rank(m["median_dist"], act["median"]),
                "pctile_hit": _pct_rank(m["hit_dist"], act["hit"]),
            }
            print(f"MC-{mode} h={h} done", flush=True)

    (RAW / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    print(json.dumps(rep, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for s in ("extract", "resolve", "claims", "prices", "score", "report", "all"):
        ap.add_argument(f"--{s}", action="store_true")
    a = ap.parse_args()
    if a.extract or a.all:
        stage_extract()
    if a.resolve or a.all:
        stage_resolve()
    if a.claims or a.all:
        stage_claims()
    if a.prices or a.all:
        stage_prices()
    if a.score or a.all:
        stage_score()
    if a.report or a.all:
        stage_report()
