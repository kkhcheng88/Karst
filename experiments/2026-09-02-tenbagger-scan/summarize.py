# -*- coding: utf-8 -*-
"""KARST-160:名單的匯總統計(回撤、今日位置、鏈位分佈、宇宙分段),供報告引用。"""
import json
import os

import numpy as np
import pandas as pd

ROOT = r"C:\projects\Karst"
BASE = os.path.join(ROOT, "experiments", "2026-09-02-tenbagger-scan")
OUT = os.path.join(BASE, "out")
P_NEW = os.path.join(ROOT, "experiments", "2026-09-02-narrative-layers-v2", "data", "new_close.parquet")
P_PANEL = os.path.join(ROOT, "experiments", "2026-09-02-panel-scale-fix", "out", "panel_monthly_v2.parquet")


def main():
    nm = pd.read_csv(os.path.join(OUT, "tenbagger_names.csv"), encoding="utf-8-sig")
    new = set(pd.read_parquet(P_NEW).columns)
    pt = set(pd.read_parquet(P_PANEL, columns=["ticker"]).ticker.unique())
    nm["宇宙分段"] = np.where(nm.ticker.isin(new), "新增154", "既有574")
    nm["有帳目面板"] = nm.ticker.isin(pt)
    nm["t0_year"] = pd.to_datetime(nm.t0).dt.year
    nm["峰頂年"] = pd.to_datetime(nm.peak_date).dt.year
    nm.to_csv(os.path.join(OUT, "tenbagger_names.csv"), index=False, encoding="utf-8-sig")

    res = {}
    for h in ["3y", "5y"]:
        d = nm[nm.horizon == h]
        res[h] = {
            "家數": int(len(d)),
            "倍數中位": round(float(d.multiple.median()), 2),
            "倍數上四分位": round(float(d.multiple.quantile(0.75)), 2),
            "峰後最大跌幅_中位": round(float(d.maxdd_after_peak.median()), 4),
            "峰後跌逾五成的比例": round(float((d.maxdd_after_peak <= -0.5).mean()), 4),
            "峰後跌逾八成的比例": round(float((d.maxdd_after_peak <= -0.8).mean()), 4),
            "今日仍在峰頂七成以上的比例": round(float((d.today_vs_peak >= -0.3).mean()), 4),
            "今日相對峰頂_中位": round(float(d.today_vs_peak.median()), 4),
            "在鏈表某鏈位的比例": round(float(d.chain_theme.notna().mean()), 4),
            "有帳目面板的家數": int(d["有帳目面板"].sum()),
            "新增154段家數": int((d["宇宙分段"] == "新增154").sum()),
            "峰頂年份分佈": d["峰頂年"].value_counts().sort_index().to_dict(),
        }
    d5 = nm[nm.horizon == "5y"]
    res["5y_鏈位分佈"] = d5.chain_theme.fillna("(不在鏈表)").value_counts().head(15).to_dict()
    json.dump(res, open(os.path.join(OUT, "names_summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
