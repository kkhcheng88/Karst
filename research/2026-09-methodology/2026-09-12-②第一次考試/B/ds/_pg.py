import json, sys
eid = sys.argv[1]
lim = int(sys.argv[2]) if len(sys.argv) > 2 else 1200
p = json.load(open('A3/packets/%s.json' % eid, encoding='utf-8'))
g = p['2_觸發資料'].get('prior_release_guidance')
if g is None:
    print('NO prior_release_guidance')
    sys.exit()
if isinstance(g, dict):
    for k, v in g.items():
        print('KEY', k, '=>', str(v)[:lim])
else:
    print('TYPE', type(g))
    print(str(g)[:lim])
