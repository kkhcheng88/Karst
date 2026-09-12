# -*- coding: utf-8 -*-
"""KARST-226 票 A″(v1.2)第十三步:把執行紀錄要用的數一次過數齊 → `cache/stats_summary.json`。

只讀不改;跑完之後人手把數字寫進 `執行紀錄——A3.md`(紀錄正本是人寫的,這支只負責令數字
可重複核對)。與 A2 版之別:全部改讀 v1.2 建池的欄位(前視門檻、稿頭 T0、稿內收入、
適用性 F、併購閘、七個標籤),並加 `release_timing`、指引解析器抽查錯誤率、三項調查。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DOCS = HERE.parent / "A" / "edgar_cache"

SCRIPTS = ["s1_scan_events.py", "s2_price_metrics.py", "s2_turnover.py", "s2b_dateline.py",
           "s3_xbrl.py", "s4_assemble.py", "s4a_thresholds.py", "s4b_merger_scan.py",
           "s4c_merger_text.py", "s5_fetch_text.py", "s5b_merger_body.py",
           "s6_improve_text.py", "s6b_audit.py", "s7_sample_lock.py", "s8_controls.py",
           "s9_packets.py", "s10_export.py", "s11_verify3.py", "s12_stats.py",
           "s13_checks.py", "finlib.py", "pxlib.py", "buckets.py"]


def main() -> None:
    out: dict = {}
    out["scripts"] = {}
    for s in SCRIPTS:
        p = HERE / s
        if p.exists():
            out["scripts"][s] = {
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest()[:16],
                "lines": sum(1 for _ in p.open(encoding="utf-8")),
                "mtime": pd.Timestamp(p.stat().st_mtime, unit="s").strftime(
                    "%Y-%m-%dT%H:%M:%S")}

    out["data_sources"] = {
        "8-K 申報": "data/sec/submissions/CIK*.json(本地 submissions 快取)",
        "XBRL": "data/sec/companyfacts/CIK*.json.gz",
        "日線": "data/prices/daily/part_*.parquet(series_role == primary)",
        "SPY": "data/prices/spy_daily.csv",
        "公司與行業": "data/universe/entities.parquet",
        "申報原文": "A/edgar_cache/(gitignore,不入庫)",
    }

    df = pd.read_parquet(CACHE / "population_base.parquet")
    imp = pd.read_parquet(CACHE / "population_improvement.parquet")
    s4 = json.loads((CACHE / "s4_summary.json").read_text(encoding="utf-8"))
    out["population"] = {
        "掃到的 8-K Item 2.02 事件數": int(len(df)),
        "涉及公司數": int(df["cik"].nunique()),
        "在池窗口內(2015+)": int(df["in_pool_window"].sum()),
        "宇宙內": int(df["in_universe"].sum()),
        "排除": {
            "無日線": int((imp["excl_no_price"] == 1).sum()),
            "成交額不足 1,000 萬": int((imp["excl_volume"] == 1).sum()),
            "上市未滿 12 個月": int((imp["excl_listed_lt_12m"] == 1).sum()),
            "SPAC": int((imp["excl_spac"] == 1).sum()),
            "同日 8-K Item 2.01(v1.2 併購閘)": int(s4["excl_merger_2_01"]),
            "同日 8-K Item 1.01 且正文有併購字眼": int(s4["excl_merger_1_01_text"]),
            "舊閘(只認 Item 1.01,不作廢但記錄)": int(s4["excl_merger_1_01_old_gate"]),
            "併購正文待抓": int(s4["merger_text_pending"]),
            "金融業 SIC 60–64、67": int((imp["excl_financial_sic"] == 1).sum()),
            "適用性 F 不通過": int((imp["excl_applicability"] == 1).sum()),
            "歷史季度未於 T1 前公開": int((imp["excl_hist_not_public"] == 1).sum()),
            "疑更早公開(前一日絕對報酬 > 8%)": int((imp["excl_earlier_release"] == 1).sum()),
            "業績稿盤中發布": int((imp["excl_intraday"] == 1).sum()),
        },
        "全年母體中的排除旗標計數(分母 124,853,部分旗標只對候選檢過)": {
            "稿內找不到訊號季收入": int((imp["excl_no_text"] == 1).sum()),
        },
        "持續經營疑慮": {"有": int((imp["excl_going_concern"] == "有").sum()),
                    "無": int((imp["excl_going_concern"] == "無").sum()),
                    "未核": int((imp["excl_going_concern"] == "未核").sum())},
        "逐年事件數": {str(k): int(v) for k, v in
                   df["year"].astype(str).value_counts().sort_index().items()},
        "逐年宇宙內": {str(k): int(v) for k, v in
                   df[df["in_universe"] == 1]["year"].astype(str)
                   .value_counts().sort_index().items()},
    }

    # 適用性 F 的三類原因(b)與 release_timing 分佈
    ar = imp.loc[imp["excl_applicability"] == 1, "applicability_reason"]
    out["applicability_reason"] = {str(k): int(v) for k, v in ar.value_counts().items()}
    out["release_timing"] = {str(k): int(v) for k, v in
                             imp["release_timing"].value_counts(dropna=False).items()}
    out["t0_source"] = {str(k): int(v) for k, v in
                        imp["t0_source"].value_counts(dropna=False).items()}
    out["xbrl_status"] = {str(k): int(v) for k, v in
                          imp["xbrl_status"].value_counts(dropna=False).items()}
    out["n_consec_q_分位"] = {str(q): float(imp["n_consec_q"].quantile(q))
                          for q in (0.1, 0.5, 0.9)}

    th_all = json.loads((CACHE / "thresholds.json").read_text(encoding="utf-8"))
    out["thresholds"] = th_all
    win = pd.read_parquet(CACHE / "thresholds_window.parquet")
    out["thresholds_window"] = {
        "事件數": int(len(win)),
        "窗口內事件數分位": {str(q): float(win["thr_n"].quantile(q))
                       for q in (0.1, 0.5, 0.9)},
        "用 504 日窗": int((win["thr_win_days"] == 504).sum()),
        "門檻資料不足": int(win["thr_insufficient"].sum()),
    }

    ep = imp[imp["entry_pool"] == 1]
    out["entry_pool"] = {
        "n": int(len(ep)),
        "逐年": {str(k): int(v) for k, v in ep["year"].astype(str)
                 .value_counts().sort_index().items()},
        "逐桶": {str(k): int(v) for k, v in ep["bucket"].value_counts().items()},
        "訊號類型": {str(k): int(v) for k, v in ep["improvement_type"].value_counts().items()},
        "標籤計數(不作閘)": {
            **{c: int(ep[c].sum()) for c in
               ("g0_negative", "both_signals", "above_200dma", "rs6_top20",
                "rel_sic2_ge5", "accel_2q", "guidance_raise_eps_only")
               if c in ep.columns},
            # 這兩個是數值欄(最近四季收入、g0 − 前四季平均),數非空值
            "rev_ttm_有值": int(ep["rev_ttm"].notna().sum()),
            "rev_ttm_中位": float(ep["rev_ttm"].median()),
            "surprise_c2_有值": int(ep["surprise_c2"].notna().sum()),
            "surprise_c2_中位": float(ep["surprise_c2"].median()),
        },
    }
    cand = imp[(imp["in_universe"] == 1) & (imp["in_pool_window"])
               & (imp["pass_thr"] == True)]                                  # noqa: E712
    out["candidates"] = {
        "過前視門檻且同業正": int(len(cand)),
        "其中剔:稿內無訊號季收入": int(cand["excl_no_text"].sum()),
        "其中剔:盤中": int(cand["excl_intraday"].sum()),
        "其中剔:疑更早公開": int(cand["excl_earlier_release"].sum()),
        "其中剔:歷史季度未公開": int(cand["excl_hist_not_public"].sum()),
        "其中剔:適用性 F": int(cand["excl_applicability"].sum()),
        "其中剔:金融 SIC": int(cand["excl_financial_sic"].sum()),
    }

    # 指引解析器
    gp = CACHE / "guidance_parsed.jsonl"
    if gp.exists():
        recs = [json.loads(x) for x in gp.open(encoding="utf-8")]
        g = pd.DataFrame(recs)
        out["guidance_parser"] = {
            "紀錄數": int(len(g)),
            "指標分佈": {str(k): int(v) for k, v in g["metric"].value_counts().items()},
            "期間分佈": {str(k): int(v) for k, v in g["period"].value_counts().items()},
            "上調(raise_flag)": {str(k): int(v) for k, v in
                             g["raise_flag"].value_counts().items()},
            "收入上調紀錄": int(((g["metric"] == "revenue") & (g["raise_flag"] == True)  # noqa: E712
                             ).sum()),
            "抽查錯誤率": "見 guidance_audit.md(全體 52.5%、收入上調子集 55%)",
        }

    # 抓文本
    for name, f in (("觸發稿", "fetch_log_a3.jsonl"), ("併購正文", "merger_fetch_log.jsonl")):
        log = CACHE / f
        if not log.exists():
            continue
        tot, ok, why = 0, set(), {}
        for line in log.open(encoding="utf-8"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            tot += 1
            k = r["status"].split(":")[0]
            if k == "ok":
                ok.add(r["accessionNumber"])
            else:
                why[k] = why.get(k, 0) + 1
        out["fetch_" + name] = {"log 行數": tot, "成功(去重)": len(ok),
                                "失敗狀態": why}
    out["edgar_cache"] = {
        "檔數": sum(1 for _ in DOCS.iterdir()) if DOCS.exists() else 0,
        "EX-99.1 全文檔": sum(1 for _ in DOCS.glob("*__EX991.txt.gz")),
        "8-K 全文檔": sum(1 for _ in DOCS.glob("*__8k.txt.gz")),
    }

    picks = CACHE / "picks.json"
    if picks.exists():
        pj = json.loads(picks.read_text(encoding="utf-8"))
        out["picks"] = {"seed": pj["seed"], "hash": pj["hash"],
                        "n_main": len(pj["main"]), "n_backup": len(pj["backup"]),
                        "逐月/逐桶": {str(k): int(v) for k, v in
                                  pd.Series([p["year"] for p in pj["main"]])
                                  .value_counts().sort_index().items()}}
    for f in ("picks_compare_a2.json", "packets_substitutions.json"):
        p = CACHE / f
        if p.exists():
            out[f.replace(".json", "")] = json.loads(p.read_text(encoding="utf-8"))
    pk = CACHE / "packets_log.csv"
    if pk.exists():
        p = pd.read_csv(pk, encoding="utf-8-sig")
        out["packets"] = {"n": int(len(p)), "遮罩不合": int((~p["ok"]).sum()),
                          "無 EX-99.1 全文": int((p["ex991_chars"] == 0).sum()),
                          "季數分佈": {str(k): int(v) for k, v in
                                   p["n_quarters"].value_counts().items()}}

    co = HERE / "controls_operating.csv"
    if co.exists():
        c = pd.read_csv(co, encoding="utf-8-sig")
        blank = lambda s: int((s.fillna("") != "").sum())                  # noqa: E731
        out["controls"] = {
            "n": int(len(c)),
            "C1 有值": blank(c["C1_implied_yoy"]),
            "C1 全部標估算": bool((c.loc[c["C1_implied_yoy"].notna(),
                                     "C1_estimated"] == "真").all()),
            "C2 有值": blank(c["C2_prev4_avg_yoy"]),
            "C3 有值": blank(c["C3_g0_text"]),
            "C1 無值原因": {str(k): int(v) for k, v in
                        c.loc[c["C1_implied_yoy"].isna(), "C1_note"]
                        .str.slice(0, 14).value_counts().items()},
        }

    # ---- A2(v1.1)對 A3(v1.2)
    A2 = HERE.parent / "A2"
    a2imp = pd.read_parquet(A2 / "cache" / "population_improvement.parquet")
    a2pop = pd.read_parquet(A2 / "cache" / "population_base.parquet")
    if "entry_pool" in a2imp.columns:
        a2ep = a2imp[a2imp["entry_pool"] == 1]
    else:      # A2 用 v1.1 定義:同年第 90 百分位 + 改善非無 + 無持續經營疑慮
        a2ep = a2imp[(a2imp["pass_p90"] == 1)
                     & (a2imp["improvement_type"].isin(["加速", "指引", "兩者"]))
                     & (a2imp["excl_going_concern"] != "有")]
    th12 = th_all.get("by_year", {})
    out["a2_vs_a3"] = {
        "母體事件數": {"a2": int(len(a2pop)), "a3": int(len(df))},
        "宇宙內": {"a2": int(a2pop["in_universe"].sum()), "a3": int(df["in_universe"].sum())},
        "宇宙內逐年": {y: {"a2": int(((a2pop["year"].astype(str) == y)
                                 & (a2pop["in_universe"] == 1)).sum()),
                        "a3": int(((df["year"].astype(str) == y)
                                   & (df["in_universe"] == 1)).sum())}
                   for y in sorted(th12)},
        "入口池": {"a2": int(len(a2ep)), "a3": int(len(ep))},
        "入口池逐年": {y: {"a2": int((a2ep["year"].astype(str) == y).sum()),
                       "a3": int((ep["year"].astype(str) == y).sum())}
                   for y in sorted(th12)},
        "門檻定義": "a2 = 同年全體事件第 90 百分位;a3 = 逐事件前 252 交易日窗口第 90 百分位",
    }

    g = subprocess.run(["git", "status", "--porcelain", "--", "strategy", "karst",
                        "library", "tools"], cwd=ROOT, capture_output=True, text=True)
    out["git_status_strategy_karst_library_tools"] = g.stdout.strip() or "(乾淨)"
    g2 = subprocess.run(["git", "log", "--oneline", "-1"], cwd=ROOT,
                        capture_output=True, text=True)
    out["git_head"] = g2.stdout.strip()

    (CACHE / "stats_summary.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for k in ("population", "entry_pool", "candidates", "thresholds_window", "controls",
              "release_timing"):
        print("== %s ==" % k)
        print(json.dumps(out.get(k, {}), ensure_ascii=False, indent=1)[:1200])
    print("→", CACHE / "stats_summary.json")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
