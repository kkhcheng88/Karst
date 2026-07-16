"""thesis/paper_league.py -- unified paper-trading "league table" across ALL of Karst's parallel
paper strategies (user's explicit call, 2026-07-13: AA-strict is NOT migrating to real capital
yet -- run every candidate structure side by side on paper and let the DATA pick the winner).

Motivation: three strategy lines currently live in three disconnected places with no common NAV
axis -- core v2 (playbook_readout.py's real-signal live logic, no paper NAV of its own),
AA-strict (thesis/aa_strict_paper_tracker.py, has its OWN NAV series), and sizing v1/v2 (
thesis/sizing.py, prints a daily target-$ table but never turns that into a NAV line). This file
does not replace any of them -- it is a thin daily "mark everyone to the same NAV=100 starting
line and print one scoreboard" layer on top.

Registered strategies (STRATEGIES dict below -- add a new one here, nowhere else):
  aa-strict   -- MIRRORS thesis/aa_strict_paper_tracker.py's own aa_paper_nav column, read
                 verbatim from thesis/.raw/aa_strict_paper_log.jsonl. Never recomputed here --
                 that tracker already runs daily and owns its own math.
  spy-bh      -- MIRRORS the same jsonl's spy_bh_nav column (aa-strict's own B&H reference,
                 reused as the league's passive benchmark line -- same number, not recomputed).
  sizing-v1   -- a NEW NAV line this file builds and owns: thesis/sizing.py's build_table() (v1,
                 confidence-only) target %-of-budget per active theme -> an equal-weight ticker
                 basket per theme (thesis/beta_check.py's build_basket(), backtest/data.py daily
                 closes) -> daily mark-to-market by the SAME ratio method paper_ledger.py's
                 cmd_update() uses (drift the position by the basket's cumulative return since
                 it was last marked, not a fresh daily rebalance to a moving target). Whatever
                 %-of-budget isn't deployed (PRELIMINARY judge status caps total deployment at
                 50%) sits in cash earning a flat 0% -- it never shrinks or grows on its own.
  sizing-v2   -- identical mechanics, sizing.py's build_table_v2() (confidence x magnitude
                 score, top-K selection, fixed micro-positions for event-binary themes).

Neither sizing.py, aa_strict_paper_tracker.py, nor paper_ledger.py is imported for its SIDE
EFFECTS or modified in any way -- sizing.py and beta_check.py are pure-function imports (same
"reused as-is" pattern paper_ledger.py itself already established for beta_check.py), and
aa_strict_paper_tracker.py's log is only ever READ, never re-derived.

Start date ("開賽日") = the trading day --init first runs, taken from SPY's own calendar (so
every strategy's history lands on the same trading-day axis, not wall-clock dates that could
disagree with a weekend/holiday). No strategy's history is backfilled before that day, INCLUDING
aa-strict/spy-bh even though their own underlying jsonl may already have earlier rows -- the
league's cross-strategy comparison honestly starts today, not before (this also means the
mirrored NAV shown for aa-strict/spy-bh on day 0 is whatever their tracker's most recently
written row says, even if that row itself is a day or two stale -- flagged via a note, not
silently smoothed over).

State:  thesis/.raw/paper_league_state.json (gitignored, like aa_strict_paper_state.json -- the
        daily "carry forward" working file; each strategy's positions/history since day 0).
Report: thesis/.raw/paper_league_report.json (regenerable any time via --report from state).

Run:
  python thesis/paper_league.py --init      # register the league (only if state is missing);
                                             # captures every strategy's day-0 baseline, no
                                             # history backfill
  python thesis/paper_league.py --update    # daily mark (idempotent within the same trading
                                             # day); also runs --report
  python thesis/paper_league.py --report    # print + write the scoreboard
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd
import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))            # thesis/
REPO_ROOT = os.path.dirname(ROOT)                             # Karst/
sys.path.insert(0, ROOT)
sys.path.insert(0, REPO_ROOT)
import beta_check as beta_check_mod    # noqa: E402 -- sibling module, reused build_basket() as-is
import sizing as sizing_mod            # noqa: E402 -- sibling module, reused build_table(_v2)() as-is
from backtest import data as data_mod  # noqa: E402 -- SPY close, used only for the trading-day axis

STATE_PATH = os.path.join(ROOT, ".raw", "paper_league_state.json")
REPORT_PATH = os.path.join(ROOT, ".raw", "paper_league_report.json")
AA_LOG_PATH = os.path.join(ROOT, ".raw", "aa_strict_paper_log.jsonl")
# thesis/narrative_flow_tracker.py's own log (2026-07-17: "narrative-flow" paper player --
# composition-driven target allocation, mirrored here the same way aa-strict/spy-bh are: this
# file never recomputes the NAV math, only reads the latest row).
NARRATIVE_FLOW_LOG_PATH = os.path.join(ROOT, ".raw", "narrative_flow_paper_log.jsonl")
NARRATIVE_FLOW_JOURNAL_PATH = os.path.join(ROOT, "paper", "narrative_flow.yaml")

# ============================================================================
# strategy registry -- add a new paper strategy here, nowhere else in this file.
#   kind="mirror": read `source_field` verbatim from `log_path`'s (default AA_LOG_PATH) latest row.
#   kind="sizing": build+mark an equal-weight theme-basket NAV from sizing.py's `table`
#                  ("v1" -> build_table(), "v2" -> build_table_v2()).
# ============================================================================
STRATEGIES = {
    "aa-strict": {"kind": "mirror", "source_field": "aa_paper_nav",
                  "label": "AA-strict (paper, mirrored)"},
    "spy-bh":    {"kind": "mirror", "source_field": "spy_bh_nav",
                  "label": "SPY B&H (benchmark, mirrored)"},
    "sizing-v1": {"kind": "sizing", "table": "v1",
                  "label": "Sizing v1 (confidence-only)"},
    "sizing-v2": {"kind": "sizing", "table": "v2",
                  "label": "Sizing v2 (confidence x magnitude)"},
    "narrative-flow": {"kind": "mirror", "source_field": "narrative_flow_nav",
                        "log_path": NARRATIVE_FLOW_LOG_PATH,
                        "holdings_from_journal": NARRATIVE_FLOW_JOURNAL_PATH,
                        "label": "Narrative Flow (KOL 目標配置, 紙上)"},
    "qqq-bh-nf": {"kind": "mirror", "source_field": "qqq_bh_nav",
                  "log_path": NARRATIVE_FLOW_LOG_PATH,
                  "label": "QQQ B&H (narrative-flow 對照, mirrored)"},
}


# ============================================================================
# small helpers
# ============================================================================


def _today_trading_str():
    """The latest trading day per SPY's own close index -- the single calendar axis every
    strategy's history is marked against, so all four lines move on the same days."""
    spy_close = data_mod.load("SPY")["close"]
    return spy_close.index[-1].date().isoformat()


def _read_jsonl(path):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _load_state():
    if not os.path.exists(STATE_PATH):
        return None
    with open(STATE_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def _save_report(report):
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)


# ============================================================================
# sizing-v1 / sizing-v2 target reader (pure import of sizing.py -- no local reimplementation
# of its math; same $-target -> %-of-budget conversion thesis/paper_ledger.py's own
# compute_sizing_targets() uses for v1, extended here to also cover v2)
# ============================================================================


def _sizing_pct_by_slug(kind):
    """kind: 'v1' or 'v2'. Returns (themes_dict, {slug: pct_of_DEFAULT_BUDGET}) using sizing.py's
    own build_table()/build_table_v2() completely unchanged."""
    themes = sizing_mod.load_themes()
    judge = sizing_mod.load_judge()
    status = judge.get("status", "PRELIMINARY")
    circuit_breaker = bool(judge.get("circuit_breaker", False)) or status == "FAIL"
    budget = sizing_mod.DEFAULT_BUDGET

    pct = {}
    if kind == "v1":
        rows, _cut_log, _total_cap, _total_factor = sizing_mod.build_table(
            themes, status, circuit_breaker, budget)
        for r in rows:
            pct[r["slug"]] = (r["final"] / budget * 100.0) if budget else 0.0
    elif kind == "v2":
        rows, binary_rows, _cut_log, _total_cap = sizing_mod.build_table_v2(themes, status, budget)
        for r in rows:
            pct[r["slug"]] = (r["final"] / budget * 100.0) if budget else 0.0
        for r in binary_rows:
            pct[r["slug"]] = (r["final"] / budget * 100.0) if budget else 0.0
    else:
        raise ValueError(f"unknown sizing table kind: {kind!r}")
    return themes, pct


# ============================================================================
# daily mark -- shared by --init (day-0 baseline) and --update (subsequent days). Idempotent:
# a strategy whose history already has an entry for today_trading_str is left untouched.
# ============================================================================


def _mark_all(state, today_trading_str):
    notes = []
    changed = False

    for name, spec in STRATEGIES.items():
        strat = state["strategies"][name]
        hist = strat["history"]
        if hist and hist[-1]["date"] == today_trading_str:
            continue  # idempotent -- already marked for today's trading day

        if strat["kind"] == "mirror":
            log_path = spec.get("log_path", AA_LOG_PATH)
            rows = _read_jsonl(log_path)
            if not rows:
                notes.append(f"{name}: source log {log_path} missing/empty -- left unmarked")
                continue
            latest = rows[-1]
            nav = latest.get(spec["source_field"])
            if nav is None:
                notes.append(f"{name}: source row missing field {spec['source_field']!r} -- left unmarked")
                continue
            hist.append({"date": today_trading_str, "nav": round(float(nav), 4),
                         "source_as_of": latest.get("date")})
            changed = True
            if latest.get("date") != today_trading_str:
                notes.append(f"{name}: source log's latest row is dated {latest.get('date')} "
                              f"(behind today's trading day {today_trading_str}) -- mirrored "
                              "as-is, not recomputed")

        elif strat["kind"] == "sizing":
            themes, pct_by_slug = _sizing_pct_by_slug(STRATEGIES[name]["table"])
            positions = strat["positions"]

            for slug, pos in positions.items():
                theme = themes.get(slug)
                if theme is None or theme.get("status", "active") != "active":
                    continue  # frozen -- mirrors paper_ledger.py's "leave unmarked" convention
                tickers = theme.get("tickers") or []
                if not tickers:
                    continue
                basket_ret, _loaded, _failed = beta_check_mod.build_basket(tickers)
                if basket_ret is None or len(basket_ret) == 0:
                    continue
                cum = (1.0 + basket_ret).cumprod()
                new_trading_str = cum.index[-1].date().isoformat()
                last_marked = pos.get("last_marked")
                if last_marked == new_trading_str:
                    continue  # this basket's own data hasn't advanced since it was last marked

                ratio = None
                if last_marked:
                    anchor_ts = pd.Timestamp(last_marked)
                    prior = cum[cum.index <= anchor_ts]
                    if len(prior):
                        ratio = float(cum.iloc[-1] / prior.iloc[-1])
                if ratio is None:
                    # no anchor row in the basket's own loaded history -- fall back to the
                    # latest single-day return rather than silently compounding against nothing
                    # (same fallback paper_ledger.py's cmd_update() uses).
                    ratio = float(1.0 + basket_ret.iloc[-1])

                pos["pct"] = round(pos["pct"] * ratio, 4)
                pos["last_marked"] = new_trading_str
                changed = True

            # pick up any theme newly admitted to themes.yaml since this line last ran (fresh
            # baseline at its current sizing target -- mirrors paper_ledger.py's own convention;
            # funded "fresh" rather than debited from cash, a known simplification that only
            # matters once a theme is added mid-flight, not on day 0).
            for slug, pct in pct_by_slug.items():
                if pct > 0 and slug not in positions:
                    positions[slug] = {"pct": round(pct, 4), "entry_date": today_trading_str,
                                        "last_marked": today_trading_str}
                    notes.append(f"{name}: newly active theme '{slug}' added at its current sizing target")
                    changed = True

            nav = sum(p["pct"] for p in positions.values()) + strat["cash_pct"]
            hist.append({"date": today_trading_str, "nav": round(nav, 4)})
            changed = True

    return notes, changed


# ============================================================================
# --init
# ============================================================================


def _fresh_strategy_state(spec, today_trading_str):
    """A brand-new strategy's day-0 state -- shared by cmd_init (every strategy) and cmd_update's
    late-registration path (2026-07-17, added for narrative-flow: a strategy added to STRATEGIES
    AFTER the league state file already exists must not KeyError in _mark_all, and must start its
    own history from today rather than being backfilled)."""
    if spec["kind"] == "mirror":
        return {"kind": "mirror", "history": []}
    _themes, pct_by_slug = _sizing_pct_by_slug(spec["table"])
    positions = {slug: {"pct": round(pct, 4), "entry_date": today_trading_str,
                         "last_marked": today_trading_str}
                 for slug, pct in pct_by_slug.items() if pct > 0}
    deployed = sum(p["pct"] for p in positions.values())
    return {
        "kind": "sizing", "positions": positions,
        "cash_pct": round(max(0.0, 100.0 - deployed), 4), "history": [],
    }


def _register_new_strategies(state, today_trading_str):
    """Any name in STRATEGIES not yet present in a pre-existing state file gets a fresh day-0
    entry, dated today (not backfilled) -- same "league started_on stays honest" convention the
    module docstring describes for the league as a whole."""
    notes = []
    for name, spec in STRATEGIES.items():
        if name not in state["strategies"]:
            state["strategies"][name] = _fresh_strategy_state(spec, today_trading_str)
            notes.append(f"{name}: newly registered strategy -- day-0 baseline as of "
                         f"{today_trading_str}, no history backfilled")
    return notes


def cmd_init():
    if os.path.exists(STATE_PATH):
        print(f"state already exists at {STATE_PATH} -- --init only runs when the state file is "
              "missing (use --update for daily marks). No change made.")
        return

    today_trading_str = _today_trading_str()
    state = {"meta": {"started_on": today_trading_str}, "strategies": {}}

    for name, spec in STRATEGIES.items():
        state["strategies"][name] = _fresh_strategy_state(spec, today_trading_str)

    notes, _changed = _mark_all(state, today_trading_str)
    _save_state(state)

    print(f"initialized {STATE_PATH}  (league start / trading day: {today_trading_str})")
    for name in STRATEGIES:
        strat = state["strategies"][name]
        nav = strat["history"][-1]["nav"] if strat["history"] else None
        nav_s = f"{nav:.2f}" if nav is not None else "n/a"
        if strat["kind"] == "sizing":
            print(f"  {name}: {len(strat['positions'])} theme position(s), "
                  f"deployed={100 - strat['cash_pct']:.2f}%  cash={strat['cash_pct']:.2f}%  "
                  f"day-0 nav={nav_s}")
        else:
            print(f"  {name}: mirrors '{STRATEGIES[name]['source_field']}' from "
                  f"{STRATEGIES[name].get('log_path', AA_LOG_PATH)}  day-0 nav={nav_s}")
    for n in notes:
        print(f"  note: {n}")


# ============================================================================
# --update (daily mark, idempotent within the same trading day)
# ============================================================================


def cmd_update():
    state = _load_state()
    if state is None:
        print(f"no state file at {STATE_PATH} -- run --init first.")
        return

    today_trading_str = _today_trading_str()
    reg_notes = _register_new_strategies(state, today_trading_str)
    notes, changed = _mark_all(state, today_trading_str)
    changed = changed or bool(reg_notes)
    notes = reg_notes + notes
    _save_state(state)

    print(f"update complete ({'state changed' if changed else 'idempotent -- no change'}).")
    for n in notes:
        print(f"  note: {n}")


# ============================================================================
# --report
# ============================================================================


def _narrative_flow_holdings(journal_path):
    """Latest (max effective_date <= today) journal version's target weights, in the same
    {"slug"/"pct"} + cash_pct shape _format_holdings_line() (dashboard_render.py) already expects
    from sizing-v1/v2 rows -- "slug" here is a ticker, not a theme, since dashboard_render.py's
    theme_zh() falls back to the raw string for any name it doesn't recognise (tickers included)."""
    try:
        with open(journal_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except OSError:
        return None, None
    versions = sorted(data.get("journal") or [], key=lambda v: v["effective_date"])
    today_str = datetime.now().date().isoformat()
    applicable = [v for v in versions if str(v["effective_date"]) <= today_str]
    latest = (applicable or versions or [None])[-1]
    if latest is None:
        return None, None
    weights = {tk: float(w) for tk, w in latest["weights"].items()}
    cash_pct = weights.pop("CASH", 0.0)
    holdings = sorted(({"slug": tk, "pct": w} for tk, w in weights.items()), key=lambda h: -h["pct"])
    return holdings, cash_pct


def _max_dd(history):
    """Max drawdown (%, <=0) over a strategy's own recorded history since league start --
    running-peak method, scale-invariant so it works whether or not a strategy's raw NAV
    literally starts at 100 (aa-strict/spy-bh are mirrored as-is, not rebased)."""
    if not history:
        return 0.0
    peak = history[0]["nav"]
    worst = 0.0
    for h in history:
        peak = max(peak, h["nav"])
        if peak > 0:
            worst = min(worst, (h["nav"] - peak) / peak * 100.0)
    return round(worst, 4)


def _build_report(state):
    rows = []
    for name, spec in STRATEGIES.items():
        strat = state["strategies"][name]
        hist = strat["history"]
        if hist:
            nav = hist[-1]["nav"]
            baseline = hist[0]["nav"]
            return_pct = round((nav / baseline - 1.0) * 100.0, 4) if baseline else 0.0
            max_dd = _max_dd(hist)
            as_of = hist[-1]["date"]
        else:
            nav, return_pct, max_dd, as_of = None, 0.0, 0.0, None
        row = {
            "name": name,
            "label": spec.get("label", name),
            "nav": round(nav, 4) if nav is not None else None,
            "return_pct": return_pct,
            "max_dd": max_dd,
            "as_of": as_of,
        }
        if strat["kind"] == "sizing":
            # holdings detail (2026-07-14, reader asked for "more detail on holdings/performance"):
            # only sizing-v1/v2 have a per-theme breakdown to show -- aa-strict/spy-bh are mirrored
            # black-box NAV lines with no theme-level position data available to this file.
            row["holdings"] = sorted(
                ({"slug": slug, "pct": pos["pct"]} for slug, pos in strat["positions"].items()),
                key=lambda h: -h["pct"])
            row["cash_pct"] = strat["cash_pct"]
        journal_path = spec.get("holdings_from_journal")
        if journal_path:
            # narrative-flow (2026-07-17): unlike sizing-v1/v2, this strategy's current weights
            # live in its own composition journal, not in this file's state -- read the LATEST
            # applicable version's weights straight from there for the same holdings display
            # sizing rows get. Read-only; the journal itself is never written by this file.
            holdings, cash_pct = _narrative_flow_holdings(journal_path)
            if holdings is not None:
                row["holdings"] = holdings
                row["cash_pct"] = cash_pct
        rows.append(row)
    rows.sort(key=lambda r: (r["nav"] is None, -r["return_pct"]))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "league_started_on": state["meta"]["started_on"],
        "strategies": rows,
    }


def _print_report(report):
    print("\n=== 紙上擂台 (Paper League) -- 統一 NAV 對照 ===")
    print(f"開賽日: {report['league_started_on']}   生成時間: {report['generated_at']}")
    header = f"{'排名':<4}{'策略':<12}{'NAV':>10}{'自開賽起%':>12}{'最大回撤%':>12}  最新讀數日"
    print("\n" + header)
    print("-" * (len(header) + 4))
    for i, r in enumerate(report["strategies"], start=1):
        nav_s = f"{r['nav']:.2f}" if r["nav"] is not None else "n/a"
        ret_s = f"{r['return_pct']:+.2f}%"
        dd_s = f"{r['max_dd']:.2f}%"
        print(f"{i:<4}{r['name']:<12}{nav_s:>10}{ret_s:>12}{dd_s:>12}  {r['as_of'] or 'n/a'}")
    print()


def cmd_report():
    state = _load_state()
    if state is None:
        print(f"no state file at {STATE_PATH} -- run --init first.")
        return
    report = _build_report(state)
    _save_report(report)
    _print_report(report)
    print(f"wrote {REPORT_PATH}")


# ============================================================================
# main
# ============================================================================


def main():
    ap = argparse.ArgumentParser(
        description="Unified paper-trading NAV league table across Karst's parallel paper strategies.")
    ap.add_argument("--init", action="store_true",
                     help="register the league (only if thesis/.raw/paper_league_state.json "
                          "doesn't exist yet); captures every strategy's day-0 baseline, no "
                          "history backfill")
    ap.add_argument("--update", action="store_true",
                     help="daily mark of every registered strategy (idempotent within the same "
                          "trading day); also writes the report")
    ap.add_argument("--report", action="store_true",
                     help="print + write thesis/.raw/paper_league_report.json")
    args = ap.parse_args()

    if not (args.init or args.update or args.report):
        ap.print_help()
        return

    if args.init:
        cmd_init()

    ran_report = False
    if args.update:
        cmd_update()
        cmd_report()
        ran_report = True
    if args.report and not ran_report:
        cmd_report()


if __name__ == "__main__":
    main()
