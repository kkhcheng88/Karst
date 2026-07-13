"""thesis/demand_side_scan.py -- demand-side reverse-validation scan (Fable 交接書 P2-14).

thesis/constraint_scan.py listens to SELLERS (a theme's own tracked suppliers) describing
their OWN supply tightness ("we are supply constrained", "lead times are stretching"). This
script instead searches the FULL corpus (all ~5,370 tickers, not just a theme's tracked
tickers) for DOWNSTREAM BUYERS -- companies NOT in that theme's own themes.yaml ticker list --
complaining about not being able to get enough of the theme's product ("memory prices are
killing our margins", "transformer lead times have blown out"). Buyers have no incentive to
talk up a supplier's tightness, so a buyer-side confirmation is a cleaner, more independent
check than the seller-side scan alone.

Method (v1, documented scope -- same spirit as constraint_scan.py's v1 disclaimer):
  1. THEME_BUYER_PROBES below: for each supply-constrained theme, 3-5 hand-picked
     (product_term, tension_term) word/phrase pairs, phrased the way a DOWNSTREAM CUSTOMER
     talks about a shortage (task's own worked examples: memory -> "DRAM cost" / "memory
     prices" / "HBM allocation"). Two themes are deliberately SKIPPED (SKIP_THEMES below,
     with a documented reason) -- they are not "buyer complains about a physical shortage"
     type theses, so there is no natural buyer-language probe to write.
  2. Matched via FTS5 NEAR(a b, WINDOW) -- proximity, not rigid phrase-adjacency. Verified
     2026-07-13 on this corpus: exact phrase "transformer lead time" = 0 hits; NEAR(transformer
     "lead time", 8) = 64 hits, same window. Real earnings-call speech rarely uses the exact
     3-word phrase ("we procured long lead time components such as turbines and transformers");
     NEAR tolerates the intervening words while still requiring true proximity (not a bag-of-words
     OR, which would be noisy).
  3. Buyer-identity filter: SQL-level `primary_ticker NOT IN (<theme's own tickers>)` -- a hit
     from a theme's OWN supplier talking about itself is exactly what constraint_scan.py
     already covers; counting it here would double-count, not independently confirm.
  4. Direction classification (heuristic, v1 -- flagged as a documented gap, not hidden):
     each hit's snippet is scanned for EASE_MARKERS (eased/improved/normalized/resolved/...) ->
     'reverse' (buyer says it loosened); else the buyer NEGATIONS list (reused from
     constraint_scan.py) is checked in the ~8-token window before each bracketed match -> if
     ALL occurrences in the snippet are negated, 'negated-no-signal'; otherwise 'confirm'.
     This is snippet-level (not full-body), same practical trade-off constraint_scan.py makes.
     A human/LLM re-reading the printed excerpt can always override -- that's why every hit's
     verbatim excerpt is retained in the output, not just the classification label.
  5. Cross-referenced against the seller-side scan's LATEST density reading
     (thesis/.raw/constraint_scan_state.json, written by constraint_scan.py) to flag two cases
     per the task brief: seller says tight + buyer confirms (strongest) vs. seller says tight
     but buyers are silent (caution -- may be one-sided supplier narrative).

NOT built (documented gap, v1 scope): no LLM-based stance classification, no cross-quarter
trend for the buyer side (unlike constraint_scan.py's 6-quarter heatmap) -- this is a single
lookback-window snapshot, rerun with --quarters N any time.

Run: python thesis/demand_side_scan.py --quarters 4
Output: backtest/results/<date>_demand_side_scan.md
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import sqlite3

ROOT = os.path.dirname(os.path.abspath(__file__))
import corpus as _corpus              # noqa: E402  (sibling module; thesis/ is on sys.path)
import constraint_scan as _cscan      # noqa: E402  (reuse _load_themes + NEGATIONS -- not modified)

RESULTS_DIR = os.path.join(ROOT, "..", "backtest", "results")
STATE_PATH = os.path.join(ROOT, ".raw", "constraint_scan_state.json")

NEAR_WINDOW = 8          # tokens -- matches constraint_scan.py's NEG_WINDOW_TOKENS order of magnitude
ROWS_PER_PROBE = 60      # safety cap per (theme, probe) query

# themes.yaml theme -> 3-5 buyer-perspective (product_term, tension_term) probes. Each becomes
# an FTS5 NEAR(a b, NEAR_WINDOW) query. Multi-word terms are auto-quoted as a literal sub-phrase.
THEME_BUYER_PROBES = {
    "memory-supercycle": [
        ("DRAM", "cost"), ("memory", "prices"), ("HBM", "allocation"),
        ("memory", "pricing"), ("NAND", "pricing"),
    ],
    "photonics-optical": [
        ("optics", "lead time"), ("transceiver", "shortage"),
        ("optical component", "shortage"), ("laser", "lead time"), ("transceiver", "lead time"),
    ],
    "advanced-packaging": [
        ("advanced packaging", "capacity"), ("substrate", "shortage"),
        ("advanced packaging", "allocation"), ("chip packaging", "lead time"), ("CoWoS", "capacity"),
    ],
    "ai-power-grid": [
        ("transformer", "lead time"), ("turbine", "backlog"), ("switchgear", "lead time"),
        ("power equipment", "shortage"), ("generator", "lead time"),
    ],
    "rare-earth-materials": [
        ("rare earth", "shortage"), ("magnet", "supply"), ("gallium", "shortage"),
        ("indium", "shortage"), ("rare earth", "allocation"),
    ],
    "gas-compression-equipment": [
        ("compressor", "lead time"), ("compression equipment", "shortage"),
        ("compressor", "backlog"), ("compression equipment", "capacity"),
    ],
    "tpu-custom-silicon": [
        ("ASIC", "capacity"), ("custom silicon", "lead time"), ("TPU", "allocation"),
        ("foundry capacity", "constrained"),
    ],
    "semicap-equipment": [
        ("burn-in", "capacity"), ("test capacity", "constrained"), ("package test", "capacity"),
    ],
    "aerospace-specialty-alloys": [
        ("titanium", "shortage"), ("nickel alloy", "shortage"),
        ("specialty alloy", "lead time"), ("forging", "capacity"), ("alloy", "allocation"),
    ],
    "euv-lithography-monopoly": [
        ("EUV", "lead time"), ("lithography tool", "allocation"),
        ("EUV tool", "backlog"), ("lithography", "capacity constrained"),
    ],
    "us-solar-manufacturing": [
        ("solar module", "shortage"), ("panel", "allocation"),
        ("solar module", "lead time"), ("solar module", "supply"),
    ],
    "specialty-siding-pricing-power": [
        ("siding", "allocation"), ("siding", "lead time"), ("siding", "cost increase"),
    ],
    "glp1-biologics-packaging": [
        ("vial", "shortage"), ("stopper", "shortage"), ("elastomer", "shortage"),
        # NOTE: an earlier ("component","allocation") probe was DROPPED (2026-07-13) -- it
        # matched almost exclusively "capital allocation...is a key COMPONENT of our strategy"
        # boilerplate (dozens of false positives, zero true positives on manual read), not
        # component/parts shortages. "component" alone is too generic a noun to pair with
        # "allocation" (a near-universal capital-allocation-strategy phrase in earnings calls).
    ],
}

SKIP_THEMES = {
    "space-satellite": "早週期需求/執行敘事(發射、頻譜、月球任務),唔係「買家買唔到實物」型供給樽頸——"
                        "冇自然嘅下游買家投訴語言可測,強行造 probe 只會製造假訊號。",
    "oil-gas-energy": "thesis 本身標記 thin-split-watch(油價 macro 腿 + gas-power watch 腿混合,非單一"
                       "商品/零件供給樽頸故事),唔屬於呢個掃描方法適用嘅「單一實物瓶頸」型 thesis。",
}

EASE_MARKERS = re.compile(
    r"\b("
    r"(?:supply|availability|lead times?|capacity|shortage|constraint|bottleneck|pricing|prices?)"
    r"\s+(?:have |has |had )?(?:eased|easing|improved|improving|normalized|normalizing|abated|"
    r"resolved|caught up|stabilized|stabilizing|come down|coming down|cooled|cooling|"
    r"loosened|loosening|relaxed)"
    r"|no longer (?:a |an )?(?:constraint|issue|problem|shortage|bottleneck)"
    r"|plentiful supply|ample supply"
    r")\b",
    re.I,
)
# NOTE (2026-07-13): first cut of EASE_MARKERS used bare adjectives ("improved"/"eased"/...)
# and misfired on unrelated context -- e.g. NVMI "...capacity for advanced packaging...while
# further IMPROVING our manufacturing process..." (about NVMI's own process quality, not supply
# loosening) and ONTO "...visibility has dramatically IMPROVED as customers plan for SUSTAINED
# investment..." (backlog-visibility improving = a TENSION-CONFIRMING statement, the opposite of
# what the marker was meant to catch). Tightened to require the ease/improve word be directly
# attached to a supply-side noun (supply/availability/lead time/capacity/shortage/pricing).

# LITERAL_GUARDS -- porter stemmer collision guard (found empirically 2026-07-13, first full
# run of this script): FTS5's porter stemmer folds several unrelated English words down to the
# SAME stem as a probe's product term, producing high-volume false positives that NEAR alone
# cannot distinguish (NEAR only checks token proximity, not which surface form matched):
#   "generator"    stems to "gener"  -- collides with generally/generation/generate/generating
#                  (e.g. "our lead times are GENERALLY within..." false-matched "generator")
#   "transformer"  stems to "transform" -- collides with transformation/transformed/transforming
#                  (e.g. "AI tools have TRANSFORMED how we build products" false-matched)
#   "siding"       stems to "sid" -- collides with the extremely common "side"/"sides" ("on the
#                  cost SIDE...") -- this alone produced ~55 of ~57 raw hits for the
#                  specialty-siding-pricing-power theme before this guard was added
#   "forging"      stems to "forg" -- collides with "Forge" used as a proper noun/project name
#                  (e.g. data-center project "Polaris Forge One", "Freedom's Forge" WWII ref)
# A hit is DISCARDED (not just reclassified) if neither probe term's literal surface form is
# present in the snippet -- i.e. the NEAR match fired purely off a stemmed collision, not the
# word the probe was actually written for.
LITERAL_GUARDS = {
    "generator": re.compile(r"\bgenerators?\b", re.I),
    "transformer": re.compile(r"\btransformers?\b", re.I),
    "siding": re.compile(r"\bsiding\b", re.I),
    "forging": re.compile(r"\bforging\b", re.I),
}


def _quarter_of(date_str):
    return _cscan._quarter_of(date_str)


def _cutoff_date(n_quarters):
    """Start date of the quarter N-1 quarters before the current calendar quarter (inclusive
    lookback window of exactly n_quarters quarters ending at 'today')."""
    today = datetime.date.today()
    y, q = today.year, (today.month - 1) // 3 + 1
    for _ in range(n_quarters - 1):
        q -= 1
        if q == 0:
            q, y = 4, y - 1
    m = (q - 1) * 3 + 1
    return f"{y:04d}-{m:02d}-01"


def _near_query(a, b, window=NEAR_WINDOW):
    # quote any term containing a space OR a non-alnum char (e.g. "burn-in") -- FTS5 treats
    # bare '-' as a column-filter/NOT token, so an unquoted hyphenated single "word" is a
    # syntax error, not just a tokenization miss.
    qa = f'"{a}"' if not a.replace(" ", "").isalnum() else a
    qb = f'"{b}"' if not b.replace(" ", "").isalnum() else b
    return f"NEAR({qa} {qb}, {window})"


def _classify(snippet_text):
    """Heuristic direction classification off the FTS snippet (not full body -- same
    practical trade-off constraint_scan.py makes). Returns 'confirm' | 'reverse' |
    'negated-no-signal'."""
    if EASE_MARKERS.search(snippet_text):
        return "reverse"
    matches = list(re.finditer(r"\[([^\]]+)\]", snippet_text))
    if not matches:
        return "confirm"
    for m in matches:
        window = snippet_text[max(0, m.start() - 60):m.start()].lower()
        toks = re.findall(r"[a-z']+", window)
        if not any(t in _cscan.NEGATIONS for t in toks[-8:]):
            return "confirm"
    return "negated-no-signal"


def scan(n_quarters=4):
    themes = _cscan._load_themes()  # slug -> [tickers] (uppercased), from themes.yaml
    cutoff = _cutoff_date(n_quarters)
    con = sqlite3.connect(_corpus.DB)

    results = {}  # slug -> {"hits": [...], "probe_counts": {...}}
    for slug, probes in THEME_BUYER_PROBES.items():
        theme_tickers = set(themes.get(slug, []))
        seen_slugs = set()
        hits = []
        for prod, tens in probes:
            q = _near_query(prod, tens)
            placeholders = ",".join("?" * len(theme_tickers)) if theme_tickers else None
            excl = f"AND d.primary_ticker NOT IN ({placeholders})" if theme_tickers else ""
            params = [q, cutoff] + sorted(theme_tickers) + [ROWS_PER_PROBE] if theme_tickers \
                else [q, cutoff, ROWS_PER_PROBE]
            sql = (
                "SELECT d.primary_ticker, d.published, d.slug, d.title, "
                "  snippet(docs_fts_en,4,'[',']','...',30) AS snip "
                "FROM docs_fts_en JOIN docs d ON d.slug=docs_fts_en.slug "
                f"WHERE docs_fts_en MATCH ? AND d.published >= ? AND d.thesistype='transcript' "
                f"AND d.primary_ticker != '' {excl} "
                "ORDER BY bm25(docs_fts_en) LIMIT ?"
            )
            rows = con.execute(sql, params).fetchall()
            for ticker, published, doc_slug, title, snip in rows:
                if doc_slug in seen_slugs:
                    continue  # already captured via an earlier probe this theme
                # LITERAL_GUARDS: discard if the probe fired purely off a porter-stem collision
                # (see LITERAL_GUARDS docstring) -- neither term is guarded, or the guarded
                # term's literal surface form genuinely appears in the snippet.
                guard_prod = LITERAL_GUARDS.get(prod.lower())
                guard_tens = LITERAL_GUARDS.get(tens.lower())
                if guard_prod and not guard_prod.search(snip):
                    continue
                if guard_tens and not guard_tens.search(snip):
                    continue
                seen_slugs.add(doc_slug)
                direction = _classify(snip)
                hits.append({
                    "ticker": ticker, "published": published, "quarter": _quarter_of(published),
                    "slug": doc_slug, "probe": f"{prod} / {tens}", "direction": direction,
                    "excerpt": re.sub(r"\s+", " ", snip).strip(),
                })
        hits, n_dup = _dedup_by_content(hits)
        if n_dup:
            print(f"[demand_side_scan]   {slug}: collapsed {n_dup} duplicate-content hit(s) "
                  f"(same transcript text under multiple tickers -- OTC/ADR dual-listings, "
                  f"preferred-share series, etc.)")
        results[slug] = hits
    con.close()
    return results, cutoff


def _dedup_by_content(hits):
    """The corpus tags some transcripts under multiple primary_ticker values (verified
    2026-07-13: OTC/ADR dual-listings like SONY/SNEJF, NOK/NOKBF; utility preferred-share
    series like AEE's ~15 subsidiary tickers) -- same earnings call, byte-identical text,
    different ticker tag. Collapsing these (same quarter + near-identical excerpt) avoids
    inflating the 'distinct buyer' count with what is really one voice repeated N times."""
    seen, deduped, n_dup = {}, [], 0
    for h in hits:
        key = (h["quarter"], re.sub(r"\s+", "", h["excerpt"].lower())[:150])
        if key in seen:
            n_dup += 1
            continue
        seen[key] = True
        deduped.append(h)
    return deduped, n_dup


def _load_seller_state():
    import json
    if not os.path.exists(STATE_PATH):
        return {}
    with open(STATE_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    out = {}
    for slug, qdict in raw.items():
        if not qdict:
            continue
        latest_q = sorted(qdict, key=lambda q: (int(q.split("Q")[0]), int(q.split("Q")[1])))[-1]
        out[slug] = (latest_q, qdict[latest_q])
    return out


def _verdict(seller_density, n_confirm, n_reverse):
    if seller_density is None:
        return "無賣家側讀數對照"
    if seller_density >= 0.5:
        if n_confirm > 0 and n_confirm >= n_reverse:
            return "雙重確認(最強)"
        if n_confirm == 0 and n_reverse == 0:
            return "賣家話緊,買家靜(要小心)"
        if n_reverse > n_confirm:
            return "賣家話緊,買家反指鬆咗(矛盾,要覆核)"
        return "賣家話緊,買家訊號弱"
    else:
        if n_confirm > 0:
            return "賣家已轉鬆,買家仍確認緊張(落後訊號?)"
        return "雙方皆無/弱訊號"


def write_report(results, cutoff, n_quarters, out_path):
    seller_state = _load_seller_state()
    today_str = datetime.date.today().isoformat()

    lines = []
    lines.append(f"# 需求端反向驗證掃描 -- {today_str}\n")
    lines.append(
        "Fable 交接書 P2-14。thesis/constraint_scan.py 聽**賣家**(themes.yaml 追蹤 tickers 自己)"
        "講自己供給緊;呢個掃描聽**買家**(唔喺該 theme tickers 名單入面嘅下游客戶)講「買唔夠/交期長」"
        "反向驗證。買家冇動機吹噓供應商緊張,理論上係更乾淨嘅確認訊號。\n"
    )
    lines.append(
        f"**方法**:thesis/demand_side_scan.py。每個 theme 3-5 條買家視角 (product, tension) 詞組"
        f"(如 memory→'DRAM cost'/'memory prices'/'HBM allocation'),用 FTS5 `NEAR(a b, {NEAR_WINDOW})` "
        "近接查詢(非硬性連續片語——已驗證 2026-07-13:完全一致片語 'transformer lead time' 喺呢個 corpus "
        "得 0 命中,NEAR 版本(視窗 8 tokens)得 64 命中,因為真實 earnings call 講法通常有插入字"
        "\"we procured long lead time components such as turbines and transformers\")。"
        f"掃描視窗:最近 {n_quarters} 個日曆季(cutoff >= {cutoff})、僅英文 transcript 語料"
        "(docs_fts_en)。\n"
    )
    lines.append(
        "**買家身份檢查**:SQL 層 `primary_ticker NOT IN (<該 theme 自己嘅 themes.yaml tickers>)`——"
        "逐 theme 分開排除,只排除嗰個 theme 自己嘅供應商,唔係全局排除(例如 GLW 同時喺 "
        "photonics-optical/advanced-packaging 兩個 theme,兩邊各自排除自己嗰份)。呢個過濾喺下面每個 "
        "theme 表格前已註明採用嘅排除清單。\n"
    )
    lines.append(
        "**兩個實測發現嘅雜訊來源,已喺 script 修正**(唔係隱藏,寫低俾覆核):"
        "(1) porter stemmer 詞根碰撞——首輪跑出嚟 'generator' 匹配到 'generally/generation'、"
        "'transformer' 匹配到 'transformation'、'siding' 匹配到極常見嘅 'side'(單一呢個碰撞就製造"
        "咗 specialty-siding-pricing-power theme 55/57 條假命中!)、'forging' 匹配到專有名詞 'Forge'"
        "(如數據中心項目名'Polaris Forge One')——已加 LITERAL_GUARDS,要求 snippet 入面literal 字面"
        "字串(唔止靠詞根)先算數,唔係就直接棄用嗰條命中。(2) corpus 有部分 transcript 俾多個 "
        "primary_ticker 標籤(OTC/ADR 雙重上市如 SONY/SNEJF、NOK/NOKBF;公用事業優先股系列如 AEE 底下"
        "~15 個關聯 ticker)——同一份 transcript 逐字重複,已加內容排重(同季度+前150字元完全相同視為"
        "同一個買家聲音,只計一次)。方法仍係 v1 啟發式,唔係 100% 乾淨(例如 'packaging'/'module' 呢類"
        "多義詞喺部分 theme 仍可能有殘餘雜訊——逐條引句已保留俾人手/LLM 覆核)。\n"
    )
    lines.append(
        "**方向判定**(v1 啟發式,非 LLM):snippet 內見 EASE_MARKERS(要求 eased/improved/normalized/"
        "resolved/caught up 呢類字直接掛住 supply/availability/lead time/capacity/shortage/pricing "
        "呢類供給名詞先算,唔係淨係見到隻字就算——首輪跑出嚟兩條假 `reverse`(NVMI「further IMPROVING "
        "our manufacturing PROCESS」、ONTO「backlog VISIBILITY has IMPROVED」,兩條都同「供給鬆咗」"
        "冇關,已用呢個收緊修正)→ 見到就算 `reverse`(買家話鬆咗);否則喺每個命中片語前 ~8 個 token 檢查"
        "否定詞(沿用 constraint_scan.py 嘅 NEGATIONS 清單)——全部命中都被否定先算 `negated-no-signal`,"
        "否則 `confirm`。呢個係 snippet 層面(唔係全文)嘅啟發式,同 constraint_scan.py 一樣嘅務實取捨——"
        "每條命中嘅原句都保留喺表入面,人手/LLM 可以覆核。\n"
    )
    lines.append("**未覆蓋 theme**(有記錄理由,唔係靜靜跳過):\n")
    for slug, reason in SKIP_THEMES.items():
        lines.append(f"- **{slug}**:{reason}\n")
    lines.append("")

    # -- summary table --
    lines.append("## 摘要:每 theme 買家側確認數 vs 反向數 vs 賣家側最新讀數\n")
    lines.append("| theme | 賣家側最新密度(季) | 買家確認 | 買家反向(鬆咗) | 買家無訊號(被否定) | 對照結論 |")
    lines.append("|---|---|---|---|---|---|")
    summary_rows = []
    for slug in THEME_BUYER_PROBES:
        hits = results.get(slug, [])
        n_confirm = sum(1 for h in hits if h["direction"] == "confirm")
        n_reverse = sum(1 for h in hits if h["direction"] == "reverse")
        n_neg = sum(1 for h in hits if h["direction"] == "negated-no-signal")
        seller_q, seller_val = seller_state.get(slug, (None, None))
        seller_disp = f"{seller_val:.2f} ({seller_q})" if seller_val is not None else "--"
        verdict = _verdict(seller_val, n_confirm, n_reverse)
        summary_rows.append((slug, seller_val, n_confirm, n_reverse, n_neg, verdict))
        lines.append(f"| {slug} | {seller_disp} | {n_confirm} | {n_reverse} | {n_neg} | {verdict} |")
    lines.append("")

    strongest = sorted(
        [r for r in summary_rows if r[5] == "雙重確認(最強)"],
        key=lambda r: (-(r[1] or 0), -r[2]),
    )
    caution = [r for r in summary_rows if r[5] == "賣家話緊,買家靜(要小心)"]
    lines.append("### 賣家話緊、買家又話緊(最強confirmation)\n")
    if strongest:
        for slug, sv, nc, nr, nn, _ in strongest:
            lines.append(f"- **{slug}**:賣家密度 {sv:.2f}、買家確認 {nc} 條、反向 {nr} 條")
    else:
        lines.append("- (無 theme 同時滿足賣家密度>=0.5 且買家確認>反向)")
    lines.append("")
    lines.append("### 賣家話緊、但買家靜晒(要小心——可能係單方面供應商敘事)\n")
    if caution:
        for slug, sv, nc, nr, nn, _ in caution:
            lines.append(f"- **{slug}**:賣家密度 {sv:.2f}、買家確認 0 條、反向 0 條")
    else:
        lines.append("- (無)")
    lines.append("")
    thin_seller_strong_buyer = [
        r for r in summary_rows
        if r[5] == "賣家已轉鬆,買家仍確認緊張(落後訊號?)" and r[2] >= 3
    ]
    lines.append(
        "### 賣家籃子太薄、讀數唔穩,但買家側(全市場)反而強確認(額外發現,唔係任務原定兩類)\n"
    )
    lines.append(
        "呢類 theme 嘅賣家側 constraint_scan.py 追蹤 tickers 得 1-2 隻(rare-earth-materials 得 "
        "MP/USAR 兩隻;semicap-equipment 得 AEHR 一隻),單一 ticker 轉態就令密度喺 0/0.5/1.0 之間跳"
        "(睇 backtest/results/2026-07-12_constraint_scan_production.md 嘅歷史列:rare-earth-materials "
        "6 季讀數 1.00→0.00→1.00→0.50→1.00→0.00,noise 主導,唔可靠)。但買家側掃描係跨全市場"
        "(~5,370 tickers)搵,唔受單一供應商籃子太細影響——呢個先真係「反向驗證」原本要做嘅嘢:賣家讀數"
        "唔穩定嗰陣,買家側可以充當更穩健嘅獨立確認。\n"
    )
    if thin_seller_strong_buyer:
        for slug, sv, nc, nr, nn, _ in thin_seller_strong_buyer:
            lines.append(f"- **{slug}**:賣家最新密度 {sv:.2f}(籃子太細唔可靠)、買家確認 **{nc} 條**"
                          f"(跨多間唔同公司,見下逐 theme 明細)")
    else:
        lines.append("- (無)")
    lines.append("")

    # -- per-theme detail --
    lines.append("## 逐 theme 命中明細\n")
    for slug, probes in THEME_BUYER_PROBES.items():
        theme_tickers = sorted(_cscan._load_themes().get(slug, []))
        hits = results.get(slug, [])
        probe_str = "; ".join(f"{p}/{t}" for p, t in probes)
        lines.append(f"### {slug}\n")
        lines.append(f"probe 組:{probe_str}")
        lines.append(f"排除嘅該 theme 自己 tickers(唔當買家):{', '.join(theme_tickers)}\n")
        if not hits:
            lines.append("_無命中(全部 probe 喺呢個視窗 0 hits,或全部命中都嚟自被排除嘅自己 tickers)。_\n")
            continue
        hits_sorted = sorted(hits, key=lambda h: (h["direction"] != "confirm", h["published"]), reverse=False)
        lines.append("| 買家 ticker | 季度 | 方向 | probe | 引句(≤2句,已截) |")
        lines.append("|---|---|---|---|---|")
        for h in hits_sorted:
            excerpt = h["excerpt"][:280]
            lines.append(f"| {h['ticker']} | {h['quarter']} | {h['direction']} | {h['probe']} | {excerpt} |")
        lines.append("")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return summary_rows


def run(n_quarters=4):
    print(f"[demand_side_scan] scanning last {n_quarters} quarters across full corpus "
          f"({len(THEME_BUYER_PROBES)} themes, {sum(len(v) for v in THEME_BUYER_PROBES.values())} probes)...")
    results, cutoff = scan(n_quarters)
    today_str = datetime.date.today().isoformat()
    out_path = os.path.join(RESULTS_DIR, f"{today_str}_demand_side_scan.md")
    summary_rows = write_report(results, cutoff, n_quarters, out_path)
    total_hits = sum(len(v) for v in results.values())
    print(f"[demand_side_scan] {total_hits} distinct buyer-side transcript hits across "
          f"{len(THEME_BUYER_PROBES)} themes -> {out_path}")
    for slug, sv, nc, nr, nn, verdict in summary_rows:
        print(f"  {slug:32s} seller={sv if sv is not None else '--':<6} confirm={nc:<3} reverse={nr:<3} "
              f"neg={nn:<3} {verdict}")
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quarters", type=int, default=4)
    args = ap.parse_args()
    run(n_quarters=args.quarters)
