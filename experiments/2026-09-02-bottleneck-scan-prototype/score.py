"""KARST-142: turn the frozen annotations into the three headline numbers
and the 657-company production cost estimate.

Scores below are transcribed from annotations.md, which was produced by reading
texts/*_candidates.md against the frozen lexicon v0. Nothing here re-judges the
text; this file only does arithmetic so the report's numbers are reproducible.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

# doc -> (arm, D1..D6), label_reliable
SCORES = {
    "ENPH_FY2021": ("bottleneck", [0, 0, 0, 1, 1, 0], True),
    "ENPH_FY2019": ("normal",     [0, 0, 0, 0, 0, 0], True),
    "GNRC_FY2021": ("bottleneck", [1, 1, 0, 1, 1, 0], True),
    "GNRC_FY2019": ("normal",     [0, 0, 0, 1, 0, 0], True),
    "ROK_FY2022":  ("bottleneck", [1, 1, 1, 1, 1, 0], True),
    "ROK_FY2019":  ("normal",     [0, 0, 0, 1, 0, 0], True),
    # label contradicted by the text itself (backlog flat, margins improved)
    "POWL_FY2024": ("bottleneck", [0, 1, 0, 0, 0, 0], False),
    "POWL_FY2019": ("normal",     [0, 0, 1, 0, 0, 0], True),
    # label contradicted by the text itself ("no significant component
    # shortages to date"; labour constraints "since abated")
    "BE_FY2024":   ("bottleneck", [0, 0, 0, 0, 1, 0], False),
    "BE_FY2019":   ("normal",     [0, 0, 1, 0, 0, 0], True),
    "CMI_FY2021":  ("bottleneck", [0, 0, 0, 1, 1, 0], True),
    "CMI_FY2019":  ("normal",     [0, 0, 0, 0, 0, 0], True),
}

THRESHOLD = 3          # frozen in lexicon v0 section 4
D5_INDEX = 4           # supply constraint dimension

UNIVERSE = 657         # companies in the Karst universe
QUARTERS = 4
# indicative LLM input pricing, USD per 1M input tokens, mid-tier model
PRICE_PER_MTOK = 3.0


def rates(threshold: int, dim: int | None = None, reliable_only: bool = False):
    hit = fp = nb = nn = 0
    for _doc, (arm, dims, ok) in SCORES.items():
        if reliable_only and arm == "bottleneck" and not ok:
            continue
        flagged = (dims[dim] == 1) if dim is not None else (sum(dims) >= threshold)
        if arm == "bottleneck":
            nb += 1
            hit += flagged
        else:
            nn += 1
            fp += flagged
    return hit, nb, fp, nn


def main() -> int:
    summary = json.loads((HERE / "candidate_summary.json").read_text(encoding="utf-8"))
    full = [r["full_tokens"] for r in summary]
    cand = [r["cand_tokens"] for r in summary]
    chars = [r["full_chars"] for r in summary]

    avg_full = sum(full) / len(full)
    avg_cand = sum(cand) / len(cand)

    print("=== scores ===")
    b = [sum(d) for _, (a, d, _) in SCORES.items() if a == "bottleneck"]
    n = [sum(d) for _, (a, d, _) in SCORES.items() if a == "normal"]
    print(f"bottleneck arm totals {b}  mean {sum(b)/len(b):.2f}")
    print(f"normal     arm totals {n}  mean {sum(n)/len(n):.2f}")

    print("\n=== headline (frozen threshold >= 3) ===")
    h, nb, fp, nn = rates(THRESHOLD)
    print(f"hit rate            {h}/{nb} = {h/nb:.0%}")
    print(f"false positive rate {fp}/{nn} = {fp/nn:.0%}")

    print("\n=== post-hoc sensitivity (NOT the graded result) ===")
    for label, kw in [
        ("threshold >= 2", dict(threshold=2)),
        ("D5 only", dict(threshold=0, dim=D5_INDEX)),
        ("D5 only, reliable labels", dict(threshold=0, dim=D5_INDEX, reliable_only=True)),
        ("threshold >= 3, reliable labels", dict(threshold=3, reliable_only=True)),
    ]:
        h, nb, fp, nn = rates(**kw)
        print(f"{label:<34} hit {h}/{nb} = {h/nb:>4.0%}   fp {fp}/{nn} = {fp/nn:>4.0%}")

    print("\n=== per-document cost ===")
    print(f"MD&A chars      mean {sum(chars)/len(chars):>9,.0f}  "
          f"min {min(chars):,}  max {max(chars):,}")
    print(f"A full tokens   mean {avg_full:>9,.0f}  min {min(full):,}  max {max(full):,}")
    print(f"B cand tokens   mean {avg_cand:>9,.0f}  min {min(cand):,}  max {max(cand):,}")
    print(f"compression A->B  {avg_full/avg_cand:.1f}x")

    print(f"\n=== production estimate: {UNIVERSE} companies x {QUARTERS} quarters ===")
    docs = UNIVERSE * QUARTERS
    for name, avg in (("A full-text", avg_full), ("B pre-filtered", avg_cand)):
        tok_y = docs * avg
        print(f"{name:<16} {docs:,} docs/yr  {tok_y/1e6:>7.1f}M tok/yr  "
              f"${tok_y/1e6*PRICE_PER_MTOK:>7.2f}/yr  "
              f"${tok_y/1e6*PRICE_PER_MTOK/QUARTERS:>6.2f}/quarter")
    reqs = docs * 2
    print(f"EDGAR requests   {reqs:,}/yr at 10 req/s cap -> "
          f"{reqs/10/60:.0f} min/yr of pure network time")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
