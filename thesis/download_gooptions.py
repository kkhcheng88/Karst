"""Download gooptions.cc Trend-Core RESEARCH reports to a local raw corpus.

These are the site's FREE public research reports (the ~100 analyst-grade write-ups it lists at
/trend-core-research/ and posts on Facebook to attract subscribers) -- NOT a paid feature.
Stored locally for private research reference + citation (Tier-2 opinion / crowding signal).

Canonical index: https://gooptions.cc/trend-core-research-manifest.json  (items[] with slug, url,
issue, publishedAt, thesis, thesisType, theme, tickers, card). Each report body is SSR HTML inside
<article class="article"> at https://gooptions.cc<url> -- no JS/API/login needed.

Store: thesis/.raw/gooptions/research/<issue>-<slug>.md  (gitignored -- local corpus, re-downloadable)
       thesis/.raw/gooptions/research-manifest.json      (the raw index snapshot)
Polite: rate-limited + resumable (skips reports already saved). Run:
    python thesis/download_gooptions.py            # = research
    python thesis/download_gooptions.py research
"""
import html as _html
import json
import os
import re
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, ".raw", "gooptions")
RESEARCH = os.path.join(RAW, "research")
UA = "Mozilla/5.0 (compatible; Karst-research/1.0; private research)"
BASE = "https://gooptions.cc"
MANIFEST = BASE + "/trend-core-research-manifest.json"
PAUSE = 1.2  # seconds between report fetches -- keep Cloudflare / their host happy


def _get(url, tries=3):
    h = {"User-Agent": UA, "Accept": "text/html,application/json"}
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise last


def _article_markdown(page_html):
    """Extract <article class="article"> and convert to lightweight markdown text."""
    m = re.search(r"(?is)<article[^>]*>(.*?)</article>", page_html)
    frag = m.group(1) if m else page_html
    frag = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", frag)
    # structure-preserving conversions
    frag = re.sub(r"(?i)<h1[^>]*>", "\n\n# ", frag)
    frag = re.sub(r"(?i)<h2[^>]*>", "\n\n## ", frag)
    frag = re.sub(r"(?i)<h3[^>]*>", "\n\n### ", frag)
    frag = re.sub(r"(?i)<h[4-6][^>]*>", "\n\n#### ", frag)
    frag = re.sub(r"(?i)</(h[1-6]|p|div|section|tr)>", "\n", frag)
    frag = re.sub(r"(?i)<li[^>]*>", "\n- ", frag)
    frag = re.sub(r"(?i)<br\s*/?>", "\n", frag)
    frag = re.sub(r"(?i)</td>\s*<td[^>]*>", " | ", frag)
    frag = re.sub(r"(?s)<[^>]+>", "", frag)
    frag = _html.unescape(frag)
    frag = re.sub(r"[ \t]+", " ", frag)
    frag = re.sub(r"\n\s*\n\s*\n+", "\n\n", frag)
    return frag.strip()


def _yaml_list(xs):
    # quote each item -> YAML-safe (tickers like ON/NO/YES would else coerce to bool)
    return "[" + ", ".join(f"'{x}'" for x in (xs or [])) + "]"


def download_research():
    os.makedirs(RESEARCH, exist_ok=True)
    man = json.loads(_get(MANIFEST))
    with open(os.path.join(RAW, "research-manifest.json"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    items = man.get("items", [])
    print(f"[research] manifest: {len(items)} reports (version {man.get('version')},"
          f" generated {man.get('generated_at')})")
    new = skipped = failed = 0
    for i, it in enumerate(items, 1):
        slug = it.get("slug", "")
        issue = (it.get("issue") or "").lstrip("#") or "0000"
        fn = f"{issue}-{slug}.md"
        path = os.path.join(RESEARCH, fn)
        if os.path.exists(path):
            skipped += 1
            continue
        url = BASE + it.get("url", "/" + slug + "/")
        try:
            body = _article_markdown(_get(url))
        except Exception as e:
            print(f"[research] {i}/{len(items)} {slug} -> ERR {e}")
            failed += 1
            time.sleep(PAUSE)
            continue
        card = it.get("card") or {}
        stats = "; ".join(f"{s.get('lbl')}={s.get('val')}({s.get('tone')})"
                          for s in (card.get("stats") or []))
        fm = [
            "---",
            f"issue: '#{issue}'",
            f"slug: {slug}",
            f"url: {url}",
            f"publishedAt: {it.get('publishedAt','')}",
            f"readMinutes: {it.get('readMinutes','')}",
            f"thesisType: {it.get('thesisType','')}",
            f"primary_ticker: '{it.get('primary_ticker','') or ''}'",
            f"tickers: {_yaml_list(it.get('tickers'))}",
            "source: gooptions.cc/trend-core-research",
            "tier: 2",
            "---",
            "",
            f"# {card.get('title') or it.get('theme') or slug}",
            "",
            f"> **theme:** {it.get('theme','')}  ",
            f"> **thesis:** {it.get('thesis','')}  ",
            f"> **dek:** {card.get('dek','')}  ",
            f"> **stats:** {stats}",
            "",
            "---",
            "",
            body,
        ]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(fm))
        new += 1
        print(f"[research] {i}/{len(items)} saved {fn} ({len(body)} chars)")
        time.sleep(PAUSE)
    print(f"[research] DONE. new={new} skipped(existing)={skipped} failed={failed} -> {RESEARCH}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "research"
    if mode == "research":
        download_research()
    else:
        print("usage: python thesis/download_gooptions.py research")
