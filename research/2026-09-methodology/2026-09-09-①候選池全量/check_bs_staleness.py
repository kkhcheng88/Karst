"""KARST-188:六十家的資產負債表新鮮度普查。

RMBS 的用例揭出一個未查過的前提:SEC companyfacts 未必已經收錄公司最近一次申報。
RMBS 的快取是 2026-09-09 當日下載,但最新一張資產負債表仍停在 2026-03-31——
而事實隊由 10-Q 一手文件讀到 2026-06-30 的數。
若這件事普遍,整批的淨負債、現金、股數都可能落後一季。
輸出:bs_staleness.csv
"""
import os, sys
import pandas as pd

sys.path.insert(0, r"C:\projects\Karst\strategy\tools")
import implied_expectations as IE  # noqa

D = r"C:\projects\Karst\research\2026-09-methodology\2026-09-09-①候選池全量"
PRICE_DATE = pd.Timestamp("2026-09-08")


def main():
    d = pd.read_csv(os.path.join(D, "screen60_full.csv"))
    rows = []
    for tk, asof in zip(d["ticker"], d["asof"]):
        try:
            facts = IE.load_facts(IE.cik_for(tk))
        except Exception:
            rows.append((tk, asof, None, None)); continue
        us = facts.get("facts", {}).get("us-gaap", {})
        mx, mf = None, None
        for tag in ("Assets", "StockholdersEquity", "LiabilitiesAndStockholdersEquity"):
            for _, rr in us.get(tag, {}).get("units", {}).items():
                for r in rr:
                    if "end" in r and "start" not in r:
                        if mx is None or r["end"] > mx:
                            mx = r["end"]
                        if r.get("filed") and (mf is None or r["filed"] > mf):
                            mf = r["filed"]
        rows.append((tk, asof, mx, mf))
    f = pd.DataFrame(rows, columns=["ticker", "used_asof", "latest_bs", "latest_filed"])
    f["lag_days"] = (PRICE_DATE - pd.to_datetime(f["latest_bs"])).dt.days
    f.to_csv(os.path.join(D, "bs_staleness.csv"), index=False, encoding="utf-8")
    same = int((f["used_asof"] == f["latest_bs"]).sum())
    print("用的結算日 = companyfacts 內最新資產負債表日:%d / %d" % (same, len(f)))
    stale = f[f["lag_days"] > 100].sort_values("lag_days", ascending=False)
    print("")
    print("最新資產負債表距價格日超過 100 日(即很可能已經漏了一季)的家數:%d" % len(stale))
    print(stale.to_string(index=False))
    print("")
    print("落後日數分佈:")
    print(f["lag_days"].describe().round(1).to_string())


if __name__ == "__main__":
    main()
