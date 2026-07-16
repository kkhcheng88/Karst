"""thesis/zsxq_pull.py -- headless puller for the zsxq KOL channel (社会观察从业者).

WHY: the 2026-07-16/17 backfill was scraped through the user's logged-in browser, which needs
a human at the keyboard. Nightshift tracking needs a cookie-authenticated API path instead.
Canonical record of what this channel is and why we track it:
thesis/.raw/zsxq/INDEX.md + PDF_TRIAGE.md.

CREDENTIAL: ~/.config/karst/zsxq_cookie -- one line, the raw Cookie header value copied from a
logged-in browser session (same convention as ~/.config/karst/telegram). Never committed, never
echoed. Absent file = clean skip, never a crash: nightshift must not fail because a cookie expired.

Run: PYTHONUTF8=1 python thesis/zsxq_pull.py [--since YYYY-MM-DD] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
COOKIE_PATH = os.path.expanduser("~/.config/karst/zsxq_cookie")
OUT_DIR = os.path.join(ROOT, ".raw", "zsxq")
STATE_PATH = os.path.join(OUT_DIR, ".pull_state.json")
PDF_DIR = os.path.join(OUT_DIR, "pdf")

GROUP_ID = "51115542524144"
API_BASE = "https://api.zsxq.com/v2"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def read_cookie() -> str | None:
    """Cookie from the credential file. Missing/empty -> None (caller skips cleanly)."""
    try:
        with open(COOKIE_PATH, encoding="utf-8") as fh:
            val = fh.read().strip()
        return val or None
    except OSError:
        return None


def api_get(path: str, cookie: str, params: dict | None = None) -> dict:
    url = f"{API_BASE}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Cookie": cookie,
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Referer": f"https://wx.zsxq.com/group/{GROUP_ID}",
    })
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_topics(cookie: str, since: datetime, max_pages: int = 40) -> list[dict]:
    """Walk the group's topic feed newest->oldest until `since`. Returns raw topic dicts."""
    out, end_time, pages = [], None, 0
    while pages < max_pages:
        params = {"scope": "all", "count": 20}
        if end_time:
            params["end_time"] = end_time
        try:
            data = api_get(f"groups/{GROUP_ID}/topics", cookie, params)
        except urllib.error.HTTPError as e:
            # 401/403 = cookie expired. Say so once, plainly; don't retry into a rate-limit.
            print(f"HTTP {e.code} from zsxq API -- cookie likely expired; refresh "
                  f"{COOKIE_PATH} from a logged-in browser session.")
            break
        if not data.get("succeeded"):
            print(f"API returned succeeded=false: {str(data)[:200]}")
            break
        topics = data.get("resp_data", {}).get("topics", [])
        if not topics:
            break
        for t in topics:
            ts = t.get("create_time", "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                continue
            if dt < since:
                return out
            out.append(t)
        end_time = topics[-1].get("create_time")
        pages += 1
        time.sleep(1.5)  # be a polite client; this is the user's paid subscription
    return out


def topic_to_md(t: dict) -> str:
    """One topic -> markdown block. Keeps text verbatim; records file attachments by name."""
    ts = t.get("create_time", "")[:19].replace("T", " ")
    talk = t.get("talk") or {}
    text = talk.get("text") or t.get("question", {}).get("text") or ""
    owner = (talk.get("owner") or {}).get("name", "")
    lines = [f"## {ts}  {('— ' + owner) if owner else ''}".rstrip(), ""]
    lines.append(text.strip() or "(無文字內容)")
    files = talk.get("files") or []
    if files:
        lines.append("")
        lines.append("**附件**:")
        for f in files:
            lines.append(f"- {f.get('name', '?')} ({f.get('size', '?')} bytes, file_id={f.get('file_id')})")
    imgs = talk.get("images") or []
    if imgs:
        lines.append(f"\n_(附 {len(imgs)} 張圖,未下載)_")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="YYYY-MM-DD; default = last pull, else 7 days back")
    ap.add_argument("--dry-run", action="store_true", help="fetch + report, write nothing")
    args = ap.parse_args()

    cookie = read_cookie()
    if not cookie:
        # Clean skip, exit 0: a missing cookie is a not-configured state, not a failure.
        print(f"zsxq: no cookie at {COOKIE_PATH} -- skipping (see module docstring to set up).")
        return 0

    if args.since:
        since = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
    else:
        last = None
        try:
            with open(STATE_PATH, encoding="utf-8") as fh:
                last = json.load(fh).get("last_pull")
        except OSError:
            pass
        since = (datetime.fromisoformat(last) if last
                 else datetime.now(timezone.utc) - timedelta(days=7))

    print(f"zsxq: pulling topics since {since.date()} ...")
    topics = fetch_topics(cookie, since)
    print(f"zsxq: got {len(topics)} topics")
    if not topics or args.dry_run:
        if args.dry_run and topics:
            print(topic_to_md(topics[0])[:400])
        return 0

    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = os.path.join(OUT_DIR, f"{stamp}_pull.md")
    header = (f"# zsxq 自動拉取 — {stamp}\n\n"
              f"> 來源:知識星球 group {GROUP_ID}(社会观察从业者,用戶付費訂閱)。\n"
              f"> 由 thesis/zsxq_pull.py 拉取,範圍 {since.date()} 起,共 {len(topics)} 帖。\n"
              f"> 背景/慣例見 thesis/.raw/zsxq/INDEX.md。\n\n---\n\n")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(header)
        for t in reversed(topics):  # oldest -> newest, reading order
            fh.write(topic_to_md(t))
            fh.write("\n")
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump({"last_pull": datetime.now(timezone.utc).isoformat()}, fh)
    print(f"zsxq: wrote {out_path}")

    n_files = sum(len((t.get('talk') or {}).get('files') or []) for t in topics)
    if n_files:
        print(f"zsxq: {n_files} file attachment(s) seen -- names recorded, not downloaded "
              f"(PDF download stays manual; see thesis/.raw/zsxq/PDF_TRIAGE.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
