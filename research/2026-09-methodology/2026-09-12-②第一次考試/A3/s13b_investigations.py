# -*- coding: utf-8 -*-
"""KARST-226 票 A″(執行口徑 v1.2 第 10 項)三項調查 → `cache/investigations.json`。

  一、A2(上一次建池)290 宗「無 XBRL 數列」的原因分類(三類)。
  二、`adr_flag` 幾乎全 1 的原因(來源欄 + 邏輯錯)。
  三、Item 1.01 舊閘誤剔數(v1.1 任何同日 1.01 即剔 → v1.2 要正文有併購字眼才剔)。

只讀;不印公司名或代號。執行紀錄的數字由本檔產生,人手抄進去。
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
A2 = HERE.parent / "A2"
ROOT = Path(r"C:\projects\Karst")


def main() -> None:
    out: dict = {}
    a2 = pd.read_parquet(A2 / "cache" / "population_improvement.parquet")
    a2ep = a2[(a2["pass_p90"] == 1)
              & (a2["improvement_type"].isin(["加速", "指引", "兩者"]))
              & (a2["excl_going_concern"] != "有")]

    # ---------- 一、290 宗無 XBRL 數列 ----------
    st = a2ep["xbrl_status"].astype(str)
    bad = a2ep[st.str.len() > 0]
    out["1_a2_no_xbrl_series"] = {
        "A2 入口池": int(len(a2ep)),
        "無可用 XBRL 季度數列": int(len(bad)),
        "三類原因": {k: int(v) for k, v in collections.Counter(
            bad["xbrl_status"]).most_common()},
        "這批的 improvement_type": {k: int(v) for k, v in
                                collections.Counter(bad["improvement_type"]).items()},
        "說明": "三者都令『季度收入序列』算不出:（甲）companyfacts 有檔但申報日前 120 日內"
              "找不到單季收入期末(多為財年末季只以年報申報、或 20-F 外國申報者);"
              "（乙）有單季但缺去年同季,算不出 g0;（丙）只報累計數(YTD),無單季事實。",
        "A3 的處理": "v1.2 第 3 步加「財年末季 = 年報(340–380 日)− 同期 9 個月累計」推算,"
                 "甲類大減;適用性 F 的三類原因(標籤缺/季度轉換失敗/真無披露)正是同一批"
                 "原因在 A3 的寫法,不再只寫一句「無數列」。",
    }
    a3 = pd.read_parquet(CACHE / "population_improvement.parquet")
    ar = a3["applicability_reason"].fillna("")
    out["1_a2_no_xbrl_series"]["A3 適用性 F 三類(全母體)"] = {
        k: int(v) for k, v in ar[ar != ""].value_counts().items()}
    out["1_a2_no_xbrl_series"]["A3 適用性 F 三類(入口池內)"] = {
        k: int(v) for k, v in ar[a3["entry_pool"] == 1].value_counts().items()}

    # ---------- 二、adr_flag ----------
    ent = pd.read_parquet(ROOT / "data" / "universe" / "entities.parquet")
    ctry = ent["country"].fillna("").astype(str)
    picks = json.loads((A2 / "cache" / "picks.json").read_text(encoding="utf-8"))
    accs = [p["acc"] for p in picks["main"]] + [p["acc"] for p in picks["backup"]]
    sub = a2[a2["accessionNumber"].isin(accs)]
    cik2ff = dict(zip(ent["entity_id"], ent["is_foreign_filer"]))
    true_ff = sum(1 for c in sub["cik"] if bool(cik2ff.get(str(c).zfill(10), False)))
    a3sub = a3[a3["entry_pool"] == 1]
    a3_true_ff = sum(1 for c in a3sub["cik"]
                     if bool(cik2ff.get(str(c).zfill(10), False)))
    out["2_adr_flag"] = {
        "來源欄": "data/universe/entities.parquet 的 country 與 is_foreign_filer",
        "寫法(s4_assemble.py)":
            "adr_flag = 1 若 is_foreign_filer 為真 **或** country 不等於 \"US\"",
        "邏輯錯": "entities.country 對美國公司填的是**註冊州代碼**(CA/NY/TX/FL/MA/PA/IL/NJ…),"
                "不是國名或 ISO 國碼;故 `country.ne(\"US\")` 幾乎恆真,把絕大多數美國公司"
                "都標成 adr_flag=1。正確做法是用 is_foreign_filer(該欄是券商/交易所口徑的"
                "外國申報者旗標),state_of_incorporation 才是州。",
        "entities_country_等於_US_的家數": int((ctry == "US").sum()),
        "entities 總家數": int(len(ent)),
        "entities_is_foreign_filer_真": int(ent["is_foreign_filer"].fillna(False).sum()),
        "country_值分佈前12": {k: int(v) for k, v in collections.Counter(
            ctry).most_common(12)},
        "A2 母體 adr_flag=1 的比例": "%d / %d" % (int(a2["adr_flag"].sum()), len(a2)),
        "A2 抽中 128 宗 adr_flag=1": int(sub["adr_flag"].sum()),
        "A2 抽中 128 宗真正外國申報者(is_foreign_filer)": int(true_ff),
        "A3 入口池 adr_flag=1": int(a3sub["adr_flag"].sum()),
        "A3 入口池真正外國申報者": int(a3_ff := a3_true_ff),
        "處置": "本輪**不改**(改 adr_flag 會動到宇宙與池,而它不入任何閘、不入入池判);"
              "若要當篩選欄用,須先重定義為 is_foreign_filer,並重跑逐事件欄位。",
    }

    # ---------- 三、Item 1.01 舊閘誤剔 ----------
    old = a3["excl_merger_1_01_old"] == 1
    new = a3["excl_merger_1_01"] == 1
    wrong = a3[old & ~new]
    out["3_item_1_01_old_gate"] = {
        "舊閘(v1.1)寫法": "同日(含自身)任何 8-K 帶 Item 1.01 即剔",
        "新閘(v1.2)寫法": "同日 8-K 帶 Item 2.01,或帶 Item 1.01 **且正文**含 "
                     "merger / acquisition / agreement and plan of merger / acquire",
        "舊閘會剔的母體事件數": int(old.sum()),
        "新閘實際剔的母體事件數": int(new.sum()),
        "舊閘會誤剔(新閘不剔)的母體事件數": int(len(wrong)),
        "其中宇宙內": int((wrong["in_universe"] == 1).sum()),
        "其中落在 2015 後池窗": int((wrong["in_pool_window"] == 1).sum()),
        "其中最終入池": int((wrong["entry_pool"] == 1).sum()),
        "正文未抓到、未能判定的(保守不剔)": int(a3["merger_text_pending"].sum()),
        "A2(v1.1)母體被舊閘剔的數": int((a2["excl_merger_1_01"] == 1).sum()),
        "說明": "「誤剔」＝同日有 1.01 但正文查無併購字眼者:多為信貸/合作/租約類 1.01,"
              "與併購無關。v1.2 這批不再剔;真正併購者(正文有字眼)照剔。",
    }

    # ---------- 其他供執行紀錄抄的數 ----------
    imp = a3
    cand = (imp["in_universe"] == 1) & imp["in_pool_window"] & (imp["pass_thr"] == True)  # noqa: E712
    out["4_other_counts"] = {
        "疑更早公開(前一日|報酬|>8%)": int((imp["excl_earlier_release"] == 1).sum()),
        "疑更早公開(在宇宙內)": int(((imp["excl_earlier_release"] == 1)
                              & (imp["in_universe"] == 1)).sum()),
        "訊號季收入不在稿內(候選層才真檢)": int((imp["excl_no_text"] == 1).sum()),
        "歷史季度未於 T1 前申報(全母體旗標)": int((imp["excl_hist_not_public"] == 1).sum()),
        "公開時段分佈(候選層)": {k: int(v) for k, v in
                         imp.loc[cand, "release_timing"]
                         .value_counts(dropna=False).items()},
        "T0 來源分佈(候選層)": {k: int(v) for k, v in
                          imp.loc[cand, "t0_source"]
                          .value_counts(dropna=False).items()},
        "盤中發布(候選層)": int(imp.loc[cand, "excl_intraday"].sum()),
        "候選層事件數": int(cand.sum()),
        "候選層_稿內無訊號季收入": int((imp.loc[cand, "excl_no_text"] == 1).sum()),
        "候選層_疑更早公開": int((imp.loc[cand, "excl_earlier_release"] == 1).sum()),
        "候選層_歷史季度未於T1前申報": int((imp.loc[cand, "excl_hist_not_public"] == 1).sum()),
        "候選層_適用性F不通過": int((imp.loc[cand, "excl_applicability"] == 1).sum()),
        "候選層_金融SIC": int((imp.loc[cand, "excl_financial_sic"] == 1).sum()),
        "候選層_全部排除理由命中的事件數": int(
            (imp.loc[cand, ["excl_no_text", "excl_intraday", "excl_earlier_release",
                            "excl_hist_not_public", "excl_applicability",
                            "excl_financial_sic"]].sum(axis=1) > 0).sum()),
    }
    (CACHE / "investigations.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
