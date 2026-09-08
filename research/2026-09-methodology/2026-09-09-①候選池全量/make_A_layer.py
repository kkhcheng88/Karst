"""KARST-188 交付:A 層——六十家不含模型的鎖定判斷(每家一行)。

體例沿用 2026-09-08 的 A-不含模型鎖定判斷(五家一次過).md:先寫規則,後看數字。
"""
import os
import numpy as np
import pandas as pd

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"


def pct(x, nd=1):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return ("%+." + str(nd) + "f%%") % (x * 100)


def num(x, nd=2):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return ("%." + str(nd) + "f") % x


def musd(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return format(x / 1e6, ",.0f")


def main():
    f = pd.read_csv(os.path.join(D, "ranking_60.csv"))
    ext = pd.read_csv(os.path.join(D, "screen60_full.csv")).set_index("ticker")
    for c in ("px_vs_ma200", "ma200_slope_40d", "rel_spy_win", "mdd_1y"):
        f[c] = [ext[c].get(t) for t in f["ticker"]]
    L = []
    L.append("# A 層:不含模型的鎖定判斷(六十家一次過)")
    L.append("")
    L.append("- 票:KARST-188;依 D-169 第 7 條四層對照的第一、二層")
    L.append("- **鎖定時間:2026-09-09,寫於任何質性研究之前**")
    L.append("- **資料截止日:2026-09-09;價格為 2026-09-08 美股收市。** 之後公開的資料一律不得用於本檔。")
    L.append("- 這一份只用得着兩樣東西:**申報帳目**與**價格**。沒有讀年報、沒有讀新聞、"
             "沒有讀電話會、沒有任何行業判斷。")
    L.append("- 用途:之後 B 層(加模型)寫完,兩份對照,量「模型加了什麼」。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 一、判斷規則(先寫規則,後看數字)")
    L.append("")
    L.append("**入池條件(上一輪已做):** 2026-06-01 至 2026-09-04,相對 SPY 回報 ≤ −25%,"
             "且過第一版篩四道閘。本票接手的是這六十家。")
    L.append("")
    L.append("**這一層再加四項:**")
    L.append("")
    L.append("| 代號 | 條件 | 資料來源 |")
    L.append("|---|---|---|")
    L.append("| (a) 負債閘 | 淨現金,或淨負債 ÷ 近四季營運現金流 ≤ 3 倍 | SEC XBRL companyfacts |")
    L.append("| (b) 折讓格(兩把尺) | 現時市銷率 **同時** ≤ 四年中位數 × 0.8 **與** ≤ 一年中位數 × 0.8。"
             "只過一把 = 重估已完成,不是折讓 | yfinance 日線 × SEC 收入 |")
    L.append("| (c) 200 日線形態 | 三格:價 > 200 日線 = **回調**(否決);價 < 200 日線且 40 日斜率 ≤ 0 = **殺**(通過);"
             "價 < 200 日線但斜率 > 0 = **線附近**(不通過亦不否決) | yfinance 日線 |")
    L.append("| (d) 跌幅歸因 | 同業(同四位 SIC,不足 5 家改用兩位 SIC)相對 SPY 中位數 ≤ −15% = **行業殺**;"
             "≥ −5% = **個別殺**;之間 = **混合** | KARST-184 第一步原始表 |")
    L.append("")
    L.append("**結論三格:**")
    L.append("- **入選** —— (a) 過、(b) 兩把尺都過、(c) 判為「殺」")
    L.append("- **觀察** —— (a) 過,(b)(c) 至少一項未達「入選」,而 (c) 不是「回調」、(b) 不是「都不過」")
    L.append("- **不入** —— (a) 未過,或 (c) 判為「回調」,或 (b) 兩把尺都不過")
    L.append("")
    L.append("規則在看數字之前定好,六十家同一套,不逐家調。")
    L.append("")
    L.append("**與 2026-09-08 五家版的兩處分別(都是那一輪流程檢討自己提出的):**")
    L.append("1. 折讓格由「一把尺」(四年中位數)改為「兩把尺」(四年 + 一年中位數同時要過)。"
             "五家版的 LULU 用四年分佈算出 4.5 倍折讓,加模型之後被推翻,改用一年分佈只剩 1.7 倍——"
             "兩把尺就是把這個推翻寫成規則。")
    L.append("2. 負債閘由「第一版篩內的一項」提升為**獨立否決項**:不過就不入,無論其他格幾好。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 二、六十家的裁決(截至 2026-09-08 收市)")
    L.append("")
    L.append("| 代號 | 公司 | 現價 | 相對 SPY(窗口) | 淨負債(百萬) | 營運現金流(百萬) | (a) 負債閘 "
             "| 市銷率 現時 / 四年中位 / 一年中位 | (b) 折讓格 | 價 vs 200日線 | 40日斜率 | (c) 形態 "
             "| (d) 歸因 | **鎖定結論** |")
    L.append("|" + "---|" * 14)
    order = {"入選": 0, "觀察": 1, "不入": 2}
    f2 = f.copy()
    f2["o"] = f2["A_conclusion"].map(order)
    f2 = f2.sort_values(["o", "ticker"])
    for _, r in f2.iterrows():
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s / %s / %s | %s | %s | %s | %s | %s | **%s** |" % (
            r["ticker"], str(r["name"])[:24], num(r["price"]),
            pct(r["rel_spy_win"]),
            musd(r["net_debt"]), musd(r["ocf_ttm"]),
            "過" if r["debt_gate"] else "**不過**",
            num(r["ps_now"]), num(r["ps_p50_4y"]), num(r["ps_p50_1y"]),
            r["discount_grade"],
            pct(r["px_vs_ma200"]),
            pct(r["ma200_slope_40d"]), r["ma200_form"],
            r["kill_type"] if isinstance(r["kill_type"], str) else "—",
            r["A_conclusion"]))
    L.append("")
    vc = f["A_conclusion"].value_counts()
    L.append("**結論分佈:** " + "、".join("%s %d 家" % (k, v) for k, v in vc.items()) + "。")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## 三、鎖定當時明寫的四句話")
    L.append("")
    n_debt = int((~f["debt_gate"]).sum())
    n_pull = int((f["ma200_form"] == "回調").sum())
    n_both = int((f["discount_grade"] == "兩把尺都過").sum())
    n_one = int((f["discount_grade"].astype(str).str.startswith("只過一把")).sum())
    L.append("1. **七家在負債閘就出局(%s)。** 這七家全部在上一輪初篩已經過閘——"
             "分別在於上一輪用的抽取程式漏讀了信貸額度、可轉債、有抵押債等一批債務科目"
             "(見假設冊 A-053)。**即是說,上一輪的候選池本身有 11.7%% 是不應該在裡面的。**"
             % "、".join(f[~f["debt_gate"]]["ticker"]))
    L.append("2. **折讓格是這一層最嚴的一關:六十家之中只有 %d 家兩把尺都過,%d 家只過一把。**"
             "只過一把的意思是——它相對四年前便宜,但相對過去一年不便宜,即市場的重估已經完成,"
             "現價不是折讓,是新的常態價。" % (n_both, n_one))
    L.append("3. **只有 %d 家判為「回調」。** 這一批是相對大市跌逾兩成半才入池的,"
             "價格仍高於 200 日線的本來就少;上一輪五家版之中 ARM 就是這一格,這一輪它仍然是。"
             % n_pull)
    kv = f["kill_type"].value_counts()
    L.append("4. **跌幅歸因分佈:%s。** 這一格在這一層只是描述,不參與裁決——"
             "但 A-051 已經量出「行業一齊被殺」那一格是唯一量得出優勢的分格,"
             "所以它會在 B 層被讀第二次。" % "、".join("%s %d 家" % (k, v) for k, v in kv.items()))
    L.append("")
    L.append("## 四、這一層看不見什麼(留給 B 層去答)")
    L.append("")
    L.append("- 為什麼跌——完全不知道。")
    L.append("- 護城河是否受損、故事是否已破——完全不知道。")
    L.append("- 下一項能改變估值的證據是什麼、幾時出——完全不知道。")
    L.append("- 現價隱含公司要壞到什麼程度——這一層只有市銷率比值,答不出;三個數在排序表那一份。")
    L.append("- **市銷率分位本身是否有效**——生意性質變過的公司(上一輪的 LULU),"
             "歷史分佈不是有效的退出倍數。這一層分不出,兩把尺只是把最明顯的一類擋住。")
    L.append("")

    with open(os.path.join(D, "A-不含模型鎖定判斷(六十家一次過).md"), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")
    print("已寫 A 層")
    print(vc.to_string())
    print("負債閘不過:", list(f[~f["debt_gate"]]["ticker"]))
    print("折讓格分佈:")
    print(f["discount_grade"].value_counts().to_string())
    print("形態分佈:")
    print(f["ma200_form"].value_counts().to_string())
    print("歸因分佈:")
    print(f["kill_type"].value_counts().to_string())


if __name__ == "__main__":
    main()
