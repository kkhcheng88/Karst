# -*- coding: utf-8 -*-
"""KARST-225 票 A′(v1.1):把執行紀錄要用的數一次過數齊,落 cache/stats_summary.json。

不改任何既有檔,只讀。跑完之後人手把數字寫進 `執行紀錄——A.md`(紀錄的正本是人寫的,
這支只負責令數字可重複核對)。
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
DOCS = HERE.parent / "A" / "edgar_cache"      # 沿用 v1 的原文快取

SCRIPTS = ["s2_turnover.py", "s4_assemble.py", "s5_fetch_text.py", "s6_guidance.py",
           "s7_sample_lock.py", "s8_controls.py", "s9_packets.py", "s10_export.py",
           "s11_verify3.py", "s12_stats.py", "s13_checks.py", "finlib.py", "pxlib.py",
           "buckets.py"]


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
        "8-K 申報": "data/sec/submissions/CIK*.json(本地 submissions 快取,8121 檔)",
        "XBRL": "data/sec/companyfacts/CIK*.json.gz",
        "日線": "data/prices/daily/part_*.parquet(series_role == primary)",
        "SPY": "data/prices/spy_daily.csv",
        "公司與行業": "data/universe/entities.parquet",
        "票價代號": "data/universe/ticker_periods.parquet",
        "10-K 全文": "data/sec/10k_text/*.txt.gz(只作對照)",
        "申報原文": "A/edgar_cache/(gitignore,不入庫)",
    }

    df = pd.read_parquet(CACHE / "population_base.parquet")
    imp = pd.read_parquet(CACHE / "population_improvement.parquet")
    out["population"] = {
        "掃到的 8-K Item 2.02 事件數": int(len(df)),
        "涉及公司數": int(df["cik"].nunique()),
        "宇宙內": int(df["in_universe"].sum()),
        "排除": {
            "無日線": int((df["excl_no_price"] == 1).sum()),
            "成交額不足": int((df["excl_volume"] == 1).sum()),
            "上市未滿 12 個月": int((df["excl_listed_lt_12m"] == 1).sum()),
            "SPAC": int((df["excl_spac"] == 1).sum()),
            "同日 8-K 有 Item 1.01": int((df["excl_merger_1_01"] == 1).sum()),
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

    th = json.loads((CACHE / "thresholds.json").read_text(encoding="utf-8"))
    out["thresholds"] = th
    out["entry_counts"] = {}
    for pc in ("pass_p95", "pass_p90", "pass_p80"):
        s = imp[(imp[pc] == 1) & (imp["improvement_type"].isin(["加速", "指引", "兩者"]))]
        out["entry_counts"][pc] = {
            "n": int(len(s)),
            "by_year": {str(k): int(v) for k, v in
                        s["year"].astype(str).value_counts().sort_index().items()},
            "by_bucket": {k: int(v) for k, v in s["bucket"].value_counts().items()},
            "improvement_type": {k: int(v) for k, v in
                                 s["improvement_type"].value_counts().items()},
        }
    out["improvement_type_全母體"] = {k: int(v) for k, v in
                                  imp["improvement_type"].value_counts().items()}

    # 抓文本
    log = CACHE / "fetch_log.jsonl"
    if log.exists():
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
        p90 = set(df[df["pass_p90"] == 1]["accessionNumber"])
        out["fetch"] = {
            "log 行數(含重複嘗試)": tot,
            "成功事件數(去重)": len(ok),
            "失敗狀態分佈": why,
            "p90 集內已有全文": len(p90 & ok),
            "p90 集內缺全文": len(p90 - ok),
            "edgar_cache 檔數": sum(1 for _ in DOCS.iterdir()) if DOCS.exists() else 0,
            "edgar_cache 全文檔": sum(1 for _ in DOCS.glob("*__EX991.txt.gz")),
        }

    picks = CACHE / "picks.json"
    if picks.exists():
        pj = json.loads(picks.read_text(encoding="utf-8"))
        out["picks"] = {"seed": pj["seed"], "hash": pj["hash"],
                        "n_main": len(pj["main"]), "n_backup": len(pj["backup"])}
    sub = CACHE / "packets_substitutions.json"
    if sub.exists():
        out["substitutions"] = json.loads(sub.read_text(encoding="utf-8"))
    pk = CACHE / "packets_log.csv"
    if pk.exists():
        p = pd.read_csv(pk, encoding="utf-8-sig")
        out["packets"] = {"n": int(len(p)),
                          "遮罩不合": int((~p["ok"]).sum()),
                          "無 EX-99.1 全文": int((p["ex991_chars"] == 0).sum())}
    # ---- v1 對 v1.1 的差(執行紀錄第 8 步)
    A = HERE.parent / "A"
    v1pop = pd.read_parquet(A / "cache" / "population_base.parquet")
    v1imp = pd.read_parquet(A / "cache" / "population_improvement.parquet")
    v1ep = v1imp[(v1imp["pass_p90"] == 1)
                 & (v1imp["improvement_type"].isin(["加速", "指引", "兩者"]))
                 & (v1imp["excl_going_concern"] != "有")]
    ep11 = imp[(imp["pass_p90"] == 1)
               & (imp["improvement_type"].isin(["加速", "指引", "兩者"]))
               & (imp["excl_going_concern"] != "有")]
    v1th = json.loads((A / "cache" / "thresholds.json").read_text(encoding="utf-8"))
    cmp = json.loads((CACHE / "picks_compare_v1.json").read_text(encoding="utf-8"))
    out["v1_vs_v11"] = {
        "母體事件數": int(len(df)),
        "宇宙內事件數": {"v1": int(v1pop["in_universe"].sum()),
                    "v11": int(df["in_universe"].sum())},
        "宇宙內逐年": {y: {"v1": int(((v1pop["year"].astype(str) == y)
                                 & (v1pop["in_universe"] == 1)).sum()),
                        "v11": int(((df["year"].astype(str) == y)
                                    & (df["in_universe"] == 1)).sum())}
                   for y in sorted(th)},
        "入口池數": {"v1": int(len(v1ep)), "v11": int(len(ep11))},
        "入口池逐年": {y: {"v1": int((v1ep["year"].astype(str) == y).sum()),
                       "v11": int((ep11["year"].astype(str) == y).sum())}
                   for y in sorted(th)},
        "逐年門檻": {y: {"v1_p90": v1th[y]["p90"], "v11_p90": th[y]["p90"],
                      "v1_n": v1th[y]["n"], "v11_n": th[y]["n"]} for y in sorted(th)},
        "picks_compare": cmp,
    }

    # ---- 取證包:新建 vs 可對應 A/packets(同 accessionNumber)
    v1acc = set()
    for f in (A / "packets").glob("*.json"):
        v1acc.add(json.loads(f.read_text(encoding="utf-8"))["1_事件識別"]["accessionNumber"])
    log = CACHE / "packets_log.csv"
    if log.exists():
        pl = pd.read_csv(log, encoding="utf-8-sig")
        out["packets_copy_vs_new"] = {
            "n_packets": int(len(pl)),
            "copied_from_A": 0,
            "built_new": int(len(pl)),
            "same_accession_as_A_packet": int(pl["acc"].isin(v1acc).sum()),
            "note": "A2 全部 84 包由 s9 新建;與 A/packets 同 accessionNumber 者另做逐節比對",
        }

    co = HERE / "controls_operating.csv"
    if co.exists():
        c = pd.read_csv(co, encoding="utf-8-sig")
        out["controls"] = {
            "n": int(len(c)),
            "C1 有值": int((c["C1_guidance_implied_growth"].notna()).sum()),
            "C2 有值": int((c["C2_prev4_avg_yoy"].notna()).sum()),
            "C3 有值": int((c["C3_g0"].notna()).sum()),
            "C1 註解分佈": {k: int(v) for k, v in c["C1_note"].value_counts().items()},
        }

    # git 不改(只讀狀態作證)
    g = subprocess.run(["git", "status", "--porcelain", "--", "strategy", "karst",
                        "library", "tools"], cwd=ROOT, capture_output=True, text=True)
    out["git_status_strategy_karst_library_tools"] = g.stdout.strip() or "(乾淨)"
    g2 = subprocess.run(["git", "log", "--oneline", "-1"], cwd=ROOT,
                        capture_output=True, text=True)
    out["git_head"] = g2.stdout.strip()

    (CACHE / "stats_summary.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out["population"], ensure_ascii=False, indent=1))
    print(json.dumps(out.get("entry_counts", {}), ensure_ascii=False, indent=1)[:2000])
    print(json.dumps(out.get("fetch", {}), ensure_ascii=False, indent=1))
    print("→", CACHE / "stats_summary.json")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
