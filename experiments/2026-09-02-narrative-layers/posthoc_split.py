"""KARST-152 事後診斷(不參與 CRITERIA.md 第 8 節的判準)。

主判數的平均值被一個「大雜燴層」拖死,但眼看層表,細層明顯是真故事。
本檔量的是:把層按大小分開之後,層內殘餘相關長什麼樣——即「訊號到底住在哪裡」。
Run: PYTHONUTF8=1 python posthoc_split.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import analyze as A

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"


def main() -> int:
    layers = json.loads((OUT / "layers.json").read_text(encoding="utf-8"))
    res = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    meta = A.load_meta()
    px = A.load_prices()

    report = {}
    for sl in A.SLICES:
        end = (pd.Timestamp(sl) + pd.Timedelta(days=365)).strftime("%Y-%m-%d")
        rets = A.window_returns(px, sl, end)
        tk, _ = A.build_corpus(sl, meta)
        resid = A.residualise(rets, meta, tk)
        C = resid.corr(min_periods=150)
        report[sl] = {}
        for k in A.KS:
            g2 = res["slices"][sl]["k"][str(k)]["pair_stats"]["G2_same_subind_diff_layer"]["mean"]
            small, big = [], []
            n_small_stocks = 0
            beats = 0
            for rec in layers:
                if rec["slice"] != sl or rec["k"] != k:
                    continue
                mem = [m for m in rec["members"] if m in C.columns]
                if len(mem) < 3:
                    continue
                sub = C.loc[mem, mem].to_numpy()
                iu = np.triu_indices(len(mem), 1)
                v = float(np.nanmean(sub[iu]))
                if not np.isfinite(v):
                    continue
                if rec["size"] <= 25:
                    small.append(v)
                    n_small_stocks += rec["size"]
                    if v > g2:
                        beats += 1
                else:
                    big.append(v)
            report[sl][str(k)] = {
                "G2_same_subind_baseline": round(g2, 4),
                "small_layers_3to25": {
                    "n_layers": len(small),
                    "n_stocks": n_small_stocks,
                    "mean_within_corr": round(float(np.mean(small)), 4) if small else None,
                    "median_within_corr": round(float(np.median(small)), 4) if small else None,
                    "n_beating_G2": beats,
                },
                "big_layers_over25": {
                    "n_layers": len(big),
                    "mean_within_corr": round(float(np.mean(big)), 4) if big else None,
                },
            }
        print(sl, "done", flush=True)

    (OUT / "posthoc_layer_size_split.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
