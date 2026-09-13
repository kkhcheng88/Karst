import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

eid = sys.argv[1]
idx = int(sys.argv[2]) if len(sys.argv) > 2 else -1
lim = int(sys.argv[3]) if len(sys.argv) > 3 else 3000
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'A3', 'packets')
d = json.load(open(os.path.join(base, eid + '.json'), encoding='utf-8'))
keys = list(d.keys())
print('SECTIONS', keys)
if idx < 0:
    sys.exit(0)
k = keys[idx]
v = d[k]
print('== SECTION', idx, '==')
if isinstance(v, dict):
    for kk, vv in v.items():
        s = json.dumps(vv, ensure_ascii=False)
        print('--', kk, '::', s[:lim])
else:
    print(json.dumps(v, ensure_ascii=False)[:lim])
