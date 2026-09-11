# -*- coding: utf-8 -*-
"""KARST-212 批 1:衝擊起日前一日收市價、股數、市值、EV,以及折現率用的十年息。

全部只用「衝擊起日之前」的資料:
  價  = data/prices/daily 內,衝擊起日之前最後一個交易日收市
  股數 = data/sec/companyfacts 內 dei:EntityCommonStockSharesOutstanding(封面頁,≤ 起日)
  負債/現金 = 取證包面板(最後一期 ≤ 起日)
  利率 = FRED DGS10 該日值 + 5 個百分點(v3 口徑第二節)

輸出:out/market_snapshot.csv(逐家一行)。
"""
import csv
import glob
import gzip
import json
import os

import pandas as pd

ROOT = "C:/projects/Karst"
BASE = f"{ROOT}/research/2026-09-methodology/2026-09-11-①v3全量回測/批1"
FACTS = ROOT + "/data/sec/companyfacts/CIK{cik}.json.gz"
FRED = BASE + "/dgs10.csv"

PICKS = [
    ("E01", "T", "0000732717", "2013-05-21"),
    ("E01", "SPG", "0001063761", "2013-05-21"),
    ("E01", "NLY", "0001043219", "2013-05-21"),
    ("E01", "ED", "0001047862", "2013-05-21"),
    ("E02", "BIIB", "0000875045", "2015-09-18"),
    ("E02", "REGN", "0000872589", "2015-09-18"),
    ("E02", "GILD", "0000882095", "2015-09-18"),
    ("E02", "JNJ", "0000200406", "2015-09-18"),
    ("E03", "UNFI", "0001020859", "2017-06-15"),
    ("E03", "KR", "0000056873", "2017-06-15"),
    ("E03", "SFM", "0001575515", "2017-06-15"),
    ("E03", "GIS", "0000040704", "2017-06-15"),
    ("E04", "ZM", "0001585521", "2021-02-12"),
    ("E04", "PTON", "0001639825", "2021-02-12"),
    ("E04", "TDOC", "0001477449", "2021-02-12"),
    ("E04", "FSLY", "0001517413", "2021-02-12"),
    ("E09", "OXY", "0000797468", "2014-11-26"),
    ("E09", "RIG", "0001451505", "2014-11-26"),
    ("E09", "HAL", "0000045012", "2014-11-26"),
    ("E09", "CVX", "0000093410", "2014-11-26"),
]


def load_prices():
    frames = []
    for p in sorted(glob.glob(ROOT + "/data/prices/daily/part_*.parquet")):
        df = pd.read_parquet(p, columns=["ticker", "date", "close", "series_role"])
        frames.append(df)
    allp = pd.concat(frames, ignore_index=True)
    allp["date"] = pd.to_datetime(allp["date"])
    return allp


def px(allp, tk, day, back=None):
    d = allp[(allp["ticker"] == tk) & (allp["date"] < pd.Timestamp(day))]
    if back:
        d = d[d["date"] <= pd.Timestamp(day) - pd.Timedelta(days=back)]
    if not len(d):
        return None, None
    r = d.iloc[-1]
    return str(r["date"].date()), float(r["close"])


def shares(cik, cutoff):
    p = FACTS.format(cik=cik)
    if not os.path.exists(p):
        return None
    d = json.load(gzip.open(p, "rt", encoding="utf-8"))
    f = d.get("facts", {}).get("dei", {}).get("EntityCommonStockSharesOutstanding")
    if not f:
        return None
    best = None
    for unit, arr in f["units"].items():
        for x in arr:
            if x.get("filed", "") <= cutoff and float(x.get("val") or 0) > 0:
                if best is None or x["filed"] > best["filed"]:
                    best = x
    return (float(best["val"]), best["filed"], best.get("end")) if best else None


def dgs10(day):
    best = None
    with open(FRED, encoding="utf-8") as f:
        for row in csv.reader(f):
            if row and row[0][:4].isdigit() and row[0] <= day and row[1] not in ("", "."):
                best = (row[0], float(row[1]))
    return best


def split_factor(tk, day):
    """價格庫 close 是拆股調整後;乘回衝擊日之後所有拆股比率 = 當時未調整價。"""
    try:
        import yfinance as yf
        s = yf.Ticker(tk).splits
    except Exception:
        return None, []
    f, used = 1.0, []
    for ts, r in s.items():
        if str(ts.date()) > day:
            f *= float(r)
            used.append((str(ts.date()), float(r)))
    return f, used


# companyfacts 缺 dei 股數的公司,由衝擊前申報封面頁抄出來(出處見 extracts/)
SHARES_OVERRIDE = {
    "ZM": (286007052.0, "10-Q 2020-12-04 封面頁 2020-11-20:A 198,715,606 + B 87,291,446"),
    "PTON": (294501665.0, "10-Q 2021-02-05 封面頁 2021-01-29:A 263,637,415 + B 30,864,250"),
    "FSLY": (113500000.0, "10-Q 2020-11-06 封面頁 2020-10-31:A 102.4M + B 11.1M"),
    "TDOC": (157120286.0, "10-Q 2020-11-06 XBRL 股本表 2020-09-30:72,761,941 + 84,358,345"),
}


def main():
    allp = load_prices()
    packs = {e: json.load(open(f"{BASE}/packets/{e}.json", encoding="utf-8"))
             for e in ("E01", "E02", "E03", "E04", "E09")}
    rows = []
    for eid, tk, cik, cutoff in PICKS:
        end = {"E01": "2013-06-25", "E02": "2015-09-28", "E03": "2017-06-23",
               "E04": "2021-03-09", "E09": "2015-01-30"}[eid]
        c = [x for x in packs[eid]["companies"] if x["ticker"] == tk]
        c = c[0] if c else {}
        d1, p1 = px(allp, tk, cutoff)
        d0, p0 = px(allp, tk, cutoff, back=400)
        sh = shares(cik, cutoff)
        sh_note = f"companyfacts dei filed {sh[1]}" if sh else ""
        if tk in SHARES_OVERRIDE:
            sh = (SHARES_OVERRIDE[tk][0], "封面頁", "")
            sh_note = SHARES_OVERRIDE[tk][1]
        sf, sf_used = split_factor(tk, cutoff)
        # 衝擊窗結束日收市(判斷時點),同窗起價,以及同窗 SPY 變動
        de, pe = px(allp, tk, end)
        dm, pm = px(allp, "SPY", cutoff)
        dn, pn = px(allp, "SPY", end)
        shock_drop = (pe / p1 - 1) if (pe and p1) else None
        raw = (p1 * sf) if (p1 and sf) else None
        rr = dgs10(cutoff)
        mcap = raw * sh[0] if (raw and sh) else None
        cash, debt = c.get("cash"), c.get("total_debt")
        cash = float(cash) if cash not in (None, "") else None
        debt = float(debt) if debt not in (None, "") else None
        ev = (mcap + debt - cash) if (mcap and debt is not None and cash is not None) else None
        rows.append({
            "event_id": eid, "ticker": tk, "shock_start": cutoff,
            "news_shock_end": end,
            "px_end_date": de, "px_end_raw": (pe * sf) if (pe and sf) else None,
            "px_end_over_start": shock_drop,
            "spy_start_over": (pn / pm - 1) if (pm and pn) else None,
            "px_date": d1, "px_close_raw": raw, "split_factor_after": sf,
            "splits_after": ";".join(f"{d}:{r}" for d, r in sf_used),
            "px_date_400d_earlier": d0, "px_400d_earlier": p0,
            "shares": sh[0] if sh else None, "shares_src": sh_note,
            "mcap_at_px": mcap, "cash": cash, "total_debt": debt, "ev": ev,
            "ttm_revenue": c.get("ttm_revenue"), "ttm_ocf": c.get("ttm_ocf"),
            "ttm_net_income": c.get("ttm_net_income"),
            "panel_period_end": c.get("panel_period_end"), "panel_filed": c.get("panel_filed"),
            "shock_rel_drop": c.get("f_shock_rel_drop"),
            "dgs10_date": rr[0] if rr else None, "dgs10": rr[1] if rr else None,
            "discount_rate_plus5": (rr[1] / 100 + 0.05) if rr else None,
        })
    os.makedirs(BASE + "/out", exist_ok=True)
    with open(BASE + "/out/market_snapshot.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    def f2(v, s=1e9, n=1):
        try:
            return round(float(v) / s, n)
        except (TypeError, ValueError):
            return None

    for r in rows:
        print(r["event_id"], r["ticker"], r["px_date"], f2(r["px_close_raw"], 1, 2),
              "mcap", f2(r["mcap_at_px"]), "ev", f2(r["ev"]),
              "rev", f2(r["ttm_revenue"], 1e9, 2),
              "dgs10", r["dgs10"])


if __name__ == "__main__":
    main()
