"""KARST-157 事後診斷(**不參與判詞**,CRITERIA.md 第 11 節的判準已經跑完)。

三件事:
 1. 人手鏈位表逐條鏈位的層內殘餘相關(2023 / 2025 兩個切片)。
 2. 機器分層與語意分層之中,跨越 ≥2 個子行業而層內殘餘相關最高的十五層(人眼核)。
 3. 配對數的結構性上限:人手表要多少成員才生得出 100 對 G1。

Run: PYTHONUTF8=1 python posthoc.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd

import analyze as A

OUT = A.OUT


def within_layer_corr(C: np.ndarray, idx: list[int]) -> float:
    if len(idx) < 2:
        return float("nan")
    sub = C[np.ix_(idx, idx)]
    iu = np.triu_indices(len(idx), 1)
    v = sub[iu]
    v = v[~np.isnan(v)]
    return float(v.mean()) if len(v) else float("nan")


def main() -> int:
    meta = A.load_meta()
    px = A.load_prices()
    res: dict = {"manual_layer_detail": {}, "exemplar_layers": {}, "pair_ceiling": {}}

    # ---- 1. 人手表逐條鏈位 ----
    for sl in ["2023-06-30", "2025-06-30"]:
        end = (pd.Timestamp(sl) + pd.Timedelta(days=365)).strftime("%Y-%m-%d")
        labels_map = A.manual_labels_at(sl)
        rets = A.window_returns(px, sl, end)
        stocks = [t for t in labels_map if t in px.columns]
        resid = A.residualise(rets, meta, stocks)
        keep = [t for t in stocks if t in resid.columns and (meta.get(t) or {}).get("industry")]
        C = resid[keep].corr(min_periods=150).to_numpy()
        detail = {}
        for th in sorted(set(labels_map[t] for t in keep)):
            idx = [i for i, t in enumerate(keep) if labels_map[t] == th]
            subs = sorted({(meta[keep[i]] or {}).get("industry") or "" for i in idx})
            detail[th] = {"members": [keep[i] for i in idx], "n": len(idx),
                          "n_subindustries": len(subs),
                          "within_layer_resid_corr": within_layer_corr(C, idx)}
        res["manual_layer_detail"][sl] = dict(
            sorted(detail.items(),
                   key=lambda kv: (-(kv[1]["within_layer_resid_corr"]
                                     if kv[1]["within_layer_resid_corr"] == kv[1]["within_layer_resid_corr"]
                                     else -9))))

    # ---- 2. 機器/語意分層的典型層 ----
    layers = list(csv.DictReader(open(OUT / "layers_v2.csv", encoding="utf-8-sig")))
    for sl in A.SLICES:
        end = (pd.Timestamp(sl) + pd.Timedelta(days=365)).strftime("%Y-%m-%d")
        rets = A.window_returns(px, sl, end)
        tickers, _tf, _raw = A.build_corpus(sl, meta)
        resid = A.residualise(rets, meta, tickers)
        keep = [t for t in tickers if t in resid.columns and (meta.get(t) or {}).get("industry")]
        pos = {t: i for i, t in enumerate(keep)}
        C = resid[keep].corr(min_periods=150).to_numpy()
        rows = []
        for r in layers:
            if r["slice"] != sl or r["arm"] not in ("machine_v2", "semantic"):
                continue
            mem = [m for m in r["members"].split() if m in pos]
            if len(mem) < 3 or int(r["n_subindustries"]) < 2:
                continue
            rows.append({"arm": r["arm"], "slice": sl, "size": len(mem),
                         "n_subindustries": int(r["n_subindustries"]),
                         "members": mem, "top_terms": r["top_terms"],
                         "within_layer_resid_corr": within_layer_corr(C, [pos[m] for m in mem])})
        rows = [x for x in rows if x["within_layer_resid_corr"] == x["within_layer_resid_corr"]]
        rows.sort(key=lambda x: -x["within_layer_resid_corr"])
        res["exemplar_layers"][sl] = rows[:15]

    # ---- 3. 配對數的結構性上限 ----
    for sl in ["2023-06-30", "2025-06-30"]:
        r = json.loads((OUT / "results_v2.json").read_text(encoding="utf-8"))["manual"][sl]
        g1 = r["pair_stats"]["G1_same_layer_diff_subind"]["n_pairs"]
        n = r["n_labelled"]
        # 同形狀放大:層數與成員同比例增加時,層內配對數約與成員數成正比(層大小不變)
        need = n * (100.0 / g1) if g1 else None
        res["pair_ceiling"][sl] = {
            "n_members": n, "n_layers": r["n_layers"], "median_layer_size": r["median_layer"],
            "G1_pairs": g1, "G2_pairs": r["pair_stats"]["G2_same_subind_diff_layer"]["n_pairs"],
            "members_needed_for_100_G1_pairs_same_shape": round(need) if need else None,
        }

    (OUT / "posthoc_v2.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    print(json.dumps(res["pair_ceiling"], ensure_ascii=False, indent=1))
    for sl, d in res["manual_layer_detail"].items():
        print(f"-- manual {sl} top --")
        for th, v in list(d.items())[:12]:
            print(f"   {th:20s} n={v['n']} subind={v['n_subindustries']} "
                  f"corr={v['within_layer_resid_corr']:.3f} {' '.join(v['members'])}")
    for sl, rows in res["exemplar_layers"].items():
        print(f"-- exemplar {sl} top 5 --")
        for x in rows[:5]:
            print(f"   {x['arm']:11s} n={x['size']} sub={x['n_subindustries']} "
                  f"corr={x['within_layer_resid_corr']:.3f} | {' '.join(x['members'][:10])} "
                  f"| {x['top_terms'][:70]}")
    print("written -> out/posthoc_v2.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
