# -*- coding: utf-8 -*-
"""KARST-200 步驟五:把預測登記 csv 渲染成 md。

體例沿用 KARST-188 的 `前瞻預測登記表.md`,**加一欄「事件」**,
以便日後與個股大跌那一批合併成同一張成績表(本票工作內容第五步)。

輸入:預測登記表.csv(逐條預測一行,由判斷層各批的 md 抄入,不代算)
輸出:預測登記表.md
"""
import json
import re

import pandas as pd

OUT = "C:/projects/Karst/research/2026-09-methodology/2026-09-10-①SaaS事件前瞻登記"

COLS = ["事件", "家", "代號", "敘事適用度", "輪次", "到期狀態", "編號", "可證偽的預測",
        "勝率區間", "核的日期", "核的文件", "作廢前提", "證偽出場價", "現價",
        "證偽出場價相對現價%", "證偽出場價算式", "支不支持買入"]

STANCE = "2026-09-10"  # 立場日:觀察日期早過這一日的,不計入前瞻成績(見總覽第七節)


def main():
    df = pd.read_csv(f"{OUT}/預測登記表.csv")
    meta = json.load(open(f"{OUT}/prices.meta.json", encoding="utf-8"))

    # 現價與跌幅由主 agent 這一層計,判斷層沒有拿過現價(盲判,見判準檔第一之二節)
    adj = pd.read_parquet(f"{OUT}/prices_adjclose.parquet")
    adj.index = pd.to_datetime(adj.index)
    px = adj.loc[pd.Timestamp(meta["price_date"])]
    df["現價"] = df["代號"].map(lambda t: round(float(px[t]), 2) if t in px.index else None)
    ex = pd.to_numeric(df["證偽出場價"], errors="coerce")
    df["證偽出場價相對現價%"] = ((ex / df["現價"] - 1) * 100).round(1)

    # 到期狀態:觀察日期取該格內最後出現的年月
    def last_ym(s):
        m = re.findall(r"20\d\d-\d\d", str(s))
        return m[-1] if m else None

    df["_ym"] = df["核的日期"].map(last_ym)
    df["到期狀態"] = df["_ym"].map(
        lambda y: "未知" if y is None
        else ("已到期(不計前瞻成績)" if y < STANCE[:7] else "前瞻")
    )
    if "輪次" not in df.columns:
        df["輪次"] = "第一輪"
    if "作廢前提" not in df.columns:
        df["作廢前提"] = ""
    df["作廢前提"] = df["作廢前提"].fillna("")

    missing = [c for c in COLS if c not in df.columns]
    if missing:
        raise SystemExit(f"csv 缺欄:{missing}")

    with open(f"{OUT}/預測登記表.md", "w", encoding="utf-8") as f:
        f.write("# KARST-200 前瞻預測登記表——2026 年 SaaSpocalypse 事件籃\n\n")
        f.write("**這一份是日後覆核用的正本。** 每一項都是可證偽的預測:有門檻、有核的日期、"
                "有核的文件。到期逐項打勾,就能回答一條問題——"
                "**代理可不可以在事前分辨「這個敘事對這一家適不適用」。**\n\n")
        f.write(f"- 立場日:2026-09-10。價格參照 **{meta['price_date']}** 收市價"
                f"(抽數時美東 {meta['et_now'][:19]},市場 {meta['market_state']},"
                f"已丟棄未完成日線)。\n")
        f.write("- 敘事適用度的判準見同目錄 `敘事適用度判準.md`;判級只用 2026-01-29 之前"
                "已公開的資料,並刻意不使用衝擊後的價格表現(判準檔第一之二節)。\n")
        f.write("- 勝率一律寫成區間,**只作評分用,不作倉位輸入**(①材料 §11 第 23 項)。\n")
        f.write("- 證偽出場價依 D-174 第一項:由預測失效點逐家推出,不是公式壓力跌幅。\n")
        f.write("- **現價與「相對現價%」由主 agent 這一層計**;判斷層寫出場價時沒有拿過現價,"
                "以免用事後價位倒推一個好看的下行空間。\n")
        f.write("- 拆股口徑:NOW 已按 2025-12-18 五拆一還原、CRWD 已按 2026-07-02 四拆一還原,"
                "兩家的每股數與現價同一口徑。\n")
        f.write("- **出場價多數是公司層估值**(同一家各條預測共用一個),"
                "不是逐條各有一個;抄寫時按公司層填入該家每一條。\n")
        f.write("- **「作廢前提」一欄要先看**:該欄有字的條目,若前提發生(公司被收購、"
                "資產出售後不再申報),到期時記**作廢**,不記勝負。"
                "沒有這一欄的話,一條無從裁決的預測會被當成答錯——"
                "**查不到與答錯是兩回事**,兩者混在一起會令命中率無聲失真。\n")
        f.write("- 覆核時「核的文件」必須是一手申報文件;查不到那份就記「未能核」,"
                "不准用新聞或第二手轉述代替。\n")
        f.write("- **加了「事件」欄**,以便日後與 KARST-188 那批個股大跌的登記合併成同一張成績表。\n\n")
        n_fwd = (df["到期狀態"] == "前瞻").sum()
        n_old = (df["到期狀態"] == "已到期(不計前瞻成績)").sum()
        f.write(f"共 {len(df)} 項,涵蓋 {df['代號'].nunique()} 家:"
                f"**前瞻 {n_fwd} 項**、已到期 {n_old} 項。\n\n")
        f.write("> **「已到期」那批不計前瞻成績。** 第一輪預測是站在 2026-01-12 的資訊集寫的,"
                "所以觀察日期多數落在 2026 年 2 至 3 月,今日已經過去。依 D-168,"
                "判斷層是語言模型,那幾個月的結果有機會已在其訓練資料內,"
                "**「它當時不知道結果」無法證明**,故只可作帶已知污染的參考讀數。"
                "第二輪補登(`前瞻補登-組A/B/C.md`)專為補回真正前瞻的條目而做。\n\n")
        f.write(df[COLS].to_markdown(index=False))
        f.write("\n")
    print(f"寫好 {len(df)} 條,{df['代號'].nunique()} 家")


if __name__ == "__main__":
    main()
