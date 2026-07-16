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

P2 formula lint (docs/2026-07-15_quantification_review.md 提案2 + DESIGN §4a/§4c, added 2026-07-16):
  - ERROR: if a theme's wiki has a "## confidence 推導" section with machine-readable 4-KPI
    subscores (moat/capital/valuation/growth, format "KPI X/2"), recompute confidence via
    thesis/confidence_formula.py (crowding from thesis/.raw/crowding_composite.json, cycle_stage
    + sources count from themes.yaml) and compare to the recorded themes.yaml confidence; diff
    > 0.01 -> error listing wiki subscores, crowding, cycle, formula output, themes.yaml value.
  - WARNING: subscores section present but not machine-readable (couldn't extract all 4 KPIs), or
    crowding_composite.json unreadable/missing the theme (falls back to a conservative 40-60 band
    assumption and warns).
  - WARNING (§4c): any node tagged `magnitude_unconfirmed: true` but the wiki has no `red_team`
    section -- the red-team verdict that justifies flagging the leg must be recorded.

Run: python thesis/lint.py [--no-ticker-check]  (ticker loadability hits data.py / network; skip
with --no-ticker-check for a fast offline pass)
"""
import datetime
import glob
import json
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import confidence_formula as cf  # noqa: E402  (純函數模組,見 thesis/confidence_formula.py)

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

# --- P2 formula lint (docs/2026-07-15_quantification_review.md 提案2 + DESIGN §4a/§4c) ---
# 「## confidence 推導」段(第一個出現,到下一個 "## " 級標題為止)—— 有意窄範圍,
# 唔會誤食上面 "### 4-KPI" 證據段(三個 # 唔會撞到 "\n## " 邊界)或下面 red_team 段。
FORMULA_SECTION_RE = re.compile(r"##\s*confidence\s*推導.*?(?=\n##\s|\Z)", re.S)
# 每個 KPI 關鍵字後、30 字內出現嘅第一個 "X/2"(X 可以係半分,如 1.5)當該格 subscore。
FORMULA_KPI_RE = {
    "moat": re.compile(r"moat\D{0,30}?(\d+(?:\.\d+)?)\s*/\s*2"),
    "capital": re.compile(r"capital\D{0,30}?(\d+(?:\.\d+)?)\s*/\s*2"),
    "valuation": re.compile(r"valuation\D{0,30}?(\d+(?:\.\d+)?)\s*/\s*2"),
    "growth": re.compile(r"growth\D{0,30}?(\d+(?:\.\d+)?)\s*/\s*2"),
}
RED_TEAM_RE = re.compile(r"red_team|##\s*red.?team", re.I)


def _extract_wiki_subscores(wiki_text):
    """喺 wiki 第一個「## confidence 推導」段機讀抽 4-KPI subscores(moat/capital/
    valuation/growth,格式 `KPI X/2`)。

    回傳 (subscores_dict_or_None, section_found_bool):
      - section 唔存在 -> (None, False)         # 呢個 theme 未寫機讀推導段,靜默 skip
      - section 存在但抽唔齊 4 個 -> (None, True) # caller 要 warn「無機讀 subscores」
      - 抽齊 4 個 -> (dict, True)
    """
    m = FORMULA_SECTION_RE.search(wiki_text)
    if not m:
        return None, False
    section = m.group(0)
    out = {}
    for kpi, rx in FORMULA_KPI_RE.items():
        mm = rx.search(section)
        if mm:
            out[kpi] = float(mm.group(1))
    if len(out) < len(FORMULA_KPI_RE):
        return None, True
    return out, True


def _load_crowding_composite():
    """讀 thesis/.raw/crowding_composite.json(§4a 一致的擁擠複合分位來源)。
    讀唔到就回空 dict + 錯誤字串(caller 對每個 theme 保守假設 40-60 帶並 warn)。"""
    path = os.path.join(ROOT, ".raw", "crowding_composite.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f) or {}
        return (data.get("themes") or {}), None
    except Exception as e:
        return {}, str(e)


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
    formula_errors = {}      # slug -> [errors]    (P2 formula lint, DESIGN §4a)
    formula_warnings = {}    # slug -> [warnings]  (extraction failure / crowding fallback / §4c)
    crowding_data, crowding_read_err = _load_crowding_composite()
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

            # Type-A crisis-sleeve admission warning (WS5 Sec1.5; governance ruling 2026-07-16,
            # backtest/results/2026-07-16_governance_rules_audit.md R12): sizing.py's B-type
            # engine has no A-sleeve logic -- flag here too so it's caught before it's admitted.
            if t.get("type") == "A" and t.get("status", "active") == "active":
                admission_warnings.setdefault(slug, []).append(
                    "type: A (WS5 Sec1.5 crisis sleeve, <=10% satellite budget separate pool) "
                    "but sizing.py has no A-sleeve engine implemented yet -- sizing.py excludes "
                    "this theme from B-type sizing (loud tripwire) instead of silently sizing "
                    "it as Type B"
                )

            # 兩條「校準前 confidence 上限」規則並存,互相冇引用(2026-07-16 治理盤點發現):
            #   ws3_lifecycle.md:137 (07-08) : confidence ∈ (0, 0.6]      <- 一直只有呢條被 encode
            #   STATUS.md:261        (07-06) : 「校準迴路未通之前…confidence 上限 ≤0.40」
            # 後果:lint 一直合法放行 0.47 兩個(zero error),越界活咗 10 日至今日 cleanup 先捉到。
            # 解法 = **兩條並存、取最緊**(同 confidence_formula 兩個 cap 同一 pattern),
            # 唔係「揀邊條 doc 贏」—— 揀 doc 係酌情,取最緊係規則。0.40 < 0.6 故 0.40 governing。
            # 實際 cap 邏輯住喺 confidence_formula.UNCALIBRATED_CAP(單一實作,呢度唔複製常數);
            # 呢個 (0, 0.6] 範圍檢查降級做「結構健全性」檢查(0.6 = WS3 絕對上限,校準後都唔可以過),
            # 真正嘅 ≤0.40 由下面 P2 formula check 逐 theme 對公式輸出強制。
            conf = t.get("confidence")
            if conf is None or not (0 < float(conf) <= 0.6):
                errs.append(f"confidence {conf!r} not in (0, 0.6] (ws3_lifecycle.md:137 absolute "
                            f"bound; note the tighter uncalibrated ceiling "
                            f"{cf.UNCALIBRATED_CAP} from STATUS.md:261 is enforced per-theme by "
                            f"the P2 formula check below)")

            sources = t.get("sources") or []
            if len(sources) < 1:
                errs.append("sources empty (need >= 1)")

            # DESIGN §4a:137 執行檢查(2026-07-16 補實作 —— 之前 DESIGN 點名 lint 做執行者,
            # 但 lint 零實作,即係「加個 newsletter 就解 cap」呢個原文明講要防嘅漏洞一直冇上鎖)。
            #
            # 點解呢個係全系統最高槓桿嘅閘:single-source cap 釘死 13/15 theme 喺 <=0.30,
            # 係實際綁緊嘢嘅主要約束;而脫 cap 係 binary 開關 —— confidence 由 0.30 跳到 raw
            # (實測 0.469 = +56%)。confidence_formula 嘅條件係 n_sources <= 1,即係**加任何
            # 一個 source entry 就即刻脫 cap**,唔理嗰個 source 有冇真係佐證過承重 claim。
            #
            # 呢度只能機械檢查「有冇標 corroborates」,**判唔到佢係咪真係掂承重 claim**
            # (§4a 定義要求 Tier-1 獨立擊中承重,唔係周邊事實)—— 嗰個判斷要 red-team/人判。
            # 即係話:呢個閘擋嘅係「懶惰嘅假獨立」,唔係「有心嘅錯判」。誠實講明呢個界線。
            if len(sources) >= 2 and not any(s.get("corroborates") for s in sources
                                              if isinstance(s, dict)):
                errs.append(
                    f"sources has {len(sources)} entries (escapes the single-source cap 0.30 -> "
                    f"confidence can jump to raw) but NONE carries a `corroborates:` tag. "
                    f"DESIGN §4a requires >=1 source to state which load-bearing claim it "
                    f"independently corroborates -- a second Tier-2 source that merely restates "
                    f"the first does NOT qualify as independent. Add corroborates: <claim> to the "
                    f"qualifying source, or drop it back to single-source."
                )

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

            # --- P2 formula lint (docs/2026-07-15_quantification_review.md 提案2 + DESIGN §4a) ---
            # 只喺 wiki 有機讀「## confidence 推導」段先做;冇段 = 呢個 theme 未遷移,靜默 skip
            # (唔係全部 theme 而家都要有 -- 見 DESIGN §4a 尾段「遷移程序」,逐個覆核後先落 wiki)。
            wiki_slug = _slug(slug)
            wiki_text = pages.get(wiki_slug, {}).get("text", "")
            if wiki_text:
                wiki_subscores, section_found = _extract_wiki_subscores(wiki_text)
                if section_found and wiki_subscores is None:
                    formula_warnings.setdefault(slug, []).append(
                        "wiki 有「## confidence 推導」段但機讀唔到齊 4 個 subscores(要 "
                        "moat/capital/valuation/growth 四個都以 `KPI X/2` 格式出現)-- "
                        "無機讀 subscores,formula lint 略過呢個 theme"
                    )
                elif wiki_subscores is not None:
                    cr = crowding_data.get(slug) or crowding_data.get(wiki_slug) or {}
                    if cr.get("composite_status") == "ok" and cr.get("composite_pctile") is not None:
                        crowding_pctile = float(cr["composite_pctile"])
                    else:
                        crowding_pctile = 50.0  # 讀唔到 -> 保守假設落喺 40-60 帶中點
                        reason = crowding_read_err or cr.get("composite_status") or "missing from json"
                        formula_warnings.setdefault(slug, []).append(
                            f"crowding_composite.json 讀唔到呢個 theme 嘅 composite_pctile "
                            f"({reason}) -- formula lint 保守假設 crowding 落喺 40-60 帶"
                        )
                    try:
                        result = cf.confidence(wiki_subscores, crowding_pctile, cs, len(sources))
                        recorded = float(conf) if conf is not None else None
                        diff = None if recorded is None else abs(result["capped"] - recorded)
                        if recorded is None or diff > 0.01:
                            formula_errors.setdefault(slug, []).append(
                                f"wiki subscores={wiki_subscores}, crowding_pctile={crowding_pctile}, "
                                f"cycle_stage={cs!r}, n_sources={len(sources)} -> formula confidence="
                                f"{result['capped']:.4f} (raw={result['raw']:.4f}, "
                                f"cap_applied={result['cap_applied']}) but themes.yaml confidence="
                                f"{conf!r} (diff={diff if diff is not None else 'n/a'})"
                            )
                    except Exception as e:
                        formula_warnings.setdefault(slug, []).append(
                            f"formula lint could not compute confidence for this theme: {e}"
                        )

            # --- §4c: magnitude_unconfirmed node must have a corresponding red_team section ---
            nodes = t.get("nodes") or []
            if any(isinstance(n, dict) and n.get("magnitude_unconfirmed") for n in nodes) \
                    and not RED_TEAM_RE.search(wiki_text or ""):
                formula_warnings.setdefault(slug, []).append(
                    "theme 有 node 標 magnitude_unconfirmed: true,但 wiki 搵唔到 red_team 段 "
                    "(DESIGN §4c 要求:未證 magnitude 腿要有 red_team 判決記錄邊條腿未證)"
                )

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

    n_formula_errs = sum(len(v) for v in formula_errors.values())
    print(f"\nP2 formula lint ERRORS (DESIGN §4a, wiki subscores vs themes.yaml confidence, "
          f"MUST fix): {n_formula_errs}")
    for slug, errs in formula_errors.items():
        print(f"  {slug}:")
        for e in errs:
            print(f"    - {e}")

    n_formula_warn = sum(len(v) for v in formula_warnings.values())
    print(f"\nP2 formula lint warnings (extraction failure / crowding fallback / §4c "
          f"magnitude_unconfirmed missing red_team, not blocking): {n_formula_warn}")
    for slug, warns in formula_warnings.items():
        for w in warns:
            print(f"  {slug}: {w}")

    print("\n(Unresolved links are OK -- they mark concept pages worth writing next, not errors.)")
    return n_admission_errs + len(fm_errors) + n_formula_errs


if __name__ == "__main__":
    _no_ticker_check = "--no-ticker-check" in sys.argv
    _n_errors = run(no_ticker_check=_no_ticker_check)
    sys.exit(1 if _n_errors else 0)
