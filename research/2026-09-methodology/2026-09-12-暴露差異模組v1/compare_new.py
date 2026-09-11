# -*- coding: utf-8 -*-
"""KARST-218 樣本外新事件(E17–E20):清單判斷對三個簡單篩選。

**挑法一字不改照 KARST-216 `評分/ctrl_compare.py`**(直接 import 該檔的
`pre_event_vol` / `finance_screen` / `pick_rules` / `stats` / `eid10`),只把
候選池由 199 的 `basket_members.csv` 換成本票的 `out/basket_members_new.csv`,
把「清單臂」由 `評分明細.csv` 換成本票的 `判-E17..E20.csv`(`dmg_true == 有限`)。
**不寫入 199／216 目錄任何檔。**

四規則(同一事件、同一池(新聞點名)、同一進場日(T 錨之後下一交易日收市)、同 k 家):
  (a) 清單有限暴露 —— 照 `判-E*.csv` 錄,不重挑
  (b) 跌得最少     —— `f_shock_rel_drop` 最大
  (c) 財務簡篩     —— 衝擊前滾動四季經營現金流為正,再取最近八季營收變異係數最低
  (d) 低波動       —— 衝擊起日之前 252 個交易日(SPY 日曆)日回報標準差最低
k = 該宗判為「有限」的家數;k = 0 則四臂一齊記空,不補位。

**本對照在判斷全部落檔之後才跑**(`判-E17..E20.csv` 已寫死)。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
CTRL = ROOT / "research" / "2026-09-methodology" / "2026-09-11-①v3全量回測" / "評分"
sys.path.insert(0, str(CTRL))
sys.path.insert(0, str(ROOT / "strategy" / "tools"))

import ctrl_compare as cc  # noqa: E402  只讀不改,重用同一套挑法與取數
import implied_expectations as ie  # noqa: E402

EVENTS = ["E17", "E18", "E19", "E20"]


def main() -> None:
    named = pd.read_csv(HERE / "out" / "basket_members_new.csv", low_memory=False)
    named = named[named["basket_kind"] == "新聞點名"].copy()
    named["eid10"] = named["entity_id"].map(cc.eid10)

    spec = json.loads((HERE / "new_events_spec.json").read_text(encoding="utf-8"))
    meta = {e["event_id"]: e for e in spec["events"]}
    name_of = {e: meta[e]["name"] for e in EVENTS}
    shock = {e: ie._d(meta[e]["shock_start"]) for e in EVENTS}

    # 清單臂(照判-E*.csv,不重挑)
    fin_by_ev = {}
    for ev in EVENTS:
        d = pd.read_csv(HERE / f"判-{ev}.csv", low_memory=False)
        fin_by_ev[ev] = d[d["dmg_true"].astype(str).str.strip() == "有限"]["ticker"].tolist()
    print("清單有限暴露家數:", {k: len(v) for k, v in fin_by_ev.items()})

    bmT = named.groupby("event_id")["T_12m_excess"].median().to_dict()
    bmN = named.groupby("event_id")["N_12m_excess"].median().to_dict()
    named["rel_T"] = named["T_12m_excess"] - named["event_id"].map(bmT)
    named["rel_N"] = named["N_12m_excess"] - named["event_id"].map(bmN)

    # 事前波動
    shock_dates = {}
    for ev in EVENTS:
        for _, r in named[named["event_id"] == ev].iterrows():
            if r["eid10"]:
                shock_dates[(r["eid10"], ev)] = shock[ev]
    spy = pd.read_csv(ROOT / "data" / "prices" / "spy_daily.csv", parse_dates=["date"])
    vol_map, ncal = cc.pre_event_vol([k[0] for k in shock_dates], shock_dates, spy)
    print("SPY 日曆 %d 日,事前波動算出 %d 家" % (
        ncal, sum(1 for v in vol_map.values() if v is not None and np.isfinite(v))))

    # 財務簡篩
    fin_map, fin_rows = {}, []
    for ev in EVENTS:
        if not fin_by_ev.get(ev):
            continue
        for _, r in named[named["event_id"] == ev].iterrows():
            cik = r["eid10"]
            if not cik:
                continue
            pos, cv, note = cc.finance_screen(cik, shock[ev])
            fin_map[(cik, ev)] = (pos, cv, note)
            fin_rows.append(dict(event_id=ev, ticker=r["ticker"], entity_id=cik,
                                 經營現金流為正=("" if pos is None else int(pos)),
                                 營收變異係數=("" if cv is None else round(cv, 4)),
                                 查不到原因=note))
        print("財務簡篩 %s 取數完" % ev)
    pd.DataFrame(fin_rows).to_csv(HERE / "對照——財務簡篩取數(樣本外).csv",
                                  index=False, encoding="utf-8-sig")

    rows = []
    for ev in EVENTS:
        k = len(fin_by_ev.get(ev, []))
        pool = named[named["event_id"] == ev]
        pk = cc.pick_rules(pool, k, shock[ev], None, vol_map, fin_map, ev)
        pk["a"] = fin_by_ev.get(ev, [])
        for rule in ("a", "b", "c", "d"):
            tk = pk[rule]
            sub = pool[pool["ticker"].isin(tk)]
            st = cc.stats(sub)
            rows.append(dict(列型="彙總", event_id=ev, 事件=name_of[ev], 規則=rule,
                             清單家數k=k, 需挑家數=k, 實挑家數=len(tk),
                             揀到="、".join(tk), **st))
            for _, r in sub.iterrows():
                rows.append(dict(列型="逐家", event_id=ev, 事件=name_of[ev], 規則=rule,
                                 清單家數k=k, 需挑家數=k, 實挑家數=len(tk),
                                 揀到=r["ticker"], 家數=1,
                                 相對籃子中位=round(float(r["rel_T"]), 4),
                                 相對大市超額中位=round(float(r["T_12m_excess"]), 4),
                                 相對籃子勝率=(1.0 if r["rel_T"] > 0 else 0.0)))
    per = pd.DataFrame(rows)
    per.to_csv(HERE / "對照——清單對簡單篩選(樣本外).csv", index=False, encoding="utf-8-sig")

    # 彙總
    summ = []
    for rule in ("a", "b", "c", "d"):
        g = per[per["規則"] == rule]
        evl = g[g["列型"] == "彙總"]
        picks = g[g["列型"] == "逐家"]
        med_rel = evl["相對籃子中位"].dropna()
        med_mkt = evl["相對大市超額中位"].dropna()
        summ.append(dict(
            規則=rule, 參與事件數=int(len(evl)),
            空宗數=int((evl["實挑家數"] == 0).sum()),
            逐宗中位之四宗中位=round(float(med_rel.median()), 4) if len(med_rel) else np.nan,
            逐宗相對大市中位之四宗中位=round(float(med_mkt.median()), 4) if len(med_mkt) else np.nan,
            逐家合池相對籃子中位=round(float(picks["相對籃子中位"].median()), 4) if len(picks) else np.nan,
            逐家合池相對大市中位=round(float(picks["相對大市超額中位"].median()), 4) if len(picks) else np.nan,
            逐家勝率=round(float((picks["相對籃子中位"] > 0).mean()), 4) if len(picks) else np.nan,
            逐家數=int(len(picks))))
    summ = pd.DataFrame(summ)
    summ.to_csv(HERE / "對照——四規則彙總(樣本外).csv", index=False, encoding="utf-8-sig")

    # 重疊度 + 六個月口徑(樣本外多一個窗口看穩健度)
    ov = []
    for ev in EVENTS:
        k = len(fin_by_ev.get(ev, []))
        pool = named[named["event_id"] == ev]
        pk = cc.pick_rules(pool, k, shock[ev], None, vol_map, fin_map, ev)
        pk["a"] = fin_by_ev.get(ev, [])
        ov.append(dict(event_id=ev, 事件=name_of[ev], k=k, 清單="、".join(pk["a"]),
                       **{f"{r} 揀到": "、".join(pk[r]) for r in ("b", "c", "d")},
                       **{f"{r} 與清單重疊家數": len(set(pk["a"]) & set(pk[r])) for r in ("b", "c", "d")}))
    ov = pd.DataFrame(ov)
    ov.to_csv(HERE / "對照——重疊度(樣本外).csv", index=False, encoding="utf-8-sig")

    print("== 四規則彙總(樣本外, T 錨, 十二個月) ==")
    print(summ.to_string(index=False))

    # N 錨(新聞結束日)穩健度檢查:同一批揀家、同一批結果欄,只換錨
    nrows = []
    for ev in EVENTS:
        k = len(fin_by_ev.get(ev, []))
        pool = named[named["event_id"] == ev]
        pk = cc.pick_rules(pool, k, shock[ev], None, vol_map, fin_map, ev)
        pk["a"] = fin_by_ev.get(ev, [])
        for rule in ("a", "b", "c", "d"):
            sub = pool[pool["ticker"].isin(pk[rule])]
            s = sub["rel_N"].dropna()
            m = sub["N_12m_excess"].dropna()
            nrows.append(dict(規則=rule, event_id=ev, 實挑家數=len(sub),
                              相對籃子中位=round(float(s.median()), 4) if len(s) else np.nan,
                              相對大市超額中位=round(float(m.median()), 4) if len(m) else np.nan))
    nper = pd.DataFrame(nrows)
    nper.to_csv(HERE / "對照——N錨穩健度(樣本外).csv", index=False, encoding="utf-8-sig")
    print("== N 錨(新聞結束日)穩健度 ==")
    print(nper[nper["規則"].isin(["a", "b", "c", "d"])].groupby("規則")[
        ["相對籃子中位", "相對大市超額中位"]].median().round(4).to_string())
    print("== 重疊度 ==")
    print(ov.to_string(index=False))
    print("== 逐宗 ==")
    print(per[per["列型"] == "彙總"][["event_id", "規則", "實挑家數", "揀到",
                                    "相對籃子中位", "相對大市超額中位"]].to_string(index=False))


if __name__ == "__main__":
    main()
