# -*- coding: utf-8 -*-
"""抽驗:三個換入槽、同業查不到寫法、缺文件的槽位。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
OUT = HERE / "packets"


def main() -> None:
    picks = json.loads((CACHE / "picks_final.json").read_text(encoding="utf-8"))
    final = {f["slot"]: f for f in picks["final"]}
    for slot in ("E056", "E067", "E070"):
        d = json.loads((OUT / ("%s.json" % slot)).read_text(encoding="utf-8"))
        f = final[slot]
        peer = d["5_同業與行業"]
        p2 = peer["peer_annual_reports_2_largest"]
        if isinstance(p2, list):
            psum = [(x.get("accn"), type(x.get("capex_excerpt")).__name__,
                     (len(x.get("capex_excerpt")) if isinstance(x.get("capex_excerpt"), list)
                      else x.get("capex_excerpt"))) for x in p2]
        else:
            psum = p2
        ex = d["4_財務數列"]["quarters"][-1]["extra"]
        print(slot, "slot_id", d["1_事件識別"]["slot_id"], "event_id", d["event_id"],
              "acc", d["1_事件識別"]["accessionNumber"], "swap", f["swapped"],
              "src", f.get("src"))
        print("   peer_rule_applied", peer["peer_rule_applied"], "n_listed", peer["n_listed_peers"],
              "p2", psum)
        print("   extra keys", len(ex), list(ex)[:3],
              "| sample", json.dumps(ex.get("capex"), ensure_ascii=False)[:160])
        print("   prior", json.dumps(d["2_觸發資料"]["prior_release_guidance"], ensure_ascii=False)[:200])
        print("   prelim", d["2_觸發資料"]["preliminary_release"],
              "| mask", json.dumps(d["masking_check"]["iso_date_scan"], ensure_ascii=False)[:120])
        print("   docs", {k: (v.get("n_lines") if isinstance(v, dict) else v)
                          for k, v in d["3_截止前文件"].items()})

    # 同業查不到的寫法
    shown = 0
    for slot, f in sorted(final.items()):
        d = json.loads((OUT / ("%s.json" % slot)).read_text(encoding="utf-8"))
        p2 = d["5_同業與行業"]["peer_annual_reports_2_largest"]
        if isinstance(p2, list):
            for x in p2:
                ex = x.get("capex_excerpt")
                if not (isinstance(ex, list) and ex) and shown < 6:
                    print("CAPEX-MISS", slot, json.dumps(x, ensure_ascii=False)[:220])
                    shown += 1
    # 缺文件的槽
    for slot, f in sorted(final.items()):
        d = json.loads((OUT / ("%s.json" % slot)).read_text(encoding="utf-8"))
        for lab, v in d["3_截止前文件"].items():
            if not isinstance(v, dict):
                print("DOC-NOTDICT", slot, lab, v)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
