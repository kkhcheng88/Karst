"""KARST-136:由 revise.log 直接重分類今昔對照結果(不等 JSON 落檔)。

理由:Wayback 的 CDX 介面限速嚴重,整輪跑完要數小時;但每處理完一份存檔,
逐格判詞已經寫入日誌。本腳本解析日誌,照 classify_revisions.py 同一套規則
把「精度已毀」由「被改寫」中分離出來。

規則(與 KARST-125 §4.1 五分類對齊):
  unchanged      日誌 summary 行的 unchanged 計數(今昔逐位相同)
  split_rescaled 預估與實際同時按同一倍數搬動——單位變了,不是改寫
  precision_lost 今日值已被進位到兩位小數,量化誤差大到判不出——不計入分母
  rewritten      實際盈利不動(或量化誤差解釋不到),預估卻動了
"""
from __future__ import annotations

import pathlib
import re

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
LOG = HERE / "revise.log"

QUANT = 0.005
PREC_FLOOR = 0.05

RE_TICKER = re.compile(r"^=+ ([A-Z.\-]+) =+$")
RE_SNAP = re.compile(r"^\s+--- snapshot (\d+) ---$")
RE_SUM = re.compile(r"^\s+unchanged (\d+) \| split-rescaled (\d+) \| "
                    r"REWRITTEN (\d+) \| not comparable (\d+)$")
RE_RW = re.compile(r"^\s+(\S+): then=(\S+) now=(\S+) -> REWRITTEN "
                   r"\[actual then=(\S+) now=(\S+)\]$")
RE_SP = re.compile(r"^\s+(\S+): then=(\S+) now=(\S+) -> split-rescaled "
                   r"\(factor est=(\S+) act=(\S+)\)$")


def f(x: str) -> float | None:
    try:
        v = float(x)
        return v if v == v else None
    except Exception:  # noqa: BLE001
        return None


def rel_quant(x: float | None) -> float:
    if x is None or x == 0:
        return 1.0
    return QUANT / abs(x)


def reclass(te, ne, ta, na) -> str:
    if te is None or ne is None:
        return "not_joined"
    if rel_quant(ne) > PREC_FLOOR or (na is not None and rel_quant(na) > PREC_FLOOR):
        return "precision_lost"
    if ta and na and ne and na != 0 and ne != 0:
        r_est, r_act = te / ne, ta / na
        tol = max(0.02, rel_quant(ne) + rel_quant(na)) * max(1.0, abs(r_act))
        if abs(r_est - r_act) < tol:
            return "split_rescaled"
    return "rewritten"


def main() -> None:
    tk = snap = None
    cells, snaps = [], []
    for line in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        m = RE_TICKER.match(line)
        if m:
            tk = m.group(1)
            continue
        m = RE_SNAP.match(line)
        if m:
            snap = m.group(1)
            continue
        m = RE_SUM.match(line)
        if m:
            snaps.append({"symbol": tk, "snapshot": snap,
                          "unchanged": int(m.group(1)),
                          "rescaled_raw": int(m.group(2)),
                          "rewritten_raw": int(m.group(3)),
                          "not_comparable": int(m.group(4))})
            continue
        m = RE_RW.match(line)
        if m:
            te, ne, ta, na = (f(m.group(i)) for i in (2, 3, 4, 5))
            cells.append({"symbol": tk, "snapshot": snap, "quarter": m.group(1),
                          "then_est": te, "now_est": ne, "then_act": ta, "now_act": na,
                          "raw": "REWRITTEN", "verdict": reclass(te, ne, ta, na)})
            continue
        m = RE_SP.match(line)
        if m:
            te, ne = f(m.group(2)), f(m.group(3))
            cells.append({"symbol": tk, "snapshot": snap, "quarter": m.group(1),
                          "then_est": te, "now_est": ne, "then_act": None,
                          "now_act": None, "raw": "split-rescaled",
                          "verdict": "precision_lost" if rel_quant(ne) > PREC_FLOOR
                                     else "split_rescaled"})

    sn = pd.DataFrame(snaps)
    cl = pd.DataFrame(cells)
    cl.to_csv(HERE / "revision_cells.csv", index=False, encoding="utf-8")

    n_unchanged = int(sn["unchanged"].sum()) if len(sn) else 0
    vc = cl["verdict"].value_counts() if len(cl) else pd.Series(dtype=int)
    n_split = int(vc.get("split_rescaled", 0))
    n_prec = int(vc.get("precision_lost", 0))
    n_rw = int(vc.get("rewritten", 0))
    n_nc = int(sn["not_comparable"].sum()) if len(sn) else 0

    judgeable = n_unchanged + n_split + n_rw
    rate = n_rw / judgeable if judgeable else float("nan")

    summ = pd.DataFrame([
        {"verdict": "unchanged", "cells": n_unchanged},
        {"verdict": "split_rescaled", "cells": n_split},
        {"verdict": "precision_lost", "cells": n_prec},
        {"verdict": "not_comparable", "cells": n_nc},
        {"verdict": "rewritten", "cells": n_rw},
    ])
    total = int(summ["cells"].sum())
    summ["share"] = summ["cells"] / total if total else float("nan")
    summ.to_csv(HERE / "revision_summary.csv", index=False, encoding="utf-8")

    print(f"樣本 {sn['symbol'].nunique() if len(sn) else 0} 隻有存檔可判,"
          f"存檔 {len(sn)} 份,逐格對照 {total} 格")
    print(summ.to_string(index=False, float_format="%.3f"))
    print(f"\n判得出結論 {judgeable} 格,真‧被改寫 {n_rw} 格,改寫率 {rate:.1%}")
    if n_rw:
        print("\n真‧被改寫逐格:")
        print(cl[cl["verdict"] == "rewritten"].to_string(index=False))


if __name__ == "__main__":
    main()
