"""KARST-188:把五批子隊的錯價來源標籤併入六十家表,並機械核對「標籤有沒有跟規則」。

核對辦法:對每一家重推一次決策次序(第一把尺:隱含五年增速對共識增速,差 3 個百分點;
第二把尺:分析員目標價溢價 25% / 0%),與子隊寫的標籤比對。不一致的逐家列出,由主線
人手看子隊的理由再判——**不自動改子隊的答案**。
"""
import os, re, json
import pandas as pd

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"

CANON = {"市場比指引更悲觀": "市場比指引更悲觀",
         "市場比指引更樂觀": "市場比指引更樂觀",
         "與指引重疊": "與指引重疊",
         "資料不足": "資料不足"}


def canon(s):
    for k in CANON:
        if s.startswith(k):
            return k
    return "無法解析:" + s


def parse_batches():
    out = {}
    for i in range(1, 6):
        p = os.path.join(D, "labels_batch%d.md" % i)
        with open(p, encoding="utf-8") as fh:
            lines = fh.readlines()
        # 只讀檔末匯總表
        for ln in lines:
            m = re.match(r"^\|\s*([A-Z]{1,5})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
                         ln.strip())
            if m:
                tk = m.group(1)
                out[tk] = dict(label_raw=m.group(2).strip(), ruler=m.group(3).strip(),
                               guidance=m.group(4).strip(), batch=i)
    return out


def main():
    f = pd.read_csv(os.path.join(D, "screen60_full.csv"))
    tg = pd.read_csv(os.path.join(D, "analyst_targets.csv")).set_index("ticker")
    lab = parse_batches()
    print("子隊標籤家數:", len(lab))

    rows = []
    for _, r in f.iterrows():
        t = r["ticker"]
        L = lab.get(t)
        g5, cons = r["n1_implied_g5"], r["consensus_rev_growth"]
        prem = tg["up"].get(t)
        # 重推
        if pd.notna(g5) and pd.notna(cons):
            ruler = "第一把尺"
            rec = ("市場比指引更悲觀" if g5 <= cons - 0.03 else
                   "市場比指引更樂觀" if g5 >= cons + 0.03 else "與指引重疊")
        elif prem is not None and pd.notna(prem):
            ruler = "第二把尺"
            rec = ("市場比指引更悲觀" if prem >= 0.25 else
                   "與指引重疊" if prem > 0 else "市場比指引更樂觀")
        else:
            ruler, rec = "無", "資料不足"
        got = canon(L["label_raw"]) if L else "(子隊無)"
        rows.append(dict(ticker=t, label_team=got, label_recheck=rec,
                         ruler_team=(L["ruler"] if L else ""), ruler_recheck=ruler,
                         agree=(got == rec), guidance=(L["guidance"] if L else ""),
                         label_raw=(L["label_raw"] if L else ""),
                         implied_g5=g5, consensus=cons, target_premium=prem,
                         gap_pp=(None if (pd.isna(g5) or pd.isna(cons)) else round((g5 - cons) * 100, 1))))
    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(D, "labels_merged.csv"), index=False, encoding="utf-8")
    print(d["label_team"].value_counts().to_string())
    print()
    print("與重推不一致的家數:", int((~d["agree"]).sum()))
    print(d[~d["agree"]][["ticker", "label_team", "label_recheck", "ruler_team",
                         "ruler_recheck", "implied_g5", "consensus", "target_premium",
                         "gap_pp"]].to_string(index=False))


if __name__ == "__main__":
    main()
