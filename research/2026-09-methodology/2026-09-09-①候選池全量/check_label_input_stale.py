"""核對:派給子隊的 label_input.csv 與最終 screen60_full.csv 的隱含增速有沒有走樣。

如果 label_input.csv 是負債更正(A-050)之前產生的,受影響公司的隱含五年增速會偏低,
子隊用第一把尺判出來的標籤就可能錯邊。逐家比對,列出差 3 個百分點以上、
或會令標籤跳格的公司。
"""
import os
import pandas as pd

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"


def lab(g5, cons):
    if pd.isna(g5) or pd.isna(cons):
        return None
    return ("市場比指引更悲觀" if g5 <= cons - 0.03 else
            "市場比指引更樂觀" if g5 >= cons + 0.03 else "與指引重疊")


def main():
    a = pd.read_csv(os.path.join(D, "label_input.csv")).set_index("ticker")
    b = pd.read_csv(os.path.join(D, "screen60_full.csv")).set_index("ticker")
    rows = []
    for t in b.index:
        if t not in a.index:
            rows.append(dict(ticker=t, note="label_input 無此家"))
            continue
        g_old, g_new = a["n1_implied_g5"].get(t), b["n1_implied_g5"].get(t)
        c_old, c_new = a["consensus_rev_growth"].get(t), b["consensus_rev_growth"].get(t)
        l_old, l_new = lab(g_old, c_old), lab(g_new, c_new)
        rows.append(dict(ticker=t, g5_old=g_old, g5_new=g_new,
                         cons_old=c_old, cons_new=c_new,
                         d_pp=(None if (pd.isna(g_old) or pd.isna(g_new))
                               else round((g_new - g_old) * 100, 1)),
                         lab_old=l_old, lab_new=l_new,
                         flips=(l_old is not None and l_new is not None and l_old != l_new)))
    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(D, "label_input_staleness.csv"), index=False, encoding="utf-8")
    moved = d[d["d_pp"].abs() > 3.0] if "d_pp" in d else d
    print("隱含增速差 >3pp 的家數:", len(moved))
    print(moved[["ticker", "g5_old", "g5_new", "d_pp", "lab_old", "lab_new", "flips"]]
          .to_string(index=False))
    print()
    fl = d[d["flips"] == True]
    print("標籤會跳格的家數:", len(fl), list(fl["ticker"]))


if __name__ == "__main__":
    main()
