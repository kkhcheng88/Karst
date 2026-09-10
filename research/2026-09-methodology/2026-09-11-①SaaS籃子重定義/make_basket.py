# -*- coding: utf-8 -*-
"""KARST-209 步驟二至三:新籃子表 + 與 KARST-200 三十五家的對照。

口徑逐格照 KARST-200 的 make_basket.py(基準日 2026-01-12、急性期 01-13 至 02-27、
全期至價格日、相對大市 = 個股 adj close ÷ SPY adj close 基準日歸一、回補比例、
200 日線取 2026-02-05),**價格日同樣截在 2026-09-08**,令兩張表逐欄可對照。

市值只在「不在 35 家之內」的那批上抓(yfinance marketCap),抓不到留空。
"""
import json

import pandas as pd
import yfinance as yf

OUT = "C:/projects/Karst/research/2026-09-methodology/2026-09-11-①SaaS籃子重定義"
K200 = "C:/projects/Karst/research/2026-09-methodology/2026-09-10-①SaaS事件前瞻登記"

BASE_DATE = "2026-01-12"
ACUTE_END = "2026-02-27"
MA_CHECK = "2026-02-05"


def market_caps(tickers):
    """逐個抓市值;抓不到留 None。有快取就不再抓。"""
    import os
    cache = f"{OUT}/marketcap.csv"
    if os.path.exists(cache):
        d = pd.read_csv(cache)
        return dict(zip(d.ticker, d.market_cap))
    rows = []
    for t in tickers:
        mc = None
        try:
            fi = yf.Ticker(t).fast_info
            mc = fi.get("marketCap") if hasattr(fi, "get") else fi.market_cap
        except Exception:
            pass
        rows.append({"ticker": t, "market_cap": mc})
        print(f"  mcap {t}: {mc}")
    pd.DataFrame(rows).to_csv(cache, index=False, encoding="utf-8-sig")
    return dict(zip([r["ticker"] for r in rows], [r["market_cap"] for r in rows]))


def main():
    adj = pd.read_parquet(f"{OUT}/prices_adjclose.parquet")
    adj.index = pd.to_datetime(adj.index)
    vol = pd.read_parquet(f"{OUT}/prices_volume.parquet")
    vol.index = pd.to_datetime(vol.index)
    meta = json.load(open(f"{OUT}/prices.meta.json", encoding="utf-8"))
    price_date = pd.Timestamp(meta["price_date"])

    cons = pd.read_csv(f"{OUT}/constituents.csv")
    old = pd.read_csv(f"{K200}/basket_members.csv")
    old35 = set(old["ticker"].astype(str))

    spy = adj["SPY"]
    base_idx = adj.index[adj.index <= BASE_DATE][-1]
    dollar_vol = (adj * vol).loc["2025-11-01":BASE_DATE].median()

    todo_mc = [t for t in cons.ticker if t not in old35]
    mc = market_caps(todo_mc)

    rows = []
    for _, m in cons.iterrows():
        t, note = m["ticker"], ""
        if t not in adj.columns or adj[t].dropna().empty:
            rows.append({"代號": t, "公司": m["name"], "備註": "無價格數據"})
            continue
        px = adj[t].dropna()
        # 外地上市(東京、巴黎、多倫多)與美股日曆不齊:基準日可能休市(例:日本 2026-01-12
        # 成人の日)。這種情況退回基準日之前最近一根,並在備註寫明用了哪一日。
        b = base_idx
        if b not in px.index:
            prior = px.index[px.index <= base_idx]
            if len(prior) == 0 or price_date not in px.index:
                rows.append({"代號": t, "公司": m["name"], "備註": "基準日或價格日無價"})
                continue
            b = prior[-1]
            note = f"基準日該市場休市,改用 {b.date()}"
        if price_date not in px.index:
            rows.append({"代號": t, "公司": m["name"], "備註": "價格日無價"})
            continue
        # 200 日線在自己的序列上算:外地股與美股日曆不齊,整框 rolling 會被 NaN 洞截斷
        ma200 = px.rolling(200).mean()
        rel = (px / spy).dropna()
        rel = rel / rel.loc[b]

        acute = rel.loc[BASE_DATE:ACUTE_END]
        full = rel.loc[BASE_DATE:price_date]
        a_trough, a_date = acute.min(), acute.idxmin()
        f_trough, f_date = full.min(), full.idxmin()
        now_rel = rel.loc[price_date]

        ma_ok = None
        if MA_CHECK in ma200.index and pd.notna(ma200.loc[MA_CHECK]):
            ma_ok = "線下" if px.loc[MA_CHECK] < ma200.loc[MA_CHECK] else "線上"

        cap = mc.get(t)
        rows.append({
            "代號": t,
            "公司": m["name"],
            "ETF": m["etf"],
            "IGV權重%": m["igv_weight"] if m["in_igv"] else None,
            "CIBR權重%": m["cibr_weight"] if m["in_cibr"] else None,
            "基準價": round(float(px.loc[b]), 2),
            "急性窗相對大市低點%": round((a_trough - 1) * 100, 1),
            "急性窗低點日": a_date.date().isoformat(),
            "全期相對大市低點%": round((f_trough - 1) * 100, 1),
            "全期低點日": f_date.date().isoformat(),
            "現價": round(float(px.loc[price_date]), 2),
            "至今相對大市%": round((now_rel - 1) * 100, 1),
            "至今絕對%": round((float(px.loc[price_date]) / float(px.loc[b]) - 1) * 100, 1),
            "回補比例%": round((now_rel - a_trough) / (1 - a_trough) * 100, 1) if a_trough < 1 else None,
            "衝擊時200日線": ma_ok,
            "事前日均成交額(百萬)": round(float(dollar_vol.get(t, float("nan"))) / 1e6, 1),
            "市值(十億美元)": round(cap / 1e9, 1) if cap else None,
            "在200的35家內": "是" if t in old35 else "否",
            "備註": note,
        })

    df = pd.DataFrame(rows).sort_values("急性窗相對大市低點%")
    df.to_csv(f"{OUT}/籃子表.csv", index=False, encoding="utf-8-sig")

    n = len(df)
    inn = df[df["在200的35家內"] == "是"]
    out = df[df["在200的35家內"] == "否"]
    with open(f"{OUT}/籃子表.md", "w", encoding="utf-8") as f:
        f.write("# KARST-209 籃子表——IGV(擴展軟件)+ CIBR(網絡安全)成分股\n\n")
        f.write(f"- 成分股自報快照日:IGV **2026-09-08**、CIBR **2026-09-09**(**今日成分,非衝擊日成分**,"
                f"偏差方向見總覽)\n")
        f.write(f"- 基準日 **{base_idx.date()}**;急性期 01-13 至 {ACUTE_END};全期至價格日;"
                f"200 日線取 {MA_CHECK}\n")
        f.write(f"- 價格日 **{price_date.date()}**(**刻意截在 KARST-200 的價格日,令兩表同尺**)\n")
        f.write("- 「相對大市」= 個股 ÷ SPY,基準日歸一。回補比例 100% = 相對大市已完全收復\n")
        f.write(f"- 合併去重後 **{n} 家**;其中 **{len(inn)} 家**在 KARST-200 的 35 家之內、"
                f"**{len(out)} 家**不在\n\n")
        f.write(df.to_markdown(index=False))
        f.write("\n")
    print(df.to_string(index=False))
    print("\n家數:", n, "| 35家內:", len(inn), "| 35家外:", len(out))


if __name__ == "__main__":
    main()
