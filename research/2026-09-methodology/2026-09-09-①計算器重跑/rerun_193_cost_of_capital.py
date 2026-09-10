# -*- coding: utf-8 -*-
"""KARST-193 口徑修正重跑:七家(SNOW/AXTI/LULU/TDC/ON/ENPH/ARM)。

前(KARST-190):折現率 = 股權成本(十年期美債 + 5%,四捨五入至 0.5%),全批共用。
後(KARST-193):折現率 = WACC(股權成本與稅後債務成本按市值 / 有息負債帳面值加權,
                四捨五入至 0.5% 在 WACC 層做);淨現金公司 WACC = 股權成本,值不變。

輸出:
  2026-09-09-隱含預期計算器口徑修正重跑.json   完整重跑(含 _meta.cost_of_capital)
  2026-09-09-隱含預期計算器口徑修正重跑.txt    可讀重跑紀錄
  2026-09-09-KARST193-前後差異.csv             前後基準每股值差異表(供寫報告)
"""
import io
import json
import os
import sys
from dataclasses import replace

sys.path.insert(0, r"C:\projects\Karst\strategy\tools")
import implied_expectations as IE  # noqa: E402

OUT = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①計算器重跑"  # 2026-09-11 倉內整理搬入子目錄
TICKERS = ["SNOW", "AXTI", "LULU", "TDC", "ON", "ENPH", "ARM"]


def base_assumptions(C, wacc):
    return IE.Assumptions(
        bad_growth=C["stage1_growth_ref"], bad_years=C["stage1_years_ref"],
        recovery_growth=C["recovery_growth"], target_margin=C["target_margin"],
        margin_ramp_years=C["margin_ramp_years"], horizon=C["horizon"],
        tax_rate=C["tax_rate"], sales_to_capital=C["sales_to_capital"],
        wacc=wacc, terminal_growth=C["terminal_growth"],
        terminal_roic=C["terminal_roic"])


def main():
    rate = IE.rule_discount_rate()
    ke_rounded = rate["rate"]          # 舊口徑(KARST-190)的全批共用折現率
    buf = io.StringIO()

    def w(s=""):
        print(s)
        buf.write(s + "\n")

    w("KARST-193 口徑修正重跑 —— 企業自由現金流配加權資本成本")
    w("十年期美債 %.3f%%(來源 %s,取數日 %s)" % (
        100 * rate["treasury_yield"], rate["treasury_source"], rate["treasury_date"]))
    w("股權成本(未四捨五入)= %.3f%%;四捨五入後 %.2f%% = 舊口徑全批共用折現率" % (
        100 * rate["raw_rate"], 100 * ke_rounded))
    w("稅前債務成本 = 美債 + 信用差價 %.1f 個百分點(示例值,待對齊)= %.3f%%" % (
        100 * rate["credit_spread"], 100 * rate["cost_of_debt_pretax"]))
    w("兩個來源的嘗試紀錄:%s" % json.dumps(rate["attempts"], ensure_ascii=False))
    w()

    res = {"_meta": dict(discount_rate=rate, cost_of_capital={},
                         old_rule_rate=ke_rounded, ticket="KARST-193")}
    diff_rows = []
    for t in TICKERS:
        r = IE.analyse(t, rate_inputs=rate)
        res[t] = IE._jsonable(r)
        d = r["wacc_detail"]
        res["_meta"]["cost_of_capital"][t] = IE._jsonable(d)
        fin, mkt, C = r["fin"], r["mkt"], r["cfg"]

        # 前:同一組固定假設,折現率換回舊口徑的股權成本(四捨五入後)
        before = IE.value(fin, base_assumptions(C, ke_rounded)).per_share
        after_check = IE.value(fin, base_assumptions(C, d["wacc"])).per_share
        after = r["valA"]["基準"]["per_share"]
        assert abs(after - after_check) < 1e-6, (t, after, after_check)

        # 另一個淨現金口徑:現金 + 短期及長期投資
        alt = IE.cost_of_capital(fin, market_cap=mkt.price * fin.diluted_shares,
                                 tax_rate=C["tax_rate"],
                                 treasury_yield=rate["treasury_yield"],
                                 credit_spread=rate["credit_spread"],
                                 net_cash_include_investments=True)
        alt_ps = IE.value(fin, base_assumptions(C, alt["wacc"])).per_share

        # 四捨五入的貢獻:未四捨五入的 WACC 對比未四捨五入的股權成本,
        # 分開「槓桿本身」與「跨過 0.5% 的界」兩件事各佔多少
        ps_raw_wacc = IE.value(fin, base_assumptions(C, d["wacc_raw"])).per_share
        ps_raw_ke = IE.value(fin, base_assumptions(C, d["cost_of_equity"])).per_share

        diff_rows.append(dict(
            ticker=t, price=mkt.price, price_date=str(mkt.price_date),
            debt=d["debt_book"], cash=d["cash"], investments=d["investments"],
            lease_debt=d["lease_debt"], market_cap=d["market_cap"],
            net_cash=d["net_cash"], cost_of_equity=d["cost_of_equity"],
            cost_of_debt_after_tax=d["cost_of_debt_after_tax"],
            weight_debt=d["weight_debt"], weight_equity=d["weight_equity"],
            wacc_raw=d["wacc_raw"], wacc=d["wacc"], old_rate=ke_rounded,
            ps_before=before, ps_after=after, ps_diff=after - before,
            ps_diff_pct=(after / before - 1.0) if before else None,
            alt_net_cash=alt["net_cash"], alt_wacc=alt["wacc"], alt_ps=alt_ps,
            ps_raw_wacc=ps_raw_wacc, ps_raw_ke=ps_raw_ke,
            ps_diff_leverage=ps_raw_wacc - ps_raw_ke,
            ps_diff_rounding=(after - before) - (ps_raw_wacc - ps_raw_ke),
        ))

        w("=" * 78)
        w("%s  現價 %.2f (%s)  市值 %.0fM  有息負債 %.0fM  現金 %.0fM  投資 %.0fM  租賃 %.0fM"
          % (t, mkt.price, mkt.price_date, d["market_cap"] / 1e6, d["debt_book"] / 1e6,
             d["cash"] / 1e6, d["investments"] / 1e6, d["lease_debt"] / 1e6))
        w("  資本成本:股權 %.3f%% × %.2f%% + 稅後債務 %.3f%% × %.2f%% = %.3f%% → %.1f%%%s"
          % (100 * d["cost_of_equity"], 100 * d["weight_equity"],
             100 * d["cost_of_debt_after_tax"], 100 * d["weight_debt"],
             100 * d["wacc_raw"], 100 * d["wacc"],
             "(淨現金,WACC = 股權成本)" if d["net_cash"] else ""))
        w("  基準每股值:前(折現率 %.1f%%)%.2f → 後(WACC %.1f%%)%.2f  差 %+.2f (%+.1f%%)"
          % (100 * ke_rounded, before, 100 * d["wacc"], after, after - before,
             100 * ((after / before - 1.0) if before else 0.0)))
        w("  另一口徑(現金 + 投資 當現金):淨現金 %s,WACC %.1f%%,基準每股值 %.2f"
          % (alt["net_cash"], 100 * alt["wacc"], alt_ps))
        w("  差異拆解:槓桿本身 %+.2f(未四捨五入 %.3f%% 對 %.3f%%)+ 四捨五入跨界 %+.2f"
          % (ps_raw_wacc - ps_raw_ke, 100 * d["wacc_raw"], 100 * d["cost_of_equity"],
             (after - before) - (ps_raw_wacc - ps_raw_ke)))
        for n in fin.notes:
            w("  [注意] " + n)
        w("  三組聯合情境(每股值):")
        for k, v in r["valA_joint"].items():
            if v.get("per_share") is None:
                w("    %-44s 無解" % k)
            else:
                w("    %-44s %8.2f  相對現價 %+6.1f%%  終值佔比 %.0f%%"
                  % (k, v["per_share"], 100 * v["upside"], 100 * v["terminal_share"]))
        w("  一年回報表四情境(一年淨稀釋 %.2f%%):" % (100 * r["dilution_1y"]))
        for row in r["oneyear_four"]:
            if row["price1"] is None:
                w("    %d %-32s %s" % (row["seq"], row["scenario"], row["note"]))
                continue
            w("    %d %-32s 收入格 %-22s 倍數 %-22s 一年後 %8.2f  回報 %+7.1f%%"
              % (row["seq"], row["scenario"], row["growth_case"], row["mult_case"],
                 row["price1"], 100 * row["ret"]))
            w("        重估理由:%s" % (row["rerating_reason"] or "(空白 —— 未填)"))
        for warn in r["rerating_warnings"]:
            w("    [注意] " + warn)
        w("  (乙 附錄)原有情境網格保留 %d 行" % len(r["oneyear"]))

    w()
    w("=" * 78)
    w("前後基準每股值差異總表")
    w("%-6s %-8s %-8s %-10s %-10s %-10s %-9s %s"
      % ("代號", "舊折現率", "新WACC", "前", "後", "差", "差%", "淨現金"))
    for x in diff_rows:
        w("%-6s %7.1f%% %7.1f%% %10.2f %10.2f %+10.2f %+8.1f%% %s"
          % (x["ticker"], 100 * x["old_rate"], 100 * x["wacc"], x["ps_before"],
             x["ps_after"], x["ps_diff"], 100 * (x["ps_diff_pct"] or 0.0),
             "是" if x["net_cash"] else "否"))

    with open(os.path.join(OUT, "2026-09-09-隱含預期計算器口徑修正重跑.json"),
              "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1, default=str)
    with open(os.path.join(OUT, "2026-09-09-隱含預期計算器口徑修正重跑.txt"),
              "w", encoding="utf-8") as fh:
        fh.write(buf.getvalue())
    import csv
    with open(os.path.join(OUT, "2026-09-09-KARST193-前後差異.csv"),
              "w", encoding="utf-8", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(diff_rows[0].keys()))
        wr.writeheader()
        wr.writerows(diff_rows)


if __name__ == "__main__":
    main()
