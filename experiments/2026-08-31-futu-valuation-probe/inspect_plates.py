#!/usr/bin/env python3
"""Probe helper: summarise get_plate_list --json dumps (count + sample names)."""
import json
import sys


def load(path):
    s = open(path, encoding="utf-8").read()
    i = s.index("{")
    obj, _ = json.JSONDecoder().raw_decode(s[i:])
    return obj


def main(path, sample=40):
    obj = load(path)
    rows = obj.get("data", []) or []
    print("== %s  market=%s type=%s  count=%d" % (
        path, obj.get("market"), obj.get("type"), len(rows)))
    if obj.get("error"):
        print("   error:", obj.get("error"))
    for r in rows[:sample]:
        print("   %-16s %s" % (r.get("code"), r.get("name")))
    if len(rows) > sample:
        print("   ... (%d more)" % (len(rows) - sample))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
