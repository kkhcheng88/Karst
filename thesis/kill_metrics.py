"""thesis/kill_metrics.py -- P4 (docs/2026-07-15_quantification_review.md 提案4): kill 距離分數。

WHY: 每個 theme 嘅 kill_condition 係 prose,「離觸發幾遠」一向靠人判——夜班平模型判唔好呢種質性距離。
呢個腳本讀 themes.yaml 新增嘅 kill_metrics: 欄位(逐條軸已喺 kill_condition prose 入面明文寫低數字/
日期閾值,出處逐條記錄喺 desc),計一個「kill 距離緩衝」讀數,俾夜班/日報引用:
  - 數值型(direction: below/above):
      below (跌穿即 kill):  buffer_pct = (current - trigger) / |trigger| x 100
      above (升穿即 kill):  buffer_pct = (trigger - current) / |trigger| x 100   (方向反轉)
    buffer_pct 愈細/愈負代表愈近觸發(<=0 代表已經跌穿/升穿,應該 flag 人手覆核 confidence)。
  - 日期型(direction: date):days_to_deadline = trigger 日期 - 今日(可以係負數,代表死線已過,
    要人手覆核係咪已再延)。
  - staleness:current_as_of 距今 > STALE_DAYS(120)日 -> 標「讀數過期,要人手更新」(同 P4 提案原話
    一致);日期型冇 current_as_of 就唔查 staleness(死線本身唔會「過期」,只會「過咗」)。

誠實邊界(P4 設計原則):好多 kill 軸本質質性(例如「demand outstripping supply 語言消失」、
「LTA/SCA scorecard stalls or reverses」),呢啲 themes.yaml 冇加 kill_metrics: 欄位——唔係漏,
係刻意保留 prose,唔應該喺呢份 report 出現任何硬塞出嚟嘅數。冇 kill_metrics 嘅 theme 喺 report
尾段列出,誠實交代「呢個 theme 冇可量化軸」。

CLI:
  python thesis/kill_metrics.py --report   計全部 active theme 嘅 kill_metrics,print 表 + 寫
                                            thesis/.raw/kill_metrics_report.json(gitignored,
                                            regenerable,同 valuation_report.json/
                                            crowding_composite.json 一致嘅慣例)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import yaml  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
THEMES_PATH = os.path.join(ROOT, "themes.yaml")
OUT_JSON = os.path.join(ROOT, ".raw", "kill_metrics_report.json")

STALE_DAYS = 120  # current_as_of 距今 > 呢個日數 -> 標「讀數過期」


def load_active_themes() -> dict:
    with open(THEMES_PATH, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    themes = data.get("themes", {}) or {}
    return {slug: t for slug, t in themes.items() if t.get("status", "active") == "active"}


def _parse_date(s) -> date:
    return datetime.strptime(str(s), "%Y-%m-%d").date()


def compute_metric(m: dict, today: date) -> dict:
    """單條 kill_metric(themes.yaml 讀入嘅原始 dict)-> 派生讀數,原始欄位一律原樣帶出。"""
    direction = m.get("direction")
    out = {
        "metric": m.get("metric"),
        "desc": m.get("desc"),
        "direction": direction,
        "current": m.get("current"),
        "current_as_of": m.get("current_as_of"),
        "trigger": m.get("trigger"),
        "update_freq": m.get("update_freq"),
        "buffer_pct": None,
        "days_to_deadline": None,
        "stale": False,
        "flag": None,
    }

    if direction == "date":
        try:
            deadline = _parse_date(m.get("trigger"))
            out["days_to_deadline"] = (deadline - today).days
            if out["days_to_deadline"] < 0:
                out["flag"] = "已過死線,需人手覆核 trigger 有冇再延(kill_condition 事件未必已經發生)"
        except Exception:
            out["flag"] = f"trigger 日期格式錯誤:{m.get('trigger')!r}"
        return out

    current, trigger = m.get("current"), m.get("trigger")
    if current is None or trigger is None:
        out["flag"] = "數值型缺 current/trigger,唔計 buffer(檢查 themes.yaml)"
        return out
    try:
        current_f, trigger_f = float(current), float(trigger)
    except (TypeError, ValueError):
        out["flag"] = f"current/trigger 唔係數字:current={current!r} trigger={trigger!r}"
        return out
    if trigger_f == 0:
        out["flag"] = "trigger=0,buffer_pct 唔可計(除0)"
        return out

    if direction == "below":
        buffer_pct = (current_f - trigger_f) / abs(trigger_f) * 100.0
    elif direction == "above":
        buffer_pct = (trigger_f - current_f) / abs(trigger_f) * 100.0
    else:
        out["flag"] = f"未知 direction:{direction!r}(得 below/above/date)"
        return out

    out["buffer_pct"] = round(buffer_pct, 1)
    if buffer_pct <= 0:
        out["flag"] = "已跌穿/升穿觸發 -- 應人手覆核,考慮 confidence 歸零"

    as_of = m.get("current_as_of")
    if as_of:
        try:
            age_days = (today - _parse_date(as_of)).days
            if age_days > STALE_DAYS:
                out["stale"] = True
                stale_msg = f"讀數過期({age_days}日 > {STALE_DAYS}日),要人手更新 current"
                out["flag"] = f"{out['flag']}; {stale_msg}" if out["flag"] else stale_msg
        except Exception:
            pass

    return out


def run(write: bool = True) -> dict:
    themes = load_active_themes()
    today = date.today()

    theme_rows: dict[str, list[dict]] = {}
    themes_without_metrics: list[str] = []
    n_numeric = n_date = 0

    for slug, t in sorted(themes.items()):
        kms = t.get("kill_metrics") or []
        if not kms:
            themes_without_metrics.append(slug)
            continue
        rows = [compute_metric(m, today) for m in kms]
        for r in rows:
            if r["direction"] == "date":
                n_date += 1
            else:
                n_numeric += 1
        theme_rows[slug] = rows

    n_with = len(theme_rows)
    print(f"=== kill_metrics report ({today.isoformat()}):"
          f" {n_with}/{len(themes)} active themes 有可量化 kill 軸,"
          f"共 {n_numeric} 條數值型 + {n_date} 條日期型 ===\n")

    for slug in sorted(theme_rows):
        print(f"[{slug}]")
        for r in theme_rows[slug]:
            flag = r["flag"] or ""
            if r["direction"] == "date":
                dl = r["days_to_deadline"]
                dl_s = f"{dl:+d}日" if dl is not None else "n/a"
                print(f"  {r['metric']:<32} 死線={str(r['trigger']):<12} 距今={dl_s:<10} {flag}")
            else:
                cur_s = repr(r["current"])
                trg_s = repr(r["trigger"])
                buf = r["buffer_pct"]
                buf_s = f"{buf:+.1f}%" if buf is not None else "n/a"
                print(f"  {r['metric']:<32} current={cur_s:<10} trigger={trg_s:<8} "
                      f"方向={r['direction']:<6} 緩衝={buf_s:<10} {flag}")
        print()

    if themes_without_metrics:
        print("冇可量化 kill 軸(kill_condition 全質性,保留 prose,人手判斷距離):")
        print("  " + ", ".join(themes_without_metrics))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of_date": today.isoformat(),
        "stale_threshold_days": STALE_DAYS,
        "n_active_themes": len(themes),
        "n_themes_with_kill_metrics": n_with,
        "n_numeric_metrics": n_numeric,
        "n_date_metrics": n_date,
        "themes_without_kill_metrics": themes_without_metrics,
        "themes": theme_rows,
    }
    if write:
        os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
        with open(OUT_JSON, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"\nWrote {OUT_JSON}")
    return payload


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true",
                     help="計全部 active theme 嘅 kill_metrics,print 表 + 寫 "
                          "thesis/.raw/kill_metrics_report.json")
    args = ap.parse_args()
    if args.report or len(sys.argv) == 1:
        run(write=True)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
