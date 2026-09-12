# -*- coding: utf-8 -*-
"""KARST-230 獨立核查共用工具。只讀;不寫 A3 既有檔。
規矩:輸出永不列公司名或代號(name / ticker 欄一律不取)。
"""
import csv, gzip, json, os, sys

csv.field_size_limit(10 ** 9)

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)                      # .../2026-09-12-②第一次考試
EDGAR = os.path.join(PARENT, "A", "edgar_cache")
OUT = os.path.join(HERE, "audit_out")
os.makedirs(OUT, exist_ok=True)

# 只取核查用欄;刻意不含 name / ticker
POOL_COLS = [
    "accessionNumber", "cik", "name", "form", "sic", "sic2", "bucket", "fiscal_quarter",
    "reportDate", "filingDate", "acceptanceDateTime", "t0_et", "t0_after16", "t0_weekend",
    "t0_source", "release_timing", "dateline_used", "dateline", "reaction_date",
    "prev_date", "t1_prev_close_adj", "t1_close_adj", "t2_date", "ret_reaction",
    "spy_ret_same_day", "rel_spy", "rel_sic2", "prior_day_abs_ret", "turnover_median_60d",
    "signal_q_end", "rev_g0", "rev_g0_text", "rev_prev_q_yoy", "accel_pp", "accel_pp_text",
    "accel_hit", "accel_text_hit", "rev_signal_text", "rev_signal_xbrl",
    "signal_rev_in_text", "guide_rev_raise", "guidance_raise_eps_only", "guide_any",
    "guide_n_sent", "guidance_n_records", "guidance_metric", "guidance_period",
    "guidance_old_lo", "guidance_old_hi", "guidance_new_lo", "guidance_new_hi",
    "guidance_mid_change", "guidance_raise_flag", "guidance_old_missing", "guidance_eps_only",
    "xbrl_status", "rev_tag_used", "n_consec_q", "hist_quarters_public_by_t1",
    "hist_src_latest_filed", "prev4_yoy_mean", "improvement_type", "g0_negative",
    "excl_no_price", "excl_volume", "excl_listed_lt_12m", "excl_spac", "excl_merger_2_01",
    "excl_merger_1_01", "excl_merger_1_01_old", "excl_going_concern", "excl_no_text",
    "excl_intraday", "excl_earlier_release", "excl_hist_not_public", "excl_applicability",
    "excl_financial_sic", "applicability_reason", "suspect_earlier_release",
    "merger_text_pending", "text_stage_checked", "exclusion_reason", "in_universe",
    "in_pool_window", "thr_win_days", "thr_n", "thr_p90", "thr_p95", "thr_p80",
    "thr_insufficient", "pass_p90", "pass_p95", "pass_p80", "entry_pool",
    "repeat_company_flag", "adr_flag", "covid_window", "year",
]


def load_pool():
    """entry_pool.csv(1,802 宗)逐列 dict,key = accessionNumber。"""
    out = {}
    with open(os.path.join(HERE, "entry_pool.csv"), encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            out[r["accessionNumber"]] = r
    return out


def load_pool_header():
    with open(os.path.join(HERE, "entry_pool.csv"), encoding="utf-8-sig", newline="") as f:
        return next(csv.reader(f))


def load_population(want_accs=None):
    """population.csv 逐列;want_accs 給定時只留這些 accession(省記憶)。"""
    out = {}
    with open(os.path.join(HERE, "population.csv"), encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            a = r["accessionNumber"]
            if want_accs is None or a in want_accs:
                out[a] = r
    return out


def load_sample():
    with open(os.path.join(HERE, "cache", "audit_sample.json"), encoding="utf-8") as f:
        return json.load(f)


def load_picks_md():
    """由 md 表解出主清單與後備清單(只取非人名欄)。"""
    main, back = [], []
    with open(os.path.join(HERE, "picks_before_results.md"), encoding="utf-8") as f:
        cur = None
        for ln in f:
            s = ln.strip()
            if s.startswith("## 主清單"):
                cur = main
                continue
            if s.startswith("## 後備清單"):
                cur = back
                continue
            if s.startswith("## "):
                cur = None
                continue
            if cur is None or not s.startswith("|"):
                continue
            c = [x.strip() for x in s.strip("|").split("|")]
            if len(c) < 15 or not c[0].isdigit():
                continue
            main_i = 0
            row = {
                "row": c[0], "event_id": c[1], "year": c[2], "bucket": c[3], "cik": c[4],
                "accessionNumber": c[5], "filingDate": c[6], "reaction_date": c[7],
                "release_timing": c[8], "sic2": c[9], "improvement_type": c[10],
                "g0_text": c[11], "accel_pp": c[12], "rel_spy": c[13], "rel_sic2": c[14],
            }
            cur.append(row)
    return main, back


def edgar_text(local_gz):
    """讀 A/edgar_cache/<local_gz>,回傳 (行 list, 全文)。"""
    p = os.path.join(EDGAR, local_gz)
    with gzip.open(p, "rt", encoding="utf-8", errors="replace") as f:
        txt = f.read()
    return txt, txt.splitlines()


def find_number_lines(lines, value, tol=0.005):
    """在行內找 value 的各種寫法;回傳 [(行號, 命中數字片段)]。
    片段只保留數字本身與緊接單位的 billion/million/thousand——不留任何字詞,
    免把公司名或產品名帶進核查檔。"""
    import re
    hits = []
    if value in (None, ""):
        return hits
    v = float(value)
    cands = set()
    for scale, unit in ((1e9, ["billion", "b"]), (1e6, ["million", "m"])):
        x = v / scale
        for dec in range(0, 3):
            cands.add(f"{x:,.{dec}f}")
            cands.add(f"{x:.{dec}f}")
    x = v / 1000.0
    for dec in range(0, 2):
        cands.add(f"{x:,.{dec}f}")
    cands = {c for c in cands if c and c not in ("0", "0.0")}
    UNIT = ("billion", "million", "thousand")
    for i, ln in enumerate(lines, 1):
        low = ln.lower()
        for c in sorted(cands, key=len, reverse=True):
            m = re.search(r"(?<![\d.,])" + re.escape(c) + r"(?![\d])", ln)
            if not m:
                continue
            ctx = low[max(0, m.start() - 40): m.end() + 40]
            if not any(u in ctx for u in ("billion", "million", "$", "revenue", "net sales",
                                          "net revenues")):
                continue
            tail = ln[m.end():m.end() + 20].strip().lower().split()
            unit = tail[0] if tail and tail[0].rstrip(".,") in UNIT else ""
            snippet = (("$" if "$" in ln[max(0, m.start() - 2):m.start()] else "") +
                       m.group(0) + (" " + unit if unit else ""))
            hits.append((i, snippet))
            break
    return hits


def num(v):
    if v in (None, "", "True", "False"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def b(v):
    return str(v).strip() in ("1", "True", "true")


BUCKETS = {
    "能源原材料公用": "01 02 03 04 05 06 07 08 09 10 11 12 13 14 29 40 41 42 43 44 45 46 47 49".split(),
    "醫療": "28 38 80 81".split(),
    "科技與軟件": "36 48 73 87".split(),
    "金融地產": "60 61 62 63 64 65 66 67 68 69".split(),
    "消費與零售": "20 21 22 23 52 53 54 55 56 57 58 59 70 72 78 79".split(),
    "製造與工業": "15 16 17 24 25 26 27 30 31 32 33 34 35 37 39 50 51".split(),
}


def bucket_of_sic2(sic2):
    s = str(sic2).zfill(2)
    for k, v in BUCKETS.items():
        if s in v:
            return k
    return "其他"


# ---------------------------------------------------------------------------
# 文字去名:核查檔只留數字與財務詞,任何帶字母的字(公司名、代號、產品名、
# 人名)一律以 x 遮蔽。准用詞是一份固定的單位/財務詞表;不在表中就遮。
# 目的:核查檔要能核數字與行號,但全檔不得出現公司名或代號。
# ---------------------------------------------------------------------------
ALLOW = set("""
billion million thousand percent percentage quarter quarters fiscal year years
revenue revenues sales net total gross operating income margin margins cash flow flows
free contract contracts adjusted gaap eps share shares diluted earnings
guidance outlook expect expects expected expectation approximately
increase increased increases increasing raise raised raises raising
up down from to by for the a an of in on at as is are was were be been
and or but with without versus vs compared comparison prior previous
growth grew grow report reported reports reporting announce announced announces
results result period full half first second third fourth
range over than most least about above below higher lower
we our us its it their this that these those
""".split())
_PUNCT_KEEP = set("0123456789$%.,:;()-–—/\\*•\'\"?[]&+=<>!|")


def mask_text(s):
    """把帶字母的字(三個字母以上且不在准用表)換成同長度的 x,保留數字、標點與單位詞。"""
    if not s:
        return s
    out = []
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if ch.isalpha() and ch.isascii():
            j = i
            while j < n and s[j].isalpha() and s[j].isascii():
                j += 1
            w = s[i:j]
            if len(w) <= 2 or w.lower() in ALLOW:
                out.append(w)
            else:
                out.append("x" * len(w))
            i = j
        else:
            out.append(ch)
            i += 1
    return "".join(out)
