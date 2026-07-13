"""exp_clist_v1.py — C-list v1 candidate computation (compounding-machine crisis shopping list).

WHAT: Produces the raw numbers behind `docs/2026-07-13_clist_v1.md`. The C-list is the crisis-budget
sub-allocation (20-30%) defined in `docs/2026-07-12_opportunity_ladder.md` §危機市: a pre-committed,
pre-priced list of "compounding machines" (wide-moat / high-ROIC / durable-earnings businesses that
are almost never cheap) with two TRIGGER PRICES each. You maintain it when VIX is low; in a crisis you
execute it without thinking. Admission rule (opportunity_ladder finalized): only names whose
expectations-gap reading can cross P_base@14x > 1.0 at a reachable price (i.e. the boring, no-growth,
mid-cycle earnings power alone would cover today's EV) + a hard solvency gate.

HOW P_base INVERTS TO A TRIGGER PRICE (spec: docs/2026-07-12_valuation_expectations_gap_spec.md):
    P_base = 14 * NOPAT_norm / EV ,  EV = market_cap + net_debt
  So as PRICE falls, market_cap falls, EV falls, P_base RISES (price and P_base move opposite).
  To find the price at which P_base hits a target T:
    EV_T   = 14 * NOPAT_norm / T
    mcap_T = EV_T - net_debt
    price_T = price_now * (mcap_T / mcap_now)      # shares outstanding cancel in the ratio
  L1 (調整市檔 / first true-discount line) : T = 1.0  (supercycle-free coverage = 100% of EV)
  L2 (危機市檔 / deep crisis discount)      : T = 1.3  (normalized business worth 30% MORE than EV)
  If mcap_T <= 0 the target is UNREACHABLE at any positive price -> net debt alone exceeds the target
  EV -> the equity is a thin levered slice -> SOLVENCY FAIL (this is the USAC "leverage illusion" the
  spec called out, caught mechanically rather than by eyeball).

DATA: reuses the already-computed rows in `thesis/.raw/valuation_report.json` (today's run) for names
already in the valuation universe; computes NEW nominations live via `thesis.valuation.compute()` (the
production function, imported, NOT reimplemented). Current price per name from yfinance fast_info.

Reads/writes only: reads the valuation JSON (read-only) + network; writes ONE machine-readable dump
`backtest/experiments/exp_clist_v1_out.json`. Touches no existing file. Run: PYTHONUTF8=1 python
backtest/experiments/exp_clist_v1.py
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))          # backtest/experiments/
REPO_ROOT = os.path.dirname(os.path.dirname(ROOT))          # Karst/
sys.path.insert(0, REPO_ROOT)

import yfinance as yf  # noqa: E402
from thesis.valuation import compute  # noqa: E402  (production expectations-gap fn)

JSON_IN = os.path.join(REPO_ROOT, "thesis", ".raw", "valuation_report.json")
JSON_OUT = os.path.join(ROOT, "exp_clist_v1_out.json")

BASE_MULT = 14
L1_TARGET = 1.0   # 調整市檔: P_base@14x crosses 1.0 (admission line per opportunity_ladder)
L2_TARGET = 1.3   # 危機市檔: deeper crisis discount

# Existing valuation-universe names worth considering as compounding machines (rest of the 28 are
# cyclical / supercycle / pre-profit -> not compounders). Pulled from the JSON, not recomputed.
REUSE_FROM_JSON = ["TSM", "ASML", "AVGO", "WST", "LPX", "XOM", "CVX", "AMKR", "MCHP", "KALU", "AVT"]

# NEW nominations: large-cap quality "compounding machines" (high ROIC / wide moat / durable earnings).
# Nominated on business quality; P_base is REALLY computed below and is the admission gate, not the name.
# (ticker, one-line business, quality note)
NOMINATIONS = [
    ("MSFT",  "企業軟件+Azure雲+Office生態", "wide-moat, 淨現金, ROIC極高"),
    ("GOOGL", "搜尋/廣告/YouTube/雲", "wide-moat, 淨現金"),
    ("AAPL",  "iPhone生態+服務", "brand moat, 巨額回購"),
    ("META",  "社交廣告(FB/IG/WhatsApp)", "廣告網絡效應, 淨現金"),
    ("V",     "全球支付網絡", "近乎壟斷雙邊網絡, ROIC最高一檔"),
    ("MA",    "全球支付網絡#2", "同V雙寡頭, 高ROIC"),
    ("COST",  "會員制倉儲零售", "會員續費護城河, 低價飛輪"),
    ("UNH",   "管理式醫療+Optum", "規模護城河, 現金流穩"),
    ("HD",    "家居裝修零售龍頭", "規模+密度護城河"),
    ("TXN",   "類比/嵌入式半導體", "wide-moat, 高ROIC, 長壽產品"),
    ("KLAC",  "半導體製程檢測", "process-control近壟斷"),
    ("LRCX",  "半導體刻蝕/沉積設備", "寡頭, WFE高佔有"),
    ("ADBE",  "創意+文檔軟件(訂閱)", "Creative壟斷, 高毛利"),
    ("ISRG",  "手術機械人(da Vinci)", "裝機+耗材護城河, 淨現金"),
    ("ACN",   "IT顧問/系統整合", "規模+關係護城河"),
    ("LIN",   "工業氣體龍頭", "區域壟斷長約, 定價力"),
    ("MCO",   "信用評級(Moody's)", "評級雙寡頭, 極高ROIC"),
    ("SPGI",  "評級+指數+數據", "評級/指數雙寡頭"),
    ("INTU",  "稅務/中小企軟件(TurboTax/QB)", "轉換成本護城河"),
    ("QCOM",  "手機SoC+授權", "專利授權護城河"),
    ("CSCO",  "企業網絡設備", "現金機器, 高股息回購"),
    ("NKE",   "運動品牌龍頭(近年受挫)", "品牌護城河, 週期低位候選"),
    ("WM",    "廢物處理", "本地壟斷, 抗衰退"),
    ("TMO",   "生命科學工具/耗材", "規模+耗材黏性"),
    ("NVO",   "GLP-1/糖尿病(Novo ADR)", "GLP-1雙寡頭之一"),
    ("ODFL",  "零擔貨運(LTL)龍頭", "最佳營運, 週期性但質優"),
]


def trigger_price(nopat_norm, net_debt, mcap_now, price_now, target):
    """Price at which P_base@14x reaches `target`. Returns (price_T, drawdown_pct, reachable)."""
    if nopat_norm is None or nopat_norm <= 0 or mcap_now is None or mcap_now <= 0 or price_now is None:
        return None, None, False
    ev_t = BASE_MULT * nopat_norm / target
    mcap_t = ev_t - net_debt
    if mcap_t <= 0:
        return None, None, False          # net debt alone exceeds target EV -> unreachable
    price_t = price_now * (mcap_t / mcap_now)
    drawdown = 1.0 - price_t / price_now
    return price_t, drawdown, True


def fetch_price(sym):
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            fi = yf.Ticker(sym).fast_info
            p = getattr(fi, "last_price", None)
        return float(p) if p else None
    except Exception:
        return None


def row_from_json(jrow, ticker):
    return {
        "ticker": ticker,
        "source_of_calc": "valuation_report.json (2026-07-13 run)",
        "e_norm": jrow.get("e_norm"),
        "nopat_norm": jrow.get("nopat_norm"),
        "net_debt": jrow.get("net_debt"),
        "market_cap": jrow.get("market_cap"),
        "ev": jrow.get("ev"),
        "ebit_margin_median": jrow.get("ebit_margin_median"),
        "p_base": jrow.get("p_base"),
        "g_implied": jrow.get("g_implied"),
        "classification": jrow.get("classification"),
        "n_quarters": jrow.get("n_quarters"),
        "fin_currency": jrow.get("fin_currency"),
    }


def row_from_compute(sym):
    r = compute(sym)
    if "error" in r:
        return {"ticker": sym, "error": r["error"]}
    return {
        "ticker": sym,
        "source_of_calc": "live compute() this run",
        "e_norm": r.get("e_norm"),
        "nopat_norm": r.get("nopat_norm"),
        "net_debt": r.get("net_debt"),
        "market_cap": r.get("market_cap"),
        "ev": r.get("ev"),
        "ebit_margin_median": r.get("ebit_margin_median"),
        "p_base": r.get("p_14x"),
        "g_implied": r.get("g_implied"),
        "classification": r.get("classification"),
        "n_quarters": r.get("n_quarters"),
        "fin_currency": r.get("fin_currency"),
    }


def main():
    with open(JSON_IN, encoding="utf-8") as fh:
        vj = json.load(fh)
    jtk = vj.get("tickers", {})

    biz = {t: (b, q) for t, b, q in NOMINATIONS}
    rows = []

    for tk in REUSE_FROM_JSON:
        if tk in jtk:
            r = row_from_json(jtk[tk], tk)
            r["business"] = "(現有 universe)"
            r["quality_note"] = "(現有 universe)"
            r["origin"] = "existing-universe"
            rows.append(r)
        else:
            print(f"WARN reuse {tk} not in JSON")

    for tk, b, q in NOMINATIONS:
        print(f"computing {tk} ...")
        r = row_from_compute(tk)
        r["business"] = b
        r["quality_note"] = q
        r["origin"] = "new-nomination"
        rows.append(r)

    # prices + triggers
    for r in rows:
        if "error" in r:
            continue
        r["price_now"] = fetch_price(r["ticker"])
        for tag, tgt in (("l1", L1_TARGET), ("l2", L2_TARGET)):
            pt, dd, reach = trigger_price(r["nopat_norm"], r["net_debt"], r["market_cap"],
                                          r["price_now"], tgt)
            r[f"{tag}_price"] = pt
            r[f"{tag}_drawdown"] = dd
            r[f"{tag}_reachable"] = reach
        nd, ev = r.get("net_debt"), r.get("ev")
        r["net_debt_to_ev"] = (nd / ev) if (ev and ev > 0) else None

    # gates: E_norm>0 (hard, no binary), L1 reachable at positive price (solvency)
    def passes(r):
        if "error" in r:
            return False
        if (r.get("e_norm") or 0) <= 0:
            return False
        if not r.get("l1_reachable"):
            return False
        if r.get("price_now") is None:
            return False
        return True

    eligible = [r for r in rows if passes(r)]
    rejected = [r for r in rows if not passes(r)]
    eligible.sort(key=lambda r: -(r.get("p_base") or -9))

    out = {
        "as_of": vj.get("as_of"),
        "method": "clist_v1 (expectations-gap v1 P_base inversion)",
        "l1_target_p_base": L1_TARGET,
        "l2_target_p_base": L2_TARGET,
        "trigger_formula": "price_T = price_now * ((14*NOPAT_norm/T - net_debt) / market_cap_now)",
        "eligible_sorted_by_p_base": eligible,
        "rejected": rejected,
        "n_eligible": len(eligible),
    }
    with open(JSON_OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False, default=str)

    def f(x, d=2):
        return "N/A" if x is None else f"{x:.{d}f}"

    print(f"\n=== ELIGIBLE (E_norm>0 & L1 reachable), {len(eligible)} names, sorted by P_base ===")
    print(f"{'TK':<6}{'orig':<10}{'P_base':>7}{'price':>9}{'L1$':>9}{'L1dd':>7}{'L2$':>9}{'L2dd':>7}{'nd/EV':>7}  margin")
    for r in eligible:
        print(f"{r['ticker']:<6}{r['origin'][:9]:<10}{f(r.get('p_base')):>7}{f(r.get('price_now')):>9}"
              f"{f(r.get('l1_price')):>9}{f(r.get('l1_drawdown')):>7}{f(r.get('l2_price')):>9}"
              f"{f(r.get('l2_drawdown')):>7}{f(r.get('net_debt_to_ev')):>7}  {f(r.get('ebit_margin_median'))}")

    print(f"\n=== REJECTED, {len(rejected)} names ===")
    for r in rejected:
        if "error" in r:
            print(f"{r['ticker']:<6} ERROR: {r['error'][:80]}")
        else:
            why = []
            if (r.get("e_norm") or 0) <= 0:
                why.append("E_norm<=0 (binary)")
            if not r.get("l1_reachable"):
                why.append("L1 unreachable (solvency/over-levered)")
            if r.get("price_now") is None:
                why.append("no price")
            print(f"{r['ticker']:<6} P_base={f(r.get('p_base'))} — {', '.join(why) or 'other'}")

    print(f"\nwrote {JSON_OUT}")


if __name__ == "__main__":
    main()
