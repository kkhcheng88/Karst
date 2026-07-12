"""thesis/altdata_eia_grid.py -- EIA-930 hourly grid demand altdata probe (WS4 top-5 probe #2).

docs/2026-07-08_phase3_ws4_early_detection.md table row 14, item "EIA-930 電網逐時(AI-電力)".
Real-time-ish electricity demand as an early confirmation/disconfirmation read for the
ai-power-grid thesis (part of Karst's largest single meta_factor bet, ai-capex, 54.9% of
confidence-weight -- see thesis/themes.yaml META_FACTOR TAXONOMY REGISTRY, 2026-07-12).

Source: EIA API v2, /electricity/rto/region-data/ (Form EIA-930, Hourly Electric Grid Monitor).
Requires a free self-registered API key (eia.gov/opendata/register.php) -- user obtained and
provided 2026-07-12, stored at ~/.config/eia/api_key (mode 600, same convention as the IMA
credentials). Verified live 2026-07-12: 200 OK, real current-hour PJM demand data.

Region: PJM Interconnection only (v1 scope) -- the single largest US RTO and the most
concentrated "Data Center Alley" market (Northern Virginia). ai-power-grid's own tickers
(GNRC/SPXC/CAT/VRT/WOLF/VICR etc.) are equipment suppliers, not regional utilities, so there is
no clean per-ticker EIA mapping the way TWSE has one -- this tracks AGGREGATE demand growth as a
theme-level (not ticker-level) confirmation read, same role as the ai-capex-macro-risk.md hub
page's five lights. Other datacenter-heavy RTOs (ERCOT, MISO) are a natural v2 extension, not
built here (spec's own "3-7 instruments per theme cap" -- start with the cleanest single proxy).

v1 is DATA-COLLECTION + DISPLAY ONLY -- prints trailing-7-day demand vs the same 7-day window
one year ago (YoY %). Deliberately does NOT assert a threshold ("X% YoY = confirmed AI-driven
acceleration") -- that needs a real historical calibration pass first (same discipline the WS4
spec demands of ISM before "admission"; grid demand also has ordinary weather/economic-cycle
drivers that have to be distinguished from an AI-specific effect before this can drive a verdict).

Output: appends to thesis/.raw/altdata_eia_grid_history.jsonl (gitignored), prints latest read.

Run: python thesis/altdata_eia_grid.py
"""
from __future__ import annotations

import datetime
import json
import os
import urllib.request
import urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
KEY_PATH = os.path.join(os.path.expanduser("~"), ".config", "eia", "api_key")
HISTORY_PATH = os.path.join(ROOT, ".raw", "altdata_eia_grid_history.jsonl")
BASE_URL = "https://api.eia.gov/v2/electricity/rto/region-data/data/"
RESPONDENT = "PJM"
WINDOW_DAYS = 7


def _load_key():
    if not os.path.exists(KEY_PATH):
        raise RuntimeError(f"no EIA API key at {KEY_PATH} -- register free at "
                            f"eia.gov/opendata/register.php and save the key there")
    return open(KEY_PATH, encoding="utf-8").read().strip()


def _fetch_window(key, start, end):
    """start/end: datetime, hour-resolution. Returns list of (period_str, value_float)."""
    params = {
        "frequency": "hourly", "data[0]": "value",
        "facets[respondent][]": RESPONDENT, "facets[type][]": "D",
        "start": start.strftime("%Y-%m-%dT%H"), "end": end.strftime("%Y-%m-%dT%H"),
        "sort[0][column]": "period", "sort[0][direction]": "asc",
        "length": 5000, "api_key": key,
    }
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Karst-research/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.loads(r.read().decode("utf-8"))
    rows = body.get("response", {}).get("data", [])
    return [(row["period"], float(row["value"])) for row in rows if row.get("value") not in (None, "")]


def _avg(rows):
    vals = [v for _, v in rows]
    return sum(vals) / len(vals) if vals else None


def run():
    key = _load_key()
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    recent_start = now - datetime.timedelta(days=WINDOW_DAYS)
    year_ago_end = now - datetime.timedelta(days=365)
    year_ago_start = year_ago_end - datetime.timedelta(days=WINDOW_DAYS)

    print(f"[altdata_eia_grid] fetching {RESPONDENT} demand: trailing {WINDOW_DAYS}d + same "
          f"window 1yr ago...")
    recent = _fetch_window(key, recent_start, now)
    year_ago = _fetch_window(key, year_ago_start, year_ago_end)
    recent_avg = _avg(recent)
    year_ago_avg = _avg(year_ago)
    print(f"[altdata_eia_grid] recent: {len(recent)} hourly reads, avg {recent_avg:,.0f} MWh"
          if recent_avg else "[altdata_eia_grid] recent: no data")
    print(f"[altdata_eia_grid] year-ago: {len(year_ago)} hourly reads, avg {year_ago_avg:,.0f} MWh"
          if year_ago_avg else "[altdata_eia_grid] year-ago: no data")

    if recent_avg is None or year_ago_avg is None:
        print("[altdata_eia_grid] insufficient data for a YoY read this run")
        return

    yoy_pct = (recent_avg / year_ago_avg - 1) * 100
    today_str = datetime.date.today().isoformat()
    rec = {
        "date": today_str, "respondent": RESPONDENT, "window_days": WINDOW_DAYS,
        "recent_avg_mwh": round(recent_avg, 1), "year_ago_avg_mwh": round(year_ago_avg, 1),
        "yoy_pct": round(yoy_pct, 2),
    }
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[altdata_eia_grid] {RESPONDENT} demand YoY: {yoy_pct:+.2f}% "
          f"(NOT a verdict -- raw data-collection read, see module docstring)")


if __name__ == "__main__":
    run()
