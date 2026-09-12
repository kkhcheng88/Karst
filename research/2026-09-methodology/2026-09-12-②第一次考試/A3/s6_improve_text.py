# -*- coding: utf-8 -*-
"""KARST-226 票 A″(v1.2)第六步:稿內數字匹配 + 指引解析器 + 入口池。

執行口徑 v1.2 第 3、4、5、6、7 項 + 補一/補三。逐事件(有全文者)做四件事:

一、**訊號季收入須在稿內**(第 3 項):把 XBRL 首報訊號季收入與 EX-99.1 全文做數字匹配
    (處理 thousand/million/billion、逗號、小數、括號;容差 0.5%);找不到 → `signal_rev_in_text=假`
    不入池(記數)。稿內那個值就是「稿內訊號季收入」(`rev_signal_text`),下游加速用它。

二、**指引解析器**(第 4 項,取代正則):抽每條指引句的指標/期間/舊新上下限與中點/單位/
    幣種/GAAP/一次性提及;上調 = 新中點 > 舊中點且下限不降;取不到舊值但明文 raise 者標
    `old_missing`。**入池只認 metric=revenue 的 raise_flag**(或收入與盈利同上);
    純 EPS/盈利上調記 `guidance_raise_eps_only`。

三、**適用性 F**(第 5 項):(a) 剔 SIC 60–64、67;(b) 標準收入標籤且訊號前 ≥8 季連續
    (s3 已判,`applicability_reason` 三類);(c) 併購閘已於 s4 判。

四、**公開改善**(第 7 項 + 補一):收入加速(≥2pp,稿內訊號季 vs XBRL 去年同季 −
    XBRL 上一季增速)**或**可核實的收入指引上調;至少一項。
    另加 補二/補三 兩道資料閘:`release_timing=intraday` 不入池;
    `hist_quarters_public_by_t1=假`(歷史季度來源申報日晚於 T1)不入池。

輸出:`cache/population_improvement.parquet`、`cache/guidance_parsed.jsonl`。
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DOCS = HERE.parent / "A" / "edgar_cache"

TOL = 0.005                     # 訊號季收入匹配容差 0.5%
ACCEL_MIN_PP = 2.0

# ---------------- 稿內數字匹配 ----------------
NUM_RX = re.compile(r"(?<![\w.])(\$?\s?\(?\d[\d,]*(?:\.\d+)?\)?)\s*"
                    r"(thousand|thousands|million|millions|billion|billions|mn|bn|[MBK])?\b")
MULT = {"thousand": 1e3, "thousands": 1e3, "k": 1e3,
        "million": 1e6, "millions": 1e6, "mn": 1e6, "m": 1e6,
        "billion": 1e9, "billions": 1e9, "bn": 1e9, "b": 1e9}


def _num(s: str):
    s = s.strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace("$", "").replace(",", "").strip()
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def find_rev_in_text(text: str, v: float):
    """在全文找與 v 相符的數字(容差 0.5%)。回 (值[美元], 位置, 用了單位字, 上下文有收入字)。

    允許文本以千/百萬/十億為單位書寫(即 v 除以 10^3/10^6/10^9 亦算命中)。
    """
    if not v or v <= 0:
        return None
    best = None
    for m in NUM_RX.finditer(text):
        raw = _num(m.group(1))
        if raw is None or raw == 0:
            continue
        unit = (m.group(2) or "").lower()
        cands = []
        if unit in MULT:
            cands.append((raw * MULT[unit], True))
        for sc in (1.0, 1e3, 1e6, 1e9):      # 文本可能已按千/百萬/十億書寫
            cands.append((raw * sc, False))
        for c, used_unit in cands:
            if c > 0 and abs(c / v - 1.0) <= TOL:
                ctx = text[max(0, m.start() - 260):m.end() + 120]
                has_rev = bool(REV_CTX.search(ctx))
                rec = (c, m.start(), used_unit, has_rev)
                if best is None or (has_rev and not best[3]):
                    best = rec
                if has_rev:
                    return best
    return best


REV_CTX = re.compile(r"(?i)\b(revenue|revenues|net sales|total sales|sales)\b")

# ---------------- 指引解析器 ----------------
GUIDE_KW = re.compile(r"(?i)\b(guidance|outlook|expects?|anticipates?|forecasts?|"
                      r"projects?|estimates?|targets?)\b")
FY_KW = re.compile(r"(?i)(fiscal (?:year|20\d\d)|full[- ]year|\bfy\s?\d{0,4}\b|year ending)")
Q_KW = re.compile(r"(?i)(fiscal (?:quarter|Q\d)|next quarter|first quarter|second quarter|"
                  r"third quarter|fourth quarter|\bq[1-4]\b|three months ending)")
REV_KW = re.compile(r"(?i)\b(revenue|revenues|net sales|total sales|sales)\b")
EPS_KW = re.compile(r"(?i)(\beps\b|earnings per share|per (?:diluted )?share)")
OI_KW = re.compile(r"(?i)(operating income|operating profit|income from operations|"
                   r"operating margin)")
CF_KW = re.compile(r"(?i)(cash flow|free cash flow|adjusted ebitda|\bebitda\b|"
                   r"capital expenditure)")
RAISE_KW = re.compile(r"(?i)\b(rais\w+|increas\w+|up from|hike|higher than|"
                      r"improve[sd]? (?:our|the) (?:guidance|outlook))")
CUT_KW = re.compile(r"(?i)\b(lower\w*|reduc\w*|cut\w*|decreas\w*|withdraw\w*|"
                    r"suspend\w*|no longer)\b")
NEG_KW = re.compile(r"(?i)\b(unchanged|reaffirm\w*|maintain\w*|no change|in[-\s]line with|"
                    r"identical to|same as|consistent with)\b")
PREV_KW = re.compile(r"(?i)(previous(?:ly)?|prior|earlier|last quarter's) (?:guidance|outlook|"
                     r"estimate|expectation)|compared (?:to|with) (?:our|the) (?:previous|prior)")
FX_KW = re.compile(r"(?i)(foreign exchange|currency|\bfx\b|exchange rate)")
ACQ_KW = re.compile(r"(?i)(acquisition|acquired|merger|divestiture|business combination)")
SHARE_KW = re.compile(r"(?i)(share count|share repurchase|buyback|dilution|diluted shares)")
ONETIME_KW = re.compile(r"(?i)(one[- ]time|non[- ]recurring|restructuring|impairment|"
                        r"litigation|tax benefit)")
# 區間:兩個數之間可以夾一個單位字(「$275 million to $280 million」是最常見寫法)
RANGE_RX = re.compile(r"(?:between\s+)?\$?\s*(\d[\d,]*(?:\.\d+)?)\s*"
                      r"(?:thousand|millions?|billions?|mn|bn|[MBK])?\s*"
                      r"(?:to|through|[-–—])\s*\$?\s*(\d[\d,]*(?:\.\d+)?)", re.I)
FROM_RX = re.compile(r"(?i)\bfrom\s+(?:a range of\s+|approximately\s+|about\s+)?"
                     r"\$?\s*(\d[\d,]*(?:\.\d+)?)\s*"
                     r"(?:thousand|millions?|billions?|mn|bn|[MBK])?\s*"
                     r"(?:to|through|[-–—])\s*\$?\s*(\d[\d,]*(?:\.\d+)?)")
UNIT_IN_RX = re.compile(r"(?i)\b(in|expressed in)\s+(thousands|millions|billions)\b")
GAAP_KW = re.compile(r"(?i)\b(gaap|non-gaap|adjusted|non gaap)\b")


def split_sentences(text: str) -> list[str]:
    """逐句切。稿內單行換行亦作句界(申報文本一行一句,合併會把不相干的數字拉進同一句)。"""
    t = re.sub(r"[ \t ]+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+|\n+", t)
    return [p.strip() for p in parts if p and p.strip()]


def text_scale(text: str) -> str:
    m = UNIT_IN_RX.search(text[:4000])
    if not m:
        m = UNIT_IN_RX.search(text)
    return m.group(2).lower() if m else ""


METRICS = (("revenue", REV_KW), ("eps", EPS_KW),
           ("operating_income", OI_KW), ("cash_flow", CF_KW))
YEAR_RX = re.compile(r"^(?:19|20)\d\d$")
UNIT_WORD_RX = re.compile(r"(?i)\b(thousand|thousands|millions?|billions?|mn|bn)\b")
GUIDE_WORD_RX = re.compile(r"(?i)\b(guidance|outlook)\b")


def _looks_monetary(s: str, start: int, end: int, pct_ok: bool) -> bool:
    """值要像金額(有 $ 或單位字),或像百分比且句中明講 guidance/outlook。"""
    if "$" in s[max(0, start - 4):end]:
        return True
    if UNIT_WORD_RX.search(s[end:end + 28]):
        return True
    return bool(pct_ok and "%" in s[max(0, start - 10):end + 14])


def _range_near(s: str, kw_pos: int):
    """回傳 (距離, lo, hi, 命中物件) —— 取離該指標字眼最近的區間。"""
    best = None
    for m in RANGE_RX.finditer(s):
        if re.search(r"(?i)\bfrom\s*$", s[max(0, m.start() - 7):m.start()]):
            continue          # 「raised ... from <舊> to <新>」:from 之後那個是舊值
        lo, hi = _num(m.group(1)), _num(m.group(2))
        if lo is None or hi is None:
            continue
        if hi < lo:
            lo, hi = hi, lo
        d = abs(m.start() - kw_pos)
        if best is None or d < best[0]:
            best = (d, lo, hi, m)
    return best


def _num_near(s: str, kw_pos: int):
    """回傳 (距離, 值, 起點) —— 取離該指標字眼最近的數(剔除年份)。

    年份只在「無貨幣符號、無單位字」時才剔(「$2,024 million」是真金額)。
    """
    best = None
    for m in NUM_RX.finditer(s):
        tok = m.group(1) or ""
        raw = re.sub(r"[^\d.]", "", tok)     # NUM_RX 會吞掉緊隨的逗號,先清乾淨
        v = _num(tok)
        if v is None:
            continue
        if YEAR_RX.match(raw) and "$" not in tok and not (m.group(2) or ""):
            continue
        d = abs(m.start() - kw_pos)
        if best is None or d < best[0]:
            best = (d, v, m.start())
    return best


def parse_guidance(text: str) -> list[dict]:
    """回傳逐句、逐指標的指引紀錄。

    每句可出多於一筆(一句同時講收入與 EPS 時各出一筆),取數一律取**離該指標字眼最近**
    的區間/數字,避免把「Fiscal Year 2020」之類的年份或別的指標的數當成新指引值。
    """
    out = []
    sentences = split_sentences(text)
    for i, s in enumerate(sentences):
        if len(s) > 900 or not GUIDE_KW.search(s):
            continue
        period = ("FY" if FY_KW.search(s) else "next_quarter" if Q_KW.search(s) else "")
        if not period:
            continue
        scale = ""
        ms = UNIT_IN_RX.search(s)
        if ms:
            scale = ms.group(2).lower()
        for metric, krx in METRICS:
            km = krx.search(s)
            if not km:
                continue
            rng = _range_near(s, km.start())
            single = False
            new_end = km.start()
            pct_ok = bool(GUIDE_WORD_RX.search(s))
            if rng:
                _d, lo, hi, mo = rng
                if _d > 120 or not _looks_monetary(s, mo.start(), mo.end(), pct_ok):
                    continue
                new_end = mo.end()
            else:
                nn = _num_near(s, km.start())
                if nn is None:
                    continue
                _d, v, npos = nn
                if _d > 120 or not _looks_monetary(s, npos, npos + 1, pct_ok):
                    continue
                lo = hi = v
                single = True
                new_end = npos + 1
            # 舊值(一):「raised X to <新> from <舊>」——句內 from 子句
            old_lo = old_hi = None
            old_src = ""
            fr = FROM_RX.search(s, new_end - 1)
            if fr is not None and fr.start() >= new_end - 1:
                a, b = _num(fr.group(1)), _num(fr.group(2))
                if (a is not None and b is not None
                        and not (YEAR_RX.match(str(int(a))) and YEAR_RX.match(str(int(b))))):
                    old_lo, old_hi = (a, b) if a <= b else (b, a)
                    old_src = "同句from"
            # 舊值(二):同句 previous/prior 子句之後的區間
            pk = PREV_KW.search(s)
            if old_lo is None and pk:
                r2 = _range_near(s, pk.start() + 200)
                if r2 is not None and r2[3].start() > pk.start():
                    old_lo, old_hi = r2[1], r2[2]
                    old_src = "同句"
                else:
                    n2 = _num_near(s, pk.start() + 200)
                    if n2 is not None and n2[2] > pk.start():
                        old_lo = old_hi = n2[1]
                        old_src = "同句"
            if old_lo is None:
                for s2 in sentences[max(0, i - 6):i]:
                    if PREV_KW.search(s2) and (REV_KW.search(s2) if metric == "revenue" else True):
                        r2 = RANGE_RX.search(s2)
                        if r2:
                            old_lo, old_hi = _num(r2.group(1)), _num(r2.group(2))
                            if old_lo is not None and old_hi is not None:
                                if old_hi < old_lo:
                                    old_lo, old_hi = old_hi, old_lo
                                old_src = "前句"
                                break
                        n2 = _num_near(s2, 0)
                        if n2 is not None:
                            old_lo = old_hi = n2[1]
                            old_src = "前句單值"
                            break
            new_mid = (lo + hi) / 2.0
            old_missing = old_lo is None
            if not old_missing:
                old_mid = (old_lo + old_hi) / 2.0
                raise_flag = (new_mid > old_mid) and (lo >= old_lo)
                mid_change = new_mid - old_mid
            else:
                old_mid = mid_change = None
                # 舊值缺時,「明示上調」要在指引字眼附近才算(「increased traffic」之類不算)
                rk = RAISE_KW.search(s)
                near_guide = False
                while rk is not None:
                    seg = s[max(0, rk.start() - 45):rk.end() + 70]
                    if GUIDE_WORD_RX.search(seg) or GUIDE_KW.search(seg):
                        near_guide = True
                        break
                    rk = RAISE_KW.search(s, rk.end())
                raise_flag = (near_guide and not CUT_KW.search(s)
                              and not NEG_KW.search(s))
            out.append({
                "metric": metric, "period": period,
                "old_lo": old_lo, "old_hi": old_hi, "old_mid": old_mid,
                "new_lo": lo, "new_hi": hi, "new_mid": new_mid,
                "is_single_point": bool(single),
                "unit": scale, "currency": "USD" if "$" in s else "",
                "gaap_flag": "non-gaap" if re.search(r"(?i)non[- ]gaap", s)
                else ("gaap" if GAAP_KW.search(s) else ""),
                "mentions": "|".join(k for k, rx in
                                     (("fx", FX_KW), ("acquisition", ACQ_KW),
                                      ("share_count", SHARE_KW), ("one_time", ONETIME_KW))
                                     if rx.search(s)),
                "mid_change": mid_change, "raise_flag": bool(raise_flag),
                "old_missing": bool(old_missing), "old_src": old_src,
                "sentence": s[:600],
            })
    return out


def main() -> None:
    df = pd.read_parquet(CACHE / "population_base.parquet")
    df = df.merge(pd.read_parquet(CACHE / "thresholds_window.parquet"),
                  on="accessionNumber", how="left")
    df["accnd"] = df["accessionNumber"].str.replace("-", "")
    t1 = pd.to_datetime(df["reaction_date"], errors="coerce")

    # ---------- 逐事件讀文本 ----------
    need = df[df["accnd"].map(lambda a: (DOCS / ("%s__EX991.txt.gz" % a)).exists())]
    print("有全文的事件:%d" % len(need), flush=True)
    rev_text, in_text, gparse = {}, {}, {}
    n = 0
    for r in need.itertuples(index=False):
        p = DOCS / ("%s__EX991.txt.gz" % r.accnd)
        try:
            with gzip.open(p, "rt", encoding="utf-8") as f:
                t = f.read()
        except OSError:
            rev_text[r.accessionNumber] = None
            in_text[r.accessionNumber] = False
            gparse[r.accessionNumber] = []
            continue
        v = getattr(r, "rev_signal_xbrl", None)
        got = find_rev_in_text(t, float(v)) if (v is not None and not pd.isna(v)) else None
        rev_text[r.accessionNumber] = got[0] if got else None
        in_text[r.accessionNumber] = bool(got)
        gparse[r.accessionNumber] = parse_guidance(t)
        n += 1
        if n % 2000 == 0:
            print("  ...%d/%d" % (n, len(need)), flush=True)

    df["rev_signal_text"] = df["accessionNumber"].map(rev_text)
    df["signal_rev_in_text"] = df["accessionNumber"].map(in_text).fillna(False).astype(bool)

    # ---------- 指引彙總 ----------
    g_rev_raise, g_eps_only, g_any, g_n = {}, {}, {}, {}
    with (CACHE / "guidance_parsed.jsonl").open("w", encoding="utf-8") as f:
        for r in need.itertuples(index=False):
            recs = gparse.get(r.accessionNumber, [])
            for rec in recs:
                f.write(json.dumps({"accessionNumber": r.accessionNumber,
                                    "year": None if pd.isna(getattr(r, "year", None))
                                    else int(getattr(r, "year")), **rec},
                                   ensure_ascii=False) + "\n")
            rev_raise = any(x["metric"] == "revenue" and x["raise_flag"] for x in recs)
            eps_up = any(x["metric"] in ("eps", "operating_income", "cash_flow")
                         and x["raise_flag"] for x in recs)
            g_rev_raise[r.accessionNumber] = rev_raise
            g_eps_only[r.accessionNumber] = bool(eps_up and not rev_raise)
            g_any[r.accessionNumber] = bool(recs)
            g_n[r.accessionNumber] = len(recs)
    df["guide_rev_raise"] = df["accessionNumber"].map(g_rev_raise).fillna(False).astype(bool)
    df["guidance_raise_eps_only"] = df["accessionNumber"].map(g_eps_only).fillna(False).astype(bool)
    df["guide_any"] = df["accessionNumber"].map(g_any).fillna(False).astype(bool)
    df["guide_n_sent"] = df["accessionNumber"].map(g_n).fillna(0).astype(int)

    # ---------- 加速(稿內訊號季 vs XBRL 去年同季;上一季增速用 XBRL)----------
    with_text = df["rev_signal_text"].notna() & df["rev_yago_xbrl"].notna() \
        & (df["rev_yago_xbrl"] > 0) & df["rev_prev_q_yoy"].notna()
    g0_text = pd.Series(float("nan"), index=df.index)
    g0_text[with_text] = (df.loc[with_text, "rev_signal_text"]
                          / df.loc[with_text, "rev_yago_xbrl"] - 1.0)
    df["rev_g0_text"] = g0_text
    df["accel_pp_text"] = (g0_text - df["rev_prev_q_yoy"]) * 100.0
    df["accel_text_hit"] = (df["accel_pp_text"] >= ACCEL_MIN_PP).fillna(False)

    # ---------- 補三:歷史季度須於 T1 前申報 ----------
    hf = pd.to_datetime(df["hist_src_latest_filed"], errors="coerce")
    df["hist_quarters_public_by_t1"] = (hf.notna() & (hf <= t1)).fillna(False)
    df.loc[hf.isna(), "hist_quarters_public_by_t1"] = False

    # ---------- 標籤(第 6 項;不作閘)----------
    df["g0_negative"] = (df["rev_g0_text"] < 0).fillna(False)
    df["rev_ttm"] = df["rev_ttm_xbrl"]           # 最近四季收入(訊號季結尾;來自 XBRL)
    df["both_signals"] = (df["accel_text_hit"] & df["guide_rev_raise"])
    df["above_200dma"] = df["above_200dma"]
    df["rs6_top20"] = False
    for y, g in df[df["in_universe"] == 1].groupby("year"):
        if g["rs6"].notna().sum() >= 5:
            cut = g["rs6"].quantile(0.80)
            df.loc[g.index[g["rs6"] >= cut], "rs6_top20"] = True
    df["rel_sic2_ge5"] = (df["rel_sic2"] >= 0.05).fillna(False)
    df["accel_2q"] = (df["accel_pp_text"] >= ACCEL_MIN_PP).fillna(False)
    # surprise_c2 = 稿內 g0 − 訊號前四季按年增速平均(控制 C2)
    df["surprise_c2"] = df["rev_g0_text"] - df["prev4_yoy_mean"]

    # ---------- 入池判 ----------
    inu = (df["in_universe"] == 1) & df["in_pool_window"]
    df["excl_no_text"] = (~df["signal_rev_in_text"]).astype(int)
    df["excl_intraday"] = (df["release_timing"] == "intraday").astype(int)
    df["excl_earlier_release"] = df["suspect_earlier_release"].fillna(0).astype(int)
    df["excl_hist_not_public"] = (~df["hist_quarters_public_by_t1"]).astype(int)
    df["excl_applicability"] = df["applicability_reason"].fillna("").ne("").astype(int)
    sic2 = df["sic2"].fillna("")
    df["excl_financial_sic"] = sic2.isin([str(x) for x in range(60, 65)] + ["67"]).astype(int)

    df["pass_thr"] = ((df["rel_spy"] >= df["thr_p90"]) & (df["rel_sic2"] > 0)).fillna(False)
    df["pass_thr95"] = ((df["rel_spy"] >= df["thr_p95"]) & (df["rel_sic2"] > 0)).fillna(False)
    df["pass_thr80"] = ((df["rel_spy"] >= df["thr_p80"]) & (df["rel_sic2"] > 0)).fillna(False)

    df["improvement_type"] = "無"
    df.loc[df["accel_text_hit"] & ~df["guide_rev_raise"], "improvement_type"] = "加速"
    df.loc[~df["accel_text_hit"] & df["guide_rev_raise"], "improvement_type"] = "指引"
    df.loc[df["accel_text_hit"] & df["guide_rev_raise"], "improvement_type"] = "兩者"
    df.loc[~df["accel_text_hit"] & ~df["guide_rev_raise"]
           & df["guidance_raise_eps_only"], "improvement_type"] = "只EPS上調"

    df["pass_p90"] = (df["pass_thr"] & df["improvement_type"].isin(["加速", "指引", "兩者"])
                      ).astype(int)
    df["pass_p95"] = (df["pass_thr95"] & df["improvement_type"].isin(["加速", "指引", "兩者"])
                      ).astype(int)
    df["pass_p80"] = (df["pass_thr80"] & df["improvement_type"].isin(["加速", "指引", "兩者"])
                      ).astype(int)

    # 入池 = 宇宙內(pool 窗)且全數不予剔;2014 只作暖身窗口(in_pool_window=False)不入池
    df["entry_pool"] = ((df["pass_p90"] == 1) & (df["in_universe"] == 1)
                        & (df["in_pool_window"])
                        & (df["excl_no_text"] == 0) & (df["excl_intraday"] == 0)
                        & (df["excl_earlier_release"] == 0)
                        & (df["excl_hist_not_public"] == 0)
                        & (df["excl_applicability"] == 0)
                        & (df["excl_financial_sic"] == 0)).astype(int)

    df.to_parquet(CACHE / "population_improvement.parquet", index=False)

    nu = df[inu]
    cand = nu[nu["pass_thr"] == True]                                   # noqa: E712
    print("宇宙內(pool 窗):%d;過第 90 百分位且同業正:%d" % (len(nu), len(cand)))
    print("  其中:無稿內訊號季收入 %d;intraday %d;疑更早公開 %d;歷史季度未於 T1 前 %d;"
          "適用性剔 %d;金融 SIC 剔 %d"
          % (int(cand["excl_no_text"].sum()), int(cand["excl_intraday"].sum()),
             int(cand["excl_earlier_release"].sum()), int(cand["excl_hist_not_public"].sum()),
             int(cand["excl_applicability"].sum()), int(cand["excl_financial_sic"].sum())))
    print("入口池:%d" % int(df["entry_pool"].sum()))
    print("  組成:", df[df["entry_pool"] == 1]["improvement_type"].value_counts().to_dict())
    print("  桶:", df[df["entry_pool"] == 1]["bucket"].value_counts().to_dict())
    print("→", CACHE / "population_improvement.parquet")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
