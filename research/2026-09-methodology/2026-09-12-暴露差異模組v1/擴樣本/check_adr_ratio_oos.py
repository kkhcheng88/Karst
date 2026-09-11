# -*- coding: utf-8 -*-
"""KARST-220 擴樣本:核 ADS 比率。

20-F 自己列出「Market price per ordinary share (year end)」,價格庫則有 ADS 收市價。
同一 ADS 比率之下,兩個年結日的**比率**應該對得上(不需匯率):
    ADS 價(年結) / ADS 價(另一年結)  ≈  普通股價(年結) / 普通股價(另一年結)
對不上即比率寫錯,該家的每股換算不得用。

另外核衝擊起日前一交易日的 ADS 價與 20-F 的每股面值/淨值換算是否合理。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\projects\Karst")
B199 = ROOT / "research" / "2026-09-methodology" / "2026-09-10-①行業殺錯事件籃子"
sys.path.insert(0, str(B199))
from basket_core import build_wide, load_prices, load_spy, resolve_tickers  # noqa: E402

# 20-F 自列的年結普通股價(便士,除 HSBC 為美元)
DISCLOSED = {
    "LYG": {"2015-12-31": 73.1, "2014-12-31": 75.8, "2013-12-31": 78.9, "2012-12-31": 47.9},
    "HSBC": {"2015-12-31": 5.64, "2014-12-31": 6.16, "2013-12-31": 6.55},
    "BCS": {"2015-12-31": 2.25, "2014-12-31": 2.32},
}
RATIO = {"LYG": 4, "HSBC": 5, "BCS": 4}


def main() -> None:
    spy_df = load_spy()
    px = load_prices()
    cal, wide, _ = build_wide(px, spy_df)
    cal = pd.DatetimeIndex(cal)
    # 要用**未還原**收市價比對(還原價已扣歷年派息,不能同申報的每股價比)
    raw = px.pivot_table(index="date", columns="entity_id", values="close",
                         aggfunc="last").reindex(cal)
    for tk, pts in DISCLOSED.items():
        res = resolve_tickers([tk], pd.Timestamp("2016-06-01"))
        e = res.iloc[0]["entity_id"] if res.iloc[0]["resolve_status"] == "已解析" else None
        print(f"\n## {tk} ratio={RATIO[tk]} entity={e}")
        s = raw[e] if (e and e in raw.columns) else None
        rows = []
        for d, v in sorted(pts.items()):
            if s is None:
                continue
            i = int(cal.searchsorted(pd.Timestamp(d), side="right") - 1)
            adr = float(s.iloc[i]) if i >= 0 else np.nan
            rows.append((d, v, adr, adr / v if v else np.nan))
        for i in range(1, len(rows)):
            a, b = rows[i - 1], rows[i]
            print(f"   {b[0]}: ADS {b[2]:.3f} / 普通股 {b[1]} = {b[3]:.4f}"
                  f"   比對 {a[0]}: {a[3]:.4f}   年際比率 ADS {b[2]/a[2]:.4f} vs 普通股 {b[1]/a[1]:.4f}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
