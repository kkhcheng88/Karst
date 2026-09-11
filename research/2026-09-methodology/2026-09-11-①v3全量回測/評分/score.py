# -*- coding: utf-8 -*-
"""KARST-215 評分隊:v3 全量回測(十四宗、52 家)對上 KARST-199 籃子結果。

只讀三批的 判-E*.csv(機械版)與 199 的 out/basket_members.csv;不改任何既有輸出。
口徑:research/2026-09-methodology/2026-09-11-①v3全量回測/執行口徑——v3全量回測.md 第四節。

計算分工:
  表一 步〇可信程度三檔 × 籃子層面十二個月超額(籃子中位)
  表二 步五 dmg_true / dmg_false × 個股相對籃子中位超額(分「步〇高」與「步〇低/中」兩組)
  表三 q1_verdict 三檔 × 個股十二個月超額
  表四 必要前提事後守住/被推翻 × 超額（事後判斷,手寫於 PREMISE 表）
  表五 與 v1(KARST-204)、v2.1(KARST-210)同家對比

用法:PYTHONUTF8=1 python score.py
"""
import glob
import os

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

BASE = os.path.dirname(os.path.abspath(__file__))
V3 = os.path.dirname(BASE)                       # …/2026-09-11-①v3全量回測
METH = os.path.dirname(V3)                       # …/2026-09-methodology
BASKET = os.path.join(METH, "2026-09-10-①行業殺錯事件籃子")
MEMBERS = os.path.join(BASKET, "out", "basket_members.csv")
V1_DIR = os.path.join(BASKET, "checklist_test", "out")
V21 = os.path.join(METH, "2026-09-11-①並排歷史考試", "評分表.csv")

MIN_N = 8  # 少於此家數只報方向,不作定論

# ---- 欄位對齊(三批原檔不改,在本腳本內正規化)--------------------------------
# 判詞兩套寫法其實同一件事:批1/批2 短寫、批3 長寫。
Q1_ALIAS = {
    "更好": "更好",
    "現價要求比我們預期更好": "更好",
    "相稱": "相稱",
    "現價要求比我們預期更壞": "更壞",
    "更壞": "更壞",
    "資料不足": "資料不足",
}
# 便宜度序數:現價要求的壞結果比我們預期更壞 = 市場已打得最狠 = 最便宜。
# 若①成立,便宜度應與之後的超額正相關。
Q1_ORD = {"更壞": 3, "相稱": 2, "更好": 1}

DMG_ORD = {"重大": 3, "有限": 2, "輕微": 1.5, "輕微或受益": 1}
DMG_NAMES = ["重大", "有限", "輕微", "輕微或受益", "資料不足"]
STEP0_ORD = {"高": 3, "中": 2, "低": 1}

# KARST-214 裁決:無增長永續模型對高增長公司不可用 ⇒ 該等家的 q1 讀數剔出 q1 分析。
# 判準 = `q1_price_requires` 欄自己帶「不適用／不可用」標記(不改原檔,在此登記)。
Q1_TAG = {"不適用", "不可用"}

# ---- 表四:必要前提事後守住/被推翻(整欄為事後判斷,來源=模型既有知識,D-168 污染)----
# 值 = (守住/被推翻/查不到, 信心 高/中/低, 一句理由)
PREMISE = {
    ("E01", "T"): ("守住", "高", "季度派息 0.45 元維持並於 2014 年上調"),
    ("E01", "SPG"): ("守住", "中", "2013 全年 FFO 上升、指引未下調"),
    ("E01", "NLY"): ("被推翻", "中", "2013-06 宣布季度派息由 0.45 降至 0.40 元"),
    ("E01", "ED"): ("守住", "中", "季度股息維持、其後連年上調"),
    ("E02", "GILD"): ("被推翻", "高", "2016 年 HCV 產品收入大跌、指引下修"),
    ("E02", "BIIB"): ("守住", "中", "未見為保覆蓋而主動下調 MS 藥價"),
    ("E02", "REGN"): ("守住", "高", "EYLEA 美國銷售 2016 年仍按年增長"),
    ("E02", "JNJ"): ("守住", "中", "藥品分部佔收入比例在 10-K 有披露、查得到"),
    ("E03", "KR"): ("守住", "低", "毛利率按年跌幅未達 50bp 紅線"),
    ("E03", "UNFI"): ("被推翻", "中", "2018-02 全食超市宣布不再續約、採購安排確實有變"),
    ("E03", "SFM"): ("守住", "低", "同店銷售未轉負"),
    ("E03", "GIS"): ("守住", "中", "有機淨價實現未轉負"),
    ("E04", "ZM"): ("守住", "高", "FY2022 收入按年 +55%、遞延收入續增"),
    ("E04", "PTON"): ("被推翻", "高", "2021-11 起連續大幅下修指引、FY2022 收入轉跌"),
    ("E04", "TDOC"): ("守住", "高", "access 收入佔比與金額在一年內續升"),
    ("E04", "FSLY"): ("被推翻", "高", "2021 年第二季起收入增速跌穿 25%"),
    ("E05", "WAL"): ("被推翻", "高", "2023 年首兩季存款大額流出"),
    ("E05", "MCB"): ("守住", "中", "存款在 2023 年第二季起回穩"),
    ("E05", "ZION"): ("被推翻", "高", "2023 年第一季存款加速流失"),
    ("E05", "SCHW"): ("被推翻", "中", "客戶現金遷移延續至 2024 年"),
    ("E06", "KO"): ("守住", "高", "用藥人數未見一個數量級的躍升、KO 生意無損"),
    ("E06", "MDLZ"): ("守住", "低", "銷量走弱仍以加價彈性解讀、未見需求結構下移的證據"),
    ("E06", "DXCM"): ("守住", "中", "藥與連續監測在臨床用法上仍屬互補"),
    ("E06", "RMD"): ("守住", "中", "期內未見藥成為核准的睡眠呼吸中止療法"),
    ("E07", "NVDA"): ("守住", "高", "2025 年超大規模雲廠資本開支續增"),
    ("E07", "MU"): ("守住", "高", "HBM 供給約束與記憶體含量增長延續"),
    ("E07", "VRT"): ("守住", "高", "2025 年數據中心機櫃與電力建設未減速"),
    ("E07", "ANET"): ("守住", "中", "兩大客戶開支續增;白盒份額變化未見定論"),
    ("E08", "NKE"): ("守住", "中", "加價只做到部分轉嫁、毛利率明顯受壓"),
    ("E08", "RH"): ("被推翻", "低", "期內現金流進一步轉弱、不只是原地"),
    ("E08", "BBY"): ("守住", "中", "公司自述加價能力有限,其後亦未見成功加價而不損量"),
    ("E08", "AAPL"): ("被推翻", "中", "服務業務與整體毛利率守住、吸收了硬件端成本"),
    ("E09", "OXY"): ("被推翻", "高", "2015 至 2016 年大額減值、每桶現金邊際跌穿門檻"),
    ("E09", "RIG"): ("被推翻", "高", "合約積壓與超深水日費同跌"),
    ("E09", "HAL"): ("被推翻", "高", "2015 年收入按年大跌、北美經營收入轉負"),
    ("E09", "CVX"): ("被推翻", "高", "上游盈利跌幅遠超 25%"),
    ("E10", "FSLR"): ("守住", "低", "抵免日落表未被立法改動;專案取消未成潮"),
    ("E10", "RUN"): ("守住", "中", "稅務投資基金續關帳"),
    ("E10", "THC"): ("守住", "中", "呆帳撥備比率未升穿門檻、權益遠高於 4 億"),
    ("E10", "CNC"): ("守住", "高", "賠付率未升穿 89%、會員數續增"),
    ("E11", "META"): ("守住", "高", "2018 年廣告收入與每則廣告定價同升"),
    ("E11", "SNAP"): ("守住", "低", "收入增速大體維持、每用戶收入上升"),
    ("E12", "QCOM"): ("被推翻", "中", "授權關係未因清單中斷"),
    ("E12", "SWKS"): ("被推翻", "高", "FY2019 客戶集中度反而上升"),
    ("E12", "MU"): ("被推翻", "高", "FY2019 現金流自 FY2018 高位大幅回落"),
    ("E12", "LITE"): ("被推翻", "低", "華為佔比消失、其他客戶未見同額補上"),
    ("E13", "ASAN"): ("守住", "高", "十年息一年內由 1.6% 升至 3.5%"),
    ("E13", "BILL"): ("守住", "高", "同上"),
    ("E13", "DOCU"): ("守住", "高", "同上"),
    ("E13", "MSFT"): ("守住", "高", "同上"),
    ("E14", "CHGG"): ("守住", "高", "通用模型確實搶走新客、Chegg 收入其後連年下滑"),
    ("E14", "DUOL"): ("守住", "高", "Duolingo 2023 至 2025 收入續以四成以上增長"),
}

# ---- 表四補:前提的方向(逐家判斷,理由見總覽)-------------------------------
# D = 前提是「恐懼會成真」那一邊的條件 ⇒ 守住 = 損害成立
# S = 前提是「卡方看法」那一邊的條件 ⇒ 守住 = 損害不成立
# 由各卡「被推翻即整卡失效」一句的寫法定:講「損害鏈斷」= D,講「本卡的樂觀看法失效」= S。
PREMISE_DIR = {
    ("E08", "NKE"): "D", ("E08", "BBY"): "D", ("E08", "AAPL"): "D",
    ("E12", "QCOM"): "D", ("E12", "LITE"): "D",
    ("E13", "ASAN"): "D", ("E13", "BILL"): "D", ("E13", "DOCU"): "D", ("E13", "MSFT"): "D",
    ("E14", "CHGG"): "D",
}
# 其餘 42 家一律 S(前提寫成「某數字不跌穿／不轉負／指引不下修」,守住即卡方看法成立)。



def load_judged():
    rows = []
    for f in sorted(glob.glob(os.path.join(V3, "批*", "判-E*.csv"))):
        d = pd.read_csv(f)
        d["batch"] = os.path.basename(os.path.dirname(f))
        rows.append(d)
    j = pd.concat(rows, ignore_index=True)
    j["q1_verdict_raw"] = j["q1_verdict"].astype(str).str.strip()
    j["q1"] = j["q1_verdict_raw"].map(Q1_ALIAS)
    bad = j["q1"].isna()
    if bad.any():
        raise SystemExit("未對上的 q1_verdict 新寫法:%s" % j.loc[bad, "q1_verdict_raw"].unique())
    j["q1_ord"] = j["q1"].map(Q1_ORD)
    for c in ("dmg_true", "dmg_partial", "dmg_false"):
        j[c + "_ord"] = j[c].astype(str).str.strip().map(DMG_ORD)
    j["step0"] = j["step0_credibility"].astype(str).str.strip()
    j["step0_ord"] = j["step0"].map(STEP0_ORD)
    txt = j["q1_price_requires"].astype(str)
    j["q1_model_na"] = txt.apply(lambda s: any(t in s for t in Q1_TAG))
    j["premise_verdict"] = [PREMISE.get((e, t), ("查不到", "低", ""))[0]
                            for e, t in zip(j["event_id"], j["ticker"])]
    j["premise_conf"] = [PREMISE.get((e, t), ("查不到", "低", ""))[1]
                         for e, t in zip(j["event_id"], j["ticker"])]
    j["premise_note"] = [PREMISE.get((e, t), ("查不到", "低", ""))[2]
                         for e, t in zip(j["event_id"], j["ticker"])]
    j["premise_dir"] = [PREMISE_DIR.get((e, t), "S") for e, t in zip(j["event_id"], j["ticker"])]
    # 方向校正後的是非題:1 = 前提事後指向「損害成立」那一邊
    j["premise_damage"] = [
        (1.0 if v == "守住" else 0.0) if d == "D" else (1.0 if v == "被推翻" else 0.0)
        for v, d in zip(j["premise_verdict"], j["premise_dir"])
    ]
    return j


def load_members():
    m = pd.read_csv(MEMBERS)
    m.columns = [c.lstrip("﻿") for c in m.columns]
    for a in ("T", "N"):
        ok = m["%s_12m_status" % a].astype(str).str.strip() == "已成熟"
        m["%s_y" % a] = np.where(ok, m["%s_12m_excess" % a], np.nan)
    return m


def basket_medians(m):
    """籃子中位 = 該宗「新聞點名」成員(已成熟)的十二個月超額中位數。"""
    named = m[m["basket_kind"] == "新聞點名"]
    out = {}
    for e, g in named.groupby("event_id"):
        out[e] = {a: (float(g["%s_y" % a].median()), int(g["%s_y" % a].notna().sum()))
                  for a in ("T", "N")}
    sic = {}
    for e, g in m[m["basket_kind"] == "同SIC全體"].groupby("event_id"):
        sic[e] = {a: float(g["%s_y" % a].median()) for a in ("T", "N")}
    return out, sic


def merge_outcomes(j, m, bm):
    # basket_members 內同一代號可以同時在「新聞點名」與「同SIC全體」各佔一列,
    # 併結果前先去重,否則入卡家數會重複計算。
    keep = ["event_id", "ticker", "T_y", "N_y", "f_shock_rel_drop"]
    mm = m[keep].drop_duplicates(subset=["event_id", "ticker"])
    out = j.merge(mm, on=["event_id", "ticker"], how="left")
    for a in ("T", "N"):
        out["bm_%s" % a] = out["event_id"].map(lambda e, a=a: bm[e][a][0] if e in bm else np.nan)
        out["rel_%s" % a] = out["%s_y" % a] - out["bm_%s" % a]
    return out


def sp(x, y, label, note=""):
    x = pd.Series(list(x), dtype="float64")
    y = pd.Series(list(y), dtype="float64")
    m = x.notna() & y.notna()
    n = int(m.sum())
    if n < 3:
        return dict(欄=label, 家數=n, Spearman=np.nan, 註="家數過細,不下結論 " + note)
    rho, p = spearmanr(x[m], y[m])
    return dict(欄=label, 家數=n, Spearman=round(float(rho), 4), p值=round(float(p), 4),
                註=("家數過細,不下結論 " if n < MIN_N else "") + note)


def desc(s):
    s = pd.Series(list(s), dtype="float64").dropna()
    if not len(s):
        return dict(家數=0, 中位=np.nan, 平均=np.nan, 勝率=np.nan)
    return dict(家數=len(s), 中位=round(float(s.median()), 4),
                平均=round(float(s.mean()), 4), 勝率=round(float((s > 0).mean()), 4))


# ---------------------------------------------------------------- 表一
def table1(df, bm, sic):
    rows = []
    for e in sorted(bm):
        if e not in set(df["event_id"]):
            continue  # 199 事件表有籃子為空的宗;本回測只評三批做過的十四宗
        sub = df[df["event_id"] == e]
        r = dict(event_id=e, 步〇可信程度=sub["step0"].iloc[0] if len(sub) else "",
                 籃子家數=bm[e]["T"][1],
                 籃子中位_T=round(bm[e]["T"][0], 4), 籃子中位_N=round(bm[e]["N"][0], 4),
                 同SIC中位_T=round(sic.get(e, {}).get("T", np.nan), 4),
                 同SIC中位_N=round(sic.get(e, {}).get("N", np.nan), 4),
                 入卡家數=len(sub))
        rows.append(r)
    t1 = pd.DataFrame(rows)
    t1["_ord"] = t1["步〇可信程度"].map(STEP0_ORD)
    agg = []
    for lv in ("高", "中", "低"):
        s = t1[t1["步〇可信程度"] == lv]
        agg.append(dict(步〇可信程度=lv, 宗數=len(s),
                        T錨中位=round(float(s["籃子中位_T"].median()), 4) if len(s) else np.nan,
                        N錨中位=round(float(s["籃子中位_N"].median()), 4) if len(s) else np.nan))
    s = t1[t1["步〇可信程度"].isin(["高", "中", "低"])]
    corr = pd.DataFrame([
        sp(s["_ord"], s["籃子中位_T"], "步〇可信程度序數 vs 籃子中位(T 錨)"),
        sp(s["_ord"], s["籃子中位_N"], "步〇可信程度序數 vs 籃子中位(N 錨)"),
    ])
    return t1, pd.DataFrame(agg), corr


# ---------------------------------------------------------------- 表二
def dmg_table(df, anchor, tag):
    rows = []
    for col, name in (("dmg_true", "全真情境損害級"), ("dmg_false", "不成立情境損害級")):
        for lv in DMG_NAMES:
            sub = df[df[col].astype(str).str.strip() == lv]
            r = dict(樣本=tag, 錨=anchor, 欄=name, 損害級=lv)
            r.update(desc(sub["rel_%s" % anchor]))
            rows.append(r)
    return pd.DataFrame(rows)


def dmg_corr(df, tag):
    rows = []
    for anchor in ("T", "N"):
        for col, name in (("dmg_true", "全真情境損害級"), ("dmg_false", "不成立情境損害級")):
            rows.append(dict(樣本=tag, 錨=anchor,
                             **sp(df[col + "_ord"], df["rel_%s" % anchor],
                                  name, "相對籃子中位;預期負號")))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 表三
def table3(df):
    # KARST-214 裁甲:q1_price_requires 標「不可用/不適用」的家,q1 那一欄模型不成立
    # (高增長公司套「零增長永續」讀數),一律剔出本表的判詞分組與秩相關。
    d3 = df[~df["q1_model_na"]]
    na = df.loc[df["q1_model_na"], ["event_id", "ticker"]]
    note = "已剔模型不適用 %d 家:%s" % (
        len(na), "、".join("%s %s" % (e, t) for e, t in zip(na["event_id"], na["ticker"])))
    rows = [dict(錨="-", 判詞="__剔出__", 家數=len(na), 中位=np.nan, 平均=np.nan,
                 勝率=np.nan, 註=note)]
    for anchor in ("T", "N"):
        for v in ("更壞", "相稱", "更好", "資料不足"):
            sub = d3[d3["q1"] == v]
            r = dict(錨=anchor, 判詞=v)
            r.update(desc(sub["%s_y" % anchor]))
            r["註"] = note
            rows.append(r)
        r = dict(錨=anchor, 判詞="__全部__")
        r.update(desc(d3["%s_y" % anchor]))
        r["註"] = note
        rows.append(r)
    corr = []
    for anchor in ("T", "N"):
        for tag, sub in (("全樣本(含模型不適用者)", df),
                         ("剔模型不適用者(KARST-214 裁,主用)", d3)):
            corr.append(dict(樣本=tag, 錨=anchor,
                             **sp(sub["q1_ord"], sub["%s_y" % anchor],
                                  "便宜度序數 vs 個股十二個月超額", "預期正號")))
            corr.append(dict(樣本=tag, 錨=anchor,
                             **sp(sub["q1_ord"], sub["rel_%s" % anchor],
                                  "便宜度序數 vs 相對籃子中位", "預期正號")))
    return pd.DataFrame(rows), pd.DataFrame(corr)


# ---------------------------------------------------------------- 表四
def table4(df):
    rows, corr = [], []
    for anchor in ("T", "N"):
        for v in ("守住", "被推翻", "查不到"):
            sub = df[df["premise_verdict"] == v]
            r = dict(錨=anchor, 事後= v)
            r.update(desc(sub["%s_y" % anchor]))
            rr = dict(錨=anchor, 事後=v + "(相對籃子中位)")
            rr.update(desc(sub["rel_%s" % anchor]))
            rows.append(r); rows.append(rr)
    for anchor in ("T", "N"):
        sub = df[df["premise_verdict"].isin(["守住", "被推翻"])].copy()
        sub["_o"] = (sub["premise_verdict"] == "守住").astype(float)
        corr.append(dict(樣本="全樣本", 錨=anchor,
                         **sp(sub["_o"], sub["%s_y" % anchor], "前提守住=1 vs 十二個月超額",
                              "預期負號")))
        hi = sub[sub["premise_conf"] == "高"]
        corr.append(dict(樣本="只算高信心", 錨=anchor,
                         **sp(hi["_o"], hi["%s_y" % anchor], "前提守住=1 vs 十二個月超額",
                              "預期負號")))
        corr.append(dict(樣本="全樣本", 錨=anchor,
                         **sp(sub["_o"], sub["rel_%s" % anchor], "前提守住=1 vs 相對籃子中位",
                              "預期負號")))
        # 方向校正版:先按「這條前提是站在恐懼那一邊還是站在卡方那一邊」把非題對正,
        # 再問「事後指向損害成立」那組是否之後較差。
        for tag, s2 in (("方向校正 全樣本", sub), ("方向校正 只算高信心", sub[sub["premise_conf"] == "高"])):
            corr.append(dict(樣本=tag, 錨=anchor,
                             **sp(s2["premise_damage"], s2["%s_y" % anchor],
                                  "事後指向損害成立=1 vs 十二個月超額", "預期負號")))
            corr.append(dict(樣本=tag, 錨=anchor,
                             **sp(s2["premise_damage"], s2["rel_%s" % anchor],
                                  "事後指向損害成立=1 vs 相對籃子中位", "預期負號")))
    return pd.DataFrame(rows), pd.DataFrame(corr)


# ---------------------------------------------------------------- 表五
def v1_grades():
    g = {}
    for f in glob.glob(os.path.join(V1_DIR, "判-E*.csv")):
        for _, r in pd.read_csv(f).iterrows():
            g[(r["event_id"], r["ticker"])] = r["step5_grade"]
    return g


V1_ORD = {"高度適用": 3, "部分適用": 2, "大致不適用": 1, "資料不足": np.nan}
V21_ORD = {"重大損害": 3, "有限損害": 2, "影響輕微或受益": 1}


def table5(df):
    g = v1_grades()
    df = df.copy()
    df["v1_grade"] = [g.get((e, t)) for e, t in zip(df["event_id"], df["ticker"])]
    df["v1_ord"] = df["v1_grade"].map(V1_ORD)
    rows = []
    for anchor in ("T", "N"):
        rows.append(dict(版本="v1(KARST-204)敘事適用度四級", 錨=anchor,
                         **sp(df["v1_ord"], df["%s_y" % anchor], "適用度序數 vs 個股超額",
                              "預期負號(敘事越適用越差)")))
        rows.append(dict(版本="v3(KARST-215)步五全真損害級", 錨=anchor,
                         **sp(df["dmg_true_ord"], df["%s_y" % anchor], "全真損害序數 vs 個股超額",
                              "預期負號(損害越重越差)")))
        rows.append(dict(版本="v3(KARST-215)步五不成立損害級", 錨=anchor,
                         **sp(df["dmg_false_ord"], df["%s_y" % anchor], "不成立損害序數 vs 個股超額",
                              "預期負號")))
        rows.append(dict(版本="v3(KARST-215)q1 便宜度", 錨=anchor,
                         **sp(df[~df["q1_model_na"]]["q1_ord"],
                              df[~df["q1_model_na"]]["%s_y" % anchor],
                              "便宜度序數 vs 個股超額", "預期正號;已剔模型不適用 3 家")))
    # v2.1 十家(210 已算好,照錄;本票不重算)
    v21 = pd.DataFrame([
        dict(版本="v2.1(KARST-210)損害四級", 錨="T", 家數=10, Spearman=0.30,
             註="照錄 210 評分表;方向判反(210 原判)"),
        dict(版本="v2.1(KARST-210)步六現價對價值", 錨="T", 家數=10, Spearman=0.30,
             註="照錄 210 評分表;方向判反(210 原判)"),
        dict(版本="v2.1(KARST-210)必要前提守住", 錨="T", 家數=10, Spearman=float("nan"),
             註="照錄 210 表三:守住 +75.4% 對被推翻 −23.7%;210 判此步方向對"),
    ])
    return pd.concat([pd.DataFrame(rows), v21], ignore_index=True), df


# ---------------------------------------------------------------- 穩健度
TESTS = [
    ("表二 全真損害級 vs 相對籃中位", "dmg_true_ord", "rel_T", "T"),
    ("表二 全真損害級 vs 相對籃中位", "dmg_true_ord", "rel_N", "N"),
    ("表三 q1 便宜度 vs 個股超額", "q1_ord", "T_y", "T"),
    ("表三 q1 便宜度 vs 相對籃中位", "q1_ord", "rel_T", "T"),
    ("表四 前提守住 vs 個股超額", "premise_damage", "T_y", "T"),
]


def loo_event(t1):
    """表一的逐宗剔走:單位是宗(十四宗),不是家。"""
    rows = []
    for col in ("籃子中位_T", "籃子中位_N"):
        s = t1[t1["_ord"].notna()]
        base = sp(s["_ord"], s[col], "步〇可信程度序數 vs " + col)["Spearman"]
        vals = []
        for _, r in s.iterrows():
            sub = s[s["event_id"] != r["event_id"]]
            vals.append((r["event_id"], sp(sub["_ord"], sub[col], col)["Spearman"]))
        vals = [(e, v) for e, v in vals if pd.notna(v)]
        lo = min(vals, key=lambda kv: kv[1]); hi = max(vals, key=lambda kv: kv[1])
        rows.append(dict(測="表一 步〇可信程度 vs " + col, 錨=col[-1], 全樣本=base,
                         剔走後最低=lo[1], 剔走哪宗_最低=lo[0],
                         剔走後最高=hi[1], 剔走哪宗_最高=hi[0],
                         全負=all(v < 0 for _, v in vals),
                         全正=all(v > 0 for _, v in vals)))
    return pd.DataFrame(rows)


def loo(df):
    """逐宗剔走再算一次:看某一個宗是否獨力撐起結論(十四宗即有效樣本上限)。"""
    rows = []
    for name, xs, ys, anchor in TESTS:
        d0 = df[~df["q1_model_na"]] if xs == "q1_ord" else df
        base = sp(d0[xs], d0[ys], name)["Spearman"]
        vals = []
        for e in sorted(d0["event_id"].unique()):
            sub = d0[d0["event_id"] != e]
            r = sp(sub[xs], sub[ys], name)["Spearman"]
            vals.append((e, r))
        vals = [(e, v) for e, v in vals if pd.notna(v)]
        if not vals:
            continue
        lo = min(vals, key=lambda kv: kv[1]); hi = max(vals, key=lambda kv: kv[1])
        rows.append(dict(測=name, 錨=anchor, 全樣本=base,
                         剔走後最低=lo[1], 剔走哪宗_最低=lo[0],
                         剔走後最高=hi[1], 剔走哪宗_最高=hi[0],
                         全負=all(v < 0 for _, v in vals),
                         全正=all(v > 0 for _, v in vals)))
    return pd.DataFrame(rows)


def crosstab(df):
    return pd.crosstab(df[~df["q1_model_na"]]["q1"],
                       df[~df["q1_model_na"]]["dmg_true"])


def main():
    df = load_judged()
    m = load_members()
    bm, sic = basket_medians(m)
    df = merge_outcomes(df, m, bm)

    os.makedirs(BASE, exist_ok=True)
    df.to_csv(os.path.join(BASE, "評分明細.csv"), index=False, encoding="utf-8-sig")

    t1, t1a, t1c = table1(df, bm, sic)
    t2 = pd.concat([dmg_table(df[df["step0"] == "高"], "T", "步〇高"),
                    dmg_table(df[df["step0"] == "高"], "N", "步〇高"),
                    dmg_table(df[df["step0"].isin(["中", "低"])], "T", "步〇低/中"),
                    dmg_table(df[df["step0"].isin(["中", "低"])], "N", "步〇低/中")],
                   ignore_index=True)
    t2c = pd.concat([dmg_corr(df[df["step0"] == "高"], "步〇高"),
                     dmg_corr(df[df["step0"].isin(["中", "低"])], "步〇低/中"),
                     dmg_corr(df, "全樣本")], ignore_index=True)
    t3, t3c = table3(df)
    t4, t4c = table4(df)
    t5, dfall = table5(df)

    tl = pd.concat([loo_event(t1), loo(df)], ignore_index=True)
    ct = crosstab(df)

    # 評分表.csv:五張表合成一檔(長格式),供機械讀者一次取齊
    def long(name, d):
        d = d.copy()
        d.insert(0, "表", name)
        d.insert(1, "區塊", "")
        return d
    blocks = [
        long("表一 逐宗", t1), long("表一 三檔合計", t1a), long("表一 秩相關", t1c),
        long("表二 損害級", t2), long("表二 秩相關", t2c),
        long("表三 q1判詞", t3), long("表三 秩相關", t3c),
        long("表四 必要前提", t4), long("表四 秩相關", t4c),
        long("表五 三版方向", t5), long("穩健 逐宗剔走", tl),
    ]
    pd.concat(blocks, ignore_index=True).to_csv(
        os.path.join(BASE, "評分表.csv"), index=False, encoding="utf-8-sig")

    files = {"表一_步〇對籃子.csv": t1, "表一_三檔合計.csv": t1a, "表一_秩相關.csv": t1c,
             "表二_損害級對相對籃中位.csv": t2, "表二_秩相關.csv": t2c,
             "表三_q1判詞對超額.csv": t3, "表三_秩相關.csv": t3c,
             "表四_必要前提.csv": t4, "表四_秩相關.csv": t4c,
             "表五_三版方向.csv": t5, "表五_逐家明細.csv": dfall,
             "穩健_逐宗剔走.csv": tl}
    for name, d in files.items():
        d.to_csv(os.path.join(BASE, name), index=False, encoding="utf-8-sig")

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    for name, d in (("表一 逐宗", t1), ("表一 三檔合計", t1a), ("表一 秩相關", t1c),
                    ("表二 損害級", t2), ("表二 秩相關", t2c),
                    ("表三 判詞", t3), ("表三 秩相關", t3c),
                    ("表四 必要前提", t4), ("表四 秩相關", t4c),
                    ("表五 三版方向", t5), ("穩健 逐宗剔走", tl)):
        print("\n== %s ==" % name)
        print(d.to_string(index=False))
    print("\n== q1 判詞 × 全真損害級 ==")
    print(ct.to_string())
    print("\n== 判詞寫法對照 ==")
    print(df.groupby(["batch", "q1_verdict_raw", "q1"]).size().to_string())
    print("\n== 模型不適用(q1 剔出)==")
    print(df[df["q1_model_na"]][["event_id", "ticker", "q1", "q1_price_requires"]].to_string(index=False))
    print("\n== 必要前提信心分佈 ==")
    print(df.groupby(["premise_verdict", "premise_conf"]).size().to_string())


if __name__ == "__main__":
    main()
