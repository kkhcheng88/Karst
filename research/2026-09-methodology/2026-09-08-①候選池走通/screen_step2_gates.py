"""KARST-184 第二步:對初篩名單跑「第一版篩」四道閘(財務透明、流動性、已有現金流、
壓力下不依賴短期再融資)。

資料只用本地 SEC companyfacts 快取(data/sec/companyfacts),重用 KARST-183 計算器的
解析函式(strategy/tools/implied_expectations.py)。

四道閘的判準(寫死在這裡,不逐家調):
  G1 財務透明 —— companyfacts 有近四季收入與營業利潤、有資產負債表;最近一季季末
                 不早於 2026-03-31(即申報未落後超過兩季)
  G2 流動性   —— 已在第一步做:市值 ≥ 3 億美元、近 60 日中位成交金額 ≥ 300 萬美元
  G3 已有現金流 —— 近四季營運現金流 > 0
  G4 不靠短期再融資 —— (現金+投資) ≥ 短期有息負債 × 2,且(淨現金,或
                     淨負債 ÷ 近四季營運現金流 ≤ 3)

輸出:screen_step2_gates.csv
"""
import sys, os, datetime as dt
import pandas as pd

sys.path.insert(0, r"C:\projects\Karst\strategy\tools")
import implied_expectations as IE  # noqa

OUT = r"C:\projects\Karst\research\2026-09-methodology\2026-09-08-①候選池走通"

OCF_TAGS = ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"]

MIN_ASOF = dt.date(2026, 3, 31)


def gate_row(t: str) -> dict:
    r = dict(ticker=t)
    try:
        fin = IE.build_financials(t)
    except Exception as e:
        r["G1_transparent"] = False
        r["note"] = f"建帳失敗: {type(e).__name__}: {e}"
        return r
    facts = IE.load_facts(fin.cik)
    ocf_q = IE.quarterize(IE.duration_series(facts, OCF_TAGS))
    ocf_ttm, _ = IE.ttm(ocf_q, fin.asof) if ocf_q else (None, [])

    short_debt = IE._latest(IE.instant_series(facts, IE.DEBT_CUR_TAGS), fin.asof)
    liquid = fin.cash + fin.investments

    def _safe(fn, default=None):
        try:
            return fn()
        except Exception:
            return default

    r.update(
        name=fin.name, cik=fin.cik, asof=str(fin.asof),
        rev_ttm=fin.rev_ttm, ebit_ttm=fin.ebit_ttm,
        op_margin=_safe(lambda: fin.op_margin),
        rev_growth_yoy=_safe(lambda: fin.rev_growth_yoy),
        cash=fin.cash, investments=fin.investments, debt=fin.debt,
        lease_debt=fin.lease_debt, short_debt=short_debt, net_debt=fin.net_debt,
        ocf_ttm=ocf_ttm, capex_ttm=fin.capex_ttm,
        fcf_ttm=(None if ocf_ttm is None else ocf_ttm - fin.capex_ttm),
        sbc_ttm=fin.sbc_ttm, diluted_shares=fin.diluted_shares,
        notes="; ".join(fin.notes),
    )
    r["G1_transparent"] = bool(fin.rev_ttm and fin.ebit_ttm is not None
                              and fin.asof >= MIN_ASOF)
    r["G3_has_cashflow"] = bool(ocf_ttm is not None and ocf_ttm > 0)
    cover = liquid >= short_debt * 2
    if fin.net_debt <= 0:
        lev_ok = True
    elif ocf_ttm and ocf_ttm > 0:
        lev_ok = (fin.net_debt / ocf_ttm) <= 3.0
    else:
        lev_ok = False
    r["G4_no_refi_need"] = bool(cover and lev_ok)
    r["net_debt_to_ocf"] = (fin.net_debt / ocf_ttm) if (ocf_ttm and ocf_ttm > 0) else None
    return r


def main():
    short = pd.read_csv(OUT + r"\screen_step1_shortlist.csv")
    tickers = short["ticker"].tolist()
    print(f"gating {len(tickers)} tickers", flush=True)
    rows = []
    for i, t in enumerate(tickers):
        rows.append(gate_row(t))
        if (i + 1) % 25 == 0:
            print(f"  {i+1}/{len(tickers)}", flush=True)
    g = pd.DataFrame(rows)
    m = short.merge(g, on="ticker", how="left", suffixes=("", "_sec"))
    for c in ("G1_transparent", "G3_has_cashflow", "G4_no_refi_need"):
        m[c] = m[c].fillna(False)
    m["G2_liquidity"] = True  # 第一步已篩
    m["pass_v1_screen"] = m["G1_transparent"] & m["G3_has_cashflow"] & m["G4_no_refi_need"]
    m = m.sort_values(["pass_v1_screen", "rel_spy"], ascending=[False, True])
    m.to_csv(OUT + r"\screen_step2_gates.csv", index=False, encoding="utf-8")
    print(f"pass: {int(m['pass_v1_screen'].sum())} / {len(m)}", flush=True)
    cols = ["ticker", "name", "rel_spy", "mcap_now_usd", "sic_description",
            "G1_transparent", "G3_has_cashflow", "G4_no_refi_need", "pass_v1_screen"]
    print(m[m["pass_v1_screen"]][cols].to_string(), flush=True)


if __name__ == "__main__":
    main()
