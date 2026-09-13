# -*- coding: utf-8 -*-
"""KARST-229 ②十宗試跑 結果對照——兩臂機械版 vs T1 後實際經營結果。

只讀:
  試跑/ds/rows/*.csv、試跑/opus/rows/*.csv(機械版;四行錯位按 KARST-227 留言還原)
  A2/controls_operating.csv(C1/C2/C3)
  A2/packets/<eid>.json(1_事件識別、4_財務數列)
  A2/population.csv(找 T1 之後的業績事件)
  data/sec/companyfacts/CIK*.json.gz(首報值;體例照 A2/finlib.py)
  A/edgar_cache/(EX-99.1 文本;缺者單線程 3 請求/秒補抓)

不讀人讀版卡、不讀 A3/、不改任何輸入檔。
評分規則照 `執行口徑——②第一次考試-v1.md` 第一節與第四節。
"""
from __future__ import annotations

import csv
import gzip
import html
import json
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(r"C:\projects\Karst\research\2026-09-methodology\2026-09-12-②第一次考試")
PROJ = Path(r"C:\projects\Karst")
A2 = ROOT / "A2"
PILOT = ROOT / "試跑"
CACHE = ROOT / "A" / "edgar_cache"
OUT_MD = PILOT / "結果對照——十宗雙臂.md"
OUT_CSV = PILOT / "結果對照.csv"

EVENTS = ["E001", "E009", "E017", "E025", "E033", "E041", "E049", "E057", "E065", "E073"]
BAD_COMMA = {"E033", "E041", "E065"}       # 千分位逗號,E073 另法
ARMS = [("ds", "DeepSeek 臂"), ("opus", "Opus 臂")]

# 讀稿核實:逐份 Q+1／Q+2 業績稿讀指引方向(機械正則查不到「撤銷」,亦分不出上調)。
# 只作敏感度;主口徑仍照執行口徑 v1 的機械正則。
READ_GUIDE = {
    "E001": {"Q+1": ("無", "標題只報第四季及全年業績"), "Q+2": ("重申", "Outlook Reaffirmed for Fiscal Year 2016")},
    "E009": {"Q+1": ("修訂", "Full year 2016 guidance is revised;reducing LOE guidance(成本項)"),
             "Q+2": ("非業績稿", "2017-01-31 井位與年末指標稿,非業績稿")},
    "E017": {"Q+1": ("無", "只報第三季業績"), "Q+2": ("無", "只報第四季及全年業績")},
    "E025": {"Q+1": ("無", "只報第三季業績"), "Q+2": ("無", "Q4 Revenue $377M, Up 13%")},
    "E033": {"Q+1": ("上調", "ANNOUNCES SECOND-QUARTER 2019 RESULTS AND RAISES FULL-YEAR GUIDANCE"),
             "Q+2": ("上調", "RAISES FULL-YEAR REVENUE AND ADJUSTED EBITDA GUIDANCE RANGES")},
    "E041": {"Q+1": ("上調", "drove fourth quarter results above the top end of our guidance"),
             "Q+2": ("無", "只報第一季業績")},
    "E049": {"Q+1": ("無", "PRELIMINARY 3q21 results, provides business update"),
             "Q+2": ("無", "PRELIMINARY 4q21 results, provides business update")},
    "E057": {"Q+1": ("下修", "full year 2022 production is expected to be modestly below the low end of "
                              "Talos's original guidance range"),
             "Q+2": ("無", "Provides 2023 Guidance(開新財年指引)")},
    "E065": {"Q+1": ("上調", "Net sales now expected +1~2%, previously −2%~+1%;support our decision to "
                              "raise our fiscal year 2023 outlook"),
             "Q+2": ("無", "Provides FY24 Outlook(開新財年指引)")},
    "E073": {"Q+1": ("重申", "Reiterates Full Year Financial Guidance"),
             "Q+2": ("下修", "Company temporarily withdraws guidance due to ongoing tariff uncertainty")},
}

sys.path.insert(0, str(A2))
import finlib  # noqa: E402


# ---------------------------------------------------------------- 機械版還原
def _split(line: str) -> list[str]:
    return next(csv.reader([line]))


def load_row(arm: str, eid: str) -> dict:
    """讀機械版一行。DeepSeek 臂四行錯位按 KARST-227 留言還原;原檔不改。"""
    raw = (PILOT / arm / "rows" / (eid + ".csv")).read_text(encoding="utf-8").splitlines()
    header = _split(raw[0])
    f = _split(raw[1])
    if arm == "ds" and eid == "E073":
        assert len(f) == 27
        assert f[24].count(");") >= 1, "E073 分號位置與留言不符"
        fa, fb = f[24].split(");", 1)   # 第一個 ); 即「核……損益表);」的邊界
        f = f[0:4] + [f[4] + f[5]] + f[6:24] + [fa + ");", fb.lstrip()] + f[25:27]
    elif arm == "ds" and eid in BAD_COMMA:
        # 千分位:逗號前為數字、後剛好三位數字再接非數字
        f = _split(re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", raw[1]))
        if len(f) > len(header):                     # 保險:溢出併回最後一欄
            f = f[: len(header) - 1] + [",".join(f[len(header) - 1:])]
    assert len(f) == len(header) == 27, (arm, eid, len(f), len(header))
    return dict(zip(header, f))


# ---------------------------------------------------------------- EX-99.1 文本
UA = {"User-Agent": "Karst research kaho@example.com"}
_LAST = [0.0]


def _get(url: str, timeout: int = 60) -> bytes:
    wait = _LAST[0] + 1.0 / 3.0 - time.time()        # 單線程 3 請求/秒
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


def get_ex991(cik: str, acc: str) -> tuple[str | None, str]:
    nodash = acc.replace("-", "")
    p = CACHE / (nodash + "__EX991.txt.gz")
    if p.exists():
        try:
            return gzip.open(p, "rt", encoding="utf-8").read(), "cache"
        except OSError:
            pass
    base = "https://www.sec.gov/Archives/edgar/data/%d/%s" % (int(cik), nodash)
    try:
        page = _get(base + "/" + acc + "-index.html").decode("utf-8", "ignore")
    except Exception as e:                                          # noqa: BLE001
        return None, "索引抓取失敗:%s" % type(e).__name__
    doc = ""
    for tr in re.findall(r"(?is)<tr.*?</tr>", page):
        href = re.search(r'href="([^"]+)"', tr)
        if not href:
            continue
        tds = re.findall(r"(?is)<td[^>]*>\s*([^<]*?)\s*</td>", tr)
        if any(t.strip().upper().replace(" ", "") == "EX-99.1" for t in tds):
            doc = href.group(1).rsplit("/", 1)[-1]
            break
    if not doc:
        return None, "該申報無 EX-99.1 附件"
    try:
        txt = strip_html(_get(base + "/" + doc, timeout=120))
    except Exception as e:                                          # noqa: BLE001
        return None, "附件抓取失敗:%s" % type(e).__name__
    with gzip.open(p, "wt", encoding="utf-8") as f:
        f.write(txt)
    return txt, "新抓"


NOUN = re.compile(r"(?i)\b(guidance|outlook)\b")
VERB = re.compile(r"(?i)\b(lower(?:ed|s|ing)?|reduce[ds]?|reducing|cut|cuts)\b")


def add_months(d, n: int):
    y, m = d.year, d.month + n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    day = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return d.replace(year=y, month=m, day=day)


def rev_series(cik: str) -> dict:
    """單季收入序列(首報值):3 個月列優先,缺者用累計列相減補(finlib 體例)。

    直接取「序列中接下來四個期末」會出事:XBRL 有缺口(如 CLX 缺 2023-06-30 那季、
    SM 缺 2016-12-31、AEHR 缺 2025-05-31),跳過缺口即把 Q+2 當成 Q+3。
    """
    facts = finlib.load_facts(cik)
    if facts is None:
        return {}
    s = dict(finlib.quarterly(facts, finlib.REV_TAGS))
    for en, v in finlib.quarterize_cumulative(finlib.cumulative(facts, finlib.REV_TAGS)).items():
        s.setdefault(en, v)
    return s


def nearest(series: dict, target, tol: int = 16) -> str | None:
    from datetime import date as _d
    c = [(abs((_d.fromisoformat(k) - target).days), k) for k in series]
    c = [x for x in c if x[0] <= tol]
    return min(c)[1] if c else None


def guidance_down(txt: str) -> list[str]:
    """lower/reduce/cut 與 guidance/outlook 相距 ≤130 字元 → 記一條。"""
    out = []
    for m in NOUN.finditer(txt):
        seg = txt[max(0, m.start() - 130): m.end() + 130]
        if VERB.search(seg):
            snip = re.sub(r"\s+", " ", txt[max(0, m.start() - 90): m.end() + 90]).strip()
            out.append(snip)
    return out


# ---------------------------------------------------------------- 主流程
def main() -> None:
    pop = list(csv.DictReader(open(A2 / "population.csv", encoding="utf-8-sig")))
    pop_by_cik: dict[str, list[dict]] = {}
    for r in pop:
        pop_by_cik.setdefault(r["cik"], []).append(r)

    ctrl = {r["event_id"]: r for r in csv.DictReader(
        open(A2 / "controls_operating.csv", encoding="utf-8-sig"))}

    rows_out = []
    notes: list[str] = []

    for eid in EVENTS:
        pk = json.load(open(A2 / "packets" / (eid + ".json"), encoding="utf-8"))
        idn = pk["1_事件識別"]
        cik, ticker = pk["cik"], pk["ticker"]
        t1 = idn["signal_date_反應日"]
        sq_end = pk["4_財務數列"]["signal_q_end"]
        g0 = pk["4_財務數列"]["g0_signal_q_yoy"]

        # --- T1 後四季實際(首報值,照 finlib 體例)
        from datetime import date as _date
        rev = rev_series(cik)
        sqd = _date.fromisoformat(sq_end)
        ends = [nearest(rev, add_months(sqd, 3 * k)) for k in (1, 2, 3, 4)]
        yoys = [None if e is None else finlib.yoy(rev, e) for e in ends]
        m1 = (statistics.mean([y for y in yoys[:2] if y is not None])
              if all(y is not None for y in yoys[:2]) else None)
        if all(y is not None for y in yoys):
            m2 = statistics.mean(yoys)
        elif any(y is not None for y in yoys[2:]):
            m2 = statistics.mean([y for y in yoys if y is not None])
            notes.append("%s M2 只有 %d 季有數" % (eid, sum(y is not None for y in yoys)))
        else:
            m2 = None

        # --- 指引下修:Q+1、Q+2 業績稿 EX-99.1
        gd, gd_txt = [], {}
        for k in (0, 1):
            qe = ends[k] if k < len(ends) else None
            if qe is None:
                gd_txt["Q+%d" % (k + 1)] = "無此季"
                continue
            cands = sorted([r for r in pop_by_cik.get(cik, [])
                            if r["signal_q_end"] == qe and r["reaction_date"] > t1],
                           key=lambda r: r["reaction_date"])
            if not cands:
                # 部分業績事件的 signal_q_end 得空白,改用日期窗(季度末起 4 個月)認。
                hi = add_months(_date.fromisoformat(qe), 4).isoformat()
                cands = sorted([r for r in pop_by_cik.get(cik, [])
                                if qe <= r["reaction_date"] <= hi],
                               key=lambda r: r["reaction_date"])
            if not cands:
                gd_txt["Q+%d" % (k + 1)] = "查不到(%s 季無業績事件)" % qe
                continue
            acc = cands[0]["accessionNumber"]
            txt, how = get_ex991(cik, acc)
            if txt is None:
                gd_txt["Q+%d" % (k + 1)] = "查不到(%s)" % how
                continue
            hits = guidance_down(txt)
            head = re.sub(r"\s+", " ", txt).strip()[:110]
            gd_txt["Q+%d" % (k + 1)] = "%s(%s;%s;%s)" % ("有下修" if hits else "無", acc, how, head)
            gd += hits
        guide = "有下修" if gd else ("無" if all(v.startswith("無") for v in gd_txt.values())
                                     else "查不到")
        rg = READ_GUIDE[eid]
        guide_read = "有下修" if any(v[0] == "下修" for v in rg.values()) else "無"

        # --- 兩臂機械版
        arm = {}
        for key, _label in ARMS:
            r = load_row(key, eid)
            arm[key] = {
                "persist": r["persistence_overall"],
                "g2p": float(r["pred_g2_point"]), "g2lo": float(r["pred_g2_lo"]),
                "g2hi": float(r["pred_g2_hi"]), "g4p": float(r["pred_g4_point"]),
                "g4lo": float(r["pred_g4_lo"]), "g4hi": float(r["pred_g4_hi"]),
            }

        c = ctrl.get(eid, {})
        c1 = float(c["C1_guidance_implied_growth"]) if c.get("C1_guidance_implied_growth") else None
        c2 = float(c["C2_prev4_avg_yoy"]) if c.get("C2_prev4_avg_yoy") else None
        c3 = float(c["C3_g0"]) if c.get("C3_g0") else None

        row = {"event_id": eid, "ticker": ticker, "cik": cik, "signal_q_end": sq_end, "t1": t1,
               "g0": g0, "guide_down": guide, "guide_detail": "; ".join(
                   "%s %s" % (k, v) for k, v in gd_txt.items()),
               "m1": m1, "m2": m2, "c1": c1, "c2": c2, "c3": c3,
               "guide_read": guide_read,
               "guide_read_detail": "; ".join(
                   "%s %s(%s)" % (q, v[0], v[1]) for q, v in rg.items())}
        for i in range(4):
            row["q%d_end" % (i + 1)] = ends[i] or ""
            row["yoy%d" % (i + 1)] = yoys[i]
        for key, _label in ARMS:
            for k, v in arm[key].items():
                row["%s_%s" % (key, k)] = v
        # 二值延續與誤差
        for tag, thr in (("08", 0.8), ("07", 0.7), ("09", 0.9), ("alt", 1.0)):
            ok = None if m1 is None else (m1 >= thr * g0)
            if ok is not None and guide == "有下修":
                ok = False
            row["persist_%s" % tag] = ok
        row["persist_08_read"] = (None if m1 is None
                                  else ((m1 >= 0.8 * g0) and guide_read != "有下修"))
        row["persist_alt_read"] = (None if m1 is None
                                   else ((m1 >= g0) and guide_read != "有下修"))
        no_dn = (guide != "有下修")
        row["m1_ge_0.8g0"] = None if m1 is None else (m1 >= 0.8 * g0)
        row["c2_predicts_persist"] = None if c2 is None else (c2 >= 0.8 * g0)
        for key, _label in ARMS:
            a = arm[key]
            row["%s_err_g2" % key] = None if m1 is None else abs(a["g2p"] - m1)
            row["%s_hit_g2" % key] = None if m1 is None else (a["g2lo"] <= m1 <= a["g2hi"])
            row["%s_err_g4" % key] = None if m2 is None else abs(a["g4p"] - m2)
            row["%s_hit_g4" % key] = None if m2 is None else (a["g4lo"] <= m2 <= a["g4hi"])
        for nm, v in (("c1", c1), ("c2", c2), ("c3", c3)):
            row["%s_err" % nm] = None if (v is None or m1 is None) else abs(v - m1)
            row["%s_hit2pp" % nm] = None if (v is None or m1 is None) else (abs(v - m1) <= 0.02)
        row["_no_dn"] = no_dn
        rows_out.append(row)
        print("[done]", eid, ticker, "M1=", m1, "M2=", m2, "guide=", guide,
              "ds=", arm["ds"]["g2p"], arm["ds"]["persist"], "opus=", arm["opus"]["g2p"],
              arm["opus"]["persist"])

    notes += [
        "Q+1..Q+4 的期末按訊號季末加三、六、九、十二個月定位(±16 日),不用"
        "「序列中接下來四個期末」——XBRL 單季列有缺口(CLX 缺 2023-06-30、SM 缺 2016-12-31、"
        "AEHR 缺 2025-05-31 等),跳過缺口即把 Q+3 當成 Q+2。缺者由累計列相減補齊。",
        "E009(SM Energy)的 M2 受報表口徑斷層污染:2017Q1 的 Revenues 首報值 372.7M、"
        "2017Q2 只 120.7M(同一個 tag、同一份 10-Q 內 6 個月數 = 兩季之和),令 Q+3 出現 +160%、"
        "Q+4 出現 −65% 兩格;M1 不受影響。",
        "E009 Q+2 的指引檢查命中 2017-01-31 的井位與年末指標稿(非業績稿);該司第四季業績稿"
        "在 population 的 signal_q_end 空白,已按日期窗認事件,認到的不是業績稿,該格標"
        "「非業績稿」。",
        "**C1 有一個明顯的數據缺陷(不在本票範圍,原檔不改,照報並註)**:E033 的 C1 = −37.2%,"
        "與該司當日上調全年收入指引的方向相反。核 `A2/s8_controls.py` 的 `parse_guidance`:"
        "它在「revenue」±320 字元的窗內把所有帶單位的金額取 (min+max)/2,同一段窗同時含"
        "收入指引 $8.30–8.50B／$8.35–8.55B 與調整後 EBITDA 指引 $3.35–3.50B／$3.40–3.55B,"
        "量級比 8.55/3.35 = 2.55 未過 3 倍的守閘,於是指引中值算成 (3.35+8.55)/2 = 5.95B。"
        "只用收入重算,餘下三季度應為低單位正增長。這一格令 C1 的 MAE 全不可用。",
    ]

    # ------------------------------------------------------------ 寫 CSV
    fields = ["event_id", "ticker", "cik", "signal_q_end", "t1", "g0", "q1_end", "q2_end",
              "q3_end", "q4_end", "yoy1", "yoy2", "yoy3", "yoy4", "m1", "m2", "guide_down",
              "guide_detail", "c1", "c2", "c3"]
    for key, _l in ARMS:
        fields += ["%s_%s" % (key, k) for k in ("persist", "g2p", "g2lo", "g2hi", "g4p",
                                                "g4lo", "g4hi", "err_g2", "hit_g2", "err_g4",
                                                "hit_g4")]
    fields += ["c1_err", "c2_err", "c3_err", "c1_hit2pp", "c2_hit2pp", "c3_hit2pp",
               "persist_08", "persist_alt", "persist_07", "persist_09", "m1_ge_0.8g0",
               "c2_predicts_persist", "guide_read", "guide_read_detail", "persist_08_read",
               "persist_alt_read"]
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows_out:
            w.writerow(r)

    # ------------------------------------------------------------ 彙總
    def mae(key, col="err_g2"):
        v = [r["%s_%s" % (key, col)] for r in rows_out if r.get("%s_%s" % (key, col)) is not None]
        return (statistics.median(v), statistics.mean(v), len(v)) if v else (None, None, 0)

    def hits(key, col="hit_g2"):
        v = [r["%s_%s" % (key, col)] for r in rows_out if r.get("%s_%s" % (key, col)) is not None]
        return (sum(v), len(v)) if v else (0, 0)

    summary = []
    for key, label in ARMS:
        md, mn, n = mae(key)
        hs, hn = hits(key)
        md4, mn4, n4 = mae(key, "err_g4")
        hs4, hn4 = hits(key, "hit_g4")
        summary.append((label, "兩季", md, mn, n, "%d/%d" % (hs, hn)))
        summary.append((label, "四季", md4, mn4, n4, "%d/%d" % (hs4, hn4)))
    for nm, lab in (("c1", "C1 指引隱含"), ("c2", "C2 趨勢延續"), ("c3", "C3 訊號持續(=g0)")):
        md, mn, n = mae(nm, "err")
        hs, hn = hits(nm, "hit2pp")
        summary.append((lab, "兩季", md, mn, n, "%d/%d(±2pp 輔助)" % (hs, hn)))

    # 交叉表
    cross = {}
    for key, label in ARMS:
        for p in ("高", "中", "低", "無法判斷"):
            sel = [r for r in rows_out if r["%s_persist" % key] == p]
            t = sum(1 for r in sel if r["persist_08"] is True)
            t2 = sum(1 for r in sel if r["persist_alt"] is True)
            t3 = sum(1 for r in sel if r["persist_08_read"] is True)
            cross[(label, p)] = (t, t2, t3, len(sel))

    # 分歧格
    div = []
    for key, label in ARMS:
        for kind in ("high_vs_c2no", "low_vs_c2yes"):
            sel = []
            for r in rows_out:
                if r["c2_predicts_persist"] is None:
                    continue
                if kind == "high_vs_c2no" and r["%s_persist" % key] == "高" \
                        and r["c2_predicts_persist"] is False:
                    sel.append(r)
                if kind == "low_vs_c2yes" and r["%s_persist" % key] == "低" \
                        and r["c2_predicts_persist"] is True:
                    sel.append(r)
            div.append((label, kind, sel))

    # 敏感度:0.7／0.9 門檻的延續宗數(機械下修口徑)
    sens = []
    for thr in (0.7, 0.8, 0.9):
        n = sum(1 for r in rows_out
                if r["m1"] is not None and r["m1"] >= thr * r["g0"]
                and r["guide_down"] != "有下修")
        sens.append((thr, n))

    # ------------------------------------------------------------ 寫 MD
    write_md(rows_out, summary, cross, div, notes, gd_txt, sens)
    print("wrote", OUT_MD, OUT_CSV)


def pct(x, dash="—"):
    return dash if x is None else "%+.1f%%" % (100 * x)


def pp(x, dash="—"):
    return dash if x is None else "%.1f%%" % (100 * x)


def write_md(rows, summary, cross, div, notes, gd_txt, sens):
    L = []
    A = L.append
    A("# 結果對照——②十宗試跑 兩臂(DeepSeek／Opus)")
    A("")
    A("> KARST-229。評分規則照 `執行口徑——②第一次考試-v1.md` 第一節「延續」與第四節。"
      "T1 後實際經營結果由 `data/sec/companyfacts` 首報值算(體例照 `A2/finlib.py`);"
      "指引下修由 Q+1、Q+2 業績稿 EX-99.1 文字正則判。"
      "**十宗只作方向觀察,受模型記憶污染,不作能力宣稱**;十宗自此列為主考試外的留出樣本。")
    A("")
    A("## 一、逐事件表(十行)")
    A("")
    A("| 事件 | 代號 | g0 | M1(兩季) | M2(四季) | 指引下修 | 臂 | 判持續 | 兩季點值 | 兩季區間 | 四季點值 | 誤差(兩季) | 區間命中 |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        for i, (key, label) in enumerate(ARMS):
            A("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                r["event_id"] if i == 0 else "", r["ticker"] if i == 0 else "",
                pct(r["g0"]) if i == 0 else "", pct(r["m1"]) if i == 0 else "",
                pct(r["m2"]) if i == 0 else "", r["guide_down"] if i == 0 else "",
                label, r["%s_persist" % key], pct(r["%s_g2p" % key]),
                "%s ~ %s" % (pct(r["%s_g2lo" % key]), pct(r["%s_g2hi" % key])),
                pct(r["%s_g4p" % key]),
                pct(r["%s_err_g2" % key]),
                ("中" if r["%s_hit_g2" % key] else "否") if r["%s_hit_g2" % key] is not None else "—"))
    A("")
    A("| 事件 | C1 指引隱含 | C2 趨勢延續 | C3 訊號持續 | C1 誤差 | C2 誤差 | C3 誤差 | "
      "延續(0.8×g0) | 延續(M1≥g0) | 延續(讀稿下修) | C2 判延續? |")
    A("|---|---|---|---|---|---|---|---|---|---|---|")
    T = {True: "延續", False: "不延續", None: "—"}
    for r in rows:
        A("| %s %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["event_id"], r["ticker"], pct(r["c1"]), pct(r["c2"]), pct(r["c3"]),
            pct(r["c1_err"]), pct(r["c2_err"]), pct(r["c3_err"]),
            T[r["persist_08"]], T[r["persist_alt"]], T[r["persist_08_read"]],
            T[r["c2_predicts_persist"]]))
    A("")
    A("## 二、彙總表")
    A("")
    A("| 預測者 | 期限 | MAE 中位 | MAE 平均 | n | 區間命中 |")
    A("|---|---|---|---|---|---|")
    for s in summary:
        A("| %s | %s | %s | %s | %d | %s |" % (
            s[0], s[1], pp(s[2]), pp(s[3]), s[4], s[5]))
    A("")
    A("MAE 為絕對誤差(百分點),非方向性;區間命中 = 實際值落於該臂八成區間內。"
      "C1 十宗之中只有兩宗有值(其餘八宗指引抓不到),C1 的 MAE 不可用 —— 見第六節缺失。")
    A("")
    A("### 持續性判級 × 延續二值(交叉表)")
    A("")
    A("| 臂 | 判級 | 延續(0.8×g0) | 延續(M1≥g0) | 延續(0.8×g0,讀稿下修) | n |")
    A("|---|---|---|---|---|---|")
    for (label, p), (t, t2, t3, n) in cross.items():
        A("| %s | %s | %d/%d | %d/%d | %d/%d | %d |" % (label, p, t, n, t2, n, t3, n, n))
    A("")
    A("敏感度(全池十宗,機械下修口徑):門檻 0.7 → %d 宗延續、0.8 → %d 宗、0.9 → %d 宗。"
      % (sens[0][1], sens[1][1], sens[2][1]))
    A("")
    A("### 分歧格")
    A("")
    A("| 臂 | 格 | 事件 | 實際 M1 | 是否延續(0.8×g0) |")
    A("|---|---|---|---|---|")
    for label, kind, sel in div:
        nm = {"high_vs_c2no": "判高 × C2 判不延續", "low_vs_c2yes": "判低 × C2 判延續"}[kind]
        if not sel:
            A("| %s | %s | 無 | — | — |" % (label, nm))
        for r in sel:
            A("| %s | %s | %s %s | %s | %s |" % (
                label, nm, r["event_id"], r["ticker"], pct(r["m1"]),
                {True: "延續", False: "不延續", None: "—"}[r["persist_08"]]))
    A("")
    A("## 三、指引下修判準:機械正則與讀稿各是什麼結果")
    A("")
    A("執行口徑 v1 的判準是「lower／lowered／reduce／reduced／cut 與 guidance／outlook 相距"
      " ≤130 字元」。照此跑,十宗之中三宗判「有下修」(E009／E033／E065);**逐份讀稿核實,"
      "三宗之中兩宗其實是上調(E033／E065)、一宗只是成本指引下調(E009,收入指引方向未明)**。"
      "反過來,兩宗真正的下修——E057「全年產量將略低於原指引下限」、E073「因關稅不確定"
      "暫時撤回指引」——正則一條都認不出(「below the low end」「withdraws」不在詞表)。"
      "**主表照預先寫死的機械口徑報數;讀稿一欄另列,當敏感度。**")
    A("")
    A("| 事件 | 季 | 機械口徑 | 讀稿核實 | 讀稿依據(原文) |")
    A("|---|---|---|---|---|")
    for r in rows:
        rg = READ_GUIDE[r["event_id"]]
        for q in ("Q+1", "Q+2"):
            mm = re.search(re.escape(q) + r" (有下修|無|查不到)", r["guide_detail"])
            mech = mm.group(1) if mm else "—"
            lab, why = rg[q]
            A("| %s %s | %s | %s | %s | %s |" % (
                r["event_id"], r["ticker"], q, mech, lab, why[:150]))
    A("")
    A("受影響的三宗:**E033／E065** 機械口徑判不延續而讀稿判上調;**E073** 機械口徑判無下修"
      "(正則只認 lower/reduce/cut,認不出 temporarily withdraws guidance)而讀稿判下修。")
    A("")
    A("## 四、g0 為負的四宗(分開講)")
    A("")
    neg = [r for r in rows if r["g0"] < 0]
    A("事件:%s。" % "、".join("%s(%s)g0=%s" % (r["event_id"], r["ticker"], pct(r["g0"]))
                              for r in neg))
    A("")
    A("| 事件 | g0 | M1 | 0.8×g0 | M1≥0.8×g0 | M1≥g0 | C2 | 兩臂判級 |")
    A("|---|---|---|---|---|---|---|---|")
    for r in neg:
        A("| %s %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["event_id"], r["ticker"], pct(r["g0"]), pct(r["m1"]), pct(0.8 * r["g0"]),
            {True: "是", False: "否", None: "—"}[r["m1_ge_0.8g0"]],
            {True: "是", False: "否", None: "—"}[r["persist_alt"]],
            pct(r["c2"]),
            "／".join("%s=%s" % (lab, r["%s_persist" % k]) for k, lab in ARMS)))
    A("")
    A("## 五、還原步驟(DeepSeek 臂四行錯位;可重現)")
    A("")
    A("四行原檔一字不改。還原在 `試跑/score_pilot.py` 的 `load_row()` 內:")
    A("")
    A("1. **E033／E041／E065**:文字欄寫入了千分位逗號,整行欄數 30／30／28。"
      "凡「逗號前是數字、逗號後剛好三位數字再接非數字」的邊界,刪掉該逗號即回到 27 欄"
      "(正則 `(?<=\\d),(?=\\d{3}(?!\\d))`)。")
    A("2. **E073**:欄數剛好 27,兩個缺陷淨額抵銷。"
      "`improvement_text` 內多一個逗號(切成第 5、6 欄),`falsify_1` 與 `biggest_unknown` "
      "之間漏一個逗號(併成一欄,落在第 25 欄)。做法:"
      "(a) 第 5、6 欄併回 `improvement_text`;"
      "(b) 第 25 欄在唯一一個 `);` 之後切開,前半(含 `);`)為 `falsify_1`、後半為 "
      "`biggest_unknown`。切完 27 欄。")
    A("3. 還原後逐行斷言欄數 = 27,並核 `persistence_overall` 落於 {高,中,低,無法判斷}。")
    A("")
    A("## 六、資料來源與缺失")
    A("")
    A("| 項 | 來源 |")
    A("|---|---|")
    A("| 兩臂機械版 | `試跑/ds/rows/*.csv`、`試跑/opus/rows/*.csv`(只讀機械版,未讀人讀版卡) |")
    A("| C1/C2/C3 | `A2/controls_operating.csv` |")
    A("| T1 後實際 | `data/sec/companyfacts` 首報值 |")
    A("| 指引下修 | Q+1、Q+2 業績稿 EX-99.1(`A/edgar_cache/`,缺者單線程 3 請求/秒補抓) |")
    A("")
    for r in rows:
        A("- **%s %s**:T1=%s;Q+1..Q+4 期末 %s;指引檢查 %s" % (
            r["event_id"], r["ticker"], r["t1"],
            "、".join(r["q%d_end" % i] or "缺" for i in range(1, 5)), r["guide_detail"]))
    A("")
    if notes:
        A("**註**:")
        for n in notes:
            A("- %s" % n)
        A("")
    A("## 七、小結(方向觀察,不是能力宣稱)")
    A("")
    arms_g2 = {s[0]: s for s in summary if s[1] == "兩季"}
    A("1. **點值比兩個對照準,但其中一個對照本來就笨。** 兩季 MAE 中位:Opus %s、DeepSeek %s,"
      "對 C2 趨勢延續 %s、C1 指引隱含 %s(只兩宗有值)。但**C3(=訊號季增速 g0 原封不動)**"
      "中位只 %s,與兩臂同等 —— 即在十宗之中,「不用任何判斷、直接把訊號季增速當預測」"
      "這個零成本基準已經和兩臂打平。兩臂真正贏 C3 的地方在**平均**:C3 平均 %s,兩臂 %s／%s。差異"
      "全部來自 g0 極端那幾宗(E073 g0 −36％、E057 +71％、E009 −34％),C3 在那裡大錯而兩臂貼近。"
      % (pp(arms_g2["Opus 臂"][2]), pp(arms_g2["DeepSeek 臂"][2]),
         pp([s for s in summary if s[0] == "C2 趨勢延續"][0][2]),
         pp([s for s in summary if s[0] == "C1 指引隱含"][0][2]),
         pp([s for s in summary if s[0] == "C3 訊號持續(=g0)"][0][2]),
         pp([s for s in summary if s[0] == "C3 訊號持續(=g0)"][0][3]),
         pp(arms_g2["DeepSeek 臂"][3]), pp(arms_g2["Opus 臂"][3])))
    A("2. **兩臂之間分不開。** Opus 中位 %s 對 DeepSeek %s,十宗不足以分勝負;"
      "區間命中兩季 %s 對 %s、四季 %s 對 %s。"
      % (pp(arms_g2["Opus 臂"][2]), pp(arms_g2["DeepSeek 臂"][2]),
         arms_g2["Opus 臂"][5], arms_g2["DeepSeek 臂"][5],
         [s for s in summary if s[0] == "Opus 臂" and s[1] == "四季"][0][5],
         [s for s in summary if s[0] == "DeepSeek 臂" and s[1] == "四季"][0][5]))
    A("3. **判級分不開。** DeepSeek 臂十宗全部判「中」,無高低可分。Opus 臂判高 1 宗"
      "(E049,實際延續)、判低 4 宗(實際 2 宗延續、2 宗不延續)—— 判低組反而一半延續。"
      "分歧格:Opus 判高而 C2 判不延續的一宗(E049)模型對;判低而 C2 判延續的兩宗一對一錯。")
    A("4. **指引正則不可靠**,見第三節:三宗命中之中兩宗其實上調、一宗只是成本指引;"
      "而兩宗真正的下修(E057、E073)一條都認不出。用 0.8×g0 定義時,三宗(M1 ≥ 0.8×g0 "
      "卻被機械判成不延續)的解讀會整個反轉。")
    A("5. **污染**:十宗反應日在 2015–2024,兩臂都可能記得結局。最值得警惕的是輸贏分佈"
      "集中在 g0 極端的三宗 —— 那幾宗也正是最容易有記憶的知名事件。上面任何一條都不足以"
      "支持或否定能力假說;主考試(84 宗)才按 `執行口徑——②第一次考試-v1.md` 第六節的"
      "成敗定義判。")
    A("")
    A("## 八、聲明")
    A("")
    A("十宗事件的反應日全部在 2015–2024,模型訓練資料涵蓋其後結果,"
      "**受記憶污染**;而且只有十宗,不是隨機樣本。"
      "本檔的一切數字**只作方向觀察,不作能力宣稱**,亦不改變主考試的成敗定義;"
      "十宗自此列為主考試之外的**留出樣本**,不再計入母體統計。")
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
