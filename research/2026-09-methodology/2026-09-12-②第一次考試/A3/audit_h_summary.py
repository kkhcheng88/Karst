# -*- coding: utf-8 -*-
"""KARST-230 驗收摘要材料用的純數字:母體漏斗、入池原因分佈、時點三項、解析、考試、成本。
只計數,不寫判詞;不列公司名或代號。輸出 audit_out/summary.json。
"""
import collections, csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_common as C

COST = {"低": 110, "高": 210}   # 執行口徑 v1.2 第四輪外評後重估(美元)


def main():
    out = {}
    # ---- 母體漏斗(建池者執行紀錄 §一 所載)
    out["漏斗"] = {"母體": 124853, "母體公司數": 4047, "宇宙內": 52811,
                 "宇宙內_2014暖身": 1411, "宇宙內_2015後": 51400,
                 "過門檻且同業正_候選層": 5364, "入口池": 1802,
                 "主清單": 84, "後備清單": 44}
    pool = C.load_pool()
    n = len(pool)
    imp = collections.Counter(r["improvement_type"] for r in pool.values())
    out["入口池"] = {"總數": n, "改善類型": dict(imp),
                   "只靠加速": imp.get("加速", 0),
                   "只靠指引": imp.get("指引", 0),
                   "兩者": imp.get("兩者", 0),
                   "無改善": imp.get("無", 0) + imp.get("", 0)}
    yr = collections.Counter(r["year"] for r in pool.values())
    out["入口池"]["年份"] = {k: v for k, v in sorted(yr.items())}
    bk = collections.Counter(r["bucket"] for r in pool.values())
    out["入口池"]["行業桶"] = dict(bk)
    # 未檢欄位殘留
    out["訊號季收入標記"] = dict(collections.Counter(r["signal_rev_in_text"] for r in pool.values()))
    out["指引收入上調"] = sum(1 for r in pool.values() if C.b(r["guide_rev_raise"]))
    out["指引純盈利上調標籤"] = sum(1 for r in pool.values() if C.b(r["guidance_raise_eps_only"]))

    main_, back = C.load_picks_md()
    out["主清單"] = {"總數": len(main_), "改善類型": dict(collections.Counter(r["improvement_type"] for r in main_)),
                   "年份": {k: v for k, v in sorted(collections.Counter(r["year"] for r in main_).items())},
                   "行業桶": dict(collections.Counter(r["bucket"] for r in main_)),
                   "公開時段": dict(collections.Counter(r["release_timing"] for r in main_))}
    out["後備清單"] = {"總數": len(back), "改善類型": dict(collections.Counter(r["improvement_type"] for r in back)),
                    "年份": {k: v for k, v in sorted(collections.Counter(r["year"] for r in back).items())},
                    "行業桶": dict(collections.Counter(r["bucket"] for r in back))}
    out["成本_美元"] = COST

    # ---- 時點三項(本次核查實測)
    with open(os.path.join(C.OUT, "part1.json"), encoding="utf-8") as f:
        p1 = json.load(f)
    out["時點"] = {
        "反應日與公開時段_合": sum(1 for r in p1 if r["a"]["timing_match"] and r["a"]["reaction_match"]),
        "反應日與公開時段_共": len(p1),
        "前一日絕對報酬_差最大值": max((r["a"]["prior_day_abs_delta"] or 0) for r in p1),
        "窗口門檻_p90_差最大值": max((r["b"]["p90_delta"] or 0) for r in p1),
        "窗口門檻_窗內最晚事件早於本宗": sum(1 for r in p1 if r["b"]["latest_before_own"]),
        "訊號季收入_稿內有命中": sum(1 for r in p1 if r["c"]["n_line_hits"] > 0),
        "訊號季收入_共": len(p1),
    }
    with open(os.path.join(C.OUT, "part2.json"), encoding="utf-8") as f:
        p2 = json.load(f)
    out["時點"]["masking_過"] = p2["n_packets"] - p2["by_item"].get("P6", {}).get("n", 0)
    out["時點"]["masking_共"] = p2["n_packets"]

    # ---- 考試(包)統計
    with open(os.path.join(C.OUT, "part3.json"), encoding="utf-8") as f:
        p3 = json.load(f)
    out["重疊"] = {"試跑宗數": p3["n_pilot"], "主清單重疊": p3["n_overlap_main"],
                 "後備清單重疊": p3["n_overlap_back"], "合計重疊": p3["n_overlap_union"],
                 "主清單內與後備重複": p3["n_same_acc_in_both_lists"]}
    with open(os.path.join(C.OUT, "part2.json"), encoding="utf-8") as f:
        pass
    out["包"] = {"總數": p2["n_packets"], "六項全過": p2["n_pass"],
               "至少一項未過": p2["n_fail"],
               "逐項全過": {k: (p2["n_packets"] - v["n"]) for k, v in
                        dict([("P1", {"n": 0}), ("P2", {"n": 0}), ("P6", {"n": 0}),
                              *p2["by_item"].items()]).items()
                        if isinstance(v, dict) and k in ("P1", "P2", "P3", "P4", "P5", "P6")},
               "P4細分": {k: v["n"] for k, v in p2["sub"].items()}}
    with open(os.path.join(C.OUT, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
