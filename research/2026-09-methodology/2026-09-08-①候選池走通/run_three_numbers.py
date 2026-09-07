"""KARST-184 第三步:對五個候選跑「三個數」(隱含預期反推)。

用 KARST-183 的計算器 strategy/tools/implied_expectations.py,但**不改動該檔**:
固定假設與資產負債表更正由本檔注入(monkeypatch),改動全部有記錄。

折現率規則(KARST-184 定,可預登記,不逐家手調):
    折現率 = 美國十年期國債收益率(取數日 2026-09-04,^TNX 收 4.784%)+ 股權溢價 5.0%
           = 9.784% → 四捨五入至 0.5% → **10.0%**,同一批候選全部同一個數。
    敏感度另跑 ±1 個百分點(9.0% / 11.0%)。

輸出:three_numbers.json、three_numbers.txt
"""
import sys, json, io
from dataclasses import replace

sys.path.insert(0, r"C:\projects\Karst\strategy\tools")
import implied_expectations as IE  # noqa

OUT = r"C:\projects\Karst\research\2026-09-methodology\2026-09-08-①候選池走通"

WACC = 0.10          # 由上述規則得出,五家同一個數
WACC_SENS = (0.09, 0.11)

# --- 資產負債表人手更正(XBRL 標籤缺口;每項註明來源與理由)---------------
BS_FIX = {
    # lululemon:companyfacts 的 CashAndCashEquivalentsAtCarryingValue 最後一筆停在
    # 2019 財年,現金改用 CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents
    # 2026-05-03 的 1,515 百萬(10-Q 資產負債表)。不更正的話現金當 0,淨負債會誇大 15 億。
    "LULU": dict(cash=1515e6, investments=0.0),
}

CASES = {
    # 五家的固定假設。折現率由規則定死,其餘各項是判斷,理由寫在總覽檔的假設清單。
    "TDC": dict(
        wacc=WACC, terminal_growth=0.025, terminal_roic=0.15, tax_rate=0.23,
        sales_to_capital=3.0, margin_ramp_years=5, horizon=10,
        recovery_growth=0.02, target_margin=0.18,
        stage1_growth_ref=-0.03, stage1_years_ref=5, dilution_1y=0.020,
        g1_cases={"加速流失(收入 -10%)": -0.10, "緩慢流失(-3%)": -0.03, "企穩(+2%)": 0.02},
    ),
    "ARM": dict(
        wacc=WACC, terminal_growth=0.025, terminal_roic=0.25, tax_rate=0.23,
        sales_to_capital=4.0, margin_ramp_years=6, horizon=10,
        recovery_growth=0.08, target_margin=0.40,
        stage1_growth_ref=0.25, stage1_years_ref=5, dilution_1y=0.020,
        g1_cases={"授權見頂(+5%)": 0.05, "減速(+15%)": 0.15, "維持現速(+25%)": 0.25},
    ),
    "ON": dict(
        wacc=WACC, terminal_growth=0.025, terminal_roic=0.12, tax_rate=0.23,
        sales_to_capital=1.2, margin_ramp_years=4, horizon=10,
        recovery_growth=0.04, target_margin=0.25,
        stage1_growth_ref=0.05, stage1_years_ref=5, dilution_1y=0.010,
        g1_cases={"再跌一年(-8%)": -0.08, "見底走平(0%)": 0.0, "週期回升(+12%)": 0.12},
    ),
    "ENPH": dict(
        wacc=WACC, terminal_growth=0.025, terminal_roic=0.15, tax_rate=0.23,
        sales_to_capital=4.0, margin_ramp_years=4, horizon=10,
        recovery_growth=0.05, target_margin=0.20,
        stage1_growth_ref=0.05, stage1_years_ref=5, dilution_1y=0.020,
        g1_cases={"補貼退場(-20%)": -0.20, "走平(0%)": 0.0, "回升(+15%)": 0.15},
    ),
    "LULU": dict(
        wacc=WACC, terminal_growth=0.025, terminal_roic=0.18, tax_rate=0.23,
        sales_to_capital=3.0, margin_ramp_years=3, horizon=10,
        recovery_growth=0.03, target_margin=0.17,
        stage1_growth_ref=0.03, stage1_years_ref=5, dilution_1y=0.005,
        g1_cases={"北美續跌(-5%)": -0.05, "走平(0%)": 0.0, "低單位數增長(+4%)": 0.04},
    ),
}

_orig_build = IE.build_financials


def build_patched(ticker: str):
    fin = _orig_build(ticker)
    fix = BS_FIX.get(ticker.upper())
    if fix:
        fin = replace(fin, **fix)
        fin.notes.append("本票人手更正資產負債表:%s(見 run_three_numbers.py 的 BS_FIX)" % fix)
    return fin


IE.build_financials = build_patched
IE.CASES.update(CASES)

TICKERS = ["TDC", "ARM", "ON", "ENPH", "LULU"]


def main():
    out = {}
    buf = io.StringIO()
    for t in TICKERS:
        rec = {}
        IE.CASES[t] = dict(CASES[t])
        rec["base"] = IE.analyse(t)
        for w in WACC_SENS:
            IE.CASES[t] = dict(CASES[t], wacc=w)
            try:
                rec["wacc_%.2f" % w] = IE.analyse(t)
            except Exception as e:
                rec["wacc_%.2f" % w] = {"error": str(e)}
        IE.CASES[t] = dict(CASES[t])
        out[t] = rec
        # 可讀輸出
        b = rec["base"]
        f, m = b["fin"], b["mkt"]
        buf.write("=" * 70 + "\n")
        buf.write(f"{t} {f.name} 帳目截至 {f.asof} 現價 {m.price:.2f} ({m.price_date})\n")
        buf.write(f"  TTM 收入 {f.rev_ttm/1e6:,.0f}M 營業利潤率 {f.op_margin:.1%} "
                  f"淨負債 {f.net_debt/1e6:,.0f}M 稀釋股數 {f.diluted_shares/1e6:,.1f}M "
                  f"股權薪酬 {f.sbc_ttm/1e6:,.0f}M\n")
        buf.write(f"  市銷率 現時 {m.ps_now:.2f} / 四年 p25-p50-p75 "
                  f"{m.ps_hist['p25']:.2f}-{m.ps_hist['p50']:.2f}-{m.ps_hist['p75']:.2f}"
                  f" / 近一年中位 {m.ps_hist_1y.get('p50', float('nan')):.2f}\n")
        buf.write("  表A 固定利潤率 %.0f%%,反推第一階段收入年增率:\n" % (b["cfg"]["target_margin"] * 100))
        for r in b["tableA"]:
            g = r["implied_growth"]
            buf.write(f"    {r['years']} 年: {('無解' if g is None else format(g,'+.1%'))}"
                      f"  終值佔比 {('-' if r['terminal_share'] is None else format(r['terminal_share'],'.0%'))}"
                      f"  對比現時 {('-' if r['gap_vs_current'] is None else format(r['gap_vs_current']*100,'+.1f') + ' 個百分點')}\n")
            if r["years"] == 5:
                buf.write("      敏感度(各 ±10%,反推增長率變動百分點):"
                          + ", ".join("%s %s %+.1f" % (s["key"], s["bump"], s["delta"] * 100)
                                      for s in r["sens"] if s.get("delta") is not None) + "\n")
        buf.write("  表B 固定收入路徑,反推第 10 年正常化營業利潤率:\n")
        for r in b["tableB"]:
            mm = r["implied_margin"]
            buf.write(f"    第一階段增長 {r['stage1_growth']:+.0%}: "
                      f"{('無解' if mm is None else format(mm,'.1%'))}"
                      f"  終值佔比 {('-' if r['terminal_share'] is None else format(r['terminal_share'],'.0%'))}\n")
        for w in WACC_SENS:
            rr = rec["wacc_%.2f" % w]
            if isinstance(rr, dict) and "tableA" in rr:
                g5 = [x for x in rr["tableA"] if x["years"] == 5][0]["implied_growth"]
                buf.write(f"  [折現率 {w:.1%}] 表A 5 年隱含增長 "
                          f"{('無解' if g5 is None else format(g5,'+.1%'))}\n")
        buf.write("  (甲)長期價值範圍(每股):\n")
        for name, v in b["valA"].items():
            buf.write(f"    {name}: {v['per_share']:.2f}  相對現價 {v['upside']:+.0%}"
                      f"  終值佔比 {v['terminal_share']:.0%}\n")
        buf.write("  (乙)一年持有回報情境(一年淨稀釋 %.1f%%):\n" % (b["dilution_1y"] * 100))
        for s in b["oneyear"]:
            buf.write(f"    {s['growth_case']} × {s['mult_case']}: 一年後 {s['price1']:.2f} "
                      f"回報 {s['ret']:+.0%}\n")
        if f.notes:
            buf.write("  [注意] " + " / ".join(f.notes) + "\n")
    txt = buf.getvalue()
    print(txt)
    with open(OUT + r"\three_numbers.txt", "w", encoding="utf-8") as fh:
        fh.write(txt)
    with open(OUT + r"\three_numbers.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1, default=IE._jsonable)


if __name__ == "__main__":
    main()
