# -*- coding: utf-8 -*-
"""KARST-225 票 A′ 第二步:宇宙成交額門檻(60 個交易日日均成交額,**算術平均**)重算。

執行口徑 v1.1:公布前 60 個交易日成交額的算術平均 ≥ 1,000 萬美元;同時輸出中位數欄備查。

做法:逐檔掃描 `data/prices/daily/part_*.parquet`(沿用 pxlib 的逐檔策略,避免一次讀入
2,065 萬列),只對「有 8-K Item 2.02 事件」的公司做 rolling。視窗口徑與 `A/s2_price_metrics.py`
完全一致:取該公司自己日線序列中、反應日**之前**那 60 列(不含反應日),並且要有滿 60 列
(`i >= 60`)才算得出門檻。

輸出 `cache/turnover60.parquet`(accessionNumber、turnover_mean_60d、turnover_median_60d、
n_window)。本檔同時把重算的平均值與 `A/cache/price_metrics.parquet` 的 `dvol_med_60` 對照
(該欄在 v1 實作裡其實就是平均數,見執行紀錄),不一致列數記入 `cache/turnover_check.json`。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
PRICES = ROOT / "data" / "prices" / "daily"
PX_FROM = "2013-06-01"
VOL_WINDOW = 60


def main() -> None:
    ev = pd.read_parquet(CACHE / "events_raw.parquet")
    ev = ev.drop_duplicates(subset=["accessionNumber"]).reset_index(drop=True)
    pm = pd.read_parquet(CACHE / "price_metrics.parquet")[
        ["accessionNumber", "reaction_date", "dvol_med_60", "gate_volume"]]
    df = ev[["accessionNumber", "cik"]].merge(pm, on="accessionNumber", how="left")
    print("事件(去重後):%d" % len(df), flush=True)

    # 需要查價的 (entity, 反應日)
    want: dict[str, set] = {}
    for cik, rd in zip(df["cik"].astype(str), df["reaction_date"].fillna("")):
        if rd:
            want.setdefault(cik, set()).add(np.datetime64(rd, "D"))
    print("需查價公司數:%d" % len(want), flush=True)

    rows: list[pd.DataFrame] = []
    nan_dv_total = 0
    for p in sorted(PRICES.glob("part_*.parquet")):
        d = pd.read_parquet(p, columns=["entity_id", "date", "adj_close", "close",
                                        "volume", "series_role"])
        d = d[d["series_role"] == "primary"]
        d["date"] = pd.to_datetime(d["date"])
        d = d[d["date"] >= PX_FROM]
        d = d.dropna(subset=["adj_close"])
        d["dvol"] = d["close"] * d["volume"]
        nan_dv_total += int(d["dvol"].isna().sum())
        d = d[d["entity_id"].isin(want)].sort_values(["entity_id", "date"], kind="stable")
        if not len(d):
            del d
            continue
        d = d.reset_index(drop=True)
        g = d.groupby("entity_id", sort=False)["dvol"]
        d["m60"] = g.transform(lambda s: s.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).mean())
        d["md60"] = g.transform(lambda s: s.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).median())
        d["n60"] = g.transform(lambda s: s.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).count())
        # 反應日的位置:視窗取 [i-60, i),故值 = 序列在第 i-1 列的 rolling 值
        keep = []
        for eid, gg in d.groupby("entity_id", sort=False):
            dates = gg["date"].values.astype("datetime64[D]")
            m = gg["m60"].to_numpy(dtype="float64")
            md = gg["md60"].to_numpy(dtype="float64")
            n = gg["n60"].to_numpy(dtype="float64")
            for rd in want.get(eid, ()):  # noqa: B007
                i = int(np.searchsorted(dates, rd, side="right")) - 1
                if i < 0 or dates[i] != rd or i < VOL_WINDOW:
                    continue
                keep.append((eid, str(rd), m[i - 1], md[i - 1], n[i - 1]))
        if keep:
            rows.append(pd.DataFrame(keep, columns=["cik", "reaction_date",
                                                    "turnover_mean_60d",
                                                    "turnover_median_60d", "n_window"]))
        print("  %s → 命中 %d 宗" % (p.name, len(keep)), flush=True)
        del d

    t = pd.concat(rows, ignore_index=True).drop_duplicates(
        subset=["cik", "reaction_date"]).reset_index(drop=True)
    out = df[["accessionNumber", "cik", "reaction_date"]].merge(
        t, on=["cik", "reaction_date"], how="left")
    assert len(out) == len(df), "合併後列數變了"
    out.to_parquet(CACHE / "turnover60.parquet", index=False)

    # ---- 與 v1 實作的 dvol_med_60 對照(該欄在 v1 用 nanmean 算出,即平均數)
    a = out.merge(pm[["accessionNumber", "dvol_med_60", "gate_volume"]].rename(
        columns={"dvol_med_60": "v1_dvol_med_60"}), on="accessionNumber", how="left")
    both = a[a["turnover_mean_60d"].notna() & a["v1_dvol_med_60"].notna()]
    diff = (both["turnover_mean_60d"] - both["v1_dvol_med_60"]).abs()
    chk = {
        "n_events": int(len(out)),
        "n_with_window": int(out["turnover_mean_60d"].notna().sum()),
        "n_v1_value": int(a["v1_dvol_med_60"].notna().sum()),
        "n_overlap": int(len(both)),
        "max_abs_diff_vs_v1_dvol_med_60": None if not len(both) else float(diff.max()),
        "n_diff_gt_1e-6": int((diff > 1e-6).sum()),
        "n_v1_value_but_no_window": int((a["v1_dvol_med_60"].notna()
                                         & a["turnover_mean_60d"].isna()).sum()),
        "nan_dvol_rows_in_price_scan": nan_dv_total,
        "n_turnover_mean_ge_10m": int((out["turnover_mean_60d"] >= 10_000_000).sum()),
        "n_turnover_mean_ge_3m": int((out["turnover_mean_60d"] >= 3_000_000).sum()),
        "n_turnover_median_ge_10m": int((out["turnover_median_60d"] >= 10_000_000).sum()),
        "n_turnover_median_lt_mean": int(
            (out["turnover_median_60d"] < out["turnover_mean_60d"]).sum()),
    }
    (CACHE / "turnover_check.json").write_text(
        json.dumps(chk, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(chk, ensure_ascii=False, indent=1))
    print("→", CACHE / "turnover60.parquet")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
