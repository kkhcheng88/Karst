# -*- coding: utf-8 -*-
"""KARST-210 角色丙「評分隊」:把甲的四級與步六判詞、乙的證偽評估,對照 199 的十二個月超額。

**角色丙是唯一讀 199 `out/` 的角色。** 甲、乙的所有產物(卡-E06.md、卡-E07.md、熊方.md、
step6_numbers.csv)在本腳本執行前已落檔,本腳本只讀它們的**結論欄**,不回頭改。

輸入:
- 甲:`step6_numbers.csv`(步六判詞與各情境價值)、卡檔內的四級(下表照抄,附出處)
- 乙:`熊方.md` 對證偽條件鑑別力的評價
- 答案:199 `out/basket_members.csv` 的 T/N 3/6/12 個月超額

輸出:評分表.csv + 主控台摘要
用法:PYTHONUTF8=1 python score.py
"""
import csv
import os

BASE199 = ("C:/projects/Karst/research/2026-09-methodology/"
           "2026-09-10-①行業殺錯事件籃子/out/basket_members.csv")
HERE = os.path.dirname(os.path.abspath(__file__))

# 甲的四級判級(照卡檔,每格附卡內出處節)
GRADE = {
    "NVDA": ("有限損害", "卡-E07.md 步五"), "MU": ("重大損害", "卡-E07.md 步五"),
    "VRT": ("有限損害", "卡-E07.md 步五"), "ANET": ("重大損害", "卡-E07.md 步五"),
    "ORCL": ("有限損害", "卡-E07.md 步五"),
    "MDLZ": ("有限損害", "卡-E06.md 步五"), "KO": ("影響輕微或受益", "卡-E06.md 步五"),
    "RMD": ("有限損害", "卡-E06.md 步五"), "DXCM": ("重大損害", "卡-E06.md 步五"),
    "DVA": ("重大損害", "卡-E06.md 步五"),
}
# 乙對「必要前提(步七第 1 條)事後有沒有被推翻」的評價。
# **全部為判斷,且建基於模型對界線後事實的既有知識(D-168 污染),不是讀界線後文件。**
PREMISE = {
    "NVDA": "未推翻", "MU": "未推翻", "VRT": "未推翻", "ANET": "未推翻", "ORCL": "未推翻",
    "MDLZ": "推翻", "KO": "未推翻", "RMD": "未推翻", "DXCM": "推翻", "DVA": "未推翻",
}
PREMISE_NOTE = {
    "NVDA": "資料中心收入增速全年遠高於 +30% 門檻",
    "MU": "DRAM 收入增速未轉負,HBM 週期延續",
    "VRT": "積壓訂單全年續增",
    "ANET": "兩家雲商合計佔比未跌穿 20%",
    "ORCL": "基建雲增速未轉負,反而加速",
    "MDLZ": "有機銷量轉負,門檻觸發",
    "KO": "全球銷量大致持平,未轉負(邊際)",
    "RMD": "面罩與耗材收入續增",
    "DXCM": "美國收入增速大幅放緩,門檻觸發",
    "DVA": "美國洗腎治療總數未下降",
}
# 204 v1 的敘事適用度(卡-E06.md / 卡-E07.md 步五原文)
V1 = {"NVDA": "部分適用", "MU": "部分適用", "VRT": "資料不足", "ANET": "部分適用",
      "ORCL": "資料不足", "MDLZ": "部分適用", "KO": "部分適用", "RMD": "部分適用",
      "DXCM": "高度適用", "DVA": "部分適用"}
EV = {"NVDA": "E07", "MU": "E07", "VRT": "E07", "ANET": "E07", "ORCL": "E07",
      "MDLZ": "E06", "KO": "E06", "RMD": "E06", "DXCM": "E06", "DVA": "E06"}
ORDER = {"重大損害": 4, "有限損害": 3, "影響輕微或受益": 2, "關鍵資料不足": 1}


def spearman(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    def ranks(v):
        s = sorted(range(n), key=lambda i: v[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[s[j + 1]] == v[s[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[s[k]] = avg
            i = j + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = sum((a - mx) ** 2 for a in rx) ** 0.5
    dy = sum((b - my) ** 2 for b in ry) ** 0.5
    return num / (dx * dy) if dx and dy else None


def main():
    ans = {}
    for r in csv.DictReader(open(BASE199, encoding="utf-8-sig")):
        ans[(r["event_id"], r["ticker"])] = r
    six = {r["ticker"]: r for r in csv.DictReader(
        open(f"{HERE}/step6_numbers.csv", encoding="utf-8"))}

    rows = []
    for tk in GRADE:
        a = ans[(EV[tk], tk)]
        s = six[tk]
        rows.append(dict(
            event=EV[tk], ticker=tk, grade=GRADE[tk][0], grade_level=ORDER[GRADE[tk][0]],
            v1=V1[tk], verdict=s["verdict"], px_vs_lo=float(s["px_vs_lo"]),
            T3=float(a["T_3m_excess"]), T6=float(a["T_6m_excess"]), T12=float(a["T_12m_excess"]),
            N3=float(a["N_3m_excess"]), N6=float(a["N_6m_excess"]), N12=float(a["N_12m_excess"]),
            premise=PREMISE[tk], premise_note=PREMISE_NOTE[tk]))

    out = f"{HERE}/評分表.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    def pct(x):
        return "%.1f%%" % (100 * x)

    for ev in ("E07", "E06"):
        rs = [r for r in rows if r["event"] == ev]
        print("\n================ %s ================" % ev)
        print("%-5s %-14s %-22s %8s %8s %8s" % ("代號", "四級", "步六判詞", "T12", "N12", "現價對下限"))
        for r in sorted(rs, key=lambda r: -r["grade_level"]):
            print("%-5s %-14s %-22s %8s %8s %8s" % (
                r["ticker"], r["grade"], r["verdict"], pct(r["T12"]), pct(r["N12"]),
                pct(r["px_vs_lo"])))
        print("--- 表一:四級 × 十二個月超額(組平均)")
        for g in sorted({r["grade"] for r in rs}, key=lambda g: -ORDER[g]):
            sub = [r for r in rs if r["grade"] == g]
            print("  %-14s n=%d  T12 平均 %8s  N12 平均 %8s" % (
                g, len(sub), pct(sum(x["T12"] for x in sub) / len(sub)),
                pct(sum(x["N12"] for x in sub) / len(sub))))
        rho = spearman([r["grade_level"] for r in rs], [r["T12"] for r in rs])
        rho_n = spearman([r["grade_level"] for r in rs], [r["N12"] for r in rs])
        print("  秩相關(四級 vs T12) = %s ;vs N12 = %s" % (
            "%.2f" % rho if rho is not None else "n/a",
            "%.2f" % rho_n if rho_n is not None else "n/a"))
        print("--- 表二:步六判詞 × 一年後回報")
        for v in sorted({r["verdict"] for r in rs}):
            sub = [r for r in rs if r["verdict"] == v]
            print("  %-22s n=%d  T12 平均 %8s  N12 平均 %8s" % (
                v, len(sub), pct(sum(x["T12"] for x in sub) / len(sub)),
                pct(sum(x["N12"] for x in sub) / len(sub))))
        rho2 = spearman([r["px_vs_lo"] for r in rs], [r["T12"] for r in rs])
        print("  現價對下限溢價 vs T12 秩相關 = %s(n=%d,越小=越便宜)" % (
            "%.2f" % rho2 if rho2 is not None else "n/a", len(rs)))
        print("--- 表三:必要前提(步七第 1 條)事後有沒有被推翻")
        for p in ("未推翻", "推翻"):
            sub = [r for r in rs if r["premise"] == p]
            if not sub:
                continue
            print("  %-6s n=%d  T12 平均 %8s  N12 平均 %8s  [%s]" % (
                p, len(sub), pct(sum(x["T12"] for x in sub) / len(sub)),
                pct(sum(x["N12"] for x in sub) / len(sub)),
                "、".join(x["ticker"] for x in sub)))

    allrows = rows
    print("\n================ 兩宗合計 ================")
    print("--- 表一(合計):四級 × 十二個月超額")
    for g in sorted({r["grade"] for r in allrows}, key=lambda g: -ORDER[g]):
        sub = [r for r in allrows if r["grade"] == g]
        print("  %-14s n=%d  T12 平均 %8s  N12 平均 %8s" % (
            g, len(sub), pct(sum(x["T12"] for x in sub) / len(sub)),
            pct(sum(x["N12"] for x in sub) / len(sub))))
    rho = spearman([r["grade_level"] for r in allrows], [r["T12"] for r in allrows])
    print("  秩相關(四級 vs T12) = %.2f (n=%d)" % (rho, len(allrows)))
    print("--- 表二(合計):步六判詞")
    for v in sorted({r["verdict"] for r in allrows}):
        sub = [r for r in allrows if r["verdict"] == v]
        print("  %-22s n=%d  T12 平均 %8s  N12 平均 %8s" % (
            v, len(sub), pct(sum(x["T12"] for x in sub) / len(sub)),
            pct(sum(x["N12"] for x in sub) / len(sub))))
    print("--- 表三(合計):必要前提")
    for p in ("未推翻", "推翻"):
        sub = [r for r in allrows if r["premise"] == p]
        print("  %-6s n=%d  T12 平均 %8s  N12 平均 %8s" % (
            p, len(sub), pct(sum(x["T12"] for x in sub) / len(sub)),
            pct(sum(x["N12"] for x in sub) / len(sub))))
    print("--- 表四:v1 敘事適用度 vs v2.1 損害四級(逐家)")
    print("%-5s %-12s %-14s %8s %8s" % ("代號", "v1 適用度", "v2.1 四級", "T12", "N12"))
    for r in allrows:
        print("%-5s %-12s %-14s %8s %8s" % (
            r["ticker"], r["v1"], r["grade"], pct(r["T12"]), pct(r["N12"])))
    m = [("高度適用", 4), ("部分適用", 3), ("大致不適用", 2), ("資料不足", 1)]
    lv = {k: v for k, v in m}
    rho1 = spearman([lv[r["v1"]] for r in allrows], [r["T12"] for r in allrows])
    rho2 = spearman([r["grade_level"] for r in allrows], [r["T12"] for r in allrows])
    print("  秩相關(v1 適用度 vs T12) = %.2f ;(v2.1 四級 vs T12) = %.2f" % (rho1, rho2))
    print("  註:v1 高度適用 = 敘事真 = 不買,故**負**相關才是判對方向;"
          "v2.1 損害四級重 = 生意真受損 = 不該是①好注,同樣**負**相關才是判對方向。")
    print("wrote " + out)


if __name__ == "__main__":
    main()
