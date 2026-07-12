"""thesis/constraint_scan.py -- production constraint-language scan (Phase-3 WS4 backlog #1,
docs/2026-07-08_phase3_ws4_early_detection.md Sec3). Karst's PRIMARY early-detection channel
(proven: MU's constrained-language score turned positive ~17mo before gooptings/analyst
narrative caught up -- see backtest/results/2026-07-08_constraint_language_probe.md).

v1 scope (deliberately smaller than the full spec): scans themes.yaml's OWN tracked tickers per
theme (this already includes each theme's chain-head name -- e.g. MU is already in
memory-supercycle's ticker list -- so no separate "chain-head" schema field is needed). Reuses
the negation-aware phrase-match logic already validated in
backtest/experiments/exp_sector_constraint_language.py (2026-07-10), re-grouped by Karst THEME
instead of GICS sector (themes ARE Karst's sector-equivalent unit).

What this does NOT do yet (spec's full ambition, left as a documented gap, not silently skipped):
  - anti-noise NEW-PHRASE discovery (spec: a candidate phrase must appear across >=3 companies
    AND >=2 quarters before being promoted into CONSTRAINT_PHRASES) -- this needs unsupervised
    n-gram mining, not built here. v1 only tracks the EXISTING validated CONSTRAINT_PHRASES list
    (thesis/corpus.py) at the THEME level over time; it will catch a known-phrase density shift
    (e.g. a theme's tickers newly go quiet or newly light up) but NOT a genuinely novel phrase
    nobody has coded for yet.

Output:
  - dated heatmap: backtest/results/<date>_constraint_scan_production.md (theme x last-6-quarter
    density table, always overwritten with latest state -- this is a snapshot, not a log)
  - persistent alert queue: thesis/.raw/constraint_scan_queue.md (gitignored; appends ONLY
    NEW state changes since the last run, bidirectional -- newly-constrained AND newly-loosened
    listed side by side per spec Sec3 "雙向必須並列" -- so a session can triage without re-reading
    unchanged history every week)
  - state file: thesis/.raw/constraint_scan_state.json (last-seen density per theme-quarter, so
    reruns are idempotent and don't re-alert on unchanged data)

Run: python thesis/constraint_scan.py
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sqlite3

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
import corpus as _corpus  # noqa: E402  (sibling module; thesis/ is on sys.path when run directly)

THEMES_PATH = os.path.join(ROOT, "themes.yaml")
STATE_PATH = os.path.join(ROOT, ".raw", "constraint_scan_state.json")
QUEUE_PATH = os.path.join(ROOT, ".raw", "constraint_scan_queue.md")
RESULTS_DIR = os.path.join(ROOT, "..", "backtest", "results")

# same negation guard as exp_sector_constraint_language.py (2026-07-10, validated)
NEGATIONS = {"not", "no", "n't", "without", "unlikely", "never", "avoid", "avoided",
             "avoiding", "isn't", "aren't", "wasn't", "weren't", "don't", "doesn't",
             "didn't", "won't", "wouldn't", "shouldn't", "couldn't", "hasn't", "haven't"}
NEG_WINDOW_TOKENS = 8
# a theme-quarter state change smaller than this is noise (small baskets: 1 ticker flipping in
# a 3-name theme = 0.33 density swing) -- only alert on a real state change, not float jitter
ALERT_DELTA_MIN = 0.20


def _quarter_of(date_str):
    y, m = int(date_str[:4]), int(date_str[5:7])
    return f"{y}Q{(m - 1) // 3 + 1}"


def _negated_at(body, match_start):
    window = body[max(0, match_start - 80):match_start].lower()
    tokens = re.findall(r"[a-z']+", window)
    return any(t in NEGATIONS for t in tokens[-NEG_WINDOW_TOKENS:])


def _load_themes():
    themes = (yaml.safe_load(open(THEMES_PATH, encoding="utf-8")) or {}).get("themes", {}) or {}
    return {slug: [str(tk).upper() for tk in (t.get("tickers") or [])]
            for slug, t in themes.items()}


def scan():
    """Per-ticker-quarter constraint hit/negation status, restricted to themes.yaml's tracked
    tickers (not the full 9.9k-ticker discovery universe -- this job MONITORS existing theses,
    it does not discover new ones; that's thesis/discovery_radar.py's job)."""
    themes = _load_themes()
    all_tickers = sorted({tk for tks in themes.values() for tk in tks})
    ticker_to_themes = {}
    for slug, tks in themes.items():
        for tk in tks:
            ticker_to_themes.setdefault(tk, []).append(slug)

    con = sqlite3.connect(_corpus.DB)
    match = " OR ".join(f'"{p}"' for p in _corpus.CONSTRAINT_PHRASES)
    placeholders = ",".join("?" * len(all_tickers))
    rows = con.execute(
        f"SELECT d.slug, d.primary_ticker, d.published, docs_fts_en.body "
        f"FROM docs_fts_en JOIN docs d ON d.slug = docs_fts_en.slug "
        f"WHERE d.thesistype='transcript' AND d.primary_ticker IN ({placeholders})",
        all_tickers).fetchall()
    con.close()
    print(f"[constraint_scan] {len(all_tickers)} tracked tickers, {len(rows)} transcripts to check")

    # theme x quarter -> {covered: set(ticker), flagged: set(ticker)}
    panel = {}
    for slug, ticker, published, body in rows:
        q = _quarter_of(published)
        n_kept = 0
        for p in _corpus.CONSTRAINT_PHRASES:
            for m in re.finditer(re.escape(p), body, re.IGNORECASE):
                if not _negated_at(body, m.start()):
                    n_kept += 1
                    break  # one confirmed phrase is enough to flag this transcript
            if n_kept:
                break
        for slug_t in ticker_to_themes.get(ticker, []):
            key = (slug_t, q)
            panel.setdefault(key, {"covered": set(), "flagged": set()})
            panel[key]["covered"].add(ticker)
            if n_kept:
                panel[key]["flagged"].add(ticker)
    return panel


def _density_by_theme_quarter(panel):
    out = {}
    for (slug, q), d in panel.items():
        n_cov = len(d["covered"])
        out.setdefault(slug, {})[q] = (len(d["flagged"]) / n_cov if n_cov else None, n_cov)
    return out


def _load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)


def _last_n_quarters(quarters, n=6):
    def key(q):
        y, qn = q.split("Q")
        return (int(y), int(qn))
    return sorted(quarters, key=key)[-n:]


def run():
    panel = scan()
    density = _density_by_theme_quarter(panel)
    state = _load_state()
    today_str = datetime.date.today().isoformat()

    new_alerts_up, new_alerts_down = [], []
    for slug, qdict in density.items():
        quarters = _last_n_quarters(list(qdict.keys()), n=6)
        if not quarters:
            continue
        latest_q = quarters[-1]
        latest_val, latest_cov = qdict[latest_q]
        if latest_val is None:
            continue
        prev_val = state.get(slug, {}).get(latest_q)
        if prev_val is not None and abs(latest_val - prev_val) < 1e-9:
            continue  # already alerted this exact reading, skip (idempotent rerun)
        # compare vs the prior QUARTER's density (not just prior run) for the delta-magnitude gate
        prior_quarters = quarters[:-1]
        prior_val = qdict[prior_quarters[-1]][0] if prior_quarters else None
        if prior_val is None:
            baseline = 0.0  # first quarter with any coverage -- treat prior as zero
        else:
            baseline = prior_val
        delta = latest_val - baseline
        if abs(delta) >= ALERT_DELTA_MIN:
            line = (f"- [ ] **{slug}** {latest_q}: density {baseline:.2f} -> {latest_val:.2f} "
                    f"(n={latest_cov} tracked tickers) {today_str}")
            (new_alerts_up if delta > 0 else new_alerts_down).append(line)
        state.setdefault(slug, {})[latest_q] = latest_val
    _save_state(state)

    # -- persistent queue (append-only, bidirectional, human triage checklist) --
    if new_alerts_up or new_alerts_down:
        os.makedirs(os.path.dirname(QUEUE_PATH), exist_ok=True)
        with open(QUEUE_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n## {today_str} constraint-language scan\n")
            if new_alerts_up:
                f.write("### 轉緊(constrained, density up)\n" + "\n".join(new_alerts_up) + "\n")
            if new_alerts_down:
                f.write("### 轉鬆(loosening, density down)\n" + "\n".join(new_alerts_down) + "\n")
        print(f"[constraint_scan] {len(new_alerts_up)} up / {len(new_alerts_down)} down "
              f"new alert(s) -> {QUEUE_PATH}")
    else:
        print("[constraint_scan] no new theme-level state changes this run")

    # -- dated heatmap snapshot (overwritten each run, not a log) --
    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_path = os.path.join(RESULTS_DIR, f"{today_str}_constraint_scan_production.md")
    all_quarters = sorted({q for qdict in density.values() for q in qdict},
                           key=lambda q: (int(q.split("Q")[0]), int(q.split("Q")[1])))
    show_q = _last_n_quarters(all_quarters, n=6)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# Constraint-language production scan -- {today_str}\n\n")
        f.write("WS4 backlog #1 (docs/2026-07-08_phase3_ws4_early_detection.md Sec3). "
                "Density = fraction of a theme's TRACKED tickers (themes.yaml) whose transcript "
                "that quarter matched >=1 constraint phrase (negation-filtered), NOT a full-market "
                "discovery scan (see thesis/discovery_radar.py for that).\n\n")
        f.write("| theme | " + " | ".join(show_q) + " |\n")
        f.write("|---" * (len(show_q) + 1) + "|\n")
        for slug in sorted(density):
            cells = []
            for q in show_q:
                v = density[slug].get(q, (None, 0))[0]
                cells.append(f"{v:.2f}" if v is not None else "--")
            f.write(f"| {slug} | " + " | ".join(cells) + " |\n")
    print(f"[constraint_scan] heatmap -> {out_path}")


if __name__ == "__main__":
    run()
