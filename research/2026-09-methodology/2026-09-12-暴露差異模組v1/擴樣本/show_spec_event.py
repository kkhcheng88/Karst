# -*- coding: utf-8 -*-
"""列出擴樣本 spec 的逐宗欄位(寫卡前核敘事、籃子定義、出處與備註)。用法:`python show_spec_event.py E22`"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    want = sys.argv[1:] or [f"E{i}" for i in range(21, 28)]
    spec = json.loads((HERE / "new_events_spec_oos.json").read_text(encoding="utf-8"))
    for e in spec["events"]:
        if e["event_id"] not in want:
            continue
        print(f"\n{'=' * 76}\n## {e['event_id']} {e['name']} [{e['event_type']}] "
              f"{e['shock_start']} → {e['news_shock_end']}")
        print(f"敘事: {e['narrative']}")
        print(f"籃子: {e['basket_definition']}")
        print(f"來源: {e['basket_source']}")
        print(f"A 名單({len(e['tickers'])}): {', '.join(e['tickers'])}")
        print(f"B 名單({len(e.get('tickers_headline_only', []))}): {', '.join(e.get('tickers_headline_only', []))}")
        print(f"同 SIC 對照: {e.get('sic2_basket')}")
        print(f"備註: {e.get('notes', '')}")
        for s in e["sources"]:
            print(f"  - [{s.get('verified', '')}] {s.get('outlet', '')} {s.get('date', '')} {s.get('url', '')}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
