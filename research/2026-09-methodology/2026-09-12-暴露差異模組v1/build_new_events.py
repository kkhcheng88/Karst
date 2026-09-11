# -*- coding: utf-8 -*-
"""KARST-218 樣本外新事件(E17-E20):籃子、衝擊窗、T/N 兩錨與十二個月超額。

**算法照 KARST-199 `build_baskets.py` 一字不改的口徑**(直接 import 199 的 `basket_core`:
同一套 `load_spy` / `load_prices` / `build_wide` / `resolve_tickers` / `PanelFeatures` 與
同一條 `excess()` 進場規矩),只把輸入換成 `new_events_spec.json`、輸出落到本票目錄。
**不寫入 199 目錄任何檔。**

輸出:
  out/event_list_new.csv      事件清單(日期、敘事、來源、籃子大小、籃子相對跌幅、T 低點)
  out/basket_members_new.csv  逐宗逐家(解析狀態、衝擊跌幅、T/N 兩錨 3/6/12 個月超額、事前特徵)
  out/unresolved_new.csv      解析不到的點名代號(倖存者偏差正本)
  out/dispersion_new.csv      籃內分散度(新聞點名,三窗口 T/N 兩錨)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
B199 = ROOT / "research" / "2026-09-methodology" / "2026-09-10-①行業殺錯事件籃子"
OUT = HERE / "out"
OUT.mkdir(parents=True, exist_ok=True)
SPEC = HERE / "new_events_spec.json"

sys.path.insert(0, str(B199))
from basket_core import (HORIZONS, PanelFeatures, build_wide, load_prices,  # noqa: E402
                         load_spy, log, resolve_tickers)


def excess(px_wide, spy, cal, eid, anchor_i: int, h: int):
    """照 199 `build_baskets.excess`:錨日之後下一個交易日收市進場,持有 h 個交易日。"""
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

    log("[1/4] 讀價格庫與 SPY")
    spy_df = load_spy()
    px = load_prices()
    cal, wide, spy = build_wide(px, spy_df)
    cal = pd.DatetimeIndex(cal)
    dvw = (px.assign(dv=px["close"] * px["volume"])
             .pivot_table(index="date", columns="entity_id", values="dv", aggfunc="last")
             .reindex(cal))
    dollar_vol = {c: dvw[c] for c in dvw.columns}
    log(f"      日曆 {cal[0].date()} → {cal[-1].date()},{len(cal):,} 個交易日,{wide.shape[1]:,} 個實體")

    log("[2/4] 讀面板 v3(事前特徵)")
    pf = PanelFeatures()
    ent = pd.read_parquet(ROOT / "data" / "universe" / "entities.parquet",
                          columns=["entity_id", "name", "primary_ticker", "sic", "sic_description"])
    ent_map = ent.set_index("entity_id")
    ent_sic = ent.copy()
    ent_sic["sic2"] = ent_sic["sic"].astype("string").str.zfill(4).str[:2]

    log("[3/4] 逐宗建籃子")
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

        a_list = list(ev["tickers"])
        b_list = list(ev.get("tickers_headline_only", []))
        conf = {t.upper(): "A" for t in a_list}
        conf.update({t.upper(): "B" for t in b_list if t.upper() not in conf})
        res = resolve_tickers(a_list + [t for t in b_list if t.upper() not in
                                        {x.upper() for x in a_list}], t0)
        res["named_confidence"] = res["ticker"].map(conf)
        conf_by_entity = dict(zip(res["entity_id"], res["named_confidence"]))
        good = res[res["resolve_status"] == "已解析"]["entity_id"].tolist()
        for r in res[res["resolve_status"] != "已解析"].to_dict("records"):
            unres_rows.append(dict(event_id=eid_, event=ev["name"], **r))

        members = [e for e in good if e in wide.columns and np.isfinite(wide[e].iloc[i0])]
        for e in set(good) - set(members):
            unres_rows.append(dict(event_id=eid_, event=ev["name"],
                                   ticker=ent_map["primary_ticker"].get(e, ""),
                                   entity_id=e, resolve_status="已解析但衝擊起日無報價"))
        if len(members) < 3:
            log(f"      ! {eid_} {ev['name']}:可用成員只有 {len(members)} 家")

        sic_members: list[str] = []
        if ev.get("sic2_basket"):
            want = set(str(s).zfill(2) for s in ev["sic2_basket"])
            for e in ent_sic[ent_sic["sic2"].isin(want)]["entity_id"].tolist():
                if e in wide.columns and np.isfinite(wide[e].iloc[i0]):
                    hist = wide[e].iloc[max(0, i0 - 250):i0 + 1]
                    if hist.notna().sum() >= 200:
                        sic_members.append(e)

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
                dv = dollar_vol.get(e)
                rec["dollar_vol_60d"] = float(dv.iloc[max(0, i0 - 59):i0 + 1].median()) if dv is not None else np.nan
                rec.update(pf.at(e, t0, px_close))
                mem_rows.append(rec)

        ev_rows.append(dict(
            event_id=eid_, name=ev["name"], narrative=ev["narrative"],
            shock_start=t0.date(), trough_date=t_trough.date(),
            news_shock_end=cal[i_news_end].date(),
            basket_rel_drawdown=round(basket_drop, 4),
            basket_definition=ev["basket_definition"], basket_source=ev["basket_source"],
            n_named=len(conf), n_named_A=len(a_list), n_named_B=len(conf) - len(a_list),
            n_resolved=len(good), n_usable=len(members),
            n_lost_to_survivorship=len(conf) - len(members),
            sic2_basket=",".join(str(s).zfill(2) for s in ev.get("sic2_basket", [])),
            n_sic_basket=len(sic_members),
            sources=" | ".join(f"{s['outlet']} {s['date']} {s['url']} [{s.get('verified','')}]"
                               for s in ev["sources"]),
            notes=ev.get("notes", "")))
        log(f"      {eid_} {ev['name']}: 點名 {len(conf)} → 可用 {len(members)}"
            f",籃子相對跌 {basket_drop:.1%},低點 {t_trough.date()},新聞結束 {cal[i_news_end].date()}")

    evdf = pd.DataFrame(ev_rows)
    memdf = pd.DataFrame(mem_rows)
    evdf.to_csv(OUT / "event_list_new.csv", index=False, encoding="utf-8-sig")
    memdf.to_csv(OUT / "basket_members_new.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(unres_rows).to_csv(OUT / "unresolved_new.csv", index=False, encoding="utf-8-sig")

    log("[4/4] 籃內分散度")
    rows = []
    for (evid, evname, kind), g in memdf.groupby(["event_id", "event", "basket_kind"], sort=False):
        for tag, aname in (("T", "衝擊低點"), ("N", "衝擊結束日(新聞)")):
            for hn in HORIZONS:
                v = g[f"{tag}_{hn}_excess"].dropna()
                mature = int((g[f"{tag}_{hn}_status"] == "已成熟").sum())
                if len(v) == 0:
                    rows.append(dict(event_id=evid, event=evname, 籃子=kind, 口徑=aname, 窗口=hn,
                                     n=0, 成熟數=mature, 備註="無成熟樣本"))
                    continue
                lo = v.nsmallest(max(1, int(round(len(v) * 0.2)))).mean()
                hi = v.nlargest(max(1, int(round(len(v) * 0.2)))).mean()
                rows.append(dict(event_id=evid, event=evname, 籃子=kind, 口徑=aname, 窗口=hn,
                                 n=int(len(v)), 成熟數=mature,
                                 中位=round(float(v.median()), 4), 平均=round(float(v.mean()), 4),
                                 前20均=round(float(hi), 4), 後20均=round(float(lo), 4),
                                 前後20差距=round(float(hi - lo), 4),
                                 贏家比例=round(float((v > 0).mean()), 4),
                                 最好=round(float(v.max()), 4), 最差=round(float(v.min()), 4),
                                 標準差=round(float(v.std()), 4)))
    pd.DataFrame(rows).to_csv(OUT / "dispersion_new.csv", index=False, encoding="utf-8-sig")
    log("完成。")
    log(evdf[["event_id", "shock_start", "trough_date", "basket_rel_drawdown",
              "n_named", "n_usable", "n_lost_to_survivorship"]].to_string(index=False))


if __name__ == "__main__":
    main()
