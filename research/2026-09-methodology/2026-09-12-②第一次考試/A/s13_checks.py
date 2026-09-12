# -*- coding: utf-8 -*-
"""KARST-222 票 A:驗收條件自查(逐條以「反例」形式檢查),輸出 cache/acceptance_checks.json。

只讀,不改任何交付品。
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DATE_RE = re.compile(r"(20\d\d)-(\d\d)-(\d\d)")


def main() -> None:
    out: dict = {}
    pop = pd.read_csv(HERE / "population.csv", encoding="utf-8-sig", low_memory=False)
    ep = pd.read_csv(HERE / "entry_pool.csv", encoding="utf-8-sig", low_memory=False)
    th = json.loads((CACHE / "thresholds.json").read_text(encoding="utf-8"))

    # 1 population.csv
    need_id = ["accessionNumber", "cik", "ticker", "sic2", "fiscal_quarter", "cluster_id",
               "repeat_company_flag", "adr_flag", "covid_window", "improvement_type",
               "reaction_date", "t2_date", "exclusion_reason"]
    out["1_population"] = {
        "rows": len(pop), "cols": pop.shape[1], "entry_pool_rows": len(ep),
        "rows_ge_entry": len(pop) >= len(ep),
        "missing_id_cols": [c for c in need_id if c not in pop.columns],
        "excl_reason_blank": int((pop["exclusion_reason"].fillna("") == "").sum()),
    }

    # 2 entry_pool 逐列
    yr = ep["year"].astype(str)
    p90 = yr.map(lambda y: th[y]["p90"])
    bad_p = int((ep["rel_spy"] < p90).sum())
    bad_i = int((~ep["improvement_type"].isin(["加速", "指引", "兩者"])).sum())
    out["2_entry_pool"] = {"rows": len(ep), "below_p90": bad_p, "improvement_無": bad_i,
                           "nan_rel_spy": int(ep["rel_spy"].isna().sum()),
                           "by_year": yr.value_counts().sort_index().to_dict(),
                           "by_bucket": ep["bucket"].value_counts().to_dict()}

    # 3 picks 鎖定檔
    md = (HERE / "picks_before_results.md").read_bytes()
    picks = json.loads((CACHE / "picks.json").read_text(encoding="utf-8"))
    mtime = (HERE / "picks_before_results.md").stat().st_mtime
    pkt = sorted((HERE / "packets").glob("*.json"))
    pk_times = [p.stat().st_mtime for p in pkt]
    ctrl_t = (HERE / "controls_operating.csv").stat().st_mtime
    # 由 md 內文的清單逐行重算雜湊,證明本體未被改動(不靠檔案 mtime)
    txt = md.decode("utf-8")
    main_rows = re.findall(r"^\d+\. (\S+)\(E\d+,(\d+),", txt, re.M)
    bk_rows = re.findall(r"^\d+\. (\S+)\(B\d+,(\d+),", txt, re.M)
    payload = "\n".join("%s|%s" % (y, a) for a, y in main_rows) + "\n---\n" + \
        "\n".join("%s|%s" % (y, a) for a, y in bk_rows)
    recomputed = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    out["3_lock"] = {
        "md_sha256": hashlib.sha256(md).hexdigest(),
        "清單雜湊_由內文重算": recomputed,
        "清單雜湊_與鎖定時相同": recomputed == picks["hash"],
        "重算用列數": [len(main_rows), len(bk_rows)],
        "md_mtime": pd.Timestamp(mtime, unit="s", tz="UTC").isoformat(),
        "picks_json_hash": picks["hash"],
        "n_main": len(picks["main"]), "n_backup": len(picks["backup"]),
        "packets": len(pkt),
        "earliest_packet_mtime": pd.Timestamp(min(pk_times), unit="s", tz="UTC").isoformat(),
        "controls_mtime": pd.Timestamp(ctrl_t, unit="s", tz="UTC").isoformat(),
        "lock_earlier_than_all": bool(mtime < min(pk_times) and mtime < ctrl_t),
        "seconds_before_earliest_packet": round(min(pk_times) - mtime, 1),
    }

    # 4 逐包掃描
    leak_keys = ["C1_guidance", "C2_prev4", "C3_g0", "controls_operating"]
    bad_mask, bad_date, ex_missing, n_pkt = [], [], [], 0
    worst = []
    for p in pkt:
        d = json.loads(p.read_text(encoding="utf-8"))
        n_pkt += 1
        mc = d.get("masking_check", {})
        if not mc.get("verified"):
            bad_mask.append(p.name)
        cut = d["1_事件識別"]["signal_date_反應日"]
        raw = p.read_text(encoding="utf-8")
        # 剔走包內元資料欄(provenance.frozen = 凍結日),只掃資料本身
        raw = raw.replace('"frozen": "2026-09-12"', "")
        t2 = d["1_事件識別"]["T2_可成交"].split(" ")[0]
        ds = [m.group(0) for m in DATE_RE.finditer(raw) if m.group(0) > cut]
        other = sorted({x for x in ds if x != t2})   # T2(反應日後首個交易日)屬設計內欄位
        if other:
            bad_date.append({"packet": p.name, "cutoff": cut, "n": len(other),
                             "max": max(other),
                             "context": [raw[max(0, raw.find(x) - 30):raw.find(x) + len(x) + 12]
                                         .replace("\n", " ") for x in other]})
        worst.append((d["masking_check"]["latest_data_date"], cut))
        if not d["2_觸發資料"]["ex991_full_text"].strip() or \
                d["2_觸發資料"]["ex991_full_text"] == "查不到":
            ex_missing.append(p.name)
        if any(k in raw for k in leak_keys):
            bad_mask.append(p.name + ":對照預測欄")
    out["4_packets"] = {
        "n": n_pkt, "masking_unverified": bad_mask,
        "packets_with_iso_date_after_cutoff": bad_date,
        "ex991_missing": ex_missing,
        "latest_le_cutoff_all": all(a <= b for a, b in worst),
        "max_latest_data_date": max(a for a, _ in worst),
    }

    # 5 controls 另檔
    ctrl = pd.read_csv(HERE / "controls_operating.csv", encoding="utf-8-sig")
    out["5_controls"] = {
        "rows": len(ctrl), "one_row_per_event": bool(ctrl["event_id"].is_unique),
        "cols": [c for c in ctrl.columns if c.startswith("C")],
        "C1_有值": int((ctrl["C1_guidance_implied_growth"].notna()).sum()),
        "C2_有值": int((ctrl["C2_prev4_avg_yoy"].notna()).sum()),
        "C3_有值": int((ctrl["C3_g0"].notna()).sum()),
        "n_events_expected": len(picks["main"]) + len(picks["backup"]),
    }
    (CACHE / "acceptance_checks.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
