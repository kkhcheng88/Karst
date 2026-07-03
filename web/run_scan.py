"""Cron target: run the daily Karst scan and write a machine-readable artifact.

This is the COMPUTE half of the dashboard (compute/serve are kept separate so a slow
or failing scan never blocks the web server). It writes:

    web/data/latest.json          -- the newest scan (what the dashboard renders)
    web/data/scan-YYYY-MM-DD.json -- a dated snapshot (history; cheap, ~50KB each)

Run it from cron / Zeabur Cron / Windows Task Scheduler:

    python web/run_scan.py

On a headless VPS set KARST_DATA_SOURCE=defeatbeta first (Yahoo throttles datacenter
IPs); see backtest/data.py. Writes are atomic (temp file + os.replace) so the web
server never reads a half-written file.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_DATA = os.path.join(_HERE, "data")
sys.path.insert(0, _ROOT)                    # so `import backtest` resolves
sys.path.insert(0, os.path.join(_ROOT, "backtest"))  # so orchestrator's `import data` resolves
sys.path.insert(0, _HERE)                    # so `import market_score` (web/) resolves for any caller


def build_payload(universe: str | None = None) -> dict:
    from backtest.spine import card as card_mod
    from backtest.spine import orchestrator
    mc, rot, sec_ctx, cards = orchestrator.run_daily(universe)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "market": asdict(mc),
        "rotation": asdict(rot) if rot else None,
        "sectors": {k: asdict(v) for k, v in sec_ctx.items()},
        "cards": [card_mod.to_dict(c) for c in cards],
    }
    try:                     # composite risk-on score (magnitude + trend + factor breakdown)
        import market_score
        payload["market_score"] = market_score.compute()
    except Exception as e:   # never let the score composite break the scan
        print(f"[run_scan] market_score failed: {e}")
        payload["market_score"] = None
    return payload


def _atomic_write(path: str, text: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def main(universe: str | None = None) -> str:
    os.makedirs(_DATA, exist_ok=True)
    payload = build_payload(universe)
    text = json.dumps(payload, indent=2, default=str, ensure_ascii=False)
    _atomic_write(os.path.join(_DATA, "latest.json"), text)
    asof = str(payload.get("market", {}).get("asof", "unknown"))
    _atomic_write(os.path.join(_DATA, f"scan-{asof}.json"), text)
    print(f"[run_scan] wrote latest.json + scan-{asof}.json "
          f"({len(payload['cards'])} cards, gate={payload['market'].get('gate')})")
    return asof


if __name__ == "__main__":
    uni = sys.argv[1] if len(sys.argv) > 1 else None
    main(uni)
