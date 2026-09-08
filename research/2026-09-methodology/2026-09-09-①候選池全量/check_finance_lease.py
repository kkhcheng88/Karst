"""KARST-188 第六處取數缺陷的全批查證:融資租賃有沒有被漏掉。

由 LMB/LINC 卡片隊查出:共用工具的租賃標籤只涵蓋經營租賃
(OperatingLeaseLiabilityCurrent / Noncurrent),債務標籤亦不含融資租賃,
於是 FinanceLeaseLiability* 整筆消失。LINC 一家漏 3,090 萬美元。

本腳本逐家由 companyfacts 取融資租賃負債(取用與主線同一個結算日),
算出漏掉的金額、佔淨負債的比例,以及加回之後負債閘會不會翻轉。

輸出:finance_lease_gap.csv
"""
import os
import sys
import pandas as pd

sys.path.insert(0, r"C:\projects\Karst")
from strategy.tools import implied_expectations as IE  # noqa: E402

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"

FL_CUR = ["FinanceLeaseLiabilityCurrent",
          "CapitalLeaseObligationsCurrent"]
FL_NC = ["FinanceLeaseLiabilityNoncurrent",
         "CapitalLeaseObligationsNoncurrent"]
FL_TOT = ["FinanceLeaseLiability", "CapitalLeaseObligations"]


def pick(facts, tags, asof):
    """取結算日等於 asof 的那一筆;同日多筆取最近申報的一筆。"""
    us = facts.get("facts", {}).get("us-gaap", {})
    best, src = 0.0, None
    for t in tags:
        node = us.get(t)
        if not node:
            continue
        rows = []
        for unit, arr in node.get("units", {}).items():
            if not unit.startswith("USD"):
                continue
            for it in arr:
                if it.get("end") == asof and it.get("val") is not None:
                    rows.append((it.get("filed", ""), float(it["val"])))
        if rows:
            rows.sort()
            if abs(rows[-1][1]) > abs(best):
                best, src = rows[-1][1], t
    return best, src


def main():
    f = pd.read_csv(os.path.join(D, "screen60_full.csv")).set_index("ticker")
    out = []
    for t, r in f.iterrows():
        asof = str(r.get("asof"))
        if asof in ("nan", ""):
            out.append(dict(ticker=t, note="無結算日"))
            continue
        try:
            facts = IE.load_facts(IE.cik_for(t))
        except Exception as e:
            out.append(dict(ticker=t, note="load_facts 失敗:%s" % e))
            continue
        cur, s1 = pick(facts, FL_CUR, asof)
        nc, s2 = pick(facts, FL_NC, asof)
        tot, s3 = pick(facts, FL_TOT, asof)
        # 合計標籤若大於分項之和,用合計(同一筆錢的兩種寫法,取較完整那個)
        fl = tot if tot > cur + nc else cur + nc
        srcs = "; ".join([x for x in (s1, s2, s3) if x])
        nd = r.get("net_debt")
        ocf = r.get("ocf_ttm")
        nd2 = (nd + fl) if pd.notna(nd) else None
        gate_now = bool(r.get("debt_gate"))

        def gate(x):
            if x is None:
                return None
            if x < 0:
                return True                     # 淨現金
            if ocf and ocf > 0:
                return (x / ocf) <= 3.0
            return False
        gate_new = gate(nd2)
        out.append(dict(
            ticker=t, asof=asof, fl_musd=round(fl / 1e6, 1),
            fl_tags=srcs,
            net_debt_musd=round(nd / 1e6, 1) if pd.notna(nd) else None,
            net_debt_fixed_musd=round(nd2 / 1e6, 1) if nd2 is not None else None,
            share_of_net_debt=(round(fl / abs(nd), 3)
                               if pd.notna(nd) and nd != 0 else None),
            gate_now=gate_now, gate_after=gate_new,
            gate_flips=(gate_new is not None and gate_new != gate_now)))
    o = pd.DataFrame(out).set_index("ticker")
    o.to_csv(os.path.join(D, "finance_lease_gap.csv"), encoding="utf-8-sig")
    hit = o[o["fl_musd"].fillna(0) > 0]
    print("有融資租賃而被漏掉的家數:%d / %d" % (len(hit), len(o)))
    print()
    print(hit.sort_values("fl_musd", ascending=False)
          [["fl_musd", "net_debt_musd", "net_debt_fixed_musd",
            "gate_now", "gate_after", "gate_flips"]].head(20).to_string())
    print()
    flip = o[o["gate_flips"].fillna(False)]
    print("加回融資租賃之後負債閘會翻轉的:%d 家 %s" % (len(flip), list(flip.index)))
    t12 = ["CRDO", "STRL", "COLL", "CLS", "LULU", "CRUS",
           "CRNC", "INOD", "FN", "AGX", "RMBS", "LMB"]
    print()
    print("正本十二家:")
    print(o.loc[[x for x in t12 if x in o.index],
                ["fl_musd", "net_debt_musd", "net_debt_fixed_musd",
                 "gate_flips"]].to_string())
    print()
    print("已寫 finance_lease_gap.csv")


if __name__ == "__main__":
    main()
