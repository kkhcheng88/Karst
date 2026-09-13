# -*- coding: utf-8 -*-
"""KARST-236 第 5–6 步:由「修正前備份 vs 現行包」直接計出逐包改動清單。

來源是 `cache/packets_before_fix235/`(KARST-235 修正前快照)對 `packets/`,
不靠重建腳本的 log(該 log 已被冪等第二次執行覆寫成 0 改動)。
輸出 `audit_out_fixed/fix235_diff.json`(逐包改動)、`audit_out_fixed/fix235_diff.csv`
(只列四欄與 g0/prev/accel 的 before/after)。不列公司名或代號。
用法:`PYTHONUTF8=1 python report_fix235_diff.py`
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "audit_out_fixed"
OUT_DIR.mkdir(exist_ok=True)
BEFORE = HERE / "cache" / "packets_before_fix235"
PKT = HERE / "packets"
COLS = ("revenue", "gross_profit", "operating_income", "ocf")
NINE = ["E017", "E021", "E022", "E024", "E025", "E047", "E057", "E073", "E006"]


def walk(a, b, path=""):
    """深度比對兩份 JSON,回 ["路徑 舊 → 新"]。"""
    out = []
    if type(a) is not type(b):
        return ["%s: %r → %r" % (path or ".", a, b)]
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            p = "%s.%s" % (path, k) if path else k
            if k not in a:
                out.append("%s: (無) → %r" % (p, b[k]))
            elif k not in b:
                out.append("%s: %r → (刪)" % (p, a[k]))
            else:
                out += walk(a[k], b[k], p)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append("%s: 長度 %d → %d" % (path, len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            out += walk(x, y, "%s[%d]" % (path, i))
    elif a != b:
        out.append("%s: %r → %r" % (path or ".", a, b))
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    report, table = {}, []
    for eid in NINE:
        fb = BEFORE / ("%s.json" % eid)
        fc = PKT / ("%s.json" % eid)
        if not fb.exists() or not fc.exists():
            report[eid] = {"missing": True}
            continue
        a = json.load(open(fb, encoding="utf-8"))
        b = json.load(open(fc, encoding="utf-8"))
        diffs = walk(a, b)
        fa = a["4_財務數列"]
        fbc = b["4_財務數列"]
        rowchg = []
        sig = fbc.get("signal_q_end")
        for i, (qa, qb) in enumerate(zip(fa["quarters"], fbc["quarters"])):
            keys = [k for k in sorted(set(qa) | set(qb)) if k != "extra"]
            for k in keys:
                if qa.get(k) != qb.get(k):
                    kind = "訊號季行" if qb["period_end"] == sig else "歷史行"
                    rowchg.append({"row": i, "period_end": qb["period_end"],
                                   "col": k, "before": qa.get(k),
                                   "after": qb.get(k)})
                    table.append({"event_id": eid,
                                  "group": "row" if k in COLS else "row_aux",
                                  "row": i, "period_end": qb["period_end"],
                                  "field": k, "before": qa.get(k),
                                  "after": qb.get(k), "kind": kind})
        for k in ("g0_signal_q_yoy", "g0_xbrl_for_reference", "prev_q_yoy",
                  "accel_pp", "n_rows_first_filed_after_T1"):
            if fa.get(k) != fbc.get(k):
                table.append({"event_id": eid, "group": "metric", "row": "",
                              "period_end": "", "field": k,
                              "before": fa.get(k), "after": fbc.get(k),
                              "kind": ""})
        st = (b["1_事件識別"].get("entry_status"),
              a["1_事件識別"].get("entry_status"))
        report[eid] = {
            "n_diff_lines": len(diffs), "diffs": diffs, "row_changes": rowchg,
            "entry_status_before": a["1_事件識別"].get("entry_status"),
            "entry_status_after": b["1_事件識別"].get("entry_status"),
            "accel_before": fa.get("accel_pp"), "accel_after": fbc.get("accel_pp"),
            "g0_before": fa.get("g0_signal_q_yoy"),
            "g0_after": fbc.get("g0_signal_q_yoy"),
            "prev_before": fa.get("prev_q_yoy"),
            "prev_after": fbc.get("prev_q_yoy"),
            "sig_row_sources": (next((q for q in fbc["quarters"]
                                      if q["period_end"]
                                      == fbc.get("signal_q_end")), {})
                                or {}).get("signal_row_sources"),
        }
    json.dump(report, open(OUT_DIR / "fix235_diff.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    with open(OUT_DIR / "fix235_diff.csv", "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0].keys()))
        w.writeheader()
        for r in table:
            w.writerow(r)
    for eid in NINE:
        r = report.get(eid, {})
        print("%s diff_lines=%s row_changes=%s g0 %s→%s prev %s→%s accel %s→%s st=%s→%s"
              % (eid, r.get("n_diff_lines"), len(r.get("row_changes") or []),
                 r.get("g0_before"), r.get("g0_after"),
                 r.get("prev_before"), r.get("prev_after"),
                 r.get("accel_before"), r.get("accel_after"),
                 r.get("entry_status_before"), r.get("entry_status_after")))


if __name__ == "__main__":
    main()
