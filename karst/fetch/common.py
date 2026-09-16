"""Shared pieces for the source adapters: meta writer, UTC time, hashing, rate limit, HTML to text."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import re
import time
from decimal import Decimal
from html import unescape
from pathlib import Path

META_ORDER = (
    "source", "tool", "params", "fetched_at", "published_at", "published_at_basis",
    "period", "truncated", "known_gaps", "status", "source_url",
)
STATUSES = ("ok", "empty", "error")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_env_file(path=None, environ=None) -> list[str]:
    """Load ``KEY=VALUE`` lines from a ``.env`` into the environment; returns the keys set.

    Credentials live in the repo-root ``.env`` (gitignored), not in the system
    environment. A missing file is not an error, blank/``#`` lines are skipped, and
    an already-set environment variable always wins over the file.
    """
    environ = os.environ if environ is None else environ
    path = Path(path) if path else repo_root() / ".env"
    if not path.is_file():
        return []
    loaded = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        if key and not environ.get(key):
            environ[key] = value
            loaded.append(key)
    return loaded


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_utc_z(value):
    """Offset-aware datetime or ISO string -> ``...Z`` UTC string.

    Date-only strings are returned unchanged (never invent a time of day).
    Naive datetimes / offset-less timestamps return None: the caller must record
    the basis instead of guessing a zone.
    """
    if value is None or value == "":
        return None
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            return None
        return _fmt(value.astimezone(dt.timezone.utc))
    if isinstance(value, dt.date):
        return value.isoformat()
    text = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    try:
        parsed = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return _fmt(parsed.astimezone(dt.timezone.utc))


def _fmt(value: dt.datetime) -> str:
    base = value.strftime("%Y-%m-%dT%H:%M:%S")
    if value.microsecond:
        base += f".{value.microsecond // 1000:03d}"
    return base + "Z"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path, **extra) -> dict:
    path = Path(path)
    return {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path), **extra}


def meta_path_for(path: Path) -> Path:
    path = Path(path)
    if path.name.endswith(".meta.json"):
        return path
    return path.with_suffix(".meta.json")


def write_meta(path, **fields) -> Path:
    """Write ``<path>.meta.json`` next to a landed file (or at ``path`` itself when it ends with .meta.json).

    Fixed key order (META_ORDER first, then extras in call order), ``fetched_at``
    defaults to now (UTC Z), ``status`` to ``ok``, ``source_url`` to None. When
    ``path`` is a data file and no ``file`` field was given, its bytes and
    sha256 are recorded under ``file``.
    """
    path = Path(path)
    target = meta_path_for(path)
    fields.setdefault("fetched_at", utc_now())
    fields.setdefault("status", "ok")
    fields.setdefault("source_url", None)
    fields.setdefault("published_at", None)
    fields.setdefault("published_at_basis", None)
    fields.setdefault("period", None)
    fields.setdefault("truncated", {"is_truncated": False})
    fields.setdefault("known_gaps", [])
    if fields["status"] not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}: {fields['status']!r}")
    if target != path and path.exists() and "file" not in fields and "files" not in fields:
        fields["file"] = file_record(path)
    ordered = {key: fields[key] for key in META_ORDER if key in fields}
    ordered.update({key: value for key, value in fields.items() if key not in ordered})
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(ordered, handle, ensure_ascii=False, indent=2, default=str)
        handle.write("\n")
    return target


def write_json(path, payload) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1, default=str)
        handle.write("\n")
    return path


class RateLimiter:
    """Blocking limiter: at most ``per_second`` calls per second (process-local)."""

    def __init__(self, per_second: float):
        self.interval = 1.0 / per_second if per_second and per_second > 0 else 0.0
        self._last = 0.0

    def wait(self) -> None:
        pause = self.interval - (time.monotonic() - self._last)
        if pause > 0:
            time.sleep(pause)
        self._last = time.monotonic()


_TAG_BLOCKS = re.compile(r"(?is)<(script|style)[^>]*>.*?</\1>")
_COMMENTS = re.compile(r"(?s)<!--.*?-->")
_BR = re.compile(r"(?i)<br\s*/?>")
_BLOCK_END = re.compile(r"(?i)</(p|div|tr|li|h[1-6]|table|section)>")
_CELL_END = re.compile(r"(?i)</t[dh]>")
_TAGS = re.compile(r"(?s)<[^>]+>")


def html_to_text(html) -> str:
    """Strip script/style/comments/tags, unescape entities, collapse whitespace (block ends -> newline, cells -> tab)."""
    text = html.decode("utf-8", errors="replace") if isinstance(html, (bytes, bytearray)) else str(html)
    text = _TAG_BLOCKS.sub(" ", text)
    text = _COMMENTS.sub(" ", text)
    text = _BR.sub("\n", text)
    text = _BLOCK_END.sub("\n", text)
    text = _CELL_END.sub("\t", text)
    text = _TAGS.sub(" ", text)
    text = unescape(text).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def ticker_to_cik(ticker: str, tickers_json_path) -> str:
    """Resolve a ticker to a 10-digit CIK from the local ticker map (flat ``{ticker: cik}`` or EDGAR's numbered rows)."""
    with open(tickers_json_path, encoding="utf-8") as handle:
        table = json.load(handle)
    wanted = ticker.upper()
    if isinstance(table, dict) and all(isinstance(v, str) for v in table.values()):
        hit = table.get(wanted)
    else:
        rows = table.values() if isinstance(table, dict) else table
        hit = next((row.get("cik_str") for row in rows if str(row.get("ticker", "")).upper() == wanted), None)
    if hit is None:
        raise KeyError(f"ticker {ticker!r} not in {tickers_json_path}")
    return str(hit).zfill(10)


def clean_value(value):
    """JSON-safe scalar/container: NaN -> None, Timestamp/date -> ISO, Decimal -> str (exact), numpy scalars -> python."""
    if value is None:
        return None
    if hasattr(value, "item") and not isinstance(value, (str, bytes, dict, list, tuple)):
        try:
            value = value.item()
        except (ValueError, TypeError, AttributeError):
            pass
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [clean_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): clean_value(item) for key, item in value.items()}
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def frame_records(frame) -> list[dict]:
    """pandas DataFrame (duck-typed) -> list of cleaned row dicts; None/empty -> []."""
    if frame is None:
        return []
    if isinstance(frame, list):
        return [clean_value(row) for row in frame]
    if isinstance(frame, dict):
        return [clean_value(frame)]
    if not hasattr(frame, "to_dict"):
        return [clean_value(frame)]
    return [{str(key): clean_value(item) for key, item in row.items()} for row in frame.to_dict(orient="records")]
