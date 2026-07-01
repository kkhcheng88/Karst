"""Insider signal v2 -- SEC EDGAR Form 4 (research-grade), upgrading thesis/insider.py (yfinance v1).

Why EDGAR: Form 4 carries the TRUE transaction CODE, which yfinance hides. The edge is only in genuine
DISCRETIONARY open-market trades (Cohen-Malloy-Pomorski; Lakonishok-Lee):
  P = open-market PURCHASE (the buy signal)   S = open-market SALE (discretionary)
  A = grant/award · M = option exercise · F = tax-withholding on vesting · G = gift  -> MECHANICAL, NOT signal.
yfinance's free-text lumps F/M/G into "Sale"/other, inflating the picture. EDGAR lets us keep only P/S,
read the 10b5-1 flag (pre-scheduled = less informative), and read the exact relationship (dir/officer/10%).

Still MISSING vs the full research method (a future v3): routine-vs-opportunistic classification needs
each insider's multi-year trade history (Cohen et al) -> heavier crawl + cache.

Politeness: SEC requires a User-Agent + <=10 req/s. This crawls per-ticker (slow) -> meant to build a
CACHE offline, not to run inside the live scan. Run:
    python thesis/insider_edgar.py AEHR USAR MU
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
import time
import urllib.request
from functools import lru_cache

# reuse the v1 dataclass shape so this is a drop-in
from insider import InsiderSignal, _CSUITE, _SCALE, _clip

_UA = {"User-Agent": "Karst-research/1.0 (contact research@karst.local)"}
_PAUSE = 0.2
_WINDOW = 180


def _get(url):
    for i in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=_UA), timeout=30).read().decode("utf-8", "replace")
        except Exception:
            time.sleep(0.6 * (i + 1))
    raise RuntimeError(f"fetch failed: {url}")


@lru_cache(maxsize=1)
def _ticker_map():
    return {r["ticker"].upper(): str(r["cik_str"]).zfill(10)
            for r in json.loads(_get("https://www.sec.gov/files/company_tickers.json")).values()}


def _find(tag, s, sub="value"):
    m = re.search(rf"<{tag}>\s*<{sub}>(.*?)</{sub}>", s, re.S) or re.search(rf"<{tag}>(.*?)</{tag}>", s, re.S)
    return m.group(1).strip() if m else None


def _parse_form4(cik, accession):
    acc = accession.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}"
    fi = json.loads(_get(base + "/index.json")); time.sleep(_PAUSE)
    names = [it["name"] for it in fi["directory"]["item"]]
    raw = [n for n in names if n.endswith(".xml") and "xsl" not in n.lower()]
    if not raw:
        return []
    x = _get(base + "/" + raw[0]); time.sleep(_PAUSE)
    who = _find("rptOwnerName", x) or "?"
    title = _find("officerTitle", x) or ""
    is_dir = "<isdirector>true" in x.lower() or "<isDirector>true" in x
    is_ten = "<istenpercentowner>true" in x.lower() or "<isTenPercentOwner>1" in x
    tenb51 = bool(re.search(r"10b5-?1", x, re.I))
    role = title or ("Director" if is_dir else ("10% owner" if is_ten else "Officer"))
    out = []
    for t in re.findall(r"<nonDerivativeTransaction>(.*?)</nonDerivativeTransaction>", x, re.S):
        code = _find("transactionCode", t) or "?"
        ad = _find("transactionAcquiredDisposedCode", t) or "?"
        sh = _find("transactionShares", t); pr = _find("transactionPricePerShare", t)
        try:
            val = float(sh) * float(pr)
        except Exception:
            val = 0.0
        out.append({"who": who, "role": role, "code": code, "ad": ad, "value": val,
                    "is10b51": tenb51, "is_csuite": any(c in role.lower() for c in _CSUITE)})
    return out


def insider_signal_edgar(ticker: str, window_days: int = _WINDOW, drop_10b51: bool = True) -> InsiderSignal:
    cik = _ticker_map().get(ticker.upper())
    if not cik:
        return InsiderSignal(0.0, "no-data", False, 0, 0.0, "", "no CIK", "SEC EDGAR Form 4")
    sub = json.loads(_get(f"https://data.sec.gov/submissions/CIK{cik}.json")); time.sleep(_PAUSE)
    rec = sub["filings"]["recent"]
    since = (dt.date.today() - dt.timedelta(days=window_days)).isoformat()
    idx = [i for i, f in enumerate(rec["form"]) if f == "4" and rec["filingDate"][i] >= since]
    txs = []
    for j in idx:
        try:
            txs += _parse_form4(cik, rec["accessionNumber"][j])
        except Exception:
            continue
    # keep only genuine open-market P (buy) / S (sale); drop A/M/F/G/... ; optionally drop 10b5-1
    def keep(t):
        if drop_10b51 and t["is10b51"]:
            return False
        return t["code"] in ("P", "S")
    buys = [t for t in txs if keep(t) and t["code"] == "P"]
    sells = [t for t in txs if keep(t) and t["code"] == "S"]
    buy_val = sum(t["value"] for t in buys); sell_val = sum(t["value"] for t in sells)
    buyers = len({t["who"] for t in buys}); cluster = buyers >= 2
    csuite_buy = any(t["is_csuite"] for t in buys)

    swamped = sell_val > 3 * buy_val
    buy_sig = 0.0
    if buy_val > 0 and not swamped:
        buy_sig = (0.6 + 0.4 * _clip(buy_val / _SCALE, 0, 1)) if cluster else \
                  (0.3 + 0.4 * _clip(buy_val / _SCALE, 0, 1)) if buy_val >= _SCALE else 0.2
        if csuite_buy:
            buy_sig = min(1.0, buy_sig + 0.15)
    sell_sig = -_clip(0.35 * sell_val / (_SCALE * 40), 0, 0.35)
    score = _clip(buy_sig + sell_sig, -1, 1)
    label = ("cluster-buy" if cluster else "buy") if score >= 0.6 else "buy" if score >= 0.25 \
        else "neutral" if score > -0.2 else "selling" if score > -0.32 else "heavy-selling"

    top = max(buys, key=lambda t: t["value"], default=None)
    top_buy = f"{top['who']} ({top['role']}) ${top['value']:,.0f}" if top else ""
    dropped = len(txs) - len(buys) - len(sells)
    note = (f"EDGAR: {buyers} P-buyer(s) ${buy_val:,.0f} vs S-sale ${sell_val:,.0f} in {window_days}d"
            + (f"; top {top_buy}" if top_buy else "") + ("; CLUSTER" if cluster else "")
            + ("; C-suite" if csuite_buy else "")
            + f"; dropped {dropped} mechanical (A/M/F/G/10b5-1) tx")
    return InsiderSignal(round(score, 2), label, cluster, buyers, round(buy_val - sell_val, 0),
                         top_buy, note, "SEC EDGAR Form 4")


import os

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "insider_cache.json")


def _universe_tickers():
    """Tier-2 names to cache = every thesis ticker (from themes.yaml)."""
    import yaml
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "themes.yaml")
    themes = (yaml.safe_load(open(p, encoding="utf-8")) or {}).get("themes", {}) or {}
    names = set()
    for t in themes.values():
        names.update(t.get("tickers") or [])
    return sorted(names)


def build(tickers=None):
    """Fetch+parse EDGAR Form 4 for each ticker -> thesis/insider_cache.json (the scan reads this;
    SLOW, so run offline / on a schedule, never inside the live scan). Resumable-ish: overwrites."""
    tickers = tickers or _universe_tickers()
    cache = {}
    if os.path.exists(CACHE):
        try:
            cache = json.load(open(CACHE, encoding="utf-8"))
        except Exception:
            cache = {}
    asof = dt.date.today().isoformat()
    for i, t in enumerate(tickers, 1):
        try:
            s = insider_signal_edgar(t)
            cache[t.upper()] = {"score": s.score, "label": s.label, "cluster": s.cluster,
                                "buyers": s.buyers, "net_value": s.net_value, "top_buy": s.top_buy,
                                "note": s.note, "source": s.source, "asof": asof}
            print(f"[insider-edgar] {i}/{len(tickers)} {t}: {s.label} {s.score}")
        except Exception as e:
            print(f"[insider-edgar] {i}/{len(tickers)} {t}: ERR {str(e)[:50]}")
        json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"[insider-edgar] wrote {len(cache)} signals -> {CACHE}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "build":
        build(a[1:] or None)
    else:
        for t in (a or ["AEHR", "USAR", "MU"]):
            s = insider_signal_edgar(t)
            print(f"\n{t}: {s.label}  score={s.score}  cluster={s.cluster}  net=${s.net_value:,.0f}")
            print(f"   {s.note}")
