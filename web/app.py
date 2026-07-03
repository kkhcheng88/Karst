"""Karst dashboard — the SERVE half (thin, read-only).

Reads web/data/latest.json (written by run_scan.py) and renders it. Never computes
inline, so a slow/failing scan never blocks the page. Routes:

    GET /            -> rendered Phase 0->4 dashboard (HTML)
    GET /api/scan    -> raw scan JSON
    GET /healthz     -> liveness probe (no auth)

Auth: if KARST_TOKEN is set, every route except /healthz requires it via
`?token=...` (once, then a cookie is set) or `Authorization: Bearer <token>`.
Unset -> open (a warning is logged); fine only behind a private network.

Optional in-process daily refresh: set KARST_INPROC_CRON=1 to have this process run
the scan itself (single-service Zeabur deploy). Prefer a separate cron/Zeabur-Cron
in production; then leave it unset and serve-only.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

from flask import Flask, Response, request

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(_HERE, "data")
_LATEST = os.path.join(_DATA, "latest.json")
sys.path.insert(0, _HERE)

import render as render_mod  # noqa: E402

app = Flask(__name__)
log = logging.getLogger("karst.web")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

_TOKEN = os.getenv("KARST_TOKEN", "").strip()
_REFRESH_HOUR = int(os.getenv("KARST_REFRESH_HOUR", "9"))   # local server hour to run the scan
if not _TOKEN:
    log.warning("KARST_TOKEN unset -> dashboard is OPEN. Set it before exposing publicly.")


def _authed() -> bool:
    if not _TOKEN:
        return True
    tok = (request.args.get("token")
           or request.cookies.get("karst_token")
           or (request.headers.get("Authorization", "").removeprefix("Bearer ").strip()))
    return tok == _TOKEN


def _guard():
    """Return None if allowed, else a 401 Response."""
    if _authed():
        return None
    return Response("unauthorized — append ?token=YOUR_TOKEN", status=401,
                    mimetype="text/plain")


def _load_payload() -> dict | None:
    try:
        with open(_LATEST, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:  # corrupt/partial -> treat as missing
        log.error("failed reading latest.json: %s", e)
        return None


@app.get("/healthz")
def healthz():
    p = _load_payload()
    ok = p is not None
    body = {"ok": ok, "generated_at": (p or {}).get("generated_at"),
            "asof": ((p or {}).get("market") or {}).get("asof")}
    return Response(json.dumps(body), status=200 if ok else 503, mimetype="application/json")


@app.get("/")
def index():
    if (r := _guard()) is not None:
        return r
    p = _load_payload()
    html = (render_mod.render(p) if p is not None
            else render_mod.render_error("No scan yet. The first scan has not run."))
    resp = Response(html, mimetype="text/html")
    if _TOKEN and request.args.get("token") == _TOKEN:
        resp.set_cookie("karst_token", _TOKEN, max_age=90 * 86400, httponly=True, samesite="Lax")
    return resp


@app.get("/api/scan")
def api_scan():
    if (r := _guard()) is not None:
        return r
    p = _load_payload()
    if p is None:
        return Response(json.dumps({"error": "no scan yet"}), status=503,
                        mimetype="application/json")
    return Response(json.dumps(p, default=str, ensure_ascii=False), mimetype="application/json")


def _seconds_until(hour: int) -> float:
    now = datetime.now(timezone.utc).astimezone()   # local tz
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def _refresh_loop():
    import run_scan
    # cold start: if there is no scan at all, compute one immediately
    if _load_payload() is None:
        try:
            log.info("cold start: no latest.json, running first scan ...")
            run_scan.main()
        except Exception as e:
            log.error("initial scan failed: %s", e)
    while True:
        try:
            time.sleep(_seconds_until(_REFRESH_HOUR))
            log.info("scheduled refresh: running scan ...")
            run_scan.main()
        except Exception as e:
            log.error("scheduled scan failed: %s", e)
            time.sleep(3600)   # back off an hour, then retry the wait loop


def _maybe_start_scheduler():
    if os.getenv("KARST_INPROC_CRON", "").strip() in {"1", "true", "yes"}:
        log.info("in-process scheduler ON (daily refresh at %02d:00 local)", _REFRESH_HOUR)
        threading.Thread(target=_refresh_loop, daemon=True).start()


_maybe_start_scheduler()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
