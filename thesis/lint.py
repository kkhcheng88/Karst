"""thesis vault lint — health check (adapted from claude-obsidian /wiki-lint, native + lean).

Reports (never fails a build):
  - unresolved [[wiki-links]] (target page missing -> future concept page to create; OK, tracked)
  - orphan wiki pages (no inbound [[link]] and not registered in themes.yaml)
  - PENDING evidence: unchecked "[ ]" items in a thesis (the 待補 list)
  - themes.yaml <-> wiki consistency (registered wiki path exists; confidence/cycle present)

Phase-3 WS3 (docs/2026-07-08_phase3_ws3_lifecycle.md §2) — ADMISSION gate (ERRORS, block a new
theme; reported here so an existing registry entry that regresses is caught too):
  - kill_condition non-empty AND contains a trigger verb (Trigger/觸發)
  - tickers all loadable via backtest/data.py (or explicitly marked "掛牌後補"/"未上市"/"未有數據"
    in the theme's note -> pre-listing exemption)
  - cycle_stage in {early, mid, late, event-driven}
  - confidence in (0, 0.6]
  - sources >= 1 entry
  - meta_factors >= 1 entry
  - wiki page exists with valid frontmatter (existing check)
  - admitted / last_evidence are valid ISO dates

WARNINGS (not blocking): single-source cap — len(sources) < 2 AND confidence > 0.30 (spec §2 hard
rule: single-source theses should be capped at 0.30; a small early/thin-evidence bet, not a big one).

Run: python thesis/lint.py [--no-ticker-check]  (ticker loadability hits data.py / network; skip
with --no-ticker-check for a fast offline pass)
"""
import datetime
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
WIKI = os.path.join(ROOT, "wiki")
LINK_RE = re.compile(r"\[\[([^\]|]+)")
PENDING_RE = re.compile(r"^\s*[-*]?\s*\[ \]\s+(.*)$", re.M)
VALID_CYCLE_STAGES = {"early", "mid", "late", "event-driven"}
# meta_factor canonical registry (formalized 2026-07-12) -- keep in sync with the
# "META_FACTOR TAXONOMY REGISTRY" comment block at the top of thesis/themes.yaml (that's the
# documented/human-readable copy; this is the enforcement copy, same split as VALID_CYCLE_STAGES).
VALID_META_FACTORS = {
    "ai-capex", "energy-macro", "policy-defense", "china-supply", "pharma-manufacturing",
    "aerospace-capex", "building-products", "trade-policy",
    "rates-duration", "consumer",  # reserved, not yet used by any theme
}
TRIGGER_RE = re.compile(r"Trigger|觸發|to zero|de-?list|歸零|mean-revert", re.I)
PRELISTING_RE = re.compile(r"掛牌後補|未上市|未有數據|pre-listing")


def _valid_date(v):
    if v is None:
        return False
    if isinstance(v, (datetime.date, datetime.datetime)):
        return True
    try:
        datetime.date.fromisoformat(str(v))
        return True
    except Exception:
        return False


def _tickers_loadable(tickers, note, no_ticker_check=False):
    """Return list of ticker-level errors. A ticker is OK if backtest/data.py can load it,
    or if the theme's note explicitly marks it as pre-listing (掛牌後補 etc.)."""
    errs = []
    if no_ticker_check:
        return errs
    exempt = bool(PRELISTING_RE.search(note or ""))
    try:
        sys.path.insert(0, os.path.join(ROOT, ".."))
        from backtest import data as _data
    except Exception as e:
        return [f"cannot import backtest/data.py to check tickers: {e}"]
    for tk in tickers or []:
        try:
            df = _data.load(str(tk), min_rows=5)
            if df is None or len(df) == 0:
                raise RuntimeError("empty")
        except Exception:
            if not exempt:
                errs.append(f"ticker {tk} not loadable via data.py (no pre-listing marker in note)")
    return errs


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.strip().lower()).strip("-")


def _frontmatter_error(text):
    """Return an error string if the YAML frontmatter fails to parse, else None.
    Common bug: bare [[wiki-links]] in frontmatter -> invalid YAML (they belong in the body)."""
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "frontmatter not closed with ---"
    try:
        yaml.safe_load(parts[1])
        return None
    except Exception as e:
        return f"invalid YAML frontmatter: {str(e).splitlines()[0]}"


def run(no_ticker_check=False):
    pages = {}
    fm_errors = {}
    for p in glob.glob(os.path.join(WIKI, "*.md")):
        name = os.path.splitext(os.path.basename(p))[0]
        text = open(p, encoding="utf-8", errors="replace").read()
        pages[_slug(name)] = {"path": p, "name": name, "text": text}
        err = _frontmatter_error(text)
        if err:
            fm_errors[name] = err
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
    admission_errors = {}    # slug -> [errors]  (Phase-3 WS3 admission gate)
    admission_warnings = {}  # slug -> [warnings] (single-source cap etc.)
    ticker_data_issues = {}  # slug -> [ticker unloadable]  (data/ops health, non-blocking)
    meta_factor_themes = {}  # meta_factor -> [slug, ...]  (WS3 §1a hub-page-coverage check)
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

            # --- Phase-3 WS3 admission gate (docs/2026-07-08_phase3_ws3_lifecycle.md §2) ---
            errs = []
            kc = t.get("kill_condition") or ""
            if not str(kc).strip():
                errs.append("kill_condition empty")
            elif not TRIGGER_RE.search(str(kc)):
                errs.append("kill_condition has no trigger verb (Trigger/觸發)")

            tickers = t.get("tickers") or []
            if not tickers:
                errs.append("tickers empty")
            else:
                tk_issues = _tickers_loadable(tickers, t.get("note"), no_ticker_check)
                if tk_issues:
                    ticker_data_issues[slug] = tk_issues

            cs = t.get("cycle_stage")
            if cs not in VALID_CYCLE_STAGES:
                errs.append(f"cycle_stage {cs!r} not in {sorted(VALID_CYCLE_STAGES)}")

            conf = t.get("confidence")
            if conf is None or not (0 < float(conf) <= 0.6):
                errs.append(f"confidence {conf!r} not in (0, 0.6]")

            sources = t.get("sources") or []
            if len(sources) < 1:
                errs.append("sources empty (need >= 1)")

            meta_factors = t.get("meta_factors") or []
            if len(meta_factors) < 1:
                errs.append("meta_factors empty (need >= 1)")
            unknown_mf = [mf for mf in meta_factors if mf not in VALID_META_FACTORS]
            if unknown_mf:
                admission_warnings.setdefault(slug, []).append(
                    f"meta_factors {unknown_mf} not in canonical registry (thesis/themes.yaml "
                    f"header / WS3 lifecycle doc §1a) -- typo, or a genuinely new factor that "
                    f"needs registering in BOTH themes.yaml's header comment AND lint.py's "
                    f"VALID_META_FACTORS in the same commit"
                )
            for mf in meta_factors:
                meta_factor_themes.setdefault(mf, []).append(slug)

            if not _valid_date(t.get("admitted")):
                errs.append(f"admitted {t.get('admitted')!r} not a valid ISO date")
            if not _valid_date(t.get("last_evidence")):
                errs.append(f"last_evidence {t.get('last_evidence')!r} not a valid ISO date")

            if errs:
                admission_errors[slug] = errs

            # single-source cap warning (spec §2 hard rule): len(sources) < 2 and confidence > 0.30
            if conf is not None:
                try:
                    if len(sources) < 2 and float(conf) > 0.30:
                        admission_warnings.setdefault(slug, []).append(
                            f"single-source (sources={len(sources)}) but confidence {conf} > 0.30 cap"
                        )
                except (TypeError, ValueError):
                    pass

        # WS3 §1a hub-page-coverage check: any meta_factor shared by >=2 themes must have a
        # cross-theme concept page at thesis/wiki/<meta_factor>-macro-risk.md (the naming
        # convention set by the existing ai-capex-macro-risk.md). This is a WARNING (not an
        # admission error) because it's a backlog-able gap, not a per-theme defect -- but it's
        # exactly the kind of thing that silently drifted before (see energy-macro, flagged
        # 2026-07-12, still missing as of this writing).
        for mf, mf_slugs in meta_factor_themes.items():
            if len(mf_slugs) >= 2:
                hub_path = os.path.join(WIKI, f"{mf}-macro-risk.md")
                if not os.path.exists(hub_path):
                    admission_warnings.setdefault("(cross-theme)", []).append(
                        f"meta_factor '{mf}' has {len(mf_slugs)} themes ({', '.join(sorted(mf_slugs))}) "
                        f"but no hub page at thesis/wiki/{mf}-macro-risk.md (WS3 §1a rule 2)"
                    )
    except Exception as e:
        theme_issues.append(f"themes.yaml unreadable: {e}")

    orphans = [pages[s]["name"] for s in slugs
               if not inbound[s] and s not in theme_slugs]

    print("\n=== thesis lint ===")
    print(f"pages: {len(pages)} | registered themes: {len(theme_slugs)}")
    print(f"\nERRORS -- invalid frontmatter (MUST fix): {len(fm_errors)}")
    for name, err in fm_errors.items():
        print(f"  {name}: {err}  [put [[wiki-links]] in the BODY, not YAML frontmatter]")
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

    n_admission_errs = sum(len(v) for v in admission_errors.values())
    print(f"\nADMISSION gate errors (Phase-3 WS3, MUST fix): {n_admission_errs}")
    for slug, errs in admission_errors.items():
        print(f"  {slug}:")
        for e in errs:
            print(f"    - {e}")

    n_warn = sum(len(v) for v in admission_warnings.values())
    print(f"\nADMISSION gate warnings (single-source cap etc., not blocking): {n_warn}")
    for slug, warns in admission_warnings.items():
        for w in warns:
            print(f"  {slug}: {w}")

    n_ticker_issues = sum(len(v) for v in ticker_data_issues.values())
    print(f"\nticker data-availability issues (data.py load failed; NOT an admission-gate error --"
          f" data/ops health only): {n_ticker_issues}")
    for slug, issues in ticker_data_issues.items():
        for i in issues:
            print(f"  {slug}: {i}")

    print("\n(Unresolved links are OK -- they mark concept pages worth writing next, not errors.)")
    return n_admission_errs + len(fm_errors)


if __name__ == "__main__":
    _no_ticker_check = "--no-ticker-check" in sys.argv
    _n_errors = run(no_ticker_check=_no_ticker_check)
    sys.exit(1 if _n_errors else 0)
