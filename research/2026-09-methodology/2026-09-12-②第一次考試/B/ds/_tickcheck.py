import json, re, glob, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
PK = os.path.join(BASE, '..', '..', 'A3', 'packets')
EXCH = re.compile(r'\((?:NYSE|NASDAQ|Nasdaq|New York Stock Exchange|NYSE American|NYSE MKT)[:\s]+([A-Z][A-Z.\-]{0,5})\)')

rows = []
for f in sorted(glob.glob(os.path.join(PK, 'E*.json'))):
    with open(f, encoding='utf-8') as fh:
        p = json.load(fh)
    t = p['2_觸發資料']['ex991_full_text']
    found = sorted({m.group(1) for m in EXCH.finditer(t)})
    rows.append((p.get('event_id'), p.get('ticker'), found, p.get('name')))

mis = [r for r in rows if r[2] and r[1] not in r[2]]
noTag = [r[0] for r in rows if not r[2]]
print('total', len(rows), 'with_exchange_tag', len(rows) - len(noTag), 'mismatch', len(mis))
for r in mis:
    print('MISMATCH', r[0], 'packet_ticker=', r[1], 'release_tag=', r[2], 'packet_name=', r[3])
print('NO_TAG', noTag)
