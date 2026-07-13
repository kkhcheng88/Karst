"""thesis/paper_ledger.py -- Karst's OWN paper position ledger (no real capital, no broker
account read anywhere in this file).

Motivation: the dashboard has three gaps (kill-scenario VaR, per-theme target-vs-current gap,
LEAP roll countdown) that all need an "existing position" concept before they can be computed
at all (see thesis/dashboard_render.py's BACKLOG_NOTE). This ledger IS that concept -- but it
records the positions the STRATEGY itself would hold by mechanically following its own signals
(sizing.py's target $ -> converted to %, LEAP legs read from playbook_log.txt), never a human's
real broker holdings. Same blood-line as thesis/aa_strict_paper_tracker.py (paper NAV tracker for
a different structure) -- this one tracks the LIVE core-v2 + Phase-3 structure's own paper
positions, not a shadow structure.

HARD RULE (karst-user-agnostic-system-design, .agents/KARS_MEMORY.md Sec15 + the 2026-07-12
all_active_design_response.md "sizing is %NAV, never $" principle): this file's PERSISTED state
(thesis/paper_ledger.json) and report (thesis/.raw/paper_ledger_report.json) may NEVER contain an
absolute $ amount -- only "% of the satellite sleeve" (satellite sleeve = sizing.py's
DEFAULT_BUDGET, the fixed % denominator; core_leaps are tracked by ticker/expiry/date, not $
cost). sizing.py's own $ figures are used only as an INTERNAL transit value at --init time
(final_$ / budget * 100 -> %), immediately converted and never written back out as $. Both
_save_state() and _save_report() below hard-assert no literal "$" character reaches disk, as a
mechanical backstop for this rule (not just a convention).

State: thesis/paper_ledger.json (COMMITTED to git, like thesis/track_record.jsonl -- this is the
ledger's own accumulated history, not regenerable cache).
  satellite:  {theme_slug: {current_pct, entry_date, last_marked}}   -- current_pct = % of the
              satellite sleeve (sizing.py's DEFAULT_BUDGET), mark-to-market updated daily.
  core_leaps: [{ticker, expiry, entry_date}]                        -- SPY/QQQ LEAP legs, read
              from playbook_log.txt's "leg quote" lines.
  meta:       {initialized_on, last_update}

Report: thesis/.raw/paper_ledger_report.json (regenerable any time from state + current
sizing.py/themes.yaml reads -- NOT committed, same convention as beta_check_report.json).

Run:
  python thesis/paper_ledger.py --init      # only when paper_ledger.json doesn't exist yet
  python thesis/paper_ledger.py --update    # daily mark-to-market (idempotent same trading day)
  python thesis/paper_ledger.py --report    # also runs automatically at the end of --update
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone

import pandas as pd

ROOT = os.path.dirname(os.path.abspath(__file__))          # thesis/
REPO_ROOT = os.path.dirname(ROOT)                            # Karst/
sys.path.insert(0, ROOT)
sys.path.insert(0, REPO_ROOT)
import beta_check as beta_check_mod  # noqa: E402 -- sibling module, reused build_basket() as-is
import sizing as sizing_mod          # noqa: E402 -- sibling module, reused load_themes/load_judge/build_table

STATE_PATH = os.path.join(ROOT, "paper_ledger.json")
REPORT_PATH = os.path.join(ROOT, ".raw", "paper_ledger_report.json")
PLAYBOOK_LOG = os.path.join(REPO_ROOT, "playbook_log.txt")
# v* not v0 (2026-07-13): thesis/valuation.py production v1 writes *_expectations_gap_v1.md in
# the same table format; sorted() date-prefix ordering picks the newest run automatically.
EXP_GAP_GLOB = os.path.join(REPO_ROOT, "backtest", "results", "*_expectations_gap_v*.md")

ROLL_WARN_DAYS = 90          # spec: <=90 calendar days to expiry -> roll warning
GAP_ACTION_THRESHOLD = 1.0   # spec: |gap_pct| > 1pp -> ADD/TRIM, else HOLD

# regex reference: thesis/dashboard_render.py's LEAP_QUOTE_RE / EXPGAP_ROW_RE / last_block()
# (copied here self-contained rather than imported, to avoid coupling to dashboard_render.py's
# unrelated module-level state e.g. its NOW=datetime.now() global and Telegram/git side modules).
LEAP_QUOTE_RE = re.compile(
    r"^(?P<ticker>SPY|QQQ) leg quote: (?P<expiry>\S+) \((?P<dte>\d+)d\) K=(?P<strike>[\d.]+) "
    r"delta=(?P<delta>[\d.]+) mid=(?P<mid>[\d.]+) \(1 contract = \$(?P<cost>[\d,]+)\)", re.MULTILINE)
EXPGAP_ROW_RE = re.compile(
    # NOTE: dashboard_render.py's own EXPGAP_ROW_RE uses `[\d.]+` (no leading '-') for pbase,
    # which silently drops every N/A-binary row (their P_base is negative, e.g. "-0.08x") --
    # harmless there today (dashboard_render.py never reads .get(slug) for those specific slugs
    # in a way that changes behavior) but worth not reproducing here since kill_var downside
    # classification DOES branch on this value; `-?` added so negative P_base rows parse too.
    r"^\|\s*(?P<slug>[a-z][a-z0-9-]+)\s*\|\s*(?P<ticker>\S+)\s*\|\s*(?P<pbase>-?[\d.]+)x\s*\|"
    r"\s*(?P<cls>[^|]+?)\s*\|\s*$", re.MULTILINE)

# ============================================================================
# Kill-scenario downside-by-cycle-stage table (SIMPLIFIED 3-tier collapse of the real per-theme
# table). ORIGIN: docs/2026-07-12_fable_investment_logic_review.md Sec2.1 item 4 ("Kill-scenario
# 壓力數(meta-factor VaR)" -- "用 sizing MC 同一張 downside 表計"), whose underlying full table
# lives in backtest/results/2026-07-12_sizing_two_axis_decision_analysis.md ("15 個 theme 的
# magnitude/downside 假設表", explicitly flagged ASSUMPTION not measurement there). That table's
# per-theme downsides cluster into three bands: event_binary rows = -80% exactly; late_priced rows
# = -50% (or -45%/-40% at the cushioned/heterogeneous edge); mid/early_cheap rows = -35%. This
# ledger uses the coarser 3-bucket version the spec calls for (matches the modal value of each
# band, not each theme's individually-adjusted number) -- a deliberate v1 simplification, not a
# re-derivation of the MC analysis.
# ============================================================================
DOWNSIDE_EVENT_DRIVEN = 0.80
DOWNSIDE_LATE_OR_MOSTLY_HOPE = 0.50
DOWNSIDE_DEFAULT = 0.35
EXPGAP_MOSTLY_HOPE_LABEL = "大部分係希望"
EXPGAP_BINARY_LABEL = "N/A-binary (option framing)"


# ============================================================================
# small helpers
# ============================================================================


def _read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def _today_str():
    return datetime.now().date().isoformat()


def _parse_date(s):
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _no_dollar_guard(obj, path):
    """Mechanical backstop for the %-only rule (see module docstring): refuse to write a file if
    a literal '$' character would land in it anywhere (values or keys)."""
    text = json.dumps(obj, ensure_ascii=False)
    if "$" in text:
        raise ValueError(
            f"refusing to write {path}: payload contains a literal '$' -- paper_ledger.py's "
            "state/report files are %-of-satellite-sleeve only, never absolute $ amounts "
            "(karst-user-agnostic-system-design principle). Fix the code path that let a $ "
            "figure leak past the %-conversion step.")


def _load_state():
    if not os.path.exists(STATE_PATH):
        return None
    with open(STATE_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _save_state(state):
    _no_dollar_guard(state, STATE_PATH)
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def _save_report(report):
    _no_dollar_guard(report, REPORT_PATH)
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)


# ============================================================================
# readers: playbook_log.txt (LEAP legs) / expectations-gap snapshot / sizing targets
# ============================================================================


def read_playbook_leaps():
    """Read the latest live SPY/QQQ LEAP leg quotes from playbook_log.txt.

    playbook_log.txt is appended to by several independent scheduled jobs, each writing its own
    '==== ... ====' header block (Core-v2 playbook readout, AA-strict paper tracker, premarket
    check, ...) -- so the literal LAST block in the file is not necessarily the last one with a
    LEAP quote (dashboard_render.py's last_block() convention, replicated here). Scans blocks from
    the end and returns the first (i.e. most recent) one containing 'leg quote' lines.

    Returns {ticker: {"expiry": str, "dte_at_quote": int, "block_date": "YYYY-MM-DD"|None}} for
    whichever of SPY/QQQ have a quote in that block, or {} if none found yet.
    """
    text = _read_text(PLAYBOOK_LOG)
    if not text:
        return {}
    parts = re.split(r"(?=^==== .+ ====\s*$)", text, flags=re.MULTILINE)
    for part in reversed(parts):
        matches = list(LEAP_QUOTE_RE.finditer(part))
        if not matches:
            continue
        header_m = re.match(r"^==== (.+?) ====", part)
        block_date = None
        if header_m:
            # header is either ISO ("2026-07-08 16:54") or Chinese-weekday+slash
            # ("週三 2026/07/08 16:51:29.76") -- try both, normalize to ISO.
            dm = re.search(r"(\d{4})-(\d{2})-(\d{2})", header_m.group(1))
            if not dm:
                dm = re.search(r"(\d{4})/(\d{2})/(\d{2})", header_m.group(1))
            if dm:
                block_date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}"
        out = {}
        for m in matches:
            out[m.group("ticker")] = {
                "expiry": m.group("expiry"),
                "dte_at_quote": int(m.group("dte")),
                "block_date": block_date,
            }
        return out
    return {}


def load_expectations_gap():
    """Latest one-off expectations-gap snapshot (backtest/results/*_expectations_gap_v0.md) --
    theme -> classification string (e.g. '大部分係希望'). Parse approach mirrors
    dashboard_render.py's load_expectations_gap() (same file, same "## Theme-level rollup"
    section, same row regex), replicated self-contained here. {} if no result file exists yet."""
    matches = sorted(glob.glob(EXP_GAP_GLOB))
    if not matches:
        return {}
    text = _read_text(matches[-1])
    if not text:
        return {}
    section = text.split("## Theme-level rollup", 1)
    body = section[1] if len(section) > 1 else text
    body = body.split("\n## ", 1)[0]
    out = {}
    for m in EXPGAP_ROW_RE.finditer(body):
        out[m.group("slug")] = m.group("cls").strip()
    return out


def compute_sizing_targets():
    """Current sizing.py target, converted to % of the satellite budget immediately (the $
    figures from sizing.py are a pure transit value here, per the module-level %-only rule)."""
    themes = sizing_mod.load_themes()
    judge = sizing_mod.load_judge()
    status = judge.get("status", "PRELIMINARY")
    circuit_breaker = bool(judge.get("circuit_breaker", False)) or status == "FAIL"
    budget = sizing_mod.DEFAULT_BUDGET
    rows, _cut_log, _total_cap, _total_factor = sizing_mod.build_table(
        themes, status, circuit_breaker, budget)
    target_pct = {r["slug"]: (r["final"] / budget * 100.0) if budget else 0.0 for r in rows}
    return themes, target_pct, budget


def theme_downside(theme, exp_gap_classification):
    """Kill-scenario downside fraction for one theme -- see the DOWNSIDE_* constants above for
    the origin/citation. Priority: binary (0.80) checked first -- BOTH cycle_stage=='event-driven'
    AND expectations-gap 'N/A-binary (option framing)' land here (2026-07-13 brain review: the
    option-framing class means every computed ticker is pre-profit/E_norm<=0, i.e. exactly the
    lottery profile the Fable table's binary -80% row describes; the original spec only keyed on
    cycle_stage and under-assumed 0.35 for e.g. space-satellite) -- then late-cycle OR
    expectations-gap 'mostly hope' (0.50), else the default (0.35)."""
    cycle = theme.get("cycle_stage")
    if cycle == "event-driven" or exp_gap_classification == EXPGAP_BINARY_LABEL:
        return DOWNSIDE_EVENT_DRIVEN
    if cycle == "late" or exp_gap_classification == EXPGAP_MOSTLY_HOPE_LABEL:
        return DOWNSIDE_LATE_OR_MOSTLY_HOPE
    return DOWNSIDE_DEFAULT


# ============================================================================
# --init
# ============================================================================


def cmd_init():
    if os.path.exists(STATE_PATH):
        print(f"state already exists at {STATE_PATH} -- --init only runs when the state file is "
              "missing (use --update for daily marks). No change made.")
        return

    themes, target_pct, budget = compute_sizing_targets()
    today = _today_str()

    satellite = {}
    for slug, t in themes.items():
        if t.get("status", "active") != "active":
            continue
        pct = target_pct.get(slug, 0.0)
        satellite[slug] = {"current_pct": round(pct, 4), "entry_date": today, "last_marked": today}

    leaps_raw = read_playbook_leaps()
    core_leaps = []
    for ticker in ("SPY", "QQQ"):
        info = leaps_raw.get(ticker)
        if not info:
            continue
        core_leaps.append({
            "ticker": ticker,
            "expiry": info["expiry"],
            # entry_date here = the date this exact strike/expiry was last CONFIRMED live in
            # playbook_log.txt (the block's own header date) -- not a literal option-open trade
            # date, since playbook_log.txt doesn't retain full roll history. Closest honest
            # anchor available; bumped forward on --update if/when the expiry itself rolls.
            "entry_date": info["block_date"] or today,
        })

    state = {
        "satellite": satellite,
        "core_leaps": core_leaps,
        "meta": {"initialized_on": today, "last_update": today},
    }
    _save_state(state)

    total_pct = sum(v["current_pct"] for v in satellite.values())
    print(f"initialized {STATE_PATH}")
    print(f"satellite themes: {len(satellite)}  total current_pct: {total_pct:.2f}% "
          f"(of the satellite sleeve; sizing.py budget={budget:,.0f} used only as internal % transit)")
    if core_leaps:
        for leg in core_leaps:
            print(f"  core_leaps: {leg['ticker']} {leg['expiry']} (entry {leg['entry_date']})")
    else:
        print("  WARNING: no core LEAP legs found in playbook_log.txt yet ('leg quote' lines "
              "missing) -- core_leaps left empty, will pick up on the next --update.")


# ============================================================================
# --update (daily mark-to-market, idempotent same trading day)
# ============================================================================


def cmd_update():
    state = _load_state()
    if state is None:
        print(f"no state file at {STATE_PATH} -- run --init first.")
        return

    themes, target_pct, _budget = compute_sizing_targets()
    today = _today_str()
    notes = []
    changed = False

    for slug, pos in state["satellite"].items():
        theme = themes.get(slug)
        if theme is None:
            notes.append(f"{slug}: no longer in themes.yaml's active set -- left unmarked "
                          "(paper position stays open until a session explicitly closes it)")
            continue
        if theme.get("status", "active") != "active":
            notes.append(f"{slug}: status != active -- left unmarked")
            continue
        tickers = theme.get("tickers") or []
        if not tickers:
            notes.append(f"{slug}: no tickers to build a mark-to-market basket from -- left unmarked")
            continue

        basket_ret, loaded, failed = beta_check_mod.build_basket(tickers)
        if basket_ret is None or len(basket_ret) == 0:
            notes.append(f"{slug}: basket load failed (loaded={loaded}, failed={failed}) -- left unmarked")
            continue

        cum = (1.0 + basket_ret).cumprod()
        today_trading_str = cum.index[-1].date().isoformat()
        if pos.get("last_marked") == today_trading_str:
            continue  # idempotent -- already marked as of this trading day

        ratio = None
        last_marked = pos.get("last_marked")
        if last_marked:
            anchor_ts = pd.Timestamp(last_marked)
            prior = cum[cum.index <= anchor_ts]
            if len(prior):
                ratio = float(cum.iloc[-1] / prior.iloc[-1])
        if ratio is None:
            # no anchor row found in the basket's own loaded history (e.g. entry predates the
            # basket's earliest loaded price) -- fall back to the latest single-day return
            # rather than silently compounding against nothing.
            ratio = float(1.0 + basket_ret.iloc[-1])

        pos["current_pct"] = round(pos["current_pct"] * ratio, 4)
        pos["last_marked"] = today_trading_str
        changed = True

    # pick up any theme newly admitted to themes.yaml since the ledger last ran (fresh baseline
    # at its current sizing target -- mirrors --init's own logic for a single new theme).
    for slug, t in themes.items():
        if t.get("status", "active") != "active" or slug in state["satellite"]:
            continue
        state["satellite"][slug] = {
            "current_pct": round(target_pct.get(slug, 0.0), 4),
            "entry_date": today, "last_marked": today,
        }
        notes.append(f"{slug}: newly active theme -- added to ledger at its current sizing target")
        changed = True

    # refresh core_leaps expiry (idempotent unless a real roll happened between updates).
    core_leaps_now = read_playbook_leaps()
    for leg in state["core_leaps"]:
        info = core_leaps_now.get(leg["ticker"])
        if info and info["expiry"] != leg["expiry"]:
            notes.append(f"{leg['ticker']}: expiry rolled {leg['expiry']} -> {info['expiry']}")
            leg["expiry"] = info["expiry"]
            leg["entry_date"] = info["block_date"] or today
            changed = True
    if not state["core_leaps"] and core_leaps_now:
        for ticker in ("SPY", "QQQ"):
            info = core_leaps_now.get(ticker)
            if info:
                state["core_leaps"].append({
                    "ticker": ticker, "expiry": info["expiry"],
                    "entry_date": info["block_date"] or today})
                changed = True

    state["meta"]["last_update"] = today
    _save_state(state)

    print(f"update complete ({'state changed' if changed else 'idempotent -- no change'}).")
    for n in notes:
        print(f"  note: {n}")


# ============================================================================
# --report
# ============================================================================


def cmd_report():
    state = _load_state()
    if state is None:
        print(f"no state file at {STATE_PATH} -- run --init first.")
        return

    themes, target_pct, _budget = compute_sizing_targets()
    exp_gap = load_expectations_gap()

    theme_rows = []
    kill_var_pct = 0.0
    for slug, t in themes.items():
        if t.get("status", "active") != "active":
            continue
        current_pct = float(state["satellite"].get(slug, {}).get("current_pct", 0.0))
        tgt = float(target_pct.get(slug, 0.0))
        gap = tgt - current_pct
        if gap > GAP_ACTION_THRESHOLD:
            action = "ADD"
        elif gap < -GAP_ACTION_THRESHOLD:
            action = "TRIM"
        else:
            action = "HOLD"
        exp_cls = exp_gap.get(slug)
        downside = theme_downside(t, exp_cls)
        kill_var_pct += current_pct * downside
        theme_rows.append({
            "slug": slug,
            "target_pct": round(tgt, 4),
            "current_pct": round(current_pct, 4),
            "gap_pct": round(gap, 4),
            "action": action,
            "downside_assumption": downside,
            "expectations_gap_classification": exp_cls,
        })
    theme_rows.sort(key=lambda r: -r["target_pct"])

    today = datetime.now().date()
    core_leaps_out = []
    for leg in state.get("core_leaps", []):
        exp = _parse_date(leg["expiry"])
        dte = (exp - today).days if exp else None
        core_leaps_out.append({
            "ticker": leg["ticker"],
            "expiry": leg["expiry"],
            "entry_date": leg["entry_date"],
            "days_to_expiry": dte,
            "roll_warn": bool(dte is not None and dte <= ROLL_WARN_DAYS),
        })

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "themes": theme_rows,
        "kill_var_pct": round(kill_var_pct, 4),
        "core_leaps": core_leaps_out,
        "satellite_deployed_pct": round(sum(r["current_pct"] for r in theme_rows), 4),
    }
    _save_report(report)

    print(f"wrote {REPORT_PATH}")
    print(f"satellite deployed: {report['satellite_deployed_pct']:.2f}% of sleeve  |  "
          f"kill_var_pct: {report['kill_var_pct']:.2f}% of sleeve")
    for leg in core_leaps_out:
        warn = "  *** ROLL WARN (<=90d) ***" if leg["roll_warn"] else ""
        print(f"  core_leaps: {leg['ticker']} {leg['expiry']}  {leg['days_to_expiry']}d to expiry{warn}")


# ============================================================================
# main
# ============================================================================


def main():
    ap = argparse.ArgumentParser(
        description="Karst's own paper position ledger (no real capital, %-of-satellite-sleeve only).")
    ap.add_argument("--init", action="store_true",
                     help="create thesis/paper_ledger.json from sizing.py's current targets + "
                          "playbook_log.txt's current LEAP legs (only if the state file doesn't exist yet)")
    ap.add_argument("--update", action="store_true",
                     help="daily mark-to-market of the satellite themes (idempotent within the "
                          "same trading day) + refresh core_leaps expiry; also writes the report")
    ap.add_argument("--report", action="store_true",
                     help="write thesis/.raw/paper_ledger_report.json (target-vs-current gap per "
                          "theme, kill-scenario VaR, LEAP roll countdown)")
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
