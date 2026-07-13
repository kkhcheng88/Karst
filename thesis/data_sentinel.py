"""thesis/data_sentinel.py — Karst data freshness sentinel.

Motivation (docs/2026-07-08_phase3_architecture.md sec5 backlog #3): the dashboard renders a
daily briefing by AGGREGATING output files a chain of scheduled batch jobs already wrote (see
thesis/dashboard_render.py). None of those files carry their own "am I stale?" flag -- if a
batch job silently stops running, or yfinance goes quiet, the reader has no way to tell a real
fresh signal from a stale one wearing today's date on the dashboard chrome. This script is the
single place that checks "is every upstream data source actually current" and writes one
report-only verdict. When it goes red, EVERY other reading on the dashboard that day should be
treated as unverified -- but that wiring (suppressing/flagging the rest of the briefing) is the
dashboard's job, not this script's. This script only checks and reports.

Report-only by design: exit code is ALWAYS 0, and no check is allowed to raise past its own
try/except -- a missing file or a parse failure is exactly the kind of thing this sentinel
exists to surface, so it must become an "issue" entry, never a crash (see run_check()).

8 checks (see thesis/DESIGN.md-adjacent docs/2026-07-08_phase3_architecture.md sec5 #3 for the
motivating gap analysis; each check's own tolerance is documented on the check function):
  1. playbook_freshness    -- playbook_log.txt latest "Core v2 playbook readout" block's date,
                               vs the approximate previous US trading day (<=2 trading days old)
  2. premarket_freshness    -- premarket_log.txt latest "PREMARKET CHECK" block (<=4 cal days)
  3. aa_paper_log_freshness -- thesis/.raw/aa_strict_paper_log.jsonl last line's date (<=4 cal days)
  4. ic_report_freshness    -- thesis/ic_report.json generated_at (<=4 cal days)
  5. beta_report_freshness  -- thesis/.raw/beta_check_report.json generated_at (<=10 cal days, weekly)
  6. themes_yaml_parse      -- thesis/themes.yaml parses with yaml.safe_load
  7. yfinance_spot_check    -- backtest/data.py load('SPY') last close date, vs previous US
                               trading day (<=2 trading days old) -- catches a silent yfinance outage
  8. crash_safety           -- meta-check: reaching this line proves every check above ran inside
                               run_check()'s try/except, so no unhandled exception escaped any of
                               them (see run_check()). Always ok=True; this is a structural
                               guarantee, not a data reading.

Trading-day approximation (per spec, used by checks 1 and 7): skip Saturday/Sunday only, no US
market-holiday calendar. A holiday will therefore show up as a false-positive "stale" issue --
each such issue's detail text says so explicitly, so a human reader isn't misled.

Run: python thesis/data_sentinel.py [--verbose]
     python thesis/data_sentinel.py --playbook-path <bogus path>   # forces a red/issue for testing
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))            # thesis/
REPO_ROOT = os.path.dirname(ROOT)                              # Karst/

PLAYBOOK_LOG = os.path.join(REPO_ROOT, "playbook_log.txt")
PREMARKET_LOG = os.path.join(REPO_ROOT, "premarket_log.txt")
AA_LOG = os.path.join(ROOT, ".raw", "aa_strict_paper_log.jsonl")
IC_REPORT = os.path.join(ROOT, "ic_report.json")
BETA_REPORT = os.path.join(ROOT, ".raw", "beta_check_report.json")
THEMES_YAML = os.path.join(ROOT, "themes.yaml")
OUT_PATH = os.path.join(ROOT, ".raw", "data_sentinel.json")

NOW = datetime.now(timezone.utc)

# ============================================================================
# small self-contained parsing helpers (deliberately NOT imported from dashboard_render.py --
# a sentinel should not be able to crash because of an unrelated module's own import chain;
# last_block()'s split-on-'==== ... ===='-header logic mirrors thesis/dashboard_render.py's
# function of the same name, which is the reference implementation named in the spec)
# ============================================================================


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def last_block(text, marker):
    """Split `text` on '==== ... ====' header lines; return (block, header_str) for the LAST
    block that contains `marker`, or (None, None)."""
    if not text:
        return None, None
    parts = re.split(r"(?=^==== .+ ====\s*$)", text, flags=re.MULTILINE)
    for part in reversed(parts):
        if marker in part:
            m = re.match(r"^==== (.+?) ====", part)
            return part, (m.group(1) if m else None)
    return None, None


# header text isn't always ISO ("==== 2026-07-13 05:42 ====" vs an older
# "==== 週三 2026/07/08 16:51:29.76 ====" style) -- search for either dash- or slash-separated
# y/m/d anywhere in the header rather than anchoring to the start.
DATE_IN_HEADER_RE = re.compile(r"(\d{4})[-/](\d{2})[-/](\d{2})")


def parse_date_from_header(header):
    if not header:
        return None
    m = DATE_IN_HEADER_RE.search(header)
    if not m:
        return None
    y, mo, d = (int(x) for x in m.groups())
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def parse_date_only(s):
    """'2026-07-10' or '2026-07-10T05:00:00' -> date(2026,7,10); None on any failure."""
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_iso(s):
    if not s:
        return None
    s = str(s).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def prev_trading_day(ref_date):
    """Approximate previous US trading day: skip Sat/Sun only, no holiday calendar (per spec --
    holiday false-positives are called out in the issue text of callers instead)."""
    d = ref_date - timedelta(days=1)
    while d.weekday() >= 5:  # Sat=5, Sun=6
        d -= timedelta(days=1)
    return d


def trading_days_ago(check_date, ref_date):
    """How many (weekend-skipping) trading days before prev_trading_day(ref_date) does
    check_date fall? 0 = check_date IS the previous trading day (or newer)."""
    anchor = prev_trading_day(ref_date)
    if check_date >= anchor:
        return 0
    n, d = 0, anchor
    while d > check_date:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


# ============================================================================
# checks 1-7 -- each returns (ok: bool, detail: str in Traditional Chinese)
# ============================================================================


def check_playbook(ref_date, path):
    text = read_text(path)
    if text is None:
        return False, f"playbook_log.txt 讀取失敗或唔存在:{path}"
    block, header = last_block(text, "Core v2 playbook readout")
    if block is None:
        return False, "playbook_log.txt 入面搵唔到最新嘅 'Core v2 playbook readout' 區塊"
    d = parse_date_from_header(header)
    if d is None:
        return False, f"playbook_log.txt 最新區塊日期解析失敗(區塊標頭:{header!r})"
    age = trading_days_ago(d, ref_date)
    if age > 2:
        return False, (f"playbook readout 最新日期 {d},已相隔 {age} 個交易日"
                        f"(交易日以跳過六日近似,實際亦有可能係美股假期),批次 job 可能冇跑")
    return True, f"playbook readout 最新日期 {d},相隔 {age} 個交易日,新鮮"


def check_premarket(ref_date, path):
    text = read_text(path)
    if text is None:
        return False, f"premarket_log.txt 讀取失敗或唔存在:{path}"
    block, header = last_block(text, "PREMARKET CHECK")
    if block is None:
        return False, "premarket_log.txt 入面搵唔到最新嘅 'PREMARKET CHECK' 區塊"
    d = parse_date_from_header(header)
    if d is None:
        return False, f"premarket_log.txt 最新區塊日期解析失敗(區塊標頭:{header!r})"
    age = (ref_date - d).days
    if age > 4:
        return False, f"premarket_log.txt 最新區塊日期 {d},已相隔 {age} 日曆日(上限4日,已容忍週末)"
    return True, f"premarket_log.txt 最新區塊日期 {d},相隔 {age} 日曆日,新鮮"


def check_aa_log(ref_date, path):
    text = read_text(path)
    if text is None:
        return False, f"aa_strict_paper_log.jsonl 讀取失敗或唔存在:{path}"
    lines = [l for l in text.strip().split("\n") if l.strip()]
    if not lines:
        return False, "aa_strict_paper_log.jsonl 存在但係空檔"
    try:
        rec = json.loads(lines[-1])
    except json.JSONDecodeError as e:
        return False, f"aa_strict_paper_log.jsonl 最後一行 JSON 解析失敗:{e}"
    d = parse_date_only(rec.get("date"))
    if d is None:
        return False, f"aa_strict_paper_log.jsonl 最後一行冇有效 date 欄位(值:{rec.get('date')!r})"
    age = (ref_date - d).days
    if age > 4:
        return False, f"aa_strict_paper_log.jsonl 最後一筆日期 {d},已相隔 {age} 日曆日(上限4日)"
    return True, f"aa_strict_paper_log.jsonl 最後一筆日期 {d},相隔 {age} 日曆日,新鮮"


def check_json_generated_at(ref_date, path, label, max_age_days):
    text = read_text(path)
    if text is None:
        return False, f"{label} 讀取失敗或唔存在:{path}"
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as e:
        return False, f"{label} JSON 解析失敗:{e}"
    ts = obj.get("generated_at") if isinstance(obj, dict) else None
    dt = parse_iso(ts)
    if dt is None:
        return False, f"{label} 冇有效 generated_at 欄位(值:{ts!r})"
    age = (ref_date - dt.date()).days
    if age > max_age_days:
        return False, f"{label} generated_at={dt.date()},已相隔 {age} 日曆日(上限{max_age_days}日)"
    return True, f"{label} generated_at={dt.date()},相隔 {age} 日曆日,新鮮"


def check_themes_yaml(path):
    text = read_text(path)
    if text is None:
        return False, f"themes.yaml 讀取失敗或唔存在:{path}"
    try:
        obj = yaml.safe_load(text)
    except yaml.YAMLError as e:
        return False, f"themes.yaml YAML 解析失敗:{e}"
    if obj is None:
        return False, "themes.yaml 可以解析但內容係空"
    n = len(obj) if hasattr(obj, "__len__") else "?"
    return True, f"themes.yaml 可以正常 yaml.safe_load,頂層 {n} 個項目"


def check_yfinance_spot(ref_date):
    try:
        if REPO_ROOT not in sys.path:
            sys.path.insert(0, REPO_ROOT)
        from backtest import data as data_mod  # local import: heavy (yfinance/defeatbeta) chain
        df = data_mod.load("SPY")
    except Exception as e:
        return False, f"yfinance spot check 失敗(backtest/data.py load('SPY')):{type(e).__name__}: {e}"
    if df is None or len(df) == 0:
        return False, "yfinance spot check:backtest/data.py load('SPY') 回傳空資料"
    try:
        d = df.index.max().date()
    except (AttributeError, TypeError):
        return False, f"yfinance spot check:SPY 最後日期格式異常({df.index.max()!r})"
    age = trading_days_ago(d, ref_date)
    if age > 2:
        return False, (f"yfinance spot check:SPY 最後收市日 {d},已相隔 {age} 個交易日"
                        f"(交易日以跳過六日近似,實際亦有可能係美股假期),yfinance 可能斷咗")
    return True, f"yfinance spot check:SPY 最後收市日 {d},相隔 {age} 個交易日,新鮮"


# ============================================================================
# runner + main
# ============================================================================


def run_check(name, fn):
    """Wrap a check so NOTHING it does can crash the sentinel -- any unexpected exception
    becomes an issue on that one check instead of taking down the whole run (spec item 8)."""
    try:
        ok, detail = fn()
    except Exception as e:  # noqa: BLE001 -- deliberately broad, this is the crash firewall
        ok, detail = False, (f"{name} 檢查本身拋出未預期例外(已攔截,冇令哨兵崩潰):"
                              f"{type(e).__name__}: {e}")
    return {"check": name, "ok": bool(ok), "detail": detail}


def main():
    ap = argparse.ArgumentParser(
        description="Karst data freshness sentinel (report-only, exit code always 0).")
    ap.add_argument("--verbose", action="store_true", help="print每項檢查結果")
    ap.add_argument("--playbook-path", default=PLAYBOOK_LOG)
    ap.add_argument("--premarket-path", default=PREMARKET_LOG)
    ap.add_argument("--aa-log-path", default=AA_LOG)
    ap.add_argument("--ic-report-path", default=IC_REPORT)
    ap.add_argument("--beta-report-path", default=BETA_REPORT)
    ap.add_argument("--themes-path", default=THEMES_YAML)
    ap.add_argument("--out-path", default=OUT_PATH)
    ap.add_argument("--skip-yfinance", action="store_true",
                     help="跳過真實 yfinance 網絡呼叫(測試用,唔代表已驗證新鮮度)")
    args = ap.parse_args()

    ref_date = NOW.date()

    checks = [
        run_check("playbook_freshness", lambda: check_playbook(ref_date, args.playbook_path)),
        run_check("premarket_freshness", lambda: check_premarket(ref_date, args.premarket_path)),
        run_check("aa_paper_log_freshness", lambda: check_aa_log(ref_date, args.aa_log_path)),
        run_check("ic_report_freshness", lambda: check_json_generated_at(
            ref_date, args.ic_report_path, "ic_report.json", 4)),
        run_check("beta_report_freshness", lambda: check_json_generated_at(
            ref_date, args.beta_report_path, "beta_check_report.json", 10)),
        run_check("themes_yaml_parse", lambda: check_themes_yaml(args.themes_path)),
    ]
    if args.skip_yfinance:
        checks.append({"check": "yfinance_spot_check", "ok": True,
                        "detail": "已用 --skip-yfinance 跳過真實網絡呼叫(測試用,唔代表已驗證新鮮度)"})
    else:
        checks.append(run_check("yfinance_spot_check", lambda: check_yfinance_spot(ref_date)))

    # check 8 (crash_safety): a structural guarantee, not a data reading -- reaching this line
    # proves every check above ran inside run_check()'s try/except, so no unhandled exception
    # escaped any of them.
    checks.append({"check": "crash_safety", "ok": True,
                   "detail": "全部檢查已喺 try/except 保護下執行完成,無未攔截例外令哨兵崩潰"})

    issues = [{"check": c["check"], "detail": c["detail"]} for c in checks if not c["ok"]]
    status = "red" if issues else "green"

    result = {
        "generated_at": NOW.isoformat(),
        "status": status,
        "issues": issues,
        "checks": checks,  # full per-check detail (incl. ok ones) -- extra, dashboard may use later
    }

    out_dir = os.path.dirname(args.out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)

    if args.verbose:
        for c in checks:
            mark = "OK" if c["ok"] else "ISSUE"
            print(f"[{mark}] {c['check']}: {c['detail']}")
    print(f"data_sentinel: status={status} issues={len(issues)}/{len(checks)} -> wrote {args.out_path}")

    return 0  # report-only: exit code is ALWAYS 0 regardless of status


if __name__ == "__main__":
    sys.exit(main())
