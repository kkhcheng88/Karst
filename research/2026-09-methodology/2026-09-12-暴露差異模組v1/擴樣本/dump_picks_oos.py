# -*- coding: utf-8 -*-
"""KARST-220 擴樣本:列出四家挑選公司的取證包內容(只含遮蔽後欄位),供逐家寫卡引用。

只印包內已有的東西;結果欄(T/N 兩錨超額)不入包,故本檔印不出來。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKT = HERE / "packets_oos"
FIELDS = ["close_raw_i0", "adj_close_i0", "mcap_oos", "ttm_revenue", "ttm_ocf",
          "ttm_net_income", "equity", "assets", "cash", "total_debt",
          "f_ocf_margin", "f_ni_margin", "f_rev_growth_yoy", "f_rev_cv8",
          "f_shock_rel_drop", "dollar_vol_60d", "panel_period_end", "panel_filed", "currency"]


def fmt(v, key):
    if v is None:
        return "—"
    if isinstance(v, (int, float)):
        if key in ("mcap_oos", "ttm_revenue", "ttm_ocf", "ttm_net_income", "equity",
                   "assets", "cash", "total_debt", "dollar_vol_60d"):
            return f"{v / 1e9:,.2f}B" if abs(v) >= 1e8 else f"{v:,.0f}"
        if key == "close_raw_i0" or key == "adj_close_i0":
            return f"{v:.2f}"
        return f"{v:.4f}"
    return str(v)


def main() -> None:
    evs = sys.argv[1:] or [f"E{i}" for i in range(21, 28)]
    for eid in evs:
        pack = json.loads((PKT / f"{eid}.json").read_text(encoding="utf-8"))
        print(f"\n{'=' * 78}\n## {eid} {pack['name']} [{pack['event_type']}]")
        print(f"   衝擊 {pack['shock_start']} → 新聞結束 {pack['news_shock_end']}"
              f" · 折現率 {pack['discount_rate']:.2f}%(DGS10 {pack['discount_rate_base']:.2f}%+500bp)")
        print(f"   籃子: {pack['basket_definition']}")
        for c in pack["companies"]:
            if not c.get("picked"):
                continue
            pf = c.get("prefilings", {})
            fs = " ".join(f"{k}={v['form']}/{v['filingDate']}/{v['accession']}"
                          for k, v in pf.items() if isinstance(v, dict))
            print(f"\n  -- {c['ticker']} {c['name']} (CIK {c['entity_id']}, SIC {c['sic']} "
                  f"{c['sic_description']}, 點名信心 {c['named_confidence']})")
            print("     " + " · ".join(f"{k}={fmt(c.get(k), k)}" for k in FIELDS))
            print(f"     申報: {fs}")
            if c.get("mcap_note"):
                print(f"     市值註: {c['mcap_note'][:150]}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
