# -*- coding: utf-8 -*-
"""KARST-202 第二步:按主成因分組,重出一/三/六/十二個月結果分佈。

不重建事件、不重新發明統計:直接讀 out/events_gatefix.csv 與 out/events_cause.csv,
分組統計整格沿用 gate_cost.py 的 cell()(它本身又沿用 make_tables.py 的簇 bootstrap
boot_ci、MIN_CELL=30 只報樣本數、剔前 1%/5%、觸及 −33%/−50%/−80%)。

口徑(與 KARST-194 加不加閘對照同一條底線):
  資料底線 = 剔「拆股基準可疑」
  主口徑 = 資料底線 + 流動性閘(近 60 日中位成交金額 >= 300 萬美元)
  進場格用 A(觸發日即買),與基準率表主表一致
  年份段:全期 2010-2026 / 建表 2010-2021 / 驗證 2022-2026

輸出:
  out/cause_groups_cause.csv          按主成因 × 期 × 年份段
  out/cause_by_gatepool_cause.csv     主成因 × 過不過三閘(12 個月)
  out/cause_industry_cross_cause.csv  行業共跌 × 主成因 交叉表(宗數 + 12 個月結果)
  out/cause_secondary_cause.csv       副成因出現次數(不分組統計,只列出現率)
  out/cause_summary_cause.json        一頁摘要
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gate_cost as GC  # noqa: E402  沿用 cell()/assign_group(),不另寫統計
import make_tables as MT  # noqa: E402

OUT = HERE / "out"
HORIZONS = MT.HORIZONS
MIN_CELL = MT.MIN_CELL
LIQ_MIN = MT.LIQ_MIN

CAUSE_ORDER = [
    "破產(8-K 1.03)",
    "重列或不可依賴(8-K 4.02)",
    "退市或不合規通知(8-K 3.01)",
    "稀釋增發(S-1/S-3/424B)",
    "業績(8-K 2.02)",
    "收購或處置(8-K 2.01)",
    "高管離任(8-K 5.02)",
    "指引或其他重大訊息(8-K 7.01/8.01)",
    "重大合約或舉債(8-K 1.01/2.03)",
    "內部人擬售(Form 144)",
    "分拆孤兒(Form 10)",
    "定期報告(10-K/10-Q)",
    "其他申報",
    "無申報",
]


def load() -> pd.DataFrame:
    ev = GC.load_events()
    cause = pd.read_csv(OUT / "events_cause.csv", encoding="utf-8-sig",
                        parse_dates=["trigger_date"], dtype={"entity_id": "string"})
    cause["entity_id"] = cause["entity_id"].str.zfill(10)
    keep = ["entity_id", "trigger_date", "主成因", "副成因", "主成因申報日",
            "主成因表格", "窗內申報份數", "窗內實質申報份數"]
    ev = ev.merge(cause[keep], on=["entity_id", "trigger_date"], how="left",
                  validate="one_to_one")
    assert ev["主成因"].notna().all(), "有觸發貼不到成因標籤"
    ev["組_可判"] = GC.assign_group(ev, "可判")
    return ev


def build_groups(ev: pd.DataFrame) -> pd.DataFrame:
    base = ev[ev["資料底線"] & ev["過流動性閘"]]
    rows = []
    for yr_label, ymask in (("全期 2010-2026", pd.Series(True, index=base.index)),
                            ("全期剔 2020", base["trigger_year"] != 2020),
                            ("建表年份 2010-2021", base["trigger_year"] <= 2021),
                            ("建表年份剔 2020", (base["trigger_year"] <= 2021) &
                                                (base["trigger_year"] != 2020)),
                            ("驗證年份 2022-2026", base["trigger_year"] >= 2022)):
        seg = base[ymask]
        for cname in ["0 全部觸發(不分成因)"] + CAUSE_ORDER:
            sub = seg if cname.startswith("0 ") else seg[seg["主成因"] == cname]
            if len(sub) == 0:
                continue
            for h in HORIZONS:
                rec = {"年份段": yr_label, "主成因": cname, "期": h,
                       "全期觸發宗數": int(len(sub))}
                rec.update(GC.cell(sub, h, do_boot=True))
                rows.append(rec)
    out = pd.DataFrame(rows)
    out["期"] = pd.Categorical(out["期"], categories=HORIZONS, ordered=True)
    return out


def build_by_gatepool(ev: pd.DataFrame) -> pd.DataFrame:
    """主成因 × 過不過三閘(12 個月,主口徑)——答「哪些成因可作①候選來源」。"""
    base = ev[ev["資料底線"] & ev["過流動性閘"] & ev["負債閘可判"]]
    rows = []
    for pool_label, mask in (("過三閘(現行①池)", base["組_可判"] == "1 過三閘(現行①池)"),
                             ("不過三閘", base["組_可判"] != "1 過三閘(現行①池)")):
        seg = base[mask]
        for cname in ["0 全部觸發(不分成因)"] + CAUSE_ORDER:
            sub = seg if cname.startswith("0 ") else seg[seg["主成因"] == cname]
            if len(sub) == 0:
                continue
            for h in ("3m", "12m"):
                rec = {"池": pool_label, "主成因": cname, "期": h}
                rec.update(GC.cell(sub, h, do_boot=(h == "12m")))
                rows.append(rec)
    return pd.DataFrame(rows)


def build_industry_cross(ev: pd.DataFrame) -> pd.DataFrame:
    """行業共跌 × 個股成因交叉表(主口徑,3 與 12 個月)。"""
    base0 = ev[ev["資料底線"] & ev["過流動性閘"]]
    rows = []
    for yr_label, base in (("全期 2010-2026", base0),
                           ("全期剔 2020", base0[base0["trigger_year"] != 2020])):
        for ik in sorted(base["industry_kill"].dropna().unique()):
            seg = base[base["industry_kill"] == ik]
            for cname in ["0 全部觸發(不分成因)"] + CAUSE_ORDER:
                sub = seg if cname.startswith("0 ") else seg[seg["主成因"] == cname]
                if len(sub) == 0:
                    continue
                for h in ("3m", "12m"):
                    rec = {"年份段": yr_label, "行業共跌": ik, "主成因": cname, "期": h}
                    rec.update(GC.cell(sub, h, do_boot=(h == "12m")))
                    rows.append(rec)
    return pd.DataFrame(rows)


def build_secondary(ev: pd.DataFrame) -> pd.DataFrame:
    base = ev[ev["資料底線"] & ev["過流動性閘"]]
    rows = []
    for cname in CAUSE_ORDER:
        n = int(base["副成因"].fillna("").str.split("|").apply(lambda xs: cname in xs).sum())
        # 「窗內任何位置出現過」= 主成因是它,或副成因含它
        n_any = int((base["主成因"] == cname).sum()) + n
        rows.append({"成因": cname, "作副成因出現宗數": n,
                     "作主成因宗數": int((base["主成因"] == cname).sum()),
                     "窗內出現過(主或副)宗數": n_any,
                     "窗內出現率": n_any / len(base)})
    return pd.DataFrame(rows)


def main() -> None:
    ev = load()
    base = ev[ev["資料底線"] & ev["過流動性閘"]]
    info = {
        "事件表列數": int(len(ev)),
        "資料底線(剔拆股基準可疑)後": int(ev["資料底線"].sum()),
        "主口徑(再加流動性閘)後": int(len(base)),
        "主口徑公司數": int(base["entity_id"].nunique()),
        "全體觸發各成因宗數": {k: int(v) for k, v in ev["主成因"].value_counts().items()},
        "主口徑各成因宗數": {k: int(v) for k, v in base["主成因"].value_counts().items()},
        "主口徑各成因公司數": {k: int(v) for k, v in
                              base.groupby("主成因")["entity_id"].nunique().items()},
        "全體無申報比例": float((ev["主成因"] == "無申報").mean()),
        "主口徑無申報比例": float((base["主成因"] == "無申報").mean()),
        "主口徑窗內實質申報為零比例": float((base["窗內實質申報份數"] == 0).mean()),
        "指數剔除": "未判——本倉無免費的歷史指數成分變動名單,此成因不曾指派給任何一宗",
    }

    groups = build_groups(ev)
    groups.to_csv(OUT / "cause_groups_cause.csv", index=False, encoding="utf-8-sig")

    pool = build_by_gatepool(ev)
    pool.to_csv(OUT / "cause_by_gatepool_cause.csv", index=False, encoding="utf-8-sig")

    cross = build_industry_cross(ev)
    cross.to_csv(OUT / "cause_industry_cross_cause.csv", index=False, encoding="utf-8-sig")

    sec = build_secondary(ev)
    sec.to_csv(OUT / "cause_secondary_cause.csv", index=False, encoding="utf-8-sig")

    with open(OUT / "cause_summary_cause.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2, default=str)

    cols = ["主成因", "樣本N", "公司數", "簇數", "勝率", "勝率下限", "勝率上限",
            "中位超額", "平均超額", "平均超額下限", "平均超額上限",
            "剔走前1%後平均", "平均盈虧比", "中位盈虧比",
            "觸及負33比例", "觸及負80比例", "中位期內最大跌幅", "可信度"]
    for yr in ("全期 2010-2026", "建表年份 2010-2021", "驗證年份 2022-2026"):
        for h in ("3m", "12m"):
            t = groups[(groups["年份段"] == yr) & (groups["期"] == h)]
            print("\n===== %s,%s =====" % (yr, h))
            print(t[cols].to_string(index=False))
    print(json.dumps(info, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
