"""
exp_power_etf_basket.py — ai-power-grid 衛星:ETF 籃覆蓋 vs 重疊研究(非訊號回測)

Question: 用戶想用 ETF 籃(非個股)表達 ai-power-grid 主題(核/氣發電、電網設備、電力半導體、
uranium 燃料週期),候選 {URA, URNM(URES 已由用戶確認 = UTES;URNM 保留做鈾腿對照), NLR, XLU, UTES, GRID, FCG}。
邊 2-3 隻組合「覆蓋最多子腿 + 持倉重疊最少」?
(2026-07-08 更新:用戶確認「URES」原意 = UTES(Virtus Reaves Utilities ETF,主動管理公用),
 已加入宇宙;關鍵判斷 = UTES vs XLU 邊隻做「公用/發電」腿。)

Method: 純描述性研究(唔係訊號回測,冇 IC/no alpha claim)。
  1. URES 身份核實(yfinance load 測試 + WebSearch)。
  2. 全宇宙 + SPY/QQQ 基準,yfinance adjusted daily close,盡量攞 5y。
  3. Top-10 持倉(yfinance funds_data.top_holdings),兩兩 top-10 重疊(名+權重加總)。
  4. Pairwise 日報酬相關矩陣(3y + 2020 起兩窗)+ 對 SPY/QQQ 的 corr/beta。
  5. CAGR/vol/MaxDD(3y/5y/2020+)、費率、AUM、日均量(yfinance info fields)。
  6. 子腿映射表(人手,對照 thesis/wiki/ai-power-grid.md 價值鏈)。
  7. 組合建議(人手綜合,判準:腿覆蓋數 + 內部平均 corr 最低 + 避開最擠估值腿)。

誠實框架(寫入結論):呢批全部係股票 ETF(REIT/公用/工業股),「持倉 top-10 重疊低」
≠「同大市低相關」——corr vs SPY/QQQ 一定要同時報,唔可以用低重疊包裝做「對沖」。

Cost/data assumptions: adjusted close(含息),唔計交易成本(呢度唔係交易訊號)。
"""
import os
import sys
import json
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import yfinance as yf

UNIVERSE = ["URA", "URNM", "NLR", "XLU", "UTES", "GRID", "FCG"]
BENCH = ["SPY", "QQQ"]
ALL_TICKERS = UNIVERSE + BENCH

OUT_MD = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "results", "2026-07-08_power_etf_basket.md",
)


def step0_ures_identity():
    """URES 身份核實：yfinance load 測試。"""
    t = yf.Ticker("URES")
    info = t.info
    hist = t.history(period="5d")
    result = {
        "quoteType": info.get("quoteType"),
        "longName": info.get("longName"),
        "shortName": info.get("shortName"),
        "exchange": info.get("exchange"),
        "history_rows": len(hist),
    }
    return result


def load_prices(tickers, period="5y"):
    data = {}
    for tk in tickers:
        df = yf.download(tk, period=period, auto_adjust=True, progress=False)
        if df.empty:
            print(f"WARN: {tk} empty")
            continue
        s = df["Close"]
        if isinstance(s, pd.DataFrame):
            s = s.iloc[:, 0]
        s.name = tk
        data[tk] = s
    prices = pd.DataFrame(data)
    return prices


def cagr(series):
    n_years = (series.index[-1] - series.index[0]).days / 365.25
    if n_years <= 0:
        return np.nan
    total_ret = series.iloc[-1] / series.iloc[0]
    return total_ret ** (1 / n_years) - 1


def max_dd(series):
    cummax = series.cummax()
    dd = series / cummax - 1
    return dd.min()


def ann_vol(returns):
    return returns.std() * np.sqrt(252)


def stats_for_window(prices, tickers, start=None):
    rows = []
    for tk in tickers:
        s = prices[tk].dropna()
        if start is not None:
            s = s[s.index >= start]
        if len(s) < 30:
            rows.append({"ticker": tk, "CAGR": np.nan, "vol": np.nan, "MaxDD": np.nan, "n_days": len(s)})
            continue
        rets = s.pct_change().dropna()
        rows.append({
            "ticker": tk,
            "CAGR": cagr(s),
            "vol": ann_vol(rets),
            "MaxDD": max_dd(s),
            "n_days": len(s),
        })
    return pd.DataFrame(rows).set_index("ticker")


def corr_beta_matrix(prices, tickers, start=None):
    df = prices[tickers].copy()
    if start is not None:
        df = df[df.index >= start]
    rets = df.pct_change().dropna(how="any")
    corr = rets.corr()
    beta = {}
    for tk in tickers:
        if tk in BENCH:
            continue
        for b in BENCH:
            cov = rets[tk].cov(rets[b])
            var = rets[b].var()
            beta[(tk, b)] = cov / var if var > 0 else np.nan
    return corr, beta, len(rets)


def top10_overlap(holdings: dict):
    """holdings: {ticker: {symbol: weight}}. Returns pairwise overlap dict."""
    tickers = list(holdings.keys())
    overlaps = {}
    detail = {}
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            a, b = tickers[i], tickers[j]
            ha, hb = holdings[a], holdings[b]
            common = set(ha.keys()) & set(hb.keys())
            # overlap weight = sum(min(wa, wb)) over common names (standard overlap measure)
            w = sum(min(ha[s], hb[s]) for s in common)
            overlaps[(a, b)] = w
            detail[(a, b)] = sorted(common, key=lambda s: -min(ha[s], hb[s]))
    return overlaps, detail


def get_holdings(tickers):
    holdings = {}
    for tk in tickers:
        t = yf.Ticker(tk)
        try:
            fd = t.funds_data
            df = fd.top_holdings
            holdings[tk] = dict(zip(df.index, df["Holding Percent"]))
        except Exception as e:
            print(f"WARN holdings {tk}: {e}")
            holdings[tk] = {}
    return holdings


def get_fund_info(tickers):
    rows = []
    for tk in tickers:
        t = yf.Ticker(tk)
        info = t.info
        rows.append({
            "ticker": tk,
            "AUM_USD_bn": (info.get("totalAssets") or 0) / 1e9,
            "expense_ratio_pct": info.get("annualReportExpenseRatio") or info.get("netExpenseRatio"),
            "avg_daily_vol": info.get("averageVolume"),
            "category": info.get("category"),
        })
    return pd.DataFrame(rows).set_index("ticker")


def main():
    print("=== Step 0: URES identity ===")
    ures = step0_ures_identity()
    print(json.dumps(ures, indent=2, default=str))

    print("=== Step 1-2: prices ===")
    prices = load_prices(ALL_TICKERS, period="5y")
    print(prices.tail(3))
    prices.to_csv(os.path.join(os.path.dirname(__file__), "_power_etf_prices.csv"))

    print("=== Step 3: holdings & overlap ===")
    holdings = get_holdings(UNIVERSE)
    overlaps, detail = top10_overlap(holdings)
    for (a, b), w in sorted(overlaps.items(), key=lambda x: -x[1]):
        print(f"{a}-{b}: overlap_weight={w:.3f}  common_names={[d for d in detail[(a,b)]]}")

    print("=== Step 4: corr/beta ===")
    start_2020 = pd.Timestamp("2020-01-01")
    start_3y = prices.index[-1] - pd.Timedelta(days=365 * 3)
    corr_3y, beta_3y, n_3y = corr_beta_matrix(prices, ALL_TICKERS, start=start_3y)
    corr_2020, beta_2020, n_2020 = corr_beta_matrix(prices, ALL_TICKERS, start=start_2020)
    print("3y corr:\n", corr_3y.round(2))
    print("2020+ corr:\n", corr_2020.round(2))
    print("3y beta:", {k: round(v, 2) for k, v in beta_3y.items()})
    print("2020+ beta:", {k: round(v, 2) for k, v in beta_2020.items()})

    print("=== Step 5: stats ===")
    stats_3y = stats_for_window(prices, ALL_TICKERS, start=start_3y)
    stats_5y = stats_for_window(prices, ALL_TICKERS, start=None)
    stats_2020 = stats_for_window(prices, ALL_TICKERS, start=start_2020)
    print("3y:\n", stats_3y.round(3))
    print("5y:\n", stats_5y.round(3))
    print("2020+:\n", stats_2020.round(3))

    fund_info = get_fund_info(UNIVERSE + BENCH)
    print(fund_info)

    # dump everything needed for report writing to a json for traceability
    out = {
        "ures": ures,
        "overlaps": {f"{a}-{b}": w for (a, b), w in overlaps.items()},
        "overlap_detail": {f"{a}-{b}": v for (a, b), v in detail.items()},
        "corr_3y": corr_3y.round(3).to_dict(),
        "corr_2020": corr_2020.round(3).to_dict(),
        "beta_3y": {f"{k[0]}_vs_{k[1]}": round(v, 3) for k, v in beta_3y.items()},
        "beta_2020": {f"{k[0]}_vs_{k[1]}": round(v, 3) for k, v in beta_2020.items()},
        "stats_3y": stats_3y.round(4).to_dict(orient="index"),
        "stats_5y": stats_5y.round(4).to_dict(orient="index"),
        "stats_2020": stats_2020.round(4).to_dict(orient="index"),
        "fund_info": fund_info.round(4).to_dict(orient="index"),
        "n_days_3y": n_3y,
        "n_days_2020": n_2020,
        "holdings": holdings,
    }
    with open(os.path.join(os.path.dirname(__file__), "_power_etf_basket_data.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str, ensure_ascii=False)
    print("Saved intermediate data JSON.")


if __name__ == "__main__":
    main()
