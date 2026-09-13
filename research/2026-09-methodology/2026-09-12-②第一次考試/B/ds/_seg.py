import json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
eid = sys.argv[1]
idxs = [int(x) for x in sys.argv[2].split(',')]
width = int(sys.argv[3]) if len(sys.argv) > 3 else 4000
start = int(sys.argv[4]) if len(sys.argv) > 4 else 0
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'A3', 'packets')
d = json.load(open(os.path.join(base, eid + '.json'), encoding='utf-8'))
segs = d['2_觸發資料']['earnings_call_transcript']['segments']
for i in idxs:
    s = segs[i]
    txt = s.get('text') or s.get('content') or ''
    print('--- seg', i, 'len', len(txt))
    print(txt[start:start + width])
