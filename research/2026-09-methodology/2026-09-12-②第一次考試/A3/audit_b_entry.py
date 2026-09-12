# -*- coding: utf-8 -*-
"""KARST-230 第一部:入口抽查 20 宗(四類各 5)逐宗五項。
(a) 反應日與公開時間 (b) 窗口門檻無前視 (c) 訊號季收入在稿內 (d) 指引解析 (e) 適用性與併購排除
只讀;輸出 audit_out/part1.json。全檔不列公司名或代號。
"""
import json, os, re, sys
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audit_common as C

ROOT = r"C:\projects\Karst"
SPY = pd.read_csv(os.path.join(ROOT, "data", "prices", "spy_daily.csv"), parse_dates=["date"])
SPY = SPY.sort_values("date").reset_index(drop=True)
SD = SPY["date"].values.astype("datetime64[D]")

_MON = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
        "december": 12, "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
        "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12}
MONTHS = "|".join(sorted(_MON, key=len, reverse=True))
DATE_RE = re.compile(r"\b(%s)\.?\s+(\d{1,2}),?\s+(20\d\d)\b" % MONTHS, re.I)


def parse_dt(s):
    if s in (None, "", "NaT"):
        return None
    return pd.Timestamp(str(s)[:10])


def next_trading_day(d):
    i = int(np.searchsorted(SD, np.datetime64(d, "D"), side="right"))
    return None if i >= len(SD) else pd.Timestamp(SD[i])


def is_trading_day(d):
    return bool((SD == np.datetime64(d, "D")).any())


def headline_date(lines, filing):
    """EX-99.1 稿頭日期:首 2,500 字元內第一個『Month DD, YYYY』且日期合理
    (年份 2005–2026、不遲於申報日、與申報日相距 ≤ 45 日);找不到放寬到首 8,000 字元。
    回傳 (日期, 行號, 行片段)。獨立重寫,不呼叫建池者的函式。"""
    if filing is None:
        return None, None, ""
    LIM = (2500, 8000)
    for lim in LIM:
        pos = 0
        for i, ln in enumerate(lines, 1):
            if pos > lim:
                break
            for m in DATE_RE.finditer(ln):
                try:
                    t = pd.Timestamp("%s %s, %s" % (m.group(1).capitalize(), m.group(2), m.group(3)))
                except Exception:
                    continue
                if not (2005 <= t.year <= 2026):
                    continue
                lag = (filing - t).days
                if lag < 0 or lag > 45:
                    continue
                return t, i, ln.strip()[:200]
            pos += len(ln) + 1
    return None, None, ""


def norm_timing(rt):
    """把建池者的細分標籤歸成四類主類。"""
    if rt in ("pre_market", "pre_market_inferred", "pre_market_8k"):
        return "pre_market"
    if rt in ("after_close", "after_close_8k", "prior_day_after_close"):
        return "after_close" if rt != "prior_day_after_close" else "prior_day_after_close"
    return rt


def main():
    s = C.load_sample()
    rows = [(g, r) for g, rs in s["groups"].items() for r in rs]
    accs = [r["accessionNumber"] for _, r in rows]
    pop = C.load_population(set(accs))
    guid = {}
    with open(os.path.join(C.HERE, "cache", "guidance_parsed.jsonl"), encoding="utf-8") as f:
        for ln in f:
            r = json.loads(ln)
            if r["accessionNumber"] in set(accs):
                guid.setdefault(r["accessionNumber"], []).append(r)
    merger = pd.read_parquet(os.path.join(C.HERE, "cache", "merger_scan.parquet"))
    merger = merger.set_index("accessionNumber")
    mtext = pd.read_parquet(os.path.join(C.HERE, "cache", "merger_text.parquet"))
    mtext = mtext.set_index("accessionNumber")

    # 宇宙事件(重算門檻用)
    uni = pd.read_csv(os.path.join(C.HERE, "population.csv.gz"), usecols=[
        "accessionNumber", "in_universe", "rel_spy", "reaction_date"],
        encoding="utf-8-sig", low_memory=False)
    uni = uni[(uni["in_universe"] == 1) & uni["rel_spy"].notna()
              & uni["reaction_date"].notna()]
    URD = pd.to_datetime(uni["reaction_date"]).values.astype("datetime64[D]")
    URV = uni["rel_spy"].to_numpy(float)
    order = np.argsort(URD)
    URD, URV = URD[order], URV[order]

    prev_cut = None
    out = []
    import price_cache
    px = price_cache.get()

    for g, r in rows:
        a = r["accessionNumber"]
        p = pop.get(a, {})
        rec = {"group": g, "acc": a, "cik": r["cik"], "year": r["year"]}
        # ---------------- (a) 反應日與公開時間
        local = a.replace("-", "") + "__EX991.txt.gz"
        txt, lines = "", []
        try:
            txt, lines = C.edgar_text(local)
        except FileNotFoundError:
            rec["a_textfile"] = "查不到:" + local
        filing = parse_dt(p.get("filingDate"))
        hd, hd_line, hd_snip = headline_date(lines, filing)
        acc_utc = p.get("acceptanceDateTime", "")
        t0_et = p.get("t0_et", "")
        rt = p.get("release_timing", "")
        react = parse_dt(p.get("reaction_date"))
        # 期望公開時段
        exp_rt, exp_reason = None, ""
        if hd is not None and filing is not None and hd < filing:
            exp_rt = "prior_day_after_close"
            exp_reason = "稿頭日 %s < 申報日 %s" % (hd.date(), filing.date())
        elif filing is not None and (hd is None or hd == filing):
            # 稿頭日 = 申報日,或稿內查不到稿頭日 → 只按 8-K 受理時間判
            hh, mm = (t0_et[11:16].split(":") if len(t0_et) >= 16 else ("", ""))
            if hh.isdigit():
                mins = int(hh) * 60 + int(mm)
                if mins < 9 * 60 + 30:
                    exp_rt, exp_reason = "pre_market", "受理 %s 早於 09:30" % t0_et[11:16]
                elif mins >= 16 * 60:
                    exp_rt, exp_reason = "after_close", "受理 %s 不早於 16:00" % t0_et[11:16]
                else:
                    exp_rt, exp_reason = "intraday?", "受理 %s 在 09:30–16:00(需跳空檢定)" % t0_et[11:16]
        elif hd is not None and filing is not None and hd > filing:
            exp_rt, exp_reason = "稿頭晚於申報日?", "%s > %s" % (hd.date(), filing.date())
        # 期望反應日
        exp_react = None
        if exp_rt == "prior_day_after_close" and hd is not None:
            exp_react = next_trading_day(hd)
        elif exp_rt in ("pre_market", "intraday?"):
            exp_react = filing if is_trading_day(filing) else next_trading_day(filing)
        elif exp_rt == "after_close":
            exp_react = next_trading_day(filing)
        # 舊價與前一日絕對報酬(自算)
        eid = "CIK" + p.get("cik", "")
        got = px.get(eid) or px.get(p.get("cik", ""))
        pdr = None
        if got is not None:
            dts, adj = got[0], got[1]
            pd_ = parse_dt(p.get("prev_date"))
            if pd_ is not None:
                i = int(np.searchsorted(dts, np.datetime64(pd_, "D")))
                if i > 0 and i < len(dts) and dts[i] == np.datetime64(pd_, "D"):
                    pdr = abs(float(adj[i] / adj[i - 1] - 1.0))
        rec["a"] = {
            "headline_date": None if hd is None else str(hd.date()),
            "headline_line": hd_line, "headline_masked": C.mask_text(hd_snip)[:60],
            "filingDate": p.get("filingDate"), "acceptance_utc": acc_utc,
            "t0_et": t0_et, "t0_source": p.get("t0_source"),
            "release_timing": rt, "reaction_date": p.get("reaction_date"),
            "expected_timing": exp_rt, "expected_reason": exp_reason,
            "expected_reaction_date": None if exp_react is None else str(exp_react.date()),
            "timing_match": (norm_timing(rt) == norm_timing(exp_rt)) if exp_rt else None,
            "reaction_match": (str(exp_react.date()) == str(react.date())) if (exp_react is not None and react is not None) else None,
            "prior_day_abs_ret_csv": p.get("prior_day_abs_ret"),
            "prior_day_abs_ret_recomputed": pdr,
            "prior_day_abs_delta": (None if (pdr is None or p.get("prior_day_abs_ret") in (None, ""))
                                    else abs(pdr - float(p["prior_day_abs_ret"]))),
        }
        # ---------------- (b) 窗口門檻
        if react is not None:
            d = np.datetime64(react, "D")
            pos = np.searchsorted(SD, d)
            if pos >= len(SD) or SD[pos] != d:
                pos = int(np.searchsorted(SD, d, side="right"))
            lo = SD[max(0, pos - 252)]
            i0 = int(np.searchsorted(URD, lo, side="left"))
            i1 = int(np.searchsorted(URD, d, side="left"))
            n252, p90_252 = i1 - i0, (None if i1 <= i0 else float(np.percentile(URV[i0:i1], 90)))
            win, n, p90 = 252, n252, p90_252
            if n252 < 300:
                lo2 = SD[max(0, pos - 504)]
                j0 = int(np.searchsorted(URD, lo2, side="left"))
                if i1 - j0 > n252:
                    win, n, p90 = 504, i1 - j0, float(np.percentile(URV[j0:i1], 90))
            latest = None if i1 <= (i0 if win == 252 else j0) else str(URD[i1 - 1])
            rec["b"] = {
                "thr_win_days_csv": p.get("thr_win_days"), "thr_n_csv": p.get("thr_n"),
                "thr_p90_csv": p.get("thr_p90"),
                "recomputed_win": win, "recomputed_n": n,
                "recomputed_p90": p90,
                "p90_delta": (None if (p90 is None or p.get("thr_p90") in (None, ""))
                              else abs(p90 - float(p["thr_p90"]))),
                "latest_window_event_reaction": latest,
                "latest_before_own": (latest is not None and latest < str(react.date())),
                "insufficient": n < 300,
                "rel_spy": p.get("rel_spy"), "pass_p90": p.get("pass_p90"),
            }
        # ---------------- (c) 訊號季收入在稿內
        v = C.num(p.get("rev_signal_text"))
        hits = C.find_number_lines(lines, v) if (lines and v) else []
        # 取最短/最相關的 3 條
        rec["c"] = {
            "rev_signal_text": v, "rev_signal_xbrl": C.num(p.get("rev_signal_xbrl")),
            "signal_rev_in_text_csv": p.get("signal_rev_in_text"),
            "n_line_hits": len(hits),
            "line_hits": [{"line": i, "num": t} for i, t in hits[:4]],
            "rel_diff_text_vs_xbrl": (None if (v in (None, 0) or C.num(p.get("rev_signal_xbrl")) in (None, 0))
                                      else abs(v / C.num(p["rev_signal_xbrl"]) - 1)),
            "signal_q_end": p.get("signal_q_end"),
        }
        # ---------------- (d) 指引
        gr = guid.get(a, [])
        rev_up = [x for x in gr if x["metric"] == "revenue" and x.get("raise_flag")]
        rec["d"] = {
            "n_guidance_records_parsed": len(gr),
            "csv": {k: p.get(k) for k in [
                "guide_rev_raise", "guidance_metric", "guidance_period", "guidance_old_lo",
                "guidance_old_hi", "guidance_new_lo", "guidance_new_hi",
                "guidance_mid_change", "guidance_raise_flag", "guidance_old_missing",
                "guidance_eps_only", "guidance_raise_eps_only", "guidance_n_records",
                "improvement_type", "accel_text_hit"]},
            "parsed_revenue_raise": [{
                "period": x["period"], "old_lo": x["old_lo"], "old_hi": x["old_hi"],
                "old_mid": x["old_mid"], "new_lo": x["new_lo"], "new_hi": x["new_hi"],
                "new_mid": x["new_mid"], "mid_change": x["mid_change"],
                "raise_flag": x["raise_flag"], "old_missing": x["old_missing"],
                "old_src": x["old_src"], "sentence": C.mask_text(x["sentence"][:400])} for x in rev_up[:3]],
            "parsed_any": [{
                "metric": x["metric"], "period": x["period"], "raise_flag": x["raise_flag"],
                "new_lo": x["new_lo"], "new_hi": x["new_hi"], "old_lo": x["old_lo"],
                "old_hi": x["old_hi"], "old_missing": x["old_missing"],
                "sentence": C.mask_text(x["sentence"][:300])} for x in gr[:4]],
        }
        # ---------------- (e) 適用性與併購
        items = ""
        if a in merger.index:
            it = merger.loc[a, "items"]
            items = it if isinstance(it, str) else str(it)
        mw = ""
        if a in mtext.index:
            mw = str(mtext.loc[a, "has_merger_words"])
        rec["e"] = {
            "sic": p.get("sic"), "sic2": p.get("sic2"),
            "rev_tag_used": p.get("rev_tag_used"), "n_consec_q": p.get("n_consec_q"),
            "applicability_reason": p.get("applicability_reason"),
            "excl_financial_sic": p.get("excl_financial_sic"),
            "excl_applicability": p.get("excl_applicability"),
            "excl_merger_2_01": p.get("excl_merger_2_01"),
            "excl_merger_1_01": p.get("excl_merger_1_01"),
            "excl_merger_1_01_old": p.get("excl_merger_1_01_old"),
            "excl_spac": p.get("excl_spac"),
            "excl_listed_lt_12m": p.get("excl_listed_lt_12m"),
            "excl_volume": p.get("excl_volume"),
            "items_same_day": items, "merger_words": mw,
            "merger_text_pending": p.get("merger_text_pending"),
            "exclusion_reason": p.get("exclusion_reason"),
            "in_universe": p.get("in_universe"), "entry_pool": p.get("entry_pool"),
            "improvement_type": p.get("improvement_type"),
            "excl_no_text": p.get("excl_no_text"),
            "excl_intraday": p.get("excl_intraday"),
            "excl_earlier_release": p.get("excl_earlier_release"),
            "excl_hist_not_public": p.get("excl_hist_not_public"),
        }
        out.append(rec)
        print("done", g, a)
    with open(os.path.join(C.OUT, "part1.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, default=str)
    print("→", os.path.join(C.OUT, "part1.json"))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
