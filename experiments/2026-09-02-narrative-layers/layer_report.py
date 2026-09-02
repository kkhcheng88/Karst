"""KARST-152 步驟 3:把每層成員與前十關鍵詞攤成人眼可核的表,並挑最典型的幾層。

「最典型」= 該層內部平均殘餘相關最高(層內至少 3 隻),因為鏈層的定義核心正是
「同層對同一消息反應相似」(CONTEXT.md)。
Run: PYTHONUTF8=1 python layer_report.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd

import analyze as A

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"


def main() -> int:
    layers = json.loads((OUT / "layers.json").read_text(encoding="utf-8"))
    meta = A.load_meta()
    px = A.load_prices()

    rows = []
    for sl in A.SLICES:
        end = (pd.Timestamp(sl) + pd.Timedelta(days=365)).strftime("%Y-%m-%d")
        rets = A.window_returns(px, sl, end)
        tk, _ = A.build_corpus(sl, meta)
        resid = A.residualise(rets, meta, tk)
        C = resid.corr(min_periods=150)
        for rec in layers:
            if rec["slice"] != sl:
                continue
            mem = [m for m in rec["members"] if m in C.columns]
            if len(mem) >= 2:
                sub = C.loc[mem, mem].to_numpy()
                iu = np.triu_indices(len(mem), 1)
                vals = sub[iu]
                within = float(np.nanmean(vals)) if np.isfinite(vals).any() else float("nan")
            else:
                within = float("nan")
            inds = [(meta.get(m) or {}).get("industry") or "?" for m in rec["members"]]
            n_ind = len(set(inds))
            rows.append({
                "slice": sl, "k": rec["k"], "layer": rec["layer"], "size": rec["size"],
                "within_layer_resid_corr": round(within, 4) if within == within else "",
                "n_subindustries": n_ind,
                "members": " ".join(rec["members"]),
                "top_terms": " | ".join(rec["top_terms"]),
            })
        print(f"{sl} done", flush=True)

    with (OUT / "layers_table.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # 最典型的層:k=80、層內 3-25 隻、跨至少兩個子行業、層內殘餘相關最高
    picks = [r for r in rows if r["k"] == 80 and 3 <= r["size"] <= 25
             and r["n_subindustries"] >= 2 and r["within_layer_resid_corr"] != ""]
    picks.sort(key=lambda r: -float(r["within_layer_resid_corr"]))
    (OUT / "exemplar_layers.json").write_text(
        json.dumps(picks[:15], ensure_ascii=False, indent=1), encoding="utf-8")
    for r in picks[:12]:
        print(f"{r['slice']} L{r['layer']} n={r['size']} corr={r['within_layer_resid_corr']} "
              f"| {r['members'][:90]} | {r['top_terms'][:110]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
