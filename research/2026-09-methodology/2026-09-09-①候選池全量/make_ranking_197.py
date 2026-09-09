# -*- coding: utf-8 -*-
"""KARST-197 第三步:新版排序表(ranking_pool_v2.csv / .md)+ 舊六十家逐家對比。

版式按票上寫入的六件裁決(正本 D-172、D-173):
  1. 市值閘取消(D-172,用戶裁決)——已在篩選層執行,排序表不設市值欄作條件
  2. 閘只剩兩條(D-173,用戶裁決)——現金流閘 + 成交額線;負債比率作標籤欄
  3. 回報底線三級(暫定)——≥17% 過線 / 13–17% 貼線(列「觀察」)/ <13% 不過
  4. 否決者留表(暫定)——200 日線形態「回調」者照列,另欄標「被否決(形態)」
  5. 三類機制標籤(暫定)——經營損害被高估 / 現金或資產價值實現 / 倍數重估;
     第三類寫不出重估理由即標「無理由」
  6. 預測零支持不得升買(暫定)——預登記預測沒有一項支持買入者,結論上限「觀察」

D-174(用戶 2026-09-10 裁決)再加兩件,本檔以**加欄**方式補上,不重做上面六件:
  7. **賠率分母降為參考欄** —— 公式壓力跌幅仍然是現用分母,但它只是參考口徑,
     表上另立「分母口徑」欄寫明;真正要用的是**證偽出場價**(論點失效時該賣的價),
     由判斷層逐家寫,只對填了卡的家數填,未填卡者留空——不准用公式數字冒充。
  8. **200 日線由否決改為定義** —— 觸發時價格在 200 日線之上者**不入①池**,歸②回調
     入口。原「被否決(形態)」欄改名「不入池(線上)」,照列供日後對照,不落注、不填卡。

另:A-055 資料落後者基準每股值扣起(賠率一併扣起),表上標明;
    倖存者缺口深段(市值 < 5 億美元 或 負債比率 > 6 倍 / 算不出)另標。
"""
import json
import os

import numpy as np
import pandas as pd

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"

# ── 預登記預測「支持買入」逐項判定(主 agent 判定,非用戶裁決) ────────────────
# 判準:該項預測若成真,是否支持「錯價會被糾正」這一邊。
# 指引維持/上調、收入或利潤率不失守、去槓桿、內部人買入 = 支持;
# 指引下調、利潤率轉差、稀釋、集中度風險持續、倍數不回歸 = 不支持。
PRED_SUPPORT = {
    "FSLR": (1, 3, "P1 指引不下調 = 支持;P2 毛利率轉差、P3 收入按年下降 = 不支持"),
    "LINC": (0, 3, "三項全部指向招生失速、指引下調、自由現金流為負"),
    "AGX":  (0, 3, "三項全部指向在手訂單縮、毛利率跌、市銷率不回歸"),
    "CLS":  (1, 3, "P1 收入達指引上限 = 支持;P2 稀釋、P3 股價不回高位 = 不支持"),
    "COLL": (2, 3, "P2 指引不再下調、P3 新藥合計收入達標 = 支持;P1 舊藥收入跌 = 不支持"),
    "CRDO": (1, 3, "P1 毛利率達指引 = 支持;P2 無內部人買入、P3 客戶集中度持續 = 不支持"),
    "CRNC": (2, 3, "P1 自由現金流達指引下限、P3 回購可轉債 = 支持;P2 收入指引按年跌 = 不支持"),
    "CRUS": (2, 3, "P1 收入不穿指引下限、P2 毛利率守 52% = 支持;P3 市銷率不回歸 = 不支持"),
    "FN":   (2, 3, "P2 下季指引達標、P3 營業利潤率守 10% = 支持;P1 自由現金流仍為負 = 不支持"),
    "INOD": (1, 3, "P1 收入增速守 40% 指引 = 支持;P2 動用 ATM 稀釋、P3 客戶預付款下降 = 不支持"),
    "LMB":  (0, 3, "三項全部指向 EBITDA 利潤率不達節奏、有機收入仍負、無內部人買入"),
    "LULU": (2, 3, "P2 指引不第五度下調、P3 內部人買入 = 支持;P1 可比銷售 ≤ −10% = 不支持"),
    "RMBS": (3, 3, "三項全部指向權利金與總收入達指引上限、大客戶無流失"),
    "STRL": (1, 3, "P2 全年收入指引不下調 = 支持;P1 分部利潤率續跌、P3 無內部人買入 = 不支持"),
}

BL_PASS, BL_NEAR = 0.17, 0.13
DEEP_MCAP = 5e8
CUTOFF = "2026-09-10"

# ── 證偽出場價(D-174 第一件):論點失效時該賣的價 ──────────────────────────
# **只准填卡片第五節「壓力情境」裡由人手推出來的壓力價**,即「原先認為的護城河失效」
# 之後這盤生意值多少。未填卡的公司一律留空——公式壓力跌幅是參考欄,不准冒充這一格。
# 每一格後面那句是出處(卡內哪一節、怎樣推出來的)。
FALSIFY_EXIT_FILE = "falsify_exit_197.json"


def pct(x, nd=1):
    if x is None or (isinstance(x, float) and (np.isnan(x))):
        return "—"
    return ("%+." + str(nd) + "f%%") % (x * 100)


def num(x, nd=2):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return ("%." + str(nd) + "f") % x


def bl_grade(r):
    if r is None or (isinstance(r, float) and np.isnan(r)):
        return "算不出"
    if r >= BL_PASS:
        return "過線(≥17%)"
    if r >= BL_NEAR:
        return "貼線(13–17%)"
    return "不過(<13%)"


def mechanism(row):
    """三類機制標籤(D-173 暫定第三件)。機械批次判得出的只有前兩類。"""
    g5, cg = row.get("n1_implied_g5"), row.get("consensus_rev_growth")
    nd, mcap = row.get("net_debt"), row.get("mcap_now")
    if (g5 is not None and not pd.isna(g5) and cg is not None and not pd.isna(cg)
            and g5 <= cg - 0.03):
        return ("經營損害被高估",
                "反推五年增速 %.1f%%,低於共識 %.1f%%,差 %.1f 個百分點"
                % (100 * g5, 100 * cg, 100 * (g5 - cg)))
    if (nd is not None and not pd.isna(nd) and nd < 0
            and mcap and not pd.isna(mcap) and (-nd) / mcap >= 0.30):
        return ("現金或資產價值實現",
                "淨現金 %.0f 百萬美元,佔市值 %.0f%%" % (-nd / 1e6, 100 * (-nd) / mcap))
    return ("倍數重估", "無理由(機械批次寫不出重估理由,須人手補)")


def deep_gap(row):
    why = []
    mcap = row.get("mcap_now")
    if mcap is None or pd.isna(mcap):
        why.append("市值未知")
    elif mcap < DEEP_MCAP:
        why.append("市值 %.2f 億美元 < 5 億" % (mcap / 1e8))
    dl = row.get("debt_label")
    if dl in ("高(>6 倍)", "算不出"):
        why.append("負債比率 " + str(dl))
    return ("是" if why else "否"), ";".join(why)


def main():
    f = pd.read_csv(os.path.join(D, "screen_pool_197.csv"))
    f = f[f["error"].isna()].copy() if "error" in f.columns else f
    old60 = set(pd.read_csv(os.path.join(D, "screen60_full.csv"))["ticker"])

    f["ret_1y_grade"] = [bl_grade(x) for x in f["n3_ret_1y"]]
    mech = [mechanism(r) for _, r in f.iterrows()]
    f["mechanism_label"] = [m[0] for m in mech]
    f["mechanism_reason"] = [m[1] for m in mech]
    dg = [deep_gap(r) for _, r in f.iterrows()]
    f["survivor_gap_deep"] = [d[0] for d in dg]
    f["survivor_gap_why"] = [d[1] for d in dg]
    # D-174 第二件:200 日線由「否決」改為「定義」——線上者不入①池,歸②回調入口
    f["not_in_pool_above_ma"] = np.where(
        f["ma200_form"] == "回調", "不入池(線上,歸②回調入口)", "")
    f["in_pool_1"] = f["not_in_pool_above_ma"] == ""
    # D-174 第一件:賠率分母降為參考欄
    f["denominator_basis"] = "公式壓力跌幅(參考欄)"
    try:
        with open(os.path.join(D, FALSIFY_EXIT_FILE), encoding="utf-8") as fh:
            fx = json.load(fh)
    except FileNotFoundError:
        fx = {}
    fx = {k: v for k, v in fx.items() if not k.startswith("_")}
    f["falsify_exit_price"] = [fx.get(t, {}).get("exit_price", "") for t in f["ticker"]]
    f["falsify_exit_drop"] = [fx.get(t, {}).get("drop", "") for t in f["ticker"]]
    f["falsify_exit_source"] = [fx.get(t, {}).get("source", "") for t in f["ticker"]]
    f["falsify_exit_note"] = [fx.get(t, {}).get("note", "") for t in f["ticker"]]
    f["pred_support"] = [PRED_SUPPORT.get(t, (0, 0, ""))[0] for t in f["ticker"]]
    f["pred_total"] = [PRED_SUPPORT.get(t, (0, 0, ""))[1] for t in f["ticker"]]
    f["pred_note"] = [PRED_SUPPORT.get(t, (0, 0, "未登記預測"))[2] for t in f["ticker"]]
    f["is_new_entrant"] = ~f["ticker"].isin(old60)
    f["has_card"] = f["ticker"].isin(PRED_SUPPORT.keys())

    def conclude(r):
        if r["not_in_pool_above_ma"]:
            return "不入池(線上,歸②回調入口)"
        if r["baseline_withheld"]:
            return "觀察(基準值扣起:資料落後)"
        g = r["ret_1y_grade"]
        if g == "算不出":
            return "觀察(一年回報算不出)"
        if g == "不過(<13%)":
            return "不入(一年回報不過線)"
        if g == "貼線(13–17%)":
            return "觀察(貼線,不下結論)"
        if r["pred_support"] == 0:
            return ("觀察(預登記預測零支持)" if r["has_card"]
                    else "觀察(未填卡、無預登記預測)")
        return "買入候選"

    f["conclusion"] = f.apply(conclude, axis=1)
    f["odds_negative"] = np.where(f["odds"].notna() & (f["odds"] <= 0), "是", "")

    # 甲 = ①池內且賠率算得出;乙 = ①池內但不排位;丙 = 線上,不入①池(照列)
    f["grp"] = np.where(~f["in_pool_1"], 2, np.where(f["odds"].notna(), 0, 1))
    f = f.sort_values(["grp", "odds", "n3_ret_1y"],
                      ascending=[True, False, False]).reset_index(drop=True)
    f["rank"] = [i + 1 if r["grp"] == 0 else None for i, r in f.iterrows()]

    cols = ["rank", "ticker", "name", "odds", "denominator_basis",
            "falsify_exit_price", "falsify_exit_drop", "falsify_exit_source",
            "falsify_exit_note",
            "ret_1y_grade", "n3_ret_1y",
            "debt_label", "net_debt_to_ocf", "ma200_form", "not_in_pool_above_ma",
            "in_pool_1", "mechanism_label", "mechanism_reason", "survivor_gap_deep",
            "survivor_gap_why", "pred_support", "pred_total", "pred_note",
            "conclusion", "odds_negative", "is_new_entrant", "has_card",
            "baseline_withheld", "price", "price_date", "mcap_now", "rel_spy_screen",
            "n1_implied_g5", "consensus_rev_growth", "gap_vs_consensus_pp",
            "n2_per_share", "n2_upside", "n2_per_share_withheld", "n2_upside_withheld",
            "odds_withheld", "n2_unreliable", "stress_drop", "stress_floor_applied",
            "discount_grade", "ps_now", "ps_p50_1y", "ps_p50_4y", "ps_p25_1y",
            "wacc", "de_ratio", "net_debt", "ocf_ttm", "rev_ttm", "op_margin",
            "diluted_shares", "asof", "stale_lag_days", "sic_description", "grp"]
    cols = [c for c in cols if c in f.columns]
    f[cols].to_csv(os.path.join(D, "ranking_pool_v2.csv"),
                   index=False, encoding="utf-8-sig")

    # ── Markdown ────────────────────────────────────────────────────────────
    L = []
    L.append("# ①候選池排序表 v2(KARST-197,新閘重篩)")
    L.append("")
    L.append("- 立場日:%s。價格:**2026-09-08 收市價**(美東時間判市,已退回上一個"
             "完成交易日;口徑見 KARST-195 第七項)。" % CUTOFF)
    L.append("- 池:由 5,104 家宇宙按 **D-172 / D-173 新閘**重篩,%d 家入池"
             "(舊版 60 家,全部留在池內)。" % len(f))
    L.append("- 閘只有兩條:**滾動四季經營現金流 > 0**、**近 60 日中位成交金額 ≥ 300 萬美元**"
             "(示例值,待參數對齊)。觸發條件不變:2026-06-01 → 2026-09-04 相對 SPY 跌逾 25%。")
    L.append("- **市值不再是條件,亦不作標籤**(D-172,用戶裁決)。負債比率**只算不剔**"
             "(D-173,用戶裁決)。")
    L.append("- 排序只按賠率(基準每股值相對現價 ÷ 壓力跌幅),由高至低;賠率算不出或"
             "基準值被扣起者不排位,列乙組。")
    L.append("")
    L.append("## 版式的六條規則(出處:D-172、D-173;第三至六條為暫定工作規則)")
    L.append("")
    L.append("| # | 規則 | 身分 |")
    L.append("|---|---|---|")
    L.append("| 1 | 市值閘取消,市值不作篩選亦不作標籤 | **用戶裁決**(D-172) |")
    L.append("| 2 | 閘只剩現金流閘 + 成交額線;負債比率降為標籤 | **用戶裁決**(D-173) |")
    L.append("| 3 | 一年回報底線三級:≥17% 過線、13–17% 貼線(不下結論)、<13% 不過 | 暫定(主 agent 建議) |")
    L.append("| 4 | 200 日線形態「回調」者照列排序表,另欄標「被否決」,不落注 | 暫定 |")
    L.append("| 5 | 錯價來源改三類機制標籤;倍數重估寫不出理由標「無理由」 | 暫定 |")
    L.append("| 6 | 預登記預測沒有一項支持買入者,結論上限「觀察」 | 暫定 |")
    L.append("| 7 | 賠率分母(公式壓力跌幅)降為參考欄;證偽出場價由判斷層逐家寫,"
             "只對填卡的家數填 | **用戶裁決**(D-174) |")
    L.append("| 8 | 200 日線由否決改為定義:觸發時價在線之上者**不入①池**,歸②回調入口;"
             "照列供對照,不落注、不填卡 | **用戶裁決**(D-174) |")
    L.append("")
    L.append("**第七條要講清楚的一件事。** 現時排序用的賠率,分母仍然是那條公式壓力跌幅"
             "(退出市銷率 25 分位,以一年最大回撤封底)——它量的是「這隻股票過去跌過幾多」,"
             "不是「論點失效時它值幾多」。D-174 把它降為參考欄,真正要用的是**證偽出場價**,"
             "而那個數只有填了卡、逐家推過壓力情境的公司才寫得出。**未填卡的一律留空,"
             "不准用公式數字冒充**——留白至少講得出自己不知道。")
    L.append("")
    L.append("**第八條改變了池的定義,不只是一個欄名。** 觸發時價格仍在 200 日線之上的"
             "公司,由「入池但被否決」改為**根本不入①池**——它們是上升趨勢中的回調,"
             "屬②的入口,不是錯殺。表上照列,是為了日後可以對照「當初判了不入的那批,"
             "後來走成點」。")
    L.append("")
    pool1 = f[f["in_pool_1"]]
    n_deep = int((pool1["survivor_gap_deep"] == "是").sum())
    n_new = int(pool1["is_new_entrant"].sum())
    n_wh = int(pool1["baseline_withheld"].sum())
    n_above = int((~f["in_pool_1"]).sum())
    L.append("## 一眼看到的數")
    L.append("")
    L.append("| 項目 | 數 |")
    L.append("|---|---:|")
    L.append("| 過兩道閘的候選(觸發 + 現金流 + 成交額) | %d |" % len(f))
    L.append("| **扣除 200 日線之上者,①池家數** | **%d** |" % len(pool1))
    L.append("| 不入①池(線上,歸②回調入口) | %d |" % n_above)
    L.append("| ①池內舊六十家 | %d |" % int((~pool1["is_new_entrant"]).sum()))
    L.append("| ①池內新進池 | %d |" % n_new)
    L.append("| 一年回報過線(≥17%%) | %d |" % int((pool1["ret_1y_grade"] == "過線(≥17%)").sum()))
    L.append("| 貼線(13–17%%,不下結論) | %d |" % int((pool1["ret_1y_grade"] == "貼線(13–17%)").sum()))
    L.append("| 基準值扣起(資料落後,A-055) | %d |" % n_wh)
    L.append("| 倖存者缺口深段(市值 < 5 億 或 負債 > 6 倍 / 算不出) | %d |" % n_deep)
    L.append("| 證偽出場價已填(只限填卡者) | %d |"
             % int((f["falsify_exit_price"].astype(str) != "").sum()))
    L.append("| 結論「買入候選」 | %d |" % int((f["conclusion"] == "買入候選").sum()))
    L.append("")
    L.append("**倖存者缺口深段是什麼意思**:市值 1–5 億美元那一段與高負債公司,歷史基準率"
             "建基於今日仍然在生的公司,已經倒閉或除牌那些不在名單內——所以那一段的歷史"
             "成績天生偏樂觀(D-172 影響欄)。標了這一格的公司,基準率對它的估計要打折看。")
    L.append("")

    GRP_TITLE = {0: "## 甲組 —— ①池內、可排序(賠率算得出),按賠率由高至低",
                 1: "## 乙組 —— ①池內但不排位(賠率算不出,或基準值被扣起)",
                 2: "## 丙組 —— 不入①池(觸發時價在 200 日線之上,歸②回調入口);"
                    "照列供日後對照,不落注、不填卡"}
    HEAD = ("| 排位 | 代號 | 公司 | 賠率 | 分母口徑 | 證偽出場價 | 一年回報 | (數值) "
            "| 負債比率標籤 | 200日線 | 不入池(線上) "
            "| 機制標籤 | 缺口深段 | 預測支持 | 結論 | 新進 |")
    SEP = "|---:|---|---|---:|---|---|---|---:|---|---|---|---|---|---|---|---|"
    for g in (0, 1, 2):
        sub = f[f["grp"] == g]
        if sub.empty:
            continue
        L.append(GRP_TITLE[g])
        L.append("")
        L.append(HEAD)
        L.append(SEP)
        for _, r in sub.iterrows():
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                ("%d" % r["rank"]) if r["grp"] == 0 else "—",
                r["ticker"], str(r["name"])[:28],
                num(r["odds"]), r["denominator_basis"],
                (("%.2f（%.0f%%）" % (float(r["falsify_exit_price"]), 100 * float(r["falsify_exit_drop"]))) if str(r["falsify_exit_price"]) else "（留空：未填卡）"),
                r["ret_1y_grade"], pct(r["n3_ret_1y"], 0),
                r["debt_label"], r["ma200_form"],
                r["not_in_pool_above_ma"] or "—", r["mechanism_label"],
                r["survivor_gap_deep"],
                ("%d/%d" % (r["pred_support"], r["pred_total"])) if r["pred_total"] else "未登記",
                r["conclusion"], "新" if r["is_new_entrant"] else "—"))
        L.append("")

    L.append("## 機制標籤怎樣判(機械層)")
    L.append("")
    L.append("| 標籤 | 機械判準 | 家數 |")
    L.append("|---|---|---:|")
    vc = f["mechanism_label"].value_counts()
    L.append("| 經營損害被高估 | 反推五年增速比分析員共識低 3 個百分點以上 | %d |"
             % int(vc.get("經營損害被高估", 0)))
    L.append("| 現金或資產價值實現 | 淨現金 ≥ 市值 30%% | %d |"
             % int(vc.get("現金或資產價值實現", 0)))
    L.append("| 倍數重估 | 其餘 | %d |" % int(vc.get("倍數重估", 0)))
    L.append("")
    L.append("**「倍數重估」那一格全部標「無理由」。** 規則第五條要求倍數重估必須寫得出"
             "重估理由(接到盈利能力、增長、風險或資本配置的一項具體變化);機械批次寫不出"
             "——它只看得見倍數低,看不見倍數為什麼會回來。要用這一格就要人手補那句話。")
    L.append("")
    L.append("## 賠率為負的家數")
    L.append("")
    nneg = int((f["odds_negative"] == "是").sum())
    nneg_buy = int(((f["odds_negative"] == "是") & (f["conclusion"] == "買入候選")).sum())
    L.append("賠率 ≤ 0(基準每股值低於現價)共 **%d** 家;其中結論仍是「買入候選」的有 "
             "**%d** 家。六條規則沒有一條管得住這一格——一年回報靠退出市銷率,"
             "與長期基準值無關,兩者可以指相反方向。**這是規則的洞,不是數字的錯**,已在票上舉手。"
             % (nneg, nneg_buy))
    L.append("")

    with open(os.path.join(D, "ranking_pool_v2.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")

    meta = dict(cutoff=CUTOFF, price_date="2026-09-08",
                price_note="收市價;美東時間判市後退回上一個完成交易日(KARST-195 第七項)",
                pool=len(f), new_entrants=n_new, withheld=n_wh, deep_gap=n_deep,
                rules_source=["D-172(用戶裁決)", "D-173(用戶裁決 + 四件暫定)"])
    with open(os.path.join(D, "ranking_pool_v2.meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    print("已寫 ranking_pool_v2.csv / .md;%d 家,買入候選 %d 家"
          % (len(f), int((f["conclusion"] == "買入候選").sum())))
    print(f[f["grp"] == 0].head(12)[["rank", "ticker", "odds", "ret_1y_grade",
                                     "conclusion"]].to_string())


if __name__ == "__main__":
    main()
