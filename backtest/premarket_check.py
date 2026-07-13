"""Premarket overlay for core-v2 + satellite watchlist (docs/2026-07-07_core_playbook.md).

Two daily runs (user design, 2026-07-09):
  POST-CLOSE (~5am HKT, after US close): playbook_readout.py -- closed-form next-close TRIGGER
    prices from the last close (dip/accumulate, sell-covered-call, 200SMA gate). Uses CLOSE.
  PREMARKET  (~1h before US open, ~20:30 HKT): THIS script -- fetches LIVE premarket prices and
    overlays them on those trigger levels: distance to each line + a chase-warning when an
    accumulate name gaps up. Uses PREMARKET price IN ADDITION to the close-based triggers.

Read-only, no orders. Premarket price = yfinance prepost 1m last bar (fallback fast_info).

AUTO WATCHLIST (2026-07-13 expansion -- SK Hynix -15.4% memory panic prompted this; the old
static 8-name DEFAULT missed SNDK/WDC and had no peer/basket coverage at all):
  always: SPY, QQQ
  auto  : every ACTIVE theme (thesis/themes.yaml) that is EITHER (a) currently held in
          thesis/paper_ledger.json's satellite sleeve, OR (b) flagged ACCUMULATE/BUY-ZONE/
          KILL-WATCH in the LATEST theme_signal run parsed out of playbook_log.txt -- union,
          theme-level `tickers:` field (theme_signal.py's own ROLLUP), capped per-theme via
          --topn=N if runtime needs trimming. As of 2026-07-13 the ledger already holds all 15
          active themes, so in practice this == "every active theme's tickers" (~68 names).
  CLI args (plain tickers), same as before, override the auto list entirely.

GOLDEN-DIP CHECK -- four sensors, params are EMPIRICALLY-FIXED CONSTANTS (do not retune ad hoc):
  1. single-name anomaly : premarket gap <= -max(FULL_SIGMA_MULT * sigma20, FLOOR_PCT)
  2. theme basket         : equal-weight basket premarket gap <= -BASKET_SIGMA_MULT * basket_sigma20
  3. entry bell           : premarket price <= the RSI-2 dip/accumulate trigger price (trigger_nums)
  4. peer tape            : a configured foreign/untradeable sentinel's latest COMPLETE session
                            return <= -PEER_SIGMA_MULT * its own sigma20 (Korea/Europe close
                            before the US premarket session -- an early read)
  sigma20 = rolling 20-trading-day std of daily close-to-close returns, using data up to and
  including the LAST CLOSE only (no lookahead -- premarket price is never in the sigma window).

TWO-TIER ALERT (2026-07-13 correction -- the original single 1.5sigma union threshold fired on
~12 buyer-gate names every ~4 trading days, too noisy to be a card trigger; raised to 2.0sigma
for the full card, kept 1.5sigma as a quieter one-line-only tier):
  FULL CARD  ("==== GOLDEN-DIP CHECK ====" checklist, all 5 fields) opens when:
    - theme verdict in {ACCUMULATE, BUY-ZONE} (buyer gate) AND ANY of: basket 1.25sigma hit,
      single-name >= FULL_SIGMA_MULT(2.0)sigma hit, entry bell hit, peer tape hit; OR
    - theme is held in paper_ledger AND its basket hits 1.25sigma (kill-watch/trim review --
      "is the kill condition starting to be confirmed", independent of buyer-gate status).
  ONE LINE (fact only, no checklist) opens when:
    - theme verdict in {ACCUMULATE, BUY-ZONE} AND a single name hits the SOFT_SIGMA_MULT(1.5)
      threshold but the theme did not otherwise qualify for a full card.
  Anything else (WAIT-verdict, not held, or held-but-basket-didn't-fire) that still tripped a
  sensor is NOT printed per-theme -- rolled into one summary sentence, no card, no line, so the
  alert budget stays on buyer-gate/kill-review themes only (empirical target ~4-5 full cards/month
  board-wide).

    python backtest/premarket_check.py                          # auto watchlist (default)
    python backtest/premarket_check.py MU LITE GEV               # custom tickers (overrides auto)
    python backtest/premarket_check.py --topn=3                  # cap auto watchlist to first
                                                                  #   3 tickers/theme (speed)
    python backtest/premarket_check.py --test-gap=MU:-8.0         # force MU's premarket gap to
                                                                  #   -8% (sensor 1/3 test hook)
    python backtest/premarket_check.py --test-basket=memory-supercycle:-6.0   # force a basket hit
    python backtest/premarket_check.py --test-peer=memory-supercycle:-16.0    # force a peer hit
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import yaml

from backtest.data import load as _data_load

# ---------------------------------------------------------------------------
# paths
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THESIS_DIR = os.path.join(ROOT, "thesis")
THEMES_PATH = os.path.join(THESIS_DIR, "themes.yaml")
LEDGER_PATH = os.path.join(THESIS_DIR, "paper_ledger.json")
PLAYBOOK_LOG = os.path.join(ROOT, "playbook_log.txt")
VALUATION_PATH = os.path.join(THESIS_DIR, ".raw", "valuation_report.json")
CROWDING_PATH = os.path.join(THESIS_DIR, ".raw", "crowding_composite.json")
# Static reference (2026-07-13 demand-side buyer-confirmation scan) -- per user design this is
# a STATIC citation, not a live re-scan, so the path is a fixed constant, not a glob-latest.
DEMAND_SCAN_PATH = os.path.join(ROOT, "backtest", "results", "2026-07-13_demand_side_scan.md")

# legacy static 8-name list, kept only as an emergency fallback if themes.yaml/paper_ledger
# can't be loaded at all (so the script degrades instead of losing SPY/QQQ coverage).
DEFAULT = ["SPY", "QQQ", "MU", "LITE", "GEV", "COHR", "ON", "AVGO"]

# ---------------------------------------------------------------------------
# 黃金坑四感應器參數(實證頻率定死;2026-07-13 兩級修正 -- 唔准自行再調)
# ---------------------------------------------------------------------------
SIGMA_WINDOW = 20                     # rolling trading days for sigma20
SINGLE_NAME_FLOOR_PCT = 0.025         # 2.5% floor, applies to both single-name tiers
SINGLE_NAME_FULL_SIGMA_MULT = 2.0     # 開卡級單名門檻(2026-07-13 由 1.5 上調 -- union 1.5σ 全板
                                       # 每 ~4 個交易日響一次,太嘈用唔到做卡)
SINGLE_NAME_SOFT_SIGMA_MULT = 1.5     # 一行級(唔開卡)單名門檻,只適用買方閘主題
BASKET_SIGMA_MULT = 1.25              # 主題籃子(開卡;買方閘 或 持倉KILL-WATCH減持檢視 兩用)
PEER_SIGMA_MULT = 2.0                 # 同業盤(開卡,買方閘專用)

# 同業/海外 sentinel(唔可交易或刻意用海外掛牌做早訊號):首批只加有合理理據嘅兩個主題,
# 其餘主題留空(冇合理 peer 就唔加,唔強行砌).
THEME_PEERS = {
    # SK Hynix + Samsung -- 兩者都係 HBM/DRAM 供給鏈嘅直接同業,KRX 喺美股盤前已收市,係真.
    # 領先訊號(2026-07-13 驗證:SK 海力士 -15.4% 早過美股盤前齊跌 4.5-5%)。
    "memory-supercycle": ["000660.KS", "005930.KS"],
    # ASML 嘅 Euronext Amsterdam 主要掛牌,美股 ASML 淨係 ADR。歐洲收市早過美股盤前,一樣公司
    # 兩個掛牌 = 最乾淨嘅領先讀數(唔係嚴格意義嘅「同業」,但滿足「更早收市的價格訊號」呢個
    # 設計目的;2026-07-13 驗證:AS 掛牌已有週一讀數嗰陣、美股 ADR 仲停留喺上週五收市)。
    "euv-lithography-monopoly": ["ASML.AS"],
    # 其他主題:未有合理同業/海外 sentinel,刻意留空(唔肯定就唔加)。
}


# ---------------------------------------------------------------------------
# cached data loader (in-process only) -- shared by trigger_nums (via monkeypatch below),
# sigma20, basket sigma, and peer sigma so a symbol's history is fetched from source ONCE per
# run instead of 2-3x. Does not touch backtest/data.py or backtest/playbook_readout.py on disk.
# ---------------------------------------------------------------------------
_load_cache: dict[str, object] = {}


def cached_load(symbol):
    if symbol in _load_cache:
        val = _load_cache[symbol]
        if isinstance(val, BaseException):
            raise val
        return val
    try:
        df = _data_load(symbol)
    except Exception as e:  # noqa: BLE001 -- cache the failure too, don't retry a dead symbol
        _load_cache[symbol] = e
        raise
    _load_cache[symbol] = df
    return df


import backtest.playbook_readout as _pbr  # noqa: E402 -- after cached_load is defined

_pbr.load = cached_load  # runtime monkeypatch of the module-level name playbook_readout.py
# resolves at call time -- NOT an on-disk edit to playbook_readout.py. trigger_nums()/
# trigger_levels() now share the same in-process cache as everything else in this script.
from backtest.playbook_readout import trigger_nums  # noqa: E402


def fetch_premarket(sym):
    """Live premarket (or latest) price: yfinance prepost 1m last bar, fallback fast_info."""
    import yfinance as yf
    tk = yf.Ticker(sym)
    try:
        h = tk.history(period="1d", interval="1m", prepost=True)
        if len(h):
            return float(h["Close"].iloc[-1])
    except Exception:
        pass
    try:
        return float(tk.fast_info["lastPrice"])
    except Exception:
        return None


def sigma20(symbol):
    """Rolling 20d close-to-close std, using data through the last close only (no lookahead)."""
    try:
        c = cached_load(symbol)["close"]
        r = c.pct_change().dropna()
        if len(r) < SIGMA_WINDOW:
            return None
        return float(r.tail(SIGMA_WINDOW).std())
    except Exception:
        return None


def verdict(pre, n):
    """One-line actionable read of premarket vs the post-close trigger levels. UNCHANGED from
    the pre-2026-07-13 version -- format/behavior must stay byte-identical for backward compat."""
    gap = pre / n["last"] - 1
    if n["dip"] and pre <= n["dip"]:
        return "DIP TRIGGER HIT -> accumulate zone (RSI-2<10 level)"
    if n["sell"] and pre >= n["sell"]:
        return "SELL-CALL TRIGGER HIT -> RSI-2>90 (sell covered call)"
    if n["gate"] == "ON" and pre < n["cross"]:
        return "premarket below 200SMA -> LEAP-gate-flip WATCH"
    if gap >= 0.03:
        return f"gap +{gap*100:.1f}% -> CHASING; don't market-buy, wait / limit lower"
    if gap <= -0.03:
        return f"gap {gap*100:.1f}% -> weakness, moving toward accumulate"
    return "in range -- no trigger (hold / scale on weakness)"


# ---------------------------------------------------------------------------
# auto watchlist: themes.yaml (active) x paper_ledger.json (held) x latest theme_signal verdicts
# ---------------------------------------------------------------------------
def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def load_themes_yaml():
    with open(THEMES_PATH, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data.get("themes", {}) or {}


def load_paper_ledger():
    with open(LEDGER_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def theme_ticker_index(themes):
    """slug -> theme-level `tickers:` list (theme_signal.py's own ROLLUP field, NOT node-level);
    ticker -> [slugs] reverse index for grouping any given ticker back to its theme(s)."""
    slug_tickers, ticker_slugs = {}, {}
    for slug, t in themes.items():
        tickers = list(t.get("tickers") or [])
        slug_tickers[slug] = tickers
        for tk in tickers:
            ticker_slugs.setdefault(tk, []).append(slug)
    return slug_tickers, ticker_slugs


# Mirrors thesis/dashboard_render.py's ACCUM_RE/BUYZONE_RE/KILLWATCH_RE (duplicated here rather
# than imported, so this script has no import-time dependency on dashboard_render.py, which is
# off-limits to edit and not meant to be a library). Keep in sync if that file's line format
# changes -- both read the exact same "ACCUMULATE: a, b, c" / "(none)" lines theme_signal.py
# prints into playbook_log.txt.
ACCUM_RE = re.compile(r"^ACCUMULATE: (?P<v>.+?)\s*$", re.MULTILINE)
BUYZONE_RE = re.compile(r"^BUY-ZONE: (?P<v>.+?)\s*$", re.MULTILINE)
KILLWATCH_RE = re.compile(r"^KILL-WATCH: (?P<v>.+?)\s*$", re.MULTILINE)
RUN_HEADER_RE = re.compile(r"^==== (?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}) ====\s*$", re.MULTILINE)


def _slug_list(s):
    s = s.strip()
    if not s or s == "(none)":
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def parse_latest_theme_verdicts():
    """Latest theme-level verdict lists, parsed straight out of playbook_log.txt's most recent
    '=== thesis theme_signal ...' run (rfind -> everything after it belongs to that one run,
    since theme_signal.py always writes those 3 summary lines exactly once per run)."""
    out = {"buy_zone": [], "accumulate": [], "kill_watch": [], "asof": None, "found": False}
    text = read_text(PLAYBOOK_LOG)
    if not text:
        return out
    idx = text.rfind("=== thesis theme_signal")
    if idx == -1:
        return out
    block = text[idx:]
    out["found"] = True
    m = BUYZONE_RE.search(block)
    if m:
        out["buy_zone"] = _slug_list(m.group("v"))
    m = ACCUM_RE.search(block)
    if m:
        out["accumulate"] = _slug_list(m.group("v"))
    m = KILLWATCH_RE.search(block)
    if m:
        out["kill_watch"] = _slug_list(m.group("v"))
    headers = RUN_HEADER_RE.findall(text[:idx])
    if headers:
        out["asof"] = headers[-1]
    return out


def build_watchlist(cli_tickers, topn_per_theme=None):
    """Returns a dict with the resolved watchlist + all the bookkeeping the golden-dip check
    needs (theme membership, ledger holdings, latest verdicts). Falls back to DEFAULT (with a
    printed warning) if themes.yaml/paper_ledger.json can't be loaded at all."""
    warnings = []
    try:
        themes = load_themes_yaml()
    except Exception as e:
        warnings.append(f"themes.yaml load failed ({type(e).__name__}: {e}) -- using legacy DEFAULT watchlist")
        return dict(watchlist=list(DEFAULT), active={}, slug_tickers={}, ticker_slugs={},
                    verdicts=parse_latest_theme_verdicts(), ledger_slugs=set(), target_slugs=[],
                    capped_note=None, warnings=warnings, cli_mode=bool(cli_tickers))
    active = {slug: t for slug, t in themes.items() if t.get("status", "active") == "active"}
    slug_tickers, ticker_slugs = theme_ticker_index(active)
    verdicts = parse_latest_theme_verdicts()
    try:
        ledger = load_paper_ledger()
        ledger_slugs = set((ledger.get("satellite") or {}).keys())
    except Exception as e:
        warnings.append(f"paper_ledger.json load failed ({type(e).__name__}: {e}) -- ledger-held set empty")
        ledger_slugs = set()
    verdict_slugs = set(verdicts["buy_zone"]) | set(verdicts["accumulate"]) | set(verdicts["kill_watch"])
    target_slugs = sorted((ledger_slugs | verdict_slugs) & set(active.keys()))

    if cli_tickers:
        watchlist = list(dict.fromkeys(cli_tickers))
        return dict(watchlist=watchlist, active=active, slug_tickers=slug_tickers,
                    ticker_slugs=ticker_slugs, verdicts=verdicts, ledger_slugs=ledger_slugs,
                    target_slugs=target_slugs, capped_note=None, warnings=warnings, cli_mode=True)

    watchlist = ["SPY", "QQQ"]
    capped = False
    for slug in target_slugs:
        tks = slug_tickers.get(slug, [])
        if topn_per_theme and len(tks) > topn_per_theme:
            capped = True
            tks = tks[:topn_per_theme]
        for tk in tks:
            if tk not in watchlist:
                watchlist.append(tk)
    capped_note = f"每主題頭 {topn_per_theme} 隻(--topn,跑時控制)" if capped else None
    return dict(watchlist=watchlist, active=active, slug_tickers=slug_tickers,
                ticker_slugs=ticker_slugs, verdicts=verdicts, ledger_slugs=ledger_slugs,
                target_slugs=target_slugs, capped_note=capped_note, warnings=warnings, cli_mode=False)


# ---------------------------------------------------------------------------
# reference data for the golden-dip checklist (約束/估值/擁擠) -- static/cheap reads
# ---------------------------------------------------------------------------
BUYER_VERDICT_RE = re.compile(
    r"^\| (?P<slug>[a-z][a-z0-9-]+) \| (?P<seller>[^|]+) \| (?P<confirm>\d+) \| "
    r"(?P<reverse>\d+) \| (?P<neg>\d+) \| (?P<concl>[^|]+) \|\s*$", re.MULTILINE)


def load_demand_side_map():
    """Static reference to the 2026-07-13 buyer-side confirmation scan -- NOT re-scanned here."""
    text = read_text(DEMAND_SCAN_PATH)
    out = {}
    if not text:
        return out
    for m in BUYER_VERDICT_RE.finditer(text):
        out[m.group("slug")] = dict(
            seller=m.group("seller").strip(), confirm=int(m.group("confirm")),
            reverse=int(m.group("reverse")), neg=int(m.group("neg")), concl=m.group("concl").strip())
    return out


def load_valuation_map():
    """ticker -> classification (thesis/.raw/valuation_report.json)."""
    out = {}
    try:
        with open(VALUATION_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        for tk, row in (data.get("tickers") or {}).items():
            out[tk] = row.get("classification")
    except Exception:
        pass
    return out


def load_crowding_map():
    """slug -> {pctile, status} (thesis/.raw/crowding_composite.json)."""
    out = {}
    try:
        with open(CROWDING_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        for slug, row in (data.get("themes") or {}).items():
            out[slug] = dict(pctile=row.get("composite_pctile"), status=row.get("composite_status"))
    except Exception:
        pass
    return out


# ---------------------------------------------------------------------------
# sensors
# ---------------------------------------------------------------------------
def classify_single_name(gap, sigma):
    """Two-tier single-name classification. Returns (tier, threshold) where tier is
    'full' | 'soft' | None. 'full' implies it would also have crossed 'soft' (2.0sigma > 1.5sigma
    -> the full threshold is the more negative one), so tiers are mutually exclusive here."""
    if sigma is None:
        return None, None
    full_t = -max(SINGLE_NAME_FULL_SIGMA_MULT * sigma, SINGLE_NAME_FLOOR_PCT)
    soft_t = -max(SINGLE_NAME_SOFT_SIGMA_MULT * sigma, SINGLE_NAME_FLOOR_PCT)
    if gap <= full_t:
        return "full", full_t
    if gap <= soft_t:
        return "soft", soft_t
    return None, None


def basket_trigger(tickers, per_ticker, override_pct=None):
    """Equal-weight theme basket: premarket gap vs BASKET_SIGMA_MULT x basket sigma20."""
    if override_pct is not None:
        return dict(gap=override_pct / 100.0, threshold=None, sigma=None, triggered=True,
                    note="TEST OVERRIDE --test-basket")
    gaps = []
    for tk in tickers:
        cached = per_ticker.get(tk)
        if not cached:
            continue
        n, pre = cached
        if n and pre:
            gaps.append(pre / n["last"] - 1.0)
    if not gaps:
        return dict(gap=None, threshold=None, sigma=None, triggered=False, note="no premarket data")
    basket_gap = sum(gaps) / len(gaps)
    series = []
    for tk in tickers:
        try:
            c = cached_load(tk)["close"]
            r = c.pct_change().dropna()
            if len(r):
                series.append(r)
        except Exception:
            continue
    if not series:
        return dict(gap=basket_gap, threshold=None, sigma=None, triggered=False, note="no sigma history")
    # sort=True: explicit chronological ordering of the unioned DatetimeIndex (pandas4 warns and
    # will require this argument -- fixed here rather than silenced, since a real "Pandas4Warning"
    # on stderr can otherwise interleave mid-line with stdout in the log file when a wrapper .cmd
    # merges 2>&1, e.g. daily_premarket.cmd -- corrupting that ticker's printed verdict text).
    aligned = pd.concat(series, axis=1, sort=True)
    basket_ret = aligned.mean(axis=1, skipna=True).dropna()
    if len(basket_ret) < SIGMA_WINDOW:
        return dict(gap=basket_gap, threshold=None, sigma=None, triggered=False, note="insufficient sigma window")
    sigma = float(basket_ret.tail(SIGMA_WINDOW).std())
    threshold = -BASKET_SIGMA_MULT * sigma
    return dict(gap=basket_gap, threshold=threshold, sigma=sigma, triggered=basket_gap <= threshold, note="")


def peer_trigger(slug, override_pct=None):
    """Foreign/untradeable sentinel(s): latest COMPLETE session return vs PEER_SIGMA_MULT x its
    own sigma20. These markets close before the US premarket window -- an early read."""
    peers = THEME_PEERS.get(slug) or []
    if override_pct is not None:
        return [dict(peer=(peers[0] if peers else "(test)"), ret=override_pct / 100.0, sigma=None,
                     triggered=True, note="TEST OVERRIDE --test-peer")]
    results = []
    for peer in peers:
        try:
            c = cached_load(peer)["close"]
            if len(c) < 2:
                results.append(dict(peer=peer, ret=None, sigma=None, triggered=False, note="insufficient history"))
                continue
            ret = float(c.iloc[-1] / c.iloc[-2] - 1.0)
            # Peer's "latest complete session" IS the tested day (its market already closed) --
            # unlike single-name/basket sigma (which only ever sees data through YESTERDAY's
            # close, since today's US session hasn't closed yet), a naive tail(20) here would
            # bake the very move being tested into its own volatility baseline, inflating sigma
            # and making a big move self-defeating (verified 2026-07-13: 000660.KS -15.4% vs a
            # sigma that already includes that -15.4% day = 7.85% > 2x threshold NOT tripped;
            # excluding it -> prior-20d sigma 7.21%, threshold -14.4% -> DOES trip, matching the
            # obvious real-world read of a peer-market panic). So sigma uses the PRIOR window,
            # excluding the last (tested) return -- no lookahead, no self-contamination.
            r_hist = c.pct_change().dropna().iloc[:-1]
            sig = float(r_hist.tail(SIGMA_WINDOW).std()) if len(r_hist) >= SIGMA_WINDOW else None
            triggered = sig is not None and ret <= -PEER_SIGMA_MULT * sig
            note = f"asof {c.index[-1].date()}" + ("" if sig is not None else " (sigma n/a)")
            results.append(dict(peer=peer, ret=ret, sigma=sig, triggered=triggered, note=note))
        except Exception as e:
            results.append(dict(peer=peer, ret=None, sigma=None, triggered=False,
                                note=f"fetch fail: {type(e).__name__}"))
    return results


# ---------------------------------------------------------------------------
# golden-dip checklist formatting
# ---------------------------------------------------------------------------
def format_full_card(slug, theme, open_reasons, tickers, per_ticker, verdict_tag, held,
                     demand_map, valuation_map, crowding_map):
    lines = [f"-- {slug} -- verdict={verdict_tag or 'n/a'}{'  [台帳持倉]' if held else ''}",
             f"   開卡條件: {'; '.join(open_reasons)}"]
    d = demand_map.get(slug)
    if d is None:
        lines.append("   約束仲绑住(買家反向驗證): 未評估(demand_side_scan.md 未覆蓋或缺席此主題)")
    else:
        lines.append(f"   約束仲绑住(買家反向驗證): 賣家密度{d['seller']} | 買家確認{d['confirm']}條 / "
                    f"反向{d['reverse']}條 / 被否定{d['neg']}條 -- {d['concl']}")
    vparts = []
    for tk in tickers:
        c = valuation_map.get(tk)
        if c:
            vparts.append(f"{tk}={c}")
    lines.append("   估值(valuation_report.json 分類): " + (", ".join(vparts) if vparts else "n/a(無覆蓋)"))
    cr = crowding_map.get(slug)
    if cr and cr.get("pctile") is not None:
        lines.append(f"   擁擠(crowding percentile): {cr['pctile']:.1f}th ({cr.get('status')})")
    elif cr:
        lines.append(f"   擁擠(crowding percentile): n/a ({cr.get('status')})")
    else:
        lines.append("   擁擠(crowding percentile): n/a(無覆蓋)")
    bell_parts = []
    for tk in tickers:
        cached = per_ticker.get(tk)
        if not cached:
            continue
        n, pre = cached
        if n and pre and n.get("dip"):
            dist = (n["dip"] / pre - 1.0) * 100
            bell_parts.append(f"{tk}: premkt {pre:.2f} vs dip {n['dip']:.2f} ({dist:+.1f}%)")
    lines.append("   距入場鐘: " + ("; ".join(bell_parts) if bell_parts else "n/a"))
    kill_txt = (theme.get("kill_condition") or "").strip().replace("\n", " ")
    if len(kill_txt) > 60:
        kill_txt = kill_txt[:57] + "..."
    lines.append(f"   kill_condition(頭60字): {kill_txt}")
    lines.append("   [WARN] 檢查今日新聞有冇打中呢條軸(系統冇實時新聞,人手覆核)")
    return lines


def main(argv):
    tickers_cli, test_gap, test_basket, test_peer, topn = [], {}, {}, {}, None
    for a in argv:
        if a.startswith("--test-gap="):
            for pair in a.split("=", 1)[1].split(","):
                if ":" in pair:
                    sym, pct = pair.split(":", 1)
                    test_gap[sym.strip().upper()] = float(pct)
        elif a.startswith("--test-basket="):
            for pair in a.split("=", 1)[1].split(","):
                if ":" in pair:
                    slug, pct = pair.split(":", 1)
                    test_basket[slug.strip()] = float(pct)
        elif a.startswith("--test-peer="):
            for pair in a.split("=", 1)[1].split(","):
                if ":" in pair:
                    slug, pct = pair.split(":", 1)
                    test_peer[slug.strip()] = float(pct)
        elif a.startswith("--topn="):
            topn = int(a.split("=", 1)[1])
        elif a.startswith("--"):
            continue
        else:
            tickers_cli.append(a)

    wl = build_watchlist(tickers_cli, topn_per_theme=topn)
    watchlist = wl["watchlist"]

    print(f"==== PREMARKET CHECK {datetime.now():%Y-%m-%d %H:%M} "
          f"(live premarket vs post-close closed-form triggers) ====")
    for w in wl["warnings"]:
        print(f"(WARNING: {w})")
    if not wl["cli_mode"]:
        v = wl["verdicts"]
        note = f" | {wl['capped_note']}" if wl["capped_note"] else ""
        stale = ""
        if v["asof"]:
            try:
                asof_date = datetime.strptime(v["asof"][:10], "%Y-%m-%d").date()
                if (datetime.now().date() - asof_date).days >= 2:
                    stale = "  [STALE >=2d, theme_signal hasn't re-run]"
            except Exception:
                pass
        print(f"(auto watchlist: {len(watchlist)} tickers across {len(wl['target_slugs'])} active themes "
              f"[{len(wl['ledger_slugs'])} ledger-held U {len(set(v['buy_zone'])|set(v['accumulate'])|set(v['kill_watch']))} "
              f"verdict-flagged]{note} | theme_signal asof {v['asof'] or 'n/a'}{stale})")

    # --- batch-prefetch (parallel): history for sigma/trigger_nums + live premarket quotes,
    # so the sequential print loop below only reads from warm in-process caches (speed). ---
    peer_syms = sorted({p for peers in THEME_PEERS.values() for p in peers})
    hist_syms = list(dict.fromkeys(list(watchlist) + peer_syms))
    premkt_cache = {}

    def _hist(sym):
        try:
            cached_load(sym)
        except Exception:
            pass

    def _pre(sym):
        if sym in test_gap:
            premkt_cache[sym] = None  # resolved after trigger_nums below (needs n['last'])
            return
        premkt_cache[sym] = fetch_premarket(sym)

    # History prefetch MUST be sequential: backtest/data.py wraps every yfinance/defeatbeta call
    # in contextlib.redirect_stdout(io.StringIO()) to swallow import/download banners, and that
    # context manager mutates the GLOBAL sys.stdout (not thread-local). Running it concurrently
    # across threads races on that global and can permanently leave sys.stdout pointed at an
    # orphaned StringIO for the rest of the process -- every print() after that point silently
    # vanishes even though the script keeps running to completion (found via a real test run:
    # header printed fine, then everything after the prefetch went missing). Cannot edit
    # backtest/data.py, so this stage stays a plain loop; only the live premarket-quote fetch
    # (fetch_premarket, which never touches redirect_stdout) is parallelized.
    for sym in hist_syms:
        _hist(sym)
    sys.stdout = sys.__stdout__  # defensive: restore in case anything upstream still clobbered it
    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        list(ex.map(_pre, watchlist))

    # --- per-ticker print loop (UNCHANGED format for backward compat) + sensor collection ---
    per_ticker = {}       # sym -> (n, pre)
    single_class = {}     # sym -> (tier, threshold, gap, sigma)
    entrybell_hits = set()

    for sym in watchlist:
        n = trigger_nums(sym)
        if n is None:
            print(f"{sym:6} triggers unavailable")
            continue
        pre = premkt_cache.get(sym)
        if sym in test_gap:
            pre = n["last"] * (1 + test_gap[sym] / 100.0)
        if pre is None:
            print(f"{sym:6} premarket unavailable (last close={n['last']:.2f})")
            continue
        gap = (pre / n["last"] - 1) * 100
        dip_s = f"dip {n['dip']:.2f} [{(n['dip']/pre-1)*100:+.1f}%]" if n["dip"] else "dip n/a"
        sell_s = f"sell {n['sell']:.2f} [{(n['sell']/pre-1)*100:+.1f}%]" if n["sell"] else "sell n/a"
        print(f"{sym:6} close {n['last']:.2f} -> PREMKT {pre:.2f} ({gap:+.1f}%) | {dip_s} | {sell_s} "
              f"| 200SMA {n['cross']:.2f} gate {n['gate']}")
        print(f"       -> {verdict(pre, n)}")

        per_ticker[sym] = (n, pre)
        sig = sigma20(sym)
        tier, thresh = classify_single_name(gap / 100.0, sig)
        if tier:
            single_class[sym] = dict(tier=tier, threshold=thresh, gap=gap / 100.0, sigma=sig)
        if n.get("dip") and pre <= n["dip"]:
            entrybell_hits.add(sym)

    print("(dip/sell [%] = move from premarket to hit that trigger; triggers are CLOSE-based, "
          "premarket is an early read -- confirm at the close.)")

    # --- golden-dip check (marker line = its own "==== ... ====" block for last_block()) ---
    print()
    print("==== GOLDEN-DIP CHECK ====")
    print(f"參數(定死,2026-07-13 兩級修正): 開卡級單名 <= -max({SINGLE_NAME_FULL_SIGMA_MULT}x sigma20,"
          f"{SINGLE_NAME_FLOOR_PCT*100:.1f}%) | 一行級單名(買方閘) <= -max({SINGLE_NAME_SOFT_SIGMA_MULT}x sigma20,"
          f"{SINGLE_NAME_FLOOR_PCT*100:.1f}%) | 籃子(開卡) <= -{BASKET_SIGMA_MULT}x 籃子sigma20 | "
          f"入場鐘(開卡,買方閘)= RSI-2 dip 觸發價 | 同業盤(開卡,買方閘) <= -{PEER_SIGMA_MULT}x sigma20")

    active = wl["active"]
    slug_tickers = wl["slug_tickers"]
    ticker_slugs = wl["ticker_slugs"]
    ledger_slugs = wl["ledger_slugs"]
    v = wl["verdicts"]
    accum_bz = set(v["buy_zone"]) | set(v["accumulate"])

    def verdict_tag(slug):
        if slug in v["accumulate"]:
            return "ACCUMULATE"
        if slug in v["buy_zone"]:
            return "BUY-ZONE"
        if slug in v["kill_watch"]:
            return "KILL-WATCH"
        return None

    relevant_slugs = set(wl["target_slugs"]) | set(test_basket.keys()) | set(test_peer.keys())
    if wl["cli_mode"]:
        for tk in watchlist:
            relevant_slugs.update(ticker_slugs.get(tk, []))
    relevant_slugs &= (set(active.keys()) | set(test_basket.keys()) | set(test_peer.keys()))

    demand_map = load_demand_side_map()
    valuation_map = load_valuation_map()
    crowding_map = load_crowding_map()

    full_cards, one_liners, rollup = [], [], []
    themeless_facts = []
    peer_diag = []  # always-printed peer-tape readings (any configured theme), regardless of trigger

    for slug in sorted(relevant_slugs):
        theme = active.get(slug, {})
        tickers = slug_tickers.get(slug, [])
        is_buyer_gate = slug in accum_bz
        is_held = slug in ledger_slugs
        vt = verdict_tag(slug)

        single_full = [tk for tk in tickers if single_class.get(tk, {}).get("tier") == "full"]
        single_soft = [tk for tk in tickers if single_class.get(tk, {}).get("tier") == "soft"]
        bell = [tk for tk in tickers if tk in entrybell_hits]
        bskt = basket_trigger(tickers, per_ticker, override_pct=test_basket.get(slug))
        peers = peer_trigger(slug, override_pct=test_peer.get(slug))
        peer_hit = [p for p in peers if p["triggered"]]
        for p in peers:
            ret_s = f"{p['ret']*100:+.1f}%" if p["ret"] is not None else "n/a"
            sig_s = f"{p['sigma']*100:.1f}%" if p["sigma"] is not None else "n/a"
            peer_diag.append(f"{slug:<28} {p['peer']:<12} ret={ret_s:>8} sigma20={sig_s:>7} "
                             f"triggered={p['triggered']}  ({p['note']})")

        bskt_thresh_s = f"{bskt['threshold']*100:+.1f}%" if bskt["threshold"] is not None else "n/a(test override)"
        open_reasons = []
        if is_buyer_gate:
            if bskt["triggered"]:
                open_reasons.append(f"籃子1.25sigma gap{bskt['gap']*100:+.1f}%<=閾值{bskt_thresh_s}")
            if single_full:
                d = ", ".join(f"{tk}{single_class[tk]['gap']*100:+.1f}%" for tk in single_full)
                open_reasons.append(f"單名2.0sigma[{d}]")
            if bell:
                open_reasons.append(f"入場鐘[{', '.join(bell)}]")
            if peer_hit:
                d = ", ".join(f"{p['peer']}{p['ret']*100:+.1f}%" for p in peer_hit)
                open_reasons.append(f"同業盤2.0sigma[{d}]")
        if not open_reasons and is_held and bskt["triggered"]:
            open_reasons.append(f"持倉減持檢視:籃子1.25sigma gap{bskt['gap']*100:+.1f}%<=閾值{bskt_thresh_s}")

        if open_reasons:
            full_cards.append(format_full_card(slug, theme, open_reasons, tickers, per_ticker,
                                               vt, is_held, demand_map, valuation_map, crowding_map))
            continue

        if is_buyer_gate and single_soft:
            d = ", ".join(f"{tk} {single_class[tk]['gap']*100:+.1f}% (閾值{single_class[tk]['threshold']*100:+.1f}%,"
                          f"sigma20={single_class[tk]['sigma']*100:.1f}%)" for tk in single_soft)
            one_liners.append(f"{slug:<28} [一行,未達開卡] verdict={vt} 單名1.5sigma弱訊號: {d}")
            continue

        if single_full or single_soft or bskt["triggered"] or bell or peer_hit:
            rollup.append(slug)

    covered_tickers = {tk for slug in relevant_slugs for tk in slug_tickers.get(slug, [])}
    for tk, info in single_class.items():
        if tk in covered_tickers:
            continue
        themeless_facts.append(f"[單名異常,無主題歸屬] {tk} {info['gap']*100:+.1f}% "
                               f"(閾值{info['threshold']*100:+.1f}%, tier={info['tier']}, sigma20={info['sigma']*100:.1f}%)")

    n_full = len(full_cards)
    n_one = len(one_liners)
    print(f"覆蓋 {len(watchlist)} 隻 / {len(relevant_slugs)} 主題已評估 | 開卡 {n_full} | 一行級 {n_one} | "
          f"非買方閘/未達開卡但有訊號 {len(rollup)} 個主題(唔開卡)")
    if peer_diag:
        print("同業盤(peer tape)讀數(always-on 透明度,不論是否開卡):")
        for ln in peer_diag:
            print(f"  {ln}")

    if not full_cards and not one_liners and not themeless_facts:
        print("(今日無任何黃金坑感應器觸發)")
    for tf in themeless_facts:
        print(tf)
    for line in one_liners:
        print(line)
    for card in full_cards:
        print()
        for ln in card:
            print(ln)
    if rollup:
        print(f"\n非買方閘/未開卡主題今日有訊號但唔開卡(一句歸總): {', '.join(rollup)}")


if __name__ == "__main__":
    main(sys.argv[1:])
