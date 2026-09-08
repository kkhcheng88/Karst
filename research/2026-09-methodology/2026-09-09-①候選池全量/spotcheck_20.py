"""KARST-188 抽核:對六十家之中的 20 家(三分之一),用**另一條資料路徑**重算
不含模型判斷的機械欄位,與 run_60_full.py 的輸出逐格比對。

抽核名單 = 排位前十二家全部 + 另外 8 家(涵蓋被股數更正影響的 VIAV、
KARST-184 的四家舊候選、以及大型股 QCOM),共 20 家。

另一條路徑:
  淨負債   —— yfinance 的季度資產負債表(Ticker.balance_sheet / quarterly_balance_sheet),
              對比 SEC companyfacts 抽出來的淨負債
  市銷率   —— yfinance 市值 ÷ 近四季收入(Ticker.income_stmt),對比 現價 × 稀釋股數 ÷ TTM 收入
  200 日線 —— 另行下載一段價格自行計算,對比腳本輸出的形態格
  同業歸因 —— 重算同業中位數

輸出:spotcheck_20.csv、spotcheck_20.txt
"""
import os, sys, glob, json
import pandas as pd
import numpy as np

OUT_DIR = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"
SRC_DIR = r"C:\projects\Karst\research\2026-09-methodology\2026-09-08-①候選池走通"

CHECK = ["CRDO", "STRL", "COLL", "AAON", "CLS", "KRMN", "LULU", "INOD", "CRUS", "FN",
         "AGX", "CLVT", "ADTN", "ENPH", "ON", "ARM", "QCOM", "ORCL", "TDC", "VIAV"]


def yf_net_debt(tk):
    """由 yfinance 季度資產負債表算淨負債(現金+短期投資 − 總債務)。"""
    try:
        bs = tk.quarterly_balance_sheet
        if bs is None or bs.empty:
            bs = tk.balance_sheet
        if bs is None or bs.empty:
            return None, "無資產負債表"
        col = bs.columns[0]

        def g(*names):
            for n in names:
                if n in bs.index:
                    v = bs.loc[n, col]
                    if pd.notna(v):
                        return float(v)
            return 0.0
        cash = g("Cash And Cash Equivalents", "CashAndCashEquivalents",
                 "Cash Cash Equivalents And Short Term Investments")
        sti = g("Other Short Term Investments", "Short Term Investments")
        lti = g("Long Term Equity Investment", "Investmentin Financial Assets",
                "Available For Sale Securities")
        debt = g("Total Debt")
        if debt == 0.0:
            debt = g("Long Term Debt") + g("Current Debt")
        return debt - cash - sti - lti, str(col.date())
    except Exception as e:
        return None, "錯誤 %s" % e


def main():
    import yfinance as yf
    df = pd.read_csv(os.path.join(OUT_DIR, "screen60_full.csv")).set_index("ticker")
    raw = pd.read_csv(os.path.join(SRC_DIR, "screen_step1_raw.csv")).dropna(subset=["sic", "rel_spy"])
    raw["sic4"] = raw["sic"].astype(int)
    raw["sic2"] = raw["sic4"] // 100

    rows = []
    for t in CHECK:
        r = df.loc[t]
        tk = yf.Ticker(t)
        out = dict(ticker=t)

        # 1) 200 日線:另行下載,自己計
        h = tk.history(period="18mo", auto_adjust=False)["Close"]
        px = float(h.iloc[-1])
        ma = float(h.iloc[-200:].mean())
        mas = h.rolling(200).mean()
        slope = float(mas.iloc[-1]) / float(mas.iloc[-41]) - 1.0
        form = "回調" if px > ma else ("殺" if slope <= 0 else "線附近")
        out.update(price_chk=px, price_src=float(r["price"]),
                   price_ok=abs(px / float(r["price"]) - 1) < 0.005,
                   form_chk=form, form_src=r["ma200_form"], form_ok=(form == r["ma200_form"]))

        # 2) 市銷率:yfinance 市值 ÷ 近四季收入
        ps_alt = None
        try:
            mc = tk.fast_info.get("marketCap")
            inc = tk.quarterly_income_stmt
            if inc is not None and not inc.empty and "Total Revenue" in inc.index:
                rev4 = float(inc.loc["Total Revenue"].dropna().iloc[:4].sum())
                if mc and rev4 > 0:
                    ps_alt = mc / rev4
        except Exception:
            pass
        out.update(ps_src=float(r["ps_now"]), ps_chk=ps_alt,
                   ps_ok=(None if ps_alt is None else abs(ps_alt / float(r["ps_now"]) - 1) < 0.15))

        # 3) 淨負債:yfinance 資產負債表
        nd, nd_asof = yf_net_debt(tk)
        src_nd = float(r["net_debt"])
        tol = max(abs(src_nd) * 0.25, 0.02 * px * float(r["diluted_shares"]))
        out.update(nd_src_musd=round(src_nd / 1e6), nd_chk_musd=(None if nd is None else round(nd / 1e6)),
                   nd_asof=nd_asof,
                   nd_ok=(None if nd is None else abs(nd - src_nd) <= tol))

        # 4) 負債閘方向(淨現金 or 淨負債/營運現金流 ≤ 3)
        out.update(debt_gate_src=bool(r["debt_gate"]),
                   debt_gate_chk=(None if nd is None else
                                  (nd < 0 or (r["ocf_ttm"] and r["ocf_ttm"] > 0
                                              and nd / r["ocf_ttm"] <= 3.0))))
        out["debt_gate_ok"] = (None if out["debt_gate_chk"] is None
                               else out["debt_gate_chk"] == out["debt_gate_src"])

        # 5) 同業歸因:重算
        row = raw[raw["ticker"] == t]
        kill = None
        if not row.empty:
            s4, s2 = int(row["sic4"].iloc[0]), int(row["sic2"].iloc[0])
            g = raw[(raw["sic4"] == s4) & (raw["ticker"] != t)]
            if len(g) < 5:
                g = raw[(raw["sic2"] == s2) & (raw["ticker"] != t)]
            if len(g) >= 5:
                m = float(g["rel_spy"].median())
                kill = "行業殺" if m <= -0.15 else ("個別殺" if m >= -0.05 else "混合")
        out.update(kill_src=r["kill_type"], kill_chk=kill, kill_ok=(kill == r["kill_type"]))

        # 6) 折讓格:用腳本存下的市銷率分位重推,核規則有沒有寫錯
        gr = ("資料不足" if pd.isna(r["ps_ratio_4y"]) or pd.isna(r["ps_ratio_1y"]) else
              "兩把尺都過" if (r["ps_ratio_4y"] <= 0.8 and r["ps_ratio_1y"] <= 0.8) else
              "只過一把(重估已完成,不是折讓)" if (r["ps_ratio_4y"] <= 0.8 or r["ps_ratio_1y"] <= 0.8)
              else "都不過")
        out.update(grade_src=r["discount_grade"], grade_chk=gr, grade_ok=(gr == r["discount_grade"]))

        # 7) 鎖定結論重推
        cc = ("不入" if (not bool(r["debt_gate"]) or r["ma200_form"] == "回調"
                        or gr == "都不過") else
              "入選" if (gr == "兩把尺都過" and r["ma200_form"] == "殺" and bool(r["debt_gate"]))
              else "觀察")
        out.update(concl_src=r["A_conclusion"], concl_chk=cc, concl_ok=(cc == r["A_conclusion"]))

        rows.append(out)
        print(t, "價%s 形態%s 市銷率%s 淨負債%s 負債閘%s 歸因%s 折讓%s 結論%s" % tuple(
            "OK" if out[k] else ("?" if out[k] is None else "**不符**")
            for k in ("price_ok", "form_ok", "ps_ok", "nd_ok", "debt_gate_ok",
                      "kill_ok", "grade_ok", "concl_ok")))

    d = pd.DataFrame(rows)
    d.to_csv(os.path.join(OUT_DIR, "spotcheck_20.csv"), index=False, encoding="utf-8")
    print("=" * 60)
    for k in ("price_ok", "form_ok", "ps_ok", "nd_ok", "debt_gate_ok", "kill_ok",
              "grade_ok", "concl_ok"):
        v = d[k]
        print("%-14s 相符 %d  不符 %d  無法核 %d" %
              (k, int((v == True).sum()), int((v == False).sum()), int(v.isna().sum())))
    bad = d[(d[["price_ok", "form_ok", "ps_ok", "nd_ok", "debt_gate_ok", "kill_ok",
                "grade_ok", "concl_ok"]] == False).any(axis=1)]
    print("有不符的家數:", len(bad), list(bad["ticker"]))


if __name__ == "__main__":
    main()
