# -*- coding: utf-8 -*-
"""把 audit_out/part1.json 的 20 宗五項證據壓成可讀摘要(寫 audit_out/part1_digest.txt)。
只列 accessionNumber 與 event_id;不列公司名或代號。
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_common as C

E_FIELDS = ["sic", "sic2", "rev_tag_used", "n_consec_q", "applicability_reason",
            "excl_financial_sic", "excl_applicability", "excl_merger_2_01", "excl_merger_1_01",
            "excl_merger_1_01_old", "excl_spac", "excl_listed_lt_12m", "excl_volume",
            "items_same_day", "merger_words", "merger_text_pending", "exclusion_reason",
            "in_universe", "entry_pool", "improvement_type", "excl_no_text", "excl_intraday",
            "excl_earlier_release", "excl_hist_not_public",
            "accel_text_hit", "accel_pp_text", "rev_g0_text", "guide_rev_raise",
            "rev_signal_text", "signal_rev_in_text", "hist_quarters_public_by_t1"]


def main():
    with open(os.path.join(C.OUT, "part1.json"), encoding="utf-8") as f:
        d = json.load(f)
    pop = C.load_population({r["acc"] for r in d})
    L = []
    for r in d:
        a, b, c, e = r["a"], r["b"], r["c"], r["e"]
        L.append("=" * 78)
        L.append("%s %s year=%s" % (r["group"], r["acc"], r["year"]))
        L.append(" (a) 稿頭日=%s(行 %s) 申報日=%s 受理/稿頭源=%s T0_ET=%s | 公開時段(包)=%s 期望=%s 合=%s"
                 % (a["headline_date"], a["headline_line"], a["filingDate"], a["t0_source"],
                    a["t0_et"], a["release_timing"], a["expected_timing"], a["timing_match"]))
        L.append("     理由:%s" % a["expected_reason"])
        L.append("     反應日(包)=%s 期望=%s 合=%s" % (a["reaction_date"], a["expected_reaction_date"],
                                                      a["reaction_match"]))
        L.append("     稿頭行(遮蔽後首 60 字):%s" % a.get("headline_masked", ""))
        L.append("     前一日絕對報酬:包=%s 自算=%s 差=%s"
                 % (a["prior_day_abs_ret_csv"], a["prior_day_abs_ret_recomputed"], a["prior_day_abs_delta"]))
        L.append(" (b) 窗=%s/自算 %s 宗數=%s/%s p90=%s/自算 %s 差=%s 窗內最晚事件反應日=%s 早於本宗=%s 不足=%s"
                 % (b["thr_win_days_csv"], b["recomputed_win"], b["thr_n_csv"], b["recomputed_n"],
                    b["thr_p90_csv"], b["recomputed_p90"], b["p90_delta"],
                    b["latest_window_event_reaction"], b["latest_before_own"], b["insufficient"]))
        L.append("     相對SPY=%s 過門檻=%s" % (b["rel_spy"], b["pass_p90"]))
        L.append(" (c) 稿內訊號季收入=%s XBRL=%s 標記=%s 行命中=%d 首命中行=%s"
                 % (c["rev_signal_text"], c["rev_signal_xbrl"], c["signal_rev_in_text_csv"],
                    c["n_line_hits"], (c["line_hits"][0]["line"] if c["line_hits"] else None)))
        for h in c["line_hits"][:1]:
            L.append("     命中行內數字:%s(行 %s)" % (h["num"], h["line"]))
        L.append(" (d) 解析記錄數=%s csv=%s" % (r["d"]["n_guidance_records_parsed"],
                                             json.dumps(r["d"]["csv"], ensure_ascii=False)))
        for x in r["d"]["parsed_revenue_raise"]:
            L.append("     收入上調[%s] 舊=%s-%s 新=%s-%s 中點變化=%s raise=%s 舊值缺=%s 舊值來源=%s"
                     % (x["period"], x["old_lo"], x["old_hi"], x["new_lo"], x["new_hi"],
                        x["mid_change"], x["raise_flag"], x["old_missing"], x["old_src"]))
            L.append("       原句:%s" % x["sentence"][:260])
        L.append(" (e) " + json.dumps({k: e.get(k) for k in E_FIELDS}, ensure_ascii=False))
        p = pop.get(r["acc"], {})
        L.append("     入池三閘:加速稿內命中=%s 加速pp=%s g0稿內=%s 指引收入上調=%s 歷史季度T1前公開=%s 稿內收入標記=%s"
                 % (p.get("accel_text_hit"), p.get("accel_pp_text"), p.get("rev_g0_text"),
                    p.get("guide_rev_raise"), p.get("hist_quarters_public_by_t1"),
                    p.get("signal_rev_in_text")))
        L.append("     排除欄位字串(整欄拼成,非單一原因):%s" % p.get("exclusion_reason"))
    with open(os.path.join(C.OUT, "part1_digest.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("→", os.path.join(C.OUT, "part1_digest.txt"), len(L), "lines")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
