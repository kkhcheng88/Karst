# -*- coding: utf-8 -*-
"""KARST-197 第二步:對新池(129 家)跑三個數,出新版篩選表。

**與 KARST-188 run_60_full.py 的分別**:
  1. 名單 —— 新閘重篩的 129 家(screen_pool_197_gates.csv 的 in_pool),不是舊六十家
  2. 取數 —— 全部用修後的 strategy/tools/implied_expectations.py(KARST-195 八處 +
     KARST-196 槓桿調整);run_60_full.py 內那批本地補丁(債務、現金、股數)已經
     收進工具,本腳本不再自帶,呼叫方式照 rerun60_karst196.py
  3. 價格 —— IE.market_data() 的收市價口徑(KARST-195 第七項),price_date /
     is_closing_price / market_state 逐家記入輸出
  4. 資料落後 —— A-055:filing_freshness 判「落後」者**扣起基準每股值**,原值移入
     *_withheld 欄,賠率一併扣起,表上標明
  5. 通用機械假設 —— 沿用 run_60_full.py D 節,一格未改

輸出:screen_pool_197.csv / .json
"""
import datetime as dt
import json
import os
import sys

import pandas as pd

sys.path.insert(0, r"C:\projects\Karst\strategy\tools")
import implied_expectations as IE  # noqa: E402

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"
TAX_RATE = 0.23
WIN_START = dt.date(2026, 6, 1)


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


def price_block(ticker, spy_hist, price_date, price, hist_cache):
    """200 日線形態與一年最大回撤。價格一律用 market_data 的收市價,
    歷史序列截到 price_date 為止,不讓未完成的當日線混進來。"""
    import yfinance as yf
    h = hist_cache.get(ticker)
    if h is None:
        h = yf.Ticker(ticker).history(period="2y", auto_adjust=False)
        hist_cache[ticker] = h
    if h is None or h.empty:
        return None
    close = h["Close"].copy()
    close.index = [d.date() for d in close.index]
    close = close[[d <= price_date for d in close.index]]
    if len(close) < 60:
        return None
    p0_dates = [d for d in close.index if d >= WIN_START]
    p0 = float(close.loc[p0_dates[0]]) if p0_dates else None
    ret = (price / p0 - 1.0) if p0 else None
    rel = None
    if p0 and spy_hist is not None:
        sd = [d for d in spy_hist.index if d >= WIN_START]
        if sd:
            spy0 = float(spy_hist.loc[sd[0]])
            spy1 = float(spy_hist[[d for d in spy_hist.index if d <= price_date]].iloc[-1])
            rel = ret - (spy1 / spy0 - 1.0)
    ma200 = float(close.iloc[-200:].mean()) if len(close) >= 200 else float("nan")
    ma_series = close.rolling(200).mean()
    slope = (float(ma_series.iloc[-1]) / float(ma_series.iloc[-41]) - 1.0) \
        if len(ma_series.dropna()) > 41 else float("nan")
    px_vs = (price / ma200 - 1.0) if ma200 == ma200 else float("nan")
    if px_vs != px_vs:
        form = "資料不足"
    elif px_vs > 0:
        form = "回調"
    elif slope != slope or slope <= 0:
        form = "殺"
    else:
        form = "線附近"
    yr = close.iloc[-252:]
    mdd = float((yr / yr.cummax() - 1.0).min())
    return dict(ret_win=ret, rel_spy_win=rel, ma200=ma200, px_vs_ma200=px_vs,
                ma200_slope_40d=slope, ma200_form=form, mdd_1y=mdd)


def analyst_block(ticker):
    """共識收入增長 —— 只為機制標籤那一格,取不到就當沒有。"""
    import yfinance as yf
    out = {}
    try:
        tk = yf.Ticker(ticker)
        info = tk.info or {}
        out["info"] = {k: info.get(k) for k in
                       ("targetMeanPrice", "numberOfAnalystOpinions",
                        "recommendationKey", "revenueGrowth", "sector", "industry")}
        try:
            df = tk.revenue_estimate
            out["revenue_estimate"] = json.loads(df.to_json(orient="index")) \
                if df is not None else None
        except Exception as e:
            out["revenue_estimate_err"] = str(e)
    except Exception as e:
        out["err"] = str(e)
    cons_g, key = None, None
    try:
        re_ = out.get("revenue_estimate") or {}
        for k in ("+1y", "0y"):
            if k in re_ and re_[k].get("growth") is not None:
                cons_g, key = float(re_[k]["growth"]), k
                break
    except Exception:
        pass
    if cons_g is None:
        cons_g = (out.get("info") or {}).get("revenueGrowth")
        if cons_g is not None:
            key = "info.revenueGrowth(近況,非預測)"
    return out, cons_g, key


def main():
    import yfinance as yf
    gates = pd.read_csv(os.path.join(D, "screen_pool_197_gates.csv"))
    pool = gates[gates["in_pool"].astype(str).isin(["True", "true"])].copy()
    tickers = pool["ticker"].tolist()
    ocf_map = dict(zip(pool["ticker"], pool["ocf_ttm"]))
    mcap_map = dict(zip(pool["ticker"], pool["mcap_now_usd"]))
    rel_map = dict(zip(pool["ticker"], pool["rel_spy"]))
    sic_map = dict(zip(pool["ticker"], pool["sic_description"]))
    print("新池 %d 家" % len(tickers), flush=True)

    spy = yf.Ticker("SPY").history(period="2y", auto_adjust=False)["Close"]
    spy.index = [d.date() for d in spy.index]
    rate_inputs = IE.rule_discount_rate()
    print("資本成本規則:美債 %.3f%% + 無槓桿溢價 %.1fpp,差價 %.1fpp,D/E 上限 %.1f,重槓桿 %s"
          % (100 * rate_inputs["treasury_yield"], 100 * rate_inputs["equity_premium"],
             100 * rate_inputs["credit_spread"], rate_inputs["de_cap"],
             rate_inputs["relever"]), flush=True)

    rows, meta, hist_cache, analyst_raw = [], {}, {}, {}
    for i, t in enumerate(tickers, 1):
        r = dict(ticker=t, rel_spy_screen=rel_map.get(t),
                 mcap_screen=mcap_map.get(t), sic_description=sic_map.get(t))
        try:
            fin = IE.build_financials(t)
        except Exception as e:
            r["error"] = "建帳失敗:%s" % e
            rows.append(r); print("%3d/%d %-6s 建帳失敗" % (i, len(tickers), t), flush=True)
            continue
        try:
            mkt = IE.market_data(fin)
        except Exception as e:
            r["error"] = "無價格:%s" % e
            rows.append(r); print("%3d/%d %-6s 無價格" % (i, len(tickers), t), flush=True)
            continue
        fin = IE.reconcile_diluted_shares(fin, mkt.shares_now)
        fresh = IE.filing_freshness(fin.cik, fin.asof, mkt.price_date)
        price = mkt.price
        pb = price_block(t, spy, mkt.price_date, price, hist_cache)
        if pb is None:
            r["error"] = "價格歷史不足"
            rows.append(r); print("%3d/%d %-6s 價格歷史不足" % (i, len(tickers), t), flush=True)
            continue
        r.update(pb)
        ocf = ocf_map.get(t)
        nd = fin.net_debt
        r.update(name=fin.name, asof=str(fin.asof), price=price,
                 price_date=str(mkt.price_date),
                 is_closing_price=not mkt.price_check.get("fell_back"),
                 market_state=mkt.price_check.get("market_state"),
                 stale=fresh.get("stale"), stale_lag_days=fresh.get("lag_days"),
                 latest_filing=fresh.get("latest_filing_date"),
                 latest_report=fresh.get("latest_report_date"),
                 expired=fresh.get("expired"),
                 rev_ttm=fin.rev_ttm, op_margin=fin.op_margin,
                 rev_growth_yoy=fin.rev_growth_yoy, net_debt=nd, ocf_ttm=ocf,
                 debt=fin.debt, cash=fin.cash, investments=fin.investments,
                 lease_debt=fin.lease_debt, sbc_ttm=fin.sbc_ttm,
                 diluted_shares=fin.diluted_shares,
                 fin_notes="; ".join(fin.notes) if fin.notes else "")
        # 負債:只作標籤,不剔人(D-173)
        ndo = (nd / ocf) if (ocf and ocf > 0) else None
        r["net_debt_to_ocf"] = ndo
        r["debt_label"] = ("淨現金" if nd < 0 else
                           "算不出" if ndo is None else
                           "低(≤3 倍)" if ndo <= 3 else
                           "中(3–6 倍)" if ndo <= 6 else "高(>6 倍)")
        r["debt_gate_old"] = bool(nd < 0 or (ndo is not None and ndo <= 3))
        if not fin.diluted_shares:
            r["error"] = "稀釋股數為 0"
            rows.append(r); print("%3d/%d %-6s 股數 0" % (i, len(tickers), t), flush=True)
            continue
        mcap = price * fin.diluted_shares
        r["mcap_now"] = mcap
        wd = IE.cost_of_capital(fin, market_cap=mcap, tax_rate=TAX_RATE,
                                treasury_yield=rate_inputs["treasury_yield"],
                                equity_premium=rate_inputs["equity_premium"],
                                credit_spread=rate_inputs["credit_spread"],
                                round_step=rate_inputs["rounded_to"],
                                de_cap=rate_inputs["de_cap"], relever=True)
        a = generic_assumptions(fin, wd["wacc"])
        r.update(wacc=wd["wacc"], wacc_raw=wd["wacc_raw"], de_ratio=wd["de_ratio"],
                 de_capped=wd["de_capped"], wacc_net_cash=wd["net_cash"],
                 wacc_floor_binding=wd["wacc_floor_binding"])
        try:
            g5 = IE.solve(fin, a, "bad_growth", price, *IE.GBOUND)
        except Exception:
            g5 = None
        r["n1_implied_g5"] = g5
        per_share = tshare = None
        try:
            v = IE.value(fin, a)
            per_share, tshare = v.per_share, v.terminal_share
        except Exception as e:
            r["n2_error"] = str(e)
        upside = (per_share / price - 1.0) if (per_share and per_share > 0) else None
        unreliable = []
        if fin.op_margin is None or fin.op_margin <= 0:
            unreliable.append("現時營業利潤率 ≤ 0")
        if tshare is not None and tshare > 1.5:
            unreliable.append("終值佔比 >150%")
        if per_share is None or per_share <= 0:
            unreliable.append("每股值無解或 ≤ 0")
        r["n2_unreliable"] = "; ".join(unreliable)
        # 市銷率
        ps_now = price * fin.diluted_shares / fin.rev_ttm if fin.rev_ttm else None
        p50_4y = mkt.ps_hist.get("p50"); p50_1y = mkt.ps_hist_1y.get("p50")
        p25_1y = mkt.ps_hist_1y.get("p25")
        ratio4 = (ps_now / p50_4y) if (p50_4y and ps_now) else None
        ratio1 = (ps_now / p50_1y) if (p50_1y and ps_now) else None
        grade = ("資料不足" if (ratio4 is None or ratio1 is None) else
                 "兩把尺都過" if (ratio4 <= 0.8 and ratio1 <= 0.8) else
                 "只過一把(重估已完成,不是折讓)" if (ratio4 <= 0.8 or ratio1 <= 0.8)
                 else "都不過")
        r.update(ps_now=ps_now, ps_p50_4y=p50_4y, ps_p50_1y=p50_1y, ps_p25_1y=p25_1y,
                 ps_ratio_4y=ratio4, ps_ratio_1y=ratio1, discount_grade=grade)
        # 數三與壓力
        dil = max(0.005, (fin.sbc_ttm or 0.0) / mcap)
        ret1 = (p50_1y * fin.rev_ttm / (fin.diluted_shares * (1 + dil)) / price - 1.0) \
            if (p50_1y and fin.rev_ttm) else None
        r.update(dilution_1y=dil, n3_ret_1y=ret1)
        if p25_1y and fin.rev_ttm:
            sp = p25_1y * fin.rev_ttm * 0.9 / fin.diluted_shares
            raw_drop = sp / price - 1.0
        else:
            sp, raw_drop = None, None
        floor = pb["mdd_1y"]
        if raw_drop is None or raw_drop > floor:
            drop, applied = floor, True
        else:
            drop, applied = raw_drop, False
        drop = min(drop, -0.05)
        r.update(stress_price=sp, stress_drop_raw=raw_drop, stress_drop=drop,
                 stress_floor_applied=bool(applied))
        # A-055:資料落後即扣起基準每股值(連賠率)
        withheld = bool(fresh.get("stale"))
        odds = (upside / abs(drop)) if (upside is not None and drop) else None
        r["baseline_withheld"] = withheld
        if withheld:
            r.update(n2_per_share=None, n2_upside=None, odds=None,
                     n2_per_share_withheld=per_share, n2_upside_withheld=upside,
                     odds_withheld=odds, n2_terminal_share=tshare)
        else:
            r.update(n2_per_share=per_share, n2_upside=upside, odds=odds,
                     n2_terminal_share=tshare)
        # 共識與機制標籤輸入
        ar, cons_g, key = analyst_block(t)
        analyst_raw[t] = ar
        r.update(consensus_rev_growth=cons_g, consensus_growth_key=key)
        r["gap_vs_consensus_pp"] = (None if (cons_g is None or g5 is None)
                                    else (g5 - cons_g) * 100)
        rows.append(r)
        meta[t] = dict(freshness=IE._jsonable(fresh), price_check=IE._jsonable(mkt.price_check))
        print("%3d/%d %-6s 價 %8.2f 數一 %7s 數二 %8s 數三 %7s 壓力 %5.0f%% 賠率 %6s %s%s"
              % (i, len(tickers), t, price,
                 "n/a" if g5 is None else "%+.1f%%" % (100 * g5),
                 "n/a" if r.get("n2_upside") is None else "%+.0f%%" % (100 * r["n2_upside"]),
                 "n/a" if ret1 is None else "%+.0f%%" % (100 * ret1),
                 100 * drop,
                 "n/a" if r.get("odds") is None else "%.2f" % r["odds"],
                 r["ma200_form"], "(扣起)" if withheld else ""), flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(D, "screen_pool_197.csv"), index=False, encoding="utf-8-sig")
    with open(os.path.join(D, "screen_pool_197.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(rate_inputs=IE._jsonable(rate_inputs),
                       run_at_eastern=IE._now_eastern().strftime("%Y-%m-%d %H:%M:%S %Z"),
                       per_ticker=meta), fh, indent=1, ensure_ascii=False, default=str)
    with open(os.path.join(D, "yf_analyst_raw_197.json"), "w", encoding="utf-8") as fh:
        json.dump(analyst_raw, fh, indent=1, ensure_ascii=False, default=str)
    print("=" * 70)
    print("完成 %d 家;錯誤 %d 家" % (len(df), int(df["error"].notna().sum())
                                    if "error" in df else 0))


if __name__ == "__main__":
    main()
