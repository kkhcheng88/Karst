"""EDGAR adapter: local submissions index -> selected filings -> local 10-K cache first (D-134), else EDGAR Archives.

Lands ``<out>/edgar/<accession>.<form>[.EX-99.1].raw.<ext>[.gz]`` + ``.txt`` + ``.meta.json``
and ``<out>/edgar/CIK<10>.submissions_slice.json`` + meta. Network only through ``http_get``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

from .common import (RateLimiter, html_to_text, repo_root, sha256_bytes, ticker_to_cik, to_utc_z,
                     write_json, write_meta)
from .port import LandedRecord, cik_for, options_for, scan

SOURCE = "edgar"
KINDS = ("filing", "filing_index")

ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
ROW_FIELDS = (
    "accessionNumber", "form", "filingDate", "reportDate", "acceptanceDateTime", "items",
    "primaryDocument", "primaryDocDescription", "isXBRL", "isInlineXBRL", "size",
)
HEADER_FIELDS = (
    "name", "sic", "sicDescription", "tickers", "exchanges", "fiscalYearEnd", "stateOfIncorporation",
    "entityType", "category",
)
GZIP_OVER_BYTES = 1_000_000
TEXT_EXTS = (".htm", ".html", ".xml", ".txt")
ACCEPTANCE_BASIS = (
    "EDGAR acceptanceDateTime of the accession (UTC). Not necessarily first public release time; "
    "8-K press release may have been issued earlier (資料來源 §四 4)"
)
FILING_DATE_BASIS = "EDGAR filingDate only (date precision; acceptanceDateTime absent in local index) — no time of day"
INDEX_BASIS = "per-row filingDate (date precision) and acceptanceDateTime (EDGAR UTC); no single publish time for the index"
TEXT_DERIVATION = "regex strip script/style/comments/tags, html.unescape, whitespace collapse"


class HttpGet:
    """GET bytes with a User-Agent, gzip transport, ``rate`` req/s and one retry. Raises the last error."""

    def __init__(self, user_agent: str, rate: float = 4, retries: int = 1, timeout: int = 60):
        if not user_agent:
            raise ValueError("EDGAR requires a User-Agent with contact info (KARST_EDGAR_USER_AGENT or --user-agent)")
        self.user_agent, self.retries, self.timeout = user_agent, retries, timeout
        self.limiter = RateLimiter(rate)

    def __call__(self, url: str) -> bytes:
        error = None
        for attempt in range(self.retries + 1):
            self.limiter.wait()
            try:
                request = urllib.request.Request(url, headers={"User-Agent": self.user_agent, "Accept-Encoding": "gzip"})
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    data = response.read()
                    return gzip.decompress(data) if response.headers.get("Content-Encoding") == "gzip" else data
            except Exception as exc:  # noqa: BLE001 - recorded in meta, never silently swallowed
                error = exc
                if attempt < self.retries:
                    time.sleep(1.5)
        raise error


def accession_nodash(accession: str) -> str:
    return accession.replace("-", "")


def archive_url(cik: str, accession: str, filename: str) -> str:
    return f"{ARCHIVES}/{int(cik)}/{accession_nodash(accession)}/{filename}"


def index_url(cik: str, accession: str) -> str:
    return archive_url(cik, accession, f"{accession}-index.htm")


def _rows(record: dict) -> list[dict]:
    count = len(record.get("accessionNumber", []))
    return [{field: (record[field][i] if field in record else None) for field in ROW_FIELDS} for i in range(count)]


def load_submissions(cik: str, submissions_dir) -> dict:
    """Local ``CIK<10>.json`` (+ paged files when present) -> header, rows sorted newest first, paging status."""
    submissions_dir = Path(submissions_dir)
    path = submissions_dir / f"CIK{cik}.json"
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    rows = _rows(data["filings"]["recent"])
    paged = []
    for entry in data["filings"].get("files", []):
        page_path = submissions_dir / entry["name"]
        note = {"name": entry["name"], "found_locally": page_path.exists()}
        if page_path.exists():
            with open(page_path, encoding="utf-8") as handle:
                rows += _rows(json.load(handle))
            note.update({k: entry.get(k) for k in ("filingCount", "filingFrom", "filingTo")})
        paged.append(note)
    rows.sort(key=lambda row: (row["filingDate"] or "", row["acceptanceDateTime"] or ""), reverse=True)
    mtime = to_utc_z(dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc))
    header = {"cik": cik, **{field: data.get(field) for field in HEADER_FIELDS}}
    return {"path": path, "header": header, "rows": rows, "paged_files": paged, "snapshot_mtime_utc": mtime}


def select_filings(rows: list[dict], *, forms=("10-K", "10-Q", "8-K"), n_10k=1, n_10q=2, n_8k=2, eightk_items=("2.02",)) -> list[dict]:
    """Newest N per form; 8-K limited to those carrying one of ``eightk_items`` (None = any 8-K)."""
    limits = {"10-K": n_10k, "10-Q": n_10q, "8-K": n_8k}
    chosen = []
    for form in forms:
        limit = limits.get(form, 1)
        taken = 0
        for row in rows:
            if taken >= limit:
                break
            if row["form"] != form:
                continue
            if form == "8-K" and eightk_items and not set(eightk_items) & set((row.get("items") or "").split(",")):
                continue
            chosen.append(row)
            taken += 1
    return chosen


def local_tenk(accession: str, tenk_cache_dir) -> tuple[dict | None, Path | None]:
    """Manifest entry + gz path when the accession is in the local 10-K cache (manifest keyed by dash-less accession)."""
    tenk_cache_dir = Path(tenk_cache_dir)
    manifest = tenk_cache_dir / "manifest.jsonl"
    if not manifest.exists():
        return None, None
    wanted = accession_nodash(accession)
    with open(manifest, encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if accession_nodash(str(entry.get("accession", ""))) == wanted:
                candidate = tenk_cache_dir / f"{entry.get('ticker')}_{wanted}.txt.gz"
                if not candidate.exists():
                    candidate = next(iter(tenk_cache_dir.glob(f"*_{wanted}.txt.gz")), None)
                return entry, candidate
    return None, None


_TR = re.compile(r"(?is)<tr[^>]*>(.*?)</tr>")
_TD = re.compile(r"(?is)<td[^>]*>(.*?)</td>")
_HREF = re.compile(r'href="([^"]+)"')


def parse_index_attachments(html) -> list[dict]:
    """Rows of an accession ``-index.htm`` page -> [{file, description, type, href}]."""
    text = html.decode("utf-8", errors="replace") if isinstance(html, (bytes, bytearray)) else html
    out = []
    for row in _TR.findall(text):
        cells = _TD.findall(row)
        if len(cells) < 4:
            continue
        href = _HREF.search(cells[2])
        name = os.path.basename(href.group(1)) if href else html_to_text(cells[2])
        out.append({"file": name, "description": html_to_text(cells[1]), "type": html_to_text(cells[3]),
                    "href": href.group(1) if href else None})
    return out


def find_exhibit(attachments: list[dict], exhibit="EX-99.1") -> dict | None:
    for item in attachments:
        kind = (item.get("type") or "").upper()
        if kind.startswith(exhibit) or kind == exhibit.rsplit(".", 1)[0]:
            return item
    return None


def _published(row: dict) -> tuple[str | None, str]:
    stamp = to_utc_z(row.get("acceptanceDateTime"))
    if stamp:
        return stamp, ACCEPTANCE_BASIS
    return row.get("filingDate") or None, FILING_DATE_BASIS


def _doc_meta(row: dict, cik: str, ticker, filename: str, kind: str, tool: str, url: str | None) -> dict:
    published_at, basis = _published(row)
    return {
        "source": "edgar", "tool": tool,
        "params": {"ticker": ticker, "cik": cik, "accession": row["accessionNumber"], "form": row["form"],
                   "document": filename, "url": url, "kind": kind},
        "published_at": published_at, "published_at_basis": basis,
        "filingDate": row.get("filingDate"), "reportDate": row.get("reportDate"), "items": row.get("items"),
        "period": {"reportDate": row.get("reportDate"), "filingDate": row.get("filingDate")},
        "source_url": url,
    }


def _land_text(out_dir: Path, base: str, text: str, max_text_chars) -> tuple[dict, dict]:
    full_chars = len(text)
    kept = text if not max_text_chars or full_chars <= max_text_chars else text[:max_text_chars]
    txt_path = out_dir / f"{base}.txt"
    with open(txt_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(kept)
    text_rec = {"name": txt_path.name, "chars": len(kept), "sha256_full_text": sha256_bytes(text.encode("utf-8")),
                "derivation": TEXT_DERIVATION}
    if len(kept) < full_chars:
        truncated = {"is_truncated": True, "rule": f"derived text cut to first {max_text_chars} chars",
                     "original_chars": full_chars, "kept_chars": len(kept)}
    else:
        truncated = {"is_truncated": False, "original_chars": full_chars}
    return text_rec, truncated


def _land_document(out_dir: Path, base: str, filename: str, raw: bytes, meta: dict, max_text_chars) -> dict:
    ext = (os.path.splitext(filename)[1] or ".htm").lower()
    raw_path = out_dir / f"{base}.raw{ext}"
    raw_rec = {"name": raw_path.name, "bytes": len(raw), "sha256": sha256_bytes(raw), "note": "verbatim EDGAR bytes, not truncated"}
    if len(raw) > GZIP_OVER_BYTES:
        raw_path = raw_path.with_name(raw_path.name + ".gz")
        with gzip.open(raw_path, "wb") as handle:
            handle.write(raw)
        raw_rec.update({"name": raw_path.name, "compressed": "gzip (sha256/bytes refer to the decompressed verbatim EDGAR bytes)",
                        "gz_bytes": raw_path.stat().st_size})
    else:
        raw_path.write_bytes(raw)
    text = html_to_text(raw) if ext in TEXT_EXTS else ""
    text_rec, truncated = _land_text(out_dir, base, text, max_text_chars)
    meta = {**meta, "files": {"raw": raw_rec, "text": text_rec}, "truncated": truncated}
    meta.setdefault("known_gaps", [])
    write_meta(out_dir / f"{base}.txt", **meta)
    return {"base": base, "status": "ok", "raw": raw_path.name, "text": text_rec["name"]}


def _land_error(out_dir: Path, base: str, meta: dict, error: str, gaps=()) -> dict:
    write_meta(out_dir / f"{base}.meta.json", **{**meta, "status": "error", "error": error,
                                               "status_reason": f"fetch failed after retry: {error}",
                                               "known_gaps": list(gaps) + [f"fetch failed after retry: {error}"], "files": None})
    return {"base": base, "status": "error", "error": error}


def _fetch(http_get, url: str):
    try:
        return http_get(url), None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def fetch_filings(cik: str, out_dir, *, forms=("10-K", "10-Q", "8-K"), n_10k=1, n_10q=2, n_8k=2,
                  user_agent: str | None = None, submissions_dir=None, tenk_cache_dir=None, rate: float = 4,
                  ticker: str | None = None, index_slice: int = 40, max_text_chars: int | None = None,
                  eightk_items=("2.02",), http_get=None) -> list[dict]:
    """Land the newest filings of ``cik`` under ``<out_dir>/edgar/``. Returns one summary dict per document."""
    cik = str(cik).zfill(10)
    root = repo_root()
    submissions_dir = Path(submissions_dir or root / "data" / "sec" / "submissions")
    tenk_cache_dir = Path(tenk_cache_dir or root / "data" / "sec" / "10k_text")
    out = Path(out_dir) / "edgar"
    out.mkdir(parents=True, exist_ok=True)
    http_get = http_get or HttpGet(user_agent or os.environ.get("KARST_EDGAR_USER_AGENT", ""), rate=rate)

    index = load_submissions(cik, submissions_dir)
    rows = index["rows"]
    slice_rows = rows[:index_slice]
    index_name = f"CIK{cik}.submissions_slice.json"
    write_json(out / index_name, {**index["header"], "ticker": ticker, "total_filings_local": len(rows),
                                  "slice_rule": f"latest {index_slice} by filingDate desc, acceptanceDateTime desc; fields verbatim from submissions JSON",
                                  "filings": slice_rows})
    write_meta(out / index_name,
               source="edgar", tool="local file data/sec/submissions/CIK<10>.json (+ paged files); EDGAR submissions API snapshot",
               params={"ticker": ticker, "cik": cik, "slice": index_slice, "paged_files": index["paged_files"]},
               local_snapshot_mtime_utc=index["snapshot_mtime_utc"],
               published_at=None, published_at_basis=INDEX_BASIS,
               period={"from": slice_rows[-1]["filingDate"] if slice_rows else None, "to": slice_rows[0]["filingDate"] if slice_rows else None},
               truncated={"is_truncated": len(rows) > len(slice_rows), "rule": f"{len(slice_rows)} of {len(rows)} filings"},
               known_gaps=["items empty string for non-8-K forms as in source", "reportDate empty for some forms as in source",
                           "local snapshot may lag EDGAR by days (see local_snapshot_mtime_utc)"]
                          + [f"paged index file {p['name']} not held locally" for p in index["paged_files"] if not p["found_locally"]],
               status="ok" if rows else "empty", source_url=f"https://data.sec.gov/submissions/CIK{cik}.json")

    results = []
    for row in select_filings(rows, forms=forms, n_10k=n_10k, n_10q=n_10q, n_8k=n_8k, eightk_items=eightk_items):
        accession, form, primary = row["accessionNumber"], row["form"], row["primaryDocument"]
        base = f"{accession}.{form}"
        if form == "10-K":
            entry, gz_path = local_tenk(accession, tenk_cache_dir)
            check = {"manifest": str(tenk_cache_dir / "manifest.jsonl"), "hit": bool(entry), "hit_accession": entry and entry.get("accession")}
            if entry and gz_path:
                with gzip.open(gz_path, "rt", encoding="utf-8") as handle:
                    text = handle.read()
                text_rec, truncated = _land_text(out, base, text, max_text_chars)
                meta = _doc_meta(row, cik, ticker, primary, "primary", "local data/sec/10k_text (D-134 single copy)", entry.get("url"))
                meta["params"]["gz"] = gz_path.name
                write_meta(out / f"{base}.txt", **meta, files={"raw": None, "text": text_rec}, truncated=truncated,
                           known_gaps=["raw HTML not held locally (only derived text); fetch by accession from EDGAR if raw needed"],
                           local_cache_check=check)
                results.append({"base": base, "status": "ok", "raw": None, "text": text_rec["name"], "local_cache": True})
                continue
            extra = {"local_cache_check": check,
                     "known_gaps": ["local 10k_text manifest has no entry for this accession; fetched from EDGAR online instead"]}
        else:
            extra = {}
        url = archive_url(cik, accession, primary)
        meta = {**_doc_meta(row, cik, ticker, primary, "primary", f"EDGAR Archives HTTP GET (User-Agent set; <={rate} req/s; retry once)", url), **extra}
        if form == "8-K":
            idx = index_url(cik, accession)
            page, err = _fetch(http_get, idx)
            attachments = parse_index_attachments(page) if page is not None else None
            meta.update({"index_page": idx, "attachments_listed": attachments})
            if attachments is None:
                meta["known_gaps"] = meta.get("known_gaps", []) + [f"index page fetch failed: {err}"]
        raw, err = _fetch(http_get, url)
        results.append(_land_document(out, base, primary, raw, meta, max_text_chars) if raw is not None
                       else _land_error(out, base, meta, err, meta.get("known_gaps", [])))
        if form != "8-K":
            continue
        ex_base = f"{base}.EX-99.1"
        ex_meta_common = {"index_page": meta["index_page"], "attachments_listed": attachments}
        if attachments is None:
            results.append(_land_error(out, ex_base, {**_doc_meta(row, cik, ticker, None, "exhibit", "EDGAR index page", meta["index_page"]), **ex_meta_common},
                                       f"index page fetch failed: {err}"))
            continue
        exhibit = find_exhibit(attachments)
        if exhibit is None:
            write_meta(out / f"{ex_base}.meta.json", **_doc_meta(row, cik, ticker, None, "exhibit", "EDGAR index page", meta["index_page"]),
                       **ex_meta_common, status="empty", status_reason="no EX-99.1 exhibit listed on this filing's index page",
                       known_gaps=["no EX-99.1 exhibit listed on index page"])
            results.append({"base": ex_base, "status": "empty"})
            continue
        ex_url = archive_url(cik, accession, exhibit["file"])
        ex_meta = {**_doc_meta(row, cik, ticker, exhibit["file"], "exhibit", meta["tool"], ex_url),
                   "exhibit_type": exhibit["type"], "exhibit_description": exhibit["description"], "index_page": meta["index_page"]}
        raw, err = _fetch(http_get, ex_url)
        results.append(_land_document(out, ex_base, exhibit["file"], raw, ex_meta, max_text_chars) if raw is not None
                       else _land_error(out, ex_base, ex_meta, err))
    return results


def kind_for(meta) -> str:
    """A filing document (primary or exhibit) or the submissions index slice."""
    params = meta.get("params") or {}
    return "filing" if (params.get("document") or params.get("kind") in ("primary", "exhibit")) \
        else "filing_index"


def fetch(security, out_dir, *, since=None, client=None) -> list[LandedRecord]:
    """Land this security's newest filings. ``client`` is an HTTP getter (tests pass an offline map).

    ``since`` is not a filter here: the selection is "the newest N of each form",
    which is what a research packet needs; a date window would silently drop the
    last 10-K when nothing was filed inside it.
    """
    fetch_filings(cik_for(security), out_dir, ticker=security.get("ticker"),
                  **options_for(client, "http_get"))
    return scan(Path(out_dir) / SOURCE, kind_for)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Land newest EDGAR filings for one CIK/ticker under <out>/edgar/.")
    who = parser.add_mutually_exclusive_group(required=True)
    who.add_argument("--ticker")
    who.add_argument("--cik")
    parser.add_argument("--out", required=True)
    parser.add_argument("--forms", default="10-K,10-Q,8-K")
    parser.add_argument("--n-10k", type=int, default=1)
    parser.add_argument("--n-10q", type=int, default=2)
    parser.add_argument("--n-8k", type=int, default=2)
    parser.add_argument("--eightk-items", default="2.02", help="comma list; empty = any 8-K")
    parser.add_argument("--user-agent", default=os.environ.get("KARST_EDGAR_USER_AGENT", ""))
    parser.add_argument("--submissions-dir")
    parser.add_argument("--tenk-cache-dir")
    parser.add_argument("--tickers-json", default=str(repo_root() / "data" / "sec" / "company_tickers.json"))
    parser.add_argument("--rate", type=float, default=4)
    parser.add_argument("--index-slice", type=int, default=40)
    parser.add_argument("--max-text-chars", type=int, default=None)
    args = parser.parse_args(argv)
    cik = args.cik or ticker_to_cik(args.ticker, args.tickers_json)
    results = fetch_filings(cik, args.out, forms=tuple(f for f in args.forms.split(",") if f), n_10k=args.n_10k, n_10q=args.n_10q,
                            n_8k=args.n_8k, user_agent=args.user_agent, submissions_dir=args.submissions_dir,
                            tenk_cache_dir=args.tenk_cache_dir, rate=args.rate, ticker=args.ticker, index_slice=args.index_slice,
                            max_text_chars=args.max_text_chars, eightk_items=tuple(i for i in args.eightk_items.split(",") if i) or None)
    json.dump(results, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")
    return 0 if all(r["status"] != "error" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
