"""KARST-152:文本抓取覆蓋率與缺失名單(驗收條件一要求入 meta)。"""
from __future__ import annotations

import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
SLICES = ["2015-06-30", "2019-06-30", "2023-06-30"]


def main() -> int:
    m = json.loads((OUT / "text_manifest.json").read_text(encoding="utf-8"))
    cov: dict = {
        "universe": 574,
        "note": "宇宙 = daily_close.parquet 584 欄減 10 隻 ETF;缺失原因見各切片 missing_reasons",
    }
    for sl in SLICES:
        ok = [k.split("|")[0] for k, v in m.items() if k.endswith(sl) and v.get("ok")]
        miss = {k.split("|")[0]: v.get("why", "?")
                for k, v in m.items() if k.endswith(sl) and not v.get("ok")}
        reasons = collections.Counter(str(w).split(":")[0].split("(")[0].strip()
                                      for w in miss.values())
        cov[sl] = {"n_ok": len(ok), "n_missing": len(miss),
                   "missing_reasons": dict(reasons), "missing_tickers": sorted(miss)}
        print(sl, len(ok), "ok /", len(miss), "missing", dict(reasons))
    (OUT / "coverage_meta.json").write_text(json.dumps(cov, ensure_ascii=False, indent=1),
                                            encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
