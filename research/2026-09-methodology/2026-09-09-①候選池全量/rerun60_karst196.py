# -*- coding: utf-8 -*-
"""KARST-196:WACC 補槓桿調整前 / 後,六十家機械重跑差異。

**這張表比較的是甚麼**:同一日、同一個價格(收市價口徑)、同一組通用機械假設、
**同一個修後取數層**(KARST-195 的八處修復,前後兩邊都用),唯一的分別是資本成本
規則 ——

- 「前」= KARST-193 的規則:股權成本 = 美債 + 固定 5.0 個百分點,不隨槓桿變
  (在本腳本內以 `IE.cost_of_capital(..., relever=False)` 原樣重現)
- 「後」= KARST-196 的規則:5.0 個百分點視為**無槓桿**股權溢價,按 Hamada 式
  × (1 + (1 − 稅率) × D/E) 重槓桿;D/E 截頂 3.0 倍;WACC 不低於同一條公式的極限值

所以每一格的差異都可以歸因到折現率規則,不會混入取數、假設或價格的改動。

- 名單:screen60_full.csv 的六十家(KARST-188),與 KARST-195 重跑同一份
- 價格:`IE.market_data()` 的收市價口徑(KARST-195 第七項),`price_date` /
  `is_closing_price` / `market_state` 逐家記入輸出;新鮮度照樣記
- 通用機械假設沿用 KARST-188 run_60_full.py 的 D 節,一格未改
- 壓力跌幅的一年最大回撤下限(mdd_1y)與近四季營運現金流(ocf_ttm)直接沿用
  screen60_full.csv —— 兩者都不受折現率影響

**預先講明白一件事**:一年回報(數三)用的是退出市銷率,**完全不經折現率**;負債閘
用的是淨負債 ÷ 營運現金流,同樣不經折現率。所以這兩格前後必然一模一樣,底線翻轉
家數在結構上就是 0。會動的是基準每股值(數二)、升幅與賠率 —— 而賠率正是①候選池
排序要用的那一格。

輸出:KARST196-rerun60.csv / .json
"""
import os
import sys
import json

import pandas as pd

sys.path.insert(0, r"C:\projects\Karst\strategy\tools")
import implied_expectations as IE  # noqa: E402

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"
BOTTOM_LINE_1Y = 0.15
TAX_RATE = 0.23
GBOUND = IE.GBOUND


def generic_assumptions(fin, wacc):
    """KARST-188 run_60_full.py D 節的通用機械假設,一格未改。"""
    g = fin.rev_growth_yoy
    g = 0.0 if g is None else max(-0.5, min(1.0, g))
    return IE.Assumptions(
        bad_growth=g, bad_years=5, recovery_growth=g * 0.5,
        target_margin=fin.op_margin, margin_ramp_years=1, horizon=10,
        tax_rate=TAX_RATE, sales_to_capital=2.0,
        wacc=wacc, terminal_growth=0.025, terminal_roic=0.15,
    )


def three_numbers(fin, price, ps_p50_1y, ps_p25_1y, mdd_1y, ocf, rate_inputs, relever):
    """三個數 + 壓力跌幅 + 賠率 + 兩道閘;relever 決定用哪一版資本成本規則。"""
    out = dict(debt=fin.debt, finance_lease=getattr(fin, "finance_lease", 0.0),
               cash=fin.cash, investments=fin.investments,
               lease_debt=fin.lease_debt, net_debt=fin.net_debt,
               shares=fin.diluted_shares)
    nd = fin.net_debt
    if nd < 0:
        gate = True
    elif ocf and ocf > 0:
        gate = (nd / ocf) <= 3.0
    else:
        gate = False
    out["net_debt_to_ocf"] = (nd / ocf) if (ocf and ocf > 0) else None
    out["debt_gate"] = bool(gate)
    if not fin.diluted_shares:
        out.update(wacc=None, n1_implied_g5=None, n2_per_share=None, n2_upside=None,
                   n2_terminal_share=None, n3_ret_1y=None, stress_drop=None,
                   odds=None, pass_bottom_line=None, error="稀釋股數為 0,除零")
        return out
    mcap = price * fin.diluted_shares
    wd = IE.cost_of_capital(fin, market_cap=mcap, tax_rate=TAX_RATE,
                            treasury_yield=rate_inputs["treasury_yield"],
                            equity_premium=rate_inputs["equity_premium"],
                            credit_spread=rate_inputs["credit_spread"],
                            round_step=rate_inputs["rounded_to"],
                            de_cap=rate_inputs["de_cap"],
                            relever=relever)
    a = generic_assumptions(fin, wd["wacc"])
    out["wacc"] = wd["wacc"]
    out["wacc_raw"] = wd["wacc_raw"]
    out["wacc_net_cash"] = wd["net_cash"]
    out["weight_debt"] = wd["weight_debt"]
    out["de_ratio"] = wd["de_ratio"]
    out["de_capped"] = wd["de_capped"]
    out["equity_premium_levered"] = wd["equity_premium_levered"]
    out["cost_of_equity"] = wd["cost_of_equity"]
    out["wacc_floor"] = wd["wacc_floor"]
    out["wacc_floor_binding"] = wd["wacc_floor_binding"]
    try:
        g5 = IE.solve(fin, a, "bad_growth", price, *GBOUND)
    except Exception:
        g5 = None
    out["n1_implied_g5"] = g5
    try:
        v = IE.value(fin, a)
        out["n2_per_share"] = v.per_share
        out["n2_upside"] = v.per_share / price - 1.0
        out["n2_terminal_share"] = v.terminal_share
    except Exception as e:
        out.update(n2_per_share=None, n2_upside=None, n2_terminal_share=None,
                   error=str(e))
    # 數三:收入走平、退出倍數 = 近一年市銷率中位、一年淨稀釋 = 股權薪酬 ÷ 市值(下限 0.5%)
    # —— 不經折現率,所以前後兩邊必然相同
    dil = max(0.005, (fin.sbc_ttm or 0.0) / mcap)
    if ps_p50_1y and ps_p50_1y == ps_p50_1y:
        px1 = ps_p50_1y * fin.rev_ttm / (fin.diluted_shares * (1.0 + dil))
        out["n3_ret_1y"] = px1 / price - 1.0
    else:
        out["n3_ret_1y"] = None
    if ps_p25_1y and ps_p25_1y == ps_p25_1y:
        sp = ps_p25_1y * (fin.rev_ttm * 0.9) / fin.diluted_shares
        raw = sp / price - 1.0
        drop = min(raw, mdd_1y) if (mdd_1y is not None and mdd_1y == mdd_1y) else raw
        out["stress_drop"] = drop
    else:
        out["stress_drop"] = mdd_1y
    if out.get("n2_upside") is not None and out.get("stress_drop"):
        out["odds"] = out["n2_upside"] / abs(out["stress_drop"])
    else:
        out["odds"] = None
    out["pass_bottom_line"] = (out["n3_ret_1y"] is not None
                               and out["n3_ret_1y"] >= BOTTOM_LINE_1Y)
    return out


def main():
    prev = pd.read_csv(os.path.join(D, "screen60_full.csv")).set_index("ticker")
    tickers = list(prev.index)
    rate_inputs = IE.rule_discount_rate()
    print("資本成本規則輸入:十年期美債 %.3f%%(%s,%s)+ 無槓桿股權溢價 %.1fpp "
          "= 無槓桿股權成本 %.3f%%;信用差價 %.1fpp;D/E 上限 %.1f 倍;重槓桿 %s"
          % (100 * rate_inputs["treasury_yield"], rate_inputs["treasury_source"],
             rate_inputs["treasury_date"], 100 * rate_inputs["equity_premium"],
             100 * rate_inputs["raw_rate"], 100 * rate_inputs["credit_spread"],
             rate_inputs["de_cap"], rate_inputs["relever"]))
    rows, meta = [], {}
    for i, t in enumerate(tickers, 1):
        r = dict(ticker=t)
        try:
            fin = IE.build_financials(t)
        except Exception as e:
            r["error"] = "建帳失敗:%s" % e
            rows.append(r)
            print("%2d/%d %-6s 建帳失敗 %s" % (i, len(tickers), t, e))
            continue
        try:
            mkt = IE.market_data(fin)
        except Exception as e:
            r["error"] = "無價格:%s" % e
            rows.append(r)
            print("%2d/%d %-6s 無價格" % (i, len(tickers), t))
            continue
        fin = IE.reconcile_diluted_shares(fin, mkt.shares_now)
        fresh = IE.filing_freshness(fin.cik, fin.asof, mkt.price_date)

        ps50 = mkt.ps_hist_1y.get("p50") or mkt.ps_hist.get("p50")
        ps25 = mkt.ps_hist_1y.get("p25") or mkt.ps_hist.get("p25")
        mdd = prev.loc[t, "mdd_1y"] if "mdd_1y" in prev.columns else None
        ocf = prev.loc[t, "ocf_ttm"] if "ocf_ttm" in prev.columns else None

        # 同一份帳、同一個價格,只換資本成本規則
        a_old = three_numbers(fin, mkt.price, ps50, ps25, mdd, ocf, rate_inputs, False)
        a_new = three_numbers(fin, mkt.price, ps50, ps25, mdd, ocf, rate_inputs, True)

        r.update(name=fin.name, asof=str(fin.asof), price=mkt.price,
                 price_date=str(mkt.price_date),
                 is_closing_price=not mkt.price_check.get("fell_back"),
                 market_state=mkt.price_check.get("market_state"),
                 stale=fresh.get("stale"), stale_lag_days=fresh.get("lag_days"),
                 latest_filing=fresh.get("latest_filing_date"),
                 latest_report=fresh.get("latest_report_date"),
                 expired=fresh.get("expired"), ocf_ttm=ocf, mdd_1y=mdd)
        for k, v in a_old.items():
            r["old_" + k] = v
        for k, v in a_new.items():
            r["new_" + k] = v
        rows.append(r)
        meta[t] = dict(freshness=fresh, price_check=mkt.price_check)
        print("%2d/%d %-6s D/E %6.2f  WACC %s -> %s  每股 %s -> %s  一年回報 %s(前後同)"
              % (i, len(tickers), t, a_new.get("de_ratio") or 0.0,
                 ("%.1f%%" % (100 * a_old["wacc"])) if a_old.get("wacc") else "n/a",
                 ("%.1f%%" % (100 * a_new["wacc"])) if a_new.get("wacc") else "n/a",
                 ("%.2f" % a_old["n2_per_share"]) if a_old.get("n2_per_share") is not None else "n/a",
                 ("%.2f" % a_new["n2_per_share"]) if a_new.get("n2_per_share") is not None else "n/a",
                 ("%+.1f%%" % (100 * a_new["n3_ret_1y"])) if a_new.get("n3_ret_1y") is not None else "n/a"))

    df = pd.DataFrame(rows).set_index("ticker")
    df.to_csv(os.path.join(D, "KARST196-rerun60.csv"), encoding="utf-8-sig")
    with open(os.path.join(D, "KARST196-rerun60.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(rate_inputs=IE._jsonable(rate_inputs),
                       run_at_eastern=IE._now_eastern().strftime("%Y-%m-%d %H:%M:%S %Z"),
                       rule_before="KARST-193:股權成本 = 美債 + 固定 5.0pp,不隨槓桿變",
                       rule_after="KARST-196:5.0pp 為無槓桿溢價,Hamada 式重槓桿,"
                                  "D/E 截頂 3.0 倍,WACC 不低於規則極限值",
                       per_ticker=meta), fh, indent=2, ensure_ascii=False, default=str)
    print()
    print("已寫 KARST196-rerun60.csv / .json;%d 家" % len(df))


if __name__ == "__main__":
    main()
