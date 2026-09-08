import sys, datetime as dt, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, r"C:\projects\Karst\strategy\tools")
import implied_expectations as IE
import yfinance as yf, pandas as pd
pd.set_option("display.width", 250)

CASES = {
 "LMB": dict(rev_ttm=683_771_000., op_margin=.0574549081490733, growth=.23665672548782002,
             net_debt=37_195_000., shares=12_040_218., price=49.66,
             cash=17_529_000., debt=35_842_000., sbc=7_654_000.),
 "LINC": dict(rev_ttm=570_778_000., op_margin=.05911054735816727, growth=.2202290476159936,
              net_debt=153_023_000., shares=31_418_794., price=25.575,
              cash=44_178_000., debt=26_000_000., sbc=5_999_000.),
}

def mk(c, lease=True):
    ebit = c["rev_ttm"] * c["op_margin"]
    ld = (c["net_debt"] + c["cash"] - c["debt"]) if lease else 0.0
    return IE.Financials(ticker="X", cik="0", name="X", asof=dt.date(2026,6,30),
        rev_ttm=c["rev_ttm"], ebit_ttm=ebit, sbc_ttm=c["sbc"], da_ttm=0., capex_ttm=0.,
        tax_rate_hist=None, diluted_shares=c["shares"], cash=c["cash"], investments=0.,
        debt=c["debt"], lease_debt=ld, nci=0.)

def A(c, **kw):
    g = max(-.5, min(1., c["growth"]))
    d = dict(bad_growth=g, bad_years=5, recovery_growth=g*.5, target_margin=c["op_margin"],
             margin_ramp_years=1, horizon=10, tax_rate=.23, sales_to_capital=2.0,
             wacc=.10, terminal_growth=.025, terminal_roic=.15)
    d.update(kw); return IE.Assumptions(**d)

print("############ 一、經營租賃雙重計算的影響 ############")
for t, c in CASES.items():
    lease = c["net_debt"] + c["cash"] - c["debt"]
    v1 = IE.value(mk(c, True), A(c)); v2 = IE.value(mk(c, False), A(c))
    print("%-5s 經營租賃負債(推導)= %.1fM" % (t, lease/1e6))
    print("      含租於淨負債:每股 %.2f (%+.1f%%)   不含租:每股 %.2f (%+.1f%%)   差 %.2f/股" %
          (v1.per_share, (v1.per_share/c["price"]-1)*100, v2.per_share,
           (v2.per_share/c["price"]-1)*100, v2.per_share-v1.per_share))

print("\n############ 二、自訂情境(利潤率恢復 + 可負擔的增速) ############")
SCEN = {
 "LMB": [("悲觀:利潤率停在 5.75%,增速降到 5%", dict(bad_growth=.05, recovery_growth=.025, target_margin=.0575, sales_to_capital=3.0)),
         ("基準:利潤率回到 8.0%(FY2025 水平),增速 6%", dict(bad_growth=.06, recovery_growth=.03, target_margin=.080, margin_ramp_years=3, sales_to_capital=3.0)),
         ("樂觀:利潤率到 10%(ODR 佔比續升),增速 8%", dict(bad_growth=.08, recovery_growth=.04, target_margin=.100, margin_ramp_years=3, sales_to_capital=3.0)),
         ("零增長 + 8% 利潤率(不需再投資)", dict(bad_growth=.0, recovery_growth=.0, target_margin=.080, margin_ramp_years=3, sales_to_capital=1e9)),
        ],
 "LINC": [("悲觀:利潤率停在 5.9%,增速 3%,資本強度照實際(s2c=1.0)", dict(bad_growth=.03, recovery_growth=.015, target_margin=.059, sales_to_capital=1.0)),
          ("基準:建校完成後 s2c 回到 3.0,利潤率升到 9%,增速 6%", dict(bad_growth=.06, recovery_growth=.03, target_margin=.090, margin_ramp_years=4, sales_to_capital=3.0)),
          ("樂觀:利潤率到 12%,增速 8%,s2c=3.0", dict(bad_growth=.08, recovery_growth=.04, target_margin=.120, margin_ramp_years=4, sales_to_capital=3.0)),
          ("零增長 + 9% 利潤率(不需再投資)", dict(bad_growth=.0, recovery_growth=.0, target_margin=.090, margin_ramp_years=4, sales_to_capital=1e9)),
         ],
}
for t, c in CASES.items():
    print("---- %s (現價 %.2f)" % (t, c["price"]))
    for name, kw in SCEN[t]:
        for lease, tag in [(True,"含租"), (False,"不含租")]:
            v = IE.value(mk(c, lease), A(c, **kw))
            print("   %-46s %s 每股 %7.2f  %+7.1f%%  終值佔比 %3.0f%%" %
                  (name if tag=="含租" else "", tag, v.per_share,
                   (v.per_share/c["price"]-1)*100, v.terminal_share*100))

print("\n############ 三、季度收入與利潤率走勢(yfinance quarterly) ############")
for t in CASES:
    tk = yf.Ticker(t)
    q = tk.quarterly_financials
    rows = [r for r in ["Total Revenue","Operating Income","Gross Profit","Net Income"] if r in q.index]
    df = q.loc[rows].T
    if "Total Revenue" in df and "Operating Income" in df:
        df["op_margin%"] = (df["Operating Income"]/df["Total Revenue"]*100).round(2)
    print("====", t); print(df.to_string())

print("\n############ 四、歷史實際 sales-to-capital ############")
for t in CASES:
    tk = yf.Ticker(t); cf = tk.cashflow; fi = tk.financials
    rev = fi.loc["Total Revenue"]
    capex = cf.loc["Capital Expenditure"] if "Capital Expenditure" in cf.index else None
    acq = cf.loc["Purchase Of Business"] if "Purchase Of Business" in cf.index else None
    print("====", t)
    yrs = sorted(set(rev.index) & set(capex.index), reverse=True)
    for i in range(len(yrs)-1):
        y, yp = yrs[i], yrs[i+1]
        dr = rev[y]-rev[yp]
        cx = -capex[y] if not pd.isna(capex[y]) else 0
        aq = (-acq[y] if (acq is not None and not pd.isna(acq[y])) else 0)
        inv = cx+aq
        print("  %s 收入增 %+7.1fM  資本開支 %6.1fM  收購 %6.1fM  合計 %6.1fM  → s2c = %s" %
              (str(y)[:10], dr/1e6, cx/1e6, aq/1e6, inv/1e6,
               ("%.2f" % (dr/inv)) if inv > 0 else "n/a"))
