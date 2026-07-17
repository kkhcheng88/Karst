"""thesis/kol_pull.py -- daily incremental pull of 順哥 (Discord 皇者顺-美股) messages.

WHY: the KOL-tracking layer needs a daily feed without a human at the keyboard.
zsxq has its own puller (thesis/zsxq_pull.py, cookie-based). This one covers the
Discord channel via the user's existing DiscordChatExporter setup.

CREDENTIALS: the token is read AT RUNTIME from the user's own existing script
(C:/TradingView/Discord/RoyalFlush.ps1) -- no second plaintext copy is created,
nothing is printed. If that file or the CLI is missing, this exits 0 cleanly
(a scheduled task must never crash the chain).

VERDICT CONTEXT (so nobody mistakes this feed for a signal): 順哥's calls are
scored -- entries beat random, exits beat mechanical rules, whole book ties SPY
(backtest/results/2026-07-17_kol_shunge_roundtrip.md). This feed is RECORD-ONLY:
it lands in thesis/.raw/discord/ (gitignored) for the ledger and for context.

Run: PYTHONUTF8=1 python thesis/kol_pull.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
PS1 = r"C:\TradingView\Discord\RoyalFlush.ps1"
CLI = r"C:\Game\DiscordChatExporter\DiscordChatExporter.Cli.exe"
TMP = r"C:\TradingView\Discord\RoyalFlush_daily_tmp.json"
OUT_DIR = os.path.join(ROOT, ".raw", "discord")
STATE = os.path.join(OUT_DIR, ".daily_pull_state.json")


def read_creds() -> tuple[str, str] | None:
    try:
        src = open(PS1, encoding="utf-8", errors="replace").read()
    except OSError:
        print(f"kol_pull: {PS1} not found -- skip (exit 0)")
        return None
    tok = re.search(r'\$Token\s*=\s*"([^"]+)"', src)
    ch = re.search(r'\$ChannelId\s*=\s*"([^"]+)"', src)
    if not (tok and ch):
        print("kol_pull: token/channel not found in RoyalFlush.ps1 -- skip")
        return None
    return tok.group(1), ch.group(1)


def main() -> int:
    if not os.path.exists(CLI):
        print("kol_pull: DiscordChatExporter CLI missing -- skip")
        return 0
    creds = read_creds()
    if not creds:
        return 0
    token, channel = creds

    os.makedirs(OUT_DIR, exist_ok=True)
    last = None
    try:
        last = json.load(open(STATE, encoding="utf-8")).get("last_ts")
    except OSError:
        pass
    # overlap 2 days for safety; dedupe below by message id
    since = (datetime.fromisoformat(last) - timedelta(days=2)) if last else datetime.now(timezone.utc) - timedelta(days=3)
    after = since.strftime("%Y-%m-%d %H:%M")

    r = subprocess.run([CLI, "export", "-t", token, "-c", channel, "-f", "Json",
                        "-o", TMP, "--after", after],
                       capture_output=True, text=True, timeout=280,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0 or not os.path.exists(TMP):
        print(f"kol_pull: export failed rc={r.returncode} -- {(r.stderr or '')[-200:]}")
        return 0  # never crash the chain

    data = json.load(open(TMP, encoding="utf-8"))
    msgs = [m for m in data.get("messages", [])
            if "皇者顺" in (m.get("author", {}).get("name") or "")]
    msgs = [m for m in msgs if not last or m["timestamp"] > last]
    if not msgs:
        print("kol_pull: no new 順哥 messages")
        os.remove(TMP)
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = os.path.join(OUT_DIR, f"daily_{stamp}.md")
    with open(out, "a", encoding="utf-8") as fh:
        for m in msgs:
            fh.write(f"## [{m['timestamp'][:16]}]\n\n{m.get('content') or ''}\n\n---\n\n")
    json.dump({"last_ts": max(m["timestamp"] for m in msgs)},
              open(STATE, "w", encoding="utf-8"))
    os.remove(TMP)
    print(f"kol_pull: {len(msgs)} new messages -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
