import json, sys
eid = sys.argv[1]
sec = sys.argv[2] if len(sys.argv) > 2 else '4'
keys = sys.argv[3].split(',') if len(sys.argv) > 3 else None
p = json.load(open('A3/packets/%s.json' % eid, encoding='utf-8'))
d = p.get(sec) if sec in p else None
if d is None:
    for k, v in p.items():
        if k.startswith(sec):
            d = v
            print('SECTION', k)
            break
if not isinstance(d, dict):
    print('TYPE', type(d))
    print(str(d)[:3000])
    sys.exit()
for k, v in d.items():
    if keys and k not in keys:
        continue
    print('KEY', k, '=>', str(v)[:1500])
