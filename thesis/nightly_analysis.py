"""Nightly analysis guard + headless-Claude dispatcher (runs after the 05:30 HKT fetch batch).

Checks whether there is anything NEW to analyse (unticked transcripts inbox items, gooptions
manifest count > last-ingested count, OR a magnifier node newly flagged stale). If nothing:
exits without spending any model quota. If something: invokes headless Claude (all-opus — the
material is short, a delegation layer is not worth its overhead) with edit-only permissions +
python-only bash, per thesis/nightly_analysis_prompt.md.

Magnifier check (added 2026-07-12): runs thesis/magnifier_staleness.py's own dedup'd check
daily (cheap -- DB/JSON reads only) rather than on a separate weekly schedule, so a same-day
article or transcript touching a magnifier node's tickers gets queued for rescoring same-day,
not up to a week later. It writes any new flags to thesis/.raw/magnifier_review_queue.md itself
(see that module) -- this guard only reads back how many it wrote to decide whether to spend
headless-Claude quota this run.

    python thesis/nightly_analysis.py [--dry-run]
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime

KARST = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(KARST, "..", "Reference", "raw_data",
                     "backtest_everything_transcripts", "_PENDING_ANALYSIS.md")
MANIFEST = os.path.join(KARST, "thesis", ".raw", "gooptions", "research-manifest.json")
STATE = os.path.join(KARST, "thesis", ".raw", "gooptions", ".last_ingested_count")
PROMPT = os.path.join(KARST, "thesis", "nightly_analysis_prompt.md")
LOG = os.path.join(KARST, "thesis", ".raw", "nightly_analysis.log")

sys.path.insert(0, os.path.join(KARST, "thesis"))


def pending_transcripts() -> int:
    if not os.path.exists(INBOX):
        return 0
    text = open(INBOX, encoding="utf-8").read()
    return len(re.findall(r"^- \[ \]", text, re.M))


def manifest_count() -> int:
    try:
        data = json.load(open(MANIFEST, encoding="utf-8"))
        items = data.get("items", data) if isinstance(data, dict) else data
        return len(items)
    except Exception:
        return 0


def pending_gooptions() -> int:
    n = manifest_count()
    if not os.path.exists(STATE):
        # First run: assume caught up as of deployment (everything to date was ingested).
        with open(STATE, "w") as f:
            f.write(str(n))
        return 0
    last = int(open(STATE).read().strip() or 0)
    return max(0, n - last)


def pending_magnifier() -> int:
    """Runs magnifier_staleness's own dedup'd check (cheap -- corpus.db + manifest reads only).
    Any newly-stale node is written to thesis/.raw/magnifier_review_queue.md as a side effect;
    this just returns how many so main() can decide whether to spend headless-Claude quota."""
    try:
        import magnifier_staleness
        return len(magnifier_staleness.run() or [])
    except Exception as e:
        print(f"[nightly_analysis] magnifier_staleness check failed (non-fatal): {e}")
        return 0


# 2026-07-12 (user call): magnifier staleness check still runs nightly (free -- corpus.db/
# manifest reads only, no model spend) and still queues findings for whenever a session picks
# them up, but does NOT by itself wake up headless Claude overnight (unsupervised token spend
# while asleep). Flip to True once comfortable with the queue's signal/noise.
MAGNIFIER_TRIGGERS_HEADLESS_RUN = False


def main():
    stamp = f"{datetime.now():%Y-%m-%d %H:%M}"
    nt, ng, nm = pending_transcripts(), pending_gooptions(), pending_magnifier()
    line = f"==== {stamp} ==== pending: transcripts={nt} gooptions={ng} magnifier={nm}" \
           f"{'' if MAGNIFIER_TRIGGERS_HEADLESS_RUN else ' (magnifier logged only, not triggering)'}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    nm_trigger = nm if MAGNIFIER_TRIGGERS_HEADLESS_RUN else 0
    if nt == 0 and ng == 0 and nm_trigger == 0:
        print("nothing to analyse -> no model spend")
        return
    if "--dry-run" in sys.argv:
        print("dry-run: would invoke headless claude (opus)")
        return
    cmd = ('claude -p --model opus --permission-mode acceptEdits '
           '--allowedTools "Bash(python:*)"')
    with open(PROMPT, encoding="utf-8") as pf:
        res = subprocess.run(cmd, stdin=pf, capture_output=True, text=True,
                             shell=True, cwd=KARST, timeout=5400,
                             encoding="utf-8", errors="replace")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write((res.stdout or "") + "\n")
        if res.returncode != 0:
            f.write(f"[stderr rc={res.returncode}]\n{res.stderr}\n")
    print(f"analysis run finished rc={res.returncode}; log: {LOG}")


if __name__ == "__main__":
    main()
