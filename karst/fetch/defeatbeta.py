"""DefeatBeta adapter: transcripts, quarterly statements, revenue breakdown, shares, splits, calendar, info for one ticker.

Lands ``<out>/defeatbeta/<name>.json`` + ``.meta.json``. Empty frames -> ``status: empty``;
exceptions -> ``status: error`` (meta only). ``ticker_factory`` lets tests inject a fake Ticker.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
import sys
from pathlib import Path

from .common import clean_value, frame_records, write_json, write_meta
from .port import LandedRecord, options_for, scan, ticker_for

SOURCE = "defeatbeta"
# The kinds this adapter is the default source for (refresh_sources routing). It also
# lands filing_index (the transcript catalogue) and prices (splits); those kinds are
# routed to their own adapters.
KINDS = ("transcript", "financials", "calendar", "profile")
# tool text -> kind, in order; the first token that appears decides.
TOOL_KIND_TOKENS = (("calendar", "calendar"), ("info", "profile"), ("shares", "financials"),
                    ("splits", "prices"), ("quarterly_", "financials"), ("price", "prices"))
DATASET_URL = "https://huggingface.co/datasets/defeatbeta/yahoo-finance-data"
STATEMENTS = ("quarterly_income_statement", "quarterly_balance_sheet", "quarterly_cash_flow")
STATEMENT_GAPS = [
    "'*' string means value not available in source (kept verbatim)",
    "values are strings/objects mixed with floats as returned",
    "some period columns may be entirely '*' (source gap)",
    "currency/unit not embedded in table; see 'currency' field if available",
]
FRAMES = {  # name -> (period column, known gaps)
    "quarterly_revenue_by_breakdown": ("report_date", ["segment/geography breakdown may be absent for this ticker"]),
    "shares": ("report_date", ["shares_outstanding dates are source report dates, not filing cover dates"]),
    "splits": ("report_date", []),
    "calendar": ("report_date", ["'time' may be 'time-not-supplied'; future rows are scheduled not confirmed"]),
}
TRANSCRIPT_GAPS = [
    "source has no prepared-remarks vs Q&A section marker; only paragraph_number/speaker/content (split must be inferred, e.g. from Operator paragraphs)",
    "speaker names as given by source (may lack titles/roles)",
]
LIST_GAPS = ["list may not be contiguous by quarter (source coverage gaps kept as-is)", "no availability timestamp for transcript text"]


def open_ticker(ticker: str):
    """Import defeatbeta lazily (its banner prints to stdout) and build a Ticker."""
    with contextlib.redirect_stdout(io.StringIO()):
        from defeatbeta_api.data.ticker import Ticker  # noqa: PLC0415
        return Ticker(ticker)


def library_info(ticker_obj) -> tuple[str | None, str | None]:
    version = remote = None
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            import defeatbeta_api  # noqa: PLC0415
        version = getattr(defeatbeta_api, "__version__", None)
    except ImportError:
        pass
    client = getattr(ticker_obj, "duckdb_client", None)
    reader = getattr(client, "_read_cached_spec_update_time", None)
    if callable(reader):
        try:
            remote = reader()
        except Exception:  # noqa: BLE001 - informational only
            remote = None
    return version, clean_value(remote)


def _columns(frame) -> list:
    return [str(c) for c in frame.columns] if hasattr(frame, "columns") else []


def _span(records: list[dict], key: str | None) -> dict:
    values = sorted(str(r[key]) for r in records if key and r.get(key) is not None) if records else []
    if values:
        return {"from": values[0], "to": values[-1], "count": len(records)}
    return {"count": len(records)}


def truncate_paragraphs(paragraphs: list[dict], max_chars: int | None) -> tuple[list[dict], dict]:
    """Cut a transcript's paragraphs at a cumulative content-character budget (None = keep everything)."""
    total = sum(len(p.get("content") or "") for p in paragraphs)
    if not max_chars or total <= max_chars:
        return paragraphs, {"is_truncated": False, "rule": f"content chars cumulative <= {max_chars}" if max_chars else "no cut",
                            "original_chars": total, "kept_paragraphs": len(paragraphs), "cut_at_paragraph_number": None,
                            "total_paragraphs": len(paragraphs)}
    kept, used, cut_at = [], 0, None
    for para in paragraphs:
        content = para.get("content") or ""
        if used + len(content) > max_chars:
            room = max_chars - used
            if room > 0:
                kept.append({**para, "content": content[:room], "_truncated_paragraph": True})
            cut_at = para.get("paragraph_number")
            break
        kept.append(para)
        used += len(content)
    return kept, {"is_truncated": True, "rule": f"content chars cumulative <= {max_chars}", "original_chars": total,
                  "kept_paragraphs": len(kept), "cut_at_paragraph_number": cut_at, "total_paragraphs": len(paragraphs)}


def fetch_company(ticker: str, out_dir, *, transcripts: int = 1, max_transcript_chars: int | None = None,
                  ticker_factory=None) -> dict[str, str]:
    """Land the DefeatBeta tables for ``ticker`` under ``<out_dir>/defeatbeta/``; returns ``{name: status}``."""
    out = Path(out_dir) / "defeatbeta"
    out.mkdir(parents=True, exist_ok=True)
    obj = (ticker_factory or open_ticker)(ticker)
    version, remote = library_info(obj)
    base = {"source": "defeatbeta", "params": {"ticker": ticker}, "library_version": version,
            "cache_update_time_remote": remote, "source_url": DATASET_URL}
    statuses: dict[str, str] = {}

    def land(name: str, tool: str, produce, params=None):
        meta_params = {**base["params"], **(params or {})}
        try:
            payload, meta = produce()
        except Exception as exc:  # noqa: BLE001 - recorded as status error, never invented as empty
            write_meta(out / f"{name}.meta.json", **{**base, "params": meta_params}, tool=tool, status="error",
                       status_reason=f"source call failed: {type(exc).__name__}: {exc}",
                       error=f"{type(exc).__name__}: {exc}", known_gaps=[f"source call failed: {type(exc).__name__}: {exc}"])
            statuses[name] = "error"
            return None
        records = payload.get("records")
        status = "ok" if records else "empty"
        gaps, reason = list(meta.pop("known_gaps", [])), None
        if status == "empty":
            reason = "empty DataFrame returned by source (kept as empty records); 'nothing to report' and 'not covered' are different"
            gaps.append("empty DataFrame returned by source (kept as empty records)")
        write_json(out / f"{name}.json", {"tool": tool, **payload})
        write_meta(out / f"{name}.json", **{**base, "params": meta_params}, tool=tool, **meta, known_gaps=gaps,
                   status=status, status_reason=reason)
        statuses[name] = status
        return payload

    # transcripts: list, then newest N full texts
    def _list():
        frame = obj.earning_call_transcripts().get_transcripts_list()
        rows = frame_records(frame)
        return ({"columns": _columns(frame), "records": rows},
                {"published_at": None, "period": _span(rows, "report_date"),
                 "published_at_basis": "per-row report_date only (date precision); transcript text availability time not provided by source (資料來源 §四 4)",
                 "known_gaps": LIST_GAPS})

    listing = land("earning_call_transcripts.list", "Ticker.earning_call_transcripts().get_transcripts_list()", _list)
    rows = (listing or {}).get("records") or []
    rows = sorted(rows, key=lambda r: (int(r.get("fiscal_year") or 0), int(r.get("fiscal_quarter") or 0)))
    for row in rows[-transcripts:] if transcripts else []:
        fy, fq, report_date = int(row["fiscal_year"]), int(row["fiscal_quarter"]), row.get("report_date")

        def _one(fy=fy, fq=fq, report_date=report_date):
            frame = obj.earning_call_transcripts().get_transcript(fy, fq)
            paragraphs = frame_records(frame)
            kept, truncated = truncate_paragraphs(paragraphs, max_transcript_chars)
            speakers = sorted({p.get("speaker") for p in paragraphs if p.get("speaker")})
            return ({"params": {"fiscal_year": fy, "fiscal_quarter": fq}, "report_date": report_date, "columns": _columns(frame),
                     "paragraph_count_total": len(paragraphs), "speakers": speakers, "records": kept},
                    {"published_at": report_date,
                     "published_at_basis": "report_date from transcripts list (date precision, call date); time the text became readable is unknown",
                     "period": {"fiscal_year": fy, "fiscal_quarter": fq, "report_date": report_date},
                     "truncated": truncated, "known_gaps": TRANSCRIPT_GAPS})

        land(f"earning_call_transcript.FY{fy}Q{fq}", "Ticker.earning_call_transcripts().get_transcript", _one,
             params={"fiscal_year": fy, "fiscal_quarter": fq})

    # quarterly statements
    def _currency():
        try:
            value = obj.currency()
            return frame_records(value) if hasattr(value, "to_dict") else clean_value(value)
        except Exception:  # noqa: BLE001
            return None

    for name in STATEMENTS:
        def _statement(name=name):
            statement = getattr(obj, name)()
            frame = statement.data
            columns = _columns(frame)
            return ({"columns": columns, "row_meta": clean_value(getattr(statement, "row_meta", None)), "records": frame_records(frame)},
                    {"published_at": None,
                     "published_at_basis": "column headers are period-end dates; filing/publication dates not provided by this interface",
                     "period": {"period_end_columns": [c for c in columns if c not in ("Breakdown", "TTM")], "has_TTM": "TTM" in columns},
                     "currency": _currency(), "known_gaps": STATEMENT_GAPS})

        land(name, f"Ticker.{name}().data", _statement)

    # simple frames
    for name, (period_key, gaps) in FRAMES.items():
        def _frame(name=name, period_key=period_key, gaps=gaps):
            frame = getattr(obj, name)()
            rows = frame_records(frame)
            return ({"columns": _columns(frame), "records": rows},
                    {"published_at": None, "published_at_basis": f"per-row {period_key} (date precision)" if rows else None,
                     "period": _span(rows, period_key), "known_gaps": gaps})

        land(name, f"Ticker.{name}()", _frame)

    def _info():
        info = obj.info()
        if hasattr(info, "to_dict"):
            return {"columns": _columns(info), "records": frame_records(info)}, {"known_gaps": ["snapshot of current metadata; no as-of history"]}
        return {"records": clean_value(info)}, {"known_gaps": ["snapshot of current metadata; no as-of history"]}

    land("info", "Ticker.info()", _info)
    return statuses


def kind_for(meta) -> str:
    """Declared per tool. The transcript catalogue is an index, NOT transcript text."""
    tool = str(meta.get("tool") or "")
    if re.search(r"get_transcript(?:\(|$)", tool):
        return "transcript"
    if "earning_call_transcripts" in tool:
        return "filing_index"
    for token, kind in TOOL_KIND_TOKENS:
        if token in tool:
            return kind
    raise ValueError(f"no declared kind for defeatbeta tool {tool!r}")


def fetch(security, out_dir, *, since=None, client=None) -> list[LandedRecord]:
    """Land this security's DefeatBeta tables. ``client`` is a ``ticker -> Ticker`` factory.

    ``since`` is not a filter: the vendor returns whole tables, and the newest N
    transcripts are selected by fiscal quarter, not by date.
    """
    fetch_company(ticker_for(security), out_dir, **options_for(client, "ticker_factory"))
    return scan(Path(out_dir) / SOURCE, kind_for)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Land DefeatBeta tables for one ticker under <out>/defeatbeta/.")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--transcripts", type=int, default=1, help="newest N transcripts with full text")
    parser.add_argument("--max-transcript-chars", type=int, default=None, help="default: no cut")
    args = parser.parse_args(argv)
    statuses = fetch_company(args.ticker, args.out, transcripts=args.transcripts, max_transcript_chars=args.max_transcript_chars)
    json.dump(statuses, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")
    return 0 if "error" not in statuses.values() else 1


if __name__ == "__main__":
    sys.exit(main())
