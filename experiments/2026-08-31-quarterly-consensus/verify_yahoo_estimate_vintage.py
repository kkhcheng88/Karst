"""KARST-125 core evidence: is Yahoo's per-quarter "EPS Estimate" a frozen
pre-announcement consensus snapshot, or is it rewritten later?

Method (vintage comparison, same as KARST-121 used on the S&P spreadsheet):
  1. Pull Wayback Machine snapshots of Yahoo's own earnings-calendar page for a
     ticker, taken YEARS ago.
  2. Extract the per-quarter "EPS Estimate" values that page showed AT THAT TIME.
  3. Pull today's yfinance get_earnings_dates() for the same quarters.
  4. Cell-by-cell diff. Zero differences => Yahoo does not rewrite the estimate,
     i.e. the value stored against each earnings date is a genuine vintage.
  5. Bonus: a snapshot taken BEFORE an earnings date shows the estimate for a
     quarter not yet reported. If that forward-looking value equals what is
     stored today against that (now reported) quarter, the stored value is
     proven to be the PRE-ANNOUNCEMENT consensus, not a post-hoc figure.

Only web.archive.org is fetched programmatically (its API is public and
documented). Yahoo itself is reached only through yfinance, already a repo
dependency.

Run:  set PYTHONUTF8=1 && python verify_yahoo_estimate_vintage.py
Output: out/vintage_*.json, out/vintage_report.txt
"""
import json
import os
import re
import time
import traceback
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
# Raw archived pages are big and re-downloadable, so they go to data/, which the
# repo .gitignore already excludes (experiments/*/data/).
RAW = os.path.join(HERE, "data")
os.makedirs(OUT, exist_ok=True)
os.makedirs(RAW, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) KARST-125-research"
TICKERS = ["CROX", "AAPL", "NVDA", "MSFT", "INTC", "TSLA"]

log_lines = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    log_lines.append(s)


def get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def cdx(url_pattern, limit=200):
    """List Wayback captures for a URL."""
    api = ("https://web.archive.org/cdx/search/cdx?url="
           + urllib.parse.quote(url_pattern, safe="")
           + f"&output=json&limit={limit}&filter=statuscode:200&collapse=timestamp:6")
    try:
        raw = get(api)
        rows = json.loads(raw) if raw.strip() else []
        return rows[1:] if rows else []
    except Exception as e:
        log(f"  cdx failed for {url_pattern}: {type(e).__name__}: {str(e)[:150]}")
        return []


def extract_earnings_rows(html):
    """Yahoo embedded its page data as JSON in the HTML for many years.
    Pull every {..."epsestimate":X..., "startdatetime":"..."} record we can find."""
    rows = []

    # Form A: the calendar page's embedded JSON records
    for m in re.finditer(
            r'"ticker"\s*:\s*"([A-Z.\-]+)".{0,600}?"startdatetime"\s*:\s*"([0-9T:\-+.Z]+)"'
            r'.{0,600}?"epsestimate"\s*:\s*(-?[0-9.]+|null)'
            r'.{0,400}?"epsactual"\s*:\s*(-?[0-9.]+|null)',
            html, re.S):
        rows.append({"ticker": m.group(1), "date": m.group(2),
                     "epsestimate": m.group(3), "epsactual": m.group(4),
                     "form": "A"})

    # Form B: fields in the other order
    if not rows:
        for m in re.finditer(
                r'"startdatetime"\s*:\s*"([0-9T:\-+.Z]+)".{0,800}?'
                r'"epsestimate"\s*:\s*(-?[0-9.]+|null)', html, re.S):
            rows.append({"ticker": None, "date": m.group(1),
                         "epsestimate": m.group(2), "epsactual": None,
                         "form": "B"})

    # Form C: quoteSummary earningsHistory module. Yahoo embedded this as
    # root.App.main JSON for years.
    #
    # NOTE (bug found 2026-08-31): a regex of the shape "quarter ... epsEstimate"
    # silently pairs quarter[N] with epsEstimate[N+1], because inside each record
    # Yahoo emits epsActual/epsEstimate BEFORE quarter. That produced a clean
    # one-quarter shift that looks exactly like "Yahoo rewrote the estimate".
    # So parse the JSON array properly instead of pattern-matching across records.
    if not rows:
        rows.extend(_parse_earnings_history_json(html))
    return rows


def _parse_earnings_history_json(html):
    """Locate "earningsHistory":{"history":[ ... ] and brace-match the array."""
    out = []
    for m in re.finditer(r'"earningsHistory"\s*:\s*\{\s*"history"\s*:\s*\[', html):
        start = html.index("[", m.end() - 1)
        depth, i = 0, start
        while i < len(html):
            c = html[i]
            if c == "[":
                depth += 1
            elif c == "]":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        try:
            arr = json.loads(html[start:i + 1])
        except Exception:
            continue
        for rec in arr:
            if not isinstance(rec, dict):
                continue
            q = (rec.get("quarter") or {}).get("fmt")
            est = (rec.get("epsEstimate") or {}).get("raw")
            act = (rec.get("epsActual") or {}).get("raw")
            if q and est is not None:
                out.append({"ticker": None, "date": q,
                            "epsestimate": est, "epsactual": act,
                            "period": rec.get("period"), "form": "C"})
        if out:
            break
    return out


def today_table(ticker):
    """Today's stored estimate, keyed BOTH ways.

    The archived pages key rows by FISCAL QUARTER END (e.g. 2019-03-31); the live
    endpoint keys rows by EARNINGS REPORT DATE (e.g. 2019-04-24). So build a
    quarter-end lookup too: for a quarter ending on Q, the covering report is the
    first earnings date falling in (Q, Q+120 days]."""
    import pandas as pd
    import yfinance as yf
    # Yahoo hard-caps this endpoint at 100 rows (yfinance raises above that).
    df = yf.Ticker(ticker).get_earnings_dates(limit=100)
    by_report, by_quarter = {}, {}
    if df is None or df.empty:
        return by_report, by_quarter
    dates = sorted(pd.Timestamp(d).tz_localize(None) for d in df.index)
    est = {pd.Timestamp(i).tz_localize(None): (r.get("EPS Estimate"),
                                               r.get("Reported EPS"))
           for i, r in df.iterrows()}
    for d, v in est.items():
        by_report[str(d)[:10]] = v
    for d in dates:
        # the quarter this report covers ends somewhere in the 120 days before it
        for q_off in range(1, 121):
            q = d - pd.Timedelta(days=q_off)
            key = str(q)[:10]
            # only month-end dates are plausible fiscal quarter ends
            if (q + pd.Timedelta(days=1)).day == 1:
                by_quarter.setdefault(key, est[d])
    return by_report, by_quarter


def main():
    import urllib.parse as up
    globals()["urllib"].parse = up

    all_results = {}
    for t in TICKERS:
        log(f"\n================ {t} ================")
        by_report, by_quarter = today_table(t)
        log(f"  today: {len(by_report)} earnings dates on record, "
            f"{min(by_report) if by_report else '-'} .. "
            f"{max(by_report) if by_report else '-'}")

        candidates = [
            f"finance.yahoo.com/calendar/earnings?symbol={t}",
            f"https://finance.yahoo.com/calendar/earnings?symbol={t}",
            f"finance.yahoo.com/quote/{t}/analysis",
        ]
        caps = []
        for c in candidates:
            rows = cdx(c)
            log(f"  cdx {c}: {len(rows)} captures")
            for r in rows:
                caps.append((r[1], r[2]))  # timestamp, original url
            time.sleep(1)

        if not caps:
            log("  NO CAPTURES -> cannot run a vintage comparison for this ticker")
            all_results[t] = {"captures": 0}
            continue

        caps.sort()
        # spread the sample: oldest, 1/3, 2/3, newest
        picks = []
        for frac in (0.0, 0.12, 0.25, 0.37, 0.5, 0.62, 0.75, 0.87, 0.99):
            i = min(int(frac * (len(caps) - 1)), len(caps) - 1)
            if caps[i] not in picks:
                picks.append(caps[i])

        tres = {"captures": len(caps), "checked": []}
        for ts, orig in picks:
            wb = f"https://web.archive.org/web/{ts}id_/{orig}"
            log(f"\n  --- snapshot {ts} ---")
            # cache: archived pages never change, so never fetch one twice
            cache = os.path.join(RAW, f"snap_{t}_{ts}.html")
            if os.path.exists(cache) and os.path.getsize(cache) > 1000:
                with open(cache, encoding="utf-8") as f:
                    html = f.read()
                log("    (from cache)")
            else:
                try:
                    html = get(wb, timeout=90)
                except Exception as e:
                    log(f"    fetch failed: {type(e).__name__}: {str(e)[:150]}")
                    continue
                with open(cache, "w", encoding="utf-8") as f:
                    f.write(html)
                time.sleep(2)
            rows = extract_earnings_rows(html)
            rows = [r for r in rows if r["ticker"] in (None, t)]
            log(f"    html {len(html)} bytes, parsed {len(rows)} estimate rows")
            if not rows:
                snip = os.path.join(RAW, f"vintage_raw_{t}_{ts}.html")
                with open(snip, "w", encoding="utf-8") as f:
                    f.write(html[:400000])
                log(f"    (no rows parsed; raw saved -> {snip})")
                continue

            # Record then/now for BOTH estimate and actual, then judge.
            #
            # Split trap: Yahoo restates per-share history for stock splits, so an
            # archived pre-split page shows raw numbers N times today's. That is a
            # change of units, not a rewrite of the forecast. The split-invariant
            # test is to compare the two ratios: if then/now is the SAME factor for
            # the estimate as for the actual, only the units moved. A genuine
            # rewrite moves the estimate's ratio while the actual's stays put,
            # because a reported result is a fact and does not get re-forecast.
            pairs = []
            for r in rows:
                d = r["date"][:10]
                if r["epsestimate"] in (None, "null"):
                    continue
                hit = by_quarter.get(d) or by_report.get(d)
                if hit is None:
                    pairs.append({"date": d, "joined": False})
                    continue
                cur_est, cur_act = hit[0], hit[1]
                def _f(v):
                    try:
                        v = float(v)
                        return v if v == v else None
                    except Exception:
                        return None
                pairs.append({
                    "date": d, "joined": True,
                    "then_est": _f(r["epsestimate"]), "now_est": _f(cur_est),
                    "then_act": _f(r.get("epsactual")), "now_act": _f(cur_act),
                })

            same = diff = missing = 0
            rescaled = 0
            detail = []
            for p in pairs:
                if not p.get("joined") or p.get("then_est") is None \
                        or p.get("now_est") is None:
                    missing += 1
                    continue
                te, ne = p["then_est"], p["now_est"]
                ta, na = p.get("then_act"), p.get("now_act")
                if abs(te - ne) < 0.011:
                    same += 1
                    continue
                # different raw number -- is it just a rescaling (split)?
                if ta and na and ne and na != 0 and ne != 0:
                    r_est, r_act = te / ne, ta / na
                    if abs(r_est - r_act) < 0.02 * max(1.0, abs(r_act)):
                        rescaled += 1
                        detail.append({"date": p["date"],
                                       "then": te, "now": ne,
                                       "verdict": "split-rescaled",
                                       "factor_est": round(r_est, 4),
                                       "factor_act": round(r_act, 4)})
                        continue
                diff += 1
                detail.append({"date": p["date"], "then": te, "now": ne,
                               "then_act": ta, "now_act": na,
                               "verdict": "REWRITTEN"})

            log(f"    unchanged {same} | split-rescaled {rescaled} | "
                f"REWRITTEN {diff} | not comparable {missing}")
            for x in detail[:12]:
                log(f"      {x['date']}: then={x['then']} now={x['now']} "
                    f"-> {x['verdict']}"
                    + (f" (factor est={x['factor_est']} act={x['factor_act']})"
                       if x["verdict"] == "split-rescaled" else
                       f" [actual then={x.get('then_act')} now={x.get('now_act')}]"))
            tres["checked"].append({"timestamp": ts, "same": same,
                                    "rescaled": rescaled,
                                    "diff": diff, "missing": missing,
                                    "pairs": pairs, "detail": detail[:40]})
            time.sleep(2)
        all_results[t] = tres

    with open(os.path.join(OUT, "vintage_results.json"), "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    log("\nsaved -> out/vintage_results.json")


if __name__ == "__main__":
    import urllib.parse  # noqa
    try:
        main()
    except Exception:
        log(traceback.format_exc())
    with open(os.path.join(OUT, "vintage_report.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    print("\nlog -> out/vintage_report.txt")
