# -*- coding: utf-8 -*-
"""KARST-216 ①v3 回測口徑修正與簡單篩選對照(主腳本,只讀既有輸出,不改)。

== 這張票要答的一條問題 ==
第六輪外評論第 1 題:清單挑出的「有限暴露」公司相對籃子勝出,會不會只是
「揀了跌得少/波動低/財務穩」的公司——即一個簡單篩選也做得到?所以要在**同一事件、
同一籃子、同一截止日、同一家數**之下,拿清單對三個簡單規則。

== 四規則的挑法(先寫死,再跑;跑完不改)==
候選池 = 199 `basket_members.csv` 的「新聞點名」成員(即 199/210/215 一路用的
「籃子」定義,亦是「籃子中位」的分母)。同SIC全體不用,理由寫在報告裡。

清單在該宗挑了 k 家「有限暴露」(`評分明細.csv` 的 dmg_true == 有限),每個規則
就在同一池、同一事件、同樣挑 k 家;該宗 k = 0(全判重大/資料不足)則四個規則
一齊記空,不補位。

(a) 清單有限暴露:照錄,不重挑。
(b) 衝擊窗跌得最少:`f_shock_rel_drop` 最大(即最接近 0)的 k 家;
    同分以 ticker 字母序定先後。
(c) 財務簡篩:先過「衝擊前滾動四季經營現金流為正」這一關,再按營收波動最低
    取 k 家。取數一律用 `strategy/tools/implied_expectations.py` 的取數層
    (`_rows` / `duration_series` / `quarterize` / `ttm` 的同一套標籤),
    **知情時點閘 = 只用 `filed <= 衝擊起日` 的事實**(點-in-time,不偷看之後才交的季報);
    經營現金流 TTM = 季末 <= 衝擊起日 的最近四季合計;營收波動 = 同樣條件下
    最近八個單季營收的變異係數(std/mean)。缺數即該家不入這一條,不猜、不填零。
(d) 事前低波動:衝擊起日之前 252 個交易日(SPY 日曆)日回報標準差最低的 k 家。

若有規則在某宗取不足 k 家,該宗該規則**按實際取到的家數報**,並在家數欄記明
(票面要求「取不到數就標查不到,不猜」)。

== 成績口徑 ==
- 相對籃子 = 十二個月超額 − 該宗籃子中位(199 口徑,`T_12m_excess` − 新聞點名中位);
- 相對大市 = 十二個月超額本身(`T_12m_excess`,基準 SPY 總回報)。
- 錨 = T(衝擊低點),四個規則**同一個錨同一個進場日**(199 的 anchor_T_date 之後
  下一個交易日收市),故家數以外的東西完全一致。
- 勝出 = 相對籃子 > 0。
- 同一批公司若被「同SIC」類不同事件重複點名,一律按 (event_id, entity_id) 計,不跨宗去重。

== 樣本 ==
主樣本 = 七宗「籃內同時有有限與重大判級」的事件(E01 E06 E07 E08 E12 E13 E14);
十四宗版本 = 同一池、同一規則,惟 k = 0 的七宗全臂記空(只作完整性,不另生數字)。

== 第三部 ==
增長者分組:52 家(評分樣本)與全籃(新聞點名)各按衝擊前收入增速為正/負分兩組,
出相對籃子結果,答「增長本身是不是篩選」。

汙染照三批口徑:做判斷的模型知道結局;挑家可能受結局影響;數字只作方法診斷。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\projects\Karst")
V3 = ROOT / "research" / "2026-09-methodology" / "2026-09-11-①v3全量回測" / "評分"
B199 = ROOT / "research" / "2026-09-methodology" / "2026-09-10-①行業殺錯事件籃子"
PRICES = ROOT / "data" / "prices" / "daily"
SPY_CSV = ROOT / "data" / "prices" / "spy_daily.csv"
sys.path.insert(0, str(ROOT / "strategy" / "tools"))

import implied_expectations as ie  # noqa: E402  只讀不改,只用取數層

OCF_TAGS = [
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
]
REV_TAGS = ie.REV_TAGS
VOL_WINDOW = 252          # 事前一年日回報
REV_QUARTERS = 8          # 營收波動用最近八個單季

MAIN7 = ["E01", "E06", "E07", "E08", "E12", "E13", "E14"]   # 有有限暴露判級的事件


def log(m: str) -> None:
    print(m, flush=True)


def eid10(x) -> str:
    """entity_id 一律化成十位補零字串。

    CSV 讀出來是 int(前導零消失),parquet 與 companyfacts 檔名是 "0000732717";
    兩邊不對齊會令價格與財務簡篩靜靜取不到數 —— 所以只在這一處做正規化。
    """
    if x is None:
        return ""
    s = str(x).strip()
    if s in ("", "nan", "None"):
        return ""
    if s.isdigit():
        return s.zfill(10)
    return s


# ----------------------------------------------------------------- 載入
def load_all():
    det = pd.read_csv(V3 / "評分明細.csv", low_memory=False)
    mem = pd.read_csv(B199 / "out" / "basket_members.csv", low_memory=False)
    named = mem[mem["basket_kind"] == "新聞點名"].copy()
    spec = json.loads((B199 / "events_spec.json").read_text(encoding="utf-8"))
    meta = {e["event_id"]: e for e in spec["events"]}
    return det, named, meta


def basket_median_T(named: pd.DataFrame) -> dict:
    out = {}
    for ev, g in named.groupby("event_id"):
        s = g["T_12m_excess"].dropna()
        out[ev] = float(s.median()) if len(s) else np.nan
    return out


# ----------------------------------------------------------------- 價格 / 波動
def price_shards_for(entity_ids):
    """entity_id 尾兩位 % 16 定分片;只讀用得到的那幾個。"""
    need = {int(str(e)[-2:]) % 16 for e in entity_ids if e and str(e) != "nan"}
    return sorted(PRICES / ("part_%02d.parquet" % i) for i in need)


def pre_event_vol(entity_ids, shock_dates, spy):
    """回 {(entity_id, event_id): 事前 252 日日回報標準差}。"""
    want = set(entity_ids) - {"", "nan"}
    frames = []
    for p in price_shards_for(want):
        d = pd.read_parquet(p, columns=["entity_id", "date", "adj_close", "series_role"])
        d = d[(d["series_role"] == "primary") & (d["entity_id"].isin(want))]
        frames.append(d.drop(columns=["series_role"]))
    px = pd.concat(frames, ignore_index=True)
    px["date"] = pd.to_datetime(px["date"])
    px = px.sort_values(["entity_id", "date"])
    px["ret"] = px.groupby("entity_id")["adj_close"].pct_change()

    cal = spy["date"].sort_values().to_numpy()
    out = {}
    for (eid, ev), shock in shock_dates.items():
        sub = px[px["entity_id"] == eid]
        if len(sub) == 0:
            out[(eid, ev)] = np.nan
            continue
        before = sub[sub["date"] < pd.Timestamp(shock)]
        if len(before) < 60:
            out[(eid, ev)] = np.nan
            continue
        r = before["ret"].dropna().tail(VOL_WINDOW)
        if len(r) < 60:
            out[(eid, ev)] = np.nan
            continue
        out[(eid, ev)] = float(r.std(ddof=1))
    return out, len(cal)


# ----------------------------------------------------------------- 財務簡篩
_facts_cache: dict = {}


def _facts(cik):
    if cik not in _facts_cache:
        try:
            _facts_cache[cik] = ie.load_facts(cik)
        except (FileNotFoundError, OSError):
            _facts_cache[cik] = None
    return _facts_cache[cik]


def _pit_duration(facts, tags, asof):
    """只留 filed <= asof 的期間型事實,同期取最後申報的一份(ie 同一套規矩 + 知情時點閘)。"""
    asof_iso = asof.isoformat() if hasattr(asof, "isoformat") else str(asof)
    best = {}
    for tag in tags:
        for r in ie._rows(facts, tag):
            if "start" not in r or "end" not in r:
                continue
            filed = r.get("filed", "")
            if filed and filed > asof_iso:   # ISO 字串比大小 = 比日期
                continue
            k = (ie._d(r["start"]), ie._d(r["end"]))
            if k not in best or filed >= best[k][0]:
                best[k] = (filed, float(r["val"]))
        if best:
            break
    return {k: v[1] for k, v in best.items()}


def finance_screen(cik, shock):
    """回 (ocf_ttm>0 與否 or None, 八季營收變異係數 or None, 註)。"""
    facts = _facts(cik)
    if facts is None:
        return None, None, "無 companyfacts 快取"
    asof = shock
    try:
        ocf_q = ie.quarterize(_pit_duration(facts, OCF_TAGS, asof))
        ocf_ttm, _ = ie.ttm(ocf_q, asof) if ocf_q else (None, [])
        rev_q = ie.quarterize(_pit_duration(facts, REV_TAGS, asof))
    except Exception as e:  # noqa: BLE001  逐家掃,單家出錯不可整個腳本死
        return None, None, "取數失敗:%s" % e
    ocf_pos = None if ocf_ttm is None else bool(ocf_ttm > 0)
    cv = None
    ends = sorted([e for e in rev_q if e <= asof])
    if len(ends) >= REV_QUARTERS:
        vals = np.array([rev_q[e] for e in ends[-REV_QUARTERS:]], dtype=float)
        if vals.mean() > 0:
            cv = float(vals.std(ddof=1) / vals.mean())
    note = ""
    if ocf_pos is None:
        note = "經營現金流不足四季,算不出 TTM"
    elif cv is None:
        note = "營收不足八季,算不出波動"
    return ocf_pos, cv, note


# ----------------------------------------------------------------- 挑家
def pick_rules(pool, k, shock, eid2cik, vol_map, fin_map, ev):
    """回 {rule: [ticker, ...]}。pool 已是該宗新聞點名成員。"""
    out = {"a": [], "b": [], "c": [], "d": []}
    if k <= 0:
        return out
    # (b) 衝擊窗跌得最少
    b = pool[pool["f_shock_rel_drop"].notna()].sort_values(
        ["f_shock_rel_drop", "ticker"], ascending=[False, True])
    out["b"] = b["ticker"].head(k).tolist()
    # (c) 經營現金流為正 且 營收波動最低
    rows = []
    for _, r in pool.iterrows():
        key = (r["eid10"], ev)
        if key not in fin_map:
            continue
        pos, cv, _ = fin_map[key]
        if pos is True and cv is not None:
            rows.append((cv, r["ticker"]))
    rows.sort()
    out["c"] = [t for _, t in rows[:k]]
    # (d) 事前低波動
    rows = []
    for _, r in pool.iterrows():
        v = vol_map.get((r["eid10"], ev))
        if v is not None and np.isfinite(v):
            rows.append((v, r["ticker"]))
    rows.sort()
    out["d"] = [t for _, t in rows[:k]]
    return out


def stats(df, col_rel="rel_T", col_mkt="T_12m_excess"):
    s = df[col_rel].dropna()
    m = df[col_mkt].dropna()
    return dict(家數=int(len(df)),
                相對籃子中位=round(float(s.median()), 4) if len(s) else np.nan,
                相對大市超額中位=round(float(m.median()), 4) if len(m) else np.nan,
                相對籃子勝率=round(float((s > 0).mean()), 4) if len(s) else np.nan)


def main():
    det, named, meta = load_all()
    bmT = basket_median_T(named)
    named = named.copy()
    named["eid10"] = named["entity_id"].map(eid10)
    named["rel_T"] = named["T_12m_excess"] - named["event_id"].map(bmT)
    bmN = named.groupby("event_id")["N_12m_excess"].median().to_dict()
    named["rel_N"] = named["N_12m_excess"] - named["event_id"].map(bmN)

    # 清單選家(照 評分明細,不重挑)
    fin_by_ev = {}
    for ev, g in det.groupby("event_id"):
        fin_by_ev[ev] = g[g["dmg_true"] == "有限"]["ticker"].tolist()
    log("清單有限暴露家數:%s" % {k: len(v) for k, v in sorted(fin_by_ev.items())})

    # 事件清單(十四宗 = 本回測真正有判級與十二個月結果的那十四宗;199 的 E15 未有成熟結果,
    # 不入本對照 —— 一個全空的第十五宗只會令「十四宗版本」名不副實)
    events = [e for e in sorted(meta) if e in set(det["event_id"])]
    shock = {e: ie._d(meta[e]["shock_start"]) for e in events}   # 衝擊起日一律 datetime.date
    name_of = {e: meta[e]["name"] for e in events}

    # 逐家(事件, 實體) 需要事前波動
    shock_dates = {}
    for ev in events:
        for _, r in named[named["event_id"] == ev].iterrows():
            if r["eid10"]:
                shock_dates[(r["eid10"], ev)] = shock[ev]
    spy = pd.read_csv(SPY_CSV, parse_dates=["date"])
    vol_map, ncal = pre_event_vol([k[0] for k in shock_dates], shock_dates, spy)
    log("價格分片讀畢,SPY 日曆 %d 日,事前波動算出 %d 家" % (
        ncal, sum(1 for v in vol_map.values() if v is not None and np.isfinite(v))))

    # 財務簡篩:只在有 k>0 的事件上取數
    need_events = [e for e in events if len(fin_by_ev.get(e, [])) > 0]
    fin_map = {}
    fin_rows = []
    for ev in need_events:
        for _, r in named[named["event_id"] == ev].iterrows():
            cik = r["eid10"]
            if not cik:
                continue
            pos, cv, note = finance_screen(cik, shock[ev])
            fin_map[(cik, ev)] = (pos, cv, note)
            fin_rows.append(dict(event_id=ev, ticker=r["ticker"], entity_id=cik,
                                 經營現金流為正=("" if pos is None else int(pos)),
                                 營收變異係數=("" if cv is None else round(cv, 4)),
                                 查不到原因=note))
        log("財務簡篩 %s 取數完" % ev)
    pd.DataFrame(fin_rows).to_csv(V3 / "對照——財務簡篩取數.csv", index=False,
                                  encoding="utf-8-sig")

    # ---- 四規則逐宗逐家
    rows = []
    for sample, evs in (("七宗", MAIN7), ("十四宗", events)):
        for ev in evs:
            k = len(fin_by_ev.get(ev, []))
            pool = named[named["event_id"] == ev]
            pk = pick_rules(pool, k, shock[ev], None, vol_map, fin_map, ev)
            pk["a"] = fin_by_ev.get(ev, [])
            for rule in ("a", "b", "c", "d"):
                tk = pk[rule]
                sub = pool[pool["ticker"].isin(tk)]
                st = stats(sub)
                rows.append(dict(列型="彙總", 樣本=sample, event_id=ev, 事件=name_of[ev],
                                 規則=rule, 清單家數k=k, 需挑家數=k, 實挑家數=len(tk),
                                 揀到="、".join(tk), **st))
                for _, r in sub.iterrows():
                    rows.append(dict(列型="逐家", 樣本=sample, event_id=ev, 事件=name_of[ev],
                                     規則=rule, 清單家數k=k, 需挑家數=k,
                                     實挑家數=len(tk), 揀到=r["ticker"],
                                     家數=1, 相對籃子中位=round(float(r["rel_T"]), 4),
                                     相對大市超額中位=round(float(r["T_12m_excess"]), 4),
                                     相對籃子勝率=(1.0 if r["rel_T"] > 0 else 0.0)))
    per = pd.DataFrame(rows)
    per.to_csv(V3 / "對照——簡單篩選.csv", index=False, encoding="utf-8-sig")

    # ---- 彙總(事件等權 = 先每宗中位再跨宗中位;另出逐家合池)
    summ = []
    for sample in ("七宗", "十四宗"):
        for rule in ("a", "b", "c", "d"):
            g = per[(per["樣本"] == sample) & (per["規則"] == rule)]
            evl = g[g["列型"] == "彙總"]
            med_rel = evl["相對籃子中位"].dropna()
            med_mkt = evl["相對大市超額中位"].dropna()
            picks = g[g["列型"] == "逐家"]
            summ.append(dict(
                樣本=sample, 規則=rule,
                參與事件數=int(len(evl)),
                清單臂全空宗數=int((evl["實挑家數"] == 0).sum()),
                逐宗中位之跨宗中位=round(float(med_rel.median()), 4) if len(med_rel) else np.nan,
                逐宗相對大市中位之跨宗中位=round(float(med_mkt.median()), 4) if len(med_mkt) else np.nan,
                逐家合池相對籃子中位=round(float(picks["相對籃子中位"].median()), 4) if len(picks) else np.nan,
                逐家合池相對大市中位=round(float(picks["相對大市超額中位"].median()), 4) if len(picks) else np.nan,
                逐家勝率=round(float((picks["相對籃子中位"] > 0).mean()), 4) if len(picks) else np.nan,
                逐家數=int(len(picks))))
    summ = pd.DataFrame(summ)
    summ.to_csv(V3 / "對照——四規則彙總.csv", index=False, encoding="utf-8-sig")

    # ---- 逐宗剔走(每規則,七宗)
    loo = []
    for rule in ("a", "b", "c", "d"):
        g = per[(per["樣本"] == "七宗") & (per["規則"] == rule) & (per["列型"] == "彙總")]
        for ev in MAIN7:
            rest = g[g["event_id"] != ev]["相對籃子中位"].dropna()
            loo.append(dict(規則=rule, 剔走事件=ev,
                            剔走全宗家數=int(g[g["event_id"] == ev]["實挑家數"].iloc[0])
                            if len(g[g["event_id"] == ev]) else 0,
                            其餘六宗中位=round(float(rest.median()), 4) if len(rest) else np.nan))
    loo = pd.DataFrame(loo)
    loo.to_csv(V3 / "對照——逐宗剔走.csv", index=False, encoding="utf-8-sig")

    # ---- 重疊度
    ov = []
    for ev in MAIN7:
        k = len(fin_by_ev.get(ev, []))
        pool = named[named["event_id"] == ev]
        pk = pick_rules(pool, k, shock[ev], None, vol_map, fin_map, ev)
        pk["a"] = fin_by_ev.get(ev, [])
        rec = dict(event_id=ev, 事件=name_of[ev], k=k, 清單="、".join(pk["a"]))
        for rule in ("b", "c", "d"):
            rec["%s 揀到" % rule] = "、".join(pk[rule])
            rec["%s 與清單重疊家數" % rule] = len(set(pk["a"]) & set(pk[rule]))
        ov.append(rec)
    ov = pd.DataFrame(ov)
    ov.to_csv(V3 / "對照——重疊度.csv", index=False, encoding="utf-8-sig")

    # ---- 第三部:增長者分組
    det_named = []
    for _, r in det.iterrows():
        ev = r["event_id"]
        m = named[(named["event_id"] == ev) & (named["ticker"] == r["ticker"])]
        if len(m):
            det_named.append(dict(event_id=ev, ticker=r["ticker"], dmg_true=r["dmg_true"],
                                  rel_T=float(m.iloc[0]["rel_T"]),
                                  T_12m_excess=float(m.iloc[0]["T_12m_excess"]),
                                  f_rev_growth_yoy=m.iloc[0]["f_rev_growth_yoy"]))
    det_named = pd.DataFrame(det_named)

    grow = []
    for label, d in (("52 家(評分樣本)", det_named), ("全籃(新聞點名)", named)):
        for grp, sub in (("衝擊前收入增速為正", d[d["f_rev_growth_yoy"] > 0]),
                         ("衝擊前收入增速為負", d[d["f_rev_growth_yoy"] <= 0]),
                         ("增速查不到", d[d["f_rev_growth_yoy"].isna()])):
            s = sub["rel_T"].dropna()
            grow.append(dict(樣本=label, 分組=grp, 家數=int(len(s)),
                             相對籃子中位=round(float(s.median()), 4) if len(s) else np.nan,
                             相對大市超額中位=round(float(sub["T_12m_excess"].dropna().median()), 4)
                             if len(sub["T_12m_excess"].dropna()) else np.nan,
                             相對籃子勝率=round(float((s > 0).mean()), 4) if len(s) else np.nan,
                             其中相對籃子未勝出=int(int((s <= 0).sum())) if len(s) else 0))
    grow = pd.DataFrame(grow)
    grow.to_csv(V3 / "對照——增長者分組.csv", index=False, encoding="utf-8-sig")

    # ---- 清單增量:清單減每個簡單規則(逐宗,事件等權)
    inc = []
    for rule in ("b", "c", "d"):
        a = per[(per["樣本"] == "七宗") & (per["規則"] == "a") & (per["列型"] == "彙總")]
        b = per[(per["樣本"] == "七宗") & (per["規則"] == rule) & (per["列型"] == "彙總")]
        d = a[["event_id", "相對籃子中位"]].rename(columns={"相對籃子中位": "清單"}).merge(
            b[["event_id", "相對籃子中位"]].rename(columns={"相對籃子中位": "規則"}),
            on="event_id", how="inner")
        d["差"] = d["清單"] - d["規則"]
        for _, r in d.iterrows():
            inc.append(dict(對照規則=rule, event_id=r["event_id"],
                            清單=round(float(r["清單"]), 4), 簡單規則=round(float(r["規則"]), 4),
                            差=round(float(r["差"]), 4)))
        inc.append(dict(對照規則=rule, event_id="跨宗中位",
                        清單=round(float(d["清單"].median()), 4),
                        簡單規則=round(float(d["規則"].median()), 4),
                        差=round(float(d["差"].median()), 4)))
    inc = pd.DataFrame(inc)
    inc.to_csv(V3 / "對照——清單增量.csv", index=False, encoding="utf-8-sig")

    log("== 四規則彙總 ==")
    log(summ.to_string(index=False))
    log("== 逐宗剔走 ==")
    log(loo.pivot(index="剔走事件", columns="規則", values="其餘六宗中位").to_string())
    log("== 重疊度 ==")
    log(ov.to_string(index=False))
    log("== 增長者分組 ==")
    log(grow.to_string(index=False))
    log("== 清單增量 ==")
    log(inc.to_string(index=False))
    log("wrote 對照——簡單篩選.csv / 對照——四規則彙總.csv / 對照——逐宗剔走.csv / "
        "對照——重疊度.csv / 對照——增長者分組.csv / 對照——清單增量.csv / 對照——財務簡篩取數.csv")


if __name__ == "__main__":
    main()
