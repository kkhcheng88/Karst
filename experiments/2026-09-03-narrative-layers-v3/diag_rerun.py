# -*- coding: utf-8 -*-
"""KARST-175 診斷(**不是預先登記的數,不入判詞**)。

問題:2023 切片的置信區間由含 0 變成不含 0,幾多來自「補回缺席公司」、
幾多來自「換了價格來源」?判準第 8.8 節已寫明本票分不開這兩者;本診斷只做得到
一半的分離——把新價格限制在 v3 當年那 204 家身上再量一次:

  v3 原數(舊價格 × 204 家)  vs  本診斷(新價格 × 同一批 204 家)  = 價格來源的效果
  本診斷(新價格 × 204 家)   vs  本票主數(新價格 × 265 家)      = 補缺的效果

跑法: set PYTHONUTF8=1 && python diag_rerun.py
"""
from __future__ import annotations

import csv
import io
import json

import numpy as np
import pandas as pd

import analyze_rerun as A

T = "2023-06-30"


def v3_keep_set() -> list[str]:
    out = []
    with io.open(A.OUT / "layers_v3.csv", "r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["arm"] == "manual_v22_full" and r["slice"] == T:
                out.extend(r["members"].split())
    return sorted(set(out))


def main() -> int:
    meta, filled = A.load_meta()
    rows = A.read_chain()
    tickers = sorted({r["ticker"] for r in rows})
    series, seg_man, _ = A.load_price_library(tickers)
    etf = pd.read_parquet(A.ETF_PANEL)
    etf.index = pd.to_datetime(etf.index)
    rs = A.roster_sizes(rows)
    big = {t for t, n in rs.items() if n >= A.MIN_ROSTER}

    end = (pd.Timestamp(T) + pd.Timedelta(days=365)).strftime("%Y-%m-%d")
    lmap = A.labels_at(rows, T, big)
    seg = A.pick_segments(seg_man, sorted(lmap.keys()), T, end)
    px = A.build_panel(series, seg, etf)
    rets = A.window_returns(px, T, end)
    etf_cols = [e for e in A.ETFS if e != "SPY" and e in rets.columns]
    sector_neff = A.n_eff(rets[etf_cols].dropna())

    old = v3_keep_set()
    stocks = [t for t in lmap if t in px.columns and t in old]
    resid = A.residualise(rets, meta, stocks)
    keep = [t for t in stocks if t in resid.columns and (meta.get(t) or {}).get("industry")]
    C = resid[keep].corr(min_periods=150).to_numpy()
    subn = np.array([(meta[t] or {}).get("industry") or "" for t in keep])
    labn = np.array([lmap[t] for t in keep])
    res = A.evaluate("diag_v3set_newprice", keep, A.codes(labn), C, A.codes(subn),
                     subn, rets, sector_neff)
    res["n_v3_keep"] = len(old)
    res["n_matched"] = len(keep)
    res["v3_members_lost"] = sorted(set(old) - set(keep))
    # ---- 第二問:補回來那批公司佔了 G1 幾多? ----
    stocks2 = [t for t in lmap if t in px.columns]
    resid2 = A.residualise(rets, meta, stocks2)
    keep2 = [t for t in stocks2 if t in resid2.columns and (meta.get(t) or {}).get("industry")]
    C2 = resid2[keep2].corr(min_periods=150).to_numpy()
    sub2 = A.codes(np.array([(meta[t] or {}).get("industry") or "" for t in keep2]))
    lab2 = A.codes(np.array([lmap[t] for t in keep2]))
    isnew = np.array([t not in old for t in keep2])
    n = len(keep2)
    iu = np.triu_indices(n, 1)
    c = C2[iu]
    same_l = lab2[iu[0]] == lab2[iu[1]]
    same_s = (sub2[iu[0]] == sub2[iu[1]]) & (sub2[iu[0]] >= 0)
    ok = ~np.isnan(c)
    nnew = isnew[iu[0]].astype(int) + isnew[iu[1]].astype(int)
    decomp = {}
    for gname, gm in (("G1", same_l & ~same_s), ("G2", ~same_l & same_s)):
        for k, kn in ((0, "both_old"), (1, "one_new"), (2, "both_new")):
            m = gm & ok & (nnew == k)
            decomp[f"{gname}_{kn}"] = {"n_pairs": int(m.sum()),
                                       "mean": float(np.nanmean(c[m])) if m.sum() else None}
    res["decomposition_by_newness"] = decomp
    res["n_new_members"] = int(isnew.sum())
    print("\nG1 / G2 按『成員是否本票補回來』拆:")
    for k, v in decomp.items():
        mv = f"{v['mean']:.4f}" if v["mean"] is not None else "—"
        print(f"  {k:14s} n={v['n_pairs']:5d}  mean={mv}")

    (A.OUT / "diag_v3set_newprice.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    ps = res["pair_stats"]
    print(f"v3 那批 {len(old)} 家,新價格對得上 {len(keep)} 家")
    print(f"G1={res['G1']:.4f} G2={res['G2']:.4f} diff={res['diff']:+.4f} "
          f"mult={res['resolution_multiple']:.3f}")
    print(f"pairs G1/G2 = {ps['G1_same_layer_diff_subind']['n_pairs']} / "
          f"{ps['G2_same_subind_diff_layer']['n_pairs']}")
    print(f"CI = {[round(x, 4) for x in res['bootstrap']['diff_ci95']]}")
    print(f"n_eff = {res['n_eff_layers']:.3f} (板塊 {sector_neff:.3f})  "
          f"layers={res['n_layers']} median_layer={res['median_layer']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
