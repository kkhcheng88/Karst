"""thesis vault lint — health check (adapted from claude-obsidian /wiki-lint, native + lean).

Reports (never fails a build):
  - unresolved [[wiki-links]] (target page missing -> future concept page to create; OK, tracked)
  - orphan wiki pages (no inbound [[link]] and not registered in themes.yaml)
  - PENDING evidence: unchecked "[ ]" items in a thesis (the 待補 list)
  - themes.yaml <-> wiki consistency (registered wiki path exists; confidence/cycle present)

Run: python thesis/lint.py
"""
import glob
import os
import re

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
WIKI = os.path.join(ROOT, "wiki")
LINK_RE = re.compile(r"\[\[([^\]|]+)")
PENDING_RE = re.compile(r"^\s*[-*]?\s*\[ \]\s+(.*)$", re.M)


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.strip().lower()).strip("-")


def run():
    pages = {}
    for p in glob.glob(os.path.join(WIKI, "*.md")):
        name = os.path.splitext(os.path.basename(p))[0]
        pages[_slug(name)] = {"path": p, "name": name,
                              "text": open(p, encoding="utf-8", errors="replace").read()}
    slugs = set(pages)

    links_out = {}          # page -> set(target slugs)
    inbound = {s: set() for s in slugs}
    unresolved = {}
    pending = {}
    for s, pg in pages.items():
        targets = {_slug(m) for m in LINK_RE.findall(pg["text"])}
        links_out[s] = targets
        for t in targets:
            if t in slugs:
                inbound[t].add(s)
            else:
                unresolved.setdefault(t, set()).add(pg["name"])
        pend = PENDING_RE.findall(pg["text"])
        if pend:
            pending[pg["name"]] = pend

    # themes.yaml consistency
    themes_path = os.path.join(ROOT, "themes.yaml")
    theme_slugs, theme_issues = set(), []
    try:
        themes = (yaml.safe_load(open(themes_path, encoding="utf-8")) or {}).get("themes", {}) or {}
        for slug, t in themes.items():
            theme_slugs.add(_slug(slug))
            wp = t.get("wiki", "")
            if wp and not os.path.exists(os.path.join(ROOT, "..", wp)):
                theme_issues.append(f"{slug}: wiki path missing ({wp})")
            if t.get("confidence") is None:
                theme_issues.append(f"{slug}: no confidence")
            if not t.get("cycle_stage"):
                theme_issues.append(f"{slug}: no cycle_stage")
            if not t.get("kill_condition"):
                theme_issues.append(f"{slug}: no kill_condition")
    except Exception as e:
        theme_issues.append(f"themes.yaml unreadable: {e}")

    orphans = [pages[s]["name"] for s in slugs
               if not inbound[s] and s not in theme_slugs]

    print("\n=== thesis lint ===")
    print(f"pages: {len(pages)} | registered themes: {len(theme_slugs)}")
    print(f"\nPENDING evidence ([ ] items to fill): {sum(len(v) for v in pending.values())}")
    for name, items in pending.items():
        print(f"  {name}: {len(items)} open")
        for it in items[:6]:
            print(f"    - {it[:90]}")
    print(f"\nunresolved [[links]] (future concept pages to create): {len(unresolved)}")
    for t, srcs in sorted(unresolved.items()):
        print(f"  [[{t}]]  <- {', '.join(sorted(srcs))}")
    print(f"\norphan pages (no inbound link, not a registered theme): {len(orphans)}")
    for o in orphans:
        print(f"  {o}")
    print(f"\nthemes.yaml issues: {len(theme_issues)}")
    for i in theme_issues:
        print(f"  {i}")
    print("\n(Unresolved links are OK -- they mark concept pages worth writing next, not errors.)")


if __name__ == "__main__":
    run()
