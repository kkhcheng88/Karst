"""Append the current thesis-bearing predictions to thesis/track_record.jsonl (the AGENT's log).

NHITL: the system logs its OWN predictions (not a human diary). Runs the spine scan, and for every
tier-2 card that carries a real thesis (source "thesis:*"), appends one structured record with the
confidence/cycle_stage/prediction/kill/entry-context and outcome=null. Outcomes are back-filled
later (a separate step, once the horizon elapses) so the system can calibrate confidence + compute
forward-IC / expectancy / decay (DESIGN §6). Dedups by (ts, ticker, thesis_id).

Run: python thesis/log_predictions.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.spine.orchestrator import run_daily  # noqa: E402

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "track_record.jsonl")
HORIZON = 63


def _existing():
    seen = set()
    if os.path.exists(LOG):
        with open(LOG, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    seen.add((r.get("ts"), r.get("ticker"), r.get("thesis_id")))
                except Exception:
                    continue
    return seen


def run():
    mc, _rot, _sec, cards = run_daily()
    seen = _existing()
    added = 0
    with open(LOG, "a", encoding="utf-8") as fh:
        for c in cards:
            th = c.thesis or {}
            src = str(th.get("source", ""))
            if not src.startswith("thesis:"):
                continue                      # only log real thesis predictions
            thesis_id = src.split(":", 1)[1]
            key = (c.asof, c.ticker, thesis_id)
            if key in seen:
                continue
            rec = {
                "ts": c.asof,
                "thesis_id": thesis_id,
                "ticker": c.ticker,
                "confidence": th.get("confidence"),
                "cycle_stage": th.get("cycle_stage"),
                "prediction": {"horizon_days": HORIZON, "direction": "long",
                               "action": c.expression.get("action"), "size_hint": c.score},
                "kill_condition": th.get("kill_condition"),
                "entry_ctx": {"sector_temp": c.sector_temp, "market_gate": mc.gate_label,
                              "drivers": c.drivers},
                "outcome": None,
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            added += 1
    print(f"logged {added} new thesis prediction(s) to {os.path.relpath(LOG)} "
          f"(total keys seen before: {len(seen)})")


if __name__ == "__main__":
    run()
