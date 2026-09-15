"""Daily price adapter: local parquet library (key = CIK, shard = int(cik[-2:]) % 16) for the last N trading days,
continued past its last date by DefeatBeta ``Ticker.price()``. Overlapping dates are cross-checked, not merged.

Lands ``<out>/prices/daily.csv`` (+ ``.meta.json``) with a ``source`` column (local | defeatbeta).
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

from .common import clean_value, frame_records, ticker_to_cik, utc_now, write_meta

COLUMNS = ("date", "open", "high", "low", "close", "adj_close", "volume", "ticker", "source", "source_detail", "fetchedAt_source")
CLOSE_TOL = 0.005
VENDOR_DETAIL = "defeatbeta_api Ticker.price() (no adj_close column in source)"
PUBLISHED_BASIS = ("per-row trading date; close is the exchange session close relayed by the vendor (交易所收市,由供應商轉載), no timestamp. "
                   "Local rows carry fetchedAt_source of their library batch; defeatbeta rows carry our fetch time")
COLUMN_NOTES = {
    "date": "YYYY-MM-DD trading day",
    "open/high/low/close": "local: split-adjusted, not dividend-adjusted (data/prices/daily/README); defeatbeta: as returned (adjustment basis not documented by source)",
    "adj_close": "local only (split+dividend adjusted); null for defeatbeta rows",
    "volume": "shares", "ticker": "symbol the row came from", "source": "local | defeatbeta",
    "source_detail": "underlying fetch parameters", "fetchedAt_source": "UTC ISO",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def shard_for(cik: str) -> int:
    return int(str(cik)[-2:]) % 16


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_local_daily(cik: str, parquet_dir) -> dict:
    """Primary-role rows of one entity from its shard, normalised to COLUMNS, plus manifest/role/ticker bookkeeping."""
    import pandas as pd  # noqa: PLC0415 - only the parquet path needs pandas

    parquet_dir = Path(parquet_dir)
    shard = shard_for(cik)
    frame = pd.read_parquet(parquet_dir / f"part_{shard:02d}.parquet")
    entity = frame[frame["entity_id"] == cik]
    primary = entity[entity["series_role"] == "primary"].sort_values("date")
    rows = []
    for rec in frame_records(primary):
        rows.append({"date": str(rec["date"])[:10], "open": rec["open"], "high": rec["high"], "low": rec["low"], "close": rec["close"],
                     "adj_close": rec.get("adj_close"), "volume": rec["volume"], "ticker": rec.get("ticker"), "source": "local",
                     "source_detail": rec.get("source"), "fetchedAt_source": rec.get("fetchedAt")})
    manifest_rows = []
    manifest = parquet_dir / "manifest.csv"
    if manifest.exists():
        with open(manifest, encoding="utf-8", newline="") as handle:
            manifest_rows = [r for r in csv.DictReader(handle) if r.get("entity_id") == cik]
    return {"rows": rows, "shard": shard, "manifest_rows": manifest_rows,
            "roles": {str(k): int(v) for k, v in entity["series_role"].value_counts().items()},
            "tickers": {str(k): int(v) for k, v in entity["ticker"].value_counts().items()}}


def vendor_daily(ticker: str, fetched_at: str | None = None) -> list[dict]:
    """DefeatBeta full daily history for ``ticker`` normalised to COLUMNS (source = defeatbeta)."""
    from .defeatbeta import open_ticker  # noqa: PLC0415

    fetched_at = fetched_at or utc_now()
    rows = []
    for rec in frame_records(open_ticker(ticker).price()):
        rows.append({"date": str(rec.get("report_date") or rec.get("date"))[:10], "open": rec.get("open"), "high": rec.get("high"),
                     "low": rec.get("low"), "close": rec.get("close"), "adj_close": None, "volume": rec.get("volume"),
                     "ticker": rec.get("symbol") or ticker, "source": "defeatbeta", "source_detail": VENDOR_DETAIL,
                     "fetchedAt_source": fetched_at})
    return sorted(rows, key=lambda r: r["date"])


def merge_daily(local_rows: list[dict], vendor_rows: list[dict], *, days: int = 400) -> dict:
    """Last ``days`` local rows + vendor rows after the local last date; overlap report on shared dates (closes within CLOSE_TOL)."""
    local_all = sorted(local_rows, key=lambda r: r["date"])
    local_last = local_all[-1]["date"] if local_all else None
    local_first = local_all[0]["date"] if local_all else None
    window = local_all[-days:] if days else local_all
    vendor = sorted(vendor_rows or [], key=lambda r: r["date"])
    continuation = [r for r in vendor if local_last is None or r["date"] > local_last]
    by_date = {r["date"]: r for r in vendor}
    rel, bad, vol_diff_days, vol_rel_max = [], [], 0, 0.0
    for row in window:
        other = by_date.get(row["date"])
        if other is None:
            continue
        close_a, close_b = _num(row["close"]), _num(other["close"])
        if close_a is not None and close_b:
            diff = abs(close_a - close_b) / abs(close_b)
            rel.append(diff)
            if diff > CLOSE_TOL:
                bad.append({"date": row["date"], "close_local": close_a, "close_db": close_b})
        vol_a, vol_b = _num(row["volume"]), _num(other["volume"])
        if vol_a is not None and vol_b is not None and vol_a != vol_b:
            vol_diff_days += 1
            if vol_b:
                vol_rel_max = max(vol_rel_max, abs(vol_a - vol_b) / vol_b)
    window_dates = {r["date"] for r in window}
    report = {
        "overlap_days": len(rel), "local_slice_days": len(window),
        "close_rel_diff_max": max(rel) if rel else None, "close_rel_diff_median": statistics.median(rel) if rel else None,
        "days_close_rel_diff_over_0.5pct": len(bad), "examples_over_tol": bad[:10],
        "volume_diff_days": vol_diff_days, "volume_rel_diff_max": vol_rel_max if rel else None,
        "local_dates_missing_in_defeatbeta": sorted(window_dates - set(by_date)) if vendor else [],
        "defeatbeta_dates_missing_in_local_window": sorted(d for d in by_date if window and window[0]["date"] <= d <= local_last and d not in window_dates),
    }
    merged = window + continuation
    dates = [r["date"] for r in merged]
    return {"rows": merged, "overlap_check": report, "local_last": local_last, "local_first": local_first,
            "continuation_from": continuation[0]["date"] if continuation else None,
            "local_rows": len(window), "vendor_rows": len(continuation), "duplicate_dates": len(dates) - len(set(dates)),
            "vendor_last": vendor[-1]["date"] if vendor else None}


def fetch_daily(cik: str, ticker: str, out_dir, *, parquet_dir=None, days: int = 400, continue_with_defeatbeta: bool = True,
                local: dict | None = None, vendor_rows: list[dict] | None = None) -> dict:
    """Land ``<out_dir>/prices/daily.csv`` + meta. ``local``/``vendor_rows`` can be injected (tests, replays)."""
    cik = str(cik).zfill(10)
    parquet_dir = Path(parquet_dir or repo_root() / "data" / "prices" / "daily")
    out = Path(out_dir) / "prices"
    out.mkdir(parents=True, exist_ok=True)
    fetched_at = utc_now()
    local = local or load_local_daily(cik, parquet_dir)
    gaps, vendor_error = [], None
    if vendor_rows is None and continue_with_defeatbeta:
        try:
            vendor_rows = vendor_daily(ticker, fetched_at)
        except Exception as exc:  # noqa: BLE001 - a failed continuation is a recorded gap, not a silent short series
            vendor_error = f"{type(exc).__name__}: {exc}"
            gaps.append(f"defeatbeta continuation failed: {vendor_error}; local rows only")
            vendor_rows = []
    vendor_rows = vendor_rows or []
    merged = merge_daily(local["rows"], vendor_rows, days=days)
    rows = merged["rows"]
    csv_path = out / "daily.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: clean_value(row.get(key)) for key in COLUMNS})
    if merged["local_last"] and merged["vendor_last"] and merged["vendor_last"] <= merged["local_last"]:
        gaps.append(f"defeatbeta history ends {merged['vendor_last']}, not past local last date {merged['local_last']}; no continuation rows")
    if continue_with_defeatbeta:
        gaps += [
            "no adj_close for defeatbeta rows (source has none); stitching adjusted series across the seam requires re-derivation",
            f"local library last date for this entity is {merged['local_last']}; continuation starts {merged['continuation_from']}",
            f"defeatbeta last row {merged['vendor_last']} at fetch time; sessions after that not yet in dataset",
            "defeatbeta price dataset refresh cadence unknown; last row may lag the latest session",
        ]
    else:
        gaps.append(f"local library only; series ends at the library's last date {merged['local_last']}")
    gaps.append("neither source carries a trading calendar; missing rows = no quote that day")
    if merged["overlap_check"]["days_close_rel_diff_over_0.5pct"]:
        gaps.append(f"{merged['overlap_check']['days_close_rel_diff_over_0.5pct']} overlap days differ in close by more than {CLOSE_TOL:.1%}; see overlap_check.examples_over_tol")
    source = "local-prices + defeatbeta" if continue_with_defeatbeta else "local-prices"
    write_meta(
        csv_path, source=source,
        tool=f"pandas.read_parquet(part_{local['shard']:02d}.parquet)[entity_id==cik, series_role=='primary'].tail({days})"
             + (f" + defeatbeta_api Ticker.price()[date>{merged['local_last']}]" if continue_with_defeatbeta else ""),
        params={"ticker": ticker, "cik": cik, "shard": local["shard"], "n_local": days, "continuation_from": merged["continuation_from"],
                "continuation_rule": "first vendor date after local last date", "continue_with_defeatbeta": continue_with_defeatbeta},
        fetched_at=fetched_at, published_at=None, published_at_basis=PUBLISHED_BASIS,
        data_as_of=rows[-1]["date"] if rows else None,
        period={"from": rows[0]["date"] if rows else None, "to": rows[-1]["date"] if rows else None, "rows": len(rows),
                "local_rows": merged["local_rows"], "defeatbeta_rows": merged["vendor_rows"],
                "local_library_first_date": merged["local_first"], "local_library_last_date": merged["local_last"]},
        columns=COLUMN_NOTES,
        truncated={"is_truncated": len(local["rows"]) > merged["local_rows"], "rule": f"last {days} local trading days only"},
        overlap_check=merged["overlap_check"], local_manifest_rows=local["manifest_rows"],
        local_entity_rows_by_role=local["roles"], local_entity_rows_by_ticker=local["tickers"],
        duplicate_dates_in_merged=merged["duplicate_dates"], continuation_error=vendor_error,
        known_gaps=gaps, status="ok" if rows else "empty", source_url=None,
    )
    return {"path": str(csv_path), "rows": len(rows), "local_rows": merged["local_rows"], "defeatbeta_rows": merged["vendor_rows"],
            "overlap_check": merged["overlap_check"], "status": "ok" if rows else "empty"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Land the daily price series for one entity under <out>/prices/.")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--cik", help="default: resolve ticker via --tickers-json")
    parser.add_argument("--out", required=True)
    parser.add_argument("--parquet-dir")
    parser.add_argument("--days", type=int, default=400)
    parser.add_argument("--no-continue", action="store_true", help="local library only, no DefeatBeta continuation")
    parser.add_argument("--tickers-json", default=str(repo_root() / "data" / "sec" / "company_tickers.json"))
    args = parser.parse_args(argv)
    cik = args.cik or ticker_to_cik(args.ticker, args.tickers_json)
    result = fetch_daily(cik, args.ticker, args.out, parquet_dir=args.parquet_dir, days=args.days, continue_with_defeatbeta=not args.no_continue)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
