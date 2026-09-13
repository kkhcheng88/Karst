import json, os, re
BASE = os.path.dirname(os.path.abspath(__file__))
PK = os.path.join(BASE, '..', '..', 'A3', 'packets')
for eid, pat in [('E024', r'Michael Kors|Capri'), ('E005', r'AMN Healthcare|AHS'), ('E011', r'Platform Specialty|Element Solutions'), ('E036', r'Ubiquiti|UBNT')]:
    with open(os.path.join(PK, eid + '.json'), encoding='utf-8') as fh:
        p = json.load(fh)
    t = p['2_觸發資料']['ex991_full_text']
    names = {}
    for m in re.finditer(pat, t):
        names[m.group(0)] = names.get(m.group(0), 0) + 1
    print(eid, 'packet_ticker=', p.get('ticker'), 'packet_name=', p.get('name'), 'hits=', names)
    head = t.split('\n')
    for l in head[:20]:
        if l.strip():
            print('   HEAD |', l.strip()[:200])
            break
