# -*- coding: utf-8 -*-
"""第一部前置:列出 audit_sample 四類 20 宗在 population / entry_pool 的對應列。
輸出 audit_out/a1_sample.txt。不列公司名。
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_common as C

s = C.load_sample()
pool = C.load_pool()
main, back = C.load_picks_md()
picks_all = {r["accessionNumber"]: ("主", r["event_id"]) for r in main}
picks_all.update({r["accessionNumber"]: ("後備", r["event_id"]) for r in back})

accs = []
for g, rows in s["groups"].items():
    for r in rows:
        accs.append((g, r))

pop = C.load_population({r["accessionNumber"] for _, r in accs})

lines = []
lines.append(f"seed={s['seed']} groups={list(s['groups'])}")
lines.append(f"主清單 {len(main)} 宗;後備 {len(back)} 宗")
out = []
for g, r in accs:
    a = r["accessionNumber"]
    p = pop.get(a)
    o = {
        "group": g, "acc": a, "cik": r["cik"], "year": r["year"],
        "filingDate": r["filingDate"], "reaction_date": r["reaction_date"],
        "release_timing": r["release_timing"], "signal_q_end": r["signal_q_end"],
        "samp_signal_rev_in_text": r["signal_rev_in_text"],
        "samp_g0_text": r["rev_g0_text"], "samp_accel_pp_text": r["accel_pp_text"],
        "samp_guide_rev_raise": r["guide_rev_raise"],
        "samp_entry_pool": r["entry_pool"],
        "excl_flags": {k: r[k] for k in r if k.startswith("excl_")},
        "samp_thr_p90": r["thr_p90"],
        "in_pool_csv": a in pool,
        "picks": picks_all.get(a),
    }
    if p is None:
        o["population"] = "NOT FOUND"
    else:
        o["population"] = {
            "entry_pool": p["entry_pool"], "improvement_type": p["improvement_type"],
            "signal_rev_in_text": p["signal_rev_in_text"],
            "rev_signal_text": p["rev_signal_text"], "rev_signal_xbrl": p["rev_signal_xbrl"],
            "rev_g0_text": p["rev_g0_text"], "rev_prev_q_yoy": p["rev_prev_q_yoy"],
            "accel_pp_text": p["accel_pp_text"], "accel_text_hit": p["accel_text_hit"],
            "guide_rev_raise": p["guide_rev_raise"],
            "guidance_metric": p["guidance_metric"], "guidance_period": p["guidance_period"],
            "guidance_old_lo": p["guidance_old_lo"], "guidance_old_hi": p["guidance_old_hi"],
            "guidance_new_lo": p["guidance_new_lo"], "guidance_new_hi": p["guidance_new_hi"],
            "guidance_mid_change": p["guidance_mid_change"],
            "guidance_raise_flag": p["guidance_raise_flag"],
            "guidance_old_missing": p["guidance_old_missing"],
            "guidance_eps_only": p["guidance_eps_only"],
            "hist_quarters_public_by_t1": p["hist_quarters_public_by_t1"],
            "applicability_reason": p["applicability_reason"],
            "exclusion_reason": p["exclusion_reason"],
            "thr_win_days": p["thr_win_days"], "thr_n": p["thr_n"],
            "thr_p90": p["thr_p90"], "rel_spy": p["rel_spy"],
            "release_timing": p["release_timing"], "t0_source": p["t0_source"],
            "t0_et": p["t0_et"], "acceptanceDateTime": p["acceptanceDateTime"],
            "dateline": p["dateline"], "prior_day_abs_ret": p["prior_day_abs_ret"],
            "pass_p90": p["pass_p90"],
        }
    out.append(o)

with open(os.path.join(C.OUT, "a1_sample.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

for o in out:
    lines.append("=" * 70)
    lines.append(f"[{o['group']}] {o['acc']} cik={o['cik']} year={o['year']} "
                 f"file={o['filingDate']} react={o['reaction_date']} rt={o['release_timing']} "
                 f"qe={o['signal_q_end']} in_pool_csv={o['in_pool_csv']} picks={o['picks']}")
    p = o["population"]
    if p == "NOT FOUND":
        lines.append("  population: NOT FOUND")
    else:
        lines.append("  pop: " + json.dumps(p, ensure_ascii=False))
    lines.append("  samp entry_pool=%s thr_p90=%s guide_raise=%s" %
                 (o["samp_entry_pool"], o["samp_thr_p90"], o["samp_guide_rev_raise"]))
with open(os.path.join(C.OUT, "a1_sample.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\n".join(lines))
