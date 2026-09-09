# -*- coding: utf-8 -*-
"""KARST-200 步驟二:籃子表。

輸入:fetch_prices.py 抓落的 adj close 快取 + 籃子成員名單(basket_members.csv)。
輸出:籃子表 csv/md——每家的衝擊期跌幅(絕對與相對大市)、至今回補程度、
      衝擊當時的 200 日線位置(D-174 第二項的①定義閘,本票只標不篩)。

口徑(寫死,不是可調參數):
- 基準日 P0   :**2026-01-12**,即 Anthropic 推出 Claude Cowork(2026-01-12/13)
                之前最後一個收市日。**不是用二月那個日子**——事件核實查明敘事
                由一月中 Cowork 發布起計,二月三日的法律插件是主震不是起點;
                由 2026-01-12 起計,IGV 相對 SPY 至 02-24 跌 24.7%,
                由 01-28 起計只有 18.3%,由 02-02 起計只有 11.4%。
                用遲了的基準日會把已經跌完的一段當成沒有發生。
- 相對價格序列:個股 adj close ÷ SPY adj close,再以基準日 = 1.00 歸一。
                「相對大市」全部在這條序列上量。
- **兩個低點,因為這件事有幾條腿**(同一個基準日,只換取低點的窗):
  * 急性期 2026-01-13 至 2026-02-27——一月 Cowork 腿加二月主震腿。
  * 全期   2026-01-13 至 價格日——連四月十日與七月餘震一齊計的最低點
           (IGV 全期最低正正在 2026-04-10,不在二月)。
  兩個都報,不揀一個充數:只報急性期會低估四月才見底那一批,
  只報全期會把與本事件無關的公司自身災難也算進來。
- 回補比例    :(今日相對價 − 急性期低點) ÷ (1.00 − 急性期低點);
                100% = 相對大市已完全收復,0% = 仍在低點,>100% = 已高過事前。
- 200 日線    :2026-02-05(主震那一週)的收市價相對 200 日均線。
"""
import json

import pandas as pd

OUT = "C:/projects/Karst/research/2026-09-methodology/2026-09-10-①SaaS事件前瞻登記"

BASE_DATE = "2026-01-12"
ACUTE_END = "2026-02-27"
MA_CHECK = "2026-02-05"


def main():
    adj = pd.read_parquet(f"{OUT}/prices_adjclose.parquet")
    adj.index = pd.to_datetime(adj.index)
    vol = pd.read_parquet(f"{OUT}/prices_volume.parquet")
    vol.index = pd.to_datetime(vol.index)
    meta = json.load(open(f"{OUT}/prices.meta.json", encoding="utf-8"))
    price_date = pd.Timestamp(meta["price_date"])

    members = pd.read_csv(f"{OUT}/basket_members.csv")
    spy = adj["SPY"]
    base_idx = adj.index[adj.index <= BASE_DATE][-1]
    ma200 = adj.rolling(200).mean()
    dollar_vol = (adj * vol).loc["2025-11-01":BASE_DATE].median()

    rows = []
    for _, m in members.iterrows():
        t = m["ticker"]
        if t not in adj.columns or adj[t].dropna().empty:
            rows.append({"代號": t, "公司": m.get("name", ""), "備註": "無價格數據"})
            continue
        px = adj[t].dropna()
        if base_idx not in px.index or price_date not in px.index:
            rows.append({"代號": t, "公司": m.get("name", ""), "備註": "基準日或價格日無價"})
            continue
        rel = (px / spy).dropna()
        rel = rel / rel.loc[base_idx]

        acute = rel.loc[BASE_DATE:ACUTE_END]
        full = rel.loc[BASE_DATE:price_date]
        a_trough, a_date = acute.min(), acute.idxmin()
        f_trough, f_date = full.min(), full.idxmin()
        now_rel = rel.loc[price_date]

        ma_ok = None
        if MA_CHECK in ma200.index and pd.notna(ma200.loc[MA_CHECK, t]):
            ma_ok = "線下" if px.loc[MA_CHECK] < ma200.loc[MA_CHECK, t] else "線上"

        rows.append({
            "代號": t,
            "公司": m.get("name", ""),
            "來源": m.get("source", ""),
            "基準價": round(float(px.loc[base_idx]), 2),
            "急性窗相對大市低點%": round((a_trough - 1) * 100, 1),
            "急性窗低點日": a_date.date().isoformat(),
            "全期相對大市低點%": round((f_trough - 1) * 100, 1),
            "全期低點日": f_date.date().isoformat(),
            "現價": round(float(px.loc[price_date]), 2),
            "至今相對大市%": round((now_rel - 1) * 100, 1),
            "至今絕對%": round((float(px.loc[price_date]) / float(px.loc[base_idx]) - 1) * 100, 1),
            "回補比例%": round((now_rel - a_trough) / (1 - a_trough) * 100, 1) if a_trough < 1 else None,
            "衝擊時200日線": ma_ok,
            "事前日均成交額(百萬)": round(float(dollar_vol.get(t, float("nan"))) / 1e6, 1),
            "備註": "",
        })

    df = pd.DataFrame(rows).sort_values("急性窗相對大市低點%")
    df.to_csv(f"{OUT}/籃子表.csv", index=False, encoding="utf-8-sig")

    with open(f"{OUT}/籃子表.md", "w", encoding="utf-8") as f:
        f.write("# KARST-200 籃子表——2026 年 SaaSpocalypse 衝擊籃\n\n")
        f.write(f"- 基準日 **{base_idx.date()}**(Anthropic 推出 Claude Cowork 之前最後一個收市日)\n")
        f.write(f"- 急性期低點取自 2026-01-13 至 {ACUTE_END};全期低點取自 2026-01-13 至價格日\n")
        f.write(f"- 價格日 **{price_date.date()}** 收市價。抽數時美東 {meta['et_now'][:19]},"
                f"市場 {meta['market_state']},已按 KARST-195 第七項丟棄未完成日線"
                f"({meta['dropped_incomplete_bar']})\n")
        f.write("- 「相對大市」= 個股 ÷ SPY,基準日歸一。回補比例 100% = 相對大市已完全收復\n")
        f.write("- 「衝擊時 200 日線」= 2026-02-05 收市價相對 200 日均線(D-174 第二項的①定義閘,本票只標不篩)\n\n")
        f.write(df.to_markdown(index=False))
        f.write("\n")
    print(df.to_string(index=False))
    print("\n家數:", len(df))


if __name__ == "__main__":
    main()
