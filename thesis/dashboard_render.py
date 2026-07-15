"""thesis/dashboard_render.py — Karst daily investment briefing (Telegram-primary).

Pure AGGREGATION of existing output files/functions -- computes nothing that isn't already
produced by an existing scheduled script. Two exceptions, both trivial calendar/derived
arithmetic rather than new investment signals: top-up countdown (next month's first weekday,
approximate -- no trading-calendar utility exists in this repo), and meta_factor $ share
(re-groups sizing.py's own already-computed per-theme final $, same computation
apply_meta_factor_cut already does internally).

Honesty rule (NHITL "唔扮有" -- see memory karst-role-nhitl-decision-support): any element with
no real computed source yet (kill-scenario VaR, position ledger, opportunity-ladder tier, data
sentinel) is simply omitted from the reader-facing briefing rather than shown as a fabricated or
jargon-labelled placeholder. See BACKLOG_NOTE for the developer-facing list of what's missing.

Reader model (2026-07-13, corrected after user feedback): this is written for a Traditional-
Chinese investor with NO technical background who is reading a push notification on their
phone, not an engineer reading a status dump. Concretely: no internal jargon (verdict/meta_
factor/ROW0-3/exp-gap/裁判/隊列/學習迴路), no wide tables (mobile requires horizontal scroll),
grouped by reader intent (what do I need to do today?) not by internal computation category.
200SMA and RSI-2 ARE kept as-is (user confirmed these are fine to show plainly).

Delivery (2026-07-13, corrected): Telegram is the PRIMARY and self-sufficient channel, sent as
several short focused messages (not one wall of text) -- a reader should never need to leave
Telegram. DASHBOARD.md is still written + committed + pushed to the GitHub mirror
(.dashboard_mirror/, branch github-main tracking origin/main) purely as a low-cost historical
archive; nothing in the Telegram messages points the reader there anymore.

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

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))          # thesis/
REPO_ROOT = os.path.dirname(ROOT)                            # Karst/
MIRROR_ROOT = os.path.join(REPO_ROOT, ".dashboard_mirror")
sys.path.insert(0, ROOT)
import composite_score as composite_mod  # noqa: E402 -- sibling module, P1 0-100 綜合分(純組合現有讀數)
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
TRIGGER_STATE_PATH = os.path.join(ROOT, ".raw", "entry_exit_trigger_state.json")

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
TARGET_ENTRY_RE = re.compile(
    r"^(?P<slug>[a-z][a-z0-9-]+) \([A-Z-]+\):\n\s+TARGET: (?P<text>.+?)(?=\n\n|\Z)",
    re.MULTILINE | re.DOTALL)
HARD_BASIS_RE = re.compile(r"HARD \[(?P<basis>[^\]]+)\]: 200SMA=\$?(?P<sma>[\d.]+|n/a), "
                            r"now=\$?(?P<now>[\d.]+|n/a)")
TRIGGER_BLOCK_RE = re.compile(
    r"^(?P<ticker>SPY|QQQ) triggers \(from \S+ close, RSI-2=(?P<rsi2>[\d.]+)\):\n"
    r"\s+LEAP gate \w+ -> flips if close crosses 200SMA (?P<sma>[\d.]+) \((?P<sma_pct>[+-][\d.]+)%\)\n"
    r"\s+RSI-2<10 \(dip/accumulate\): close <= (?P<dip>[\d.]+) \((?P<dip_pct>[+-][\d.]+)%\)\n"
    r"\s+RSI-2>90 \(sell covered call\): close >= (?P<sell>[\d.]+) \((?P<sell_pct>[+-][\d.]+)%\)",
    re.MULTILINE)
LEAP_QUOTE_RE = re.compile(
    r"^(?P<ticker>SPY|QQQ) leg quote: (?P<expiry>\S+) \((?P<dte>\d+)d\) K=(?P<strike>[\d.]+) "
    r"delta=(?P<delta>[\d.]+) mid=(?P<mid>[\d.]+) \(1 contract = \$(?P<cost>[\d,]+)\)", re.MULTILINE)
TICKER_SECTION_RE = re.compile(
    r"^-- (?P<slug>[a-z][a-z0-9-]+) \(cycle=\S+\) --\n(?P<body>.*?)(?=\n-- |\Z)",
    re.MULTILINE | re.DOTALL)
TICKER_ROW_RE = re.compile(
    r"^\s+(?P<symbol>[A-Z]+)\s+(?P<pe_pctile>\S+)\s+(?P<last_pe>\S+)\s+(?P<vs200sma>\S+)\s+"
    r"(?P<pos52>\S+)\s+(?P<sma_price>\$[\d.]+|n/a)\s+(?P<derate>\S+)\s+"
    r"(?P<verdict>BUY-ZONE|ACCUMULATE|WAIT|KILL-WATCH)(?P<stale> +\[STALE[^\]]*\])?\s*$",
    re.MULTILINE)


def _slug_list(raw):
    raw = raw.strip()
    return [] if raw == "(none)" else [s.strip() for s in raw.split(",")]


def parse_core_block(block):
    """Extract SPY/QQQ 200SMA gate status, VIX/RSI-2/crisis-sleeve, and per-theme verdicts
    from a playbook_readout.py + theme_signal.py combined log block."""
    out = {"spy": None, "qqq": None, "vix": None, "crisis": None,
           "buy_zone": [], "accumulate": [], "kill_watch": [], "theme_rows": {}, "targets": {},
           "triggers": {}, "leap_quotes": {}, "ticker_rows": {}}
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
    # per-ticker entry/exit price levels (RSI-2 dip/sell triggers, 200SMA break price) --
    # these are the concrete numbers a reader needs for market-open positioning, not just a
    # directional read.
    for m in TRIGGER_BLOCK_RE.finditer(block):
        out["triggers"][m.group("ticker")] = m.groupdict()
    for m in LEAP_QUOTE_RE.finditer(block):
        out["leap_quotes"][m.group("ticker")] = m.groupdict()
    # per-ticker table within each theme (real price, real 200SMA level, own verdict) -- the
    # answer to "which specific stock, not just which theme".
    for sm in TICKER_SECTION_RE.finditer(block):
        rows = [rm.groupdict() for rm in TICKER_ROW_RE.finditer(sm.group("body"))]
        if rows:
            out["ticker_rows"][sm.group("slug")] = rows
    # per-theme HARD trend-break status: has the 200SMA kill condition actually fired, or how
    # far away is it? Distinguishes a real trend break from a merely-expensive valuation watch.
    # Also captures the actual price level (real $ for a single-ticker basis, or the basket's
    # own normalized index for a multi-ticker basis -- HARD_BASIS_RE's basis field tells you
    # which, and callers should only show it as a $ price when basis starts with "$").
    parts = block.split("=== targets ", 1)
    if len(parts) == 2:
        body = parts[1].split("\n=== ", 1)[0]
        for tm in TARGET_ENTRY_RE.finditer(body):
            text = tm.group("text")
            gap_m = re.search(r"needs ~?([\d.]+)% pullback", text)
            basis_m = HARD_BASIS_RE.search(text)
            out["targets"][tm.group("slug")] = {
                "triggered": "ALREADY BELOW" in text or "ALREADY" in text,
                "gap_pct": gap_m.group(1) if gap_m else None,
                "basis": basis_m.group("basis") if basis_m else None,
                "sma_level": basis_m.group("sma") if basis_m else None,
                "now_level": basis_m.group("now") if basis_m else None,
            }
    return out


PREMKT_ROW_RE = re.compile(
    r"^(?P<ticker>\S+)\s+close (?P<close>[\d.]+) -> PREMKT (?P<premkt>[\d.]+) "
    r"\((?P<pct>[+-][\d.]+)%\) \| dip (?:(?P<dip>[\d.]+) \[(?P<dip_pct>[+-][\d.]+)%\]|n/a) "
    r"\| sell (?:(?P<sell>[\d.]+) \[(?P<sell_pct>[+-][\d.]+)%\]|n/a) "
    r"\| 200SMA (?P<sma>[\d.]+|n/a) gate (?P<gate>ON|OFF)\s*\n"
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


def _load_json(path):
    text = read_text(path)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def load_sentinel():
    """data_sentinel.py's verdict (refreshed by the .cmd chain right before this render).
    A red sentinel means every other reading in the briefing may be stale -- the renderer
    puts that warning ABOVE everything else rather than burying it."""
    return _load_json(os.path.join(ROOT, ".raw", "data_sentinel.json"))


def load_ladder():
    """opportunity_ladder.py's tier + radar states (same refresh contract as the sentinel)."""
    return _load_json(os.path.join(ROOT, ".raw", "opportunity_ladder.json"))


def load_ledger_report():
    """paper_ledger.py's report: strategy-own paper positions (% of sleeve), kill-VaR,
    target-vs-current gaps, LEAP roll countdown. See karst-user-agnostic-system-design:
    these are the STRATEGY's own accumulated paper positions, never the user's broker."""
    return _load_json(os.path.join(ROOT, ".raw", "paper_ledger_report.json"))


def load_crowding():
    """crowding_composite.py's per-theme crowding percentile (weekly refresh)."""
    return _load_json(os.path.join(ROOT, ".raw", "crowding_composite.json"))


def load_valuation_tickers():
    """valuation.py's PER-TICKER block (thesis/.raw/valuation_report.json 'tickers' section) --
    finer-grained than the theme-rollup markdown table load_expectations_gap() parses; used by
    the composite score's expect dimension (per-ticker P_base, not the theme's best ticker)."""
    payload = _load_json(os.path.join(ROOT, ".raw", "valuation_report.json"))
    return (payload or {}).get("tickers") or {}


def load_news():
    """news_watch.py's kill-axis headlines (context, not signal -- max 8/day by design)."""
    return _load_json(os.path.join(ROOT, ".raw", "news_watch.json"))


def load_league():
    """paper_league.py's multi-strategy NAV comparison (core/AA/sizing-v1/v2 paper race)."""
    return _load_json(os.path.join(ROOT, ".raw", "paper_league_report.json"))


def load_due_milestones():
    """Count milestone predictions past deadline but still unresolved (milestones.yaml).
    Surfacing this count in the daily briefing IS the resolver reminder mechanism -- a due
    prediction that nobody judges silently breaks the Brier calibration loop."""
    try:
        with open(os.path.join(ROOT, "milestones.yaml"), encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except (OSError, yaml.YAMLError):
        return None, None
    today = NOW.date()
    due, upcoming = [], []
    for m in data.get("milestones", []):
        if m.get("status") != "pending":
            continue
        dl = m.get("deadline")
        dl_date = dl if hasattr(dl, "year") else None
        if dl_date is None:
            try:
                dl_date = datetime.strptime(str(dl)[:10], "%Y-%m-%d").date()
            except ValueError:
                continue
        if dl_date < today:
            due.append(m.get("id"))
        elif (dl_date - today).days <= 45:
            upcoming.append(m.get("id"))
    return due, upcoming


def count_checklist_pending(path):
    text = read_text(path)
    if text is None:
        return None
    return len(re.findall(r"^- \[ \]", text, flags=re.MULTILINE))


EXPGAP_ROW_RE = re.compile(
    r"^\|\s*(?P<slug>[a-z][a-z0-9-]+)\s*\|\s*(?P<ticker>\S+)\s*\|\s*(?P<pbase>-?[\d.]+)x\s*\|"
    r"\s*(?P<cls>[^|]+?)\s*\|\s*$", re.MULTILINE)
# ^ -? added 2026-07-13: N/A-binary themes carry NEGATIVE P_base (e.g. "-0.08x") in the rollup
# table; without it those rows silently vanish from the exp-gap column (found by the
# paper_ledger agent when it reused this regex).


def load_expectations_gap():
    """Parse the latest one-off expectations-gap markdown result (backtest/results/
    *_expectations_gap_v0.md) -- historical snapshot, NOT recomputed live. Returns
    (slug -> {p_base, classification}, as_of_date) or ({}, None) if no result file exists."""
    # v* not v0: valuation.py (2026-07-13, production v1) writes *_expectations_gap_v1.md in the
    # same table format -- the sorted() date-prefix ordering then naturally picks the newest run.
    matches = sorted(glob.glob(os.path.join(REPO_ROOT, "backtest", "results",
                                             "*_expectations_gap_v*.md")))
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
# plain-language glossary (Traditional Chinese) -- no internal jargon leaks past this point
# ============================================================================

THEME_ZH = {
    "memory-supercycle": "記憶體超級週期",
    "photonics-optical": "光通訊/光學元件",
    "ai-power-grid": "AI電力與電網",
    "advanced-packaging": "先進晶片封裝",
    "space-satellite": "太空衛星",
    "rare-earth-materials": "稀土礦產",
    "tpu-custom-silicon": "客製化AI晶片",
    "oil-gas-energy": "油氣能源",
    "semicap-equipment": "半導體設備",
    "aerospace-specialty-alloys": "航太特殊合金",
    "euv-lithography-monopoly": "微影設備(EUV)",
    "us-solar-manufacturing": "美國太陽能製造",
    "gas-compression-equipment": "天然氣壓縮設備",
    "specialty-siding-pricing-power": "特殊外牆建材",
    "glp1-biologics-packaging": "減肥藥專用包裝",
}

META_FACTOR_ZH = {
    "aerospace-capex": "航太資本開支",
    "ai-capex": "AI資本開支",
    "building-products": "建材相關",
    "china-supply": "中國供應鏈相關",
    "energy-macro": "能源大環境",
    "pharma-manufacturing": "醫藥製造",
    "policy-defense": "國防政策",
    "trade-policy": "貿易政策",
}

# node slug -> layman business-Chinese name (display only; the slug stays the canonical key in
# themes.yaml). Kept here in the display layer so batch rollouts of nodes don't each have to
# carry a translation. A node not in this map falls back to its raw slug (visible = go add it).
NODE_ZH = {
    "dram-hbm-integrated-leader": "DRAM/HBM 整合龍頭",
    "nand-flash-shortage": "NAND 快閃記憶體缺貨",
    "hdd-nearline-storage": "硬碟近線儲存",
    "hbm4-oligopoly-leader-unbuyable": "HBM4 寡頭(難買入)",
    "inp-substrate-chokehold": "磷化銦基板咽喉",
    "laser-idm-moat": "雷射自產護城河",
    "silicon-photonics-dsp": "矽光子/DSP 晶片",
    "modules-transceivers": "光模組/收發器",
    "cpo-speculative-preprofit": "光引擎投機(未盈利)",
    "glass-fiber-coupling": "玻璃光纖耦合",
    "grid-hardware": "電網硬件",
    "power-semis-mature": "成熟電源半導體",
    "pre-earnings-optionality": "業績前選擇權(高風險)",
    "uranium-fuel": "鈾燃料",
    "ipp-utilities": "獨立發電/公用事業",
    "osat-arms-dealers": "封測軍火商",
    "pcb-substrate-tollbooth": "PCB/載板收費站",
    "process-equipment-test": "製程設備/測試",
    "emib-optionality": "EMIB 封裝選擇權",
    "glass-substrate-nextgen": "玻璃基板(下世代)",
    "hdd-storage-hoya-downstream": "硬碟儲存(Hoya 下游)",
    "profitable-aero-space-diluted": "成熟航太(倍數被稀釋)",
    "launch-execution-bet": "火箭發射執行賭注",
    "d2d-spectrum-optionality": "衛星直連手機頻譜",
    "preprofit-smallcap-lottery": "未盈利細價股彩票",
    "golden-dome-policy-option": "金穹國防政策選擇權",
    "merger-arb-special-sit": "併購套利特殊情況",
    "custom-asic-tollbooth": "客製晶片收費站",
    "foundry-both-chains": "晶圓代工(兩邊通吃)",
    "odm-system-assembly": "系統組裝代工",
    "rare-earth-separation-chokehold": "稀土分離咽喉",
    "de-china-magnet-preprofit": "去中國化磁材(未盈利)",
    "named-alloy-breadth-moat": "特種合金產品廣度",
    "requalification-switching-lock": "換供應商認證鎖",
    "burn-in-tollgate-froth": "老化測試收費閘(炒風)",
    "sole-euv-supplier-monopoly": "EUV 唯一供應商",
    "cdte-policy-moat-cheap": "碲化鎘政策護城河(平)",
    "compression-shortage-unloved": "壓縮設備缺貨(被冷落)",
    "siding-segment-diluted": "外牆板業務(被稀釋)",
    "hvp-regulatory-lock": "高價值包裝監管鎖",
}

CYCLE_ZH = {"early": "早期", "mid": "中段", "mid-late": "中後段", "late": "後段",
            "event-driven": "事件驅動", "—": "—"}

# tier -> a one-glyph marker for the PAYOFF SHAPE of a node. Design note (2026-07-13 user
# review): magnitude and confidence are TWO INDEPENDENT dimensions -- "binary" describes a
# bimodal payoff shape (works -> explosive, fails -> near zero), NOT a claim that high return
# must mean low confidence. High-confidence + high-magnitude is the jackpot quadrant (MU-2023-
# at-trough); rare, but it's what the magnifier framework exists to find. Hence 🎲 (shape) not
# ⚡ (danger), and the legend says "形狀唔等於冇把握,把握睇信心".
def tier_glyph(tier):
    t = str(tier or "")
    if "binary" in t:
        return "🎲"
    if "durable" in t:
        return "💎"
    if t.startswith("2x") or t == "2x":
        return "🔸"
    return "🔷"


def node_zh(slug):
    return NODE_ZH.get(slug, slug)

# These describe how much future optimism is embedded in the current price (Mauboussin
# expectations lens) -- a DIFFERENT axis from theme_signal's "cheap/expensive vs own history",
# so they're labelled "市場預期" in the output, not "估值", to avoid reading as a contradiction
# when a theme is cheap-vs-history (ACCUMULATE) yet still has a lot of growth priced in.
EXPGAP_ZH = {
    "supercycle 白送": "現價相對保守,主升幅仲未 price 入去",
    "買緊部分希望": "現價已反映部分未來增長預期",
    "大部分係希望": "現價已反映大部分未來增長預期",
    "N/A-binary (option framing)": "未有穩定盈利,屬高風險賭注型",
}


def theme_zh(slug):
    return THEME_ZH.get(slug, slug)


def _format_holdings_line(strat, limit=6):
    """paper_league.py's per-theme holdings (sizing-v1/v2 only -- aa-strict/spy-bh are mirrored
    black-box NAV lines with no theme breakdown). Caps the list at `limit` names + a "仲有N個"
    tail so a fully-deployed 15-theme sleeve doesn't blow out the Telegram message."""
    holdings = strat.get("holdings") or []
    if not holdings:
        return None
    parts = [f"{theme_zh(h['slug'])} {h['pct']:.0f}%" for h in holdings[:limit]]
    more = len(holdings) - limit
    if more > 0:
        parts.append(f"…仲有{more}個")
    cash = strat.get("cash_pct")
    if cash is not None:
        parts.append(f"現金 {cash:.0f}%")
    return "｜".join(parts)


def expgap_zh(classification):
    return EXPGAP_ZH.get(classification, classification)


def expgap_detail(eg):
    """Business-term expansion of the expectations-gap label. The label alone answers
    "cheap or expensive vs the growth story"; readers asked (2026-07-14) for the "by how much"
    behind it -- recast valuation.py's P_base@14x coverage ratio (NOPAT at a conservative,
    no-supercycle-credit multiple, divided by today's enterprise value) as a plain percentage:
    how much of today's price a boring/non-growing version of the business would already
    justify, with the rest being the growth story the market is paying for. 14x itself is a
    round-number assumption, not an empirically-derived discount rate (valuation.py's own spec
    flags this) -- kept out of the reader-facing text for that reason; the percentage is still
    directionally honest even though its anchor multiple is a judgment call, not a proven one."""
    if not eg:
        return None, None
    label = expgap_zh(eg["classification"])
    try:
        p_base = float(eg["p_base"])
    except (TypeError, ValueError):
        return label, None
    if p_base < 0:  # N/A-binary rows carry a negative placeholder, not a real coverage ratio
        return label, None
    pct = round(p_base * 100)
    if pct >= 100:
        detail = "保守估值下,現有正常盈利已足以支撐現價,增長故事屬額外 upside"
    else:
        detail = f"保守估值下,現有正常盈利可支撐現價 {pct}%,其餘 {100 - pct}% 靠未來增長預期能否兌現"
    return label, detail


def crowding_read(pctile, is_buy):
    """Plain-language crowding interpretation -- a raw percentile means nothing to a reader, so
    every card gets the ACTION-APPROPRIATE read: on a buy, high crowding = don't chase; on a
    sell/watch, high crowding = the crowded trade unwinds hard, so an exit is better supported.
    Returns (text, is_warning)."""
    if pctile is None:
        return "未評估", False
    p = round(pctile)
    if p >= 90:
        return (f"{p}分,市場好逼——追入風險高,寧可等" if is_buy
                else f"{p}分,擁擠盤——散起上嚟快,減持更有理由"), True
    if p >= 70:
        return (f"{p}分,偏逼——入場唔急" if is_buy else f"{p}分,偏擁擠"), False
    if p <= 30:
        return (f"{p}分,未算逼——入場相對舒服" if is_buy else f"{p}分,唔算擁擠"), False
    return f"{p}分,中等", False


def trend_read(vs200sma, triggered):
    """Plain-language trend read vs the 200-day line (the action trigger). vs200sma is a signed
    percent string like '+43.9%' / '-4.5%' from the per-ticker table; triggered means the theme
    basket has already broken below its 200-day line."""
    if triggered:
        return "已跌穿200日均線 🔴(趨勢已破)"
    if vs200sma is None:
        return "未評估"
    return f"在200日均線之上 {vs200sma}(趨勢未破)" if not str(vs200sma).startswith("-") \
        else f"已在200日均線之下 {vs200sma}(趨勢轉弱)"


def _current_price(sma_price, vs200sma):
    """Derive a ticker's current price from its 200SMA price ('$557.35') and its signed % gap
    to that line ('+43.9%') -- the per-ticker table carries those two but not the absolute
    current price. Returns a float, or None if either input is missing/unparseable."""
    if not sma_price or vs200sma is None:
        return None
    try:
        sma = float(str(sma_price).replace("$", "").replace(",", ""))
        pct = float(str(vs200sma).replace("%", ""))
    except (TypeError, ValueError):
        return None
    return sma * (1 + pct / 100.0)


def classify_action(verdict, triggered):
    """Translate an internal verdict into a plain-language urgency + label. Deliberately
    distinguishes an ACTUAL trend break (price already below 200SMA -- real action signal) from
    a merely-expensive valuation watch (theme_signal.py's KILL-WATCH conflates both) -- calling
    both "止蝕" (stop-loss) would mislead the reader into thinking every KILL-WATCH theme needs
    action today, when most are just "getting pricey, keep an eye on it"."""
    if verdict == "KILL-WATCH":
        if triggered:
            return {"urgency": "high", "icon": "🔴", "label": "止蝕訊號已觸發"}
        return {"urgency": "watch", "icon": "🟠", "label": "估值偏貴,列入監察"}
    if verdict == "ACCUMULATE":
        return {"urgency": "opportunity", "icon": "🟢", "label": "估值轉吸引,可考慮分批吸納"}
    if verdict == "BUY-ZONE":
        return {"urgency": "opportunity", "icon": "🟢", "label": "早期主題,現價未算貴"}
    return {"urgency": "quiet", "icon": "⚪", "label": "觀望"}


def _load_trigger_state():
    return _load_json(TRIGGER_STATE_PATH) or {}


def _save_trigger_state(state):
    os.makedirs(os.path.dirname(TRIGGER_STATE_PATH), exist_ok=True)
    with open(TRIGGER_STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def new_trigger_lines(action_items, as_of_date):
    """Cross-day diff on top of already-computed action_items (2026-07-14, reader asked to be
    told WHEN a specific ticker's entry/exit condition first fires, not just see it repeated in
    every day's briefing while it stays true). Persists each trading day's per-ticker
    entry/exit state to TRIGGER_STATE_PATH and reports only tickers whose state CHANGED since
    the last recorded trading day -- idempotent within the same `as_of_date` (mirrors paper_
    league.py's "already marked for today" convention) so a morning + evening run on the same
    trading day doesn't fire the same notice twice.

    Deliberately labelled "系統規則觸發" (this file's own rule fired), not "訊號"/"已驗證" --
    the underlying 200SMA break rule is validated for the SPY/QQQ core sleeve (core-strategy-v2)
    but NOT yet for individual satellite tickers at this granularity (backtest/results/
    2026-07-13_trim_rule_validation.md's theme-composite version shows an inconsistent sign
    pre/post-2021, n=8-10 declustered) -- honest framing over false confidence."""
    if not as_of_date:
        return []
    state = _load_trigger_state()
    if state.get("as_of") == as_of_date:
        return []  # already diffed for this trading day

    prev_tickers = state.get("tickers", {})
    current = {}
    for a in action_items:
        if a["urgency"] == "opportunity" and a.get("ticker"):
            current[a["ticker"]] = {"state": "entry", "theme": a["name"]}
        elif a["urgency"] == "high":
            for tk in (a.get("weak_tickers") or []):
                current[tk] = {"state": "exit", "theme": a["name"]}

    lines = []
    for tk, info in sorted(current.items()):
        prev_state = prev_tickers.get(tk, {}).get("state")
        if prev_state == info["state"]:
            continue
        icon = "🟢" if info["state"] == "entry" else "🔴"
        label = "入場" if info["state"] == "entry" else "離場"
        lines.append(f"   {icon} {label}:{tk}({info['theme']})")

    _save_trigger_state({"as_of": as_of_date, "tickers": current})
    return lines


def ticker_node_map(theme):
    """ticker -> its magnifier node (name/magnitude_tier/cycle_stage), for themes that have
    per-node magnifier data (only 1/15 as of 2026-07-13: ai-power-grid -- see magnifier P2
    backlog #12 to extend). {} for the other 14 themes, which callers must handle honestly
    (valuation-only pick, not magnifier-informed) rather than silently pretending otherwise."""
    m = {}
    for n in theme.get("nodes") or []:
        for tk in (n.get("tickers") or []):
            m[tk] = n
    return m


def pick_ticker(verdict, ticker_rows, node_map=None):
    """Pick the single most representative/actionable ticker within a theme's basket -- the
    concrete answer to "which stock, not just which theme" (themes have 2-13 tickers each).
    For a KILL-WATCH theme, prefer a ticker that's ALSO individually KILL-WATCH (most
    representative of the danger); for ACCUMULATE/BUY-ZONE, prefer a matching-verdict ticker.
    BUY pools rank by the 0-100 composite score FIRST when available (P1, docs/2026-07-15_
    quantification_review.md -- pure composition of already-computed reads, attached to each
    row as `_composite` by build_briefing), falling back to the previous magnitude-then-
    cheapest-pe_pctile sort for rows without a score (pre-profit N/A lane) and as tiebreaker.
    KILL-WATCH picks keep the old logic unchanged -- the composite is a buy-quality score,
    not a danger-representativeness score. Returns (picked_row, node_or_None)."""
    if not ticker_rows:
        return None, None
    if verdict == "KILL-WATCH":
        pool = [r for r in ticker_rows if r["verdict"] == "KILL-WATCH"] or ticker_rows
    elif verdict in ("ACCUMULATE", "BUY-ZONE"):
        pool = [r for r in ticker_rows if r["verdict"] in ("ACCUMULATE", "BUY-ZONE")] or ticker_rows
    else:
        pool = ticker_rows
    node_map = node_map or {}
    is_buy = verdict in ("ACCUMULATE", "BUY-ZONE")

    def sort_key(r):
        node = node_map.get(r["symbol"])
        mag = sizing_mod.parse_magnitude_tier(node.get("magnitude_tier")) if node else None
        try:
            pe = float(r["pe_pctile"])
        except (TypeError, ValueError):
            pe = 999.0
        comp = (r.get("_composite") or {}).get("score")
        comp_rank = -(comp if (is_buy and comp is not None) else -1.0)
        return (comp_rank, -(mag or 0.0), bool(r.get("stale")), pe)

    picked = sorted(pool, key=sort_key)[0]
    return picked, node_map.get(picked["symbol"])


# ============================================================================
# content model -- single source of truth for both Telegram messages and the archive
# ============================================================================


def build_briefing(mode, core, core_date, premkt, premkt_date, aa_latest, judge_info,
                    sizing_info, mf_shares, beta_report, exp_gap, queues):
    rows = sorted(sizing_info["rows"], key=lambda r: -r["final"])
    targets = core.get("targets", {})
    ticker_rows = core.get("ticker_rows", {})
    budget = sizing_info["budget"]

    # --- P1 綜合分(docs/2026-07-15_quantification_review.md):組合現有讀數,唔計新訊號。
    # crowding 因此提早喺呢度 load(原本喺 loop 之後先 load,weave 邏輯不變)。
    crowding = load_crowding()
    val_tickers = load_valuation_tickers()
    composite_cfg = composite_mod.load_weights()
    composite_log_rows = []
    for slug2, t_rows in ticker_rows.items():
        theme_meta = sizing_info["themes"].get(slug2, {})
        sizing_row = next((sr for sr in sizing_info["rows"] if sr["slug"] == slug2), None)
        crowd_pct = None
        if crowding and isinstance(crowding.get("themes"), dict):
            crowd_pct = (crowding["themes"].get(slug2) or {}).get("composite_pctile")
        theme_ctx_base = {
            "confidence": sizing_row["confidence"] if sizing_row else None,
            "cycle_stage": theme_meta.get("cycle_stage"),
            "crowding_pctile": crowd_pct,
        }
        for tr in t_rows:
            ctx = dict(theme_ctx_base)
            ctx["p_base"] = (val_tickers.get(tr["symbol"]) or {}).get("p_base")
            tr["_composite"] = composite_mod.score_ticker(tr, ctx, composite_cfg)
            if tr["_composite"]["score"] is not None:
                composite_log_rows.append({"ticker": tr["symbol"], "theme": slug2,
                                            "score": tr["_composite"]["score"],
                                            "dims": tr["_composite"]["dims"]})
    if core_date and composite_log_rows:
        # committed forward log -- point-in-time composite 事後砌唔返(crowding/valuation
        # 檔會被覆寫),要驗證權重就只能而家開始儲;idempotent per trading day([:10]
        # 剪走 playbook 時間戳嘅 HH:MM,免同日重跑 playbook 造成重複記帳)。
        composite_mod.append_log(composite_log_rows, str(core_date)[:10])

    action_items = []
    quiet_count = 0
    for r in rows:
        slug = r["slug"]
        theme_row = core.get("theme_rows", {}).get(slug)
        verdict = theme_row["verdict"] if theme_row else (
            "KILL-WATCH" if slug in core.get("kill_watch", []) else
            "ACCUMULATE" if slug in core.get("accumulate", []) else
            "BUY-ZONE" if slug in core.get("buy_zone", []) else None)
        if verdict is None:
            quiet_count += 1
            continue
        triggered = targets.get(slug, {}).get("triggered", False)
        act = classify_action(verdict, triggered)
        if act["urgency"] == "quiet":
            quiet_count += 1
            continue
        eg = exp_gap.get(slug)
        theme_tickers = ticker_rows.get(slug, [])
        val_label, val_detail = expgap_detail(eg) if eg else (None, None)
        item = {"name": theme_zh(slug), "urgency": act["urgency"], "icon": act["icon"],
                "label": act["label"], "slug": slug,
                "valuation": val_label, "valuation_detail": val_detail}

        if act["urgency"] == "high":
            # theme-level 200SMA break = the WHOLE theme's composite basket has broken trend, not
            # a single name -- so the action is "review/reduce the whole theme", and we name the
            # individual tickers that are themselves also breaking down (their own verdict is
            # KILL-WATCH), not just one "pick". Deliberately NO position % here: sizing.py sizes
            # by confidence and doesn't know about this trend break, so its target allocation
            # would read as "buy this much" right next to a reduce signal -- contradictory.
            weak = [tr["symbol"] for tr in theme_tickers if tr["verdict"] == "KILL-WATCH"]
            item["weak_tickers"] = weak
        elif act["urgency"] == "watch":
            # expensive-but-not-broken: pure monitoring, no action today, so no position % and no
            # "buy this" pick -- just the valuation context. Trend is definitionally intact (a
            # broken one would be "high"/kill), so surface how far above the 200-day line it is
            # from the target's pullback gap rather than leaving trend "未評估".
            gap = targets.get(slug, {}).get("gap_pct")
            if gap:
                item["ticker_vs200sma"] = f"+{gap}%"
        else:  # opportunity -- the only case where a buy is actually being suggested
            node_map = ticker_node_map(sizing_info["themes"].get(slug, {}))
            picked, node = pick_ticker(verdict, theme_tickers, node_map)
            # % of the satellite/thematic sleeve, NOT a $ amount -- Karst is user-agnostic
            # (doesn't know the reader's account size), so a raw $ against the internal
            # DEFAULT_BUDGET would be meaningless. % of the satellite allocation is meaningful
            # regardless of account size (same "% NAV, not $" principle as the Fable review).
            item["pct"] = (r["final"] / budget * 100.0) if budget else 0.0
            if picked:
                item.update({
                    "ticker": picked["symbol"], "ticker_verdict": picked["verdict"],
                    "ticker_vs200sma": picked["vs200sma"], "ticker_sma_price": picked["sma_price"],
                    "node_magnitude": node.get("magnitude_tier") if node else None,
                    "composite": (picked.get("_composite") or {}).get("score")})
                # 同主題 peer 對比(P1):有分嘅由高到低,N/A 車道名單獨列——回答
                # 「點解揀呢隻唔揀嗰隻」,唔使讀者自己逐隻查。
                scored = sorted((tr for tr in theme_tickers
                                  if (tr.get("_composite") or {}).get("score") is not None),
                                 key=lambda tr: -tr["_composite"]["score"])
                if len(scored) >= 2:
                    item["peer_scores"] = [f"{tr['symbol']} {tr['_composite']['score']:.0f}"
                                            for tr in scored[:4]]
                na_names = [tr["symbol"] for tr in theme_tickers
                             if (tr.get("_composite") or {}).get("score") is None]
                if na_names:
                    item["peer_na"] = na_names[:4]
        # theme-level trend read (for the consistent 3-read block on every card): use the picked
        # ticker's vs200sma if we have one, else the theme target's basket read.
        tgt = targets.get(slug, {})
        item["vs200sma_read"] = item.get("ticker_vs200sma") or (
            tgt.get("now_level") and f"基準 {tgt.get('now_level')} vs 均線 {tgt.get('sma_level')}")
        item["triggered"] = triggered
        action_items.append(item)
    urgency_rank = {"high": 0, "watch": 1, "opportunity": 2}
    action_items.sort(key=lambda a: (urgency_rank[a["urgency"]], -a.get("pct", 0.0)))

    # full board -- every active theme with its confidence / stage / verdict / crowding / nodes,
    # for the end-of-report appendix (the reader asked to see the whole picture, not just the
    # themes that surfaced as action items today).
    all_themes = []
    for r in rows:
        slug = r["slug"]
        t = sizing_info["themes"].get(slug, {})
        theme_row = core.get("theme_rows", {}).get(slug)
        verdict = theme_row["verdict"] if theme_row else "—"
        eg = exp_gap.get(slug)
        val_label, val_detail = expgap_detail(eg) if eg else (None, None)
        nodes = [{"name": n.get("name"), "tier": n.get("magnitude_tier"),
                   "tickers": n.get("tickers") or []}
                  for n in (t.get("nodes") or [])]
        all_themes.append({
            "slug": slug, "name": theme_zh(slug),
            "confidence": r["confidence"], "cycle_stage": t.get("cycle_stage", "—"),
            "verdict": verdict,
            "valuation": val_label, "valuation_detail": val_detail,
            "nodes": nodes, "target_pct": (r["final"] / budget * 100.0) if budget else 0.0,
        })

    market = {"rows": [], "vix": None, "vix_desc": None,
              "crisis_armed": False, "crisis_raw": None, "leap_quotes": []}
    if mode == "evening" and premkt:
        market["mode"] = "premarket_preview"
        for tk in ("SPY", "QQQ"):
            r = premkt.get(tk)
            if r:
                market["rows"].append({
                    "ticker": tk, "premkt": r["premkt"], "pct": r["pct"], "close": r["close"],
                    "dip": r.get("dip"), "sell": r.get("sell"), "sma": r.get("sma"),
                    "gate": r.get("gate")})
    else:
        market["mode"] = "close"
        triggers = core.get("triggers", {})
        for tk_key, tk_label in (("spy", "SPY"), ("qqq", "QQQ")):
            r = core.get(tk_key)
            if r:
                fresh = "FRESH-CROSS" in r["cross"] or "cross" in r["cross"].lower()
                trig = triggers.get(tk_label) or {}
                market["rows"].append({
                    "ticker": tk_label, "close": r["close"], "sma": r["sma"], "pct": r["pct"],
                    "trend": "向上" if r["side"] == "ABOVE" else "向下", "fresh_cross": fresh,
                    "rsi2": trig.get("rsi2"), "dip": trig.get("dip"), "sell": trig.get("sell"),
                    "break_px": trig.get("sma")})
        for tk_label, q in core.get("leap_quotes", {}).items():
            market["leap_quotes"].append({"ticker": tk_label, **q})
        vix = core.get("vix")
        if vix:
            vix_f = float(vix["vix"])
            market["vix"] = vix["vix"]
            market["vix_desc"] = ("偏低,市場情緒平靜" if vix_f < 20 else
                                   "中等" if vix_f < 30 else "偏高,市場緊張")
        crisis = core.get("crisis") or ""
        market["crisis_armed"] = bool(crisis) and not crisis.startswith("DISARMED")
        market["crisis_raw"] = crisis

    # Portfolio sizing shown as % of the satellite/thematic sleeve, NOT $ -- see the action-item
    # loop above for why (Karst is user-agnostic, doesn't know the reader's account size).
    total_final = sum(r["final"] for r in sizing_info["rows"])
    budget = sizing_info["budget"]
    portfolio = {
        "deployed_pct": (total_final / budget * 100.0) if budget else 0.0,
        "cap_pct": (sizing_info["total_cap"] / budget * 100.0) if budget else 0.0,
        "judge_status": judge_info["status"], "top_concentration": None}
    if mf_shares:
        top = mf_shares[0]
        portfolio["top_concentration"] = {
            "name": META_FACTOR_ZH.get(top["meta_factor"], top["meta_factor"]),
            "pct": top["pct"], "over_cap": top["pct"] > 50}

    matured = judge_info.get("matured", 0)
    need = judge_info.get("thresholds", {}).get("preliminary_matured_min", 60)
    trust_note = (f"提提你:系統仍在驗證期(已完成 {matured}/{need} 次歷史準確度驗證),"
                  "而家啲信心分數係排序參考,唔係已證實嘅準確度,預計2026年10月先有初步結果。")

    aa_note = None
    if aa_latest:
        aa_note = (f"新策略虛擬測試中(未動用真錢):模擬表現 {aa_latest.get('aa_paper_nav'):.2f} "
                   f"vs 現行策略對照 {aa_latest.get('spy_bh_nav'):.2f}")

    high = [a for a in action_items if a["urgency"] == "high"]
    watch = [a for a in action_items if a["urgency"] == "watch"]
    opp = [a for a in action_items if a["urgency"] == "opportunity"]
    anomaly = judge_info["status"] == "FAIL" or judge_info["circuit_breaker"]

    level = "green"
    if high or market["crisis_armed"] or anomaly:
        level = "red"
    elif watch or opp:
        level = "yellow"

    # --- new signal integrations (2026-07-13 finale) ---
    sentinel = load_sentinel()
    sentinel_red = bool(sentinel) and sentinel.get("status") == "red"
    if sentinel_red:
        level = "red"

    ladder = load_ladder()
    ledger = load_ledger_report()
    due_ms, upcoming_ms = load_due_milestones()  # crowding already loaded above (composite step)

    # weave crowding percentile into action items AND the full-board appendix (top-decile
    # crowding on a buy candidate is exactly the "crowded trade" caution feature-5 exists for)
    if crowding and isinstance(crowding.get("themes"), dict):
        for a in action_items:
            c = crowding["themes"].get(a.get("slug") or "", {})
            pct = c.get("composite_pctile")
            if pct is not None:
                a["crowding_pctile"] = pct
        for t in all_themes:
            c = crowding["themes"].get(t["slug"], {})
            t["crowding_pctile"] = c.get("composite_pctile")

    # ledger enrichment: VaR + actionable gaps + roll countdown
    ledger_view = None
    if ledger:
        gaps = [t for t in ledger.get("themes", []) if t.get("action") in ("ADD", "TRIM")]
        gaps.sort(key=lambda t: -abs(t.get("gap_pct") or 0.0))
        roll = []
        for l in ledger.get("core_leaps", []):
            roll.append({"ticker": l.get("ticker"), "days": l.get("days_to_expiry"),
                          "warn": bool(l.get("roll_warn"))})
        ledger_view = {"kill_var_pct": ledger.get("kill_var_pct"),
                        "gaps": gaps[:3], "roll": roll}

    bits = []
    if sentinel_red:
        bits.append("⚠ 數據哨兵紅燈——以下所有讀數可能唔可信,先查數據")
    if high:
        bits.append(f"{len(high)}個主題止蝕訊號已觸發")
    if watch:
        bits.append(f"{len(watch)}個主題估值偏貴需要留意")
    if opp:
        bits.append(f"{len(opp)}個主題可考慮吸納")
    if market["crisis_armed"]:
        bits.append("緊急避險機制已啟動")
    if anomaly:
        bits.append("系統偵測到異常,建議人手覆核")
    if due_ms:
        bits.append(f"{len(due_ms)}條預測到期待判")
    headline = ("、".join(bits) + "。") if bits else "大市維持正常,組合維持現有部署,今日毋須郁手。"

    queue_total = sum(n for n in queues.values() if n is not None) or 0

    return {
        "mode": mode, "level": level, "headline": headline, "action_items": action_items,
        "quiet_count": quiet_count, "market": market, "portfolio": portfolio,
        "trust_note": trust_note, "aa_note": aa_note, "queue_total": queue_total,
        "core_date": core_date, "premkt_date": premkt_date,
        "sentinel": sentinel, "sentinel_red": sentinel_red, "ladder": ladder,
        "ledger": ledger_view, "due_milestones": due_ms or [],
        "upcoming_milestones": upcoming_ms or [], "all_themes": all_themes,
        "news": load_news(), "league": load_league(),
    }


# ============================================================================
# renderers: Telegram (primary, multi-message) + GitHub archive (secondary, same content)
# ============================================================================


def render_telegram_messages(briefing):
    date_str = NOW.strftime("%Y-%m-%d")
    mode_label = "晨早版" if briefing["mode"] == "morning" else "開市前瞻版"
    icon = {"red": "🔴", "yellow": "🟡", "green": "✅"}[briefing["level"]]
    head = f"{icon} Karst 投資簡報 {date_str}({mode_label})"
    ladder = briefing.get("ladder") or {}
    tier = ladder.get("tier")
    if tier:
        head += f"\n市況檔位:{tier}"
    msgs = [f"{head}\n\n{briefing['headline']}"]

    # sentinel red = its own message, first after the headline -- nothing below it is trustworthy
    if briefing.get("sentinel_red"):
        s = briefing.get("sentinel") or {}
        issue_lines = [f"• {i.get('detail', i.get('check', '?'))}" for i in (s.get("issues") or [])[:6]]
        msgs.append("⚠️ 數據哨兵紅燈——今日部分數據未更新,以下讀數請當存疑:\n" + "\n".join(issue_lines))

    if briefing["action_items"]:
        # every card has the SAME skeleton so the reader isn't confused by shifting columns:
        #   點做 (what to do) -> 股票 (which names) -> 三個參考讀數 (trend / valuation / crowding),
        # each read always present, "未評估" where data is missing. Node-level potential-multiple
        # lives ONLY in the appendix (it exists for 5/15 themes, so showing it per-card looks
        # like a bug when it's absent).
        lines = ["【要留意嘅事】"]
        for a in briefing["action_items"]:
            lines.append(f"\n{a['icon']} {a['name']} — {a['label']}")
            # 1) what to do + which names
            if a["urgency"] == "high":
                lines.append("• 點做:整個主題趨勢已破位,建議檢視並考慮減持")
                if a.get("weak_tickers"):
                    lines.append(f"• 當中已破位嘅股票:{'、'.join(a['weak_tickers'])}")
            elif a["urgency"] == "watch":
                lines.append("• 點做:估值偏貴但未破位,今日毋須行動,繼續觀察")
            else:  # opportunity
                lines.append(f"• 點做:可分批吸納,建議佔衛星倉位 {a.get('pct', 0):.0f}%")
                if a.get("ticker"):
                    cur = _current_price(a.get("ticker_sma_price"), a.get("ticker_vs200sma"))
                    cur_s = f"現價約 ${cur:,.0f}," if cur else ""
                    comp_s = f"綜合分 {a['composite']:.0f}/100," if a.get("composite") is not None else ""
                    lines.append(f"• 首選標的:{a['ticker']}({comp_s}{cur_s}距200日均線 {a['ticker_vs200sma']})")
                    if a.get("peer_scores"):
                        peer_line = "、".join(a["peer_scores"])
                        na_tail = (f";{'/'.join(a['peer_na'])} 屬事件型,唔比分"
                                    if a.get("peer_na") else "")
                        lines.append(f"• 同主題比較(綜合分,高=較吸引):{peer_line}{na_tail}")
                    sma_s = a.get("ticker_sma_price")
                    has_sma = sma_s and sma_s != "n/a"
                    lines.append(f"• 入場:現價細注分批;回落至200日均線 {sma_s if has_sma else 'n/a'} 可加大注碼")
                    if has_sma:
                        lines.append(f"• 離場:收市跌穿200日均線 {sma_s} = 趨勢破位,離場訊號")
                    else:
                        lines.append("• 離場:200日均線讀數未有,暫無機械離場位")
                    lines.append("   ↳ 呢啲係系統機械規則(200日均線閘),並非保證獲利嘅訊號")
            # 2) the consistent 3-read block
            is_buy = a["urgency"] == "opportunity"
            lines.append(f"• 趨勢:{trend_read(a.get('ticker_vs200sma'), a.get('triggered'))}")
            lines.append(f"• 市場預期:{a.get('valuation') or '未評估'}")
            if a.get("valuation_detail"):
                lines.append(f"   ↳ {a['valuation_detail']}")
            ctext, _warn = crowding_read(a.get("crowding_pctile"), is_buy)
            lines.append(f"• 擁擠度:{ctext}")
        msgs.append("\n".join(lines))

    trigger_lines = new_trigger_lines(briefing["action_items"], briefing.get("core_date"))
    if trigger_lines:
        tmsg = ["🆕 今日新觸發個股(系統規則今日先由「未觸發」轉「已觸發」,唔係每日重複嘅同一句):",
                "",
                "⚠️ 呢個係本系統嘅入場/離場規則自動判斷,並非已驗證嘅獲利訊號——",
                "跟唔跟由你自己決定。"]
        tmsg.append("")
        tmsg.extend(trigger_lines)
        msgs.append("\n".join(tmsg))

    m = briefing["market"]
    lines = ["大市同組合現況:"]
    if m["mode"] == "premarket_preview":
        lines.append("(開市前預覽價,實際以收市判定為準)")
        for r in m["rows"]:
            lines.append(f"\n{r['ticker']} 開市前 {r['premkt']}(較前收市{r['pct']}%),前收市 {r['close']}")
            bits = []
            if r.get("dip"):
                bits.append(f"逢跌吸納 ≤{r['dip']}")
            if r.get("sell"):
                bits.append(f"賣call ≥{r['sell']}")
            if r.get("sma"):
                bits.append(f"200SMA閘 {r['sma']}({r.get('gate', '?')})")
            if bits:
                lines.append("• " + " | ".join(bits))
        if not m["rows"]:
            lines.append("(未讀到開市前價格數據)")
    else:
        for r in m["rows"]:
            note = " (剛剛轉勢,要留意)" if r["fresh_cross"] else ""
            lines.append(f"\n{r['ticker']} {r['close']}{note}")
            lines.append(f"• 200SMA {r['sma']}({r['trend']}{r['pct']}%)"
                         + (f" | RSI-2 {r['rsi2']}" if r.get("rsi2") else ""))
            bits = []
            if r.get("dip"):
                bits.append(f"逢跌吸納 ≤{r['dip']}")
            if r.get("sell"):
                bits.append(f"賣call ≥{r['sell']}")
            if r.get("break_px"):
                bits.append(f"破位價 {r['break_px']}")
            if bits:
                lines.append("• " + " | ".join(bits))
        if not m["rows"]:
            lines.append("(未讀到大盤讀數)")
        if m["vix"]:
            lines.append(f"\n• VIX恐慌指數:{m['vix']}({m['vix_desc']})")
        if m["crisis_armed"]:
            lines.append(f"• ⚠️ 緊急避險機制:{m['crisis_raw']}")
        if m["leap_quotes"]:
            lines.append("\nLEAP參考報價:")
            for q in m["leap_quotes"]:
                lines.append(f"• {q['ticker']} {q['expiry']}到期(剩{q['dte']}日) "
                             f"K{q['strike']} Δ{q['delta']} 約${q['cost']}/張")
    p = briefing["portfolio"]
    lines.append(f"\n• 已運用衛星倉位額度:{p['deployed_pct']:.0f}%"
                 f"(本階段上限{p['cap_pct']:.0f}%,系統狀態:{p['judge_status']})")
    top_alloc = sorted(briefing.get("all_themes") or [], key=lambda t: -t["target_pct"])[:3]
    if top_alloc:
        lines.append("• 組成(頭三大):" + "、".join(
            f"{t['name']} {t['target_pct']:.0f}%" for t in top_alloc)
            + "——15 個主題全表見文末一覽")
    if p["top_concentration"]:
        tc = p["top_concentration"]
        over = " ⚠️超過安全上限" if tc["over_cap"] else ""
        lines.append(f"• 最集中類別:「{tc['name']}」相關主題共佔{tc['pct']:.0f}%額度{over}")
    lg = briefing.get("ledger")
    if lg:
        if lg.get("kill_var_pct") is not None:
            lines.append(f"• 最壞情境估算:如果所有主題嘅止蝕劇本同時應驗,"
                         f"衛星倉位最多蝕約 {lg['kill_var_pct']:.0f}%(壓力測試數,唔係預測)")
        if lg.get("gaps"):
            lines.append("• 倉位對齊(「現時」= 策略自己嘅紙上累積倉,唔係閣下實倉;"
                         "差距通常因為公式目標郁咗,例如估值閘生效):")
        for g in lg.get("gaps", []):
            act_zh = "加倉" if g.get("action") == "ADD" else "減倉"
            lines.append(f"  ↳ {theme_zh(g.get('slug'))} 建議{act_zh}"
                         f"(目標 {g.get('target_pct', 0):.1f}% vs 現時 {g.get('current_pct', 0):.1f}%)")
        for r in lg.get("roll", []):
            warn = " ⚠️ 換月警戒(剩不足90日)" if r.get("warn") else ""
            lines.append(f"• {r.get('ticker')} LEAP 距到期 {r.get('days')} 日{warn}")
    msgs.append("\n".join(lines))

    # 止蝕條件相關消息 (context, not signal): each item is annotated with WHICH kill axis its
    # query belongs to and a MECHANICAL first-pass direction read -- the honest limit is that
    # direction comes from the query's design (kill-confirming vs kill-relieving), not from
    # reading the article, so the header says 初判 and the human/nightly layer judges.
    news = briefing.get("news") or {}
    items = (news.get("items") or [])[:8]
    if items:
        nlines = ["📰 主題消息(同止蝕條件相關;方向係機械初判,以人判為準):"]
        for it in items:
            nlines.append(f"\n• {theme_zh(it.get('theme'))}|{it.get('title','')[:80]}"
                          f"({it.get('source','?')})")
            if it.get("direction") == "kill-confirming":
                dir_s = "⚠ 傾向止蝕劇本方向(要留意)"
            elif it.get("direction") == "kill-relieving":
                dir_s = "✅ 傾向約束仍然緊(對主題有利)"
            else:
                dir_s = "◻ 方向待判"
            nlines.append(f"  ↳ 掛喺「{it.get('query','?')}」呢條監察軸|{dir_s}")
        # accumulation cue: several confirming items on one theme in one day = review prompt
        from collections import Counter
        confirm_counts = Counter(it.get("theme") for it in items
                                  if it.get("direction") == "kill-confirming")
        heavy = [t for t, n in confirm_counts.items() if n >= 2]
        if heavy:
            nlines.append(f"\n⚠ 同日多條止蝕方向消息:{'、'.join(theme_zh(t) for t in heavy)}"
                          f"——建議人手/夜班判一次「止蝕條件有冇實質靠近」")
        msgs.append("\n".join(nlines))

    lines = []
    if briefing["quiet_count"]:
        lines.append(f"• 其餘 {briefing['quiet_count']} 個主題觀望中,暫時毋須理會。")
    lg2 = briefing.get("league") or {}
    strategies = lg2.get("strategies") or lg2.get("rows") or []
    if strategies:
        lines.append("")
        lines.append("• 紙上擂台(各策略自開賽起表現;回撤 = 期間最大帳面浮虧,非已實現虧損):")
        for s in strategies:
            nm = s.get("label") or s.get("name") or s.get("strategy")
            dd = s.get("max_dd")
            dd_s = f"　回撤 {dd:.1f}%" if dd is not None else ""
            lines.append(f"   {nm}　{s.get('return_pct', 0):+.1f}%{dd_s}")
        holding_lines = []
        for s in strategies:
            hline = _format_holdings_line(s)
            if hline:
                nm = s.get("label") or s.get("name")
                holding_lines.append(f"   ↳ {nm} 目前持倉:{hline}")
        if holding_lines:
            lines.append("")
            lines.extend(holding_lines)
    elif briefing["aa_note"]:
        lines.append(f"• {briefing['aa_note']}")
    due = briefing.get("due_milestones") or []
    upcoming = briefing.get("upcoming_milestones") or []
    if due:
        lines.append(f"• ⚠️ {len(due)} 條系統預測已過期限待判({', '.join(due[:4])}"
                     f"{'…' if len(due) > 4 else ''})——判咗先知系統講嘢準唔準。")
    elif upcoming:
        lines.append(f"• 未來45日內有 {len(upcoming)} 條系統預測到期,到時要對答案。")
    lines.append(f"• {briefing['trust_note']}")
    msgs.append("\n".join(lines))

    # full-board appendix -- every theme, its verdict/confidence/stage/crowding, and its nodes
    # (or an explicit "per-node 評估未做" so the reader knows WHY some themes show a potential
    # multiple and others don't). Split into 2 messages if long, to respect Telegram's limit.
    msgs.extend(_render_appendix(briefing.get("all_themes") or []))
    return msgs


_VERDICT_ICON = {"KILL-WATCH": "🔴", "ACCUMULATE": "🟢", "BUY-ZONE": "🟢",
                 "WAIT": "⚪", "—": "⚪"}
_VERDICT_ZH = {"KILL-WATCH": "止蝕觀察", "ACCUMULATE": "可吸納", "BUY-ZONE": "早期買入",
               "WAIT": "等待", "—": "觀望"}


def _render_appendix(all_themes):
    if not all_themes:
        return []
    header = ("📋 全部主題一覽(🟢可買入行先、🔴止蝕觀察次之、⚪觀望殿後;組內按配置由大到細)\n"
              "\n"
              "潛在倍數 = 如果個 thesis 應驗,呢個分支可以去到幾盡。佢同「信心」係兩個獨立維度\n"
              "(信心 = 應驗嘅可能性,喺主題行顯示)——高信心+高倍數係罕有嘅頭獎象限,唔係矛盾。\n"
              "🔸 約2倍:成熟/大公司攤薄,升幅有限\n"
              "🔷 2-3倍:有真護城河,但市場已 price 咗一截\n"
              "💎 3-5倍・耐久:供給結構性地慢(新產能要幾年),高回報可以維持好耐\n"
              "🎲 5-10倍・二元:得則爆發、唔得近零嘅「形狀」(多數係未盈利/事件股)\n"
              "   ——形狀唔等於冇把握,把握睇信心;細注/選擇權框架處理")
    # sort: buys first (that's what the reader acts on), then kill-watch (risk), then quiet
    _v_rank = {"ACCUMULATE": 0, "BUY-ZONE": 0, "KILL-WATCH": 1}
    all_themes = sorted(all_themes,
                        key=lambda t: (_v_rank.get(t["verdict"], 2), -t["target_pct"]))
    blocks = []
    for t in all_themes:
        cp = t.get("crowding_pctile")
        crowd = f"擁擠{round(cp)}" if cp is not None else "擁擠—"
        vicon = _VERDICT_ICON.get(t["verdict"], "⚪")
        cyc = CYCLE_ZH.get(t["cycle_stage"], t["cycle_stage"])
        # line 1: name + verdict emoji;  line 2: compact one-line stat strip
        head = (f"\n{vicon} {t['name']}　{_VERDICT_ZH.get(t['verdict'], t['verdict'])}\n"
                f"   信心{t['confidence']:.2f}｜{cyc}｜{crowd}｜目標{t['target_pct']:.0f}%")
        sub = [f"   估值:{t.get('valuation') or '未評估'}"]
        if t.get("valuation_detail"):
            sub.append(f"      ↳ {t['valuation_detail']}")
        if t.get("nodes"):
            # nodes sorted by potential multiple, biggest story first (stable sort keeps the
            # value-chain order for ties); the glyph carries the payoff SHAPE so a 🎲 ranking
            # first reads as "biggest IF it works", not "safest".
            nodes_sorted = sorted(
                t["nodes"],
                key=lambda n: -(sizing_mod.parse_magnitude_tier(n.get("tier")) or 0.0))
            for n in nodes_sorted:
                tk = "/".join(n.get("tickers") or []) or "ETF"
                g = tier_glyph(n["tier"])
                sub.append(f"   {g} {node_zh(n['name'])}({tk})— {n['tier']}")
        else:
            sub.append("   ·(此主題 per-node 評估未做)")
        blocks.append(head + "\n" + "\n".join(sub))
    # pack blocks into <=3800-char messages (Telegram hard limit 4096)
    msgs, cur = [], header
    for b in blocks:
        if len(cur) + len(b) + 1 > 3800:
            msgs.append(cur)
            cur = b
        else:
            cur += "\n" + b
    if cur:
        msgs.append(cur)
    return msgs


BACKLOG_NOTE = """---

### 開發者附註(唔係讀者需要睇嘅內容,純技術記錄)

2026-07-13 收官整合後已接線:數據哨兵(data_sentinel.py)、市況檔位+雷達B/C
(opportunity_ladder.py)、kill-VaR/倉位對齊/roll倒數(paper_ledger.py,策略自己紙上持倉,
user-agnostic)、擁擠度(crowding_composite.py)、預測到期提示(milestones.yaml 直讀——
呢個提示機制本身就係 resolver 嘅「唔會漏判」保障)、exp-gap 已由 valuation.py v1 週更接手。

仍未接線(誠實清單):雷達A(閃縮事件庫,等 A backtest 判定)、雷達D(DRAM 只做 confirm
layer,新聞稿監控 job 未起)、ballast 季度體檢未排成經常性 check、IMA 週任務未機讀化、
PNG 圖表未起、valuation 閘接 sizing 嘅執行語意待用戶揀(BT-5 已過閘)。
"""


def render_archive_markdown(briefing):
    date_str = NOW.strftime("%Y-%m-%d %H:%M UTC")
    mode_label = "晨早版" if briefing["mode"] == "morning" else "開市前瞻版"
    parts = [f"# Karst 投資簡報\n\n_{date_str} | {mode_label}_"]
    parts.extend(render_telegram_messages(briefing))
    parts.append(BACKLOG_NOTE)
    return "\n\n---\n\n".join(parts)


# ============================================================================
# telegram + git publish
# ============================================================================


def send_telegram_message(text):
    cred = read_text(TELEGRAM_CRED)
    if not cred:
        return False, "no credential file at ~/.config/karst/telegram"
    lines = [l.strip() for l in cred.strip().split("\n") if l.strip()]
    if len(lines) < 2:
        return False, "credential file malformed (need token line 1, chat_id line 2)"
    token, chat_id = lines[0], lines[1]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # plain text, no parse_mode: avoids Telegram's Markdown-entity parse errors silently
    # dropping a whole message if reader-facing text ever contains a stray */_ character.
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
        return True, "sent"
    except (urllib.error.URLError, OSError) as e:
        return False, str(e)


def send_telegram_messages(messages):
    results = []
    for text in messages:
        ok, msg = send_telegram_message(text)
        results.append((ok, msg))
        if not ok:
            break  # stop the sequence on first failure rather than send out-of-order remnants
    return results


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
                      str(sizing_info["judge"].get("judge_horizon_days", 63)), {}).get("matured", 0)}
    mf_shares = meta_factor_shares(sizing_info["themes"], sizing_info["rows"], sizing_info["total_cap"])
    beta_report = load_beta_report()
    exp_gap, _exp_gap_date = load_expectations_gap()

    queues = {
        "constraint": count_checklist_pending(CONSTRAINT_QUEUE),
        "magnifier": count_checklist_pending(MAGNIFIER_QUEUE),
        "transcripts": count_checklist_pending(PENDING_ANALYSIS),
    }

    briefing = build_briefing(mode, core, core_date, premkt, premkt_date, aa_latest, judge_info,
                               sizing_info, mf_shares, beta_report, exp_gap, queues)
    return briefing


def main():
    ap = argparse.ArgumentParser(description="Render + publish the Karst daily briefing.")
    ap.add_argument("--mode", choices=["morning", "evening"], default="morning")
    ap.add_argument("--no-git", action="store_true", help="skip commit+push to origin/main")
    ap.add_argument("--no-telegram", action="store_true", help="skip Telegram push")
    args = ap.parse_args()

    briefing = render(args.mode)
    md = render_archive_markdown(briefing)

    out_path = os.path.join(MIRROR_ROOT, "DASHBOARD.md")
    if os.path.isdir(MIRROR_ROOT):
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(md)
        print(f"wrote {out_path}")
    else:
        out_path = os.path.join(REPO_ROOT, "DASHBOARD.preview.md")
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(md)
        print(f"WARNING: mirror worktree not found, wrote preview only to {out_path}")

    print(f"alert level: {briefing['level']}")

    if not args.no_git and os.path.isdir(MIRROR_ROOT):
        ok, msg = git_publish(f"dashboard: {args.mode} archive {NOW.strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"git publish (archive only): {'OK' if ok else 'FAILED'} — {msg}")

    if not args.no_telegram:
        messages = render_telegram_messages(briefing)
        results = send_telegram_messages(messages)
        for i, (ok, msg) in enumerate(results):
            print(f"telegram msg {i+1}/{len(messages)}: {'OK' if ok else 'FAILED'} — {msg}")


if __name__ == "__main__":
    main()
