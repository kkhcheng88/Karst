# -*- coding: utf-8 -*-
"""KARST-236 診斷:九包訊號季四欄在 EX-99.1 稿內的數字匹配(只讀,不改檔)。"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import finlib_fixed as FF  # noqa: E402

NINE = ["E017", "E021", "E022", "E024", "E025", "E047", "E057", "E073"]

NUM_RX = re.compile(r"(?<![\w.])(\$?\s?\(?\d[\d,]*(?:\.\d+)?\)?)\s*"
                    r"(thousand|thousands|million|millions|billion|billions|mn|bn|[MBK])?\b")
MULT = {"thousand": 1e3, "thousands": 1e3, "k": 1e3,
        "million": 1e6, "millions": 1e6, "mn": 1e6, "m": 1e6,
        "billion": 1e9, "billions": 1e9, "bn": 1e9, "b": 1e9}
KW = {
    "revenue": re.compile(r"(?i)\b(revenue|revenues|net sales|total sales|sales)\b"),
    "gross_profit": re.compile(r"(?i)(gross profit|gross margin)"),
    "operating_income": re.compile(
        r"(?i)(operating income|operating profit|income from operations|loss from operations)"),
    "ocf": re.compile(r"(?i)(operating activities|cash flow|net cash provided)"),
}


def _num(s):
    s = s.strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace("$", "").replace(",", "").strip()
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def match(text, v, kw, tol=0.005):
    """回 [(值, 位置, 有無關鍵字, 片段)];v=0 或 None 回 []。"""
    if not text or v is None or v == 0:
        return []
    out = []
    for m in NUM_RX.finditer(text):
        raw = _num(m.group(1))
        if raw is None or raw == 0:
            continue
        unit = (m.group(2) or "").lower()
        cands = []
        if unit in MULT:
            cands.append(raw * MULT[unit])
        for sc in (1.0, 1e3, 1e6, 1e9):
            cands.append(raw * sc)
        for c in cands:
            if c != 0 and abs(c / v - 1.0) <= tol:
                ctx = text[max(0, m.start() - 200):m.end() + 60]
                out.append((c, m.start(), bool(kw.search(ctx)),
                            re.sub(r"\s+", " ", ctx[-90:])))
                break
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    for eid in NINE:
        p = json.load(open(HERE / "packets" / ("%s.json" % eid), encoding="utf-8"))
        cik = str(p["1_事件識別"]["cik"]).zfill(10)
        t1 = str(p["1_事件識別"]["T1_分析截止"])[:10]
        f = p["4_財務數列"]
        sig = f["signal_q_end"]
        text = (p["2_觸發資料"] or {}).get("ex991_full_text") or ""
        facts = FF.load_facts(cik)
        vals = {
            "revenue": FF.quarterly_full(facts, FF.REV_TAGS, derive_fy=True).get(sig),
            "gross_profit": FF.quarterly_full(facts, FF.GP_TAGS, derive_fy=True).get(sig),
            "operating_income": FF.quarterly_full(facts, FF.OI_TAGS, derive_fy=True).get(sig),
            "ocf": None}
        ocfs = FF.ocf_series(facts)
        if sig in ocfs:
            vals["ocf"] = {"value": ocfs[sig], "first_filed": ""}
        row = next((q for q in f["quarters"] if q["period_end"] == sig), {})
        print("==== %s T1=%s sig=%s chars=%d" % (eid, t1, sig, len(text)))
        for name, r in vals.items():
            v = r["value"] if r else None
            hits = match(text, v, KW[name])
            kh = [h for h in hits if h[2]]
            print("  %-17s fix_v=%-16s cur=%-16s ex991=%s hits=%d(kw %d)" % (
                name, v, row.get(name), row.get(name + "_ex991"), len(hits), len(kh)))
            for h in (kh or hits)[:2]:
                print("      v=%s kw=%s | %s" % (h[0], h[2], h[3]))


if __name__ == "__main__":
    main()
