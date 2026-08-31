#!/usr/bin/env python3
"""Probe helper: summarise get_valuation_plate_stock_list --json dumps."""
import json
import sys


def load(path):
    s = open(path, encoding="utf-8").read()
    i = s.index("{")
    obj, _ = json.JSONDecoder().raw_decode(s[i:])
    return obj


def main(path, sample=12):
    obj = load(path)
    print("== %s" % path)
    if obj.get("error"):
        print("   ERROR:", obj.get("error"))
        return
    print("   top keys:", list(obj.keys()))
    data = obj.get("data", obj)
    if isinstance(data, dict):
        print("   count=%s next_key=%s plate_list=%s" % (
            data.get("count"), data.get("next_key"),
            len(data.get("plate_list", []) or [])))
        rows = data.get("stock_list", []) or []
    else:
        rows = data or []
    print("   rows=%d" % len(rows))
    if rows:
        print("   row keys:", list(rows[0].keys()))
        fwd = sum(1 for r in rows if r.get("forward_value") not in (None, "", 0))
        print("   rows carrying forward_value: %d / %d" % (fwd, len(rows)))
    for r in rows[:sample]:
        print("     ", r)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
