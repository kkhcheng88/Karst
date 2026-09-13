# -*- coding: utf-8 -*-
"""KARST-236 診斷:某包某欄在訊號季的全部稿內命中(值 + 相對差 + 上下文),只讀。"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import finlib_fixed as FF  # noqa: E402
import s22_fix235_rebuild as R  # noqa: E402

FIELDS = {"revenue": FF.REV_TAGS, "gross_profit": FF.GP_TAGS,
          "operating_income": FF.OI_TAGS, "ocf": FF.OCF_TAGS}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    args = [a for a in sys.argv[1:] if not a.startswith("--tol=")]
    tol = R.TOL
    for a in sys.argv[1:]:
        if a.startswith("--tol="):
            tol = float(a.split("=", 1)[1])
    eid = args[0]
    p = json.load(open(HERE / "packets" / ("%s.json" % eid), encoding="utf-8"))
    cik = str(p["1_事件識別"]["cik"]).zfill(10)
    sig = p["4_財務數列"]["signal_q_end"]
    text = (p["2_觸發資料"] or {}).get("ex991_full_text") or ""
    facts = FF.load_facts(cik)
    names = args[1:] or list(FIELDS)
    print("== %s sig=%s" % (eid, sig))
    for name in names:
        tags = FIELDS[name]
        if name == "ocf":
            base = FF.ocf_series(facts).get(sig)
        else:
            base = FF.quarterly_full(facts, tags, derive_fy=True).get(
                sig, {}).get("value")
        tg = R.sig_targets(facts, tags, sig, base)
        ytd = R.ytd_values(facts, tags, sig)
        print("  [%s] truth=%s ytd=%s" % (name, base, ytd))
        for rank, v in enumerate(tg):
            if v in (None, 0):
                continue
            for m in R.NUM_RX.finditer(text):
                raw = R._num(m.group(1))
                if raw is None or raw == 0:
                    continue
                unit = (m.group(2) or "").lower()
                cands = ([raw * R.MULT[unit]] if unit in R.MULT else []) + \
                        [raw * s for s in (1.0, 1e3, 1e6, 1e9)]
                c = next((c for c in cands
                          if c and abs(abs(c) / abs(v) - 1.0) <= tol), None)
                if c is None:
                    continue
                ctx = text[max(0, m.start() - 200):m.end() + 40]
                if not R.KW[name].search(ctx):
                    continue
                echo = any(y not in (None, 0)
                           and abs(abs(c) / abs(y) - 1.0) <= tol for y in ytd)
                snip = re.sub(r"\s+", " ", text[max(0, m.start() - 110):
                                                m.end() + 20])
                print("    r%d v=%-16s text=%-16s rel=%.5f ytd_echo=%s pos=%s | %s"
                      % (rank, v, c, abs(abs(c) / abs(v) - 1.0), echo,
                         m.start(), snip))
        print("    PICK = %s" % R.pick_text(text, tg, name, ytd))


if __name__ == "__main__":
    main()
