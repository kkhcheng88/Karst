"""Build thin source-node stubs (layer ②) from the gooptions research manifest.

One lightweight markdown node per report in thesis/wiki/sources/<issue>-<slug>.md:
  - frontmatter = valid-YAML scalars only (NO [[wiki-links]] -- breaks the parser)
  - body carries the card summary + INLINE [[links]] to the theme-cluster thesis and each ticker
  - the FULL body stays in layer ① (.raw + corpus.db); the node just points there.

So the 102 reports appear in the Obsidian graph as connected nodes (report -> [[cluster]] -> [[ticker]])
WITHOUT dumping raw prose into the vault. At scale you would stub-on-cite instead of stub-all; at 102
(small, all-relevant) we stub them all. Re-run after downloading new reports. Idempotent (overwrites).

    python thesis/build_source_nodes.py
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(ROOT, ".raw", "gooptions", "research-manifest.json")
OUT = os.path.join(ROOT, "wiki", "sources")

# theme-cluster -> keyword regex (first match wins). Cluster slug == the thesis page it feeds.
CLUSTERS = [
    ("memory-supercycle", r"記憶體|memory|dram|hbm|nand|sndk|micron|\bmu\b|cmx|wf6|tungsten"),
    ("ai-power-grid", r"電力|電網|grid|power|hvdc|btm|互聯|變壓|utilit|datacenter|1gw|tco"),
    ("photonics-optical", r"光|photonic|optical|cpo|interconnect|lpo|\bdsp\b|laser|\binp\b|dci|ocs|silicon photon"),
    ("advanced-packaging", r"封裝|packaging|cowos|emib|substrate|glass|pcb|glass-cloth|hoya"),
    ("tpu-custom-silicon", r"tpu|asic|broadcom|自研|custom silicon|inference|arms-dealer"),
    ("semicap-equipment", r"semicap|equipment|foundry|intel|製程|aehr|burn-in|mksi|litho"),
    ("space-satellite", r"太空|space|satellite|starlink|asts|d2d|golden dome|launch"),
    ("rare-earth-materials", r"稀土|rare-earth|\bmp\b|磁|indium|gallium|銦|鎵|材料"),
    ("oil-gas-energy", r"\boil\b|油|天然氣|natural gas|iran|opec|\beqt\b|xom"),
    ("nuclear", r"核能|nuclear|smr|oklo|uranium|\bleu\b"),
]


def cluster_of(it):
    hay = " ".join([it.get("slug", ""), it.get("theme", "") or "", it.get("thesis", "") or "",
                    " ".join(it.get("tickers") or [])]).lower()
    for slug, pat in CLUSTERS:
        if re.search(pat, hay):
            return slug
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    man = json.load(open(MANIFEST, encoding="utf-8"))
    items = man.get("items", [])
    n = 0
    counts = {}
    for it in items:
        slug = it.get("slug", "")
        issue = (it.get("issue") or "").lstrip("#") or "0000"
        cl = cluster_of(it)
        counts[cl] = counts.get(cl, 0) + 1
        card = it.get("card") or {}
        title = card.get("title") or it.get("theme") or slug
        tickers = it.get("tickers") or []
        raw_file = f".raw/gooptions/research/{issue}-{slug}.md"
        stats = "; ".join(f"{s.get('lbl')}={s.get('val')}" for s in (card.get("stats") or []))
        ticker_links = " ".join(f"[[{t}]]" for t in tickers)
        cluster_link = f"[[{cl}]]" if cl else "_(未歸類)_"
        fm = [
            "---",
            "type: source",
            f"slug: {slug}",
            f"issue: '#{issue}'",
            f"url: {it.get('url','')}",
            f"publishedAt: {it.get('publishedAt','')}",
            f"thesisType: {it.get('thesisType','')}",
            f"primary_ticker: '{it.get('primary_ticker','') or ''}'",
            "tickers: [" + ", ".join(f"'{t}'" for t in tickers) + "]",
            f"cluster: {cl or ''}",
            "source: gooptions.cc/trend-core-research",
            "tier: 2",
            "---",
            "",
            f"# {title}",
            "",
            f"> **thesisType:** {it.get('thesisType','')} · **published:** {it.get('publishedAt','')}"
            f" · **read:** {it.get('readMinutes','')}min  ",
            f"> **thesis:** {it.get('thesis','')}  ",
            f"> **dek:** {card.get('dek','')}  ",
            f"> **stats:** {stats}",
            "",
            f"**主題叢:** {cluster_link}　**標的:** {ticker_links}",
            "",
            f"**全文(layer ①):** `{raw_file}` · `python thesis/corpus.py get {issue}-{slug}`  ",
            f"**來源:** {it.get('url','')}  ",
            "",
            "> 薄來源節點(Tier-2)。全文在語料庫,非本頁。蒸餾成 thesis 時由 `[[cluster]]` 綜合頁引用。",
        ]
        with open(os.path.join(OUT, f"{issue}-{slug}.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(fm))
        n += 1
    print(f"[source-nodes] wrote {n} nodes -> {OUT}")
    print("cluster distribution:")
    for slug, _ in CLUSTERS:
        if counts.get(slug):
            print(f"  {slug:22s} {counts[slug]}")
    if counts.get(None):
        print(f"  {'(unclustered)':22s} {counts[None]}")


if __name__ == "__main__":
    main()
