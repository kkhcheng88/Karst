"""KARST-142: pull candidate sentences for each lexicon-v0 dimension.

The seed terms come from bottleneck-lexicon-v0.md (frozen before any text was
read). They are a RETRIEVAL device only -- whether a candidate counts as a hit
is decided by reading it against exclusion rules R1-R4, not by the match.

Two production architectures are being costed here:
  A. whole MD&A into the LLM          -> cost = full token count
  B. keyword pre-filter, LLM reads only candidates -> cost = candidate tokens

Run: PYTHONUTF8=1 python extract_candidates.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEXTS = HERE / "texts"

SEEDS: dict[str, list[str]] = {
    "D1_lead_time": [
        r"lead[- ]times?", r"delivery (?:schedule|time|cycle)s?",
        r"deliver(?:y|ies) (?:were|was|have been) (?:delayed|extended)",
    ],
    "D2_capacity": [
        r"capacity constrain", r"capacity[- ]constrained", r"constrained capacity",
        r"(?:at|near) (?:full|maximum) (?:capacity|utilization)",
        r"capacity (?:limitation|utilization|expansion)", r"expand(?:ing|ed)? (?:our )?capacity",
        r"production (?:was )?limited", r"insufficient capacity", r"additional (?:shifts|lines)",
    ],
    "D3_backlog": [
        r"backlog", r"remaining performance obligation", r"book[- ]to[- ]bill",
        r"orders (?:exceeded|outpaced)",
    ],
    "D4_pricing": [
        r"price increase", r"pricing action", r"higher (?:average )?selling price",
        r"increased? (?:our )?prices?", r"surcharge", r"price realization", r"favorable price",
    ],
    "D5_supply": [
        r"supply constrain", r"shortages?", r"component availability", r"allocation",
        r"supply chain (?:disruption|constraint|challenge|issue|pressure)",
        r"unable to (?:obtain|source|secure)", r"raw material availability",
        r"freight", r"logistic", r"semiconductor",
    ],
    "D6_visibility": [
        r"sold out", r"visibility", r"committed capacity", r"capacity (?:is )?reserved",
        r"orders? (?:further )?in advance", r"multi[- ]year (?:supply|purchase) agreement",
        r"secure (?:future )?(?:supply|capacity)",
    ],
}

# Terms that signal supply pressure EASING -- lexicon rule R3 counts these
# against a hit, so they are retrieved too and shown to the reader.
EASING = re.compile(
    r"eas(?:ed|ing)|normaliz|improved availability|has recovered|abated|"
    r"alleviat|no longer constrained|returned to normal|shorter lead[- ]times?", re.I)

# Hypothetical / forward-looking framing -- lexicon rule R1 disqualifies these.
HEDGE = re.compile(r"\b(?:may|could|might|would|if we|risk that|expect to|intend to)\b", re.I)

COMPILED = {d: [re.compile(p, re.I) for p in pats] for d, pats in SEEDS.items()}


def sentences(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z“(])", flat)
    return [p.strip() for p in parts if len(p.strip()) > 40]


def main() -> int:
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    summary = []
    for rec in manifest:
        name = f"{rec['ticker']}_FY{rec['fy']}_{rec['arm']}"
        text = (TEXTS / f"{name}_mdna.txt").read_text(encoding="utf-8")
        sents = sentences(text)

        per_dim: dict[str, list[str]] = {d: [] for d in SEEDS}
        seen: set[str] = set()
        for s in sents:
            for dim, pats in COMPILED.items():
                if any(p.search(s) for p in pats):
                    if len(s) > 1200:
                        s = s[:1200] + " ..."
                    per_dim[dim].append(s)
                    seen.add(s)

        lines = [f"# {name}  ({rec['period']})",
                 f"# source: {rec['url']}",
                 f"# full MD&A: {rec['chars']:,} chars / ~{rec['est_tokens']:,} tokens",
                 ""]
        for dim in SEEDS:
            hits = per_dim[dim]
            lines.append(f"## {dim}  ({len(hits)} candidate sentences)")
            for s in hits:
                flags = []
                if HEDGE.search(s):
                    flags.append("HEDGE?R1")
                if EASING.search(s):
                    flags.append("EASING?R3")
                tag = ("  [" + ",".join(flags) + "]") if flags else ""
                lines.append(f"- {s}{tag}")
            lines.append("")
        body = "\n".join(lines)
        (TEXTS / f"{name}_candidates.md").write_text(body, encoding="utf-8")

        cand_chars = sum(len(s) for s in seen)
        row = {
            "doc": name, "arm": rec["arm"], "ticker": rec["ticker"], "fy": rec["fy"],
            "full_chars": rec["chars"], "full_tokens": rec["est_tokens"],
            "sentences": len(sents),
            "cand_sentences": len(seen),
            "cand_chars": cand_chars, "cand_tokens": round(cand_chars / 4),
            **{d: len(per_dim[d]) for d in SEEDS},
        }
        summary.append(row)
        print(f"{name:<28} sents={len(sents):>4} cand={len(seen):>3} "
              f"full~{rec['est_tokens']:>6,}tok  cand~{row['cand_tokens']:>5,}tok  "
              + " ".join(f"{d.split('_')[0]}:{len(per_dim[d])}" for d in SEEDS))

    (HERE / "candidate_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
