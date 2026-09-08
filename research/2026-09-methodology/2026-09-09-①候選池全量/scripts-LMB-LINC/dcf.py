import sys, datetime as dt
sys.path.insert(0, r"C:\projects\Karst\strategy\tools")
import implied_expectations as IE

# 由 screen60_full.csv 的欄位重建,避免再打 SEC
CASES = {
 "LMB": dict(rev_ttm=683_771_000., op_margin=.0574549081490733, growth=.23665672548782002,
             net_debt=37_195_000., shares=12_040_218., price=49.66, ocf=52_386_000.,
             cash=17_529_000., debt=35_842_000., ps_now=.8744407470378366,
             ps_p50_1y=1.5282865897985871, ps_p25_1y=1.402636301831704, sbc=7_654_000.,
             mdd1y=-.6387695995072685),
 "LINC": dict(rev_ttm=570_778_000., op_margin=.05911054735816727, growth=.2202290476159936,
              net_debt=153_023_000., shares=31_418_794., price=25.575, ocf=94_023_000.,
              cash=44_178_000., debt=26_000_000., ps_now=1.407790210065275,
              ps_p50_1y=1.7095656663009482, ps_p25_1y=1.456878074237266, sbc=5_999_000.,
              mdd1y=-.5635776023010955),
}

def mk(c):
    ebit = c["rev_ttm"] * c["op_margin"]
    return IE.Financials(ticker="X", cik="0", name="X", asof=dt.date(2026,6,30),
        rev_ttm=c["rev_ttm"], ebit_ttm=ebit, sbc_ttm=c["sbc"], da_ttm=0., capex_ttm=0.,
        tax_rate_hist=None, diluted_shares=c["shares"], cash=c["cash"], investments=0.,
        debt=c["debt"], lease_debt=c["net_debt"] + c["cash"] - c["debt"], nci=0.)

def A(c, **kw):
    g = max(-.5, min(1., c["growth"]))
    d = dict(bad_growth=g, bad_years=5, recovery_growth=g*.5, target_margin=c["op_margin"],
             margin_ramp_years=1, horizon=10, tax_rate=.23, sales_to_capital=2.0,
             wacc=.10, terminal_growth=.025, terminal_roic=.15)
    d.update(kw)
    return IE.Assumptions(**d)

for t, c in CASES.items():
    f = mk(c); p = c["price"]
    print("="*70); print(t, " price %.2f  net_debt %.1fM  shares %.3fM" % (p, c["net_debt"]/1e6, c["shares"]/1e6))
    print(" 重建核對:lease_debt+nci = %.1fM,net_debt = %.1fM" % (f.lease_debt/1e6, f.net_debt/1e6))

    v = IE.value(f, A(c))
    print("\n[基準機械 DCF] 每股 %.2f  上行 %+.1f%%  終值佔比 %.0f%%" %
          (v.per_share, (v.per_share/p-1)*100, v.terminal_share*100))
    print("  頭五年 FCFF(百萬):", ["%.0f" % (x['fcff']/1e6) for x in v.path[:5]])
    print("  6-10年 FCFF(百萬):", ["%.0f" % (x['fcff']/1e6) for x in v.path[5:]])
    print("  明確期現值 %.0fM  終值現值 %.0fM  企業價值 %.0fM" %
          (v.pv_explicit/1e6, v.pv_terminal/1e6, v.ev/1e6))

    print("\n[拆解:再投資假設是不是元凶] 改 sales_to_capital")
    for s2c in [1.0, 2.0, 3.0, 5.0, 10.0, 30.0, 1e9]:
        vv = IE.value(f, A(c, sales_to_capital=s2c))
        lab = "無再投資" if s2c > 1e8 else "%.0f" % s2c
        print("   s2c=%-8s 每股 %8.2f  上行 %+7.1f%%" % (lab, vv.per_share, (vv.per_share/p-1)*100))

    print("\n[拆解:增長假設] 改 bad_growth(s2c 留 2.0)")
    for g in [0.0, .05, .10, .15, .20, c["growth"]]:
        vv = IE.value(f, A(c, bad_growth=g, recovery_growth=g*.5))
        print("   g=%+.1f%%  每股 %8.2f  上行 %+7.1f%%" % (g*100, vv.per_share, (vv.per_share/p-1)*100))

    print("\n[數一:現價要求的五年收入增速(固定利潤率)]")
    for m in [c["op_margin"], .07, .08, .10]:
        try:
            g5 = IE.solve(f, A(c, target_margin=m), "bad_growth", p, *IE.GBOUND)
            print("   利潤率 %.2f%% → 隱含五年增速 %+.1f%%" % (m*100, g5*100))
        except Exception as e:
            print("   利潤率 %.2f%% → 解不出 (%s)" % (m*100, e))
    print("\n[數一 反向:固定增速反推第10年利潤率]")
    for g in [0.0, .05, .10]:
        try:
            m = IE.solve(f, A(c, bad_growth=g, recovery_growth=g*.5), "target_margin", p, .001, .40)
            print("   增速 %+.0f%% → 隱含正常化營業利潤率 %.2f%%" % (g*100, m*100))
        except Exception as e:
            print("   增速 %+.0f%% → 解不出 (%s)" % (g*100, e))

    print("\n[折現率敏感度(基準假設)]")
    for w in [.09, .10, .11]:
        vv = IE.value(f, A(c, wacc=w))
        print("   wacc %.0f%%  每股 %8.2f  上行 %+7.1f%%" % (w*100, vv.per_share, (vv.per_share/p-1)*100))

    print("\n[機械壓力價重算]")
    sp = c["ps_p25_1y"] * c["rev_ttm"] * .9 / c["shares"]
    print("   公式價 = p25_1y %.4f x 收入 %.0fM x 0.9 / 股數 = $%.2f" % (c["ps_p25_1y"], c["rev_ttm"]/1e6, sp))
    print("   相對現價 %+.1f%%  → %s" % ((sp/p-1)*100, "高於現價,公式失效" if sp > p else "低於現價"))
    print("   採用的 stress_drop = 1年最大回撤 %.2f%%" % (c["mdd1y"]*100))
    dil = max(.005, c["sbc"]/(p*c["shares"]))
    print("   稀釋率 %.3f%%   數三 = p50_1y/ps_now/(1+dil)-1 = %+.1f%%" %
          (dil*100, (c["ps_p50_1y"]*c["rev_ttm"]/(c["shares"]*(1+dil))/p-1)*100))
    print("   倉位上限 = 2%% / |%.1f%%| = %.2f%%" % (abs(c["mdd1y"])*100, 2/abs(c["mdd1y"]*100)*100))
