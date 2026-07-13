"""thesis/dashboard_render.py — Karst Dashboard v4 render + publish
(docs/2026-07-13_dashboard_v4_portable.md, docs/2026-07-12_dashboard_design_v3.md).

Pure AGGREGATION of existing output files/functions -- computes nothing that isn't already
produced by an existing scheduled script (v4 doc Sec3 point 1: "唔起新計算,純聚合現有檔").
Two exceptions, both trivial calendar/derived arithmetic rather than new investment signals:
  - top-up countdown: next month's first weekday (approximate, does not account for market
    holidays -- no trading-calendar utility exists in this repo yet).
  - meta_factor $ share: groups sizing.py's own already-computed per-theme final $ by
    meta_factor (same computation sizing.py's apply_meta_factor_cut already does internally;
    this just re-exposes the grouping for display).

Honesty rule (v3 design principle 5, NHITL "唔扮有" -- see memory karst-role-nhitl-decision-
support): any v4-design element with no real computed source yet (opportunity-ladder tier,
A/B/C/D radar, kill-scenario VaR, ballast quarterly health-check, roll countdown, position
ledger target-vs-current) renders as an explicit "未接線" placeholder, never a fabricated
number. See the file's own "未接線 backlog" footer for the live list.

Publish target: this script writes DASHBOARD.md into thesis/../.dashboard_mirror/ -- a SEPARATE
git worktree checked out on the `github-main` branch (tracks origin/main, the curated
engine-only snapshot pushed 2026-07-13). This is deliberate: the research branch
(karst-dashboard-and-regime-research) and origin/main now have UNRELATED histories (origin/main
was force-pushed from a scoped orphan commit) -- committing DASHBOARD.md on the research branch
and pushing to origin/main would drag the entire research history along again, exactly the bulk
push the user scoped this remote to avoid. The mirror worktree keeps the two histories separate.

Run: python thesis/dashboard_render.py --mode morning|evening [--no-git] [--no-telegram]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))          # thesis/
REPO_ROOT = os.path.dirname(ROOT)                            # Karst/
MIRROR_ROOT = os.path.join(REPO_ROOT, ".dashboard_mirror")
sys.path.insert(0, ROOT)
import sizing as sizing_mod  # noqa: E402 -- sibling module, reused pure functions, no new calc

PLAYBOOK_LOG = os.path.join(REPO_ROOT, "playbook_log.txt")
PREMARKET_LOG = os.path.join(REPO_ROOT, "premarket_log.txt")
AA_LOG = os.path.join(ROOT, ".raw", "aa_strict_paper_log.jsonl")
BETA_REPORT = os.path.join(ROOT, ".raw", "beta_check_report.json")
CONSTRAINT_QUEUE = os.path.join(ROOT, ".raw", "constraint_scan_queue.md")
MAGNIFIER_QUEUE = os.path.join(ROOT, ".raw", "magnifier_review_queue.md")
PENDING_ANALYSIS = os.path.join(REPO_ROOT, "..", "Reference", "raw_data",
                                 "backtest_everything_transcripts", "_PENDING_ANALYSIS.md")
TELEGRAM_CRED = os.path.expanduser("~/.config/karst/telegram")
GITHUB_FILE_URL = "https://github.com/kkhcheng88/Karst/blob/main/DASHBOARD.md"

NOW = datetime.now(timezone.utc)

# ============================================================================
# parsing helpers
# ============================================================================


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def last_block(text, marker):
    """Split `text` on '==== ... ====' header lines; return (block, header_str) for the LAST
    block that contains `marker`, or (None, None). Different scripts append independently to
    the same log file with their own headers, so different blocks can legitimately have
    different (staleness-revealing) dates -- that's surfaced to the reader, not hidden."""
    if not text:
        return None, None
    parts = re.split(r"(?=^==== .+ ====\s*$)", text, flags=re.MULTILINE)
    for part in reversed(parts):
        if marker in part:
            m = re.match(r"^==== (.+?) ====", part)
            return part, (m.group(1) if m else None)
    return None, None


SPY_RE = re.compile(
    r"^SPY: close\((?P<date>\S+)\)=(?P<close>[\d.]+)\s+200SMA=(?P<sma>[\d.]+)\s+"
    r"(?P<side>ABOVE|BELOW)\s+\((?P<pct>[+-][\d.]+)%\)\s+(?P<cross>.+?)\s*$", re.MULTILINE)
QQQ_RE = re.compile(
    r"^QQQ: close\((?P<date>\S+)\)=(?P<close>[\d.]+)\s+200SMA=(?P<sma>[\d.]+)\s+"
    r"(?P<side>ABOVE|BELOW)\s+\((?P<pct>[+-][\d.]+)%\)\s+(?P<cross>.+?)\s*$", re.MULTILINE)
VIX_RE = re.compile(
    r"^VIX=(?P<vix>[\d.]+)\s+\(M1 panic window: (?P<m1>\w+)\)\s+SPY RSI-2=(?P<rsi2>[\d.]+)\s+"
    r"\(M3 sell-call: (?P<m3>\w+)\)\s+\^IRX=(?P<irx>[\d.]+)%", re.MULTILINE)
CRISIS_RE = re.compile(r"^CRISIS SLEEVE: (?P<state>.+?)\s*$", re.MULTILINE)
BUYZONE_RE = re.compile(r"^BUY-ZONE: (?P<v>.+?)\s*$", re.MULTILINE)
ACCUM_RE = re.compile(r"^ACCUMULATE: (?P<v>.+?)\s*$", re.MULTILINE)
KILLWATCH_RE = re.compile(r"^KILL-WATCH: (?P<v>.+?)\s*$", re.MULTILINE)
THEME_ROW_RE = re.compile(
    r"^(?P<slug>[a-z][a-z0-9-]+)\s+(?P<cycle>\S+)\s+(?P<pe>\S+)\s+(?P<vs200>\S+)\s+"
    r"(?P<pos52>\S+)\s+(?P<verdict>BUY-ZONE|ACCUMULATE|WAIT|KILL-WATCH)\s*$", re.MULTILINE)


def _slug_list(raw):
    raw = raw.strip()
    return [] if raw == "(none)" else [s.strip() for s in raw.split(",")]


def parse_core_block(block):
    """Extract SPY/QQQ 200SMA gate status, VIX/RSI-2/crisis-sleeve, and per-theme verdicts
    from a playbook_readout.py + theme_signal.py combined log block."""
    out = {"spy": None, "qqq": None, "vix": None, "crisis": None,
           "buy_zone": [], "accumulate": [], "kill_watch": [], "theme_rows": {}}
    if not block:
        return out
    m = SPY_RE.search(block)
    if m:
        out["spy"] = m.groupdict()
    m = QQQ_RE.search(block)
    if m:
        out["qqq"] = m.groupdict()
    m = VIX_RE.search(block)
    if m:
        out["vix"] = m.groupdict()
    m = CRISIS_RE.search(block)
    if m:
        out["crisis"] = m.group("state").strip()
    m = BUYZONE_RE.search(block)
    if m:
        out["buy_zone"] = _slug_list(m.group("v"))
    m = ACCUM_RE.search(block)
    if m:
        out["accumulate"] = _slug_list(m.group("v"))
    m = KILLWATCH_RE.search(block)
    if m:
        out["kill_watch"] = _slug_list(m.group("v"))
    for m in THEME_ROW_RE.finditer(block):
        out["theme_rows"][m.group("slug")] = m.groupdict()
    return out


PREMKT_ROW_RE = re.compile(
    r"^(?P<ticker>\S+)\s+close (?P<close>[\d.]+) -> PREMKT (?P<premkt>[\d.]+) "
    r"\((?P<pct>[+-][\d.]+)%\).*?200SMA (?P<sma>[\d.]+|n/a) gate (?P<gate>ON|OFF)\s*\n"
    r"\s*-> (?P<verdict>.+?)\s*$", re.MULTILINE)


def parse_premarket_block(block):
    out = {}
    if not block:
        return out
    for m in PREMKT_ROW_RE.finditer(block):
        out[m.group("ticker")] = m.groupdict()
    return out


def load_aa_latest():
    text = read_text(AA_LOG)
    if not text:
        return None
    lines = [l for l in text.strip().split("\n") if l.strip()]
    if not lines:
        return None
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError:
        return None


def load_beta_report():
    text = read_text(BETA_REPORT)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def count_checklist_pending(path):
    text = read_text(path)
    if text is None:
        return None
    return len(re.findall(r"^- \[ \]", text, flags=re.MULTILINE))


EXPGAP_ROW_RE = re.compile(
    r"^\|\s*(?P<slug>[a-z][a-z0-9-]+)\s*\|\s*(?P<ticker>\S+)\s*\|\s*(?P<pbase>[\d.]+)x\s*\|"
    r"\s*(?P<cls>[^|]+?)\s*\|\s*$", re.MULTILINE)


def load_expectations_gap():
    """Parse the latest one-off expectations-gap markdown result (backtest/results/
    *_expectations_gap_v0.md) -- historical snapshot, NOT recomputed live. Returns
    (slug -> {p_base, classification}, as_of_date) or ({}, None) if no result file exists."""
    matches = sorted(glob.glob(os.path.join(REPO_ROOT, "backtest", "results",
                                             "*_expectations_gap_v0.md")))
    if not matches:
        return {}, None
    path = matches[-1]
    fname = os.path.basename(path)
    as_of = fname[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", fname) else None
    text = read_text(path)
    if not text:
        return {}, as_of
    section = text.split("## Theme-level rollup", 1)
    body = section[1] if len(section) > 1 else text
    body = body.split("\n## ", 1)[0]
    out = {}
    for m in EXPGAP_ROW_RE.finditer(body):
        out[m.group("slug")] = {"p_base": m.group("pbase"), "classification": m.group("cls").strip()}
    return out, as_of


def days_since(date_str):
    if not date_str:
        return None
    s = str(date_str)[:10]
    try:
        d = datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return None
    return (NOW.replace(tzinfo=None) - d).days


def next_topup_date():
    """First weekday of next month -- APPROXIMATE, no market-holiday calendar exists in this
    repo. Purely calendar arithmetic, not an investment computation."""
    today = NOW.date()
    if today.month == 12:
        first = today.replace(year=today.year + 1, month=1, day=1)
    else:
        first = today.replace(month=today.month + 1, day=1)
    while first.weekday() >= 5:  # Sat=5, Sun=6
        first += timedelta(days=1)
    return first


# ============================================================================
# sizing / concentration / beta (imported pure functions -- no re-implementation)
# ============================================================================


def compute_sizing():
    themes = sizing_mod.load_themes()
    judge = sizing_mod.load_judge()
    status = judge.get("status", "PRELIMINARY")
    circuit_breaker = bool(judge.get("circuit_breaker", False)) or status == "FAIL"
    budget = sizing_mod.DEFAULT_BUDGET
    rows, cut_log, total_cap, total_factor = sizing_mod.build_table(
        themes, status, circuit_breaker, budget)
    return {"themes": themes, "judge": judge, "status": status,
            "circuit_breaker": circuit_breaker, "budget": budget, "rows": rows,
            "cut_log": cut_log, "total_cap": total_cap, "total_factor": total_factor}


def meta_factor_shares(themes, rows, total_cap):
    by_slug = {r["slug"]: r for r in rows}
    groups = {}
    for slug, t in themes.items():
        if slug not in by_slug:
            continue
        for mf in (t.get("meta_factors") or []):
            g = groups.setdefault(mf, {"themes": [], "final": 0.0})
            g["themes"].append(slug)
            g["final"] += by_slug[slug]["final"]
    out = []
    for mf, g in groups.items():
        pct = (g["final"] / total_cap * 100.0) if total_cap else 0.0
        out.append({"meta_factor": mf, "themes": g["themes"], "final": g["final"], "pct": pct})
    out.sort(key=lambda r: -r["pct"])
    return out


# ============================================================================
# markdown row builders
# ============================================================================

MAGNIFIER_SEEN = None  # sentinel; magnifier_review_queue.md legitimately may not exist yet


def build_row0(mode, core, core_date, premkt, premkt_date, aa_latest, judge_info):
    lines = ["## ROW 0 — 今日行動條", ""]
    if mode == "evening" and premkt:
        lines.append("> ⚠ **PREMARKET 預覽,收市判定為準**(price triggers 用 premarket 價,"
                      "非收市價;確定行動請等收市版)")
        lines.append("")
        for tk in ("SPY", "QQQ"):
            r = premkt.get(tk)
            if r:
                lines.append(f"- **{tk}** premarket {r['premkt']} ({r['pct']}%, close {r['close']}) "
                              f"| 200SMA={r['sma']} gate {r['gate']} | {r['verdict']}")
            else:
                lines.append(f"- **{tk}**: 未讀到 premarket 數(見 `premarket_log.txt`)")
        premkt_ts_m = re.match(r"PREMARKET CHECK (\S+ \S+)", premkt_date or "")
        lines.append(f"\n_premarket 讀數時間:{premkt_ts_m.group(1) if premkt_ts_m else (premkt_date or '—')}_")
    else:
        lines.append(f"_核心閘讀數截至:{core_date or '(未讀到 playbook_log.txt)'}_\n")
        for tk in ("spy", "qqq"):
            r = core.get(tk)
            if r:
                fresh = "🟡" if "FRESH-CROSS" in r["cross"] or "cross" in r["cross"].lower() else "🟢" if r["side"] == "ABOVE" else "🔴"
                lines.append(f"- **{tk.upper()}** vs 200SMA: {fresh} {r['side']} ({r['pct']}%) "
                              f"— {r['cross']} (close {r['close']} @ {r['date']})")
            else:
                lines.append(f"- **{tk.upper()}**: 未讀到(見 `playbook_log.txt`)")
        vix = core.get("vix")
        if vix:
            lines.append(f"- VIX={vix['vix']} (M1 恐慌窗: {vix['m1']}) | SPY RSI-2={vix['rsi2']} "
                          f"(M3 sell-call: {vix['m3']}) | ^IRX={vix['irx']}%")
        crisis = core.get("crisis")
        crisis_icon = "⚪" if crisis and crisis.startswith("DISARMED") else ("🔴" if crisis else "—")
        lines.append(f"- 危機 sleeve: {crisis_icon} {crisis or '未讀到'}")

    lines.append(f"- Roll 倒數(LEAP到期): —(需台帳:未有實際持倉到期日記錄,見 footer backlog)")
    lines.append(f"- Top-up 倒數:下個月首個交易日 ≈ {next_topup_date().isoformat()} "
                  f"(近似,未計市場假期)")

    if aa_latest:
        legs = aa_latest.get("n_legs_off")
        lines.append(f"- **AA-strict 並行(紙上,不郁真錢)** — regime: {legs} leg(s) off 200SMA, "
                      f"band={aa_latest.get('band')}, 目標delta={aa_latest.get('leap_target_delta', 0):.1%} "
                      f"| NAV: AA {aa_latest.get('aa_paper_nav'):.2f} vs SPY B&H {aa_latest.get('spy_bh_nav'):.2f} "
                      f"(as of {aa_latest.get('date')})")
    else:
        lines.append("- AA-strict 並行:未讀到(見 `thesis/.raw/aa_strict_paper_log.jsonl`)")

    status = judge_info["status"]
    cb = judge_info["circuit_breaker"]
    thresholds = judge_info.get("thresholds", {})
    matured = judge_info.get("matured", 0)
    need = thresholds.get("preliminary_matured_min", 60)
    status_icon = "🔴" if (status == "FAIL" or cb) else "🟡" if status == "PRELIMINARY" else "🟢"
    lines.append(f"- 裁判: {status_icon} {status}{'  ⚠ 熔斷' if cb else ''} "
                  f"(matured {matured}/{need})")

    kw = core.get("kill_watch") or []
    lines.append(f"- KILL-WATCH 主題數: {'🔴' if kw else '⚪'} {len(kw)}"
                  + (f" ({', '.join(kw)})" if kw else ""))
    return "\n".join(lines)


def build_row1(sizing_info, mf_shares, beta_report):
    lines = ["## ROW 1 — 風險條", ""]
    total_final = sum(r["final"] for r in sizing_info["rows"])
    lines.append(f"- 部署 vs 上限: **${total_final:,.0f} / ${sizing_info['total_cap']:,.0f}** "
                 f"({sizing_info['status']}狀態,{sizing_info['total_cap']/sizing_info['budget']*100:.0f}% of budget)")
    if mf_shares:
        top = mf_shares[0]
        icon = "🔴" if top["pct"] > 75 else "🟡" if top["pct"] > 60 else "⚪"
        lines.append(f"- 最大 meta_factor 集中: {icon} '{top['meta_factor']}' "
                     f"{top['pct']:.0f}% of 部署上限 ({', '.join(top['themes'])})")
    else:
        lines.append("- meta_factor 集中: 無部署中主題")
    lines.append("- Kill-scenario VaR($): —(需台帳:未有實際持倉,見 footer backlog)")

    if beta_report:
        flagged = beta_report.get("flagged") or []
        gen = beta_report.get("generated_at", "")[:10]
        stale = ""
        d = days_since(gen)
        if d is not None and d > 8:
            stale = f" ⚠ 讀數已 {d} 日未更新(週更 script 可能未跑)"
        icon = "🟡" if flagged else "⚪"
        lines.append(f"- Beta化警戒: {icon} {len(flagged)} 主題"
                     f"{(' (' + ', '.join(flagged) + ')') if flagged else ''} "
                     f"(as of {gen or '—'}{stale})")
    else:
        lines.append("- Beta化警戒: —(未讀到 `thesis/.raw/beta_check_report.json`,"
                     "要先跑一次 `python thesis/beta_check.py`)")
    lines.append("- 數據哨兵: —(未接線,design-only,見 footer backlog)")
    return "\n".join(lines)


def build_row2(sizing_info, core, exp_gap, exp_gap_date):
    lines = ["## ROW 2 — 主題作戰台(按 target $ 排;current/Δ 待台帳)", ""]
    themes = sizing_info["themes"]
    rows = sorted(sizing_info["rows"], key=lambda r: -r["final"])
    lines.append("| theme | conf | mag tier | stage | verdict | exp-gap | target $ | kill條件(節錄) | 新鮮度 |")
    lines.append("|---|---:|---|---|---|---|---:|---|---:|")
    for r in rows:
        slug = r["slug"]
        t = themes.get(slug, {})
        nodes = t.get("nodes")
        mag = nodes[0].get("magnitude_tier", "—") if nodes else "—(theme級,未跑per-node)"
        stage = t.get("cycle_stage", "—")
        theme_row = core.get("theme_rows", {}).get(slug)
        verdict = theme_row["verdict"] if theme_row else (
            "KILL-WATCH" if slug in core.get("kill_watch", []) else
            "ACCUMULATE" if slug in core.get("accumulate", []) else
            "BUY-ZONE" if slug in core.get("buy_zone", []) else "—")
        eg = exp_gap.get(slug)
        eg_s = f"{eg['p_base']}x {eg['classification']}" if eg else "—"
        kill = (t.get("kill_condition") or "")[:70]
        kill = (kill + "…") if len(t.get("kill_condition") or "") > 70 else kill
        fresh_d = days_since(t.get("last_evidence"))
        fresh_s = f"{fresh_d}d" + (" ⚠" if fresh_d is not None and fresh_d > 90 else "") if fresh_d is not None else "—"
        lines.append(f"| {slug} | {r['confidence']:.2f} | {mag} | {stage} | {verdict} | {eg_s} | "
                     f"${r['final']:,.0f} | {kill} | {fresh_s} |")
    if exp_gap_date:
        lines.append(f"\n_exp-gap 欄:歷史快照 as of {exp_gap_date}(一次性分析,非即時計算;"
                     "見 backtest/results/*_expectations_gap_v0.md)_")
    watch = [slug for slug, t in themes.items() if t.get("status") == "watch"]
    if watch:
        lines.append(f"\nwatchlist ({len(watch)}): {', '.join(watch)}")
    return "\n".join(lines)


def build_row3(sizing_info, queues):
    lines = ["## ROW 3 — 學習迴路 + 隊列", ""]
    judge = sizing_info["judge"]
    thresholds = judge.get("thresholds", {})
    h = judge.get("horizons", {}).get(str(judge.get("judge_horizon_days", 63)), {})
    matured = h.get("matured", 0)
    need = thresholds.get("preliminary_matured_min", 60)
    lines.append(f"- IC 進度: matured {matured}/{need}"
                 f"(judge_horizon={judge.get('judge_horizon_days')}d, 首判決預計 ~2026-10)")
    lines.append("- Brier: —(未接線,milestone-Brier 尚未落地,見 backlog)")
    q_parts = []
    total = 0
    for label, n in queues.items():
        if n is None:
            q_parts.append(f"{label}: —(讀唔到)")
        else:
            q_parts.append(f"{label}: {n}")
            total += n
    icon = "🟡" if total > 5 else "⚪"
    lines.append(f"- 隊列: {icon} " + " | ".join(q_parts))
    lines.append("- IMA 週任務: —(未接線,STATUS.md 表未結構化,見 backlog)")
    return "\n".join(lines)


BACKLOG_NOTE = """
---

### 未接線 backlog(design-only,唔係呢個 render 嘅 bug——留返 P1/P2 執行)

- 市況檔位橫額(平靜/調整/危機市三檔)、ROW 0.5 機會雷達(A/B/C/D)——`opportunity_ladder` 純 doc 概念,冇 script
- 數據哨兵(新鮮度/跨源抽查)——`docs/2026-07-08_phase3_architecture.md` backlog #3,未起
- Kill-scenario VaR、ROW 2 current$/Δ 行動——需要一個極簡 position ledger(未起)
- Roll 倒數——同上,需要知實際持倉嘅 LEAP 到期日
- exp-gap 欄——目前係 2026-07-12 一次性快照,未排程重跑
- ballast 季度體檢(BT-7)——一次性 backtest 結果,未排成經常性 check
- IMA 週任務 tick——STATUS.md 未結構化到可機讀
- PNG 圖表——v1 純 markdown,未起 chart 生成
"""


# ============================================================================
# telegram + git publish
# ============================================================================


def determine_alert(core, judge_info, beta_report, queue_total):
    level, reasons = "green", []
    spy_cross = (core.get("spy") or {}).get("cross", "")
    qqq_cross = (core.get("qqq") or {}).get("cross", "")
    if "FRESH-CROSS" in spy_cross or "FRESH-CROSS" in qqq_cross:
        level = "red"
        reasons.append("200SMA 剛穿越")
    crisis = core.get("crisis") or ""
    if crisis and not crisis.startswith("DISARMED"):
        level = "red"
        reasons.append(f"危機sleeve: {crisis}")
    if judge_info["status"] == "FAIL" or judge_info["circuit_breaker"]:
        level = "red"
        reasons.append("裁判 FAIL/熔斷")
    if level != "red":
        kw = core.get("kill_watch") or []
        if kw:
            level = "yellow"
            reasons.append(f"KILL-WATCH {len(kw)} 主題")
        flagged = (beta_report or {}).get("flagged") or []
        if flagged:
            level = "yellow"
            reasons.append(f"beta化 {len(flagged)} 主題")
        if queue_total is not None and queue_total > 5:
            level = "yellow"
            reasons.append(f"隊列積壓 {queue_total}")
    return level, reasons


def send_telegram(text):
    cred = read_text(TELEGRAM_CRED)
    if not cred:
        return False, "no credential file at ~/.config/karst/telegram"
    lines = [l.strip() for l in cred.strip().split("\n") if l.strip()]
    if len(lines) < 2:
        return False, "credential file malformed (need token line 1, chat_id line 2)"
    token, chat_id = lines[0], lines[1]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
        return True, "sent"
    except (urllib.error.URLError, OSError) as e:
        return False, str(e)


def git_publish(commit_msg):
    if not os.path.isdir(MIRROR_ROOT):
        return False, f"mirror worktree missing at {MIRROR_ROOT} (see module docstring)"

    def run(args):
        return subprocess.run(["git"] + args, cwd=MIRROR_ROOT, capture_output=True, text=True)

    run(["add", "DASHBOARD.md"])
    r2 = run(["commit", "-m", commit_msg])
    combined = (r2.stdout or "") + (r2.stderr or "")
    if r2.returncode != 0 and "nothing to commit" not in combined:
        return False, f"commit failed: {combined.strip()}"
    if "nothing to commit" in combined:
        return True, "no changes to publish"
    r3 = run(["push", "origin", "HEAD:main"])
    if r3.returncode != 0:
        return False, f"push failed: {(r3.stdout or '') + (r3.stderr or '')}".strip()
    return True, "published"


# ============================================================================
# main
# ============================================================================


def render(mode):
    playbook_text = read_text(PLAYBOOK_LOG)
    core_block, core_date = last_block(playbook_text, "Core v2 playbook readout")
    core = parse_core_block(core_block)

    premkt_block, premkt_date = (None, None)
    premkt = {}
    if mode == "evening":
        premkt_text = read_text(PREMARKET_LOG)
        premkt_block, premkt_date = last_block(premkt_text, "PREMARKET CHECK")
        premkt = parse_premarket_block(premkt_block)

    aa_latest = load_aa_latest()
    sizing_info = compute_sizing()
    judge_info = {"status": sizing_info["status"], "circuit_breaker": sizing_info["circuit_breaker"],
                  "thresholds": sizing_info["judge"].get("thresholds", {}),
                  "matured": sizing_info["judge"].get("horizons", {}).get(
                      str(sizing_info["judge"].get("judge_horizon_days", 63)), {}).get("matured", 0),
                  "horizons": sizing_info["judge"].get("horizons", {}),
                  "judge_horizon_days": sizing_info["judge"].get("judge_horizon_days")}
    mf_shares = meta_factor_shares(sizing_info["themes"], sizing_info["rows"], sizing_info["total_cap"])
    beta_report = load_beta_report()
    exp_gap, exp_gap_date = load_expectations_gap()

    queues = {
        "constraint": count_checklist_pending(CONSTRAINT_QUEUE),
        "magnifier": count_checklist_pending(MAGNIFIER_QUEUE),
        "transcripts": count_checklist_pending(PENDING_ANALYSIS),
    }
    queue_total = sum(n for n in queues.values() if n is not None) or 0

    gen_ts = NOW.strftime("%Y-%m-%d %H:%M UTC")
    header = (f"# Karst Dashboard\n\n_render: {gen_ts} | mode: {mode}"
              f" | [source](https://github.com/kkhcheng88/Karst)_\n")

    parts = [header,
             build_row0(mode, core, core_date, premkt, premkt_date, aa_latest, judge_info),
             build_row1(sizing_info, mf_shares, beta_report),
             build_row2(sizing_info, core, exp_gap, exp_gap_date),
             build_row3(sizing_info, queues),
             BACKLOG_NOTE]
    md = "\n\n".join(parts)

    level, reasons = determine_alert(core, judge_info, beta_report, queue_total)
    return md, level, reasons


def build_telegram_text(mode, level, reasons):
    tag = "晨版" if mode == "morning" else "晚版(PREMARKET預覽)"
    if level == "red":
        head = "🔴 Karst " + tag + " — 要睇"
    elif level == "yellow":
        head = "🟡 Karst " + tag + " — 有留意項"
    else:
        head = "✅ Karst " + tag + " — 今日無動作"
    body = "\n".join(f"- {r}" for r in reasons) if reasons else "全部指標正常。"
    return f"{head}\n{body}\n\n{GITHUB_FILE_URL}"


def main():
    ap = argparse.ArgumentParser(description="Render + publish the Karst dashboard (pure aggregation).")
    ap.add_argument("--mode", choices=["morning", "evening"], default="morning")
    ap.add_argument("--no-git", action="store_true", help="skip commit+push to origin/main")
    ap.add_argument("--no-telegram", action="store_true", help="skip Telegram push")
    args = ap.parse_args()

    md, level, reasons = render(args.mode)

    out_path = os.path.join(MIRROR_ROOT, "DASHBOARD.md")
    if os.path.isdir(MIRROR_ROOT):
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(md)
        print(f"wrote {out_path}")
    else:
        # fall back to repo root so the render is at least inspectable/testable without the
        # mirror worktree set up (e.g. a fresh clone) -- will NOT be git-published.
        out_path = os.path.join(REPO_ROOT, "DASHBOARD.preview.md")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(md)
        print(f"WARNING: mirror worktree not found, wrote preview only to {out_path}")

    print(f"alert level: {level} ({', '.join(reasons) if reasons else 'all clear'})")

    if not args.no_git and os.path.isdir(MIRROR_ROOT):
        ok, msg = git_publish(f"dashboard: {args.mode} render {NOW.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"git publish: {'OK' if ok else 'FAILED'} — {msg}")

    if not args.no_telegram:
        text = build_telegram_text(args.mode, level, reasons)
        ok, msg = send_telegram(text)
        print(f"telegram: {'OK' if ok else 'FAILED'} — {msg}")


if __name__ == "__main__":
    main()
