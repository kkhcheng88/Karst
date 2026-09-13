import json, os, glob
BASE = os.path.dirname(os.path.abspath(__file__))
PK = os.path.join(BASE, '..', '..', 'A3', 'packets')
rows = []
for fp in sorted(glob.glob(os.path.join(PK, 'E*.json'))):
    with open(fp, encoding='utf-8') as fh:
        p = json.load(fh)
    rows.append((p.get('event_id'), p.get('ticker'), p.get('sic'), p.get('sic2'), p.get('bucket'), p.get('name')))
print('total', len(rows))
from collections import Counter, defaultdict
c = Counter((r[2], r[4]) for r in rows)
print('--- sic4 x bucket ---')
for k, v in sorted(c.items(), key=lambda x: (-x[1], str(x[0]))):
    print(k, v)
print('--- nulls ---')
for r in rows:
    if not r[2] or not r[4] or not r[5]:
        print('NULL', r)
