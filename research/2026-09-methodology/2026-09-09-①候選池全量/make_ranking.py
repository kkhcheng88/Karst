"""KARST-188 交付一:六十家排序表(.md + .csv)。

輸入:screen60_full.csv(機械層,已含 A-049 股數更正與 A-050 負債標籤更正)
      labels_merged.csv(五批子隊的錯價來源標籤 + 主線重推)
輸出:ranking_60.csv、ranking_60.md

主線裁定兩家(子隊標籤與重推不一致):
  COLL —— 子隊用的隱含增速是取數更正之前的數,當時與共識差 −23.6 個百分點,故判「更悲觀」。
          債務與現金兩項更正之後,隱含五年增速是 +4.6%、共識 −1.0%,差 +5.6 個百分點,
          **方向整個掉轉**,超出 ±3 個百分點的重疊帶。**以更正後的數為準,改判
          「市場比指引更樂觀」。** 這一家是取數缺陷如何反轉結論的最清楚實例。
  CLFD —— 派工時給子隊的第二把尺決策表沒有覆蓋「目標價溢價 ≥25% 但公司剛下調指引」
          這一格,子隊保守判「重疊」。主線補一條規則:目標價抽取日距離該次業績已
          超過一個月(下調在 2026-08-05,目標價抽於 2026-09-08),視為分析員已更新,
          照溢價判 → **市場比指引更悲觀**。這條補充規則列入流程檢討的改規格建議。
"""
import os
import numpy as np
import pandas as pd

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"
CUTOFF = "2026-09-09"
PRICE_DATE = "2026-09-08"

ADJUDICATED = {
    "COLL": ("市場比指引更樂觀",
             "主線改判:子隊用了取數更正前的隱含增速,差距由 −23.6pp 變成 +5.6pp,方向掉轉"),
    "CLFD": ("市場比指引更悲觀", "主線改判:補規則後照目標價溢價判"),
}


def pct(x, nd=1):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return ("%+." + str(nd) + "f%%") % (x * 100)


def num(x, nd=2):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return ("%." + str(nd) + "f") % x


def main():
    f = pd.read_csv(os.path.join(D, "screen60_full.csv"))
    lm = pd.read_csv(os.path.join(D, "labels_merged.csv")).set_index("ticker")

    f["mispricing_label"] = [
        ADJUDICATED[t][0] if t in ADJUDICATED else lm["label_team"].get(t, "資料不足")
        for t in f["ticker"]]
    f["label_note"] = [ADJUDICATED[t][1] if t in ADJUDICATED else "" for t in f["ticker"]]
    f["label_ruler"] = [lm["ruler_team"].get(t, "") for t in f["ticker"]]
    f["label_guidance"] = [lm["guidance"].get(t, "") for t in f["ticker"]]

    f["pass_bottom_line"] = f["pass_bottom_line"].astype(str).isin(["True", "true"])
    f["sortable"] = f["debt_gate"] & f["odds"].notna()

    def grp(r):
        # 排序只按賠率(用戶 §11 第 21 條),入場券只有負債閘一道——它是 D-169 的硬否決。
        # 回報底線 +15% 是暫定示例線,而且是刀鋒:六十家有 5 家擠在 12%–18%,
        # 一日價格波動就足以令名單翻轉,所以它降做欄位,不做排序的入場券。
        if not r["debt_gate"]:
            return 2  # 負債閘不過,直接不入
        if pd.notna(r["odds"]):
            return 0  # 可排序
        return 1      # 過閘但賠率算不出(數二無解)

    f["grp"] = f.apply(grp, axis=1)
    f = f.sort_values(["grp", "odds", "n3_ret_1y"],
                      ascending=[True, False, False]).reset_index(drop=True)
    f["debt_gate"] = f["debt_gate"].astype(bool)
    f["rank"] = [i + 1 if r["grp"] == 0 else None for i, r in f.iterrows()]

    cols = ["rank", "ticker", "name", "price", "price_date", "ma200_form", "discount_grade",
            "debt_gate", "debt_note", "kill_type", "peer_basis", "peer_n", "A_conclusion",
            "n1_implied_g5", "consensus_rev_growth", "n2_per_share", "n2_upside",
            "n2_unreliable", "n3_ret_1y", "stress_drop", "stress_floor_applied", "odds",
            "mispricing_label", "label_ruler", "label_guidance", "label_note",
            "pass_bottom_line", "position_pct", "ps_now", "ps_p50_4y", "ps_p50_1y",
            "ps_p25_1y", "net_debt", "ocf_ttm", "rev_ttm", "op_margin", "diluted_shares",
            "shares_src", "debt_fixed", "shares_fixed", "debt_doubt", "asof"]
    f[cols].to_csv(os.path.join(D, "ranking_60.csv"), index=False, encoding="utf-8")

    GRP_TITLE = {
        0: "甲組 —— 可排序池(過負債閘、賠率算得出),按賠率由高至低",
        1: "乙組 —— 過負債閘但賠率算不出(數二無解,無法排位)",
        2: "丙組 —— 負債閘不過,直接不入(不參與排序)",
    }
    HEAD = ("| 排位 | 代號 | 公司 | 收市價 | 200日線 | 折讓格 | 負債閘 | 殺法 | 不含模型結論 "
            "| 數一 隱含五年增速 | 共識增速 | 數二 相對現價 | 數三 一年回報 | 壓力跌幅 | 賠率 "
            "| 錯價來源標籤 | 用哪把尺 | 過底線 |")
    SEP = "|" + "---|" * 18

    L = []
    L.append("# KARST-188 交付一:六十家候選排序表")
    L.append("")
    L.append("- **截止日**:%s(全批一致)" % CUTOFF)
    L.append("- **價格日**:%s —— ⚠ **標成收市價,實際不是。** 抽數時美股仍在交易"
             "(美東 %s 下午),取到的是即市報價。同一日相隔約一小時抽兩次,"
             "六十家有五十九家價格不同(中位差 0.39%%、最大 1.53%%),"
             "足以令 STRL 跨過回報底線、令 3 家的折讓格改判、令 2 家的不含模型結論改判。"
             "見假設冊 A-056 與總覽 6.3。**凡是差不足一個百分點的判定都在雜訊之內。**"
             % (PRICE_DATE, PRICE_DATE))
    L.append("- **折現率**:10.0%(2026-09-08 十年期美國國債 4.792% + 5.0 個百分點股權溢價,"
             "四捨五入至 0.5 個百分點;全批同一個數,不逐家調)")
    L.append("- **排序依據**:只按賠率(數二上行 ÷ 壓力跌幅絕對值)。勝率不入排序,"
             "只在卡片內以區間寫出——依用戶 2026-09-07 §11 第 21、23 條的立場。")
    L.append("- ⚠ **錯價來源標籤的第一把尺已作廢。** D-171 第 4 項(2026-09-09)以「期限錯配」"
             "作廢了同一種比較(五年隱含路徑對一年指引)。本表六十家的共識全部取自下一財年,"
             "而拿去相減的是現價隱含的**五年**年增速;38 家經第一把尺定標籤,**正本十二家 12/12 全部**。"
             "而且「市場比指引更樂觀」那 30 家,**30 家全部來自第一把尺,第二把尺一家都沒有產生過**。"
             "見假設冊 A-057。**凡是「用哪把尺」一欄寫「第一把」的,標籤不可當結論。**")
    L.append("- **回報底線**:數三(一年持有回報)≥ +15%,暫定示例線,未經對齊。"
             "**排序本身不用它做入場券**(排序的入場券只有負債閘一道,它是 D-169 的硬否決),"
             "它只在挑「哪十二家要填卡」那一步起作用——見下文。")
    L.append("")
    L.append("## 資料清單")
    L.append("")
    L.append("| 欄位 | 來源 | 抽取日 |")
    L.append("|---|---|---|")
    for a, b, c in [
        ("收市價、200 日線、40 日斜率、一年最大回撤", "yfinance 日線(未復權收市價)", PRICE_DATE),
        ("收入、營業利潤、營運現金流、現金、債務、股數", "SEC XBRL companyfacts(當日重新下載,60/60 成功)", CUTOFF),
        ("歷史市銷率四年 / 一年分位", "yfinance 日線 × SEC 收入", PRICE_DATE),
        ("同業相對標普回報(殺法歸因)", "KARST-184 第一步原始表 screen_step1_raw.csv 的 rel_spy", "2026-09-08"),
        ("共識收入增速、分析員目標價", "yfinance Ticker.revenue_estimate / analyst_price_targets", PRICE_DATE),
        ("指引原文", "SEC EDGAR 8-K / 6-K Item 2.02 業績新聞稿附件(逐家直讀原文)", CUTOFF),
        ("十年期美國國債孳息", "yfinance ^TNX", "2026-09-08"),
    ]:
        L.append("| %s | %s | %s |" % (a, b, c))
    L.append("")
    L.append("## 五處已知更正(排序表用的是更正後的數)")
    L.append("")
    L.append("- **A-049 稀釋股數**:共用工具把「稀釋後加權平均股數」當流量科目拆季,"
             "6 家(VPG、ORCL、FN、VIAV、MRCY、IREN)抽到的股數只有實際值的 0.1%–4.4%,"
             "每股值被放大 25 至 1,000 倍。本票在自己的腳本內本地更正,共用工具未改。")
    L.append("- **A-053 債務標籤**:債務科目標籤清單太窄,漏掉信貸額度、可轉債、"
             "有抵押債與合計式標籤。ORCL 的 1,301 億美元債務曾被讀成 72 億,CLVT 的 43 億債務"
             "曾被讀成淨現金,COLL 的可轉債 2.387 億美元被靜靜丟掉。"
             "更正後 **7 家(11.7%)過不了負債閘**,即上一輪初篩本來就不應放行。")
    L.append("- **A-054 現金與投資項**:投資科目標籤清單同樣太窄"
             "(CRUS 的投資項由 0 補回 3.567 億美元、AGX 由 1.834 億補回至 4.806 億,"
             "即補回 2.971 億),而且取值不查申報日期,會收到早一季的舊結餘"
             "(COLL 的 1.573 億美元在結算日之前已變現用於收購)。本批 9 家的現金項有改動。")
    L.append("- **合計標籤重覆計數(本輪新查出,由 RMBS 的卡片隊反查出來)**:"
             "`AvailableForSaleSecuritiesDebtSecurities` 是流動加非流動的**合計**標籤,"
             "原先誤放進非流動桶,於是 RMBS 同一筆 6.518 億美元證券在流動與非流動桶各計一次,"
             "淨現金虛報 6.518 億;修正後現金加投資 7.86 億,與 10-Q 的 8.25 億對得上。"
             "已加保險絲:流動桶與非流動桶金額完全相同時判為同一筆,不重覆計。")
    L.append("- **現金標籤前綴未涵蓋(本輪新查出,由 CRNC 的卡片隊反查出來)**:"
             "CRNC 的現金掛在 "
             "`CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncluding"
             "DisposalGroupAndDiscontinuedOperations`,不在清單內,現金被讀成 0。"
             "改為前綴比對後取得。**這一項令 CRNC 的數二由 −29.5% 變 +3.6%、排位由第 12 升至第 9。**")
    L.append("")

    for g in (0, 1, 2):
        sub = f[f["grp"] == g]
        if sub.empty:
            continue
        L.append("## %s(%d 家)" % (GRP_TITLE[g], len(sub)))
        L.append("")
        L.append(HEAD)
        L.append(SEP)
        for _, r in sub.iterrows():
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                ("%d" % r["rank"]) if pd.notna(r["rank"]) else "—",
                r["ticker"], str(r["name"])[:26], num(r["price"]),
                r["ma200_form"], r["discount_grade"],
                "過" if r["debt_gate"] else "**不過**",
                r["kill_type"] if isinstance(r["kill_type"], str) else "—",
                r["A_conclusion"],
                pct(r["n1_implied_g5"]), pct(r["consensus_rev_growth"]),
                pct(r["n2_upside"]), pct(r["n3_ret_1y"]),
                pct(r["stress_drop"]),
                num(r["odds"]) if pd.notna(r["odds"]) else "—",
                r["mispricing_label"],
                # 第一把尺 = 五年隱含增速對一年共識,已因期限錯配作廢(A-057、D-171 第 4 項)。
                "**第一把(已作廢)**" if pd.notna(r["n1_implied_g5"]) else "第二把(目標價)",
                "是" if r["pass_bottom_line"] else "否"))
        L.append("")

    L.append("## 表格怎樣讀")
    L.append("")
    L.append("- **200日線**:「殺」= 價低於 200 日線且線本身在向下;「線附近」= 價低於線但線仍向上;"
             "「回調」= 價仍高於線,依 D-169 不算錯殺,直接不入。")
    L.append("- **折讓格**:市銷率要同時低於四年中位數與一年中位數的 0.8 倍才算「兩把尺都過」;"
             "只過一把,代表估值重估已經完成,不是折讓。")
    L.append("- **負債閘**:淨現金,或淨負債不超過營運現金流的 3 倍。不過就不入,無論其他格幾好。")
    L.append("- **數一**:現價要成立的話,公司未來五年收入年均要增長多少。")
    L.append("- **數二**:基準情境每股值相對現價的差距。負數 = 基準情境下現價已經偏貴。")
    L.append("- **數三**:一年持有、以退出市銷率倍數收工的回報。這是回報底線那一格。")
    L.append("- **壓力跌幅**:一年市銷率第 25 百分位 × 收入打九折,再以一年最大回撤封底。"
             "**這是第一版機械公式,不是壓力測試結論。**")
    L.append("- **賠率** = 數二上行 ÷ 壓力跌幅絕對值。負賠率代表基準情境本身已經向下,"
             "排在正賠率之後、按數值大小(即向下幅度相對壓力的比例)由小到大排。")
    L.append("")
    a = f[f["grp"] == 0]
    card12 = a[a["pass_bottom_line"]].head(12)
    # 附加兩家不是「最接近底線的兩家」,是「價格雜訊會把它換入正本十二家的那兩家」
    # ——依 price_sensitivity.csv:+0.39% 換入 LINC(STRL 出),−0.39% 換入 FSLR
    # (LMB 出)。CIEN 在 −0.39% 一樣過底線,但賠率低於 FSLR,換不進十二家,
    # 所以沒有填卡。
    extra = ["FSLR", "LINC"]
    L.append("## 哪十二家要填定位卡")
    L.append("")
    L.append("票面寫死的取法:**排位前十二家,過底線者優先;不足十二家才補上最接近底線者並標明。**"
             "本批可排序的 41 家之中,過底線的有 18 家,多過十二家,"
             "所以取這 18 家之中賠率最高的十二家。")
    L.append("")
    L.append("**正本十二家**:%s" % "、".join(card12["ticker"]))
    L.append("")
    L.append("排序軸只有賠率一條,但賠率高不等於值得做:本批 CENX 賠率 1.59 排第 5,"
             "一年回報卻是 −1.1%,那不是刀鋒,是真的不值博——底線這一關擋得對。")
    L.append("")
    L.append("**另加兩家(不佔十二家名額,標明是附加)**:%s。" % "、".join(extra))
    L.append("這兩家不是「最接近底線的兩家」,而是**價格雜訊一動就會換進正本十二家的那兩家**:"
             "同一日相隔一小時的兩次抽數,價格中位差 0.39%(A-056);"
             "把全批價格整體移 +0.39%,LINC 換入、STRL 出局;移 −0.39%,FSLR 換入、LMB 出局。"
             "換言之這兩個名字與正本第十二名的分別,小於抽數時點造成的差別,"
             "**十二這個界線在此處不可重現**,所以兩家照樣填卡、明確不佔正本名額。")
    L.append("")
    L.append("底線本身同樣是刀鋒:全批有 5 家的數三落在 12%–18% 這一帶;"
             "距線最近的四家分別是 STRL +0.13%、CIEN −0.20%、FSLR −0.30%、MTZ −1.05%"
             "(數字是「價格要動多少才翻轉」),四家全部在一次抽數的價差之內。"
             "**+15% 是暫定示例線、未經對齊**,已在票上舉手請用戶裁要不要設容差。"
             "(CIEN 在 −0.39% 一樣會過底線,但賠率低於 FSLR、換不進十二家,故未填卡。)")
    L.append("")

    L.append("## 錯價來源標籤分佈")
    L.append("")
    vc = f["mispricing_label"].value_counts()
    L.append("| 標籤 | 家數 | 佔比 |")
    L.append("|---|---|---|")
    for k, v in vc.items():
        L.append("| %s | %d | %.0f%% |" % (k, v, v / len(f) * 100))
    L.append("")
    L.append("六十家全部拿到標籤,沒有一家要標「資料不足」——指引原文逐家由 SEC 8-K/6-K 原件讀出,"
             "拿不到數字指引的公司改用分析員目標價那把尺,兩把尺都用不上才會是資料不足,本批沒有。")
    L.append("")

    with open(os.path.join(D, "ranking_60.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")

    print("已寫 ranking_60.csv / ranking_60.md")
    print(f.groupby("grp").size().to_string())
    print()
    print("甲組(可排序):")
    print(f[f["grp"] == 0][["rank", "ticker", "odds", "n2_upside", "n3_ret_1y",
                            "stress_drop", "mispricing_label"]].to_string(index=False))
    print()
    print("標籤分佈:")
    print(vc.to_string())
    print()
    print("乙組(賠率算不出):", list(f[f["grp"] == 1]["ticker"]))
    print("丙組(負債閘不過):", list(f[f["grp"] == 2]["ticker"]))
    print("過底線總數(不論能否排序):", int((f["debt_gate"] & f["pass_bottom_line"]).sum()))
    print("正本十二家:", list(card12["ticker"]))
    print("附加兩家:", extra)


if __name__ == "__main__":
    main()
