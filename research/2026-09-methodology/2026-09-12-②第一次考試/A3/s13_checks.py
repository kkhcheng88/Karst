# -*- coding: utf-8 -*-
"""KARST-226 票 A″(執行口徑 v1.2)第十三步:驗收條件自查(逐條以「反例」形式檢查),
輸出 `cache/acceptance_checks.json`。

六條驗收條件(票上原文)逐條對:
  1. `thresholds.md` 是逐事件窗口的描述統計;反例 = 任何入池事件的門檻用上反應日當日或
     之後的事件。(本支**獨立重算**每宗入池事件的前視窗門檻,再與建池時的
     `thresholds_window.parquet` 對;並核窗口內事件的最大反應日嚴格早於自身反應日。)
  2. `population.csv` 每列有 t0_source / prior_day_abs_ret / signal_rev_in_text /
     guidance_parse 各欄 / applicability_reason(三類)/ 九個標籤欄。
     反例 = 任何入池事件 signal_rev_in_text 為「假」;或指引只靠 raise 字眼而無舊新中點
     且未標「舊值缺」。
  3. `guidance_audit.md`:40 句逐句原文 + 解析結果 + 人手判詞,一個錯誤率;> 15% 舉手。
  4. `picks_before_results.md`:主 84 + 後備 44、種子 20260912、每年每桶數量、SHA-256,
     且落檔早於 `packets/` 與 `controls_operating.csv`;清單不含公司名或代號。
  5. `packets/` 84 包;任何一包含 T1 之後日期的資料即整批不合格;`4_財務數列` 訊號季
     一行標明來源 = EX-99.1 稿內;控制檔另檔、不入包。
  6. `執行紀錄——A3.md` 含第 10 項三項調查與各節;`A/`、`A2/` git status 乾淨;未 commit。

只讀,不改任何交付品。
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\projects\Karst")
HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
SPY_CSV = ROOT / "data" / "prices" / "spy_daily.csv"
DATE_RE = re.compile(r"(20\d\d)-(\d\d)-(\d\d)")
WIN_MAIN, WIN_WIDE, MIN_N = 252, 504, 300
LABELS9 = ["g0_negative", "rev_ttm", "both_signals", "above_200dma", "rs6_top20",
           "rel_sic2_ge5", "accel_2q", "surprise_c2", "guidance_raise_eps_only"]
GCOLS = ["guidance_metric", "guidance_period", "guidance_old_lo", "guidance_old_hi",
         "guidance_new_lo", "guidance_new_hi", "guidance_mid_change",
         "guidance_raise_flag", "guidance_old_missing", "guidance_eps_only"]


# ---------------------------------------------------------------- 1 門檻前視
def check_thresholds(pop: pd.DataFrame, pool: pd.DataFrame) -> dict:
    spy = pd.read_csv(SPY_CSV, parse_dates=["date"]).sort_values("date")
    sd = spy["date"].values.astype("datetime64[D]")
    u = pop[(pop["in_universe"] == 1) & pop["rel_spy"].notna()
            & pop["reaction_date"].notna() & (pop["reaction_date"].astype(str) != "")]
    rd = pd.to_datetime(u["reaction_date"]).values.astype("datetime64[D]")
    rv = u["rel_spy"].to_numpy(float)
    w = pd.read_parquet(CACHE / "thresholds_window.parquet").set_index("accessionNumber")

    rp = pd.to_datetime(pool["reaction_date"]).values.astype("datetime64[D]")
    n_ok = n_mismatch = n_future = n_insuf = 0
    worst_gap = None
    mismatch, future = [], []
    for acc, d in zip(pool["accessionNumber"], rp):
        p = int(np.searchsorted(sd, d))
        if p >= len(sd) or sd[p] != d:
            p = int(np.searchsorted(sd, d, side="right"))
        m = (rd >= sd[max(0, p - WIN_MAIN)]) & (rd < d)
        nn, used = int(m.sum()), WIN_MAIN
        if nn < MIN_N:
            m2 = (rd >= sd[max(0, p - WIN_WIDE)]) & (rd < d)
            if int(m2.sum()) > nn:
                m, nn, used = m2, int(m2.sum()), WIN_WIDE
        if nn < MIN_N:
            n_insuf += 1
            continue
        p90 = float(np.percentile(rv[m], 90))
        row = w.loc[acc]
        if row["thr_win_days"] != used or int(row["thr_n"]) != nn or \
                abs(float(row["thr_p90"]) - p90) > 1e-9:
            mismatch.append({"acc": acc, "redo_n": nn, "redo_p90": round(p90, 6),
                             "table_n": int(row["thr_n"]),
                             "table_p90": round(float(row["thr_p90"]), 6),
                             "table_win": int(row["thr_win_days"]), "redo_win": used})
        else:
            n_ok += 1
        if nn:
            gap = int((d - rd[m].max()).astype("timedelta64[D]").astype(int))
            if rd[m].max() >= d:
                future.append({"acc": acc})
            if worst_gap is None or gap < worst_gap[1]:
                worst_gap = (acc, gap, used)
    md = (HERE / "thresholds.md").read_text(encoding="utf-8")
    return {
        "thresholds_md_chars": len(md),
        "thresholds_md_逐事件窗口": "反應日之前過去 252 個交易日" in md,
        "thresholds_md_描述統計": "描述統計" in md and "分佈" in md,
        "thresholds_md_逐年表": md.count("第90百分位門檻") >= 1,
        "thresholds_md_仍有「一年一個門檻」寫法": "一年的門檻" in md,
        "pool_events_rechecked": int(len(pool)),
        "recomputed_matches_table": n_ok,
        "recomputed_mismatch": mismatch,
        "events_with_window_event_on_or_after_reaction": future,
        "events_insufficient_in_recheck": n_insuf,
        "min_gap_days_own_reaction_minus_latest_window_event": (
            None if worst_gap is None else worst_gap[1]),
        "pass": (not mismatch) and (not future) and n_insuf == 0
        and "反應日之前過去 252 個交易日" in md,
    }


# ---------------------------------------------------------------- 2 population
def check_population(pop: pd.DataFrame, pool: pd.DataFrame) -> dict:
    need = ["t0_source", "dateline", "release_timing", "prior_day_abs_ret",
            "signal_rev_in_text", "applicability_reason", "exclusion_reason"]
    vals = pool["signal_rev_in_text"].value_counts().to_dict()
    bad_text = pool[pool["signal_rev_in_text"] == "假"]
    # 指引反例:只靠 raise 字眼、無舊新中點、又未標「舊值缺」
    raise_rows = pool[pool["guidance_raise_flag"] == True]                    # noqa: E712
    has_mid = raise_rows["guidance_mid_change"].notna() | (
        raise_rows["guidance_new_lo"].notna() & raise_rows["guidance_new_hi"].notna())
    bad_g = raise_rows[(~has_mid) & (raise_rows["guidance_old_missing"] != True)]  # noqa: E712
    ar = pool["applicability_reason"].fillna("")
    return {
        "rows": int(len(pop)), "cols": int(pop.shape[1]), "pool_rows": int(len(pool)),
        "missing_columns": [c for c in need if c not in pop.columns],
        "missing_guidance_columns": [c for c in GCOLS if c not in pop.columns],
        "missing_label_columns": [c for c in LABELS9 if c not in pop.columns],
        "signal_rev_in_text_值分佈(pool)": {str(k): int(v) for k, v in vals.items()},
        "pool_rows_with_signal_rev_in_text_假": int(len(bad_text)),
        "guidance_raise_rows": int(len(raise_rows)),
        "guidance_raise_缺中點且未標舊值缺": int(len(bad_g)),
        "pool_with_revenue_guidance_record": int(
            pool["guidance_metric"].eq("revenue").sum()),
        "pool_guidance_raise_flag_true": int(
            (pool["guidance_raise_flag"] == True).sum()),                       # noqa: E712
        "improvement_type_指引_only_且有收入上調紀錄": int(
            ((pool["improvement_type"] == "指引")
             & (pool["guidance_raise_flag"] == True)).sum()),                   # noqa: E712
        "applicability_reason_三類(pool)": {str(k): int(v) for k, v in
                                       ar[ar != ""].value_counts().items()},
        "applicability_reason_三類(全母體非空)": {str(k): int(v) for k, v in
                                        pop["applicability_reason"].fillna("")
                                        .replace("", np.nan).dropna()
                                        .value_counts().items()},
        "t0_source_分佈(pool)": {str(k): int(v) for k, v in
                             pool["t0_source"].value_counts().items()},
        "pass": (not [c for c in need + GCOLS + LABELS9 if c not in pop.columns])
        and len(bad_text) == 0 and len(bad_g) == 0,
    }


# ---------------------------------------------------------------- 3 指引抽查
def check_audit() -> dict:
    md = (HERE / "guidance_audit.md").read_text(encoding="utf-8")
    n_rows = len(re.findall(r"^\|\s*\d+\s*\|", md, re.M))
    rates = [float(x) for x in re.findall(r"錯誤率[^\n]*?(\d+(?:\.\d+)?)%", md)]
    over = [r for r in rates if r > 15.0]
    return {
        "chars": len(md), "table_rows_numbered": n_rows,
        "有四十句": "四十句" in md or n_rows >= 40,
        "錯誤率": rates, "高於 15% 的次數": len(over),
        "已寫明舉手": "舉手" in md,
        "pass": bool(rates) and len(over) > 0 and "舉手" in md,
    }


# ---------------------------------------------------------------- 4 抽樣鎖定
def check_lock() -> dict:
    p = HERE / "picks_before_results.md"
    md_b = p.read_bytes()
    txt = md_b.decode("utf-8")
    main = re.findall(r"^\d+\. (\S+)\(E\d+,(\d+),", txt, re.M)
    bk = re.findall(r"^\d+\. (\S+)\(B\d+,(\d+),", txt, re.M)
    payload = "\n".join("%s|%s" % (y, a) for a, y in main) + "\n---\n" + \
        "\n".join("%s|%s" % (y, a) for a, y in bk)
    recomp = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    picks = json.loads((CACHE / "picks.json").read_text(encoding="utf-8"))
    mtime = p.stat().st_mtime
    pk = sorted((HERE / "packets").glob("*.json"))
    pk_t = [x.stat().st_mtime for x in pk]
    ctrl_t = (HERE / "controls_operating.csv").stat().st_mtime
    # 表內「公司—事件」欄須為 10 位 CIK(不含公司名或代號)
    cells = re.findall(r"^\|\s*\d+\s*\|\s*[EB]\d{3}\s*\|[^|]*\|[^|]*\|\s*(\S+)\s*\|",
                       txt, re.M)
    bad_cells = [c for c in cells if not re.fullmatch(r"\d{10}", c)]
    return {
        "md_sha256": hashlib.sha256(md_b).hexdigest(),
        "清單雜湊_由內文重算": recomp,
        "清單雜湊_與鎖定檔相同": recomp == picks["hash"],
        "n_main_md": len(main), "n_backup_md": len(bk),
        "n_main_json": len(picks["main"]), "n_backup_json": len(picks["backup"]),
        "seed_in_md": "20260912" in txt, "seed_json": picks["seed"],
        "每年每桶表": "每年每桶數量" in txt,
        "CIK欄位數": len(cells), "非10位CIK的格": bad_cells[:5],
        "md_mtime": pd.Timestamp(mtime, unit="s", tz="UTC").isoformat(),
        "earliest_packet_mtime": pd.Timestamp(min(pk_t), unit="s", tz="UTC").isoformat(),
        "controls_mtime": pd.Timestamp(ctrl_t, unit="s", tz="UTC").isoformat(),
        "落檔早於全部包與控制檔": bool(mtime < min(pk_t) and mtime < ctrl_t),
        "pass": (recomp == picks["hash"] and len(main) == 84 and len(bk) == 44
                 and "每年每桶數量" in txt and "20260912" in txt and not bad_cells
                 and mtime < min(pk_t) and mtime < ctrl_t),
    }


# ---------------------------------------------------------------- 5 取證包
def check_packets() -> dict:
    pk = sorted((HERE / "packets").glob("*.json"))
    leak_keys = ["C1_implied_yoy", "C2_prev4_avg_yoy", "C3_g0", "controls_operating"]
    bad_date, bad_mask, bad_src, bad_series, no_text = [], [], [], [], []
    max_latest = ""
    for f in pk:
        raw = f.read_text(encoding="utf-8")
        d = json.loads(raw)
        cut = d["1_事件識別"]["signal_date_反應日"]
        t2 = d["1_事件識別"]["T2_可成交"].split(" ")[0]
        clean = raw.replace('"frozen": "2026-09-13"', "")
        ds = [m.group(0) for m in DATE_RE.finditer(clean) if m.group(0) > cut
              and m.group(0) != t2]
        if ds:
            bad_date.append({"packet": f.name, "cutoff": cut, "n": len(ds),
                             "max": max(ds)})
        if not d.get("masking_check", {}).get("verified"):
            bad_mask.append(f.name)
        if any(k in raw for k in leak_keys):
            bad_mask.append(f.name + ":對照預測欄")
        q = d["4_財務數列"]
        rows = q["quarters"]
        ends = [r["period_end"] for r in rows]
        sig = [r for r in rows if r["period_end"] == q["signal_q_end"]]
        if len(sig) != 1 or "EX-99.1 稿內" not in sig[0].get("revenue_source", ""):
            bad_src.append(f.name)
        if len(ends) != 8 or len(set(ends)) != 8 or ends != sorted(ends):
            bad_series.append({"packet": f.name, "n": len(ends)})
        if not d["2_觸發資料"]["ex991_full_text"].strip() or \
                d["2_觸發資料"]["ex991_full_text"] == "查不到":
            no_text.append(f.name)
        max_latest = max(max_latest, d["masking_check"]["latest_data_date"])
    return {
        "n_packets": len(pk),
        "packets_with_iso_date_after_cutoff": bad_date,
        "masking_unverified": bad_mask,
        "signal_row_source_not_ex991": bad_src,
        "series_not_8_consecutive": bad_series,
        "ex991_missing": no_text,
        "max_latest_data_date": max_latest,
        "controls_separate_file": (HERE / "controls_operating.csv").exists()
        and not list((HERE / "packets").glob("*control*")),
        "pass": (len(pk) == 84 and not bad_date and not bad_mask and not bad_src
                 and not bad_series and not no_text),
    }


# ---------------------------------------------------------------- 6 執行紀錄與 git
def check_record() -> dict:
    p = HERE / "執行紀錄——A3.md"
    if not p.exists():
        return {"exists": False, "pass": False}
    t = p.read_text(encoding="utf-8")
    need = {"v1.1 對 v1.2 差異": "v1.1", "290 宗無 XBRL 數列": "290",
            "adr_flag": "adr_flag", "Item 1.01 舊閘": "1.01",
            "疑更早公開": "疑更早公開", "稿內找不到訊號季收入": "訊號季收入",
            "適用性三類": "適用性", "時間戳": "時間戳"}
    g = subprocess.run(["git", "status", "--porcelain", "--",
                        "research/2026-09-methodology/2026-09-12-②第一次考試/A",
                        "research/2026-09-methodology/2026-09-12-②第一次考試/A2"],
                       cwd=ROOT, capture_output=True, text=True)
    head = subprocess.run(["git", "log", "--oneline", "-1"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    missing = [k for k, v in need.items() if v not in t]
    return {
        "exists": True, "chars": len(t), "缺漏小節": missing,
        "A_A2_git_status": g.stdout.strip() or "(乾淨)",
        "git_head": head,
        "pass": not missing and not g.stdout.strip(),
    }


def main() -> None:
    pop = pd.read_csv(HERE / "population.csv", encoding="utf-8-sig", low_memory=False)
    pool = pop[pop["entry_pool"] == 1].copy()
    out = {
        "1_thresholds": check_thresholds(pop, pool),
        "2_population": check_population(pop, pool),
        "3_guidance_audit": check_audit(),
        "4_picks_lock": check_lock(),
        "5_packets": check_packets(),
        "6_record": check_record(),
    }
    out["verdict"] = {k: bool(v.get("pass")) for k, v in out.items()}
    (CACHE / "acceptance_checks.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
