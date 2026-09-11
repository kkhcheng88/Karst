# -*- coding: utf-8 -*-
"""KARST-221 第二步:用修後市值只重算市銷率(f_ps)與市帳率(f_pb)兩條事前特徵。

修後市值 = 未除息還原收市價 close(t) × 申報封面頁股數 × Π(申報日後的拆股比率)
(KARST-219 查明根因、KARST-221 入 basket_core.py 生產者碼;此檔只呼叫,不改核心。)

做法與 KARST-199 的 feature_table.py 逐字一致:事件內三分位、事件內 AUC、事件內等級相關,
同一個主樣本、同一個 MIN_PER_EVENT、同一組欄名。**原檔一律不改**,新結果另存
out/feature_terciles_mcap修正.csv、out/feature_univariate_mcap修正.csv,
行級市值與兩條特徵存 out/市值與兩條特徵_行級_mcap修正.csv。

用法:PYTHONUTF8=1 python "重出——199市值修正後兩條特徵.py"
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "2026-09-12-暴露差異模組v1"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(MOD))

import basket_core as bc  # noqa: E402
from verify_mcap_patch import lean_calendar, lean_raw_close  # noqa: E402

FEATS = {"f_ps": "市銷率 P/S", "f_pb": "市帳率 P/B"}
MIN_PER_EVENT = 5


def event_auc(x: np.ndarray, y: np.ndarray):
    """事件內 AUC:y 是 0/1 贏家標籤。回 (auc, n_pairs)。與 feature_table.py 相同。"""
    pos, neg = x[y == 1], x[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return np.nan, 0
    r = stats.rankdata(np.concatenate([pos, neg]))
    auc = (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))
    return float(auc), int(len(pos) * len(neg))


def recompute(mem: pd.DataFrame, ev: pd.DataFrame) -> pd.DataFrame:
    """逐行用修後市值重算 mcap_usd / f_ps / f_pb(知情時點 = 衝擊起日對齊 SPY 日曆,同 build_baskets)。"""
    spy = bc.load_spy()
    cal = lean_calendar(spy)
    need = set(mem["entity_id"].dropna().astype(str))
    bc._RAW_CLOSE = lean_raw_close(need)
    bc.log("日曆 %d 日;價格快取 entity %d 家" % (len(cal), len(bc._RAW_CLOSE)))

    shock = dict(zip(ev["event_id"], pd.to_datetime(ev["shock_start"])))
    pf = bc.PanelFeatures()
    rows = []
    for r in mem.itertuples(index=False):
        e = r.entity_id
        if not isinstance(e, str) or e not in need:
            rows.append((np.nan, np.nan, np.nan, np.nan, "無實體"))
            continue
        t = shock.get(r.event_id)
        i0 = int(cal.searchsorted(t, side="left"))
        t0 = cal[i0] if i0 < len(cal) else t
        a = pf.at(e, t0, None, bc.raw_close_asof(e, t0))
        rows.append((a.get("mcap_usd", np.nan), a.get("f_ps", np.nan), a.get("f_pb", np.nan),
                     a.get("f_log_mcap", np.nan), a.get("mcap_status", "")))
    out = pd.DataFrame(rows, columns=["mcap_usd_修後", "f_ps_修後", "f_pb_修後",
                                      "f_log_mcap_修後", "mcap_status_修後"])
    base = mem[["event_id", "basket_kind", "entity_id", "ticker",
                "T_12m_excess", "N_12m_excess", "dollar_vol_60d",
                "f_ocf_margin", "f_ni_margin"]].reset_index(drop=True)
    return pd.concat([base, out], axis=1)


def analyse(new: pd.DataFrame, ev: pd.DataFrame):
    """照 feature_table.py 的做法,只跑 f_ps / f_pb 兩條。"""
    new = new.rename(columns={"f_ps_修後": "f_ps", "f_pb_修後": "f_pb"})
    main_ids = set(ev[ev["in_main_sample"] == True]["event_id"])
    uni_rows, terc_rows = [], []
    combos = [(k, tag, an) for k in ("新聞點名", "同SIC全體")
              for tag, an in (("T", "衝擊低點"), ("N", "衝擊結束日(新聞)"))]
    for kind, tag, aname_ in combos:
        aname = f"{kind}／{aname_}"
        col = f"{tag}_12m_excess"
        d = new[(new["basket_kind"] == kind) & (new["event_id"].isin(main_ids)) & new[col].notna()].copy()
        if len(d) == 0:
            continue
        d["_evmed"] = d.groupby("event_id")[col].transform("median")
        d["_win"] = (d[col] > d["_evmed"]).astype(int)
        for f, label in FEATS.items():
            sub = d[d[f].notna()].copy()
            if len(sub) == 0:
                uni_rows.append(dict(口徑=aname, 特徵=label, 欄名=f, 可用成員=0, 參與事件=0, 判詞="無資料"))
                continue
            cnt = sub.groupby("event_id")[f].transform("size")
            sub = sub[cnt >= MIN_PER_EVENT]
            if sub["event_id"].nunique() < 3:
                uni_rows.append(dict(口徑=aname, 特徵=label, 欄名=f, 可用成員=int(len(sub)),
                                     參與事件=int(sub["event_id"].nunique()), 判詞="事件數不足三宗,量不出"))
                continue
            rhos, aucs, wts = [], [], []
            for _evid, g in sub.groupby("event_id"):
                if g[f].nunique() < 2:
                    continue
                rho = stats.spearmanr(g[f], g[col]).statistic
                if np.isfinite(rho):
                    rhos.append(rho)
                a, np_ = event_auc(g[f].to_numpy(float), g["_win"].to_numpy())
                if np.isfinite(a):
                    aucs.append(a)
                    wts.append(np_)
            auc_w = float(np.average(aucs, weights=wts))
            rho_m = float(np.mean(rhos)) if rhos else np.nan
            sub["_terc"] = sub.groupby("event_id")[f].transform(
                lambda s: pd.qcut(s.rank(method="first"), 3, labels=["低", "中", "高"])
                if s.nunique() >= 3 else pd.Series(["中"] * len(s), index=s.index))
            for t_, g in sub.groupby("_terc", observed=True):
                terc_rows.append(dict(口徑=aname, 特徵=label, 欄名=f, 三分位=str(t_), n=int(len(g)),
                                      中位十二個月超額=round(float(g[col].median()), 4),
                                      平均十二個月超額=round(float(g[col].mean()), 4),
                                      贏家比例=round(float((g[col] > 0).mean()), 4)))
            hi, lo = sub[sub["_terc"] == "高"][col], sub[sub["_terc"] == "低"][col]
            gap = float(hi.median() - lo.median()) if len(hi) and len(lo) else np.nan
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
    return pd.DataFrame(uni_rows), pd.DataFrame(terc_rows)


def three_questions(new: pd.DataFrame, ev: pd.DataFrame) -> pd.DataFrame:
    """附錄(票面範圍以外,但 199 的「三條問題」表其中一條就是市銷率,故一併量):
    照 variance_split.py 的做法重砌一遍。同 SIC 籃子照原法加成交額 ≥ 100 萬美元閘。"""
    new = new.rename(columns={"f_ps_修後": "f_ps"})
    main_ids = set(ev[ev["in_main_sample"] == True]["event_id"])
    col = "T_12m_excess"
    rows = []
    for kind in ("新聞點名", "同SIC全體"):
        d = new[(new["basket_kind"] == kind) & (new["event_id"].isin(main_ids)) & new[col].notna()].copy()
        if kind == "同SIC全體":
            d = d[d["dollar_vol_60d"] >= 1e6]
        d = d.dropna(subset=["f_ocf_margin", "f_ni_margin", "f_ps"])
        if len(d) < 20:
            continue
        for c, q in (("f_ocf_margin", "q1"), ("f_ni_margin", "q2")):
            d[q] = d.groupby("event_id")[c].transform(lambda s: s > s.median()).astype(int)
        d["q3"] = d.groupby("event_id")["f_ps"].transform(lambda s: s < s.median()).astype(int)
        d["score"] = d["q1"] + d["q2"] + d["q3"]
        for sc, g in d.groupby("score"):
            rows.append(dict(籃子=kind, 三條中幾條=int(sc), n=int(len(g)),
                             事件數=int(g["event_id"].nunique()),
                             中位十二個月超額=round(float(g[col].median()), 4),
                             平均十二個月超額=round(float(g[col].mean()), 4),
                             贏家比例=round(float((g[col] > 0).mean()), 4)))
        rows.append(dict(籃子=kind, 三條中幾條=-1, n=int(len(d)),
                         事件數=int(d["event_id"].nunique()),
                         中位十二個月超額=round(float(d[col].median()), 4),
                         平均十二個月超額=round(float(d[col].mean()), 4),
                         贏家比例=round(float((d[col] > 0).mean()), 4)))
    return pd.DataFrame(rows)


def main() -> None:
    mem = pd.read_csv(bc.OUT / "basket_members.csv", low_memory=False, dtype={"entity_id": str})
    ev = pd.read_csv(bc.OUT / "event_list.csv")
    bc.log("成員 %d 列" % len(mem))

    new = recompute(mem, ev)
    new.to_csv(bc.OUT / "市值與兩條特徵_行級_mcap修正.csv", index=False, encoding="utf-8-sig")
    old_ps = pd.to_numeric(mem["f_ps"], errors="coerce")
    bc.log("f_ps 修前有值 %d,修後有值 %d;修後新增 %d,修後失值 %d" % (
        int(old_ps.notna().sum()), int(new["f_ps_修後"].notna().sum()),
        int((old_ps.isna() & new["f_ps_修後"].notna()).sum()),
        int((old_ps.notna() & new["f_ps_修後"].isna()).sum())))

    uni, terc = analyse(new, ev)
    uni.to_csv(bc.OUT / "feature_univariate_mcap修正.csv", index=False, encoding="utf-8-sig")
    terc.to_csv(bc.OUT / "feature_terciles_mcap修正.csv", index=False, encoding="utf-8-sig")
    new.to_csv(bc.OUT / "市值與兩條特徵_行級_mcap修正.csv", index=False, encoding="utf-8-sig")

    # 修前修後並排(三分位中位 + 贏家比例)
    old_terc = pd.read_csv(bc.OUT / "feature_terciles.csv")
    old_uni = pd.read_csv(bc.OUT / "feature_univariate.csv")
    keep = ("口徑", "特徵", "欄名", "三分位")
    o = old_terc[old_terc["欄名"].isin(FEATS)][list(keep) + ["n", "中位十二個月超額", "贏家比例"]]
    n_ = terc[list(keep) + ["n", "中位十二個月超額", "贏家比例"]]
    j = o.merge(n_, on=list(keep), how="outer", suffixes=("_修前", "_修後"))
    j = j.sort_values(["口徑", "欄名", "三分位"])
    j.to_csv(bc.OUT / "對照_三分位_修前修後_mcap修正.csv", index=False, encoding="utf-8-sig")
    ou = old_uni[old_uni["欄名"].isin(FEATS)][
        ["口徑", "欄名", "可用成員", "參與事件", "事件內AUC加權",
         "事件內AUC逐宗大於半數比例", "判詞"]]
    ju = ou.merge(uni[["口徑", "欄名", "事件內AUC加權", "事件內AUC逐宗大於半數比例", "判詞"]],
                  on=["口徑", "欄名"], how="outer", suffixes=("_修前", "_修後"))
    ju.to_csv(bc.OUT / "對照_AUC_修前修後_mcap修正.csv", index=False, encoding="utf-8-sig")

    # 附錄:三條問題表(其中一條是市銷率,故受今次修正影響)
    tq = three_questions(new, ev)
    tq.to_csv(bc.OUT / "three_questions_mcap修正.csv", index=False, encoding="utf-8-sig")
    old_tq = pd.read_csv(bc.OUT / "three_questions.csv")
    jt = old_tq.merge(tq, on=["籃子", "三條中幾條"], how="outer", suffixes=("_修前", "_修後"))
    jt.sort_values(["籃子", "三條中幾條"]).to_csv(
        bc.OUT / "對照_三條問題_修前修後_mcap修正.csv", index=False, encoding="utf-8-sig")
    bc.log("完成:新檔已寫入 out/(原檔未動)")


if __name__ == "__main__":
    main()
