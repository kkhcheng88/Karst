# -*- coding: utf-8 -*-
"""KARST-213 批 2(E05/E06/E07/E10/E11)取證包。

照 KARST-204 `checklist_test/build_packets.py` 與 `執行口徑.md`,加三樣 v3 步六/步七要用的
衝擊前資料(全部截到衝擊起日之前):
  1. 衝擊起日當日(即反應前最後一個收市)的實際收市價、52 週高低;
  2. 該股衝擊前一年市銷率(P/S)區間(中位/低/高),算法 = 日線收市價 × panel 股數 ÷ panel TTM 收入;
  3. 同宗事件、同 SIC 兩位主類的同業當期 P/S 中位(只作對照錨,不作公平價值)。
另加折現率:口徑 = 十年期美債(^TNX 收市代理)該日值 + 5.00 個百分點(FRED DGS10 無本地檔,
用 CBOE 10 年孳息指數代理,記明)。

**明文遮蔽**:T_3m/6m/12m、N_3m/6m/12m 六欄連兩個錨日一律不入包;衝擊後價格一律不入包。
遮蔽由本腳本機械保證,不靠判斷隊自律。
"""
import csv
import json
import os
import statistics as st

ROOT = "C:/projects/Karst"
BASE = ROOT + "/research/2026-09-methodology/2026-09-10-①行業殺錯事件籃子"
OUT = (ROOT + "/research/2026-09-methodology/2026-09-11-①v3全量回測/批2/packets")
EVENTS = ["E05", "E06", "E07", "E10", "E11"]
PRICES = ROOT + "/data/prices/daily"
PANEL = ROOT + "/data/panel/quarterly_v3.parquet"
SUB = ROOT + "/data/sec/submissions/CIK{cik}.json"
TXT = ROOT + "/data/sec/10k_text"

REDACT = {"T_3m_excess", "T_3m_status", "T_6m_excess", "T_6m_status",
          "T_12m_excess", "T_12m_status", "N_3m_excess", "N_3m_status",
          "N_6m_excess", "N_6m_status", "N_12m_excess", "N_12m_status",
          "anchor_T_date", "anchor_N_date"}

KEEP = ["ticker", "name", "entity_id", "sic", "sic_description", "named_confidence",
        "f_shock_rel_drop", "panel_period_end", "panel_filed", "panel_age_days", "currency",
        "ttm_revenue", "ttm_ocf", "ttm_net_income", "cash", "total_debt",
        "assets", "equity", "mcap_usd", "f_ps", "f_pb", "f_pe", "f_ocf_margin", "f_ni_margin",
        "f_net_cash_n2", "f_net_cash_over_mcap", "f_debt_to_assets", "f_liab_to_assets",
        "f_ocf_positive", "f_rev_growth_yoy", "f_rev_cv8", "dollar_vol_60d", "feat_status"]


def load_events():
    with open(BASE + "/events_spec.json", encoding="utf-8") as f:
        return {e["event_id"]: e for e in json.load(f)["events"]}


def prefilings(cik, cutoff):
    path = SUB.format(cik=cik)
    if not os.path.exists(path):
        return {"note": "本地無 submissions 快取,取證請打 EDGAR"}
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    r = d.get("filings", {}).get("recent", {})
    rows = []
    for i in range(len(r.get("form", []))):
        if r["filingDate"][i] < cutoff:
            rows.append({"form": r["form"][i], "filingDate": r["filingDate"][i],
                         "reportDate": r["reportDate"][i],
                         "accessionNumber": r["accessionNumber"][i],
                         "primaryDocument": r["primaryDocument"][i]})
    out = {}
    for form, n in (("10-K", 1), ("10-Q", 2), ("8-K", 3)):
        sel = [x for x in rows if x["form"] == form][:n]
        for j, s in enumerate(sel):
            acc = s["accessionNumber"].replace("-", "")
            key = form if n == 1 else "%s[%d]" % (form, j)
            out[key] = {
                "filingDate": s["filingDate"], "reportDate": s["reportDate"],
                "accession": s["accessionNumber"],
                "url": ("https://www.sec.gov/Archives/edgar/data/%d/%s/%s"
                        % (int(cik), acc, s["primaryDocument"])),
            }
    return out


def local_10k(ticker, acc):
    if not acc:
        return None
    p = "%s/%s_%s.txt.gz" % (TXT, ticker, acc.replace("-", ""))
    return p if os.path.exists(p) else None


def main():
    import numpy as np
    import pandas as pd

    os.makedirs(OUT, exist_ok=True)
    events = load_events()
    with open(BASE + "/out/basket_members.csv", encoding="utf-8-sig") as f:
        allrows = list(csv.DictReader(f))
    rows = [r for r in allrows if r["event_id"] in EVENTS]

    # 折現率:^TNX(CBOE 10 年孳息指數,收市)衝擊前最後一個交易日 + 5.00 個百分點
    try:
        import yfinance as yf
        tnx = yf.download("^TNX", start="2016-01-01", end="2025-02-15",
                          progress=False, auto_adjust=False)
        tnx = tnx["Close"]
        if hasattr(tnx, "columns"):
            tnx = tnx.iloc[:, 0]
        tnx = tnx.dropna()
        tnx.index = pd.to_datetime(tnx.index).tz_localize(None)
    except Exception as e:  # noqa: BLE001
        print("WARN ^TNX 抓取失敗:", e)
        tnx = None

    # 價格(只取衝擊起日或之前)
    pxcols = ["entity_id", "date", "close"]
    frames = []
    for p in sorted(os.listdir(PRICES)):
        if p.endswith(".parquet"):
            d = pd.read_parquet(PRICES + "/" + p, columns=pxcols + ["series_role"])
            frames.append(d[d["series_role"] == "primary"].drop(columns=["series_role"]))
    px = pd.concat(frames, ignore_index=True)
    px["date"] = pd.to_datetime(px["date"])
    px["close"] = px["close"].astype("float64")

    pan = pd.read_parquet(PANEL, columns=["entity_id", "period_end", "filed_date",
                                          "shares_outstanding", "shares_scale_suspect"])
    pan["period_end"] = pd.to_datetime(pan["period_end"])

    summary = []
    for eid in EVENTS:
        ev = events[eid]
        cutoff = ev["shock_start"]
        cut = pd.Timestamp(cutoff)
        pack = {"event_id": eid, "name": ev["name"], "narrative": ev["narrative"],
                "shock_start": ev["shock_start"], "news_shock_end": ev.get("news_shock_end"),
                "basket_definition": ev["basket_definition"], "basket_source": ev["basket_source"],
                "sources": ev.get("sources"),
                "evidence_cutoff": "申報日 / 價格日 < %s(起日當日收市 = 反應前最後一個收市)" % cutoff,
                "redacted": sorted(REDACT),
                "companies": []}
        # 折現率
        if tnx is not None:
            try:
                v = float(tnx.loc[:cut].iloc[-1])
                pack["discount"] = {
                    "dgs10_pct": round(v, 3),
                    "dgs10_asof": str(tnx.loc[:cut].index[-1].date()),
                    "equity_premium_pp": 5.0,
                    "discount_rate": round(v + 5.0, 3),
                    "note": "口徑:FRED DGS10 + 5pp。本地無 DGS10 檔,以 CBOE 10 年孳息指數(^TNX)收市代理,推算。",
                }
            except Exception:  # noqa: BLE001
                pack["discount"] = {"note": "查不到:^TNX 無該日或之前數據"}
        else:
            pack["discount"] = {"note": "查不到:^TNX 抓取失敗"}

        mem = [r for r in rows if r["event_id"] == eid and r["basket_kind"] == "新聞點名"]
        peers = [r for r in rows if r["event_id"] == eid and r["basket_kind"] == "同SIC全體"]
        peer_by_sic2 = {}
        for s2 in sorted({(r["sic"] or "")[:2] for r in peers}):
            vals = []
            for r in peers:
                if (r["sic"] or "")[:2] != s2:
                    continue
                try:
                    v = float(r["f_ps"])
                except (TypeError, ValueError):
                    continue
                if v > 0 and (r["panel_filed"] or "9999") < cutoff:
                    vals.append(v)
            if vals:
                peer_by_sic2[s2] = {"n": len(vals), "ps_median": round(st.median(vals), 3),
                                    "ps_p25": round(float(np.percentile(vals, 25)), 3),
                                    "ps_p75": round(float(np.percentile(vals, 75)), 3)}

        for m in mem:
            c = {k: m.get(k) for k in KEEP}
            eid_ = m["entity_id"]
            cik = eid_
            pf = prefilings(cik, cutoff) if cik else {"note": "無 CIK"}
            acc = pf.get("10-K", {}).get("accession") if isinstance(pf, dict) else None
            c["prefilings"] = pf
            c["local_10k_gz"] = local_10k(m["ticker"], acc)
            # 價格區塊
            sub_px = px[(px["entity_id"] == eid_) & (px["date"] <= cut)].sort_values("date")
            sub_px = sub_px.tail(253)
            blk = {"note": "價格只取衝擊起日或之前;P/S 為推算"}
            if len(sub_px):
                cl = sub_px["close"].values
                blk["asof"] = str(sub_px["date"].iloc[-1].date())
                blk["close"] = round(float(cl[-1]), 4)
                blk["px_52w_high"] = round(float(cl.max()), 4)
                blk["px_52w_low"] = round(float(cl.min()), 4)
                blk["pct_below_52w_high"] = round(float(cl[-1] / cl.max() - 1.0), 4)
            # 股數(衝擊前最後一筆 panel 記錄)
            sh = pan[(pan["entity_id"] == eid_) & (pan["period_end"] <= cut)]
            sh = sh.sort_values("period_end")
            if len(sh):
                blk["shares_outstanding"] = float(sh["shares_outstanding"].iloc[-1])
                blk["shares_period_end"] = str(sh["period_end"].iloc[-1].date())
                blk["shares_scale_suspect"] = bool(sh["shares_scale_suspect"].iloc[-1])
            try:
                rev = float(m["ttm_revenue"])
            except (TypeError, ValueError):
                rev = None
            if rev and blk.get("shares_outstanding") and len(sub_px):
                sh_ = blk["shares_outstanding"]
                ps = sub_px["close"].values * sh_ / rev
                blk["ps_1y_median"] = round(float(np.median(ps)), 3)
                blk["ps_1y_low"] = round(float(ps.min()), 3)
                blk["ps_1y_high"] = round(float(ps.max()), 3)
                blk["ps_at_shock"] = round(float(ps[-1]), 3)
                blk["ps_formula"] = "日線收市價 × panel 股數 ÷ panel TTM 收入(推算)"
            c["price_block"] = blk
            c["peers_sic2"] = peer_by_sic2.get((m["sic"] or "")[:2], {})
            pack["companies"].append(c)
        pack["peers_by_sic2"] = peer_by_sic2
        with open("%s/%s.json" % (OUT, eid), "w", encoding="utf-8") as f:
            json.dump(pack, f, ensure_ascii=False, indent=1)
        n_local = sum(1 for c in pack["companies"] if c["local_10k_gz"])
        summary.append((eid, ev["name"], len(mem), n_local,
                        pack["discount"].get("discount_rate")))

    for s in summary:
        print(s[0], s[2], "家, 本地 10-K 全文", s[3], "份, 折現率", s[4], "-", s[1])
    # 自檢:包內不准出現被遮蔽欄名
    for eid in EVENTS:
        t = open("%s/%s.json" % (OUT, eid), encoding="utf-8").read()
        bad = [k for k in REDACT if '"%s":' % k in t or '"%s": ' % k in t]
        print("REDACT-CHECK", eid, "FAIL " + ",".join(bad) if bad else "PASS")


if __name__ == "__main__":
    main()
