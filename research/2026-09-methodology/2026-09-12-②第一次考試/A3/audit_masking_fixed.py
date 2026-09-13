# -*- coding: utf-8 -*-
"""KARST-236 第 4 步之遮罩掃描:照 KARST-232 `s17_verify.py` 的 F 項,掃全部 84 包。

判準(逐字沿用 KARST-232):
  1. 整包原始檔文字裡任何 `YYYY-MM-DD` 若 > T1,只准等於 T2 或凍結日 `2026-09-13`;
  2. `masking_check.verified` 必須為真;
  3. `masking_check.latest_data_date` ≤ T1。

只讀;輸出寫去 `audit_out_fixed/masking_fixed.{csv,json}`,**不碰** KARST-232 的
`cache/enrich_verify.json`。不列公司名或代號。
用法:`PYTHONUTF8=1 python audit_masking_fixed.py`
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "audit_out_fixed"
OUT_DIR.mkdir(exist_ok=True)
PKT = HERE / "packets"
ISO_RX = re.compile(r"\b(19|20)\d\d-\d\d-\d\d\b")
FROZEN = "2026-09-13"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    rows, viol = [], []
    for pf in sorted(PKT.glob("*.json")):
        text = pf.read_text(encoding="utf-8")
        d = json.loads(text)
        eid = d["event_id"]
        t1 = str(d["masking_check"]["cutoff"])[:10]
        t2 = str(d["1_事件識別"]["T2_可成交"]).split()[0]
        hits = sorted({m.group(0) for m in ISO_RX.finditer(text)
                       if m.group(0) > t1 and m.group(0) not in {t2, FROZEN}})
        lat = str(d["masking_check"]["latest_data_date"])[:10]
        ver = bool(d["masking_check"]["verified"])
        bad = []
        if hits:
            bad.append("iso:" + ",".join(hits[:5]))
        if not ver:
            bad.append("verified=false")
        if lat > t1:
            bad.append("latest>t1")
        rows.append({"event_id": eid, "t1": t1, "t2": t2,
                     "latest_data_date": lat, "verified": int(ver),
                     "iso_leak_n": len(hits), "iso_leak": ";".join(hits),
                     "violations": len(bad), "detail": ";".join(bad)})
        if bad:
            viol.append({"event_id": eid, "detail": ";".join(bad),
                         "iso_leak": hits[:20]})
    with open(OUT_DIR / "masking_fixed.csv", "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    summ = {"n": len(rows), "frozen": FROZEN,
            "n_violation_packets": len(viol),
            "violation_ids": [v["event_id"] for v in viol],
            "n_iso_leak_total": sum(r["iso_leak_n"] for r in rows),
            "n_latest_gt_t1": sum(1 for r in rows if r["latest_data_date"] > r["t1"]),
            "n_verified_false": sum(1 for r in rows if not r["verified"]),
            "violations": viol}
    json.dump(summ, open(OUT_DIR / "masking_fixed.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(summ, ensure_ascii=False)[:2000])


if __name__ == "__main__":
    main()
