# -*- coding: utf-8 -*-
"""KARST-237 ②第一次考試 票 D:兩臂(DeepSeek／Opus)各 84 宗機械版 對 T1 後經營結果 與 三條機械基準。

評分規則照 `執行口徑——②第一次考試-v1.md` 第一節與第四節、v1.2 修訂頁「判斷層雙臂」,
分組照 `B/主考試執行備忘.md` 事前列明的各項。**結論段留白(由主 agent 寫)。**

只讀:
  B/ds/rows/E0*.csv、B/opus/rows/E0*.csv(機械版 28 欄,QUOTE_ALL)
  A3/packets/<event_id>.json(1_事件識別、2_觸發資料、3_截止前文件、4_財務數列)
  A3/controls_operating.csv(C1/C2/C3;C3 以 quarters 欄重算的 g0_quarters 取代)
  A3/population.csv(找 Q+1／Q+2 業績事件 → EX-99.1)
  data/sec/companyfacts/CIK*.json.gz(T1 後首報值;體例照 A3/finlib_fixed.py)
  A/edgar_cache/(EX-99.1 文本;缺者單線程 3 請求/秒補抓)

禁讀:任何卡的人讀版(B/ds/卡-*、B/opus/卡-*)、B/void/、試跑/ 的卡。不列公司名或代號。
"""
from __future__ import annotations

import csv
import gzip
import html
import json
import os
import re
import statistics
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(r"C:\projects\Karst\research\2026-09-methodology\2026-09-12-②第一次考試")
CACHE = ROOT / "A" / "edgar_cache"
A3 = ROOT / "A3"
OUT_MD = ROOT / "B" / "評分——第一次考試.md"
OUT_CSV = ROOT / "B" / "評分.csv"

sys.path.insert(0, str(A3))
import finlib_fixed as FX  # noqa: E402

ARMS = [("ds", "DeepSeek 臂"), ("opus", "Opus 臂")]
LABEL = dict(ARMS)

# ---- 事前列明的分組(來源見檔頭與 B/主考試執行備忘.md) ----
ENTRY_DEFECT = {"E006", "E050", "E026", "E064", "E002"}       # 備忘 9/12/21/28/30 項
SERIES_FIX = {"E017", "E022", "E024"}                          # 備忘 17 項(KARST-236 重建)
IDENTITY_LEAK = {"E005", "E011", "E024", "E036", "E039",
                 "E060", "E071", "E082", "E053"}               # 備忘 19 + 25 項
TAG_SCOPE = {"E025", "E033", "E038", "E039", "E047"}           # 備忘 21 項
SCALE_FIX = {"E003"}                                           # 備忘 5 項
COVID_Q = {"2020Q2", "2020Q3", "2020Q4", "2021Q1", "2021Q2"}   # 備忘 26 項

NOUN = re.compile(r"(?i)\b(guidance|outlook)\b")
VERB = re.compile(r"(?i)\b(lower(?:ed|s|ing)?|reduce[ds]?|reducing|cut|cuts)\b")
DC_RE = re.compile(r"discontinued operation", re.I)
PROFIT_KW = ("盈利", "毛利", "EPS", "利潤率")
REV_KW = ("收入", "營收", "銷售")

DEFECT_GROUPS = [
    ("entry_defect 入口缺陷", "grp_entry_defect"),
    ("series 修正三宗", "grp_series_fix"),
    ("identity_leak 身分洩漏", "grp_identity_leak"),
    ("tag 口徑差五宗", "grp_tag_scope"),
    ("pred 尺度違規", "grp_scale_fix"),
    ("門檻決定型", "grp_mech"),
    ("收購驅動", "grp_acq"),
    ("商品型(SIC 10–14／29)", "grp_commodity"),
    ("contamination 標有影響／同向", "grp_contam"),
    ("scope_break 級距跳變", "grp_scope_break"),
    ("初步業績稿(preliminary)", "grp_prelim"),
]


def add_months(d: date, n: int) -> date:
    y, m = d.year, d.month + n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    day = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return d.replace(year=y, month=m, day=day)


def nearest(series: dict, target: date, tol: int = 16) -> str | None:
    c = [(abs((date.fromisoformat(k) - target).days), k) for k in series]
    c = [x for x in c if x[0] <= tol]
    return min(c)[1] if c else None


def med(v):
    return statistics.median(v) if v else None


def mean(v):
    return statistics.mean(v) if v else None


def trimmed(pairs, cap=2.0):
    """兩端皆截尾於 ±cap 之後的平均絕對誤差。pairs = [(預測, 實際)]。"""
    if not pairs:
        return None
    c = lambda x: min(cap, max(-cap, x))          # noqa: E731
    return statistics.mean([abs(c(p) - c(a)) for p, a in pairs])


# ------------------------------------------------------------------ 機械版
def load_row(arm: str, eid: str) -> dict:
    raw = (ROOT / "B" / arm / "rows" / (eid + ".csv")).read_text(encoding="utf-8").splitlines()
    header = next(csv.reader([raw[0]]))
    f = next(csv.reader([raw[1]]))
    assert len(header) == len(f) == 28, (arm, eid, len(header), len(f))
    d = dict(zip(header, f))
    scale = False
    for k in ("pred_g2_point", "pred_g2_lo", "pred_g2_hi",
              "pred_g4_point", "pred_g4_lo", "pred_g4_hi"):
        try:
            v = float(d[k])
        except ValueError:
            d[k] = None
            continue
        if abs(v) > 5:                       # 備忘 5 項:百分比寫法
            v /= 100.0
            scale = True
        d[k] = v
    d["_scale_fixed"] = scale
    return d


# ------------------------------------------------------------------ EX-99.1
UA = {"User-Agent": "Karst research kaho@example.com"}
_LAST = [0.0]


def _get(url: str, timeout: int = 60) -> bytes:
    wait = _LAST[0] + 1.0 / 3.0 - time.time()
    if wait > 0:
        time.sleep(wait)
    _LAST[0] = time.time()
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def strip_html(raw: bytes) -> str:
    t = raw.decode("utf-8", "ignore")
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    t = re.sub(r"(?is)<br\s*/?>", "\n", t)
    t = re.sub(r"(?is)</(p|div|tr|h[1-6]|li)>", "\n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\xa0]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t


EXH = re.compile(r"(?i)(ex[-_]?99[-_.]?1|ex991|exhibit99)")


def ex991_by_acc(cik: str, acc: str):
    nodash = acc.replace("-", "")
    p = CACHE / (nodash + "__EX991.txt.gz")
    if p.exists():
        try:
            return gzip.open(p, "rt", encoding="utf-8").read(), "cache"
        except OSError:
            pass
    base = "https://www.sec.gov/Archives/edgar/data/%d/%s" % (int(cik), nodash)
    doc = ""
    try:                                    # 先試 index.json(檔名清單,最穩)
        idx = json.loads(_get(base + "/index.json", timeout=60).decode("utf-8"))
        for it in idx.get("directory", {}).get("item", []):
            nm = it.get("name", "")
            if nm.lower().endswith(".htm") and EXH.search(nm):
                doc = nm
                break
    except Exception:                                          # noqa: BLE001
        pass
    if not doc:
        try:
            page = _get(base + "/" + acc + "-index.html").decode("utf-8", "ignore")
        except Exception as e:                                 # noqa: BLE001
            return None, "索引抓取失敗:%s" % type(e).__name__
        for tr in re.findall(r"(?is)<tr.*?</tr>", page):
            href = re.search(r'href="([^"]+)"', tr)
            if not href:
                continue
            tds = re.findall(r"(?is)<td[^>]*>\s*([^<]*?)\s*</td>", tr)
            if any(t.strip().upper().replace(" ", "") in ("EX-99.1", "EX-99") for t in tds):
                doc = href.group(1).rsplit("/", 1)[-1]
                break
    if not doc:
        return None, "該申報無 EX-99.1 附件"
    try:
        txt = strip_html(_get(base + "/" + doc, timeout=120))
    except Exception as e:                                    # noqa: BLE001
        return None, "附件抓取失敗:%s" % type(e).__name__
    with gzip.open(p, "wt", encoding="utf-8") as f:
        f.write(txt)
    return txt, "新抓"


def submissions_8k(cik: str, lo: str, hi: str) -> list[dict]:
    """該司 filings(含 older 分頁)內 8-K 且 filingDate 落 [lo,hi]。"""
    out = []
    try:
        d = json.loads(_get("https://data.sec.gov/submissions/CIK%s.json" % cik,
                            timeout=60).decode("utf-8"))
    except Exception:                                          # noqa: BLE001
        return out
    packs = [d.get("filings", {}).get("recent", {})]
    for f in d.get("filings", {}).get("files", []):
        try:
            packs.append(json.loads(_get(
                "https://data.sec.gov/submissions/" + f["name"], timeout=60).decode("utf-8")))
        except Exception:                                      # noqa: BLE001
            pass
    for pk in packs:
        forms = pk.get("form", []) or []
        for i, fm in enumerate(forms):
            if fm != "8-K":
                continue
            fd = pk.get("filingDate", [])[i]
            if lo <= fd <= hi:
                out.append({"accessionNumber": pk.get("accessionNumber", [])[i],
                            "filingDate": fd})
    return sorted(out, key=lambda r: r["filingDate"])


def guidance_down(txt: str, win: int = 130) -> list[str]:
    """執行口徑 v1 的機械判準:lower／reduce／cut 與 guidance／outlook 相距 ≤ win 字元。"""
    out = []
    for m in NOUN.finditer(txt):
        seg = txt[max(0, m.start() - win): m.end() + win]
        if VERB.search(seg):
            out.append(re.sub(r"\s+", " ", txt[max(0, m.start() - 90): m.end() + 90]).strip())
    return out


RESULTS_RE = re.compile(r"(?i)(financial results|quarter(ly)? results|announces.{0,40}results)")


def pick_release(cik: str, cand_acc: list[str], limit: int = 4):
    """在候選 8-K 之中取業績稿 EX-99.1:優先正文自稱業績稿者,否則取首份有文本的。"""
    first = None
    tried = 0
    for cand in cand_acc[:limit]:
        t, h = ex991_by_acc(cik, cand)
        tried += 1
        if t is None:
            last = h
            continue
        if first is None:
            first = (t, h, cand)
        if RESULTS_RE.search(t[:6000]):
            return t, h, cand, tried
    if first:
        return first[0], first[1], first[2], tried
    return None, last if cand_acc else "無候選", None, tried


# ------------------------------------------------------------------ 主流程
def build():
    ids = sorted(f[:-5] for f in os.listdir(A3 / "packets") if f.endswith(".json"))
    pop = list(csv.DictReader(open(A3 / "population.csv", encoding="utf-8-sig")))
    by_cik: dict[str, list[dict]] = {}
    for r in pop:
        by_cik.setdefault(r["cik"], []).append(r)
    ctrl = {r["event_id"]: r for r in csv.DictReader(
        open(A3 / "controls_operating.csv", encoding="utf-8-sig"))}

    out, notes = [], []
    for eid in ids:
        pk = json.load(open(A3 / "packets" / (eid + ".json"), encoding="utf-8"))
        kk = list(pk.keys())
        idn = pk[[k for k in kk if k.startswith("1_")][0]]
        trig = pk[[k for k in kk if k.startswith("2_")][0]]
        docs = pk[[k for k in kk if k.startswith("3_")][0]]
        fin = pk[[k for k in kk if k.startswith("4_")][0]]
        cik = pk["cik"]
        t1 = idn["signal_date_反應日"]
        sqe = fin["signal_q_end"]
        quarters = fin["quarters"]

        # --- 訊號季稿內值 ÷ 去年同季 quarters 值 − 1 = g0_quarters
        sig = quarters[-1]
        sig_rev = sig.get("revenue_ex991")
        if sig_rev is None:
            sig_rev = sig.get("revenue")
        prior = quarters[-5].get("revenue") if len(quarters) >= 5 else None
        g0q = (sig_rev / prior - 1.0) if (sig_rev and prior) else None
        g0h = fin.get("g0_signal_q_yoy")

        # --- T1 後實際(首報值,與 quarters 欄同口徑)
        facts = FX.load_facts(cik)
        rec = FX.rec_full(facts, FX.REV_TAGS) if facts else {}
        ser = {k: v["value"] for k, v in rec.items()}
        sqd = date.fromisoformat(sqe)
        ends = [nearest(ser, add_months(sqd, 3 * k)) for k in (1, 2, 3, 4)]
        yoys = [None if e is None else FX.yoy(ser, e) for e in ends]
        base_ends = [None if e is None else FX.yoy_end(ser, e) for e in ends]
        m1 = statistics.mean(yoys[:2]) if all(y is not None for y in yoys[:2]) else None
        if all(y is not None for y in yoys):
            m2 = statistics.mean(yoys)
        else:
            m2 = None
            if m1 is not None:
                notes.append("%s:Q+3／Q+4 未成熟,M2 不入(標未成熟)" % eid)

        # --- 指引下修(Q+1／Q+2 業績稿 EX-99.1)
        gd_all, gd_det = [], {}
        gd_strict_any = False
        for k in (0, 1):
            qe = ends[k]
            tag = "Q+%d" % (k + 1)
            if qe is None:
                gd_det[tag] = "無此季"
                continue
            cands = sorted([r for r in by_cik.get(cik, [])
                            if r["signal_q_end"] == qe and r["reaction_date"] > t1],
                           key=lambda r: r["reaction_date"])
            if not cands:
                hi = add_months(date.fromisoformat(qe), 4).isoformat()
                cands = sorted([r for r in by_cik.get(cik, [])
                                if qe <= r["reaction_date"] <= hi],
                               key=lambda r: r["reaction_date"])
            cand_acc = [r["accessionNumber"] for r in cands]
            if not cand_acc:                      # 母體期後 → EDGAR 補抓
                cand_acc = [r["accessionNumber"] for r in submissions_8k(
                    cik, qe, add_months(date.fromisoformat(qe), 4).isoformat())]
            if not cand_acc:
                gd_det[tag] = "查不到(無業績事件)"
                continue
            txt, how, acc, tried = pick_release(cik, cand_acc)
            if txt is None:
                gd_det[tag] = "查不到(%s;試 %d 份)" % (how, tried)
                continue
            hits = guidance_down(txt)
            gd_strict = guidance_down(txt, 60)
            gd_all += hits
            if hits:
                gd_det[tag] = "有下修(%s;%s)" % (acc, how)
            else:
                gd_det[tag] = "無(%s;%s)" % (acc, how)
            if gd_strict:
                gd_strict_any = True
        if gd_all:
            guide = "有下修"
        elif all(v.startswith("無") for v in gd_det.values()):
            guide = "無"
        else:
            guide = "查不到"

        # --- 分組標籤
        tr = trig.get("earnings_call_transcript") or {}
        has_tr = bool(tr.get("n_segments")) if isinstance(tr, dict) else False
        prior_g = trig.get("prior_release_guidance") or {}
        has_prior_g = (bool(prior_g.get("n_guidance_records"))
                       or bool(prior_g.get("guidance_sentences"))
                       ) if isinstance(prior_g, dict) else False
        prelim = bool(trig.get("preliminary_release"))
        sic = int(pk.get("sic") or 0)
        commodity = 10 <= sic // 100 <= 14 or sic // 100 == 29
        revs = [q.get("revenue") for q in quarters]
        ratios = [revs[k] / revs[k - 1] for k in range(1, len(revs))
                  if revs[k] and revs[k - 1]]
        jump = 0.0
        if ratios:
            mm = statistics.median(ratios)
            jump = max(abs(r - mm) for r in ratios)
        dc = False
        for key in docs:
            nm = (docs[key] or {}).get("local_gz")
            p = CACHE / nm if nm else None
            if p and p.exists():
                try:
                    if DC_RE.search(gzip.open(p, "rt", encoding="utf-8", errors="ignore").read()):
                        dc = True
                except OSError:
                    pass
        scope_break = jump > 0.25 and dc

        c1 = ctrl.get(eid, {})
        c1v = float(c1["C1_implied_yoy"]) if c1.get("C1_implied_yoy") else None
        c2v = float(c1["C2_prev4_avg_yoy"]) if c1.get("C2_prev4_avg_yoy") else None

        e = {"event_id": eid, "cik": cik, "t1": t1, "signal_q_end": sqe,
             "fiscal_quarter": idn["fiscal_quarter"], "sic2": pk.get("sic2"),
             "bucket": pk.get("bucket"), "g0_quarters": g0q, "g0_head": g0h,
             "M1": m1, "M2": m2, "q_ends": ends, "q_yoys": yoys, "base_ends": base_ends,
             "guide_down": guide, "guide_det": gd_det,
             "has_transcript": has_tr, "has_prior_guidance": has_prior_g,
             "preliminary_release": prelim, "commodity": commodity,
             "scope_break": scope_break, "scope_jump": round(jump, 4),
             "C1": c1v, "C2": c2v}
        prof = revk = False
        for a, _l in ARMS:
            r = load_row(a, eid)
            g2p, g2lo, g2hi = r["pred_g2_point"], r["pred_g2_lo"], r["pred_g2_hi"]
            g4p, g4lo, g4hi = r["pred_g4_point"], r["pred_g4_lo"], r["pred_g4_hi"]
            t = r["improvement_text"] or ""
            prof = prof or any(k in t for k in PROFIT_KW)
            revk = revk or any(k in t for k in REV_KW)
            e["%s_persist" % a] = r["persistence_overall"]
            e["%s_pcont" % a] = float(r["p_continue"])
            e["%s_driver" % a] = r["top_driver_type"]
            e["%s_contam" % a] = r["contamination_note"]
            e["%s_scale" % a] = r["_scale_fixed"]
            for nm, v in (("g2p", g2p), ("g2lo", g2lo), ("g2hi", g2hi),
                          ("g4p", g4p), ("g4lo", g4lo), ("g4hi", g4hi)):
                e["%s_pred_%s" % (a, nm)] = v
            e["%s_err_g2" % a] = None if (m1 is None or g2p is None) else abs(g2p - m1)
            e["%s_err_g4" % a] = None if (m2 is None or g4p is None) else abs(g4p - m2)
            e["%s_hit_g2" % a] = (None if (m1 is None or g2lo is None or g2hi is None)
                                  else (g2lo <= m1 <= g2hi))
            e["%s_hit_g4" % a] = (None if (m2 is None or g4lo is None or g4hi is None)
                                  else (g4lo <= m2 <= g4hi))
            e["%s_trim_g2" % a] = (None if (m1 is None or g2p is None) else (g2p, m1))
            e["%s_trim_g4" % a] = (None if (m2 is None or g4p is None) else (g4p, m2))
        e["improve_where"] = ("組合" if (prof and revk) else "盈利" if prof
                              else "收入" if revk else "其他")
        e["driver_acq"] = all(e["%s_driver" % a] == "收購" for a, _l in ARMS)
        e["contam"] = any(("有影響" in e["%s_contam" % a] or "同向" in e["%s_contam" % a])
                          for a, _l in ARMS)

        def persist(thr):
            if m1 is None or g0q is None:
                return None
            t = g0q if g0q < 0 else thr * g0q
            return (m1 >= t) and (guide != "有下修")

        e["guide_down_strict"] = "有下修" if gd_strict_any else "無"
        e["persist_08"] = persist(0.8)
        e["persist_07"] = persist(0.7)
        e["persist_09"] = persist(0.9)
        e["persist_alt"] = (None if (m1 is None or g0q is None)
                            else (m1 >= g0q and guide != "有下修"))
        e["persist_08_nodn"] = (None if (m1 is None or g0q is None)
                                else m1 >= (g0q if g0q < 0 else 0.8 * g0q))
        e["persist_08_strict"] = (None if (m1 is None or g0q is None)
                                  else (m1 >= (g0q if g0q < 0 else 0.8 * g0q)
                                        and not gd_strict_any))
        e["persist4"] = (None if (m2 is None or g0q is None) else
                         sum(1 for y in yoys if y is not None and
                             y >= (g0q if g0q < 0 else 0.8 * g0q)) >= 3)
        e["c2_predicts"] = (None if (g0q is None or c2v is None)
                            else c2v >= (g0q if g0q < 0 else 0.8 * g0q))
        e["err_c2"] = None if (m1 is None or c2v is None) else abs(c2v - m1)
        e["err_c1"] = None if (m1 is None or c1v is None) else abs(c1v - m1)
        e["err_c3"] = None if (m1 is None or g0q is None) else abs(g0q - m1)
        e["trim_c2"] = None if (m1 is None or c2v is None) else (c2v, m1)
        e["trim_c1"] = None if (m1 is None or c1v is None) else (c1v, m1)
        e["trim_c3"] = None if (m1 is None or g0q is None) else (g0q, m1)

        e["grp_entry_defect"] = eid in ENTRY_DEFECT
        e["grp_series_fix"] = eid in SERIES_FIX
        e["grp_identity_leak"] = eid in IDENTITY_LEAK
        e["grp_tag_scope"] = eid in TAG_SCOPE
        e["grp_scale_fix"] = any(e["%s_scale" % a] for a, _l in ARMS)
        e["grp_mech"] = (g0q is not None and (g0q <= 0.02 or g0q >= 0.6
                                              or idn["fiscal_quarter"] in COVID_Q))
        e["grp_has_c1"] = c1v is not None
        e["grp_has_transcript"] = has_tr
        e["grp_acq"] = e["driver_acq"]
        e["grp_commodity"] = commodity
        e["grp_contam"] = e["contam"]
        e["grp_scope_break"] = scope_break
        e["grp_prelim"] = prelim
        e["g0_band"] = ("缺" if g0q is None else "≤0" if g0q <= 0 else
                        "0–0.3" if g0q < 0.3 else ">0.3")
        out.append(e)
    return out, notes


# ------------------------------------------------------------------ 統計
def mae_stats(rows, err_key, trim_key):
    v = [r[err_key] for r in rows if r.get(err_key) is not None]
    tr = [r[trim_key] for r in rows if r.get(trim_key) is not None]
    return {"n": len(v), "med": med(v), "mean": mean(v), "trim": trimmed(tr)}


def hit_rate(rows, key):
    v = [r[key] for r in rows if r.get(key) is not None]
    return (sum(1 for x in v if x), len(v)) if v else (0, 0)


def auc(scores, labels):
    pos = [s for s, l in zip(scores, labels) if l]
    neg = [s for s, l in zip(scores, labels) if not l]
    if not pos or not neg:
        return None
    tot = 0.0
    for a in pos:
        for b in neg:
            tot += 1.0 if a > b else 0.5 if a == b else 0.0
    return tot / (len(pos) * len(neg))


def spearman(x, y):
    def rank(v):
        s = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(s):
            j = i
            while j + 1 < len(s) and v[s[j + 1]] == v[s[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[s[k]] = avg
            i = j + 1
        return r
    if len(x) < 3:
        return None
    rx, ry = rank(x), rank(y)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = sum((a - mx) ** 2 for a in rx) ** 0.5
    dy = sum((b - my) ** 2 for b in ry) ** 0.5
    return None if dx * dy == 0 else num / (dx * dy)


def pct(x, dash="—", sign=True):
    if x is None:
        return dash
    return ("%+.1f%%" if sign else "%.1f%%") % (100 * x)


def f3(x, dash="—"):
    return dash if x is None else "%.3f" % x


def yn(b):
    return "—" if b is None else "是" if b else "否"


# ------------------------------------------------------------------ 輸出
CSV_FIELDS = (
    ["event_id", "arm", "g0_quarters", "g0_head", "M1", "M2", "guide_down",
     "persist_08", "persist_07", "persist_09", "persist_alt", "persist4",
     "persist_08_nodn", "persist_08_strict", "guide_down_strict",
     "pred_g2_point", "pred_g2_lo", "pred_g2_hi", "pred_g4_point", "pred_g4_lo",
     "pred_g4_hi", "err_g2", "hit_g2", "err_g4", "hit_g4",
     "C1", "C2", "C3", "err_c1", "err_c2", "err_c3", "c2_predicts",
     "persistence_overall", "p_continue", "top_driver_type", "scale_fixed",
     "improve_where", "driver_acq", "contamination", "has_transcript",
     "has_prior_guidance", "preliminary_release", "commodity", "scope_break",
     "tag_scope", "identity_leak", "entry_defect", "series_fix", "mech_threshold",
     "g0_band", "sic2", "bucket", "fiscal_quarter", "t1", "q1_end", "q2_end",
     "q3_end", "q4_end", "yoy1", "yoy2", "yoy3", "yoy4", "guide_Q1", "guide_Q2"])


def write_csv(rows):
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for e in rows:
            for a, _l in ARMS:
                w.writerow({
                    "event_id": e["event_id"], "arm": a,
                    "g0_quarters": e["g0_quarters"], "g0_head": e["g0_head"],
                    "M1": e["M1"], "M2": e["M2"], "guide_down": e["guide_down"],
                    "persist_08": e["persist_08"], "persist_07": e["persist_07"],
                    "persist_09": e["persist_09"], "persist_alt": e["persist_alt"],
                    "persist4": e["persist4"],
                    "persist_08_nodn": e["persist_08_nodn"],
                    "persist_08_strict": e["persist_08_strict"],
                    "guide_down_strict": e["guide_down_strict"],
                    "pred_g2_point": e["%s_pred_g2p" % a],
                    "pred_g2_lo": e["%s_pred_g2lo" % a],
                    "pred_g2_hi": e["%s_pred_g2hi" % a],
                    "pred_g4_point": e["%s_pred_g4p" % a],
                    "pred_g4_lo": e["%s_pred_g4lo" % a],
                    "pred_g4_hi": e["%s_pred_g4hi" % a],
                    "err_g2": e["%s_err_g2" % a], "hit_g2": e["%s_hit_g2" % a],
                    "err_g4": e["%s_err_g4" % a], "hit_g4": e["%s_hit_g4" % a],
                    "C1": e["C1"], "C2": e["C2"], "C3": e["g0_quarters"],
                    "err_c1": e["err_c1"], "err_c2": e["err_c2"], "err_c3": e["err_c3"],
                    "c2_predicts": e["c2_predicts"],
                    "persistence_overall": e["%s_persist" % a],
                    "p_continue": e["%s_pcont" % a],
                    "top_driver_type": e["%s_driver" % a],
                    "scale_fixed": e["%s_scale" % a],
                    "improve_where": e["improve_where"], "driver_acq": e["driver_acq"],
                    "contamination": e["contam"],
                    "has_transcript": e["has_transcript"],
                    "has_prior_guidance": e["has_prior_guidance"],
                    "preliminary_release": e["preliminary_release"],
                    "commodity": e["commodity"], "scope_break": e["scope_break"],
                    "tag_scope": e["grp_tag_scope"], "identity_leak": e["grp_identity_leak"],
                    "entry_defect": e["grp_entry_defect"], "series_fix": e["grp_series_fix"],
                    "mech_threshold": e["grp_mech"], "g0_band": e["g0_band"],
                    "sic2": e["sic2"], "bucket": e["bucket"],
                    "fiscal_quarter": e["fiscal_quarter"], "t1": e["t1"],
                    "q1_end": e["q_ends"][0], "q2_end": e["q_ends"][1],
                    "q3_end": e["q_ends"][2], "q4_end": e["q_ends"][3],
                    "yoy1": e["q_yoys"][0], "yoy2": e["q_yoys"][1],
                    "yoy3": e["q_yoys"][2], "yoy4": e["q_yoys"][3],
                    "guide_Q1": e["guide_det"].get("Q+1", ""),
                    "guide_Q2": e["guide_det"].get("Q+2", "")})


def main():
    rows, notes = build()
    write_csv(rows)
    idm = {e["event_id"]: e for e in rows}
    print("events", len(rows), "csv rows", len(rows) * 2)

    L = []
    A = L.append
    A("# 評分——②第一次考試(兩臂 84 宗機械版 對 T1 後經營結果)")
    A("")
    A("> KARST-237。評分規則照 `執行口徑——②第一次考試-v1.md` 第一節與第四節、"
      "`執行口徑——②第一次考試-v1.2(修訂頁).md`;分組照 `B/主考試執行備忘.md` 事前列明各項。"
      "評分者只讀兩臂**機械版**與其後財報,未讀任何卡的人讀版。"
      "**不列公司名或代號;結論段留白。**")
    A("")
    A("口徑:T1 後實際收入取 `data/sec/companyfacts` 首報值(跨收入 tag 取最早申報者,"
      "缺格以累計差分補;體例照 `A3/finlib_fixed.py`),與取證包 `4_財務數列` quarters 欄同口徑。"
      "門檻 g0 一律以 quarters 欄收入定義重算(`g0_quarters` = 訊號季**稿內值** ÷ 去年同季 "
      "quarters 值 − 1),取證包包頭 g0 只作對照。")
    A("")

    # ---------- 表一:主表
    A("## 表一 主表:每臂與 C1／C2／C3 對 M1 的絕對誤差")
    A("")
    A("| 預測者 | 期限 | n | MAE 中位 | MAE 平均 | MAE 截尾平均(±200%) | 區間命中 |")
    A("|---|---|---|---|---|---|---|")
    for a, lab in ARMS:
        s = mae_stats(rows, "%s_err_g2" % a, "%s_trim_g2" % a)
        h, hn = hit_rate(rows, "%s_hit_g2" % a)
        A("| %s | 兩季(M1) | %d | %s | %s | %s | %d/%d |" % (
            lab, s["n"], pct(s["med"]), pct(s["mean"]), pct(s["trim"]), h, hn))
        s4 = mae_stats(rows, "%s_err_g4" % a, "%s_trim_g4" % a)
        h4, hn4 = hit_rate(rows, "%s_hit_g4" % a)
        A("| %s | 四季(M2) | %d | %s | %s | %s | %d/%d |" % (
            lab, s4["n"], pct(s4["med"]), pct(s4["mean"]), pct(s4["trim"]), h4, hn4))
    for nm, lab in (("c1", "C1 指引隱含(有值者)"), ("c2", "C2 趨勢延續"),
                    ("c3", "C3 訊號持續(=g0_quarters)")):
        s = mae_stats(rows, "err_%s" % nm, "trim_%s" % nm)
        A("| %s | 兩季(M1) | %d | %s | %s | %s | — |" % (
            lab, s["n"], pct(s["med"]), pct(s["mean"]), pct(s["trim"])))
    A("")
    # C1 子樣本:同一批事件上兩臂的 MAE
    ctrl = {r["event_id"]: r for r in csv.DictReader(
        open(A3 / "controls_operating.csv", encoding="utf-8-sig"))}
    sub = [e for e in rows if e["C1"] is not None]
    A("C1 只有 %d 宗有值。同一批 %d 宗上並列:DeepSeek 臂中位 %s、Opus 臂中位 %s、C1 中位 %s。"
      % (len(sub), len(sub),
         pct(mae_stats(sub, "ds_err_g2", "ds_trim_g2")["med"]),
         pct(mae_stats(sub, "opus_err_g2", "opus_trim_g2")["med"]),
         pct(mae_stats(sub, "err_c1", "trim_c1")["med"])))
    A("")
    A("**C1 逐宗值(照實列出,供判讀;`A3/s8_controls.py` 的解析缺陷未修,原檔不改)**")
    A("")
    A("| 事件 | C1 隱含增速 | M1 實際 | C1 基準 | 包內自註 |")
    A("|---|---|---|---|---|")
    for e in sub:
        c1n = ctrl.get(e["event_id"], {})
        A("| %s | %s | %s | %s | %s |" % (
            e["event_id"], pct(e["C1"]), pct(e["M1"]),
            (c1n.get("C1_basis") or "")[:40], (c1n.get("C1_note") or "")[:60]))
    A("")
    A("C1 這一欄**不可用**(照實報,不改凍結口徑):十宗試跑已查出 `s8_controls.py` 的 "
      "`parse_guidance` 在「revenue」±320 字元窗內把所有帶單位金額取中點,同一窗含收入與 "
      "EBITDA 兩組指引時即混算。此 9 宗之中至少可見:E056 指引原文是「reiterate prior "
      "guidance of 10% year-over-year revenue growth」(包內自註「極端值,指引數字疑誤抽」)"
      "而 C1 報 +1,063%;E070 原文「up 10% Y/Y」而 C1 報 −73.6%;E004 原文是全年 6,000 萬"
      "美元授權收入而 C1 報 −67.1%。**故「臂 < C1」這一條不能當作能力證據**,"
      "只能記「機械對照 C1 在此樣本上解析失效」。")
    A("")
    A("| 分年 | n | DeepSeek 中位 | Opus 中位 | C2 中位 | C3 中位 | DeepSeek 勝 C2 | Opus 勝 C2 |")
    A("|---|---|---|---|---|---|---|---|")
    yrs = sorted({e["fiscal_quarter"][:4] for e in rows})
    for y in yrs:
        s = [e for e in rows if e["fiscal_quarter"][:4] == y]
        ds = mae_stats(s, "ds_err_g2", "ds_trim_g2")
        op = mae_stats(s, "opus_err_g2", "opus_trim_g2")
        c2 = mae_stats(s, "err_c2", "trim_c2")
        c3 = mae_stats(s, "err_c3", "trim_c3")
        A("| %s | %d | %s | %s | %s | %s | %s | %s |" % (
            y, len(s), pct(ds["med"]), pct(op["med"]), pct(c2["med"]), pct(c3["med"]),
            yn(ds["med"] is not None and c2["med"] is not None and ds["med"] < c2["med"]),
            yn(op["med"] is not None and c2["med"] is not None and op["med"] < c2["med"])))
    A("")
    A("| 分桶 | n | DeepSeek 中位 | Opus 中位 | C2 中位 | C3 中位 |")
    A("|---|---|---|---|---|---|")
    for b in sorted({e["bucket"] for e in rows}):
        s = [e for e in rows if e["bucket"] == b]
        A("| %s | %d | %s | %s | %s | %s |" % (
            b, len(s), pct(mae_stats(s, "ds_err_g2", "ds_trim_g2")["med"]),
            pct(mae_stats(s, "opus_err_g2", "opus_trim_g2")["med"]),
            pct(mae_stats(s, "err_c2", "trim_c2")["med"]),
            pct(mae_stats(s, "err_c3", "trim_c3")["med"])))
    A("")

    # ---------- 表二:交叉表
    A("## 表二 判級 × 延續二值(交叉表)")
    A("")
    A("延續定義:M1 ≥ 0.8 × g0_quarters(g0 < 0 時 ≥ g0)**且** 其後兩季無指引下修;"
      "「M1 ≥ g0」為替代定義;0.7／0.9 為敏感度。")
    A("")
    A("| 臂 | 判級 | n | 延續(0.8) | 延續(0.7) | 延續(0.9) | 延續(M1≥g0) | 四季延續(四中三) | "
      "延續(0.8,不計下修) | 延續(0.8,嚴窗下修) |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for a, lab in ARMS:
        for p in ("高", "中", "低", "無法判斷"):
            s = [e for e in rows if e["%s_persist" % a] == p]
            if not s:
                continue
            def cnt(k):
                v = [e[k] for e in s if e[k] is not None]
                return "%d/%d" % (sum(1 for x in v if x), len(v))
            A("| %s | %s | %d | %s | %s | %s | %s | %s | %s | %s |" % (
                lab, p, len(s), cnt("persist_08"), cnt("persist_07"), cnt("persist_09"),
                cnt("persist_alt"), cnt("persist4"), cnt("persist_08_nodn"),
                cnt("persist_08_strict")))
    A("")
    def pool(k):
        v = [e[k] for e in rows if e[k] is not None]
        return "%d/%d" % (sum(1 for x in v if x), len(v))
    A("全池(84 宗)延續率:0.8 → %s;0.7 → %s;0.9 → %s;M1 ≥ g0 → %s;四季(四中三)→ %s;"
      "0.8 不計下修 → %s;0.8 嚴窗下修 → %s。"
      % (pool("persist_08"), pool("persist_07"), pool("persist_09"),
         pool("persist_alt"), pool("persist4"), pool("persist_08_nodn"),
         pool("persist_08_strict")))
    A("")
    A("**指引下修正則的可靠度(照實報,不改凍結口徑)**:機械判準是「lower／lowered／reduce／"
      "reduced／cut 與 guidance／outlook 相距 ≤130 字元」,字串窗寬 260 字元。"
      "照此跑,84 宗之中 %d 宗判「有下修」。抽驗命中句:其中一部分命中句語意與指引方向無關"
      "(例如「reaffirmed」「remains unchanged」「reduce fixed costs」「lower cost」"
      "「REDUCE-IT 研究」「lower expected net periodic benefit income」),"
      "另一部分確實是下調(但方向多為成本／資本開支／EBITDA 而非收入)。"
      "十宗試跑已見過反方向的錯:真下修句(「below the low end」「temporarily withdraws "
      "guidance」)正則一條都認不出。因此延續率另報兩個敏感度:"
      "「不計下修」(只驗增速)與「嚴窗下修」(字串窗收窄到 ±60 字元)。"
      % sum(1 for e in rows if e["guide_down"] == "有下修"))
    A("")

    # ---------- 表三:p_continue 校準
    A("## 表三 p_continue 校準(五帶)與 AUC")
    A("")
    A("| 臂 | p_continue 帶 | n | 實際延續率(0.8) | 實際延續率(M1≥g0) |")
    A("|---|---|---|---|---|")
    bands = [("<0.2", -1, 0.2), ("0.2–0.4", 0.2, 0.4), ("0.4–0.6", 0.4, 0.6),
             ("0.6–0.8", 0.6, 0.8), ("≥0.8", 0.8, 2)]
    for a, lab in ARMS:
        for nm, lo, hi in bands:
            s = [e for e in rows if lo <= e["%s_pcont" % a] < hi]
            if not s:
                continue
            v = [e["persist_08"] for e in s if e["persist_08"] is not None]
            v2 = [e["persist_alt"] for e in s if e["persist_alt"] is not None]
            A("| %s | %s | %d | %s | %s |" % (
                lab, nm, len(s),
                ("%d/%d = %.0f%%" % (sum(1 for x in v if x), len(v),
                                     100 * sum(1 for x in v if x) / len(v))) if v else "—",
                ("%d/%d = %.0f%%" % (sum(1 for x in v2 if x), len(v2),
                                     100 * sum(1 for x in v2 if x) / len(v2))) if v2 else "—"))
    A("")
    for a, lab in ARMS:
        sc = [(e["%s_pcont" % a], e["persist_08"]) for e in rows
              if e["persist_08"] is not None]
        au = auc([x for x, _ in sc], [y for _, y in sc])
        A("- %s:p_continue 對延續(0.8)的 AUC = %s(n=%d,延續 %d 宗、不延續 %d 宗)。"
          % (lab, f3(au), len(sc), sum(1 for _, y in sc if y),
             sum(1 for _, y in sc if not y)))
    A("")

    # ---------- 表四:分歧格
    A("## 表四 分歧格(臂判高而 C2 判不延續 / 臂判低而 C2 判延續)")
    A("")
    A("C2 判延續 = C2 ≥ 0.8 × g0_quarters(同一門檻)。")
    A("")
    A("| 臂 | 格 | 事件數 | 實際延續(0.8) | 該格 M1 中位 | 該格 C2 中位 |")
    A("|---|---|---|---|---|---|")
    for a, lab in ARMS:
        for kind, nm, sel in (
                ("hi", "判高 × C2 判不延續",
                 [e for e in rows if e["%s_persist" % a] == "高" and e["c2_predicts"] is False]),
                ("lo", "判低 × C2 判延續",
                 [e for e in rows if e["%s_persist" % a] == "低" and e["c2_predicts"] is True])):
            v = [e["persist_08"] for e in sel if e["persist_08"] is not None]
            A("| %s | %s | %d | %s | %s | %s |" % (
                lab, nm, len(sel),
                ("%d/%d" % (sum(1 for x in v if x), len(v))) if v else "—",
                pct(med([e["M1"] for e in sel if e["M1"] is not None])),
                pct(med([e["C2"] for e in sel if e["C2"] is not None]))))
    A("")

    # ---------- 表五:兩臂互比
    A("## 表五 兩臂互比")
    A("")
    diffs = [(e["ds_err_g2"] - e["opus_err_g2"]) for e in rows
             if e["ds_err_g2"] is not None and e["opus_err_g2"] is not None]
    ds_win = sum(1 for d in diffs if d < 0)
    op_win = sum(1 for d in diffs if d > 0)
    tie = sum(1 for d in diffs if d == 0)
    A("- 同事件兩季誤差差(DeepSeek − Opus):中位 %s、平均 %s(n=%d;負 = DeepSeek 較準)。"
      % (pct(med(diffs)), pct(mean(diffs)), len(diffs)))
    A("- 逐事件勝負:DeepSeek 較準 %d 宗、Opus 較準 %d 宗、並列 %d 宗。"
      % (ds_win, op_win, tie))
    d4 = [(e["ds_err_g4"] - e["opus_err_g4"]) for e in rows
          if e["ds_err_g4"] is not None and e["opus_err_g4"] is not None]
    A("- 四季:DeepSeek 較準 %d 宗、Opus 較準 %d 宗、並列 %d 宗(中位差 %s)。"
      % (sum(1 for d in d4 if d < 0), sum(1 for d in d4 if d > 0),
         sum(1 for d in d4 if d == 0), pct(med(d4))))
    agree = [e for e in rows if e["ds_persist"] == e["opus_persist"]]
    A("- 判級一致率:%d/%d = %.0f%%。" % (len(agree), len(rows), 100 * len(agree) / len(rows)))
    sp = spearman([e["ds_pcont"] for e in rows], [e["opus_pcont"] for e in rows])
    A("- p_continue 兩臂 Spearman 相關 = %s。" % f3(sp))
    for a, lab in ARMS:
        w2 = sum(1 for e in rows if e["%s_err_g2" % a] is not None and e["err_c2"] is not None
                 and e["%s_err_g2" % a] < e["err_c2"])
        n2 = sum(1 for e in rows if e["%s_err_g2" % a] is not None and e["err_c2"] is not None)
        w3 = sum(1 for e in rows if e["%s_err_g2" % a] is not None and e["err_c3"] is not None
                 and e["%s_err_g2" % a] < e["err_c3"])
        w1 = sum(1 for e in rows if e["%s_err_g2" % a] is not None and e["err_c1"] is not None
                 and e["%s_err_g2" % a] < e["err_c1"])
        n1 = sum(1 for e in rows if e["%s_err_g2" % a] is not None and e["err_c1"] is not None)
        A("- %s:兩季誤差勝 C2 %d/%d、勝 C3 %d/%d、勝 C1 %d/%d。" % (lab, w2, n2, w3, len(rows), w1, n1))
    A("")

    # ---------- 表六:分組
    A("## 表六 分組表(每組 n、各臂 MAE 中位、C2、C3、延續率)")
    A("")
    A("### 6a 全池 對 逐組剔除版")
    A("")
    A("| 版本 | n | DeepSeek 中位 | Opus 中位 | C2 中位 | C3 中位 | 延續率(0.8) |")
    A("|---|---|---|---|---|---|---|")
    def gline(name, sub):
        v = [e["persist_08"] for e in sub if e["persist_08"] is not None]
        A("| %s | %d | %s | %s | %s | %s | %s |" % (
            name, len(sub), pct(mae_stats(sub, "ds_err_g2", "ds_trim_g2")["med"]),
            pct(mae_stats(sub, "opus_err_g2", "opus_trim_g2")["med"]),
            pct(mae_stats(sub, "err_c2", "trim_c2")["med"]),
            pct(mae_stats(sub, "err_c3", "trim_c3")["med"]),
            ("%d/%d" % (sum(1 for x in v if x), len(v))) if v else "—"))
    gline("全池(含全部)", rows)
    for nm, key in DEFECT_GROUPS:
        gline("剔除:" + nm, [e for e in rows if not e[key]])
    A("")
    A("### 6b g0 三檔")
    A("")
    A("| g0_quarters | n | DeepSeek 中位 | Opus 中位 | C2 中位 | C3 中位 | 延續率(0.8) |")
    A("|---|---|---|---|---|---|---|")
    for b in ("≤0", "0–0.3", ">0.3", "缺"):
        s = [e for e in rows if e["g0_band"] == b]
        if s:
            gline(b, s)
    A("")

    # ---------- 表七:成敗條件
    A("## 表七 執行口徑 v1 第六節 成敗條件逐條核對")
    A("")
    A("| 條件 | DeepSeek 臂 | Opus 臂 |")
    A("|---|---|---|")
    def medkey(sub, k, tk):
        return mae_stats(sub, k, tk)["med"]
    out_rows = []
    for a, lab in ARMS:
        arm_med = medkey(rows, "%s_err_g2" % a, "%s_trim_g2" % a)
        c2_med = medkey(rows, "err_c2", "trim_c2")
        c1_med = medkey(sub, "%s_err_g2" % a, "%s_trim_g2" % a)
        c1_only = medkey(sub, "err_c1", "trim_c1")
        hi = [e for e in rows if e["%s_persist" % a] == "高" and e["c2_predicts"] is False]
        lo = [e for e in rows if e["%s_persist" % a] == "低" and e["c2_predicts"] is True]
        vh = [e["persist_08"] for e in hi if e["persist_08"] is not None]
        vl = [e["persist_08"] for e in lo if e["persist_08"] is not None]
        # 分歧格偏向模型:判高格多數延續 AND 判低格多數不延續
        hi_ok = bool(vh) and sum(1 for x in vh if x) > len(vh) / 2
        lo_ok = bool(vl) and sum(1 for x in vl if not x) > len(vl) / 2
        # 逐年剔走方向
        flat = True
        for y in yrs:
            s = [e for e in rows if e["fiscal_quarter"][:4] != y]
            m = medkey(s, "%s_err_g2" % a, "%s_trim_g2" % a)
            c = medkey(s, "err_c2", "trim_c2")
            if not (m is not None and c is not None and m < c):
                flat = False
        out_rows.append({
            "lab": lab, "arm_med": arm_med, "c2_med": c2_med, "c1_med": c1_med,
            "c1_only": c1_only, "hi": len(hi), "lo": len(lo), "hi_ok": hi_ok,
            "lo_ok": lo_ok, "flat": flat,
            "hi_yes": sum(1 for x in vh if x), "hi_n": len(vh),
            "lo_no": sum(1 for x in vl if not x), "lo_n": len(vl),
            "beat_c2": arm_med is not None and c2_med is not None and arm_med < c2_med,
            "beat_c1": (c1_med is not None and c1_only is not None and c1_med < c1_only)})
    A("| 模型點值對 M1 絕對誤差中位 | %s | %s |" % (
        pct(out_rows[0]["arm_med"]), pct(out_rows[1]["arm_med"])))
    A("| C2 同一口徑中位 | %s | %s |" % (pct(out_rows[0]["c2_med"]), pct(out_rows[1]["c2_med"])))
    A("| 中位 < C2? | %s | %s |" % (
        yn(out_rows[0]["arm_med"] < out_rows[0]["c2_med"]),
        yn(out_rows[1]["arm_med"] < out_rows[1]["c2_med"])))
    A("| 有指引子樣本(n=%d):臂中位 | %s | %s |" % (
        len(sub), pct(out_rows[0]["c1_med"]), pct(out_rows[1]["c1_med"])))
    A("| 有指引子樣本:C1 中位 | %s | %s |" % (
        pct(out_rows[0]["c1_only"]), pct(out_rows[1]["c1_only"])))
    A("| 中位 < C1(同子樣本)? | %s | %s |" % (
        yn(out_rows[0]["arm_med"] < out_rows[0]["c1_only"]),
        yn(out_rows[1]["arm_med"] < out_rows[1]["c1_only"])))
    A("| 分歧格:判高×C2 不延續 宗數 / 其中實際延續 | %d / %d | %d / %d |" % (
        out_rows[0]["hi"], out_rows[0]["hi_yes"], out_rows[1]["hi"], out_rows[1]["hi_yes"]))
    A("| 分歧格:判低×C2 延續 宗數 / 其中實際不延續 | %d / %d | %d / %d |" % (
        out_rows[0]["lo"], out_rows[0]["lo_no"], out_rows[1]["lo"], out_rows[1]["lo_no"]))
    A("| 分歧格偏向模型?(判高格多數延續 且 判低格多數不延續) | %s | %s |" % (
        yn(out_rows[0]["hi_ok"] and out_rows[0]["lo_ok"]),
        yn(out_rows[1]["hi_ok"] and out_rows[1]["lo_ok"])))
    A("| 逐年剔走方向不變(每年剔走後仍 中位 < C2)? | %s | %s |" % (
        yn(out_rows[0]["flat"]), yn(out_rows[1]["flat"])))
    A("| **最低條件(中位 < C2,且有指引子樣本中位 < C1,分歧格偏向模型,逐年剔走方向不變)** | %s | %s |" % (
        yn(out_rows[0]["beat_c1"] and out_rows[0]["beat_c2"] and out_rows[0]["hi_ok"]
           and out_rows[0]["lo_ok"] and out_rows[0]["flat"]),
        yn(out_rows[1]["beat_c1"] and out_rows[1]["beat_c2"] and out_rows[1]["hi_ok"]
           and out_rows[1]["lo_ok"] and out_rows[1]["flat"])))
    A("| **否定條件(中位不小於 C2,或分歧格不偏向模型)** | %s | %s |" % (
        yn((not out_rows[0]["beat_c2"]) or not (out_rows[0]["hi_ok"] and out_rows[0]["lo_ok"])),
        yn((not out_rows[1]["beat_c2"]) or not (out_rows[1]["hi_ok"] and out_rows[1]["lo_ok"]))))
    A("")
    A("注意:「中位 < C1」一欄建基於 C1 的 9 宗,而該 9 宗的 C1 值已證解析失效"
      "(見表一後段逐宗值與說明:至少 3 宗與稿內原文相反)。故此欄的「是」"
      "**不構成模型優於指引的證據**;C1 這一格在本次考試中不具判別力。"
      "「中位 < C2」「分歧格」「逐年剔走」三項不受此影響(C2/C3 由本腳本自算)。")
    A("")
    # ---------- 表八:叢集
    A("## 表八 叢集(sic2 × 曆季)內相關")
    A("")
    cl = {}
    for e in rows:
        y, m = e["signal_q_end"][:4], int(e["signal_q_end"][5:7])
        cl.setdefault((e["sic2"], "%sQ%d" % (y, (m - 1) // 3 + 1)), []).append(e)
    A("- 叢集數 %d;單宗叢集 %d 個;最大叢集 %d 宗。" % (
        len(cl), sum(1 for v in cl.values() if len(v) == 1),
        max(len(v) for v in cl.values())))
    rc = {}
    for e in rows:
        rc.setdefault(e["cik"], []).append(e["event_id"])
    rep = {k: v for k, v in rc.items() if len(v) > 1}
    A("- 同公司重複事件(repeat company)的組數 %d,涉及 %d 宗(清單:%s)。"
      % (len(rep), sum(len(v) for v in rep.values()),
         "、".join("+".join(sorted(v)) for v in rep.values()) or "無"))
    A("")
    A("| 預測者 | 逐宗中位 | 叢集先平均後中位 |")
    A("|---|---|---|")
    for a, lab in ARMS:
        cm = med([mean([x for x in (e["%s_err_g2" % a] for e in v) if x is not None])
                  for v in cl.values() if any(e["%s_err_g2" % a] is not None for e in v)])
        A("| %s | %s | %s |" % (lab, pct(mae_stats(rows, "%s_err_g2" % a,
                                                   "%s_trim_g2" % a)["med"]), pct(cm)))
    for nm, lab in (("c2", "C2 趨勢延續"), ("c3", "C3 訊號持續")):
        cm = med([mean([x for x in (e["err_%s" % nm] for e in v) if x is not None])
                  for v in cl.values() if any(e["err_%s" % nm] is not None for e in v)])
        A("| %s | %s | %s |" % (lab, pct(mae_stats(rows, "err_%s" % nm,
                                                   "trim_%s" % nm)["med"]), pct(cm)))
    A("")

    # ---------- 表九:逐年剔走
    A("## 表九 逐年剔走")
    A("")
    A("| 剔走年 | 剩 n | DeepSeek 中位 | Opus 中位 | C2 中位 | 方向(臂 < C2) |")
    A("|---|---|---|---|---|---|")
    for y in yrs:
        s = [e for e in rows if e["fiscal_quarter"][:4] != y]
        a1 = mae_stats(s, "ds_err_g2", "ds_trim_g2")["med"]
        a2 = mae_stats(s, "opus_err_g2", "opus_trim_g2")["med"]
        c = mae_stats(s, "err_c2", "trim_c2")["med"]
        A("| %s | %d | %s | %s | %s | DS %s / OP %s |" % (
            y, len(s), pct(a1), pct(a2), pct(c),
            yn(a1 is not None and c is not None and a1 < c),
            yn(a2 is not None and c is not None and a2 < c)))
    A("")

    # ---------- 表十:資料缺失
    A("## 表十 資料缺失與標記")
    A("")
    g_miss = [e["event_id"] for e in rows if e["g0_quarters"] is None]
    m1_miss = [e["event_id"] for e in rows if e["M1"] is None]
    m2_miss = [e["event_id"] for e in rows if e["M2"] is None]
    c2_miss = [e["event_id"] for e in rows if e["C2"] is None]
    c1_has = [e["event_id"] for e in rows if e["C1"] is not None]
    A("| 項 | 缺／未成熟 | 數 |")
    A("|---|---|---|")
    A("| g0_quarters | %s | %d |" % ("、".join(g_miss) or "無", len(g_miss)))
    A("| M1(兩季) | %s | %d |" % ("、".join(m1_miss) or "無", len(m1_miss)))
    A("| M2(四季,含未成熟) | %s | %d |" % ("、".join(m2_miss) or "無", len(m2_miss)))
    A("| C2 趨勢延續 | %s | %d |" % ("、".join(c2_miss) or "無", len(c2_miss)))
    A("| C1 無值(指引解析不到) | — | %d |" % (84 - len(c1_has)))
    A("")
    A("C1 **有值**的 %d 宗:%s(其餘指引解析不到或無可比財年收入指引,標資料不足)。"
      % (len(c1_has), "、".join(c1_has) or "無"))
    A("")
    A("- 指引下修檢查:Q+1／Q+2 業績稿 EX-99.1,機械正則(guidance／outlook 130 字元內 "
      "lower／reduce／cut)。判定分佈:有下修 %d 宗、無 %d 宗、查不到 %d 宗(每宗兩次檢查)。"
      % (sum(1 for e in rows if e["guide_down"] == "有下修"),
         sum(1 for e in rows if e["guide_down"] == "無"),
         sum(1 for e in rows if e["guide_down"] == "查不到")))
    A("- 判「有下修」的事件:%s。"
      % ("、".join(e["event_id"] for e in rows if e["guide_down"] == "有下修") or "無"))
    A("- 指引文本來源:業績事件由 `A3/population.csv` 認(Q+1／Q+2 季末後四個月內、"
      "反應日晚於 T1);母體期(2025-06-30)之後的事件改由 EDGAR submissions 補抓;"
      "EX-99.1 已在 `A/edgar_cache/` 者直接用快取。逐宗結果見 `評分.csv` 的 "
      "`guide_Q1`／`guide_Q2` 欄(含申報編號與來源)。")
    A("- 逐字稿:有 %d 宗、無 %d 宗;上一稿指引句:有 %d 宗、無 %d 宗(只作標籤,未作閘)。"
      % (sum(1 for e in rows if e["has_transcript"]),
         84 - sum(1 for e in rows if e["has_transcript"]),
         sum(1 for e in rows if e["has_prior_guidance"]),
         84 - sum(1 for e in rows if e["has_prior_guidance"])))
    A("- 上一稿指引句重掃(備忘 32 項)本票**未逐宗人手核**,只取包內旗標;"
      "包內標「查不到」而原稿其實有指引句的個案,本票不另修,留待 v2 建包。")
    A("")
    if notes:
        A("**註**:")
        for n in notes:
            A("- %s" % n)
        A("")

    # ---------- 污染聲明
    A("## 污染聲明(照 `執行口徑——②第一次考試-v1.md` 第一節照抄)")
    A("")
    A("> 模型知結局;隨機抽樣不消除記憶;換較強模型不令歷史乾淨。")
    A("")
    A("84 宗反應日全部在 2014–2025,兩臂的訓練資料涵蓋其後結果,**受記憶污染**。"
      "本檔一切數字都建在這個已知污染之上;分組表已把兩臂自己標「有影響／同向」的卡"
      "另列一組,但自我申報不等於乾淨。")
    A("")
    A("## 結論(留白,由主 agent 寫)")
    A("")
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("wrote", OUT_MD)
    print("wrote", OUT_CSV)


if __name__ == "__main__":
    main()
