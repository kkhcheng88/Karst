import json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
# usage: _pkt.py <eid> <path>[ <maxchars>]
# path segments separated by '.'; a segment '#N' means the N-th key (0-based) of the current dict
eid = sys.argv[1]
path = sys.argv[2] if len(sys.argv) > 2 else ''
mx = int(sys.argv[3]) if len(sys.argv) > 3 else 3000
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'A3', 'packets')
d = json.load(open(os.path.join(base, eid + '.json'), encoding='utf-8'))
print('TOPKEYS', json.dumps(list(d.keys()), ensure_ascii=False))
cur = d
for seg in [s for s in path.split('.') if s]:
    if seg.startswith('#'):
        ks = list(cur.keys())
        k = ks[int(seg[1:])]
        print('SEG', seg, '->', k)
        cur = cur[k]
    else:
        cur = cur[seg]
    if isinstance(cur, dict):
        print('  KEYS', json.dumps(list(cur.keys()), ensure_ascii=False))
print('VALUE')
print(json.dumps(cur, ensure_ascii=False)[:mx])
