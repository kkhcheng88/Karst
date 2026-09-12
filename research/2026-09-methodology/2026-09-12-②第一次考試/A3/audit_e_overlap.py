# -*- coding: utf-8 -*-
"""KARST-230 第三部:十宗試跑事件(A2 包的 accessionNumber)與 A3 主清單 / 後備清單的重疊。
只報數量與 event_id(兩邊);不列公司名或代號。只讀 A2/packets 的 1_事件識別.accessionNumber。
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_common as C

A2 = os.path.join(C.PARENT, "A2", "packets")
PILOT = ["E001", "E009", "E017", "E025", "E033", "E041", "E049", "E057", "E065", "E073"]


def main():
    main_l, back_l = C.load_picks_md()
    a3_main = {r["accessionNumber"]: r["event_id"] for r in main_l}
    a3_back = {r["accessionNumber"]: r["event_id"] for r in back_l}
    pilot = {}
    for eid in PILOT:
        p = os.path.join(A2, "packets", eid + ".json")
        if not os.path.exists(p):
            p = os.path.join(A2, eid + ".json")
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        pilot[eid] = str(d["1_事件識別"]["accessionNumber"])
    ov_main = [(k, pilot[k], a3_main[pilot[k]]) for k in PILOT if pilot[k] in a3_main]
    ov_back = [(k, pilot[k], a3_back[pilot[k]]) for k in PILOT if pilot[k] in a3_back]
    both = set(a3_main) & set(a3_back)
    out = {
        "n_pilot": len(PILOT),
        "pilot_accessions": {k: pilot[k] for k in PILOT},
        "n_a3_main": len(a3_main), "n_a3_back": len(back_l), "n_a3_union": len(set(a3_main) | set(a3_back)),
        "n_overlap_main": len(ov_main), "overlap_main": ov_main,
        "n_overlap_back": len(ov_back), "overlap_back": ov_back,
        "n_overlap_union": len(set(ov_main) | set(ov_back)),
        "n_same_acc_in_both_lists": len(both),
    }
    with open(os.path.join(C.OUT, "part3.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
