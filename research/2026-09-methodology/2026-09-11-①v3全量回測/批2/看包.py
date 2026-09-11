# -*- coding: utf-8 -*-
"""KARST-213 批 2:把取證包內的關鍵數印成一張窄表(供判斷用,不含任何衝擊後結果)。

用法:python 看包.py <E??> [ticker,ticker,...]
"""
import json
import sys

B2 = "C:/projects/Karst/research/2026-09-methodology/2026-09-11-①v3全量回測/批2"


def fmt(v, n=1):
    if v is None or v == "":
        return "-"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)[:14]
    if abs(f) >= 1e9:
        return "%.1fB" % (f / 1e9)
    if abs(f) >= 1e6:
        return "%.0fM" % (f / 1e6)
    return ("%%.%df" % n) % f


def main():
    eid = sys.argv[1]
    pack = json.load(open("%s/packets/%s.json" % (B2, eid), encoding="utf-8"))
    sel = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    print("==", eid, pack["name"], "shock", pack["shock_start"], "->",
          pack.get("news_shock_end"), "disc", pack["discount"].get("discount_rate"))
    print("narrative:", pack["narrative"][:200])
    print("peers(sic2):", json.dumps(pack.get("peers_by_sic2"), ensure_ascii=False))
    hdr = ["ticker", "sic", "drop", "close", "psShock", "ps1yMed", "ps1yLo", "ps1yHi",
           "mcap", "ttmRev", "ttmOCF", "ttmNI", "ocfm", "nim", "ps", "pb", "pe",
           "cash", "debt", "netcashN2", "dta", "revYoy", "revcv8", "dvol", "10K"]
    print(" | ".join(hdr))
    for c in pack["companies"]:
        if sel and c["ticker"] not in sel:
            continue
        b = c.get("price_block") or {}
        p = c.get("prefilings") or {}
        k10 = p.get("10-K", {}) if isinstance(p, dict) else {}
        row = [c["ticker"], c["sic"], fmt(c.get("f_shock_rel_drop"), 3), fmt(b.get("close"), 2),
               fmt(b.get("ps_at_shock"), 2), fmt(b.get("ps_1y_median"), 2),
               fmt(b.get("ps_1y_low"), 2), fmt(b.get("ps_1y_high"), 2),
               fmt(c.get("mcap_usd")), fmt(c.get("ttm_revenue")), fmt(c.get("ttm_ocf")),
               fmt(c.get("ttm_net_income")), fmt(c.get("f_ocf_margin"), 3),
               fmt(c.get("f_ni_margin"), 3), fmt(c.get("f_ps"), 2), fmt(c.get("f_pb"), 2),
               fmt(c.get("f_pe"), 1), fmt(c.get("cash")), fmt(c.get("total_debt")),
               fmt(c.get("f_net_cash_n2")), fmt(c.get("f_debt_to_assets"), 2),
               fmt(c.get("f_rev_growth_yoy"), 3), fmt(c.get("f_rev_cv8"), 3),
               fmt(c.get("dollar_vol_60d")),
               (k10.get("filingDate") or "-")]
        print(" | ".join(str(x) for x in row))
    for c in pack["companies"]:
        if sel and c["ticker"] not in sel:
            continue
        p = c.get("prefilings") or {}
        if isinstance(p, dict):
            print("  ", c["ticker"], p.get("10-K", {}).get("accession"),
                  "|10Q:", [v.get("filingDate") for k, v in p.items() if k.startswith("10-Q")],
                  "|8K:", [v.get("filingDate") for k, v in p.items() if k.startswith("8-K")],
                  "|local10K:", bool(c.get("local_10k_gz")))


if __name__ == "__main__":
    main()
