# -*- coding: utf-8 -*-
"""KARST-199 第三步:事前可辨特徵單變量對照。

問題:同一個籃子裡,十二個月後的贏家與輸家,在衝擊日之前有沒有可見分別?

做法(刻意樸素,不建模型):
  - 只用衝擊日之前已公布(filed_date <= 衝擊起日)的公開資料;
  - **一律在事件之內比較**——跨事件直接混池會把「哪一年市況好」量成「特徵有效」;
  - 每條特徵各自出:事件內三分位對照表、事件內等級相關、事件內 AUC(贏家 = 該事件內超額高於中位)。

輸出:out/feature_univariate.csv、out/feature_terciles.csv、out/feature_coverage.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from basket_core import OUT, log

FEATURES = {
    "f_shock_rel_drop": "衝擊期自身相對大市跌幅(越負跌越深)",
    "f_log_mcap": "市值(對數)",
    "f_net_cash_over_mcap": "淨現金(現金−總債務)÷市值",
    "f_debt_to_assets": "總債務÷總資產",
    "f_liab_to_assets": "總負債÷總資產",
    "f_ocf_positive": "四季經營現金流為正(1/0)",
    "f_ocf_margin": "經營現金流利潤率(定價力代理)",
    "f_ni_margin": "淨利率",
    "f_ps": "市銷率 P/S",
    "f_pb": "市帳率 P/B",
    "f_pe": "市盈率 P/E(只在盈利為正時算得出)",
    "f_rev_growth_yoy": "營收按年增長(TTM 對 TTM)",
    "f_rev_cv8": "過去八格營收變異係數(經常性收入的反向代理)",
}

MIN_PER_EVENT = 5   # 一個事件內少於這麼多家有值就不參與該條特徵


def event_auc(x: np.ndarray, y: np.ndarray):
    """事件內 AUC:y 是 0/1 贏家標籤。回 (auc, n_pairs)。"""
    pos, neg = x[y == 1], x[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan, 0
    r = stats.rankdata(np.concatenate([pos, neg]))
    auc = (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))
    return float(auc), int(len(pos) * len(neg))


def main() -> None:
    mem = pd.read_csv(OUT / "basket_members.csv", low_memory=False)
    ev = pd.read_csv(OUT / "event_list.csv")
    main_ids = set(ev[ev["in_main_sample"] == True]["event_id"])

    log(f"成員 {len(mem)} 列,主樣本事件 {len(main_ids)} 宗")

    uni_rows, terc_rows, cov_rows = [], [], []

    combos = [(k, tag, an) for k in ("新聞點名", "同SIC全體")
              for tag, an in (("T", "衝擊低點"), ("N", "衝擊結束日(新聞)"))]
    for kind, tag, aname_ in combos:
        aname = f"{kind}／{aname_}"
        col = f"{tag}_12m_excess"
        d = mem[(mem["basket_kind"] == kind) & mem["event_id"].isin(main_ids) & mem[col].notna()].copy()
        if len(d) == 0:
            continue
        # 事件內中位切贏輸
        d["_evmed"] = d.groupby("event_id")[col].transform("median")
        d["_win"] = (d[col] > d["_evmed"]).astype(int)
        cov_rows.append(dict(口徑=aname, 有十二個月成熟結果的成員數=len(d),
                             事件數=d["event_id"].nunique()))

        for f, label in FEATURES.items():
            sub = d[d[f].notna()].copy()
            if len(sub) == 0:
                uni_rows.append(dict(口徑=aname, 特徵=label, 欄名=f, 可用成員=0, 參與事件=0,
                                     判詞="無資料"))
                continue
            # 只留事件內有足夠家數的事件
            cnt = sub.groupby("event_id")[f].transform("size")
            sub = sub[cnt >= MIN_PER_EVENT]
            if sub["event_id"].nunique() < 3:
                uni_rows.append(dict(口徑=aname, 特徵=label, 欄名=f, 可用成員=int(len(sub)),
                                     參與事件=int(sub["event_id"].nunique()), 判詞="事件數不足三宗,量不出"))
                continue

            rhos, aucs, wts = [], [], []
            for evid, g in sub.groupby("event_id"):
                if g[f].nunique() < 2:
                    continue
                rho = stats.spearmanr(g[f], g[col]).statistic
                if np.isfinite(rho):
                    rhos.append(rho)
                a, np_ = event_auc(g[f].to_numpy(float), g["_win"].to_numpy())
                if np.isfinite(a):
                    aucs.append(a)
                    wts.append(np_)
            if not aucs:
                uni_rows.append(dict(口徑=aname, 特徵=label, 欄名=f, 可用成員=int(len(sub)),
                                     參與事件=int(sub["event_id"].nunique()), 判詞="算不出"))
                continue
            auc_w = float(np.average(aucs, weights=wts))
            rho_m = float(np.mean(rhos)) if rhos else np.nan
            # 事件內三分位
            sub["_terc"] = sub.groupby("event_id")[f].transform(
                lambda s: pd.qcut(s.rank(method="first"), 3, labels=["低", "中", "高"])
                if s.nunique() >= 3 else pd.Series(["中"] * len(s), index=s.index))
            for t_, g in sub.groupby("_terc", observed=True):
                terc_rows.append(dict(口徑=aname, 特徵=label, 欄名=f, 三分位=str(t_), n=int(len(g)),
                                      中位十二個月超額=round(float(g[col].median()), 4),
                                      平均十二個月超額=round(float(g[col].mean()), 4),
                                      贏家比例=round(float((g[col] > 0).mean()), 4)))
            hi = sub[sub["_terc"] == "高"][col]
            lo = sub[sub["_terc"] == "低"][col]
            gap = float(hi.median() - lo.median()) if len(hi) and len(lo) else np.nan
            # 判詞:AUC 離 0.5 多遠、事件之間一不一致
            consistent = float(np.mean([a > 0.5 for a in aucs])) if aucs else np.nan
            if abs(auc_w - 0.5) < 0.05:
                verdict = "分不開"
            elif consistent >= 0.7 or consistent <= 0.3:
                verdict = "分得開,方向在事件之間一致"
            else:
                verdict = "整體有訊號但事件之間方向不一致(當分不開)"
            uni_rows.append(dict(
                口徑=aname, 特徵=label, 欄名=f, 可用成員=int(len(sub)),
                參與事件=int(sub["event_id"].nunique()),
                事件內AUC加權=round(auc_w, 4),
                事件內AUC逐宗大於半數比例=round(consistent, 3),
                事件內等級相關均值=round(rho_m, 4) if np.isfinite(rho_m) else np.nan,
                高分位減低分位中位超額=round(gap, 4) if np.isfinite(gap) else np.nan,
                判詞=verdict))

    pd.DataFrame(uni_rows).to_csv(OUT / "feature_univariate.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(terc_rows).to_csv(OUT / "feature_terciles.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(cov_rows).to_csv(OUT / "feature_coverage.csv", index=False, encoding="utf-8-sig")
    log("完成:feature_univariate.csv / feature_terciles.csv / feature_coverage.csv")


if __name__ == "__main__":
    main()
