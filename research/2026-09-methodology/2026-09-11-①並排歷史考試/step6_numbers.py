# -*- coding: utf-8 -*-
"""KARST-210 步六數字:兩宗事件、每家五家,衝擊後合理價值對衝擊前一交易日收市價。

規矩(票面 + v2.1 步六):
- 折現率與資本成本沿用 `strategy/tools/implied_expectations.py` 的規則常數,不另設一套。
  本票以「衝擊日當時十年期美債(FRED DGS10 該日值)+ 5.0pp 無槓桿股權溢價」作無槓桿股權
  成本,再照該檔 `cost_of_capital` 的 Hamada 式重槓桿與 3.0 倍 D/E 截頂、四捨五入到
  0.5 個百分點。**差別在這十家身上只有 0.5 個百分點以內,逐家已列。**
- 步六「三個結果」的算法:
  **結果一** 每股價值 [下限, 上限] × 兩個情境 = 四個數。
     - 敘事全真 = 兩年內收入原地踏步(年增 0%)——這是「市場怕的事成真」最直接的讀法。
     - 敘事部分真 = 兩年內按年增 g_part,g_part 逐家由步三／步四證據定,逐家寫來源。
     - 倍數:**不設單一倍數**,取三格敏感度:1.0(倍數不動)/ 0.8 / 0.6。
     - ⚠ **已知退化,必須明寫**:退出倍數由衝擊日 EV/收入 校準,故「倍數不動 + 收入原地
       踏步」的價值**恆等於現價**(EV = mcap − 淨現金,除以股數就是 price)。即步六那格
       「現價對衝擊後價值」在倍數不動之下**永遠得出同一個答案**,不隨公司變。**唯一會令
       判詞變的是倍數假設**,不是生意分析。此點與 KARST-208「BILL 現價等於部分真價值
       是倍數產物」同一根源,本票照樣明寫,不寫已防。
  **結果二** 現價要求什麼:倍數不動之下,現價隱含兩年收入 = r0(零增長)——**此為恆等式,
     不是發現**;倍數下調四成之下,隱含年增 29.1%(=(1/0.6)^0.5−1)。
  **結果三** 一年回報三情境(全真／部分真／證據改善但折讓未收窄)。
- 現金一律 N2 口徑(現金 + 短期投資 − 總債務);**總債務查不到的逐家標明,該家淨現金取
  現金作上限**(影響逐家列出)。

用法:PYTHONUTF8=1 python step6_numbers.py
輸出:step6_numbers.csv + 主控台摘要
"""
import csv
import os

TAX = 0.23
EQUITY_PREMIUM = 0.05
CREDIT_SPREAD = 0.02
DE_CAP = 3.0
RATE_STEP = 0.005
M_NARR = 0.60          # 敘事情境的倍數下調比例(判斷,待對齊)
M_MID = 0.80           # 敏感度中格
CLOSURE = 0.50         # 情境三:折讓收窄一半

# price = 衝擊前一交易日收市價(packet);mcap / r0 / cash / debt 出自 packet 財務面板;
# debt=None 表示面板與 10-K 都取不到,淨現金取現金為上限並在 net_cash_flag 標 1。
COMPANIES = [
    # ---- E07 2025-01 DeepSeek 殺 AI 資本開支鏈(美債 4.63%)----
    dict(ev="E07", ticker="NVDA", price=142.62, mcap=3487555.0, r0=109286.0,
         cash=9107.0, debt=8462.0, g_part=0.15, m="1.0",
         g_src="判斷:衝擊前 10-K 明文「約四成資料中心收入來自推理」,推理需求不隨訓練成本崩塌;0% 是全真那一端,+15% 是部分真一端"),
    dict(ev="E07", ticker="MU", price=103.19, mcap=114530.0, r0=29094.0,
         cash=6693.0, debt=11306.0, g_part=0.10, m="1.0",
         g_src="判斷:DRAM/NAND 是消耗品,HBM 是新產品週期;10-K 明列 ASP 歷史上曾跌穿製造成本。0% 對 +10%"),
    dict(ev="E07", ticker="VRT", price=146.32, mcap=54817.0, r0=7408.0,
         cash=909.0, debt=2931.0, g_part=0.08, m="1.0",
         g_src="判斷:10-K 風險因素自陳「重大積壓訂單」與「長約固定價」;訂單來自已批出的開支計劃,滯後一至兩季"),
    dict(ev="E07", ticker="ANET", price=129.17, mcap=40681.0, r0=6582.0,
         cash=3175.0, debt=0.0, g_part=0.10, m="1.0",
         g_src="判斷:10-K 披露兩家雲端終端客(Meta、Microsoft)各佔收入逾一成;RPO 23 億美元含 3.677 億「未來產品交付」約束性協議"),
    dict(ev="E07", ticker="ORCL", price=183.60, mcap=504844.0, r0=53587.0,
         cash=10941.0, debt=None, g_part=0.07, m="1.0",
         g_src="判斷:雲與授權佔收入 84%,其中基建(OCI)是算力的買方——算力變平對它是成本下降;支持收入為經常性。全真 +4%、部分真 +7%"),
    # ---- E06 2023-10 減肥藥殺食品與醫療器械(美債 4.81%)----
    dict(ev="E06", ticker="MDLZ", price=67.60, mcap=84831.0, r0=32710.0,
         cash=1553.0, debt=None, g_part=0.03, m="1.0",
         g_src="判斷:核心是朱古力與餅乾(10-K Item 1);10-K 明寫「2022 年無單一客戶佔收入一成以上」。全真 0%、部分真 +3%"),
    dict(ev="E06", ticker="KO", price=54.88, mcap=218991.0, r0=45340.0,
         cash=12564.0, debt=36797.0, g_part=0.04, m="1.0",
         g_src="判斷:濃縮液＋裝瓶商模式,價格／產品組合是收入槓桿(10-K MD&A 明列四項分析因子);無糖與水類產品線可對沖氣水"),
    dict(ev="E06", ticker="RMD", price=144.59, mcap=20647.0, r0=4223.0,
         cash=228.0, debt=1431.0, g_part=0.06, m="1.0",
         g_src="判斷:10-K 引 Lancet「全球逾 9.36 億人患輕至重度睡眠窒息,美國 5,400 萬人」,而診斷率不足兩成——已診斷池的增長遠大於減肥藥可能削去的病人"),
    dict(ev="E06", ticker="DXCM", price=90.94, mcap=35273.0, r0=3079.0,
         cash=1195.0, debt=0.0, g_part=0.12, m="1.0",
         g_src="判斷:感測器是耗材、收入重複發生;10-K 引 CDC 指兒童青少年肥胖率 19.7%、成人第 2 型糖尿病人數上升。全真 0%、部分真 +12%"),
    dict(ev="E06", ticker="DVA", price=93.72, mcap=8557.0, r0=11749.0,
         cash=327.0, debt=None, g_part=0.02, m="1.0",
         g_src="判斷:10-K 披露 90% 洗腎病人由政府計劃覆蓋(其中 75% Medicare/MA)、病人增長率本已偏低——敘事若真,是把它已有的低增長再壓一級"),
]


def wacc_of(price, mcap, cash, debt, treasury):
    """照 implied_expectations.cost_of_capital 的規則重算(不 import,常數照抄)。"""
    ke_u = treasury + EQUITY_PREMIUM
    kd_post = (treasury + CREDIT_SPREAD) * (1.0 - TAX)
    floor = min(ke_u, (1.0 - TAX) * (ke_u + CREDIT_SPREAD))
    if debt is None or debt <= cash or mcap <= 0:
        raw, de = ke_u, 0.0
    else:
        de = min(debt / mcap, DE_CAP)
        ke = treasury + EQUITY_PREMIUM * (1.0 + (1.0 - TAX) * de)
        w = debt / (debt + mcap)
        raw = ke * (1.0 - w) + kd_post * w
    return dict(de=de, wacc_raw=raw,
                wacc=round(max(raw, floor) / RATE_STEP) * RATE_STEP,
                net_cash_flag=int(debt is None or debt <= cash))


def main():
    TR = {"E06": 0.0481, "E07": 0.0463}   # FRED DGS10 該日值(4.81% / 4.63%)
    rows = []
    for c in COMPANIES:
        ty = TR[c["ev"]]
        cap = wacc_of(c["price"], c["mcap"], c["cash"], c["debt"], ty)
        nc = c["cash"] - (c["debt"] or 0.0)
        shares = c["mcap"] / c["price"]
        ev = c["mcap"] - nc
        exit_mult = ev / c["r0"]
        r_full = c["r0"]                                  # 兩年原地踏步
        r_part = c["r0"] * (1.0 + c["g_part"]) ** 2
        v = lambda r, m: (r * exit_mult * m + nc) / shares
        vfl, vfh = v(r_full, M_NARR), v(r_full, 1.0)
        vpl, vph = v(r_part, M_NARR), v(r_part, 1.0)
        lo = min(vfl, vpl)          # 全真 + 倍數下調四成(最壞格)
        mid_lo = v(r_full, M_MID)
        mid_hi = v(r_part, M_MID)

        def verdict_of(lo_, hi_):
            if c["price"] > hi_:
                return "現價高於衝擊後價值"
            if c["price"] < lo_:
                return "現價低於衝擊後價值"
            return "相稱"
        # 判詞取中格(倍數八折):上限=部分真、下限=全真。倍數不動那格是恆等式(見檔頭),不用。
        verdict = verdict_of(mid_lo, mid_hi)
        v_1x_full = vfh
        # 結果三:一年回報(一年後收入:全真 = r0;部分真 = r0*(1+g))
        r1_full = c["r0"]
        r1_part = c["r0"] * (1.0 + c["g_part"])
        p1i = v(r1_full, M_NARR)
        p2i = v(r1_part, 0.80)
        ret_full = p1i / c["price"] - 1.0
        ret_part = p2i / c["price"] - 1.0
        ret_third = CLOSURE * ret_part
        rows.append(dict(
            event=c["ev"], ticker=c["ticker"], price=round(c["price"], 2),
            shares_m=round(shares, 1), r0=round(c["r0"], 1), net_cash_m=round(nc, 1),
            ev_m=round(ev, 1), exit_mult=round(exit_mult, 2),
            treasury=ty, wacc=cap["wacc"], de=round(cap["de"], 3),
            debt_missing=cap["net_cash_flag"],
            r_part2=round(r_part, 1), g_part=c["g_part"],
            v_full_lo=round(vfl, 2), v_full_hi=round(vfh, 2),
            v_part_lo=round(vpl, 2), v_part_hi=round(vph, 2),
            v_mid_full=round(mid_lo, 2), v_mid_part=round(mid_hi, 2),
            v_1x_full_identity=round(v_1x_full, 2),
            px_vs_lo=round(c["price"] / lo - 1.0, 4),
            px_vs_midfull=round(c["price"] / mid_lo - 1.0, 4),
            verdict=verdict,
            ret_full=round(ret_full, 4), ret_part=round(ret_part, 4),
            ret_third=round(ret_third, 4),
            impl_2y_zero_growth=1, impl_2y_cagr_mult06=round((1.0 / M_NARR) ** 0.5 - 1.0, 4),
            g_src=c["g_src"]))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "step6_numbers.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    hdr = ("事件", "代號", "界線前價", "EV/S", "WACC",
           "0.6全真", "0.6部分", "0.8全真", "0.8部分", "現價對0.6下限", "判詞",
           "全真回報", "部分真回報", "情境三")
    print(" | ".join(hdr))
    for r in rows:
        print(" | ".join(str(x) for x in (
            r["event"], r["ticker"], r["price"], r["exit_mult"],
            "%.1f%%" % (100 * r["wacc"]),
            r["v_full_lo"], r["v_part_lo"], r["v_mid_full"], r["v_mid_part"],
            "%.1f%%" % (100 * r["px_vs_lo"]), r["verdict"],
            "%.1f%%" % (100 * r["ret_full"]), "%.1f%%" % (100 * r["ret_part"]),
            "%.1f%%" % (100 * r["ret_third"]))))
    print("\n⚠ 倍數不動(1.0)那格恆等於現價(見檔頭退化說明),故不上表;"
          "判詞取 0.8 格,下限 = 0.6 全真。")
    print("倍數下調比例 m_narr=%.2f(判斷,待對齊);情境三 = 部分真回報 x %.2f"
          % (M_NARR, CLOSURE))
    print("wrote " + out)


if __name__ == "__main__":
    main()
