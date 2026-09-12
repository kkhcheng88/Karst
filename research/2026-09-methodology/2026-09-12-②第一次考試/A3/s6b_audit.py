# -*- coding: utf-8 -*-
"""KARST-226 票 A″ 第五步後半:指引解析器 40 句抽查 + 四類各 5 宗核對樣本。

①由 `cache/guidance_parsed.jsonl` 以種子 20260912 抽 40 筆(逐句逐指標),落
  `cache/audit_sample_raw.jsonl`,供人手逐句核對,結果寫 `guidance_audit.md`。
②由入池/被剔事件抽四類各 5 宗(加速只 / 指引只 / 兩者 / 被剔),落
  `cache/audit_sample.json`,只記 accessionNumber、CIK 與欄位值,不記公司名或代號。
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
SEED = 20260912
N_AUDIT = 40


def main() -> None:
    recs = [json.loads(line) for line in
            (CACHE / "guidance_parsed.jsonl").open(encoding="utf-8")]
    print("指引紀錄總數:%d" % len(recs))
    rng = random.Random(SEED)
    sample = rng.sample(recs, N_AUDIT)
    with (CACHE / "audit_sample_raw.jsonl").open("w", encoding="utf-8") as f:
        for r in sample:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("抽查 40 句(種子 %d)→ %s" % (SEED, CACHE / "audit_sample_raw.jsonl"))

    df = pd.read_parquet(CACHE / "population_improvement.parquet")
    pool = df[df["entry_pool"] == 1]
    groups = {
        "加速只": pool[pool["improvement_type"] == "加速"],
        "指引只": pool[pool["improvement_type"] == "指引"],
        "兩者": pool[pool["improvement_type"] == "兩者"],
        "被剔": df[(df["in_universe"] == 1) & (df["in_pool_window"])
                   & (df["pass_thr"] == True)                               # noqa: E712
                   & (df["entry_pool"] == 0)],
    }
    cols = ["accessionNumber", "cik", "year", "filingDate", "reaction_date",
            "release_timing", "signal_q_end", "rev_signal_xbrl", "rev_signal_text",
            "signal_rev_in_text", "rev_g0_text", "accel_pp_text", "accel_text_hit",
            "guide_rev_raise", "guidance_raise_eps_only", "hist_quarters_public_by_t1",
            "applicability_reason", "excl_no_text", "excl_intraday", "excl_earlier_release",
            "excl_hist_not_public", "excl_applicability", "excl_financial_sic",
            "rel_spy", "rel_sic2", "thr_p90", "entry_pool"]
    out: dict = {"seed": SEED, "n_audit_sentences": N_AUDIT, "groups": {}}
    for gname, g in groups.items():
        take = g.sort_values("accessionNumber").head(5)
        out["groups"][gname] = [{c: (None if pd.isna(r[c]) else
                                     (int(r[c]) if isinstance(r[c], (bool,)) else r[c]))
                                 for c in cols} for _, r in take.iterrows()]
        print("  %s:%d 宗(取前 5)" % (gname, len(g)))
    (CACHE / "audit_sample.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("→", CACHE / "audit_sample.json")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
