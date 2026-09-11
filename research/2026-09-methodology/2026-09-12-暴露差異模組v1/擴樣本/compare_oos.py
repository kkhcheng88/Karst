# -*- coding: utf-8 -*-
"""KARST-220 擴樣本三組對照(E21–E25 新五宗 + 218 四宗 + 216 開發七宗)。

== 這張票要答的一條問題 ==
把 KARST-218 的四宗樣本外擴到十宗以上,清單的「有限暴露」判斷相對三個簡單篩選
(跌得最少 / 財務簡篩 / 低波動)還有沒有增量,增量多大、穩不穩、落在哪一類事件。

== 挑法 ==
(a) 清單有限暴露 —— 照 `判-E*.csv` / `評分明細.csv` 的 `dmg_true == 有限` 錄,不重挑。
(b) 跌得最少 —— `f_shock_rel_drop` 最大。
(c) 財務簡篩 —— 衝擊前滾動四季經營現金流為正,再取最近八季營收變異係數最低。
(d) 低波動 —— 衝擊起日之前 252 個交易日(SPY 日曆)日回報標準差最低。
k = 該宗清單判為「有限」的家數;k = 0 則四臂一齊記空,不補位。

**E17–E20 與 E01–E20 之中主樣本七宗的 (b)(c)(d) 揀家,一律讀 218／216 已落檔的
`對照——重疊度*.csv`,不重算**(號已寫死,重算只會多一次取數機會)。E21–E25 五宗
今次才跑同一套挑法,用 `ctrl_compare.pick_rules`,函數原封不動 import。

成績口徑:相對籃子 = 12 個月超額 − 該宗籃子(新聞點名)中位;相對大市 = 12 個月超額本身;
錨 = T(衝擊低點)。勝出 = 相對籃子 > 0。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
MOD = ROOT / "research" / "2026-09-methodology" / "2026-09-12-暴露差異模組v1"
V3 = ROOT / "research" / "2026-09-methodology" / "2026-09-11-①v3全量回測" / "評分"
B199 = ROOT / "research" / "2026-09-methodology" / "2026-09-10-①行業殺錯事件籃子"
PRICES = ROOT / "data" / "prices" / "daily"
SPY_CSV = ROOT / "data" / "prices" / "spy_daily.csv"
sys.path.insert(0, str(V3))
sys.path.insert(0, str(ROOT / "strategy" / "tools"))

import ctrl_compare as cc  # noqa: E402  只讀不改
import implied_expectations as ie  # noqa: E402

OOS5 = ["E21", "E22", "E23", "E24", "E25"]
NEW4 = ["E17", "E18", "E19", "E20"]
MAIN7 = cc.MAIN7
ALL16 = OOS5 + NEW4 + MAIN7

# 事件類型:只有 E21–E27 在 spec 事前登記;其餘由本票按同一條規則(價格事件 = 宏觀或
# 資金流觸發、公司基本面未變;財務事件 = 公司或行業經營條件真的變)分類,來源記「本票判」。
TYPE_SRC = {e: "spec 事前登記" for e in OOS5}
TYPE = {"E21": "價格", "E22": "財務", "E23": "價格", "E24": "財務", "E25": "財務",
        # KARST-218 票面第 3 條已寫死:E18 價格事件、E17 財務事件
        "E17": "財務", "E18": "價格", "E19": "財務", "E20": "財務",
        # 以下七宗為 KARST-199 開發樣本,原 spec 無類型欄,由本票判
        "E01": "價格", "E06": "財務", "E07": "價格", "E08": "財務",
        "E12": "財務", "E13": "價格", "E14": "財務"}
for _e in NEW4 + MAIN7:
    TYPE_SRC[_e] = "本票判(218 票面有 E17/E18)" if _e in ("E17", "E18") else "本票判"

RULE_CN = {"a": "(a) 清單有限暴露", "b": "(b) 跌得最少",
           "c": "(c) 財務簡篩", "d": "(d) 低波動"}


def log(m):
    print(m, flush=True)


# ------------------------------------------------------------------ 池
def load_pool(path, events, eid_col="entity_id"):
    d = pd.read_csv(path, low_memory=False, encoding="utf-8-sig")
    d = d[(d["basket_kind"] == "新聞點名") & (d["event_id"].isin(events))].copy()
    d["eid10"] = d[eid_col].map(cc.eid10)
    d["ticker"] = d["ticker"].astype(str).str.strip()
    return d[["event_id", "ticker", "eid10", "f_shock_rel_drop",
              "T_12m_excess", "N_12m_excess"]]


def load_spec_types(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return {e["event_id"]: e for e in d["events"]}


# ------------------------------------------------------------------ 事前波動(逐分片,不整庫入記憶體)
def vol_map_for(pairs, spy):
    """pairs = {(eid10, event_id): shock_date};逐分片讀,讀完即掉。"""
    want = {p[0] for p in pairs if p[0]}
    shards = sorted(PRICES / ("part_%02d.parquet" % i) for i in range(16))
    out = {p: np.nan for p in pairs}
    by_eid = {}
    for p in pairs:
        by_eid.setdefault(p[0], []).append(p)
    for sh in shards:
        d = pd.read_parquet(sh, columns=["entity_id", "date", "adj_close", "series_role"])
        d = d[(d["series_role"] == "primary") & (d["entity_id"].isin(want))]
        if len(d) == 0:
            del d
            continue
        d["date"] = pd.to_datetime(d["date"])
        d["ret"] = d.groupby("entity_id")["adj_close"].pct_change()
        for eid, g in d.groupby("entity_id"):
            g = g.sort_values("date")
            for key in by_eid.get(eid, []):
                shock = pairs[key]
                before = g[g["date"].dt.date < shock]
                if len(before) < 60:
                    continue
                r = before["ret"].dropna().tail(cc.VOL_WINDOW)
                if len(r) < 60:
                    continue
                out[key] = float(r.std(ddof=1))
        del d
    return out


# ------------------------------------------------------------------ 主
def main():
    pools = pd.concat([
        load_pool(HERE / "out" / "basket_members_oos.csv", OOS5),
        load_pool(MOD / "out" / "basket_members_new.csv", NEW4),
        load_pool(B199 / "out" / "basket_members.csv", MAIN7),
    ], ignore_index=True)
    log("池: %d 行, %d 宗" % (len(pools), pools["event_id"].nunique()))

    spec = {}
    spec.update(load_spec_types(HERE / "new_events_spec_oos.json"))
    spec.update(load_spec_types(MOD / "new_events_spec.json"))
    spec.update(load_spec_types(B199 / "events_spec.json"))
    name_of = {e: spec[e]["name"] for e in ALL16}
    shock = {e: ie._d(spec[e]["shock_start"]) for e in ALL16}

    # 籃子中位 + 相對籃子
    bmT = pools.groupby("event_id")["T_12m_excess"].median().to_dict()
    bmN = pools.groupby("event_id")["N_12m_excess"].median().to_dict()
    pools["rel_T"] = pools["T_12m_excess"] - pools["event_id"].map(bmT)
    pools["rel_N"] = pools["N_12m_excess"] - pools["event_id"].map(bmN)

    # 清單臂(a):一律照已落檔判級
    clist = {}
    for e in OOS5:
        d = pd.read_csv(HERE / f"判-{e}.csv", low_memory=False)
        clist[e] = d[d["dmg_true"].astype(str).str.strip() == "有限"]["ticker"].tolist()
    for e in NEW4:
        d = pd.read_csv(MOD / f"判-{e}.csv", low_memory=False)
        clist[e] = d[d["dmg_true"].astype(str).str.strip() == "有限"]["ticker"].tolist()
    det = pd.read_csv(V3 / "評分明細.csv", low_memory=False)
    for e in MAIN7:
        clist[e] = det[(det["event_id"] == e)
                       & (det["dmg_true"].astype(str).str.strip() == "有限")]["ticker"].tolist()
    log("清單家數: %s" % {e: len(clist[e]) for e in ALL16})

    # (b)(c)(d):E17–E20 與 MAIN7 讀已落檔揀家;E21–E25 今次才跑
    picks = {e: {"a": clist[e]} for e in ALL16}
    for f, evs in ((V3 / "對照——重疊度.csv", MAIN7),
                   (MOD / "對照——重疊度(樣本外).csv", NEW4)):
        d = pd.read_csv(f, low_memory=False, encoding="utf-8-sig")
        for _, r in d.iterrows():
            e = r["event_id"]
            if e not in evs:
                continue
            for rule in ("b", "c", "d"):
                picks[e][rule] = [t.strip() for t in str(r["%s 揀到" % rule]).split("、") if t.strip()]
            assert sorted(picks[e]["a"]) == sorted(
                [t.strip() for t in str(r["清單"]).split("、") if t.strip()]), e
    log("已讀 E17–E20 與七宗已落檔揀家")

    oos = pools[pools["event_id"].isin(OOS5)].copy()
    pairs = {}
    for _, r in oos.iterrows():
        if r["eid10"]:
            pairs[(r["eid10"], r["event_id"])] = shock[r["event_id"]]
    cache = HERE / "out" / "cache_vol_fin_oos.json"
    if cache.exists():
        c = json.loads(cache.read_text(encoding="utf-8"))
        vol_map = {tuple(k.split("|")): v for k, v in c["vol"].items()}
        fin_map = {tuple(k.split("|")): (v[0], v[1], v[2]) for k, v in c["fin"].items()}
        log("讀快取: 事前波動 %d 家、財務簡篩 %d 家" % (len(vol_map), len(fin_map)))
    else:
        spy = pd.read_csv(SPY_CSV, parse_dates=["date"])
        vol_map = vol_map_for(pairs, spy)
        log("事前波動: 要 %d 家,算出 %d 家" % (
            len(pairs), sum(1 for v in vol_map.values() if np.isfinite(v))))
        fin_map = {}
        for e in OOS5:
            for _, r in oos[oos["event_id"] == e].iterrows():
                if not r["eid10"]:
                    continue
                fin_map[(r["eid10"], e)] = cc.finance_screen(r["eid10"], shock[e])
            log("財務簡篩 %s 取數完" % e)
        json.dump({"vol": {"%s|%s" % k: v for k, v in vol_map.items()},
                   "fin": {"%s|%s" % k: [v[0], v[1], v[2]] for k, v in fin_map.items()}},
                  open(cache, "w", encoding="utf-8"), ensure_ascii=False)

    fin_rows = []
    for e in OOS5:
        for _, r in oos[oos["event_id"] == e].iterrows():
            if not r["eid10"]:
                continue
            pos, cv, note = fin_map[(r["eid10"], e)]
            fin_rows.append(dict(event_id=e, ticker=r["ticker"], entity_id=r["eid10"],
                                 經營現金流為正=("" if pos is None else int(pos)),
                                 營收變異係數=("" if cv is None else round(cv, 4)),
                                 查不到原因=note))
    pd.DataFrame(fin_rows).to_csv(HERE / "對照2——財務簡篩取數(E21–E25).csv",
                                  index=False, encoding="utf-8-sig")

    for e in OOS5:
        pool = oos[oos["event_id"] == e]
        pk = cc.pick_rules(pool, len(clist[e]), shock[e], None, vol_map, fin_map, e)
        pk["a"] = clist[e]
        picks[e] = pk
        log("%s k=%d 清單=%s | b=%s | c=%s | d=%s" % (
            e, len(clist[e]), pk["a"], pk["b"], pk["c"], pk["d"]))

    # ---------------- 逐宗逐臂
    rows = []
    for e in ALL16:
        pool = pools[pools["event_id"] == e]
        for rule in ("a", "b", "c", "d"):
            tk = picks[e][rule]
            sub = pool[pool["ticker"].isin(tk)]
            s, m = sub["rel_T"].dropna(), sub["T_12m_excess"].dropna()
            rows.append(dict(
                event_id=e, 事件=name_of[e], 類型=TYPE[e], 類型來源=TYPE_SRC[e], 規則=rule,
                k=len(clist[e]), 實挑家數=len(sub),
                揀到="、".join(sub["ticker"].tolist()),
                相對籃子中位=round(float(s.median()), 4) if len(s) else np.nan,
                相對大市超額中位=round(float(m.median()), 4) if len(m) else np.nan,
                勝率=round(float((s > 0).mean()), 4) if len(s) else np.nan))
    per = pd.DataFrame(rows)
    per.to_csv(HERE / "對照2——逐宗逐臂.csv", index=False, encoding="utf-8-sig")

    # ---------------- 三組彙總
    groups = {"(a) 新增五宗 E21–E25": OOS5,
              "(b) 連同 218 四宗 E17–E20 共九宗": OOS5 + NEW4,
              "(c) 連同 216 開發七宗共十六宗": ALL16}
    summ = []
    for gname, evs in groups.items():
        for rule in ("a", "b", "c", "d"):
            g = per[(per["規則"] == rule) & (per["event_id"].isin(evs))]
            rel, mkt = g["相對籃子中位"].dropna(), g["相對大市超額中位"].dropna()
            wins = g["勝率"].dropna()
            pooled = []
            for e in evs:
                pool = pools[pools["event_id"] == e]
                pooled.append(pool[pool["ticker"].isin(picks[e][rule])]["rel_T"])
            pooled = pd.concat(pooled).dropna() if pooled else pd.Series(dtype=float)
            summ.append(dict(組=gname, 規則=RULE_CN[rule], 宗數=len(g),
                             清單家數合計=int(g["k"].sum()), 實挑家數合計=int(g["實挑家數"].sum()),
                             逐宗中位之跨宗中位=round(float(rel.median()), 4) if len(rel) else np.nan,
                             逐宗相對大市中位之跨宗中位=round(float(mkt.median()), 4) if len(mkt) else np.nan,
                             逐家合池相對籃子中位=round(float(pooled.median()), 4) if len(pooled) else np.nan,
                             逐家勝率=round(float((pooled > 0).mean()), 4) if len(pooled) else np.nan,
                             逐家數=int(len(pooled)),
                             各宗勝率中位=round(float(wins.median()), 4) if len(wins) else np.nan,
                             各宗勝出宗數=int((g["相對籃子中位"] > 0).sum())))
    summ = pd.DataFrame(summ)
    summ.to_csv(HERE / "對照2——三組彙總.csv", index=False, encoding="utf-8-sig")

    # ---------------- 逐宗剔走(每組、每規則)
    loo = []
    for gname, evs in groups.items():
        for rule in ("a", "b", "c", "d"):
            g = per[(per["規則"] == rule) & (per["event_id"].isin(evs))]
            med_all = float(g["相對籃子中位"].dropna().median())
            for e in evs:
                rest = g[g["event_id"] != e]["相對籃子中位"].dropna()
                loo.append(dict(組=gname, 規則=RULE_CN[rule], 剔走事件=e,
                                全組中位=round(med_all, 4),
                                其餘中位=round(float(rest.median()), 4) if len(rest) else np.nan))
    loo = pd.DataFrame(loo)
    loo.to_csv(HERE / "對照2——逐宗剔走.csv", index=False, encoding="utf-8-sig")

    # ---------------- 一次剔兩宗(只做新增五宗,十個組合)——五宗樣本中位數只有五個數,
    # 剔一宗已足以看反轉;剔兩宗是看「優勢是不是全押在兩宗身上」。
    from itertools import combinations
    loo2 = []
    for combo in combinations(OOS5, 2):
        keep = [e for e in OOS5 if e not in combo]
        rec = dict(剔走="、".join(combo))
        for rule in ("a", "b", "c", "d"):
            g = per[(per["規則"] == rule) & (per["event_id"].isin(keep))]
            rec[RULE_CN[rule]] = round(float(g["相對籃子中位"].median()), 4)
        loo2.append(rec)
    loo2 = pd.DataFrame(loo2)
    loo2.to_csv(HERE / "對照2——剔兩宗(新增五宗).csv", index=False, encoding="utf-8-sig")

    # ---------------- 重疊度
    ov = []
    for e in ALL16:
        rec = dict(event_id=e, 事件=name_of[e], 類型=TYPE[e], k=len(clist[e]),
                   清單="、".join(picks[e]["a"]))
        for rule in ("b", "c", "d"):
            rec["%s 揀到" % rule] = "、".join(picks[e][rule])
            rec["%s 與清單重疊家數" % rule] = len(set(picks[e]["a"]) & set(picks[e][rule]))
        ov.append(rec)
    ov = pd.DataFrame(ov)
    ov.to_csv(HERE / "對照2——重疊度.csv", index=False, encoding="utf-8-sig")

    # ---------------- 價格 / 財務 分表
    sp = []
    for gname, evs in groups.items():
        for tp in ("價格", "財務"):
            sel = [e for e in evs if TYPE[e] == tp]
            for rule in ("a", "b", "c", "d"):
                g = per[(per["規則"] == rule) & (per["event_id"].isin(sel))]
                rel, mkt = g["相對籃子中位"].dropna(), g["相對大市超額中位"].dropna()
                sp.append(dict(組=gname, 類型=tp, 宗數=len(sel), 規則=RULE_CN[rule],
                               事件="、".join(sel),
                               逐宗中位之跨宗中位=round(float(rel.median()), 4) if len(rel) else np.nan,
                               逐宗相對大市中位之跨宗中位=round(float(mkt.median()), 4) if len(mkt) else np.nan))
    sp = pd.DataFrame(sp)
    sp.to_csv(HERE / "對照2——價格財務分表.csv", index=False, encoding="utf-8-sig")

    # ---------------- N 錨穩健度(只換錨,同一批揀家)
    nrows = []
    for gname, evs in groups.items():
        for rule in ("a", "b", "c", "d"):
            vals = []
            for e in evs:
                pool = pools[pools["event_id"] == e]
                sub = pool[pool["ticker"].isin(picks[e][rule])]
                s = sub["rel_N"].dropna()
                if len(s):
                    vals.append(float(s.median()))
            nrows.append(dict(組=gname, 規則=RULE_CN[rule], 宗數=len(vals),
                              逐宗中位之跨宗中位=round(float(np.median(vals)), 4) if vals else np.nan))
    nanch = pd.DataFrame(nrows)
    nanch.to_csv(HERE / "對照2——N錨穩健度.csv", index=False, encoding="utf-8-sig")

    # ---------------- 印
    log("== 三組彙總 ==")
    log(summ.to_string(index=False))
    log("== 逐宗逐臂 ==")
    log(per[["event_id", "類型", "規則", "k", "實挑家數", "揀到",
             "相對籃子中位", "相對大市超額中位", "勝率"]].to_string(index=False))
    log("== 逐宗剔走 ==")
    log(loo.pivot_table(index=["組", "剔走事件"], columns="規則",
                        values="其餘中位").to_string())
    log("== 重疊度 ==")
    log(ov.to_string(index=False))
    log("== 價格財務分表 ==")
    log(sp.to_string(index=False))
    log("== N 錨 ==")
    log(nanch.to_string(index=False))


if __name__ == "__main__":
    main()
