"""KARST-152:人手表 33 條鏈位的逐層明細(層內殘餘相關),供人眼核。"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import analyze as A

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
CHAIN_CSV = A.CHAIN_CSV


def main() -> int:
    themes: dict[str, str] = {}
    for ln in CHAIN_CSV.read_text(encoding="utf-8-sig").splitlines()[1:]:
        if not ln.strip():
            continue
        p = ln.split(",", 5)
        if len(p) < 5 or p[3].strip():
            continue
        themes.setdefault(p[1].strip(), p[0].strip())

    meta = A.load_meta()
    px = A.load_prices()
    rets = A.window_returns(px, "2022-01-01", "2026-08-31")
    stocks = [t for t in themes if t in px.columns]
    resid = A.residualise(rets, meta, stocks)
    C = resid.corr(min_periods=150)

    rows = []
    for th in sorted(set(themes.values())):
        mem = [t for t, v in themes.items() if v == th and t in C.columns]
        if len(mem) < 2:
            rows.append({"theme": th, "n_usable": len(mem), "within_corr": None,
                         "members": mem,
                         "subindustries": sorted({(meta.get(m) or {}).get("industry") or "?"
                                                  for m in mem})})
            continue
        sub = C.loc[mem, mem].to_numpy()
        iu = np.triu_indices(len(mem), 1)
        v = float(np.nanmean(sub[iu]))
        rows.append({"theme": th, "n_usable": len(mem),
                     "within_corr": round(v, 4) if np.isfinite(v) else None,
                     "members": mem,
                     "subindustries": sorted({(meta.get(m) or {}).get("industry") or "?"
                                              for m in mem})})
    rows.sort(key=lambda r: -(r["within_corr"] if r["within_corr"] is not None else -9))
    (OUT / "manual_layers_detail.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in rows:
        print(f"{r['theme']:22s} n={r['n_usable']:2d} corr={r['within_corr']} "
              f"{' '.join(r['members'])} | {len(r['subindustries'])} 子行業")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
