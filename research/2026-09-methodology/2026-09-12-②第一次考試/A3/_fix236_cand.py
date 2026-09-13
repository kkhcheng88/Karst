# -*- coding: utf-8 -*-
"""KARST-236 診斷:訊號季「各 tag 候選值 × 稿內命中」逐格看(只讀,不改檔)。"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
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
        r"(?i)(operating income|operating profit|income from operations|loss from operations|"
        r"income \(loss\) from operations)"),
    "ocf": re.compile(r"(?i)(operating activities|cash flow|net cash provided)"),
}
TAGS = {"revenue": FF.REV_TAGS, "gross_profit": FF.GP_TAGS,
        "operating_income": FF.OI_TAGS, "ocf": FF.OCF_TAGS}


def _num(s):
    t = s.strip()
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()").replace("$", "").replace(",", "").strip()
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def matches(text, v, kw, tol=0.005):
    if not text or v in (None, 0):
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
            if c and abs(c / v - 1.0) <= tol:
                ctx = text[max(0, m.start() - 200):m.end() + 40]
                out.append((c, abs(c / v - 1.0), bool(kw.search(ctx)), m.start(),
                            re.sub(r"\s+", " ", ctx[-110:])))
                break
    return out


def tag_candidates(facts, tags, end):
    """每個 tag 在該期末的值(80–100 日直接值優先,否則年報期末推算)。"""
    out = []
    for i, t in enumerate(tags):
        rep = FF._first_report(FF.unit_rows(facts, t), 80, 100)
        hit = next((v for (_s, e), (v, _f) in rep.items() if e == end), None)
        if hit is None:
            y = FF._year_end_quarters(facts, [t])
            if end in y:
                hit = y[end][0]
        if hit is not None:
            out.append((i, t, hit))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    for eid in NINE:
        p = json.load(open(HERE / "packets" / ("%s.json" % eid), encoding="utf-8"))
        cik = str(p["1_事件識別"]["cik"]).zfill(10)
        f = p["4_財務數列"]
        sig = f["signal_q_end"]
        text = (p["2_觸發資料"] or {}).get("ex991_full_text") or ""
        facts = FF.load_facts(cik)
        row = next((q for q in f["quarters"] if q["period_end"] == sig), {})
        print("==== %s sig=%s cur_rev=%s ex991=%s" % (
            eid, sig, row.get("revenue"), row.get("revenue_ex991")))
        for name, tags in TAGS.items():
            cands = tag_candidates(facts, tags, sig)
            print("  [%s]" % name)
            for i, t, v in cands:
                h = matches(text, v, KW[name])
                print("    tag%d %-56s v=%-16s hits=%d" % (i, t[:56], v, len(h)))
                for c, rel, kw, pos, snip in sorted(h, key=lambda x: x[1])[:2]:
                    print("        text=%-16s rel=%.5f kw=%s | %s" % (c, rel, kw, snip))


if __name__ == "__main__":
    main()
