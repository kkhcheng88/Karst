# -*- coding: utf-8 -*-
"""KARST-199 第一、二步:事件籃子成員、衝擊窗、籃內分散度。

讀 events_spec.json(人手編、每宗附兩條以上新聞出處),輸出:
  out/event_list.csv          事件清單(日期、敘事、籃子定義、來源、籃子大小)
  out/basket_members.csv      每宗籃子逐個成員(含解析狀態、衝擊跌幅、三/六/十二個月超額、事前特徵)
  out/unresolved_tickers.csv  解析不到的點名代號(倖存者偏差正本)
  out/dispersion.csv          籃內分散度表(兩個口徑 × 三個窗口)
  out/pool_compare.csv        同期①個股池對照
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from basket_core import (HERE, OUT, HORIZONS, ROOT, PanelFeatures, build_wide,
                         load_prices, load_spy, log, resolve_tickers, to_json)

SPEC = HERE / "events_spec.json"
POOL_EVENTS = ROOT / "research" / "2026-09-methodology" / "2026-09-09-①基準率表" / "out" / "events.csv"


def excess(px_wide, spy, cal, eid, anchor_i: int, h: int):
    """由錨日之後下一個交易日收市進場,持有 h 個交易日的相對大市超額。"""
    en = anchor_i + 1
    tgt = en + h
    if en >= len(cal) or tgt >= len(cal):
        return np.nan, "未成熟"
    s = px_wide[eid]
    base, end = s.iloc[en], s.iloc[tgt]
    if not np.isfinite(base) or not np.isfinite(end) or base <= 0:
        return np.nan, "資料不足"
    sret = end / base - 1.0
    mret = spy.iloc[tgt] / spy.iloc[en] - 1.0
    return (1 + sret) / (1 + mret) - 1.0, "已成熟"


def main() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    events = spec["events"]

    log("[1/5] 讀價格庫與 SPY")
    spy_df = load_spy()
    px = load_prices()
    cal, wide, spy = build_wide(px, spy_df)
    cal = pd.DatetimeIndex(cal)
    dvw = (px.assign(dv=px["close"] * px["volume"])
             .pivot_table(index="date", columns="entity_id", values="dv", aggfunc="last")
             .reindex(cal))
    dollar_vol = {c: dvw[c] for c in dvw.columns}
    log(f"      日曆 {cal[0].date()} → {cal[-1].date()},{len(cal):,} 個交易日,{wide.shape[1]:,} 個實體")

    log("[2/5] 讀面板 v3(事前特徵)")
    pf = PanelFeatures()

    ent = pd.read_parquet(ROOT / "data" / "universe" / "entities.parquet",
                          columns=["entity_id", "name", "primary_ticker", "sic", "sic_description"])
    ent_map = ent.set_index("entity_id")
    ent_sic = ent.copy()
    ent_sic["sic2"] = ent_sic["sic"].astype("string").str.zfill(4).str[:2]

    log("[3/5] 逐宗事件建籃子")
    ev_rows, mem_rows, unres_rows = [], [], []

    for ev in events:
        eid_ = ev["event_id"]
        t0 = pd.Timestamp(ev["shock_start"])
        t_news_end = pd.Timestamp(ev["news_shock_end"])
        i0 = int(cal.searchsorted(t0, side="left"))
        if i0 >= len(cal):
            raise SystemExit(f"{eid_} 衝擊起日超出日曆")
        t0 = cal[i0]
        i_news_end = int(min(cal.searchsorted(t_news_end, side="right") - 1, len(cal) - 1))

        # A 級 = 當時報導全文逐隻點名;B 級 = 只有標題/板塊級覆蓋,出處較弱,分開記
        a_list = list(ev["tickers"])
        b_list = list(ev.get("tickers_headline_only", []))
        conf_by_ticker = {t.upper(): "A" for t in a_list}
        conf_by_ticker.update({t.upper(): "B" for t in b_list if t.upper() not in conf_by_ticker})
        res = resolve_tickers(a_list + [t for t in b_list if t.upper() not in
                                        {x.upper() for x in a_list}], t0)
        res["named_confidence"] = res["ticker"].map(conf_by_ticker)
        conf_by_entity = dict(zip(res["entity_id"], res["named_confidence"]))
        good = res[res["resolve_status"] == "已解析"]["entity_id"].tolist()
        for r in res[res["resolve_status"] != "已解析"].to_dict("records"):
            unres_rows.append(dict(event_id=eid_, event=ev["name"], **r))

        # 有價的成員:衝擊起日與其後都要有報價
        members = [e for e in good if e in wide.columns and np.isfinite(wide[e].iloc[i0])]
        for e in set(good) - set(members):
            unres_rows.append(dict(event_id=eid_, event=ev["name"], ticker=ent_map["primary_ticker"].get(e, ""),
                                   entity_id=e, resolve_status="已解析但衝擊起日無報價"))
        if len(members) < 3:
            log(f"      ! {eid_} {ev['name']}:可用成員只有 {len(members)} 家,仍照出但標明")

        # --- 對照籃子:同 SIC 兩位全體(新聞點名天然偏向跌得最勁那幾隻,要有一個不揀人的對照)
        sic_members: list[str] = []
        if ev.get("sic2_basket"):
            want = set(str(s).zfill(2) for s in ev["sic2_basket"])
            pool_e = ent_sic[ent_sic["sic2"].isin(want)]["entity_id"].tolist()
            for e in pool_e:
                if e in wide.columns and np.isfinite(wide[e].iloc[i0]):
                    s = wide[e]
                    hist = s.iloc[max(0, i0 - 250):i0 + 1]
                    if hist.notna().sum() >= 200:
                        sic_members.append(e)

        # --- 籃子相對大市指數(等權),尋找衝擊低點
        search_hi = int(min(i_news_end + 21, len(cal) - 1))
        seg = wide.loc[:, members].iloc[i0:search_hi + 1]
        rel = seg.div(seg.iloc[0], axis=1).div(spy.iloc[i0:search_hi + 1] / spy.iloc[i0], axis=0)
        basket_rel = rel.mean(axis=1, skipna=True)
        i_trough = i0 + int(np.nanargmin(basket_rel.to_numpy()))
        t_trough = cal[i_trough]
        basket_drop = float(basket_rel.min() - 1.0)

        anchors = {"衝擊低點": i_trough, "衝擊結束日(新聞)": i_news_end}

        for kind, mem_list in (("新聞點名", members), ("同SIC全體", sic_members)):
            for e in mem_list:
                rec = dict(event_id=eid_, event=ev["name"], basket_kind=kind, entity_id=e,
                           ticker=ent_map["primary_ticker"].get(e, ""),
                           name=ent_map["name"].get(e, ""),
                           sic=ent_map["sic"].get(e, ""),
                           sic_description=ent_map["sic_description"].get(e, ""),
                           named_confidence=conf_by_entity.get(e, "") if kind == "新聞點名" else "")
                s = wide[e]
                # 衝擊期自身相對大市跌幅(起日 → 籃子低點)
                b, x = s.iloc[i0], s.iloc[i_trough]
                m = spy.iloc[i_trough] / spy.iloc[i0] - 1.0
                rec["f_shock_rel_drop"] = ((x / b) / (1 + m) - 1.0) if np.isfinite(b) and np.isfinite(x) and b > 0 else np.nan
                for aname, ai in anchors.items():
                    tag = "T" if aname == "衝擊低點" else "N"
                    rec[f"anchor_{tag}_date"] = cal[ai]
                    for hn, hh in HORIZONS.items():
                        v, st = excess(wide, spy, cal, e, ai, hh)
                        rec[f"{tag}_{hn}_excess"] = v
                        rec[f"{tag}_{hn}_status"] = st
                px_close = float(s.iloc[i0])
                # 衝擊起日前 60 個交易日的中位成交金額(可交易性,不作閘只作欄)
                dv = dollar_vol.get(e)
                rec["dollar_vol_60d"] = float(dv.iloc[max(0, i0 - 59):i0 + 1].median()) if dv is not None else np.nan
                rec.update(pf.at(e, t0, px_close))
                mem_rows.append(rec)

        ev_rows.append(dict(
            event_id=eid_, name=ev["name"], narrative=ev["narrative"],
            shock_start=t0.date(), trough_date=t_trough.date(),
            news_shock_end=cal[i_news_end].date(),
            basket_rel_drawdown=round(basket_drop, 4),
            basket_definition=ev["basket_definition"],
            basket_source=ev["basket_source"],
            n_named=len(conf_by_ticker), n_named_A=len(a_list),
            n_named_B=len(conf_by_ticker) - len(a_list),
            n_resolved=len(good), n_usable=len(members),
            n_lost_to_survivorship=len(conf_by_ticker) - len(members),
            sic2_basket=",".join(str(s).zfill(2) for s in ev.get("sic2_basket", [])),
            n_sic_basket=len(sic_members),
            in_main_sample=ev.get("in_main_sample", True),
            end_date_sourced=ev.get("end_date_sourced", True),
            sources=" | ".join(f"{s['outlet']} {s['date']} {s['url']}" for s in ev["sources"]),
            notes=ev.get("notes", ""),
        ))
        log(f"      {eid_} {ev['name']}: 點名 {len(ev['tickers'])} → 可用 {len(members)}"
            f",籃子相對跌 {basket_drop:.1%},低點 {t_trough.date()}")

    evdf = pd.DataFrame(ev_rows)
    memdf = pd.DataFrame(mem_rows)
    evdf.to_csv(OUT / "event_list.csv", index=False, encoding="utf-8-sig")
    memdf.to_csv(OUT / "basket_members.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(unres_rows).to_csv(OUT / "unresolved_tickers.csv", index=False, encoding="utf-8-sig")

    log("[4/5] 籃內分散度")
    disp_rows = []
    # 對照籃子加一條可交易線(衝擊前 60 日中位成交金額 >= 100 萬美元),與新聞點名的流動性拉近
    liq = memdf[(memdf["basket_kind"] == "同SIC全體") & (memdf["dollar_vol_60d"] >= 1e6)].copy()
    liq["basket_kind"] = "同SIC全體(成交額≥100萬)"
    # 只用 A 級出處(當時報導全文逐隻點名)的新聞籃子,答「弱出處名單有沒有拉高成績」
    agrade = memdf[(memdf["basket_kind"] == "新聞點名") & (memdf["named_confidence"] == "A")].copy()
    agrade["basket_kind"] = "新聞點名(只計A級出處)"
    memdf = pd.concat([memdf, liq, agrade], ignore_index=True)
    for (evid, evname, kind), g in memdf.groupby(["event_id", "event", "basket_kind"], sort=False):
        for tag, aname in (("T", "衝擊低點"), ("N", "衝擊結束日(新聞)")):
            for hn in HORIZONS:
                v = g[f"{tag}_{hn}_excess"].dropna()
                mature = (g[f"{tag}_{hn}_status"] == "已成熟").sum()
                if len(v) == 0:
                    disp_rows.append(dict(event_id=evid, event=evname, 籃子=kind, 口徑=aname, 窗口=hn,
                                          n=0, 成熟數=int(mature), 備註="無成熟樣本"))
                    continue
                lo = v.nsmallest(max(1, int(round(len(v) * 0.2)))).mean()
                hi = v.nlargest(max(1, int(round(len(v) * 0.2)))).mean()
                disp_rows.append(dict(
                    event_id=evid, event=evname, 籃子=kind, 口徑=aname, 窗口=hn, n=int(len(v)), 成熟數=int(mature),
                    中位=round(float(v.median()), 4), 平均=round(float(v.mean()), 4),
                    Q1=round(float(v.quantile(0.25)), 4), Q3=round(float(v.quantile(0.75)), 4),
                    四分位距=round(float(v.quantile(0.75) - v.quantile(0.25)), 4),
                    前20均=round(float(hi), 4), 後20均=round(float(lo), 4),
                    前後20差距=round(float(hi - lo), 4),
                    贏家比例=round(float((v > 0).mean()), 4),
                    最好=round(float(v.max()), 4), 最差=round(float(v.min()), 4),
                    標準差=round(float(v.std()), 4)))
    disp = pd.DataFrame(disp_rows)
    disp.to_csv(OUT / "dispersion.csv", index=False, encoding="utf-8-sig")

    log("[5/5] 同期①個股池對照")
    pool = pd.read_csv(POOL_EVENTS, low_memory=False,
                       usecols=["entity_id", "trigger_date", "gate_cf", "gate_debt_n2", "gate_mcap",
                                "A_3m_excess", "A_6m_excess", "A_12m_excess",
                                "A_3m_status", "A_6m_status", "A_12m_status"])
    pool["trigger_date"] = pd.to_datetime(pool["trigger_date"])
    pool_rows = []

    def pstat(v, label, evid, evname, window):
        v = v.dropna()
        if len(v) == 0:
            return dict(event_id=evid, event=evname, 池=label, 窗口=window, n=0)
        lo = v.nsmallest(max(1, int(round(len(v) * 0.2)))).mean()
        hi = v.nlargest(max(1, int(round(len(v) * 0.2)))).mean()
        return dict(event_id=evid, event=evname, 池=label, 窗口=window, n=int(len(v)),
                    中位=round(float(v.median()), 4), 平均=round(float(v.mean()), 4),
                    前後20差距=round(float(hi - lo), 4),
                    贏家比例=round(float((v > 0).mean()), 4),
                    最好=round(float(v.max()), 4), 最差=round(float(v.min()), 4))

    for r in evdf.itertuples(index=False):
        lo_d = pd.Timestamp(r.shock_start) - pd.Timedelta(days=60)
        hi_d = pd.Timestamp(r.trough_date) + pd.Timedelta(days=60)
        sub = pool[(pool["trigger_date"] >= lo_d) & (pool["trigger_date"] <= hi_d)]
        for hn in ("3m", "6m", "12m"):
            pool_rows.append(pstat(sub[f"A_{hn}_excess"], "①池 全部觸發", r.event_id, r.name, hn))
            pool_rows.append(pstat(sub[sub["gate_cf"] == True][f"A_{hn}_excess"],
                                   "①池 過現金流閘(D-173 口徑)", r.event_id, r.name, hn))
    for hn in ("3m", "6m", "12m"):
        pool_rows.append(pstat(pool[f"A_{hn}_excess"], "①池 全期全部觸發", "ALL", "全期基線", hn))
        pool_rows.append(pstat(pool[pool["gate_cf"] == True][f"A_{hn}_excess"],
                               "①池 全期過現金流閘", "ALL", "全期基線", hn))
    pd.DataFrame(pool_rows).to_csv(OUT / "pool_compare.csv", index=False, encoding="utf-8-sig")

    to_json(dict(n_events=len(events),
                 n_main=int(evdf["in_main_sample"].sum()),
                 n_members=int(len(memdf)),
                 n_unresolved=int(len(unres_rows)),
                 calendar_first=str(cal[0].date()), calendar_last=str(cal[-1].date())),
            OUT / "build_stats.json")
    log("完成。")


if __name__ == "__main__":
    main()
