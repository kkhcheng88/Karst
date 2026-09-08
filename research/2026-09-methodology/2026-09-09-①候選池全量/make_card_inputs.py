"""KARST-188 交付二的前置:把十二家的機械層數字整理成一份輸入表,
供寫卡片時逐格引用,避免各自重算而生出互相矛盾的數字。
輸出:card_inputs.md
"""
import os
import numpy as np
import pandas as pd

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"
# 正本十二家(票面規則:排位前十二,過底線者優先)+ 附加兩家(賠率第 2、3 但差底線不足一個百分點)
TOP12 = ["CRDO", "STRL", "COLL", "CLS", "LULU", "CRUS",
         "CRNC", "INOD", "FN", "AGX", "RMBS", "LMB",
         "FSLR", "LINC"]


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
    return format(x / 1e6, ",.0f") + " 百萬美元"


def main():
    r = pd.read_csv(os.path.join(D, "ranking_60.csv")).set_index("ticker")
    f = pd.read_csv(os.path.join(D, "screen60_full.csv")).set_index("ticker")

    L = ["# KARST-188 卡片輸入表(機械層數字正本)", "",
         "正本十二家(過底線者之中賠率最高的十二家):",
         "CRDO、STRL、COLL、CLS、LULU、CRUS、CRNC、INOD、FN、AGX、RMBS、LMB。",
         "附加兩家(不佔名額):FSLR —— 賠率排第 3 但差回報底線 0.35 個百分點;",
         "LINC —— 過底線但賠率排第 13,取數更正後被 STRL 擠出正本。", "",
         "本表是寫卡片時唯一的數字來源。卡片內任何數字與本表不符,以本表為準;",
         "覺得本表有錯,在卡片內寫明並舉手,不要自行改數。", "",
         "- 截止日 2026-09-09,折現率 10.0%(全批同一個數)。",
         "- ⚠ **價格不是收市價。** 抽數時(美東 2026-09-08 下午)美股仍在交易,",
         "  管線取到的是當日的即市報價而不是收市價,並把它標成「2026-09-08 收市」。",
         "  同一日抽兩次,六十家之中五十九家的價格不同(中位差 0.39%,最大 1.53%),",
         "  而 STRL 就是憑這 0.4 個百分點跨過回報底線、進入正本十二家的。",
         "  凡是「差不足一個百分點」的判定,都要當成落在雜訊之內。",
         "- 倉位一律標「示例值,未經對齊(D-170)」。", ""]

    for t in TOP12:
        a, b = r.loc[t], f.loc[t]
        L.append("## %s —— %s" % (t, a["name"]))
        L.append("")
        L.append("| 項目 | 值 |")
        L.append("|---|---|")
        rows = [
            ("賠率排位", "第 %d 位(全批 41 家可排序)" % int(a["rank"])),
            ("收市價", "%s 美元(2026-09-08)" % num(a["price"])),
            ("200 日線形態", a["ma200_form"]),
            ("價相對 200 日線", pct(b["px_vs_ma200"])),
            ("200 日線 40 日斜率(**40 日內累計變幅,不是每日**)",
             "%+.2f%%" % (b["ma200_slope_40d"] * 100)),
            ("窗口內相對標普", pct(b["rel_spy_win"])),
            ("一年最大回撤", pct(b["mdd_1y"])),
            ("折讓格", a["discount_grade"]),
            ("市銷率 現值 / 四年中位 / 一年中位 / 一年第 25 百分位",
             "%s / %s / %s / %s" % (num(b["ps_now"]), num(b["ps_p50_4y"]),
                                    num(b["ps_p50_1y"]), num(b["ps_p25_1y"]))),
            ("殺法歸因", "%s(同業 %d 家,%s,同業中位相對標普 %s)" %
             (a["kill_type"], int(b["peer_n"]) if pd.notna(b["peer_n"]) else 0,
              b["peer_basis"], pct(b["peer_med"]))),
            ("負債閘", ("過" if a["debt_gate"] else "不過") + "——" + str(a["debt_note"])),
            ("淨負債(含經營租賃與少數股東權益)", musd(b["net_debt"])),
            ("其中:有息負債 / 現金 / 投資",
             "%s / %s / %s" % (musd(b["debt_after_fix"]), musd(b["cash_after_fix"]),
                               musd(b["invest_after_fix"]))),
            ("營運現金流(近四季)", musd(b["ocf_ttm"])),
            ("淨負債 ÷ 營運現金流", num(b["net_debt_to_ocf"])),
            ("收入(近四季) / 營業利潤率 / 收入按年增速",
             "%s / %s / %s" % (musd(b["rev_ttm"]), pct(b["op_margin"]),
                               pct(b["rev_growth_yoy"]))),
            ("稀釋股數", format(b["diluted_shares"] / 1e6, ",.1f") + " 百萬股(來源 %s)" % b["shares_src"]),
            ("結算日", "%s%s" % (b["asof"],
                                 "  ⚠ **這是 SEC companyfacts 內最新的一張資產負債表,"
                                 "但它距價格日已 161 日,即公司已申報而未被收錄的那一季不在內——"
                                 "現金、負債、股數三格全部落後一季**"
                                 if str(b["asof"]) <= "2026-03-31" else "")),
            ("**數一** 現價隱含五年收入年增速", pct(a["n1_implied_g5"])),
            ("分析員共識收入增速", pct(a["consensus_rev_growth"])),
            ("**數二** 基準情境每股值 / 相對現價",
             "%s 美元 / %s" % (num(a["n2_per_share"]), pct(a["n2_upside"]))),
            ("數二 用的增速參考 / 利潤率 / 終值佔比",
             "%s / %s / %s" % (pct(b["g_ref_used"]), pct(b["margin_used"]),
                               pct(b["n2_terminal_share"], 0))),
            # 舊版這裡寫 `if b["n2_unreliable"]`,而沒有觸發警示的那些在 CSV 內是 NaN,
            # NaN 在 Python 是真值,於是十四家一律顯示「有警示」——是假警報,不是模型的問題。
            # 全批六十家實際只有 23 家觸發。
            ("數二 可信度警示",
             ("**是:%s——不可當合理結果**" % b["n2_unreliable"])
             if isinstance(b["n2_unreliable"], str) and b["n2_unreliable"].strip() else "無"),
            ("**數三** 一年持有回報 / 悲觀版(退出倍數用一年第 25 百分位)",
             "%s / %s" % (pct(a["n3_ret_1y"]), pct(b["n3_ret_1y_p25"]))),
            ("一年攤薄假設", "%s  ⚠ **這一格是機械估算,已知不可靠**——本票查出三家全錯"
                             "(有的公司同期在大手回購,有的剛大額增發),寫卡時請自行查"
                             "回購授權餘額與結算日之後的新發股數" % pct(b["dilution_1y"])),
            ("壓力跌幅(第一版機械公式)",
             "%s%s" % (pct(a["stress_drop"]),
                       "(機械公式算出的壓力價高於現價,已改用一年最大回撤封底)"
                       if b["stress_floor_applied"] else "")),
            ("賠率(數二上行 ÷ 壓力跌幅絕對值)", num(a["odds"])),
            ("過回報底線(數三 ≥ +15%,暫定示例線)", "是" if a["pass_bottom_line"] else "**否**"),
            ("示例倉位", "%s(示例值,未經對齊,D-170)" % pct(a["position_pct"], 2)),
            ("錯價來源標籤", "%s(第一把尺:隱含五年增速 %s 對分析員共識 %s,差 %s 個百分點;"
                              "門檻 ±3 個百分點之內為「與指引重疊」)%s"
             % (a["mispricing_label"], pct(a["n1_implied_g5"]),
                pct(a["consensus_rev_growth"]),
                ("%+.1f" % b["gap_vs_consensus_pp"]) if pd.notna(b.get("gap_vs_consensus_pp"))
                else "—",
                ("  ※ " + str(a["label_note"])) if isinstance(a["label_note"], str)
                and a["label_note"] else "")),
            ("指引原文摘要", str(a["label_guidance"])[:400]),
            ("不含模型鎖定結論", a["A_conclusion"]),
        ]
        for k, v in rows:
            L.append("| %s | %s |" % (k, str(v).replace("\n", " ")))
        L.append("")

    with open(os.path.join(D, "card_inputs.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")
    print("已寫 card_inputs.md,共 %d 家(正本十二家 + 附加兩家)" % len(TOP12))


if __name__ == "__main__":
    main()
