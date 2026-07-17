"""backtest/lint_results.py -- mechanical gates against the two failure modes of 2026-07-17.

That day produced six wrong verdicts in one session. All six shared two mechanical
signatures, both of which are text-checkable:
  1. An experiment ran without citing the frozen assumption charter (so it silently
     re-imported default assumptions -- full history, in/out framing, wrong metric).
  2. A negative verdict was issued with no control arm (single-arm test against a
     convenient benchmark). Five same-day overturns each came from adding ONE
     control arm to the SAME machine.

Rules (only files dated >= CUTOFF are gated; the 145 legacy files are history,
SETTLED.md already adjudicated them):
  R1  backtest/experiments/exp_*.py newer than CUTOFF must contain "ASSUMPTIONS.md".
  R2  backtest/results/*.md newer than CUTOFF containing a negative-verdict keyword
      must also contain a control-arm keyword.

Run: PYTHONUTF8=1 python backtest/lint_results.py   (exit 1 on any ERROR)
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CUTOFF = "2026-07-18"  # gates apply to work created from this date onward

NEG_KEYWORDS = ["冇料", "冇增量", "無增量", "唔採納", "判死", "封盤", "no edge",
                "no increment", "死咗", "否證", "falsified"]
CONTROL_KEYWORDS = ["對照", "control", "隨機同曝險", "random same-exposure", "配對",
                    "matched", "null", "A/B", "placebo"]

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def file_date(name: str) -> str | None:
    m = DATE_RE.search(name)
    return m.group(1) if m else None


def main() -> int:
    errors: list[str] = []

    exp_dir = os.path.join(ROOT, "experiments")
    for fn in sorted(os.listdir(exp_dir)):
        if not (fn.startswith("exp_") and fn.endswith(".py")):
            continue
        # experiments carry no date in the name; gate by mtime-created content marker:
        # only enforce on files that themselves declare a date >= CUTOFF, or that are
        # new since the charter existed (no ASSUMPTIONS string AND mtime >= CUTOFF).
        path = os.path.join(exp_dir, fn)
        with open(path, encoding="utf-8", errors="replace") as fh:
            head = fh.read(4000)
        import datetime as _dt
        mtime = _dt.date.fromtimestamp(os.path.getmtime(path)).isoformat()
        if mtime >= CUTOFF and "ASSUMPTIONS.md" not in head:
            errors.append(f"R1 {fn}: 冇引用 ASSUMPTIONS.md(憲章唔引 = 唔准跑)")

    res_dir = os.path.join(ROOT, "results")
    for fn in sorted(os.listdir(res_dir)):
        if not fn.endswith(".md"):
            continue
        d = file_date(fn)
        if not d or d < CUTOFF:
            continue
        with open(os.path.join(res_dir, fn), encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        has_neg = any(k in text for k in NEG_KEYWORDS)
        has_ctrl = any(k in text for k in CONTROL_KEYWORDS)
        if has_neg and not has_ctrl:
            errors.append(f"R2 {fn}: 有負面判詞但冇對照臂(單臂殺訊號 = 2026-07-17 六連錯嘅病)")

    if errors:
        print(f"results lint ERRORS: {len(errors)}")
        for e in errors:
            print("  " + e)
        return 1
    print("results lint: 0 errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
