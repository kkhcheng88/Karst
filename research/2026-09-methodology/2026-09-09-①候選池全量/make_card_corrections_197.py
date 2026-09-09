# -*- coding: utf-8 -*-
"""KARST-197:十四張卡的更正數據表(卡片改動的唯一數據來源)。

輸出 KARST197-卡片更正數據.md —— 逐家列出「舊 / 中 / 新」三欄,讓改卡的人分得清
一個數是被 KARST-195/196 的取數與折現率更正動了,還是被 KARST-197 的新閘動了。
"""
import os

import pandas as pd

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"
CARDS = ["AGX", "CLS", "COLL", "CRDO", "CRNC", "CRUS", "FN",
         "FSLR", "INOD", "LINC", "LMB", "LULU", "RMBS", "STRL"]


def main():
    o = pd.read_csv(os.path.join(D, "ranking_60.csv")).set_index("ticker")
    m = pd.read_csv(os.path.join(D, "KARST196-rerun60.csv")).set_index("ticker")
    n = pd.read_csv(os.path.join(D, "ranking_pool_v2.csv")).set_index("ticker")
    L = []
    L.append("# KARST-197 卡片更正數據(逐家)")
    L.append("")
    L.append("舊 = KARST-188 的 `ranking_60.csv`(卡片內文所引的那一批數);"
             "中 = KARST-195/196 重跑值;新 = KARST-197 的 `ranking_pool_v2.csv`。")
    L.append("列出中間值,是為了分得清一個數是被**取數與折現率更正**動了,"
             "還是被**新閘**動了。")
    L.append("")
    L.append("舊可排序基數 **41 家**(舊六十家之中過負債閘、賠率算得出的);"
             "新可排序基數 **46 家**（①池 103 家之中賠率算得出、基準值未扣起的）。")
    L.append("**排位下跌多數不是變差，是對手多了**——①池由 60 家擴大到 103 家。"
             "D-174 又把「觸發時價在 200 日線之上」那 22 家劃出①池（歸②回調入口），其中 CLS 是唯一一家已填卡的。")
    L.append("")
    for t in CARDS:
        r = n.loc[t]
        L.append("## %s —— %s" % (t, r["name"]))
        L.append("")
        L.append("| 格 | 舊(KARST-188,卡片內文) | 中(KARST-195/196) | 新(KARST-197) | 動了沒有 |")
        L.append("|---|---|---|---|---|")

        def row(k, ov, mv, nv):
            ch = "**動了**" if str(ov) != str(nv) else "無變"
            L.append("| %s | %s | %s | %s | %s |" % (k, ov, mv, nv, ch))

        if pd.notna(r["rank"]):
            newrank = "第 %d 位 / 46" % r["rank"]
        elif not bool(r["in_pool_1"]):
            newrank = "不排位（D-174：觸發時價在 200 日線之上，不屬①池）"
        else:
            newrank = "不排位（基準值扣起）"
        row("賠率排位", "第 %d 位 / 41" % o.loc[t, "rank"], "—", newrank)

        row("賠率", "%.2f" % o.loc[t, "odds"], "%.2f" % m.loc[t, "new_odds"],
            ("%.2f" % r["odds"]) if pd.notna(r["odds"]) else "扣起")
        row("數二 基準每股值", "%.2f" % o.loc[t, "n2_per_share"],
            "%.2f" % m.loc[t, "new_n2_per_share"],
            ("%.2f" % r["n2_per_share"]) if pd.notna(r["n2_per_share"])
            else "扣起(原值 %.2f)" % r["n2_per_share_withheld"])
        row("數二 相對現價", "%+.1f%%" % (100 * o.loc[t, "n2_upside"]),
            "%+.1f%%" % (100 * m.loc[t, "new_n2_upside"]),
            ("%+.1f%%" % (100 * r["n2_upside"])) if pd.notna(r["n2_upside"]) else "扣起")
        row("數三 一年回報", "%+.1f%%" % (100 * o.loc[t, "n3_ret_1y"]),
            "%+.1f%%" % (100 * m.loc[t, "new_n3_ret_1y"]),
            "%+.1f%%" % (100 * r["n3_ret_1y"]))
        row("折現率 WACC", "10.0%", "%.1f%%" % (100 * m.loc[t, "new_wacc"]),
            "%.1f%%" % (100 * r["wacc"]))
        row("淨負債(百萬美元)", "%.0f" % (o.loc[t, "net_debt"] / 1e6),
            "%.0f" % (m.loc[t, "new_net_debt"] / 1e6), "%.0f" % (r["net_debt"] / 1e6))
        row("負債閘 / 標籤", "過" if o.loc[t, "debt_gate"] else "不過", "—",
            "閘已取消;標籤「%s」(淨負債 ÷ 經營現金流 %s)"
            % (r["debt_label"], ("%.2f 倍" % r["net_debt_to_ocf"])
               if pd.notna(r["net_debt_to_ocf"]) else "算不出"))
        row("一年回報底線",
            "%s(舊 15%% 二分)" % ("過" if str(o.loc[t, "pass_bottom_line"])
                                   in ("True", "true") else "不過"),
            "—", "%s(新三級)" % r["ret_1y_grade"])
        row("200 日線形態", str(o.loc[t, "ma200_form"]), "—",
            "%s%s" % (r["ma200_form"],
                      "（D-174：不入①池，歸②回調入口）" if isinstance(r["not_in_pool_above_ma"], str) and r["not_in_pool_above_ma"] else ""))
        row("結論", str(o.loc[t, "A_conclusion"]), "—", str(r["conclusion"]))
        fx = str(r["falsify_exit_price"])
        L.append("| 證偽出場價（D-174） | （舊版無此格） | — | %s | 新增 |"
                 % (("每股 %.2f 美元（%.0f%%）" % (float(fx), 100 * float(r["falsify_exit_drop"])))
                    if fx else "（留空）"))
        L.append("")
        L.append("- 機制標籤(取代作廢的第一把尺):**%s** —— %s"
                 % (r["mechanism_label"], r["mechanism_reason"]))
        L.append("- 預登記預測支持買入:**%d / %d** —— %s"
                 % (r["pred_support"], r["pred_total"], r["pred_note"]))
        L.append("- 倖存者缺口深段:**%s**%s"
                 % (r["survivor_gap_deep"],
                    ("(%s)" % r["survivor_gap_why"])
                    if isinstance(r["survivor_gap_why"], str) and r["survivor_gap_why"] else ""))
        L.append("")
    with open(os.path.join(D, "KARST197-卡片更正數據.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("已寫 KARST197-卡片更正數據.md,%d 行" % len(L))


if __name__ == "__main__":
    main()
