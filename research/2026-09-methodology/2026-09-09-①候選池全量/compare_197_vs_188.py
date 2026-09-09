# -*- coding: utf-8 -*-
"""KARST-197 第四步:舊六十家逐家對比(排位 / 過閘 / 底線 三項變動)。

三個對照點:
  舊 = KARST-188 的 ranking_60.csv(正本,卡片建基於它;取數與折現率兩處缺陷未修)
  中 = KARST-196 的 rerun60(取數 + 折現率都修好,但仍是舊閘、舊底線、無扣起)
  新 = KARST-197 的 ranking_pool_v2.csv(新閘重篩、底線三級、A-055 扣起)

輸出:compare_197_vs_188.csv、2026-09-10-新閘重篩對比舊六十家.md
"""
import os

import numpy as np
import pandas as pd

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"
BL_OLD = 0.15


def pct(x, nd=0):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return ("%+." + str(nd) + "f%%") % (x * 100)


def num(x, nd=2):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return ("%." + str(nd) + "f") % x


def norm3(s: str) -> str:
    s = str(s)
    if s.startswith("入選") or s.startswith("買入候選"):
        return "入選 / 買入候選"
    if s.startswith("觀察"):
        return "觀察"
    if s.startswith("不入"):
        return "不入"
    return s


def main():
    old = pd.read_csv(os.path.join(D, "ranking_60.csv"))
    mid = pd.read_csv(os.path.join(D, "KARST196-rerun60.csv"))
    new = pd.read_csv(os.path.join(D, "ranking_pool_v2.csv"))

    o = old.set_index("ticker")
    m = mid.set_index("ticker")
    n = new.set_index("ticker")

    rows = []
    for t in old["ticker"]:
        r = dict(ticker=t, name=o.loc[t, "name"])
        r["rank_old"] = o.loc[t, "rank"] if pd.notna(o.loc[t, "rank"]) else None
        r["rank_new"] = n.loc[t, "rank"] if (t in n.index and pd.notna(n.loc[t, "rank"])) else None
        r["odds_old"] = o.loc[t, "odds"]
        r["odds_new"] = n.loc[t, "odds"] if t in n.index else None
        # 過閘:舊 = 負債閘(D-169 的硬否決);新 = 兩條新閘
        r["gate_old_debt"] = bool(o.loc[t, "debt_gate"])
        r["gate_new_inpool"] = bool(t in n.index)
        r["debt_label_new"] = n.loc[t, "debt_label"] if t in n.index else None
        r["gate_change"] = ("負債閘不過 → 入池(閘已取消)" if (not r["gate_old_debt"])
                            else "無變動(兩邊都在池內)")
        # 底線
        b_old = str(o.loc[t, "pass_bottom_line"]) in ("True", "true")
        r["bl_old_pass15"] = b_old
        r["ret_old"] = o.loc[t, "n3_ret_1y"]
        r["ret_new"] = n.loc[t, "n3_ret_1y"] if t in n.index else None
        r["bl_new_grade"] = n.loc[t, "ret_1y_grade"] if t in n.index else "已離池"
        newpass = r["bl_new_grade"] == "過線(≥17%)"
        r["bl_change"] = ("無變動" if newpass == b_old else
                          ("由過變不過/貼線" if b_old else "由不過變過線"))
        r["concl_old"] = o.loc[t, "A_conclusion"]
        r["concl_new"] = n.loc[t, "conclusion"] if t in n.index else "已離池"
        # 三態歸一,免得「不入」與「不入(一年回報不過線)」被當成翻轉
        r["concl_old_3"] = norm3(r["concl_old"])
        r["concl_new_3"] = norm3(r["concl_new"])
        r["flip"] = r["concl_old_3"] != r["concl_new_3"]
        r["withheld_new"] = bool(n.loc[t, "baseline_withheld"]) if t in n.index else None
        _am = n.loc[t, "not_in_pool_above_ma"] if t in n.index else ""
        r["above_ma_new"] = "" if (_am is None or pd.isna(_am)) else str(_am)
        r["in_pool_1_new"] = bool(n.loc[t, "in_pool_1"]) if t in n.index else None
        r["deep_new"] = n.loc[t, "survivor_gap_deep"] if t in n.index else ""
        # 變動主因(能機械歸因的才寫)
        why = []
        if r["above_ma_new"]:
            why.append("D-174:觸發時價在 200 日線之上,不入①池")
        if r["withheld_new"]:
            why.append("A-055 資料落後,基準值扣起")
        if pd.notna(r["odds_old"]) and t in m.index and pd.notna(m.loc[t, "new_odds"]):
            if abs(m.loc[t, "new_odds"] - r["odds_old"]) > 0.05 * max(1e-9, abs(r["odds_old"])):
                why.append("KARST-195/196 取數與折現率更正")
        if (not r["gate_old_debt"]):
            why.append("D-173 負債閘取消")
        if r["bl_change"] != "無變動":
            why.append("底線由 15% 二分改三級(17/13)")
        # 舊結論把「折讓格都不過」當硬否決,新六條規則不用折讓格
        if (str(o.loc[t, "discount_grade"]) == "都不過"
                and str(r["concl_old"]).startswith("不入")
                and not str(r["concl_new"]).startswith("不入")):
            why.append("舊結論以折讓格作硬否決,新規則不用折讓格")
        # 新規則六:未填卡 / 預測零支持,結論上限「觀察」
        if str(r["concl_new"]).startswith("觀察") and (
                "未填卡" in str(r["concl_new"]) or "預登記預測零支持" in str(r["concl_new"])):
            why.append("新規則:預登記預測零支持(或未填卡),結論上限「觀察」")
        # 舊「入選」要折讓格兩把尺都過,新規則完全不看折讓格
        if (str(o.loc[t, "discount_grade"]).startswith("只過一把")
                and str(r["concl_old"]).startswith("觀察")
                and str(r["concl_new"]).startswith("買入候選")):
            why.append("舊「入選」要折讓格兩把尺都過,新規則不看折讓格")
        # 舊「入選」要 200 日線形態是「殺」;新規則只剔走「線上回調」那一種
        if (str(o.loc[t, "ma200_form"]) == "線附近"
                and str(r["concl_old"]).startswith("觀察")
                and str(r["concl_new"]).startswith("買入候選")):
            why.append("舊「入選」要 200 日線形態為「殺」,新規則只把「線上回調」剔出①池,"
                       "「線附近」照樣可以升買")
        # 舊版底線只作欄位,新版 <13% 明文判不入
        if (str(r["concl_new"]).startswith("不入(一年回報")
                and not str(r["concl_old"]).startswith("不入")):
            why.append("新規則:一年回報 <13% 明文判不入(舊版底線只作欄位,不作否決)")
        r["why"] = ";".join(why) if why else "—"
        rows.append(r)

    c = pd.DataFrame(rows)
    c["rank_delta"] = [(None if (pd.isna(a) or pd.isna(b)) else int(b - a))
                       for a, b in zip(c["rank_old"], c["rank_new"])]
    c.to_csv(os.path.join(D, "compare_197_vs_188.csv"), index=False, encoding="utf-8-sig")

    n_gate = int((~c["gate_old_debt"]).sum())
    n_bl = int((c["bl_change"] != "無變動").sum())
    n_concl = int(c["flip"].sum())
    n_rank_out = int(c["rank_new"].isna().sum())

    L = []
    L.append("# 舊六十家逐家對比 —— 新閘重篩前後(KARST-197)")
    L.append("")
    n_above = int((c["above_ma_new"] != "").sum())
    L.append("**一句總結**:六十家全部過得到新的兩道閘,一家都沒有被閘剔走;"
             "但其中 %d 家因為 D-174 把「價在 200 日線之上」由否決改為**定義**"
             "(那是②回調入口,不是錯殺),不再屬於①池。"
             "餘下的動的是位置與結論——①池由 60 家變成 103 家,舊六十家要與新對手一起排。"
             % n_above)
    L.append("")
    L.append("## 三個對照點,不要混淆")
    L.append("")
    L.append("| 版本 | 取數 | 折現率 | 閘 | 底線 | 資料落後 |")
    L.append("|---|---|---|---|---|---|")
    L.append("| 舊(KARST-188,卡片建基於它) | 有八處缺陷 | 固定股權成本 | 四道(含市值、負債) | 15% 二分 | 不扣起 |")
    L.append("| 中(KARST-195/196 重跑) | 已修 | 已補槓桿 | 同上 | 15% 二分 | 不扣起 |")
    L.append("| **新(KARST-197,本表)** | 已修 | 已補槓桿 | **兩道(現金流、成交額)** | **三級 17/13** | **扣起(A-055)** |")
    L.append("")
    L.append("## 變動家數")
    L.append("")
    L.append("| 項目 | 家數 | 說明 |")
    L.append("|---|---:|---|")
    L.append("| 被閘剔走 | 0 | 舊六十家全部過得到新的兩道閘 |")
    L.append("| 不再屬於①池(價在 200 日線之上,歸②) | %d | D-174;照列供對照,不落注、不填卡 |"
             % n_above)
    L.append("| 過閘變動 | %d | 修後取數判負債閘不過的那批,現在照樣入池(閘已取消) |" % n_gate)
    L.append("| 底線變動 | %d | 由 15%% 二分改三級(≥17 過 / 13–17 貼線 / <13 不過) |" % n_bl)
    L.append("| 不再排位(賠率扣起或算不出) | %d | 其中 5 家是 A-055 資料落後扣起 |" % n_rank_out)
    L.append("| **結論翻轉(入選 / 觀察 / 不入 三態變格)** | **%d** | 逐家名單見文末 |" % n_concl)
    L.append("")
    L.append("**「結論翻轉」只數三態變格**(入選 / 買入候選、觀察、不入)。"
             "措詞由「不入」變成「不入(一年回報不過線)」那種只是寫法變細,不算翻轉。")
    L.append("")
    L.append("## 逐家對照(按舊排位)")
    L.append("")
    L.append("| 舊排位 | 新排位 | 移動 | 代號 | 舊賠率 | 新賠率 | 過閘變動 | 舊底線(15%) | "
             "新底線(三級) | 舊結論 | 新結論 | 變動主因 |")
    L.append("|---:|---:|---:|---|---:|---:|---|---|---|---|---|---|")
    cc = c.sort_values(["rank_old", "ticker"], na_position="last")
    for _, r in cc.iterrows():
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            "%d" % r["rank_old"] if pd.notna(r["rank_old"]) else "—",
            "%d" % r["rank_new"] if pd.notna(r["rank_new"]) else "—",
            ("%+d" % r["rank_delta"]) if pd.notna(r["rank_delta"]) else "—",
            r["ticker"], num(r["odds_old"]), num(r["odds_new"]),
            r["gate_change"], "過" if r["bl_old_pass15"] else "不過",
            r["bl_new_grade"], str(r["concl_old"]), str(r["concl_new"]), r["why"]))
    L.append("")
    L.append("## 結論翻轉的名單")
    L.append("")
    flip = cc[cc["flip"]]
    L.append("| 代號 | 舊結論 | 新結論 | 為什麼 |")
    L.append("|---|---|---|---|")
    for _, r in flip.iterrows():
        L.append("| %s | %s | %s | %s |" % (r["ticker"], r["concl_old"],
                                            r["concl_new"], r["why"]))
    L.append("")
    with open(os.path.join(D, "2026-09-10-新閘重篩對比舊六十家.md"),
              "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("過閘變動 %d;底線變動 %d;結論翻轉 %d;不再排位 %d"
          % (n_gate, n_bl, n_concl, n_rank_out))
    print(flip[["ticker", "concl_old", "concl_new"]].to_string())


if __name__ == "__main__":
    main()
