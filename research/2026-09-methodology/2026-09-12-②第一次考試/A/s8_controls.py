# -*- coding: utf-8 -*-
"""KARST-222 票 A 第八步:經營對照預測 C1/C2/C3,另檔 `controls_operating.csv`。

**必須在 `picks_before_results.md` 落檔之後才跑**(鎖定次序要求)。本檔輸出**不入任何
取證包**;取證包由 s9 獨立生成。

C1 公司當時指引隱含的餘下季度按年收入增速:由該份 EX-99.1 的財年收入指引中值,
   減去訊號季止的累計收入(YTD,XBRL 首報),除以去年同一段(去年全年減去年同一時點 YTD)
   − 1。指引抓不到或算不出者標「資料不足」。
C2 訊號前四季按年增速的平均(訊號季之前連續四季,各對去年同季)。
C3 = g0(訊號季按年收入增速)。
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

import finlib as F

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
DOCS = HERE / "edgar_cache"

AMT = re.compile(r"\$\s*(\d+(?:\.\d+)?)\s*(billion|million|bn|mn|b|m)?\b", re.I)
UNIT = {"billion": 1e9, "bn": 1e9, "b": 1e9, "million": 1e6, "mn": 1e6, "m": 1e6}
GUIDW = re.compile(r"(?i)\b(guidance|outlook|expects?|anticipates?|forecast(?:s|ed)?)\b")
REVW = re.compile(r"(?i)\brevenue[s]?\b")
FYW = re.compile(r"(?i)(full[- ]year|fiscal year|fiscal 20\d\d|FY\s?20\d\d|"
                 r"year ending|full fiscal)")


def parse_guidance(text: str) -> tuple[float | None, str]:
    """回傳 (財年收入指引中值美元, 摘句)。抓不到回 (None, "")。"""
    for m in REVW.finditer(text):
        a, b = max(0, m.start() - 320), min(len(text), m.end() + 320)
        w = text[a:b]
        if not (GUIDW.search(w) and FYW.search(w)):
            continue
        amts = []
        for am in AMT.finditer(w):
            u = (am.group(2) or "").lower()
            if not u:
                continue
            amts.append(float(am.group(1)) * UNIT[u])
        if not amts:
            continue
        lo, hi = min(amts), max(amts)
        if hi / max(lo, 1.0) > 3:        # 同窗出現量級差很遠的數 → 不當同一指引
            continue
        mid = (lo + hi) / 2 if len(amts) > 1 else lo
        return mid, re.sub(r"\s+", " ", w).strip()[:400]
    return None, ""


def c1_from(mid: float | None, b: dict, q_end: str) -> tuple[float | None, str]:
    if mid is None:
        return None, "指引抓不到"
    if not b.get("ok"):
        return None, b.get("note", "無財務快取")
    ytds = [(s, e, v) for s, e, v in b["rev_cum"] if e == q_end]
    if not ytds:
        return None, "無訊號季累計收入"
    ytd = max(ytds, key=lambda x: (date.fromisoformat(x[1]) - date.fromisoformat(x[0])).days)[2]
    q = date.fromisoformat(q_end)
    fyes = sorted(e for _s, e, _v in b["rev_annual"] if date.fromisoformat(e) >= q)
    if not fyes:
        return None, "無財年期末"
    fye = fyes[0]
    py = [x for x in b["rev_annual"]
          if 330 <= (date.fromisoformat(fye) - date.fromisoformat(x[1])).days <= 400]
    if not py:
        return None, "無去年財年收入"
    py_tot = min(py, key=lambda x: abs(
        (date.fromisoformat(fye) - date.fromisoformat(x[1])).days - 365))[2]
    py_q = None
    for e in sorted(b["rev_q"]):
        if 340 <= (q - date.fromisoformat(e)).days <= 390:
            py_q = e
    if py_q is None:
        return None, "無去年同季期末"
    py_ytd = [v for s, e, v in b["rev_cum"] if e == py_q]
    if not py_ytd:
        return None, "無去年同時點累計收入"
    denom = py_tot - max(py_ytd)
    if denom <= 0:
        return None, "去年餘下期間收入非正"
    if mid <= ytd:
        return None, "指引中值不高於已報累計收入"
    return (mid - ytd) / denom - 1.0, "指引中值換算"


def main() -> None:
    picks = json.loads((CACHE / "picks.json").read_text(encoding="utf-8"))
    pop = pd.read_parquet(CACHE / "population_improvement.parquet")
    meta = pop.set_index("accessionNumber")
    rows = []
    bundles: dict[str, dict] = {}
    for kind in ("main", "backup"):
        for p in picks[kind]:
            m = meta.loc[p["acc"]]
            cik = m["cik"]
            if cik not in bundles:
                bundles[cik] = F.bundle(cik)
            b = bundles[cik]
            q_end = m["signal_q_end"]
            docp = DOCS / ("%s__EX991.txt.gz" % p["acc"].replace("-", ""))
            mid, snip = (None, "")
            if docp.exists():
                mid, snip = parse_guidance(gzip.open(docp, "rt", encoding="utf-8").read())
            c1, note = (None, "無 EX-99.1 文本")
            if q_end:
                c1, note = c1_from(mid, b, q_end)
            c2 = None
            if b.get("ok") and q_end:
                ser = b["rev_q"]
                ends = sorted(ser)
                if q_end in ends:
                    i = ends.index(q_end)
                    ys = [y for y in (F.yoy(ser, e) for e in ends[max(0, i - 4):i])
                          if y is not None]
                    c2 = sum(ys) / len(ys) if len(ys) == 4 else None
            rows.append(dict(
                event_id=p["event_id"], kind=kind, year=p["year"], bucket=p["bucket"],
                accessionNumber=p["acc"], cik=cik, ticker=m["ticker"],
                reaction_date=m["reaction_date"], signal_q_end=q_end,
                fiscal_quarter=m["fiscal_quarter"], improvement_type=m["improvement_type"],
                C1_guidance_implied_growth="" if c1 is None else round(c1, 6),
                C1_note=note, C1_snippet=snip,
                C2_prev4_avg_yoy="" if c2 is None else round(c2, 6),
                C2_note="" if c2 is not None else "資料不足",
                C3_g0="" if pd.isna(m["rev_g0"]) else round(float(m["rev_g0"]), 6),
            ))
            print("  %s %s C1=%s(%s) C2=%s C3=%s" % (
                p["event_id"], m["ticker"], rows[-1]["C1_guidance_implied_growth"], note,
                rows[-1]["C2_prev4_avg_yoy"], rows[-1]["C3_g0"]), flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(HERE / "controls_operating.csv", index=False, encoding="utf-8-sig")
    print("C1 有值 %d / %d;C2 有值 %d;C3 有值 %d" % (
        (out["C1_guidance_implied_growth"] != "").sum(), len(out),
        (out["C2_prev4_avg_yoy"] != "").sum(), (out["C3_g0"] != "").sum()))
    print("C1 註解分佈:", out["C1_note"].value_counts().to_dict())
    print("→", HERE / "controls_operating.csv")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
