"""thesis/altdata_twse.py -- TWSE (Taiwan Stock Exchange) monthly revenue altdata probe.

WS4 altdata top-5 probe item 5 / ROADMAP execution backlog Batch-3 item 8
(docs/2026-07-08_phase3_ws4_early_detection.md table row 14): Taiwan-listed suppliers are
LEGALLY REQUIRED to disclose revenue MONTHLY (unlike US quarterly-only reporting) -- a free,
no-key, high-frequency confirmation signal for chains where a relevant Taiwan supplier exists.
Data source: TWSE OpenAPI (openapi.twse.com.tw), t187ap05_L endpoint -- genuinely public, no
registration, no API key (verified 2026-07-12: plain HTTP GET, 200 OK, JSON array).

v1 scope: only ONE ticker is wired -- ASE Technology Holding (TWSE 3711, US ADR: ASX), the
world's largest OSAT (outsourced semiconductor assembly & test) provider, a direct supply-chain
link to Karst's advanced-packaging theme (memory-supercycle's own basket -- MU/SNDK/WDC/SKHY --
has NO Taiwan-listed member, so no mapping exists there yet; same for the other themes). Mapping
more Taiwan suppliers into other themes is a SEPARATE, deliberately-deferred research task (which
specific Taiwan company is a meaningful chain-confirmation proxy for which theme is a domain
judgment call, not a mechanical lookup) -- flagged here, not rushed.

Output: appends a row to thesis/.raw/altdata_twse_history.jsonl (gitignored, one line per
company-month pulled) + prints the latest MoM/YoY read.

Run: python thesis/altdata_twse.py
"""
from __future__ import annotations

import json
import os
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
HISTORY_PATH = os.path.join(ROOT, ".raw", "altdata_twse_history.jsonl")
TWSE_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap05_L"

# {theme_slug: {twse_code: (name, rationale)}} -- v1: one entry, expand deliberately, not by default
TRACKED = {
    "advanced-packaging": {
        "3711": ("ASE Technology Holding", "world's largest OSAT; direct chain-confirmation "
                 "proxy for advanced-packaging (US ADR: ASX)"),
    },
}


def _roc_to_iso(roc_yyyymm):
    """'11506' (ROC year 115, month 06) -> '2026-06'."""
    roc_year, month = int(roc_yyyymm[:-2]), int(roc_yyyymm[-2:])
    return f"{roc_year + 1911}-{month:02d}"


def fetch():
    req = urllib.request.Request(TWSE_URL, headers={"User-Agent": "Karst-research/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _already_recorded():
    """(twse_code, period) pairs already appended -- disclosure is monthly, this job runs
    weekly, so most runs see nothing new; dedup keeps the history file from growing 4x."""
    seen = set()
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    seen.add((r["twse_code"], r["period"]))
                except Exception:
                    continue
    return seen


def run():
    codes = {code: (slug, name, why)
             for slug, m in TRACKED.items() for code, (name, why) in m.items()}
    if not codes:
        print("[altdata_twse] TRACKED is empty -- nothing to pull")
        return
    print(f"[altdata_twse] fetching TWSE OpenAPI (no key needed)...")
    data = fetch()
    print(f"[altdata_twse] {len(data)} companies in this month's disclosure batch")
    seen = _already_recorded()

    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    hits = []
    for row in data:
        code = row.get("公司代號")
        if code not in codes:
            continue
        slug, name, why = codes[code]
        period = _roc_to_iso(row.get("資料年月", ""))
        if (code, period) in seen:
            continue
        rec = {
            "theme": slug, "twse_code": code, "name_zh": row.get("公司名稱"),
            "period": period,
            "revenue_this_month": row.get("營業收入-當月營收"),
            "mom_pct": row.get("營業收入-上月比較增減(%)"),
            "yoy_pct": row.get("營業收入-去年同月增減(%)"),
            "rationale": why,
        }
        hits.append(rec)
        with open(HISTORY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    if not hits:
        print(f"[altdata_twse] no NEW rows for {list(codes)} (either already recorded this "
              f"period, or this month's disclosure window hasn't opened yet)")
        return
    for rec in hits:
        print(f"[altdata_twse] {rec['theme']} / {rec['name_zh']} ({rec['twse_code']}) "
              f"{rec['period']}: MoM {rec['mom_pct']}% / YoY {rec['yoy_pct']}%")


if __name__ == "__main__":
    run()
