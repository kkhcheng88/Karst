"""thesis/trim_rule_tracker.py -- 「獲利回收 trim 規則」前瞻 paper 追蹤機制 (Fable 交接書 P2-15;
backtest/results/2026-07-13_trim_rule_validation.md 係呢個規則嘅回溯初驗)。

WHY: Fable 交接書 P2-15 建議「擁擠複合 top decile + 倉位 >= 2x 成本 -> trim 1/3」呢條獲利回收規則,
但兩個前置(擁擠複合、紙上台帳)2026-07-13 先啱啱到位,規則本身有冇用要 paper 記錄一段時間先知
(track-record-before-adopt 原則,同 thesis/DESIGN.md Sec6 track_record 校準嗰套精神一致)。呢個
腳本淨係做「今日判定 + log 一行」,唔郁台帳、唔自動 trim -- decision support,人裁決。

Trigger 條件(逐 satellite theme):
  1. composite_pctile >= TRIGGER_COMPOSITE_PCTILE (90)   -- 擁擠複合 top decile,讀
     thesis/.raw/crowding_composite.json(thesis/crowding_composite.py 產生,唔喺呢度重算)。
  2. position_multiple >= TRIGGER_MULTIPLE (2.0)          -- 現在倉位 >= 2x 成本(entry)。

position_multiple 點計:paper_ledger.json 嘅 schema 淨係存 {current_pct, entry_date, last_marked},
冇單獨一個 "entry_pct" 欄位(唔改 paper_ledger.py 嘅任務限制下,唔加呢個欄位)。但
paper_ledger.cmd_update() 嘅 mark-to-market 係純複利:current_pct(t) = entry_pct * cum_basket_ratio
(entry_date -> t)(冇任何中途 trim/加碼會打斷呢條式,而家個台帳由頭到尾都未 trim 過)。所以
position_multiple = current_pct(now) / entry_pct 在數學上完全等於 cum_basket_ratio(entry_date -> now)
-- 用同一個 tickers 籃子(beta_check.build_basket,同 paper_ledger.py 用緊嗰個一樣)由 entry_date 讀到
今日嘅累積總回報倍數反推,唔需要新增任何 shadow state file 去記 entry_pct,亦唔會偏離台帳本身嘅
複利邏輯半分。

Reads (只讀,唔寫):
  thesis/.raw/crowding_composite.json  -- 擁擠複合(缺席會誠實提示先跑 crowding_composite.py)
  thesis/paper_ledger.json             -- 紙上台帳 state(NEVER 寫返入去)
  thesis/themes.yaml                   -- 逐 theme 嘅 tickers(起 basket 用)

Writes:
  thesis/.raw/trim_rule_log.jsonl      -- append-only 決策支援 log,淨係喺 TRIGGERED 先寫一行
                                           (同一日同一 theme 唔重複寫,idempotent)。已由 .gitignore
                                           嘅 `thesis/.raw/**/*.jsonl` 規則覆蓋,唔使加新規則。

Run: python thesis/trim_rule_tracker.py --status
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd  # noqa: E402
import yaml  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))          # thesis/
REPO_ROOT = os.path.dirname(ROOT)                            # Karst/
sys.path.insert(0, ROOT)
sys.path.insert(0, REPO_ROOT)
import beta_check as beta_check_mod  # noqa: E402 -- sibling module, build_basket() reused as-is

THEMES_PATH = os.path.join(ROOT, "themes.yaml")
CROWDING_PATH = os.path.join(ROOT, ".raw", "crowding_composite.json")
LEDGER_PATH = os.path.join(ROOT, "paper_ledger.json")
LOG_PATH = os.path.join(ROOT, ".raw", "trim_rule_log.jsonl")

TRIGGER_COMPOSITE_PCTILE = 90.0   # 擁擠複合 top decile(composite_pctile 0-100 量尺)
TRIGGER_MULTIPLE = 2.0            # 倉位 >= 2x 成本
TRIM_FRACTION = "1/3"             # 建議 trim 幅度(Fable 交接書 P2-15 原文;呢度淨係建議,唔執行)


def _today_str() -> str:
    return datetime.now().date().isoformat()


def load_themes() -> dict:
    with open(THEMES_PATH, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data.get("themes", {}) or {}


def load_crowding() -> dict | None:
    if not os.path.exists(CROWDING_PATH):
        return None
    with open(CROWDING_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def load_ledger() -> dict | None:
    if not os.path.exists(LEDGER_PATH):
        return None
    with open(LEDGER_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def position_multiple(tickers: list[str], entry_date: str) -> tuple[float | None, str]:
    """cum_basket_ratio(entry_date -> today) -- 見 module docstring,呢個數學上等於
    current_pct(now)/entry_pct。Returns (multiple|None, note)."""
    if not tickers:
        return None, "theme 冇 tickers,起唔到 basket"
    basket_ret, loaded, failed = beta_check_mod.build_basket(tickers)
    if basket_ret is None or len(basket_ret) == 0:
        return None, f"basket load 失敗(loaded={loaded}, failed={failed})"
    cum = (1.0 + basket_ret).cumprod()
    anchor_ts = pd.Timestamp(entry_date)
    prior = cum[cum.index <= anchor_ts]
    if len(prior) == 0:
        return None, f"entry_date {entry_date} 早過 basket 已載入嘅最早交易日,計唔到"
    entry_val = float(prior.iloc[-1])
    current_val = float(cum.iloc[-1])
    if entry_val <= 0:
        return None, "entry 錨點值 <= 0,計唔到倍數"
    mult = current_val / entry_val
    note = f"basket {len(loaded)}/{len(tickers)} 隻載入,錨點 {prior.index[-1].date()} -> {cum.index[-1].date()}"
    if failed:
        note += f"(略過 {failed})"
    return mult, note


def _already_logged_today(theme: str, date: str) -> bool:
    if not os.path.exists(LOG_PATH):
        return False
    with open(LOG_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("date") == date and rec.get("theme") == theme:
                return True
    return False


def _append_log(rec: dict) -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def cmd_status() -> None:
    themes = load_themes()
    crowding = load_crowding()
    ledger = load_ledger()
    today = _today_str()

    if ledger is None:
        print(f"無 {LEDGER_PATH} -- 先跑 `python thesis/paper_ledger.py --init`。")
        return
    if crowding is None:
        print(f"無 {CROWDING_PATH} -- 先跑 `python thesis/crowding_composite.py`。")
        return

    crowd_generated_at = crowding.get("generated_at", "?")
    crowd_themes = crowding.get("themes", {})

    print(f"=== trim_rule_tracker --status ({today}) ===")
    print(f"觸發條件:composite_pctile >= {TRIGGER_COMPOSITE_PCTILE:.0f} AND "
          f"position_multiple >= {TRIGGER_MULTIPLE:.1f}x  |  擁擠複合快照時間: {crowd_generated_at}")
    print(f"{'theme':<32}{'composite':>10}{'mult':>8}{'triggered':>11}  note")
    print("-" * 100)

    triggered = []
    for slug, pos in sorted(ledger.get("satellite", {}).items()):
        theme = themes.get(slug, {})
        tickers = theme.get("tickers") or []
        entry_date = pos.get("entry_date")

        crow = crowd_themes.get(slug, {})
        comp_status = crow.get("composite_status")
        comp_val = crow.get("composite_pctile")

        mult, mult_note = position_multiple(tickers, entry_date) if entry_date else (None, "台帳無 entry_date")

        comp_ok = comp_status == "ok" and comp_val is not None and comp_val >= TRIGGER_COMPOSITE_PCTILE
        mult_ok = mult is not None and mult >= TRIGGER_MULTIPLE
        is_triggered = comp_ok and mult_ok

        comp_s = f"{comp_val:.1f}" if comp_val is not None else "n/a"
        mult_s = f"{mult:.2f}x" if mult is not None else "n/a"
        trig_s = "TRIGGERED" if is_triggered else "-"
        print(f"{slug:<32}{comp_s:>10}{mult_s:>8}{trig_s:>11}  {mult_note}")

        if is_triggered:
            triggered.append({
                "slug": slug, "composite_pctile": comp_val, "position_multiple": round(mult, 4),
            })

    print("-" * 100)
    if not triggered:
        print(f"今日判定:無觸發(0 個 theme 同時滿足擁擠 top decile + 倉位 >= {TRIGGER_MULTIPLE:.0f}x 成本)。"
              "台帳啱啱初始化(entry_date = 今日附近),position_multiple 理應貼近 1.0x -- 呢個係預期內嘅"
              "誠實結果,唔係機制壞咗。")
        return

    print(f"今日判定:{len(triggered)} 個 theme 觸發 trim 建議(唔會自動執行,已寫 log 俾人審核):")
    for t in triggered:
        rec = {
            "date": today,
            "theme": t["slug"],
            "composite_pctile": t["composite_pctile"],
            "position_multiple": t["position_multiple"],
            "suggested_action": f"trim {TRIM_FRACTION}(擁擠複合 top decile + 倉位 >= {TRIGGER_MULTIPLE:.0f}x 成本)",
            "decision": "PENDING_HUMAN_REVIEW",
            "ledger_touched": False,
        }
        if _already_logged_today(t["slug"], today):
            print(f"  {t['slug']}: 今日已經 log 過,冇重複寫")
            continue
        _append_log(rec)
        print(f"  {t['slug']}: composite={t['composite_pctile']:.1f}  "
              f"multiple={t['position_multiple']:.2f}x  -> 已寫入 {LOG_PATH}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="trim 規則(擁擠複合 top decile + 倉位>=2x成本 -> 建議 trim 1/3)前瞻追蹤 -- "
                     "決策支援,唔郁台帳,人裁決。")
    ap.add_argument("--status", action="store_true", help="印今日判定(觸發時同時寫 trim_rule_log.jsonl 一行)")
    args = ap.parse_args()
    if not args.status:
        ap.print_help()
        return
    cmd_status()


if __name__ == "__main__":
    main()
