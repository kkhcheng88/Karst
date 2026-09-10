# -*- coding: utf-8 -*-
"""KARST-206 步六數字:五家並排的衝擊後價值對現價。

規矩(票面):
- 折現率與資本成本**只用** strategy/tools/implied_expectations.py 的規則,不另設一套。
  本檔以 import 方式取用該檔的十年期美債抓取與規則常數,**不改該檔一個字**。
- ΔFCF_t ≈ (Δ收入_t − Δ現金營運成本_t)(1 − T) − Δ資本開支_t − Δ營運資金_t,逐年折現。
- 收入佔比不是結論;Δ 的三個輸入由步三/步四導出。

用法:PYTHONUTF8=1 python step6_numbers.py
輸出:step6_numbers.csv + 主控台摘要
"""

import csv
import os
import sys

sys.path.insert(0, r"C:\projects\Karst\strategy\tools")
import implied_expectations as ie  # noqa: E402  只讀不改

TAX = 0.23                 # 沿用 implied_expectations 的稅率口徑
TERMINAL_G = 0.025         # 終值增長,成熟軟件
HORIZON = 2                # 步一:敘事兩年內出現損害
CONV_LO, CONV_HI = 0.30, 0.60   # Δ收入 轉 ΔFCF 的轉化率區間(判斷,見卡上說明)
CLOSURE = 0.50             # 情境三:折讓收窄一半

# 每家的輸入。r0 = 界線前的收入基準;r_narr2 = 敘事全真時第二年收入;
# exit_mult = KARST-200 的敘事路徑退出倍數;g_base = 無損害基準路徑的增速。
# 除 ASAN 的 g_base 外,其餘 g_base 均為界線前公司自己指引的隱含增速(已核)。
COMPANIES = [
    dict(ticker="ASAN", name="Asana", mode="按席位(壓倒性)",
         price=8.79, shares=237.10, cash=183.470, investments=280.146, debt=35.576,
         r0=790.0, r_narr2=750.0, g_base=0.08, exit_mult=1.5,
         r0_src="FY26 收入指引中位 US$790M(2025-12-02 8-K EX-99.1)",
         g_src="判斷:Core 客戶 +8%、$100k+ 客群續購 96% 取量級;ASAN 界線前無多年指引可核"),
    dict(ticker="NOW", name="ServiceNow", mode="混合(88.5% 按用戶 + 11.5% 按訂閱單位)",
         price=134.21, shares=1040.0, cash=2725.0, investments=6952.0, debt=1491.0,
         r0=12667.0, r_narr2=14500.0, g_base=0.205, exit_mult=6.0,
         r0_src="TTM 收入 US$12,667M(2025-10-30 10-Q)",
         g_src="已核:2026 年訂閱收入指引 15,530–15,570M,增長 20.5%–21%"),
    dict(ticker="BILL", name="BILL Holdings", mode="按交易量與交易金額(ad valorem)",
         price=47.60, shares=100.157, cash=1099.6, investments=1215.3, debt=1887.0,
         r0=1477.5, r_narr2=1540.0, g_base=0.14, exit_mult=2.5,
         r0_src="FY26 核心收入指引中位 US$1,477.5M(2025-11-06 8-K EX-99.1)",
         g_src="已核:Q1 FY26 核心收入(訂閱+交易)按年 +14%"),
    dict(ticker="QTWO", name="Q2 Holdings", mode="按方案數 × 存戶數 × 交易筆數",
         price=60.38, shares=62.530, cash=472.393, investments=96.341, debt=493.933,
         r0=791.0, r_narr2=840.0, g_base=0.135, exit_mult=3.5,
         r0_src="2025 年收入指引中位 US$791M(2025-11-05 8-K EX-99.1)",
         g_src="已核:同份新聞稿 2026 年初步訂閱收入增長約 13.5%"),
    dict(ticker="SNOW", name="Snowflake", mode="按用量(運算與儲存 credits)",
         price=335.50, shares=342.2, cash=4390.0, investments=0.0, debt=2300.0,
         r0=4596.0, r_narr2=5973.0, g_base=0.29, exit_mult=8.0,
         r0_src="FY2026E 收入 = 產品收入指引 US$4,446M + 服務約 150M(2025-12-03 8-K EX-99.1)",
         g_src="已核:界線前 EV/收入約 16×,對應 29% 增長(200 檔述)"),
]


def rule_wacc(debt, cash, investments, market_cap):
    """照 implied_expectations.cost_of_capital 的規則與預設參數重算一次。
    net_cash_include_investments=True(README 限制第 12 條:淨現金口徑是判斷),
    五家的「投資」都是流動性高的短/長期有價證券,故一併計入。"""
    info = ie.rule_discount_rate()
    ty = info["treasury_yield"]
    ke_u = ty + ie.EQUITY_PREMIUM
    kd_post = (ty + ie.CREDIT_SPREAD) * (1.0 - TAX)
    cash_base = cash + investments
    floor = min(ke_u, (1.0 - TAX) * (ke_u + ie.CREDIT_SPREAD))
    if debt <= cash_base or market_cap <= 0:
        wacc_raw, de = ke_u, 0.0
    else:
        de = min(debt / market_cap, ie.DE_CAP)
        ke = ty + ie.EQUITY_PREMIUM * (1.0 + (1.0 - TAX) * de)
        w = debt / (debt + market_cap)
        wacc_raw = ke * (1.0 - w) + kd_post * w
    wacc = max(wacc_raw, floor)
    return dict(treasury=ty, ke_u=ke_u, kd_post=kd_post, de=de,
                wacc_raw=wacc_raw, wacc=round(wacc / ie.RATE_ROUND_STEP) * ie.RATE_ROUND_STEP)


def npv_impact(r0, r_narr2, g_base, wacc, shares):
    """敘事全真路徑對自由現金流的折現影響,回傳 (每股損失下限, 每股損失上限)。"""
    out = []
    for conv in (CONV_LO, CONV_HI):
        pv = 0.0
        for t in range(1, HORIZON + 1):
            rb = r0 * (1.0 + g_base) ** t
            rn = r0 + (r_narr2 - r0) * t / HORIZON
            pv += (rn - rb) * conv / (1.0 + wacc) ** t
        # 第二年之後:敘事路徑按成熟增速走,基準路徑繼續按界線前增速走兩年再收斂
        for t in range(HORIZON + 1, 6):
            rb = r0 * (1.0 + g_base) ** HORIZON * (1.0 + TERMINAL_G) ** (t - HORIZON)
            rn = r_narr2 * (1.0 + TERMINAL_G) ** (t - HORIZON)
            pv += (rn - rb) * conv / (1.0 + wacc) ** t
        d5 = (r_narr2 * (1 + TERMINAL_G) ** 3
              - r0 * (1 + g_base) ** HORIZON * (1 + TERMINAL_G) ** 3) * conv
        pv += d5 * (1 + TERMINAL_G) / (wacc - TERMINAL_G) / (1 + wacc) ** 5
        out.append(pv / shares)
    return out[0], out[1]


def main():
    rows = []
    for c in COMPANIES:
        mcap = c["price"] * c["shares"]
        net_cash = c["cash"] + c["investments"] - c["debt"]
        cap = rule_wacc(c["debt"], c["cash"], c["investments"], mcap)
        wacc = cap["wacc"]

        rb2 = c["r0"] * (1 + c["g_base"]) ** HORIZON
        rp2 = (rb2 + c["r_narr2"]) / 2.0
        v_full = (c["r_narr2"] * c["exit_mult"] + net_cash) / c["shares"]
        v_part = (rp2 * c["exit_mult"] + net_cash) / c["shares"]

        dmg_lo, dmg_hi = npv_impact(c["r0"], c["r_narr2"], c["g_base"], wacc, c["shares"])

        # 結果二:現價在退出倍數下要求的收入,及其對應的隱含年增速
        ev_now = mcap - net_cash
        rev_req = (mcap - net_cash) / c["exit_mult"] if c["exit_mult"] else float("nan")
        cagr_req = (rev_req / c["r0"]) ** (1.0 / HORIZON) - 1.0
        ev_sales = ev_now / c["r0"]

        # 結果三:三情境一年回報(倍數依情境,價格為每股價值)
        r_full = v_full / c["price"] - 1.0
        r_part = v_part / c["price"] - 1.0
        r_third = CLOSURE * r_part

        rows.append(dict(
            ticker=c["ticker"], name=c["name"], mode=c["mode"],
            price=c["price"], shares=c["shares"], net_cash_musd=round(net_cash, 1),
            mcap_musd=round(mcap, 1), ev_musd=round(ev_now, 1), ev_sales=round(ev_sales, 2),
            wacc=round(wacc, 5), de=round(cap["de"], 3), net_cash_flag=int(cap["de"] == 0.0),
            r0=c["r0"], r_base2=round(rb2, 1), r_narr2=c["r_narr2"], r_part2=round(rp2, 1),
            damage_pct=round(c["r_narr2"] / rb2 - 1.0, 4),
            exit_mult=c["exit_mult"], v_full=round(v_full, 2), v_part=round(v_part, 2),
            premium_vs_full=round(c["price"] / v_full - 1.0, 4),
            premium_vs_part=round(c["price"] / v_part - 1.0, 4),
            dmg_npv_share_lo=round(dmg_lo, 2), dmg_npv_share_hi=round(dmg_hi, 2),
            dmg_pct_of_price_lo=round(dmg_lo / c["price"], 4),
            dmg_pct_of_price_hi=round(dmg_hi / c["price"], 4),
            rev_required=round(rev_req, 1), cagr_required=round(cagr_req, 4),
            ret_full=round(r_full, 4), ret_part=round(r_part, 4), ret_third=round(r_third, 4),
        ))

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "step6_numbers.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)

    cap0 = rule_wacc(COMPANIES[0]["debt"], COMPANIES[0]["cash"],
                     COMPANIES[0]["investments"], COMPANIES[0]["price"] * COMPANIES[0]["shares"])
    print("規則輸入:十年期美債 %.3f%% + 無槓桿溢價 %.1fpp → 無槓桿股權成本 %.3f%%;"
          "信用差價 %.1fpp;稅率 %.0f%%;D/E 上限 %.1f 倍"
          % (100 * cap0["treasury"], 100 * ie.EQUITY_PREMIUM, 100 * cap0["ke_u"],
             100 * ie.CREDIT_SPREAD, 100 * TAX, ie.DE_CAP))
    print("ΔFCF 轉化率區間 [%.2f, %.2f];終值增長 %.1f%%;折現期 %d 年 + 終值\n"
          % (CONV_LO, CONV_HI, 100 * TERMINAL_G, HORIZON))
    hdr = ("代號", "現價", "市值M", "淨現金M", "EV/收入", "WACC", "淨現金",
           "全真每股", "部分真每股", "現價對全真", "現價對部分真",
           "NPV損害/股", "全真回報", "部分真回報", "情境三回報")
    print(" | ".join(hdr))
    for r in rows:
        print(" | ".join(str(x) for x in (
            r["ticker"], r["price"], r["mcap_musd"], r["net_cash_musd"], r["ev_sales"],
            "%.1f%%" % (100 * r["wacc"]), r["net_cash_flag"],
            r["v_full"], r["v_part"], "%.1f%%" % (100 * r["premium_vs_full"]),
            "%.1f%%" % (100 * r["premium_vs_part"]),
            "[%.2f, %.2f]" % (r["dmg_npv_share_lo"], r["dmg_npv_share_hi"]),
            "%.1f%%" % (100 * r["ret_full"]), "%.1f%%" % (100 * r["ret_part"]),
            "%.1f%%" % (100 * r["ret_third"]))))
    print("\n現價隱含:退出倍數下要求收入 / 對應兩年 CAGR")
    for r in rows:
        print("  %-5s 要求收入 %8.1fM(界線前 %8.1fM)→ 隱含 CAGR %+.1f%%"
              % (r["ticker"], r["rev_required"], r["r0"], 100 * r["cagr_required"]))
    print("\nwrote " + out)


if __name__ == "__main__":
    main()
