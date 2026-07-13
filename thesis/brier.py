"""Milestone-Brier scorer —— Karst 裁判嘅第二把尺(Fable 交接 D7 / P0-2)。

現行裁判 forward_ic.py 用 63d 橫截面 IC:有效闊度 = 主題數(同主題 ticker 共用 confidence),
而且 63d horizon 同 1-3 年 thesis 錯配。呢個 scorer 補 horizon-matched 校準——掃 thesis/milestones.yaml,
對已 resolved 嘅具名預測計 Brier = mean((probability - outcome)^2),按 theme 同全局各出一個滾動分數,
先至答到「系統話 0.7 嘅嘢係咪真係 70% 中」。IC = 市場驗證,Brier = 敘事校準,兩把尺互補。

用法:
  python thesis/brier.py --score              # 計 Brier(全局 + 逐 theme);列出過期待判項
  python thesis/brier.py --list               # 全部里程碑(逐 theme)
  python thesis/brier.py --list --pending     # 只列 pending
  python thesis/brier.py --list --due         # 只列過期未判(deadline < 今日 且仍 pending)

只讀 thesis/milestones.yaml,唔郁任何其他檔。
"""
import argparse
import os
import sys
from datetime import date

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")   # Windows cp950 主控台照出繁中

MILESTONES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "milestones.yaml")


def _load():
    with open(MILESTONES, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    return doc.get("meta", {}) or {}, doc.get("milestones", []) or []


def _is_resolved(m):
    return m.get("resolved") is not None and m.get("outcome") in (0, 1, True, False)


def _brier(rows):
    """rows: list of (probability, outcome). 回傳 (score, n)。"""
    pairs = [(float(p), int(bool(o))) for p, o in rows]
    if not pairs:
        return None, 0
    return sum((p - o) ** 2 for p, o in pairs) / len(pairs), len(pairs)


def cmd_score(_meta, ms):
    today = date.today()
    resolved = [m for m in ms if _is_resolved(m)]
    overdue = [m for m in ms if not _is_resolved(m)
               and date.fromisoformat(str(m["deadline"])) < today]

    print(f"=== milestone-Brier 計分（共 {len(ms)} 條，已判 {len(resolved)}）===\n")
    if not resolved:
        print("未有已 resolved 條目 —— 冇 outcome 可計，Brier 分數仍未有讀數。")
        print("（把尺啱起,等最早到期嗰批判咗 true/false 先會出第一個分數。）")
    else:
        by_theme = {}
        for m in resolved:
            by_theme.setdefault(m["theme"], []).append((m["probability"], m["outcome"]))
        g_score, g_n = _brier([(m["probability"], m["outcome"]) for m in resolved])
        print(f"全局 Brier = {g_score:.4f}  (n={g_n}；0=完美, 0.25=擲毫, 越低越準)\n")
        print("逐 theme：")
        for th in sorted(by_theme):
            s, n = _brier(by_theme[th])
            print(f"  {th:<32} Brier={s:.4f}  n={n}")

    print(f"\n--- 過期待判（deadline < {today}，仍 pending，共 {len(overdue)}）---")
    if not overdue:
        print("（無）")
    else:
        for m in sorted(overdue, key=lambda x: str(x["deadline"])):
            print(f"  [{m['deadline']}] {m['id']}  P={m['probability']}")
            print(f"      {m['claim']}")


def cmd_list(_meta, ms, only_pending, only_due):
    today = date.today()
    rows = ms
    label = "全部"
    if only_due:
        rows = [m for m in ms if not _is_resolved(m)
                and date.fromisoformat(str(m["deadline"])) < today]
        label = f"過期待判 (deadline < {today})"
    elif only_pending:
        rows = [m for m in ms if m.get("status") == "pending"]
        label = "pending"

    print(f"=== 里程碑清單：{label}（{len(rows)} 條）===\n")
    if not rows:
        print("（無符合條件嘅條目）")
        return
    for th in sorted({m["theme"] for m in rows}):
        group = [m for m in rows if m["theme"] == th]
        print(f"[{th}]  ({len(group)} 條)")
        for m in sorted(group, key=lambda x: str(x["deadline"])):
            mark = "✓判" if _is_resolved(m) else "…pending"
            print(f"  {m['id']:<36} {m['deadline']}  P={m['probability']:<4}  {mark}  <{m['direction']}>")
            print(f"      {m['claim']}")
        print()


def main():
    ap = argparse.ArgumentParser(description="Karst milestone-Brier scorer")
    ap.add_argument("--score", action="store_true", help="計 Brier + 列過期待判")
    ap.add_argument("--list", dest="do_list", action="store_true", help="human-readable 清單")
    ap.add_argument("--pending", action="store_true", help="(配 --list) 只列 pending")
    ap.add_argument("--due", action="store_true", help="(配 --list) 只列過期待判")
    args = ap.parse_args()

    meta, ms = _load()
    if args.score:
        cmd_score(meta, ms)
    elif args.do_list:
        cmd_list(meta, ms, args.pending, args.due)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
