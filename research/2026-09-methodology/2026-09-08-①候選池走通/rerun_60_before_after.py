"""KARST-186 第三步:對 KARST-184 六十家過閘名單重跑「三個數」,比對
strategy/tools/implied_expectations.py 兩處抽取缺陷修復前後的差異。

修復內容(見票 KARST-186、strategy/tools/README.md「淨負債取數規則」一節):
  (一) A-048:instant_series 由「第一個有資料的標籤就用」改成「有序後備清單,
      取第一個覆蓋到 asof 附近 200 日內的標籤」,缺數不再靜默當 0
  (二) A-047:AXTI 的 LongTermInvestments 經 10-Q 附註核實為可流通證券,規則本身不用改,
      只是把判斷規則寫入 README——這一項對數字沒有影響,只有 (一) 會動到淨負債

本腳本不改任何候選卡結論(五家的 CASES/判斷書不動),只對 60 家用同一組**通用、機械式**
假設(不含任何個股質性判斷)算「基準每股值」與「隱含五年增速」,分離出純粹由取數缺陷
造成的差異。這組通用假設本身不是候選判斷,只用來做前後對照。

通用假設(全部 60 家同一套,不逐家調):
  wacc=10.0%(KARST-184 折現率規則)、terminal_growth=2.5%、terminal_roic=15%、
  tax_rate=23%、sales_to_capital=2.0、horizon=10
  第一階段(5 年)增長率 = 近四年 TTM 收入年增率(查不到則跳過該公司,不臆測)
  目標利潤率 = 現時 GAAP 營業利潤率(即假設利潤率不變,margin_ramp_years=1)
  「隱含增速」= 反推表 A 在 D=5、目標利潤率固定於現時利潤率下解出的第一階段年增率
  ——回答「現價要求收入五年增長多少,才剛好打平,在『利潤率不變』這個機械假設下」

輸出:2026-09-08-取數修復後六十家重跑差異.md
"""
import sys, os, datetime as dt, io, json
from dataclasses import replace
import pandas as pd

sys.path.insert(0, r"C:\projects\Karst\strategy\tools")
import implied_expectations as IE  # noqa

OUT_DIR = r"C:\projects\Karst\research\2026-09-methodology\2026-09-08-①候選池走通"

TICKERS = ['ADTN', 'SEDG', 'INOD', 'VPG', 'LINC', 'ARRY', 'UTI', 'MRAM', 'CIEN', 'LASR',
           'ENPH', 'AAON', 'STRL', 'RMBS', 'AIP', 'CLFD', 'CEVA', 'TROX', 'LMB', 'ON',
           'ARM', 'POWL', 'MEC', 'MYRG', 'LUMN', 'ORCL', 'AGX', 'DOCN', 'FN', 'MTZ',
           'AMKR', 'CRNC', 'MOD', 'FSLR', 'CRUS', 'IPGP', 'IREN', 'GNRC', 'CDNS', 'TTMI',
           'CENX', 'CLS', 'VIAV', 'ALB', 'FLEX', 'COLL', 'MRCY', 'SAIA', 'QCOM', 'HLIT',
           'KRMN', 'PUMP', 'SANM', 'CRDO', 'CLVT', 'MTSI', 'TDC', 'LULU', 'DRS', 'ACLS']

WACC = 0.10

# ---------------------------------------------------------------------------
# 修復前的舊版 instant_series(第一個有資料的標籤就用,不管新不新鮮)——
# 原封不動照抄 KARST-186 修復前的寫法,只用來重建「修復前」的財務物件做對照。
# ---------------------------------------------------------------------------

def _old_instant_series(facts, tags):
    best = {}
    for tag in tags:
        for r in IE._rows(facts, tag):
            if "start" in r or "end" not in r:
                continue
            k = IE._d(r["end"])
            filed = r.get("filed", "")
            if k not in best or filed >= best[k][0]:
                best[k] = (filed, float(r["val"]))
        if best:
            break
    return {k: v[1] for k, v in best.items()}


def build_financials_old(ticker: str) -> IE.Financials:
    """修復前行為的重建版:複製 build_financials,但用舊版 instant_series。"""
    cik = IE.cik_for(ticker)
    facts = IE.load_facts(cik)
    notes = []
    rev_q = IE.quarterize(IE.duration_series(facts, IE.REV_TAGS))
    ebit_q = IE.quarterize(IE.duration_series(facts, IE.EBIT_TAGS))
    sbc_q = IE.quarterize(IE.duration_series(facts, IE.SBC_TAGS))
    da_q = IE.quarterize(IE.duration_series(facts, IE.DA_TAGS))
    capex_q = IE.quarterize(IE.duration_series(facts, IE.CAPEX_TAGS))
    tax_q = IE.quarterize(IE.duration_series(facts, IE.TAX_TAGS))
    pretax_q = IE.quarterize(IE.duration_series(facts, IE.PRETAX_TAGS))
    dil_q = IE.quarterize(IE.duration_series(facts, IE.DILUTED_TAGS))

    asof = max(rev_q)
    rev_ttm, _ = IE.ttm(rev_q)
    ebit_ttm, _ = IE.ttm(ebit_q, asof)
    sbc_ttm, _ = IE.ttm(sbc_q, asof)
    da_ttm, _ = IE.ttm(da_q, asof)
    capex_ttm, _ = IE.ttm(capex_q, asof)
    sbc_ttm = sbc_ttm or 0.0
    da_ttm = da_ttm or 0.0
    capex_ttm = capex_ttm or 0.0
    if ebit_ttm is None:
        raise RuntimeError("缺 OperatingIncomeLoss")

    tax_rate_hist = None
    tt, _ = IE.ttm(tax_q, asof) if tax_q else (None, [])
    pt, _ = IE.ttm(pretax_q, asof) if pretax_q else (None, [])
    if tt is not None and pt is not None and pt > 0:
        tax_rate_hist = tt / pt

    dil_ttm_ends = sorted(dil_q)
    diluted_shares = dil_q[dil_ttm_ends[-1]] if dil_ttm_ends else 0.0

    cash = IE._latest(_old_instant_series(facts, IE.CASH_TAGS), asof)
    inv = (IE._latest(_old_instant_series(facts, IE.STI_TAGS), asof)
           + IE._latest(_old_instant_series(facts, IE.LTI_TAGS), asof))
    debt = (IE._latest(_old_instant_series(facts, IE.DEBT_CUR_TAGS), asof)
            + IE._latest(_old_instant_series(facts, IE.DEBT_NC_TAGS), asof))
    lease = (IE._latest(_old_instant_series(facts, IE.LEASE_CUR_TAGS), asof)
             + IE._latest(_old_instant_series(facts, IE.LEASE_NC_TAGS), asof))
    nci = IE._latest(_old_instant_series(facts, IE.NCI_TAGS), asof)

    return IE.Financials(
        ticker=ticker.upper(), cik=cik, name=facts.get("entityName", ticker),
        asof=asof, rev_ttm=rev_ttm, ebit_ttm=ebit_ttm, sbc_ttm=sbc_ttm,
        da_ttm=da_ttm, capex_ttm=capex_ttm, tax_rate_hist=tax_rate_hist,
        diluted_shares=diluted_shares, cash=cash, investments=inv,
        debt=debt, lease_debt=lease, nci=nci,
        rev_ttm_hist=IE.ttm_series(rev_q), rev_q=rev_q, notes=notes,
    )


# ---------------------------------------------------------------------------
# 通用機械式假設(不含個股判斷,只用來做前後對照的量尺)
# ---------------------------------------------------------------------------

def generic_assumptions(fin: IE.Financials) -> IE.Assumptions:
    g = fin.rev_growth_yoy
    if g is None:
        g = 0.0
    g = max(-0.5, min(1.0, g))  # 夾在反推搜尋範圍內,避免不合理極端值
    margin = fin.op_margin
    return IE.Assumptions(
        bad_growth=g, bad_years=5, recovery_growth=g * 0.5,
        target_margin=margin, margin_ramp_years=1, horizon=10,
        tax_rate=0.23, sales_to_capital=2.0,
        wacc=WACC, terminal_growth=0.025, terminal_roic=0.15,
    )


def three_numbers(fin: IE.Financials, price: float):
    a = generic_assumptions(fin)
    try:
        v = IE.value(fin, a)
        per_share = v.per_share
    except Exception:
        per_share = None
    try:
        g5 = IE.solve(fin, a, "bad_growth", price, *IE.GBOUND)
    except Exception:
        g5 = None
    return dict(net_debt=fin.net_debt, per_share=per_share, implied_g5=g5,
                rev_growth_used=a.bad_growth, margin_used=a.target_margin)


def main():
    rows = []
    for t in TICKERS:
        row = dict(ticker=t)
        try:
            fin_new = IE.build_financials(t)
        except Exception as e:
            row["error"] = f"新版建帳失敗: {e}"
            rows.append(row)
            print(t, "新版建帳失敗", e)
            continue
        try:
            fin_old = build_financials_old(t)
        except Exception as e:
            row["error"] = f"舊版建帳失敗: {e}"
            rows.append(row)
            print(t, "舊版建帳失敗", e)
            continue
        try:
            mkt = IE.market_data(fin_new)
            price = mkt.price
        except Exception as e:
            row["error"] = f"市價失敗: {e}"
            rows.append(row)
            print(t, "市價失敗", e)
            continue

        new3 = three_numbers(fin_new, price)
        old3 = three_numbers(fin_old, price)

        row.update(
            price=price,
            net_debt_old=old3["net_debt"], net_debt_new=new3["net_debt"],
            net_debt_diff=new3["net_debt"] - old3["net_debt"],
            per_share_old=old3["per_share"], per_share_new=new3["per_share"],
            per_share_diff=(None if old3["per_share"] is None or new3["per_share"] is None
                            else new3["per_share"] - old3["per_share"]),
            g5_old=old3["implied_g5"], g5_new=new3["implied_g5"],
            g5_diff=(None if old3["implied_g5"] is None or new3["implied_g5"] is None
                     else new3["implied_g5"] - old3["implied_g5"]),
            cheap_old=(None if old3["per_share"] is None else old3["per_share"] > price),
            cheap_new=(None if new3["per_share"] is None else new3["per_share"] > price),
        )
        row["flipped"] = (row.get("cheap_old") is not None and row.get("cheap_new") is not None
                           and row["cheap_old"] != row["cheap_new"])
        rows.append(row)
        print(t, "net_debt_diff=%.1fM" % (row["net_debt_diff"] / 1e6),
              "per_share_diff=%s" % row["per_share_diff"],
              "flipped=%s" % row["flipped"])

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT_DIR, "rerun_60_before_after.csv"), index=False, encoding="utf-8")

    n_ok = df["net_debt_diff"].notna().sum() if "net_debt_diff" in df else 0
    n_material = int((df["net_debt_diff"].abs() > 1e6).sum()) if "net_debt_diff" in df else 0
    n_flip = int(df["flipped"].sum()) if "flipped" in df else 0
    flip_list = df[df["flipped"] == True]["ticker"].tolist() if "flipped" in df else []

    with open(os.path.join(OUT_DIR, "rerun_60_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(n_total=len(TICKERS), n_ok=int(n_ok), n_material_netdebt_diff=n_material,
                        n_flipped=n_flip, flip_list=flip_list), fh, ensure_ascii=False, indent=1)

    print("=" * 60)
    print(f"總數 {len(TICKERS)}  成功算出對照 {n_ok}  淨負債差 >100萬美元的家數 {n_material}"
          f"  機械式『貴平』結論翻轉的家數 {n_flip}")
    print("翻轉名單:", flip_list)


if __name__ == "__main__":
    main()
