# -*- coding: utf-8 -*-
"""KARST-195:取數修復前 / 後,六十家機械重跑差異。

**這張表比較的是甚麼**:同一日、同一個價格、同一組通用機械假設、同一組資本成本規則
輸入,唯一的分別是共用工具 `strategy/tools/implied_expectations.py` 的**資產負債表
取數層**修了六處缺陷。所以每一格的差異都可以歸因到取數,不會混入折現率、假設或價格
的改動。

- 名單:screen60_full.csv 的六十家(KARST-188)
- 「前」= 修前那一版共用工具的取數路徑(舊 *_TAGS 常數 + quarterize 拆股數),
  在本腳本內以 old_extract() 原樣重建
- 「後」= 修後的 IE.build_financials()
- 折現率:KARST-193 的逐家 WACC 規則,前後各自用自己那一版的債務 / 現金 / 股數算
  (債務改了,權重就改了 —— 這一截差異同樣屬於取數修復的後果,不另外剝離)
- 通用機械假設沿用 KARST-188 run_60_full.py 的 D 節,一格未改
- 壓力跌幅的一年最大回撤下限(mdd_1y)與近四季營運現金流(ocf_ttm)直接沿用
  screen60_full.csv —— 兩者都不受本次取數修復影響(前者純價格,後者是損益表流量)

輸出:KARST195-rerun60.csv / .json
"""
import os
import sys
import json
import datetime as dt

import pandas as pd

sys.path.insert(0, r"C:\projects\Karst\strategy\tools")
import implied_expectations as IE  # noqa: E402

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"
BOTTOM_LINE_1Y = 0.15
GBOUND = IE.GBOUND


# --------------------------------------------------------------------------
# 修前那一版的取數路徑,原樣重建(舊常數一格沒動,所以重建得出來)
# --------------------------------------------------------------------------
def old_extract(t):
    cik = IE.cik_for(t)
    facts = IE.load_facts(cik)
    rev_q = IE.quarterize(IE.duration_series(facts, IE.REV_TAGS))
    asof = max(rev_q)
    dil_q = IE.quarterize(IE.duration_series(facts, IE.DILUTED_TAGS))
    ends = sorted(dil_q)

    def inst(tags):
        return IE._latest(IE.instant_series(facts, tags, asof=asof), asof)

    cash = inst(IE.CASH_TAGS)
    inv = inst(IE.STI_TAGS) + inst(IE.LTI_TAGS)
    debt = inst(IE.DEBT_CUR_TAGS) + inst(IE.DEBT_NC_TAGS)
    lease = inst(IE.LEASE_CUR_TAGS) + inst(IE.LEASE_NC_TAGS)
    nci = inst(IE.NCI_TAGS)
    return dict(shares=(dil_q[ends[-1]] if ends else 0.0), cash=cash, investments=inv,
                debt=debt, lease_debt=lease, nci=nci)


def generic_assumptions(fin, wacc):
    """KARST-188 run_60_full.py D 節的通用機械假設,一格未改。"""
    g = fin.rev_growth_yoy
    g = 0.0 if g is None else max(-0.5, min(1.0, g))
    return IE.Assumptions(
        bad_growth=g, bad_years=5, recovery_growth=g * 0.5,
        target_margin=fin.op_margin, margin_ramp_years=1, horizon=10,
        tax_rate=0.23, sales_to_capital=2.0,
        wacc=wacc, terminal_growth=0.025, terminal_roic=0.15,
    )


def three_numbers(fin, price, ps_p50_1y, ps_p25_1y, mdd_1y, ocf, rate_inputs):
    """三個數 + 壓力跌幅 + 賠率 + 兩道閘。股數為零就整組不算(舊版 ORCL 的情形)。"""
    out = dict(debt=fin.debt, finance_lease=getattr(fin, "finance_lease", 0.0),
               cash=fin.cash, investments=fin.investments,
               lease_debt=fin.lease_debt, net_debt=fin.net_debt,
               shares=fin.diluted_shares)
    # 負債閘
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
    wd = IE.cost_of_capital(fin, market_cap=mcap, tax_rate=0.23,
                            treasury_yield=rate_inputs["treasury_yield"],
                            equity_premium=rate_inputs["equity_premium"],
                            credit_spread=rate_inputs["credit_spread"],
                            round_step=rate_inputs["rounded_to"])
    a = generic_assumptions(fin, wd["wacc"])
    out["wacc"] = wd["wacc"]
    out["wacc_raw"] = wd["wacc_raw"]
    out["wacc_net_cash"] = wd["net_cash"]
    out["weight_debt"] = wd["weight_debt"]
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
    dil = max(0.005, (fin.sbc_ttm or 0.0) / mcap)
    if ps_p50_1y and ps_p50_1y == ps_p50_1y:
        px1 = ps_p50_1y * fin.rev_ttm / (fin.diluted_shares * (1.0 + dil))
        out["n3_ret_1y"] = px1 / price - 1.0
    else:
        out["n3_ret_1y"] = None
    # 壓力跌幅:近一年 25 分位 × (收入 × 0.9) ÷ 股數,再以一年最大回撤封底
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
    print("資本成本規則輸入:十年期美債 %.3f%%(%s,%s)+ 股權溢價 %.1fpp;"
          "信用差價 %.1fpp;股權成本 %.3f%%"
          % (100 * rate_inputs["treasury_yield"], rate_inputs["treasury_source"],
             rate_inputs["treasury_date"], 100 * rate_inputs["equity_premium"],
             100 * rate_inputs["credit_spread"], 100 * rate_inputs["raw_rate"]))
    rows, meta = [], {}
    for i, t in enumerate(tickers, 1):
        r = dict(ticker=t)
        try:
            fin_new = IE.build_financials(t)
        except Exception as e:
            r["error"] = "建帳失敗:%s" % e
            rows.append(r)
            print("%2d/%d %-6s 建帳失敗 %s" % (i, len(tickers), t, e))
            continue
        try:
            mkt = IE.market_data(fin_new)
        except Exception as e:
            r["error"] = "無價格:%s" % e
            rows.append(r)
            print("%2d/%d %-6s 無價格" % (i, len(tickers), t))
            continue
        fin_new = IE.reconcile_diluted_shares(fin_new, mkt.shares_now)
        fresh = IE.filing_freshness(fin_new.cik, fin_new.asof, mkt.price_date)

        old = old_extract(t)
        fin_old = IE.replace(fin_new, cash=old["cash"], investments=old["investments"],
                             debt=old["debt"], lease_debt=old["lease_debt"],
                             nci=old["nci"], diluted_shares=old["shares"],
                             finance_lease=0.0)
        # 市銷率對股數是線性的:同一組價格,換股數只需按比例縮放,不用再打一次 yfinance
        sc = (old["shares"] / fin_new.diluted_shares) if fin_new.diluted_shares else 0.0
        ps50_new = mkt.ps_hist_1y.get("p50") or mkt.ps_hist.get("p50")
        ps25_new = mkt.ps_hist_1y.get("p25") or mkt.ps_hist.get("p25")
        mdd = prev.loc[t, "mdd_1y"] if "mdd_1y" in prev.columns else None
        ocf = prev.loc[t, "ocf_ttm"] if "ocf_ttm" in prev.columns else None

        a_new = three_numbers(fin_new, mkt.price, ps50_new, ps25_new, mdd, ocf, rate_inputs)
        a_old = three_numbers(fin_old, mkt.price, (ps50_new * sc) if ps50_new else None,
                              (ps25_new * sc) if ps25_new else None, mdd, ocf, rate_inputs)

        r.update(name=fin_new.name, asof=str(fin_new.asof), price=mkt.price,
                 price_date=str(mkt.price_date),
                 is_closing_price=not mkt.price_check.get("fell_back"),
                 market_state=mkt.price_check.get("market_state"),
                 stale=fresh.get("stale"), stale_lag_days=fresh.get("lag_days"),
                 latest_filing=fresh.get("latest_filing_date"),
                 latest_report=fresh.get("latest_report_date"),
                 expired=fresh.get("expired"),
                 debt_src=fin_new.extraction["debt"]["src"],
                 finance_lease_src=fin_new.extraction["debt"]["src_finance_lease"],
                 cash_src=fin_new.extraction["cash"]["src_cash"],
                 invest_src=fin_new.extraction["cash"]["src_investments"],
                 shares_src=fin_new.shares_src, ocf_ttm=ocf, mdd_1y=mdd)
        for k, v in a_old.items():
            r["old_" + k] = v
        for k, v in a_new.items():
            r["new_" + k] = v
        rows.append(r)
        meta[t] = dict(freshness=fresh, price_check=mkt.price_check,
                       extraction=IE._jsonable(fin_new.extraction))
        print("%2d/%d %-6s 淨負債 %12.1fM -> %12.1fM  閘 %s->%s  賠率 %s->%s"
              % (i, len(tickers), t, a_old["net_debt"] / 1e6, a_new["net_debt"] / 1e6,
                 a_old["debt_gate"], a_new["debt_gate"],
                 ("%.2f" % a_old["odds"]) if a_old.get("odds") is not None else "n/a",
                 ("%.2f" % a_new["odds"]) if a_new.get("odds") is not None else "n/a"))

    df = pd.DataFrame(rows).set_index("ticker")
    df.to_csv(os.path.join(D, "KARST195-rerun60.csv"), encoding="utf-8-sig")
    with open(os.path.join(D, "KARST195-rerun60.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(rate_inputs=IE._jsonable(rate_inputs),
                       run_at_eastern=IE._now_eastern().strftime("%Y-%m-%d %H:%M:%S %Z"),
                       per_ticker=meta), fh, indent=2, ensure_ascii=False, default=str)
    print()
    print("已寫 KARST195-rerun60.csv / .json;%d 家" % len(df))


if __name__ == "__main__":
    main()
