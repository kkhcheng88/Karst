import sys, datetime as dt, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, r"C:\projects\Karst\strategy\tools")
import implied_expectations as IE

P = 25.575
REV = 570_778_000.
M0 = 0.05911054735816727      # 機械層 op_margin
SH = 31_418_794.
SBC = 5_999_000.

# 10-Q 一手(accession 0001140361-26-031995,2026-06-30)
CASH   = 44_178_000.
REVOLV = 26_000_000.
FINLEASE = 30_898_000.        # 流動 534 + 非流動 30,364
OPLEASE  = 171_201_000.       # 流動 11,127 + 非流動 160,074

ND = {
 "機械層原值(漏融資租賃)": 153_023_000.,
 "口徑A 租金留損益、只計有息(循環+融資租賃)": REVOLV + FINLEASE - CASH,
 "口徑B 機械層定義修正(有息+經營租賃−現金)": REVOLV + FINLEASE + OPLEASE - CASH,
}

def mk(nd):
    return IE.Financials(ticker="LINC", cik="0", name="LINC", asof=dt.date(2026,6,30),
        rev_ttm=REV, ebit_ttm=REV*M0, sbc_ttm=SBC, da_ttm=0., capex_ttm=0.,
        tax_rate_hist=None, diluted_shares=SH, cash=CASH, investments=0.,
        debt=REVOLV+FINLEASE, lease_debt=nd-(REVOLV+FINLEASE)+CASH, nci=0.)

def A(**kw):
    d = dict(bad_growth=.2202290476159936, bad_years=5, recovery_growth=.1101145238,
             target_margin=M0, margin_ramp_years=1, horizon=10, tax_rate=.23,
             sales_to_capital=2.0, wacc=.10, terminal_growth=.025, terminal_roic=.15)
    d.update(kw); return IE.Assumptions(**d)

print("=== 一、淨負債三種口徑,對基準 DCF 的影響")
for lab, nd in ND.items():
    f = mk(nd); v = IE.value(f, A())
    print("  %-40s 淨負債 %7.1fM  每股 %6.2f  %+7.1f%%" % (lab, nd/1e6, v.per_share, (v.per_share/P-1)*100))

ND_A = ND["口徑A 租金留損益、只計有息(循環+融資租賃)"]
print("\n  註:機械層 net_debt 153.0M = 循環 26.0 + 經營租賃 171.2 − 現金 44.2,漏了融資租賃 30.9M")
print("      yfinance Total Debt 228.099M = 26.0 + 30.898 + 171.201 (逐位吻合)")

print("\n=== 二、LINC 歷年營業利潤率(近四季是不是高位?)")
HIST = [("FY2022",17_150_000.,348_287_000.),("FY2023",6_660_000.,378_070_000.),
        ("FY2024",14_502_000.,440_064_000.),("FY2025",28_980_000.,518_241_000.),
        ("TTM 2026-06-30",REV*M0,REV)]
for y,e,r in HIST: print("   %-16s 營業利潤 %7.1fM 收入 %7.1fM  利潤率 %5.2f%%" % (y,e/1e6,r/1e6,e/r*100))

print("\n=== 三、機械層用的增速 vs 實況")
Q=[("2025Q2",116_474_000.),("2025Q3",141_389_000.),("2025Q4",142_872_000.),
   ("2026Q1",143_957_000.),("2026Q2",142_560_000.)]
for i,(k,v) in enumerate(Q):
    seq = "" if i==0 else "  按季 %+5.2f%%" % ((v/Q[i-1][1]-1)*100)
    print("   %-8s 收入 %7.1fM%s" % (k, v/1e6, seq))
print("   機械層 rev_growth_yoy = +22.02%(2026Q2 對 2025Q2);近四季按季幾乎零增長")
print("   FY2026 公司指引 590-600M vs FY2025 518.2M = +13.8% 至 +15.8%;分析師 FY2027 共識 +8.9%")

f = mk(ND_A)
print("\n=== 四、口徑A 之下的數一(現價要求什麼)")
for m in [M0,.07,.09,.12,.15]:
    try:
        g5 = IE.solve(f, A(target_margin=m), "bad_growth", P, *IE.GBOUND)
        print("   利潤率 %5.2f%% → 隱含五年收入增速 %+7.1f%%" % (m*100, g5*100))
    except Exception as e: print("   利潤率 %5.2f%% → 解不出" % (m*100))
for g in [0.,.05,.09,.15]:
    try:
        m = IE.solve(f, A(bad_growth=g, recovery_growth=g*.5), "target_margin", P, .001, .45)
        print("   增速 %+4.0f%% → 隱含正常化營業利潤率 %6.2f%%" % (g*100, m*100))
    except Exception as e: print("   增速 %+4.0f%% → 解不出" % (g*100))

print("\n=== 五、自訂情境(口徑A,淨負債 %.1fM;另列加入 7/7 新按揭 15.04M 後)" % (ND_A/1e6))
SC = [("悲觀:利潤率退回 4.0%(FY2024 3.3% 與 FY2025 5.6% 之間),增速 3%,資本強度照實際 s2c=1.0",
       dict(bad_growth=.03, recovery_growth=.015, target_margin=.040, margin_ramp_years=3, sales_to_capital=1.0)),
      ("基準:利潤率升到 7.0%,增速 6%,s2c=2.0",
       dict(bad_growth=.06, recovery_growth=.03, target_margin=.070, margin_ramp_years=4, sales_to_capital=2.0)),
      ("樂觀:建校完成、利潤率到 9.0%,增速 8%,s2c=3.0",
       dict(bad_growth=.08, recovery_growth=.04, target_margin=.090, margin_ramp_years=4, sales_to_capital=3.0)),
      ("對照:零增長 + 7% 利潤率(不需再投資)",
       dict(bad_growth=.0, recovery_growth=.0, target_margin=.070, margin_ramp_years=4, sales_to_capital=1e9))]
for name, kw in SC:
    v1 = IE.value(mk(ND_A), A(**kw)); v2 = IE.value(mk(ND_A+15_040_000.), A(**kw))
    print("   %-72s 每股 %6.2f (%+6.1f%%) | 含新按揭 %6.2f (%+6.1f%%)" %
          (name, v1.per_share, (v1.per_share/P-1)*100, v2.per_share, (v2.per_share/P-1)*100))

print("\n=== 六、下半年隱含加速度(兩家對照)")
print("  LMB  調整後EBITDA利潤率:上半年 22.6/312.3 = %.2f%%;全年指引下限要求下半年 %.2f%%  → 倍數 %.2f" %
      (22.6/312.3*100, 55.4/447.7*100, (55.4/447.7)/(22.6/312.3)))
h1r, h1e = 286.518, 28.199
for lo,hi,rl,rh in [(76.,80.,590.,600.)]:
    h2e_lo, h2e_hi = lo-h1e, hi-h1e
    h2r_lo, h2r_hi = rl-h1r, rh-h1r
    print("  LINC 調整後EBITDA利潤率:上半年 %.2f/%.2f = %.2f%%;全年指引要求下半年 %.2f%%-%.2f%%  → 倍數 %.2f-%.2f" %
          (h1e,h1r,h1e/h1r*100, h2e_lo/h2r_hi*100, h2e_hi/h2r_lo*100,
           (h2e_lo/h2r_hi)/(h1e/h1r), (h2e_hi/h2r_lo)/(h1e/h1r)))
print("  LINC 新生入學:上半年 11,478 對重列 10,531 = +9.0%;全年指引 +10~14% 要求下半年 +%.1f%% ~ +%.1f%%" %
      ((20906*1.10-11478)/10375*100-100, (20906*1.14-11478)/10375*100-100))

print("\n=== 七、壓力情境(由可查數字推)")
print("  收入 560M(低於 FY2026 指引 590-600M);營業利潤率 3.30%(FY2024 實績)→ EBIT 18.5M")
da = 7.789*4
print("  折舊攤銷年化 %.1fM(2026Q2 季 7.789M x4)→ EBITDA %.1fM" % (da, 560*.033+da))
ebitda = 560*.033+da
for mult in [6.,7.,9.]:
    for ndl, tag in [(ND_A/1e6+15.04, "口徑A+新按揭"), ((ND["口徑B 機械層定義修正(有息+經營租賃−現金)"])/1e6+15.04, "口徑B 全額資本化")]:
        eq = mult*ebitda - ndl
        print("   EV/EBITDA %.0fx  %-16s 企業價值 %6.1fM − 淨負債 %6.1fM = 股權 %6.1fM → 每股 %5.2f (%+6.1f%%)" %
              (mult, tag, mult*ebitda, ndl, eq, eq/31.418794, (eq/31.418794/P-1)*100))
print("  同業現時 EV/EBITDA:PRDO 5.85x STRA 7.17x APEI 9.04x LOPE 10.47x LAUR 10.57x UTI 17.16x LINC 16.45x")
